# UltraUltimateUpscale v7.0 — Content-Adaptive Upscale Pipeline (2026-05-20)

## 5-Algorithm Architecture

| Algorithm | Architecture | Parameters | Best For | Existing Model |
|-----------|-------------|-----------|----------|----------------|
| **HAT** | Hybrid Attention Transformer | 40.8M | Realistic detail, complex textures | 4xNomos8kSCHAT-L.pth (316MB) |
| **DRCT** | Deformable Conv Transformer | 27.6M | Geometry, architecture, buildings | 4xNomos2_hq_drct-l.pth (231MB) |
| **DAT** | Dual Aggregation Transformer | 11.2M | Balanced quality/speed | 4x-UltraSharpV2.safetensors (133MB) |
| **GRL** | Global Residual Learning | ~20M | Large images, detail preservation | auto-download (88MB) |
| **OmniSR** | Omni-Scale SR | ~12M | Multi-scale textures, edges | auto-download (12MB) |

## Architecture Detection from State Dict (Pre-Load)

Avoid loading the full model just to identify architecture. Use key prefix matching:

```python
def _detect_architecture(state_dict):
    """Quick architecture detection from state_dict keys — no full model load"""
    keys_str = " ".join(list(state_dict.keys())[:80])
    
    if "relative_position_index" in keys_str and "conv_mask" in keys_str:
        return "HAT"
    if "offset" in keys_str and "dcn" in keys_str:
        return "DRCT"
    if "dag" in keys_str or "dual_aggregation" in keys_str:
        return "DAT"
    if "grl" in keys_str or "global_residual" in keys_str:
        return "GRL"
    if "omni" in keys_str or "channel_attention" in keys_str:
        return "OmniSR"
    if "swin" in keys_str:
        return "SwinIR"
    if "conv_body" in keys_str or "RRDB" in keys_str or "rdb" in keys_str:
        return "ESRGAN"
    return "Unknown"
```

## Content Analysis for Adaptive Model Selection

Analyze the input image to pick the best model(s) automatically:

```python
def analyze_image_content(img_pil):
    """Returns recommended_arch and alt_arch based on texture/edge/size analysis"""
    arr = np.array(img_pil.convert("RGB")).astype(np.float32)
    gray = np.mean(arr, 2)
    
    # 1. Texture complexity (Laplacian variance)
    lap_var = np.var(
        gray[1:-1, 1:-1] * 4 - gray[:-2, 1:-1] - gray[2:, 1:-1] 
        - gray[1:-1, :-2] - gray[1:-1, 2:]
    )
    
    # 2. Edge density (PIL FIND_EDGES filter)
    from PIL import ImageFilter as PILFilter
    edge_arr = np.array(img_pil.convert("L").filter(PILFilter.FIND_EDGES))
    edge_density = np.mean(edge_arr > 30)
    
    # Decision tree
    if lap_var > 200 and edge_density > 0.15:
        return "hat"       # Complex texture → HAT
    elif edge_density > 0.15:
        return "detail"    # Strong edges → DRCT
    elif total_pixels > 4000000:
        return "general"   # Large image → GRL/OmniSR
    else:
        return "sharp"     # Default → DAT
```

## Frequency-Aware Enhancement Pipeline v2

Three-level processing that replaces v1's single-scale Laplacian:

### 1. Multiscale Laplacian Texture Enhancement

```python
def texture_enhance_v2(img, strength=0.2):
    """3-level Laplacian pyramid with adaptive gain"""
    arr = np.array(img).astype(np.float32)
    
    # 3 scales: level 0=detail, level 1=mid, level 2=coarse
    lap_results = []
    for level in range(3):
        kernel_vals = [0, -1, 0, -1, 4 + 4 * level, -1, 0, -1, 0]
        lap = np.array(img.filter(ImageFilter.Kernel(
            (3, 3), kernel_vals, scale=1 + level
        ))).astype(np.float32)
        lap_results.append(lap)
    
    # Weighted fusion: fine(0.5) + mid(0.3) + coarse(0.2)
    texture_signal = lap_results[0] * 0.5 + lap_results[1] * 0.3 + lap_results[2] * 0.2
    
    # Adaptive gain mask (only enhance textured regions)
    local_std = _local_std_map(arr, radius=5)
    gain = np.clip(local_std / 20.0, 0, 1)
    
    # Tanh clamping prevents overshoot halo
    texture_norm = np.tanh(texture_signal / 15.0) * 15.0
    
    return arr + texture_norm * gain * strength
```

### 2. Local Std Mask (for edge-aware processing)

```python
def _local_std_map(arr, radius=3):
    """Spatial variation map — high near edges, low in flat areas"""
    gray = np.mean(arr, 2) if arr.ndim == 3 else arr
    from scipy.ndimage import uniform_filter
    local_mean = uniform_filter(gray, radius)
    local_mean2 = uniform_filter(gray ** 2, radius)
    local_var = np.maximum(local_mean2 - local_mean ** 2, 0)
    return np.sqrt(local_var)
```

### 3. Gentle Sharpen v2 (S-curve mask + high-freq clamp)

```python
def gentle_sharpen_v2(img, strength=0.3):
    """Edge-aware USM with nonlinear mask"""
    arr = np.array(img).astype(np.float32)
    blur = np.array(img.filter(ImageFilter.GaussianBlur(1.0))).astype(np.float32)
    detail = arr - blur
    
    # S-curve mask: Sigmoid-like transition using tanh
    local_std = _local_std_map(arr, 3)
    mask = np.clip((local_std - 3.0) / 12.0, 0, 1)
    mask = np.tanh(mask * 3.0) / np.tanh(3.0)  # normalize to [0,1]
    
    # Clamp high-frequency amplitude to prevent halo
    detail = np.clip(detail, -30, 30)
    
    return arr + detail * mask * strength
```

### 4. Bilateral Denoise (edge-preserving median)

```python
def bilateral_denoise(img, strength=1):
    """PIL MedianFilter approximates bilateral — preserves edges, removes speckle"""
    for _ in range(min(strength, 2)):
        img = img.filter(ImageFilter.MedianFilter(3))
    return img
```

### 5. Color Restoration (post-enhancement)

After enhancing luminance detail, color can shift. Blend back original hue:

```python
def frequency_enhance_pipeline(img, sharpness=0.3, texture=0.2, 
                                denoise=0, color_restore=0.1):
    # Save original color
    orig_arr = np.array(img).astype(np.float32)
    
    # Apply texture → sharpen → denoise
    if texture > 0: img = texture_enhance_v2(img, strength=texture)
    if sharpness > 0: img = gentle_sharpen_v2(img, strength=sharpness)
    if denoise > 0: img = bilateral_denoise(img, strength=denoise)
    
    # Blend back original color: restored = orig * 0.1 + enhanced * 0.9
    new_arr = np.array(img).astype(np.float32)
    restored = orig_arr * color_restore + new_arr * (1 - color_restore)
    
    return Image.fromarray(restored.clip(0, 255).astype(np.uint8))
```

## Ensemble v2 Inference Patterns

### Padding Strategy

Each model has its own alignment requirement (usually 8, but sometimes larger for window-attention models). Instead of hardcoding:

```python
pad_mult = 8
# Check model for alignment requirement
if hasattr(model, "model"):
    for attr_name in ["scale", "img_range", "patch_size"]:
        if hasattr(model.model, attr_name):
            val = getattr(model.model, attr_name)
            if isinstance(val, int) and val > 1 and val < 128:
                pad_mult = max(pad_mult, val)
                break

ph = (pad_mult - h % pad_mult) % pad_mult
pw = (pad_mult - w % pad_mult) % pad_mult
if ph > 0 or pw > 0:
    t = F.pad(t, (0, pw, 0, ph), mode="reflect")
```

### Sin-Cos Dual Weight Tile Fusion

Improved from v1's single sin ramp to dual sin+cos for smoother transitions:

```python
# Precompute sin weights
sin_w_h = torch.sin(torch.linspace(0, math.pi / 2, ts)).view(-1, 1)
sin_w_w = torch.sin(torch.linspace(0, math.pi / 2, ts)).view(1, -1)

# Apply to each tile's overlap region
ffs = min(overlap * model_scale // 2, tile_h // 2, tile_w // 2)
if ffs > 4:
    for k in range(min(int(ffs), tile_h - 1, ts - 1)):
        weight[0, 0, k, :] *= sin_w_h[min(k, ts - 1)].item()
        weight[0, 0, tile_h - 1 - k, :] *= sin_w_h[min(k, ts - 1)].item()
    for k in range(min(int(ffs), tile_w - 1, ts - 1)):
        weight[0, 0, :, k] *= sin_w_w[0, min(k, ts - 1)].item()
        weight[0, 0, :, tile_w - 1 - k] *= sin_w_w[0, min(k, ts - 1)].item()
```

## No-Reference Quality Estimation

For quality reporting and debugging:

```python
def estimate_image_quality(img_pil):
    """Returns {'sharpness', 'texture_richness', 'noise_level', 'overall'}"""
    arr = np.array(img_pil.convert("RGB")).astype(np.float32)
    gray = np.mean(arr, 2)
    
    # Sharpness: Laplacian variance
    lap = gray[1:-1, 1:-1] * 4 - gray[:-2, 1:-1] - gray[2:, 1:-1] \
          - gray[1:-1, :-2] - gray[1:-1, 2:]
    sharpness = float(np.var(lap))
    
    # Texture: gradient magnitude
    gx = np.abs(gray[:, 1:] - gray[:, :-1])
    gy = np.abs(gray[1:, :] - gray[:-1, :])
    texture_richness = float(np.mean(gx) + np.mean(gy))
    
    # Noise: standard deviation of smooth-subtracted image
    smooth = uniform_filter(gray, 5)
    noise_level = float(np.std(gray - smooth))
    
    # Normalized composite
    overall = (min(sharpness/500, 1) * 0.4 
               + min(texture_richness/50, 1) * 0.4 
               + (1 - min(noise_level/20, 1)) * 0.2) * 100
    
    return {
        "sharpness": round(sharpness, 1),
        "texture_richness": round(texture_richness, 1),
        "noise_level": round(noise_level, 2),
        "overall": round(overall, 1),
    }
```

## Spandrel 0.4.2 Architecture Coverage

ComfyUI's Spandrel 0.4.2 supports 42 architectures for upscale models:

**Transformer-based:** HAT, DAT, DRCT, GRL, OmniSR, SwinIR, Swin2SR, RGT, PLKSR, FFTformer, DCTLSA, KBNet, SeemoRe, DITN, IPT, ATD, FDAT  
**CNN-based:** ESRGAN, RCAN, SAFMN, SPAN, CRAFT, Compact, SwiftSRGAN  
**Restoration:** GFPGAN, RestoreFormer, SCUNet, NAFNet, DRUNet, DnCNN, Uformer, MixDehazeNet, RetinexFormer, LaMa, FBCNN  
**Specialized:** RealCUGAN (anime), AuraSR (GAN-based), MoESR (MoE), MoSR, MMRealSR, SAFMNBCIE, HVICIDNet

## Dual Weight Loading (safetensors + .pth)

```python
ext = os.path.splitext(path)[1].lower()
if ext == ".safetensors":
    from safetensors.torch import load_file as safe_load
    raw = safe_load(path, device="cpu")
else:
    raw = torch.load(path, map_location="cpu", weights_only=False)

# Unwrap common wrapper keys
sd = raw
if isinstance(raw, dict):
    for key in ["params_ema", "params", "state_dict", "model", 
                 "net", "state", "model_state"]:
        if key in raw and isinstance(raw[key], dict):
            sd = raw[key]
            break

# Strip common prefixes
cleaned = OrderedDict()
for k, v in sd.items():
    cleaned[k.replace("module.", "").replace("_orig_mod.", "")] = v
```

## Model Enumeration Params (from real load)

| Model File | Arch | Params | Scale | Source |
|-----------|------|--------|-------|--------|
| 4x-UltraSharp.pth (64MB) | ESRGAN | 16.7M | 4x | chaiNNer |
| 4x-UltraSharpV2.safetensors (133MB) | DAT | 11.2M | 4x | chaiNNer |
| 4xNomos2_hq_drct-l.pth (231MB) | DRCT | 27.6M | 4x | OpenModelDB |
| 4xNomos8kSCHAT-L.pth (316MB) | HAT | 40.8M | 4x | OpenModelDB |
| 4x_RealisticRescaler.pth (128MB) | ESRGAN | 16.7M | 4x | OpenModelDB |
| x1_ITF_SkinDiffDetail.pth (19MB) | ESRGAN | 5.0M | 1x | OpenModelDB |
