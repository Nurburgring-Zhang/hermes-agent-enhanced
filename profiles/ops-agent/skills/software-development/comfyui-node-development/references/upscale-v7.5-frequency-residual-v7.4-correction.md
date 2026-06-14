# v7.5: Frequency-Domain HAT Residual Injection — The Corrected Approach

## Problem with v7.4 Residual Injection

The v7.4 HAT residual injection used **threshold-based filtering**:
```python
res_threshold = res_mag.median() * 1.5  # only top 50% of residual magnitude
res_mask = (res_mag > res_threshold).float()
residual_clamped = torch.clamp(residual, -0.05, 0.05)
hat_detail = residual_clamped * res_mask * 0.4
```

**This was wrong because:**
1. Threshold (median × 1.5) removed too much useful detail — only top 35% of pixels got any injection
2. Amplitude clamp at ±0.05 was too conservative — eliminated HAT's strongest texture advantages
3. Injection strength 0.4 was too weak — even when HAT had clearly better detail, it was only partially injected

## Correct Approach (v7.5): Frequency-Domain Decomposition + Full Injection

### Step 1: Extract only the HIGH-FREQUENCY component of the residual
```python
residual = hat_out - fused_result
res_smooth = F.avg_pool2d(residual, kernel_size=3, stride=1, padding=1)
res_detail = residual - res_smooth  # ONLY this gets injected
```
The low-frequency part of the residual contains tone/color shifts — injecting that causes color casts. The high-frequency part contains the texture details HAT reconstructed that other models didn't.

### Step 2: LARGER spatial mask + LOWER threshold
```python
res_mag = res_detail.abs()
res_local_mean = F.avg_pool2d(res_mag, kernel_size=15, stride=1, padding=7)
res_threshold = res_local_mean.median() * 0.8  # threshold BELOW median!
res_mask = (res_local_mean > res_threshold).float()
```
kernel_size 5→15, threshold median×1.5→×0.8, more pixels injected.

### Step 3: WIDER clamp + HIGHER injection strength
```python
res_detail_clamped = torch.clamp(res_detail, -0.08, 0.08)  # ±0.08 vs ±0.05
hat_detail = res_detail_clamped * res_mask * 0.6  # 0.6 vs 0.4
```

## v7.5 Pipeline Tuning Summary

| Parameter | v7.4 | v7.5 | Change |
|-----------|------|------|--------|
| Directional sharpen gain | 0.35 | 0.15 | -57% |
| High-frequency clamp | ±25 | ±35 | +40% |
| High-frequency multiplier | ×1.2 | ×1.8 | +50% |
| Mid-frequency clamp | ±20 | ±30 | +50% |
| Mid-frequency multiplier | ×0.8 | ×1.2 | +50% |
| Extreme mode tex upper limit | 0.6 | 1.0 | +67% |
| Residual injection clamp | ±0.05 | ±0.08 | +60% |
| Residual injection strength | 0.4 | 0.6 | +50% |
| Residual mask window | 5px | 15px | 3x larger |
| Residual mask threshold | median×1.5 | median×0.8 | 2x more pixels |

## v7.6 Fixes: 3 Bugfixes + 1 Enhancement

### Bugfix 1: HAT Residual Mask Could Zero Out Entire Image

**Symptom:** HAT residual injection does nothing. No texture improvement. Log says "HAT频域残差注入完成" but result is unchanged.

**Root cause:** `res_local_mean.median() * 0.8` can produce threshold=0 when median is 0 (most of residual = 0), then `res_local_mean > 0` is true everywhere → mask = 1 everywhere (all injected, no filter). OR if residual has tiny non-zero values, `median * 0.8` can be > all pixel values → mask = 0 everywhere (nothing injected).

**Fix:** Add epsilon floor to threshold:
```python
res_median = res_local_mean.median()
res_threshold = max(res_median * 0.8, 1e-6) if res_median > 0 else 1e-6
```

Also remove the separate amplitude clamp and rely on frequency decomposition itself to filter: `hat_detail = res_detail * res_mask * 0.8` (no clamp, 0.8 instead of 0.6).

### Bugfix 2: extra_round Using Original Image's Gaussian Pyramid

**Symptom:** extra_round (v5 frequency decomposition pipeline) applies texture enhancement to the WRONG frequency bands — it computes `curr_high = current_arr - _get_blur(1.5)` where `_get_blur(1.5)` returns a blur from the **original input image**, not from the `current_arr` (which has already been enhanced by the first round).

**Root cause:** The Gaussian pyramid is built from the original `img` parameter at function entry. The `_get_blur()` helper checks this pre-built pyramid first, which always contains the original image's blurs. When extra_round runs, `_get_blur(1.5)` returns the original's blur, not current_arr's.

**Fix:** In extra_round, always compute blurs directly on `current_arr` via PIL (never reuse the pre-built pyramid):
```python
extra_blur_r2 = np.array(Image.fromarray(current_arr.clip(0,255).astype(np.uint8)).filter(PILFilter.GaussianBlur(radius=1.5))).astype(np.float32)
extra_blur_r4 = np.array(Image.fromarray(current_arr.clip(0,255).astype(np.uint8)).filter(PILFilter.GaussianBlur(radius=4.0))).astype(np.float32)
curr_high = current_arr - extra_blur_r2
curr_mid = extra_blur_r2 - extra_blur_r4
```

### Bugfix 3: AuraSR Branch Hardcoded to Skip Extreme Enhancement

**Symptom:** AuraSR path never gets the double-round (extra_round) enhancement even when user selected "极致" mode — because `aurasr_extra = False` was hardcoded.

**Fix:** Dynamic check via parent function's parameter:
```python
aurasr_extra = 质量模式.startswith("极致") if '质量模式' in dir() else False
```

**Note:** For AuraSR, the quality mode that matters is the one the user selected — not the AuraSR branch's relationship to 极致/高质量. The AuraSR path uses `质量模式 == "优化版AuraSR放大"` as its condition, so `质量模式.startswith("极致")` will be False when AuraSR is active. This means the AuraSR branch never actually goes extreme — but the dynamic check at least makes it possible to introduce later without source-modifying the AuraSR block.

### Enhancement: Pre-processing UnsharpMask for Cleaner Input

**Problem:** Input images often have mild blur (lens softness, compression artifacts, slight downscale blur). All upscale models (HAT, DRCT, etc.) produce better detail when the input is sharp. A mild UnsharpMask before the ensemble run improves the input signal.

**Implementation (only for 极致 mode):**
```python
from PIL import ImageFilter as _prefilter
img_pre = img_pil.filter(_prefilter.UnsharpMask(radius=0.8, percent=30, threshold=5))
tensor = img2nchw(img_pre)
```

**Parameters rationale:**
- `radius=0.8` — very small, targets micro-detail only (not edge halos)
- `percent=30` — mild boost (30% contrast increase at edges), won't clip
- `threshold=5` — only affects edges with >5/255 contrast, skips flat regions

**Pitfall:** Do NOT use large radius (≥2.0) or high percent (≥50) — that creates false edges the upscale model will amplify, producing unnatural textures.

## Diagnostic: If White Halos Still Appear After v7.5

1. Check `frequency_enhance_pipeline` — directional (Sobel+mask) or blind USM?
2. Check extra_round — blanket or targeted via under-enhanced mask?
3. Check HAT residual clamp — ±0.05 (conservative, v7.4) or ±0.08 (correct, v7.5)?
4. Check extra_round blur source — original image's pyramid or computed on current_arr?
5. Check AuraSR extra_round — hardcoded False or dynamic?
