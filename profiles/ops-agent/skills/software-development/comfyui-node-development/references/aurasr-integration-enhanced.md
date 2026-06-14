# AuraSR Integration in Upscale Nodes — Enhanced Version

## About AuraSR

AuraSR is a GAN-based super-resolution model from fal-ai, reproducing the GigaGAN architecture for image-conditioned upscaling. It uses a UnetUpsampler with noise injection to generate realistic textures at 4x magnification.

**Architecture:** `AdaptiveConv2DMod` (style-modulated conv) + `UnetUpsampler` (UNet with skip connections) + noise injection (`torch.randn(batch, 128)`)

## AuraSR's 3 Core Defects

### Defect 1: Non-overlapping Tile Inference

```python
# ORIGINAL AuraSR — no overlap, hard tile boundaries
def tile_image(image, chunk_size=64):
    tiles = []
    for i in range(h_chunks):
        for j in range(w_chunks):
            tile = image[:, i*chunk_size:(i+1)*chunk_size, j*chunk_size:(j+1)*chunk_size]
            tiles.append(tile)
    return tiles, h_chunks, w_chunks
```

**Problem:** Tiles are cut at exact chunk boundaries with zero overlap. When merged, visible seam artifacts appear at every boundary.

**Fix:** Overlapped tiling with step-based extraction:

```python
def tile_image_overlapped(image_tensor, chunk_size=64, overlap=16):
    tiles, positions = [], []
    stride = chunk_size  # step = chunk_size (no skip)
    effective_overlap = min(overlap, chunk_size // 4)
    
    for hs in h_starts:
        for ws in w_starts:
            he = min(hs + chunk_size, h)
            we = min(ws + chunk_size, w)
            tile = image_tensor[:, hs:he, ws:we]
            tiles.append(tile)
            positions.append((hs, ws, he, we))
    
    return tiles, positions, (h, w)
```

Then fuse with gaussian-weighted blend:

```python
def merge_tiles_weighted(tiles, positions, image_size, output_scale=4):
    merged = torch.zeros((c, oh, ow), dtype=torch.float32)
    weight_map = torch.zeros((1, oh, ow), dtype=torch.float32)
    
    for tile, (hs, ws, he, we) in zip(tiles, positions):
        # Create gaussian weight tile — center high, edges low
        y_gauss = torch.exp(-torch.linspace(-2, 2, th)**2)
        x_gauss = torch.exp(-torch.linspace(-2, 2, tw)**2)
        w_tile = (y_gauss[:, None] * x_gauss[None, :])
        w_tile = w_tile / w_tile.max()
        
        merged[:, oys:oys+th, oxs:oxs+tw] += oc * w_tile
        weight_map[:, oys:oys+th, oxs:oxs+tw] += w_tile
    
    return merged / weight_map.clamp(min=1e-8)
```

### Defect 2: Weak Dual-Pass Fusion

AuraSR's `upscale_4x_overlapped` uses checkerboard weights for the second pass:

```python
# ORIGINAL — checkerboard pattern, sharp transitions
weight_tile = create_checkerboard_weights(tile_size)  # exp(-(d^2 / 2*sigma^2)) ** 8, sigma=0.5
```

**Problem:** The checkerboard (sigma=0.5, power=8) creates a very narrow transition band that still shows seams in high-contrast regions.

**Fix:** Use smoother gaussian (sigma=0.45, power=6) + laplacian pyramid as fallback:

```python
# IMPROVED — smoother gaussian
def create_gaussian_weights_torch(tile_size, sigma=0.45):
    weights = torch.exp(-((d)**2 / (2.0 * sigma**2)))
    weights = weights**6  # softer falloff than **8
    return weights / weights.max()

# Best quality — Laplacian pyramid blend
# Each frequency band blended independently
# High frequencies: energy-weighted (preserve richer texture side)
# Low frequency: simple average
def _laplacian_blend(img_a, img_b, levels=4):
    lp_a = laplace_pyramid(img_a, levels)
    lp_b = laplace_pyramid(img_b, levels)
    # ... per-level blend ...
```

### Defect 3: Dark/Highlight Texture Loss (GAN Hallucination)

**Root cause:** GAN generators prioritize "plausible" textures over faithful preservation. Dark regions (<60 luminance) and bright regions (>200 luminance) get simplified — GAN "fills in" with smooth gradations, discarding real texture.

**Detection metrics:**
- Dark area percentage: `np.mean(gray < 60)`
- Highlight area percentage: `np.mean(gray > 200)`
- Texture loss indicator: high local std in original but low local std in AuraSR output

**Three-layer compensation pipeline:**

```python
def aurasr_compensation_pipeline(img_pil, dark_comp=0.5, highlight_comp=0.4, 
                                  freq_comp=0.3, noise_reduction=0.2):
    # Layer 1: Dark/Highlight compensation
    #   - Dark: local adaptive histogram stretch in shadow regions
    #   - Highlight: laplacian detail injection into overexposed areas
    img = dark_highlight_compensation(img, dark_strength=dark_comp, 
                                      highlight_strength=highlight_comp)
    
    # Layer 2: Frequency domain compensation
    #   - Multi-bandpass: blur1-blur3 (mid-freq) + blur2-blur4 (low-freq)
    #   - Adaptive gain: flatter areas get MORE enhancement
    img = frequency_compensation(img, strength=freq_comp)
    
    # Layer 3: Adaptive noise reduction (anti-over-sharpen)
    #   - Detect regions where highpass > 25 with low local std
    #   - Apply mild blur only to those regions
    #   - Preserve genuine texture everywhere else
    img = adaptive_noise_reduction(img, strength=noise_reduction)
    return img
```

## Pre-Detail Extraction (Inject into AuraSR)

Run HAT/DRCT model BEFORE AuraSR to capture high-frequency detail:

```python
def extract_high_freq_detail(img_pil, model_obj=None, device='cpu'):
    # model output - bicubic upscale = high-frequency residual
    with torch.no_grad():
        out = model_obj(t)
    bicubic = F.interpolate(t, size=out.shape[2:], mode='bicubic')
    detail_map = out - bicubic
    return detail_map  # shape [C, H, W], values in [-0.3, 0.3]
```

Then inject into AuraSR output **only where AuraSR lost detail**:

```python
def inject_detail_to_aurasr(aura_output_pil, detail_map, ...):
    # Detect AuraSR's smooth regions (low local std)
    local_std = uniform_filter(gray**2, 5) - uniform_filter(gray, 5)**2
    # More injection where local_std is LOW (texture lost)
    inject_strength = 1.0 - clip(local_std / 0.15, 0, 1)
    result = aura_arr + detail_map * inject_strength * 0.3
```

## Adaptive Parameter Analysis

Auto-detect image characteristics and set optimal compensation:

```python
def analyze_aurasr_input(img_pil):
    dark_pct = np.mean(gray < 60)
    bright_pct = np.mean(gray > 200)
    texture_level = np.std(lap)  # laplacian variance
    
    return {
        "dark_comp": min(dark_pct * 2.0, 0.8),       # more dark → stronger comp
        "highlight_comp": min(bright_pct * 1.5, 0.6), # more bright → stronger comp
        "freq_comp": max(0.1, 0.4 - texture_level * 0.01), # less texture → more
        "noise_reduction": min(0.3, 0.1 + dark_pct * 0.3), # more dark → more noise
    }
```

## Module Architecture

Recommended split for production ComfyUI node:

```
uau_module1_loader.py     — Overlap tiling + gaussian merge + dual-pass fusion
uau_module2_compensation.py — Dark/highlight compensation + frequency boost + noise reduction
uau_module3_detail_preserve.py — Pre-detail extraction + injection + auto-analysis
uau_module4_node.py       — EnhancedAuraSR class + run_enhanced_aurasr() entry point
```

**Integration in main __init__.py:**

```python
if 质量模式 == "优化版AuraSR放大":
    from uau_module4_node import run_enhanced_aurasr
    result_pil = run_enhanced_aurasr(img_pil, ..., detail_model=best_model, ...)
    if result_pil is None:
        # fallback to regular model
```

## Known Limitations

- AuraSR requires downloading ~2GB model from HuggingFace (fal-ai/AuraSR)
- First run triggers auto-install via pip (`aura-sr` package)
- GAN generator creates plausible but not pixel-perfect textures — the compensation pipeline reduces this gap but cannot eliminate it
- The `_laplacian_blend` function is O(H*W) and can be slow on 4K+ images — fall back to gaussian blend for large images
