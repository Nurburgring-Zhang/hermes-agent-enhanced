# Upscale Multiplier Fix & White Halo Cascade Fix

## Problem 1: Upscale Multiplier Not Working (AuraSR Mode)

**Symptom:** Setting 放大倍率=2 or 8 in "优化版AuraSR放大" mode produces 4x output regardless.

**Root cause:** AuraSR only does 4x internally. The wrapper function `_inference_enhanced` handled non-4x by returning 4x result directly, relying on the caller to resize. But the caller (main node) didn't resize.

**Dual-resize trap:** Both `_inference_enhanced` AND the caller tried to resize. This caused double-interpolation quality loss.

**Fix (2 changes):**

1. In `uau_module4_node.py` → `_inference_enhanced()`:
```python
# BEFORE: module does its own resize
if upscale_factor != 4:
    result_4x = self._inference_enhanced(img_pil, 4, ...)
    tw = img_pil.size[0] * upscale_factor
    th = img_pil.size[1] * upscale_factor
    return result_4x.resize((tw, th), Image.LANCZOS)  # WRONG: double resize

# AFTER: module only returns 4x, caller resizes
if upscale_factor != 4:
    result_4x = self._inference_enhanced(img_pil, 4, ...)
    return result_4x  # caller does the final resize
```

2. In `__init__.py` → AuraSR branch:
```python
# AFTER inference, check if multiplier != 4 and resize
if 放大倍率 != 4:
    result_pil = result_pil.resize(
        (orig_w * 放大倍率, orig_h * 放大倍率), Image.LANCZOS
    )
```

**Rule:** Only one code path should handle resize. Let the outermost caller (the main node) be responsible. Inner wrappers return the native model output.

## Problem 2: White Halo Artifacts

**Symptom:** Bright white borders along high-contrast edges after upscaling.

**Root cause:** **Cascade overload** — not any single stage, but the cumulative effect of 5+ enhancement stages each adding 5-15% edge contrast. Total = 30-50% over-sharpening.

### The 7-Parameter Cascade Tuning

| Component | Original Clamp | Original Gain | Fixed Clamp | Fixed Gain | Reduction |
|-----------|---------------|--------------|-------------|------------|-----------|
| T3 highpass extraction | ±90 | x1.5 | **±55** | **x1.2** | 40% / 20% |
| T3 local contrast | ±60 | x0.8 | **±40** | **x0.6** | 33% / 25% |
| T3 frequency boost | ±45 | x1.0 | **±30** | **x0.8** | 33% / 20% |
| Sharpening (edge USM) | ±40 | x1.5 | **±25** | **x0.8** | 38% / 47% |

Plus AuraSR compensation defaults (from 0.5→0.35 for dark, 0.4→0.25 for highlight).

### Directional Sharpen (Permanent Fix)

Replace blind USM with edge-direction-aware sharpening:

```python
def directional_sharpen(img_pil, strength=0.3):
    """Sobel edge direction → enhance only along edge normal, not tangent.
    Traditional USM enhances contrast in ALL directions = white halos.
    Directional USM only enhances across the edge = no halos.
    """
    # 1. Compute Sobel gradient
    sobel_x = np.array([[-1,0,1],[-2,0,2],[-1,0,1]])
    sobel_y = np.array([[-1,-2,-1],[0,0,0],[1,2,1]])
    gx = convolve(gray, sobel_x)
    gy = convolve(gray, sobel_y)
    edge_mag = np.sqrt(gx**2 + gy**2)
    edge_angle = np.arctan2(gy, gx + 1e-8)
    
    # 2. Only enhance along edge normal (across the edge)
    # 3. Use gaussian-tuned mask: peak at mid-strength edges, 
    #    protect strong edges (already sharp) and weak edges (noise)
    edge_norm = edge_mag / edge_mag.max()
    mask = np.exp(-((edge_norm - 0.15)**2) / (2 * 0.08**2))
    protection = 1.0 - np.clip(edge_norm * 2.0, 0, 0.7)
    final_mask = mask * protection  # bell curve with high-edge protection
```

### The 5-Stage Compensation Pipeline (V4)

```
1. directional_sharpen (no-halo) → 
2. adaptive_tone_mapping (S-curve, prevents bright-brighter) →
3. enhance_dark_details (sigmoid lift, not linear stretch) →
4. texture_enhance_precise (DoG + local std gating) →
5. wavelet_texture_boost_v3 (multi-level Haar)
```

### Key Insight

Tuning individual stages independently is wrong — you can't fix cascading by reducing one stage. The fix must reduce ALL stages simultaneously by proportional amounts.
