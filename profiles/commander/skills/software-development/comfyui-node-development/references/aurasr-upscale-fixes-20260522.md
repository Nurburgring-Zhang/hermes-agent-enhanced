# AuraSR Upscale Fixes — 2026-05-22

## Fix 1: Upscale Factor Not Respected

### Problem
When user sets `放大倍率=2` or `放大倍率=8`, the output was always 4x (AuraSR's native scale). Non-4x factors silently ignored.

### Root Cause
AuraSR model (GigaGAN) is trained for 4x only. The `_inference_enhanced()` method had non-4x handling that did resize, but the result was intercepted by AuraSR's own 4x output — the resize never applied to the returned PIL image.

### Fix
Move the non-4x resize to the **caller** (`__init__.py`'s process method), after AuraSR returns the 4x result:

```python
# After AuraSR returns 4x result_pil:
if 放大倍率 != 4:
    result_pil = result_pil.resize(
        (orig_w * 放大倍率, orig_h * 放大倍率), 
        Image.LANCZOS
    )
```

Also remove the redundant resize from `_inference_enhanced()` to prevent double interpolation:

```python
# OLD (inside _inference_enhanced):
return result_4x.resize((tw, th), Image.LANCZOS)

# NEW:
return result_4x  # resize handled by caller
```

## Fix 2: Insufficient Detail (Texture Too Weak)

### Problem
T1/T2/T3 texture injection strength was too low. Texture thresholds were too high.

### Fix
Raise all three T-stage multipliers and lower activation thresholds:

| Stage | Threshold | Strength | Old Threshold | Old Strength |
|-------|-----------|----------|---------------|--------------|
| T1 Highpass | >0.1 | `texture*1.3` | >0.1 | `texture*1.0` |
| T2 Contrast | >0.15 | `texture*1.0` | >0.15 | `texture*0.8` |
| T3 Frequency | **>0.08** | `texture*1.3` | >0.2 | `texture*1.2` |

Plus: add 0.15 extra texture when running AuraSR mode:
```python
sharpness=max(0.0, 细节增强 - 0.2),  # reduce sharpness to prevent halos
texture=纹理增强 + 0.15,               # boost texture significantly
```

## Fix 3: White Halos (Over-Sharpening)

### Problem
High-contrast edges develop white blooming on the bright side and dark bands on the dark side.

### Root Cause: Cascade Overload
Multiple enhancement stages each add 5-15% edge contrast. With T1(highpass) + T2(contrast) + T3(frequency) + sharpen + wavelet all stacked, cumulative edge boost = 30-50% → overshoot → halos.

### 7-Point Fix

| Component | Original | Fixed | Reduction |
|-----------|----------|-------|-----------|
| T3 highpass clamp | ±90 | **±55** | 40% |
| T3 highpass gain | x1.5 | **x1.2** | 20% |
| T3 contrast clamp | ±60 | **±40** | 33% |
| T3 contrast gain | x0.8 | **x0.6** | 25% |
| T3 frequency clamp | ±45 | **±30** | 33% |
| T3 frequency gain | x1.0 | **x0.8** | 20% |
| Sharpen clamp | ±40 | **±25** | 38% |
| Sharpen gain | x1.5 | **x0.8** | 47% |
| Edge mask threshold | 8.0/20.0 | **12.0/25.0** | More conservative |

### Directional Sharpen (Permanent Fix)
Replace blind USM with Sobel-direction-aware sharpening:
- Compute gradient magnitude and direction via Sobel
- Sharpen only along edge normal direction
- Zero tangential enhancement → no edge side overshoot

See `uau_module2_compensation.py` → `directional_sharpen()`.

### S-Curve Tone Mapping
Replace linear dark-area stretch with sigmoid-style curve:
```
For pixel values < 0.3: map through sin(x * π/0.7) * 0.3 / sin(π/2)
```

### DoG + Gain Texture Enhancement
Use Difference of Gaussians to extract mid-frequency textures. Apply Gaussian gain curve peaked at medium-local-std regions. Near-zero std → no boost. High-std → minimal boost.
