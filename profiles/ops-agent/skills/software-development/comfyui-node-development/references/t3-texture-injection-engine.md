# T3 Texture Injection Engine v1

Three-stage post-processing pipeline that replaces gentle sharpen/texture enhancement for super-resolution outputs. Designed to mimic the texture richness of TTP/real-world upscaling without requiring GAN or diffusion models.

## Architecture (3 Stages)

```
output from upscale model
      │
      ▼
T1: Multi-scale Highpass Extraction
  - 3 radii: 1.5, 3.0, 6.0 pixels (Gaussian blur)
  - Weights: 0.5, 0.35, 0.15 (small→medium→large)
  - Adaptive gain via local std map: smooth areas get MORE boost
  - Clip amplitude: [-90, 90] (vs. old [-30, 30])
  - Effective range: detail_strength=0.3→1.5 mapping
  - Function: `t3_highpass_detail_extraction(img, strength)`
      │
      ▼
T2: Local Contrast Stretch
  - Subtract local mean (Gaussian blur radius=8)
  - Adaptive gain based on local contrast magnitude
  - Boost range: [0.3x, 3.0x] depending on local texture
  - Clip amplitude: [-60, 60]
  - Function: `t3_local_contrast_stretch(img, strength, radius=8)`
      │
      ▼
Sharpness Pass (edge-only, separate from texture)
  - Large radius USM (2.0px Gaussian)
  - Edge mask: local_std > 8 → full boost, local_std < 8 → tapered
  - Clip amplitude: [-40, 40]
  - Function: built into `frequency_enhance_pipeline()`
      │
      ▼
T3: Frequency Boost
  - Band-pass decomposition:
    - high_freq = small_blur(1.0) - medium_blur(2.5)
    - mid_freq = medium_blur(2.5) - large_blur(5.0)
  - Weight: high_freq×0.4 + mid_freq×0.6 (mid-band has richest texture)
  - Adaptive gain peaks at ~40% local std (moderate texture areas)
  - Clip amplitude: [-45, 45]
  - Function: `t3_frequency_boost(img, strength)`
      │
      ▼
final denoise + color restore
```

## Parameter Mapping

| User param | T1 strength | T2 strength | Sharpness | T3 strength | Denoise |
|-----------|-------------|-------------|-----------|-------------|---------|
| texture=0.1 | 0.15×1.5=0.225 | 0 | 0 | 0 | 0 |
| texture=0.3 | 0.45 | 0.36 | 0 | 0.36 | 0 |
| texture=0.5 | 0.75 | 0.6 | 0 | 0.6 | 0 |
| texture=0.8 | 1.2 | 0.96 | 0 | 0.96 | 0 |
| texture=1.0 | 1.5 | 1.2 | 0 | 1.2 | 0 |
| sharpness=X | - | - | X×1.5 | - | - |

Thresholds: T1 activates at texture>0.1, T2 at texture>0.15, T3 at texture>0.2

## Key Differences from Old v2 Pipeline

| Dimension | Old v2 | New T3 v1 |
|-----------|--------|------------|
| Highpass radius | 1.0 (single) | 1.5/3.0/6.0 (multi-scale) |
| Amplitude clamp | [-30, 30] | [-90, 90] (3×) |
| Sharpness radius | 1.0 | 2.0 (separated from texture) |
| Contrast stretch | None | 8px radius CLAHE-style |
| Frequency boost | None | Band-pass (high+mid separated) |
| Texture in smooth areas | Suppressed by gain | INCREASED by inverse gain |
| Total effective boost | 0-1× | 0-2× (with 1.5× multiplier) |

## Integration Points

In `UltraUltimateUpscale/__init__.py`:
- Replace `gentle_sharpen_v2` + `texture_enhance_v2` + `frequency_enhance_pipeline` with T3 versions
- Keep `frequency_enhance_pipeline()` as the entry point (same signature)
- Make sure denoise runs AFTER all T3 stages (not between them)
- Color restore at the end prevents color shift from aggressive texture boost

## Limitations

- NOT a replacement for GAN-based upscalers (AuraSR/GigaGAN)
- Can introduce noise if texture strength > 0.8 on clean/low-noise images — use denoise parameter as safety net
- T3 assumes the base model output has some texture to work with; outputs from bicubic/ESRGAN-lite models may not have enough high-frequency content for T3 to amplify
- Works best at 2×-4× upscale ratios; at 8× the texture bands get stretched too thin
