# Pre-processing UnsharpMask for Super-Resolution Input

## Why This Works

All super-resolution models (HAT, DRCT, SwinIR, ESRGAN) are trained on sharp, high-quality image pairs. When the input has mild blur (lens softness, JPEG compression, downscale blur), these models produce weaker detail because they're trying to recover structure from a degraded signal.

A mild UnsharpMask applied **before** the upscale model run improves the input signal-to-noise ratio for the parts the model cares about (edges, texture boundaries), without creating false edges.

## Parameters That Matter

| Parameter | Value | Why |
|-----------|-------|-----|
| `radius` | 0.8 | Targets micro-detail (hair, skin pores, fabric weave). Larger radii create over-sharp edge halos. |
| `percent` | 30 | Mild contrast boost. Higher values (≥70) clip highlights. |
| `threshold` | 5 | Ignores flat regions (noise), only applies to edges with contrast >5/255. |

## Implementation

```python
from PIL import ImageFilter

# Apply before sending to upscale model
img_sharp = img_pil.filter(ImageFilter.UnsharpMask(radius=0.8, percent=30, threshold=5))
tensor = img2nchw(img_sharp)
```

## When NOT to Use

- Input is already oversharpened (has visible white halos from post-processing)
- Input is AI-generated (SD/MJ outputs are already sharp — extra sharpening creates artifacts)
- Image is highly compressed JPEG (block artifacts amplified)
- Image has film grain (grain amplified, looks noisy)

## Known Failure Mode

If `radius >= 2.0` and `percent >= 50`, the UnsharpMask creates visible white halos around strong edges. These halosget amplified by the upscale model → doubled in the output. Always use `radius < 1.0` and `percent < 40`.

## Relation to Other Enhancements

This is a PRE-processing step (before ensemble fusion). It's different from:
- Directional sharpen (in `frequency_enhance_pipeline`) — POST-processing, Sobel-guided, runs after fusion
- HAT residual injection — runs after fusion, extracts HAT-specific detail from the residual
- T3 texture engine — PIL-based detail injection on the final output

**Pipeline order matters:**
```
Input → UnsharpMask(pre) → Ensemble Fusion → HAT Residual Injection → Frequency Decomposition(post)
```
