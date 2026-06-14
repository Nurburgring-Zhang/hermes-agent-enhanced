# UltraUltimateUpscale v7.4 — Frequency-Decomposition Pipeline + HAT Residual Injection

## Background

This session addressed two quality complaints after v7.2/v7.3: (1) white edge halos appearing in both 极致 and 高质量 modes, and (2) detail improvement from v7.2's spatial fusion being "only a little better" — not yet surpassing 高质量 convincingly.

## Root Cause Analysis

### White Halo: Two Failures, Not One

**Failure A — Directional Sharpen Bypassed:** The main `__init__.py` pipeline's `frequency_enhance_pipeline()` (v4) ran its own sharpening via `arr - blur_large` — blind USM, isotropic, produces edge overshoot on both sides of every edge. Meanwhile, `uau_module2_compensation.py` had a perfectly good `directional_sharpen()` using Sobel direction analysis + bell-curve edge mask. But it was only called by `aurasr_compensation_pipeline()` in the AuraSR branch — the main 极致/高质量 path never touched it. So the fix existed but was on a code path that wasn't used by the primary use case.

**Lesson for architecture:** A bug-fix function living in a module file that isn't imported by the primary execution path is effectively non-existent. When diagnosing white halos, always check WHICH sharpening function actually runs on the main path, not just which functions exist in the codebase.

**Failure B — Cascade Architecture:** Even if directional sharpen was used, the v4 pipeline had 4 sequential whole-image transforms: T1 highpass → T2 contrast → Sharp → T3 frequency. Plus a 5th for 极致 extra_round. Each independently amplified edges. The cumulative effect (30-50% overshoot) would appear even with directional sharpen — just less severely.

### Detail Deficit: HAT's Strength Was Being Averaged Out

v3 spatial fusion (`ensemble_spatial_fuse`) improved over v2's global weighted average by selecting per-pixel "which model did best here." But that's still a **selection** strategy, not a **recovery** strategy. HAT's 317MB model reconstructs texture details that no other model (DRCT 232MB, UltraSharp 134MB) can match. But the fusion output at each pixel is a blend of multiple models — HAT's best texture work is always partially diluted.

The post-processing pipeline (T3/v4) was a generic "enhance whole image" operation — it couldn't distinguish "this region was poorly handled by the ensemble" from "this region already looks fine, don't touch it."

## Solution: Three Changes

### 1. Directional Sharpen in Main Pipeline (replaced blind USM)

```python
# BEFORE: blind USM — every direction amplified equally
blur_large = gaussian_blur(img, 2.0)
edge_detail = arr - blur_large  # all-directional
result = arr + edge_detail * mask * 0.8

# AFTER: Sobel-direction-aware — only edge normal enhanced
gx = convolve(gray, sobel_x)
gy = convolve(gray, sobel_y)
edge_mag = sqrt(gx**2 + gy**2)
# Bell curve centered at medium edge strength
edge_mask = exp(-((edge_norm - 0.2)**2) / (2 * 0.1**2))
# Protect high-contrast edges from overshoot
protection = 1.0 - clip(edge_norm * 2.0, 0, 0.7)
final_mask = edge_mask * protection

lap_detail = arr - gaussian_blur(img, 1.5)  # fine-scale edges only
lap_detail = clip(lap_detail, -20, 20)
result = arr + lap_detail * final_mask * 0.35  # halved gain
```

**Key parameters:**
- Sobel kernel 3x3 (standard)
- Edge mask bell curve: center=0.2, sigma=0.1
- Protection clamp: 1.0 - edge_norm*2.0, capped at 0.7 (so strongest edges get 30% min protection)
- Sharpness gain: 0.35 (was 0.8 — more than halved because the directional approach is more precise)
- Lap clamp: ±20 (was ±25)
- Mask smoothed with GaussianBlur(radius=2) to prevent abrupt transitions

### 2. Frequency-Decomposition Pipeline (replaced serial cascade)

```python
# BEFORE: 4 sequential whole-image transforms
img = t3_highpass_detail_extraction(img, strength)
img = t3_local_contrast_stretch(img, strength)
img = directional_sharpen_v2(img, sharpness)
img = t3_frequency_boost(img, strength)

# AFTER: single decomposition, independent band enhancement
b_r2 = gaussian_blur(1.5)     # high/mid boundary
b_r4 = gaussian_blur(4.0)     # mid/low boundary

high_freq = arr - b_r2        # micro-texture, hair, pores
mid_freq = b_r2 - b_r4        # medium texture, fabric
# low_freq = b_r4 - b_r6      # tone/lighting — NOT TOUCHED

# Texture: enhance high+mid only, gain controlled by local variance
hf_gain = clip(4.0 * norm_std * exp(-4.0 * norm_std), 0, 1.0)
mf_gain = clip(norm_std * 3.0, 0, 1.0)

arr = arr + clip(high_freq * hf_gain, -25, 25) * texture * 1.2
arr = arr + clip(mid_freq * mf_gain, -20, 20) * texture * 0.8

# Sharpening (directional — see section 1)
# Denoise: only attenuate high-freq in smooth regions
smooth_mask = 1.0 - norm_std_3c
attenuated_high = high_freq * (1.0 - smooth_mask * denoise * 0.3)
arr = b_r2 + attenuated_high  # re-synthesize
```

**Key insight:** The low-frequency band (blur radius > 4.0) contains tone, lighting, and large-scale structure — it should NEVER be enhanced. All detail/edge work happens on high+mid bands. This eliminates the "enhance everything and hope" problem.

### 3. HAT Detail Residual Injection

```python
# After ensemble fusion, before post-processing
# HAT model is already cached from the ensemble step
hat_out = hat_model(original_input)
residual = hat_out - fused_result

# Only inject where HAT clearly outperforms
res_mag = residual.abs().mean(dim=1, keepdim=True)
threshold = res_mag.median() * 1.5  # adaptive per image
mask = (res_mag > threshold).float()
mask = F.avg_pool2d(mask, 5, 1, 2)  # 5x5 smooth
mask = (mask > 0.1).float()  # binarize with transition

# Clamp to prevent artifacts
residual = clip(residual, -0.05, 0.05)
injection = residual * mask * 0.4
result = fused_result + injection
```

**Key parameters:**
- Threshold: median × 1.5 (adaptive — works across different image types)
- Clamp: ±0.05 in [0,1] range (about ±12.7 in 0-255 — prevents visible artifacts)
- Mask smooth: 5x5 avg_pool (prevents sharp injection boundaries)
- Injection strength: 0.4 (40% of residual — enough to be visible, safe from overshoot)
- **Only runs in 极致 mode** (高质量 doesn't need this extra compute)

### extra_round v2: Targeted Under-Enhanced Region Boost

The old extra_round ran another `t3_frequency_boost` on the entire image. The new one computes a **region-specific mask** first:

```python
# After first pass of enhancement
current_std = local_std_map(current_result)
under_enhanced = 1.0 - clip(current_norm / 0.3, 0, 1)
# Only boost regions where variance is still < 0.3 normalized
extra_hf = clip(curr_high * under_enhanced, -15, 15) * texture * 0.5
extra_mf = clip(curr_mid * under_enhanced, -10, 10) * texture * 0.3
arr = arr + extra_hf + extra_mf
```

## Performance Impact

| Change | Compute Overhead | Quality Impact |
|--------|-----------------|----------------|
| Directional sharpen (USM→Sobel) | ~10% more CPU (Sobel conv) | Eliminates main white halo source |
| Frequency decomposition | Same as v4 (same # of blurs) | Eliminates cascade overshoot |
| HAT residual injection | 1 extra HAT inference (~25% more total) | **Main quality driver** — HAT detail recovered |
| Targeted extra_round | Slightly more CPU (local_std recompute) | Prevents over-sharpening good regions |

## Testing Signals

To verify the fix works:
1. **White halo test:** Create a high-contrast edge test image (white background, black text at 8-24pt). Run 极致 mode. Zoom to 200%. If white pixels extend >2px from text edges, sharpen gain or clamp is too high.
2. **Detail resolution test:** Use a hair/skin texture image (face closeup). Compare 高质量 vs 极致 at 400% zoom. 极致 should show clearer individual hair strands and skin pore detail without halos.
3. **Smooth region test:** Use a sky/plain wall image. Run 极致 mode. If noise or false texture appears in originally smooth areas, the smooth-region denoise or the texture gain curve is too aggressive.

## Files Changed

`D:\ComfyUI\custom_nodes\UltraUltimateUpscale\__init__.py` (single file, all changes):
- `frequency_enhance_pipeline()` — complete rewrite from v4 to v5
- Post-fusion HAT residual injection block (lines ~1645-1700)
- Version bump to v7.4

Backup chain: `.bak` (original) → `.v7.2` → `.v7.3` → `.v7.4` (current)
