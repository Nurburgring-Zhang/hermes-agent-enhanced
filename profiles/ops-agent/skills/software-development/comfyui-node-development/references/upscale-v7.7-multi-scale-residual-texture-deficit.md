# v7.7: Multi-Scale Residual Pyramid + Gradient Texture Deficit Injection

## Background

After v7.5 (frequency-domain HAT residual injection) and v7.6 (bugfixes + pre-processing UnsharpMask), user feedback was: "细节补充不足、材质纹理不清晰！比TTP放大工作流差太远！"

The core limitation: pure super-resolution models (HAT/DRCT) reconstruct existing information but cannot **generate** new high-frequency texture detail the way TTP's SD+tile workflow can. TTP uses Stable Diffusion + ControlNet to regenerate each tile with full generative capability — something no upscale model can match.

## Three Mechanisms to Bridge the Gap

### 1. Iterative Stepwise Upscale (2x→enhance→2x)

**File location:** `__init__.py` → `stepwise_iterative_upscale()`

Instead of 4x in one pass: downscale input to 50% → 2x model → detail enhance → 2x model again → 4x result.

**Why this works:** HAT/DRCT produce better detail when the input degradation is closer to sharp (50% downscale has less information loss than 25%). The mid-step enhancement corrects texture smoothing between passes.

**Pitfalls:**
- Only supports model_scale=4. Falls back to direct inference for other scales.
- The 2x output is at FULL resolution (w_in × h_in), not w_in/2 × h_in/2. The model takes a half-size image and upscales it 2x back to full size.
- Adds ~30% to inference time (3 model passes instead of 2, including the direct 4x).

### 2. Multi-Scale Residual Pyramid Fusion

**File location:** `__init__.py` → `multi_scale_residual_fusion()`

Computes HAT residual at 2x scale (different from v7.5's same-scale residual): downsample input, run HAT to get 2x output, compare against ensemble result downsampled to same size. Extract only the mid-frequency component (filtered via uniform_filter size=5). Spatial mask uses median×1.2 threshold.

**Key differences from v7.5 residual injection:**
| Aspect | v7.5 (same-scale) | v7.7 (multi-scale) |
|--------|-------------------|-------------------|
| Scale | 4x (original res) | 2x (half input → full intermediate) |
| Frequency filter | avg_pool2d(k=3) | uniform_filter(k=5) |
| Threshold | median × 0.8 | median × 1.2 |
| Clamp | ±0.08 on [0,1] | ±12 on [0,255] |
| Smoothing | 15px box → binary | PIL GaussianBlur(r=3) |

**Why this produces different details:** HAT's internal feature representations at different scales capture different frequency bands. At 2x, HAT emphasizes mid-frequency texture (fabric weave, skin grain). At 4x, it emphasizes high-frequency sharpening (edges, crispness). Both are useful.

### 3. Gradient-Based Texture Deficit Injection

**File location:** `__init__.py` → `texture_deficit_injection()`

Compares gradient magnitude between original (resized to output) and upscaled result. Where original has more texture, inject original's high-frequency content.

**Algorithm:**
1. Resize original to output resolution (LANCZOS)
2. Per-channel gradient magnitude via simple difference
3. Deficit = max(0, ref_gradient - upscaled_gradient × 1.5)
4. Normalize deficit to [0,1] → resize/blur → use as injection mask
5. Extract original's high-freq: original - GaussianBlur(r=1.5, clamp ±20)
6. Inject: masked_highfreq × strength × 0.5

**Pitfalls:**
- **Shape alignment:** gx is [H, W-1], gy is [H-1, W]. Must be separately compared, then combined and resized. The raw gradient images CANNOT be added without alignment.
- **Smooth region over-injection:** If original has noise/compression artifacts in smooth areas, they get amplified. The ×1.5 factor on upscaled gradient acts as a noise gate.
- **PIL GaussianBlur radius=5** for mask smoothing is critical — without it, injection boundaries look unnatural.

## TTP Architecture Analysis

TTP's `TTP_toolsets.py` (at D:\ComfyUI\custom_nodes\Comfyui_TTP_Toolset\TTP_toolsets.py) reveals the workflow:

1. **TTPlanet_Tile_Preprocessor_Simple** — downsamples input by scale_factor, blurs it, uses as structure guide
2. **TTP_Image_Tile_Batch** — splits input into tiles with overlap (calculated from tile_size and image size)
3. **TTP_Image_Assy** — reassembles tiles with gradient-based blending (horizontal row blending → vertical blending)
4. **TTP_Conditioning nodes** — SD conditioning + area conditioning per tile for guided generation

**Key insight:** TTP doesn't use upscale models at all. It uses SD's generative capability to recreate each tile at higher resolution, guided by the downsampled+blurred original as a ControlNet condition. This is fundamentally different from the ensemble+residual approach — it's generative, not reconstructive.

## Final v7.7 Pipeline

极致模式 execution order (v7.7):
```
① Pre-processing UnsharpMask (radius=0.8, 30%, threshold=5)
② Ensemble v3 spatial fusion (HAT+DRCT+UltraSharp, top-3)
③ Extreme Enhancement Pipeline:
   ③a: Multi-scale residual pyramid (HAT 2x residual)
   ③b: Gradient texture deficit injection
④ v5 Frequency pipeline (weak sharpen + strong texture + extra_round)
```
