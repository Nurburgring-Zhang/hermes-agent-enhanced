
---

## Ensemble Fusion Evolution: v2 (Weighted Average) → v3 (Spatial Adaptive)

**Session: 2026-05-24 UltraUltimateUpscale v7.2**
Source: `D:\\ComfyUI\\custom_nodes\\UltraUltimateUpscale\\__init__.py` (v7.2: 1495 lines)

### The Problem with Naive Weighted Average (v2)

Simple weighted averaging (`torch.stack(aligned).sum(dim=0)`) has a fatal flaw: **different models excel at different image regions**, but weighted averages apply the same weights everywhere.

| Model | Strength | Weakness |
|-------|----------|----------|
| HAT (317MB) | Texture reconstruction (hair, skin pores, fabric) | Slight over-sharpening on flat areas |
| DRCT (232MB) | Geometric structures, edge fidelity | Less detail density than HAT in textured zones |
| UltraSharp/DAT | High-contrast edges, text | Over-smooths fine texture |
| RealESRGAN (RRDB) | Smooth gradients, no artifacts | Poor detail reconstruction |

With equal weights, HAT's texture detail gets diluted by DRCT/UltraSharp; DRCT's geometric precision gets blurred by HAT. **Both models' strengths are averaged out.**

### Solution: Spatial Adaptive Fusion (v3)

**High-texture zones → HAT dominates. Edge zones → DRCT/UltraSharp dominates. Flat zones → weighted average.**

#### Step 1: Local Clarity Map (Laplacian of Variance)

```python
def _local_clarity_map(tensor_nchw):
    gray = arr.mean(dim=1, keepdim=True)
    lap = F.conv2d(pad(gray), laplacian_kernel)
    local_mean = F.avg_pool2d(lap, 7, 1, 3)
    local_var = F.avg_pool2d(lap**2, 7, 1, 3) - local_mean**2
    clarity = sqrt(clamp(local_var, 0))
    clarity /= clarity.max() + 1e-8
    return clarity
```

High variance = well-reconstructed detail. Low variance = smooth/detail lost.

#### Step 2: Softmax Spatial Weighting

```python
all_clarity = torch.cat(clarity_maps, dim=0)       # [N,1,H,W]
advantage = F.softmax(all_clarity * 4.0, dim=0)    # [N,1,H,W]
# Mix with global weights (60% spatial, 40% prior)
if w_sum > 0:
    w_tensor = torch.tensor([w/w_sum for w in weights]).view(N,1,1,1)
    advantage = advantage * 0.6 + w_tensor * 0.4
    advantage /= advantage.sum(dim=0, keepdim=True)
stacked = torch.cat(aligned, dim=0)
result = (stacked * advantage).sum(dim=0, keepdim=True)
```

Temperature=4.0 means near-hard selection per pixel.

#### Tiled Spatial Fusion (v3_tiled)

Key difference from v2: **fuse at tile level, not globally**.

```
v2 (BAD): Each model runs full-image → independent tile stitching → weighted average
  → N sets of tile boundary artifacts overlap in final fusion

v3 (GOOD): Per-tile: run all models → spatial fuse → single tile → stitch
  → Only 1 set of tile boundaries (from the fused result)
```

### Bug Patterns Found During Implementation

| # | Bug | Symptom | Fix |
|---|-----|---------|-----|
| 1 | **Variable shadowing** — `tensor.shape` destructured `_, _, h, w`, then `ow_` used but `w_` was referenced in loop | `NameError: name 'w_' is not defined` | Rename `ow_` → `ow_max`; use `w` for original width |
| 2 | **stack vs cat** — `torch.stack([t1,t2], dim=0)` on `[1,C,H,W]` tensors produces `[2,1,C,H,W]` | Output shape `[1,2,3,128,128]` instead of `[1,3,128,128]` | Use `torch.cat(dim=0)` |
| 3 | **Missing keepdim** — `.sum(dim=0)` drops batch dim | Output `[3,H,W]` instead of `[1,C,H,W]` | Add `keepdim=True` |
| 4 | **Zero-weight division** — `sum([0,0])=0` → NaN | NaN in advantage map | Guard with `if w_sum > 0:` |
| 5 | **Instance method override** — `obj.__call__ = fn` doesn't work for special methods | Called original method | Use separate FailModel class with `__call__` defined at class level |

### The "Too-Many-Models" Dilution Trap

Counter-intuitively, **more models in the ensemble can hurt quality**. In v7.0, "极致" mode selected top-5 models while "高质量" selected top-3. Adding #4 and #5 **diluted the ensemble** — weaker models dragged the average down.

Fix: Both modes use top-3. "极致" differentiates through:
1. Spatial adaptive fusion (v3) instead of weighted average (v2)
2. Double-pass post-processing (1.3x sharpness + frequency boost)
3. Double tile overlap (max(overlap*2, 64)) to eliminate seam artifacts

### Rigorous Testing Methodology: 3-Cycle Commercial-Grade Validation

**Framework:** "极其严苛的多工况商用级测试" — extreme multi-condition commercial-grade testing.

#### Cycle Structure

```
Phase 1: Multi-condition testing (5 modes x 3 image types x 2 sizes)
  → Phase 2: Deep code review (line-by-line, pattern analysis)
    → Phase 3: Fix + optimize
      → Repeat from Phase 1 (minimum 3 cycles)
```

#### Test Battery (44 tests)

| Category | Test Cases |
|----------|-----------|
| **Boundary conditions** | All-black, all-white, 8x8 minimum, single-channel |
| **Empty/null input** | Empty list, None, all models fail, partial models fail |
| **Dimension alignment** | Different sizes (32x32+64x64→64x64), different scales (4x+2x→128x128) |
| **Weight edge cases** | Zero weights, single weight, N weights |
| **Large images** | 256x256→1024x1024 tiled |
| **Extreme large** | 1024x1024→4096x4096 (16MP output) |
| **Zero-strength** | strength=0→return original (all T3 functions) |
| **v2 regression** | Original ensemble_v2, tiled_v2, single-model tiled still work |
| **Classification** | 8 model type classifications correct |
| **Tensor conversion** | NHWC↔NCHW round-trip accuracy |

#### Verification Checklist

- [x] Syntax passes `ast.parse()` on full source
- [x] No bare `except:` — all catch `Exception` or specific types
- [x] All model inference inside `with torch.no_grad():`
- [x] GPU→CPU transfers before operations: `.cpu()` called on all outputs
- [x] Divide-by-zero guards: `1e-8` epsilon on all divisions
- [x] Tile boundary guard: `ffs = min(ov * scale, ah//2, aw//2)` prevents index errors
- [x] Size limit: output capped at 65536px per dimension
- [x] Tensor clamping: `.clamp(0, 1)` on all output tensors
- [x] CUDA memory cleanup: `torch.cuda.empty_cache()` after tile batches
- [x] Fallback chain: ensemble → single model → Lanczos

### v7.3 Efficiency Optimizations (2026-05-24)

**Session: UltraUltimateUpscale v7.3** — four optimizations targeting different bottlenecks, validated through theoretical modeling before implementation.

#### Optimization 1: Tile Overlap Lower Bound Fix

**Problem:** `max(overlap * 2, 64)` had a hard 64px floor — users couldn't reduce overlap below 64px even for small images, causing 30% more tiles on large images.

**Fix:** `max(int(overlap * 1.5), tile_size // 8, overlap)` — scales with tile_size, no hardcoded floor.

| Image Size | v7.2 overlap | v7.3 overlap | Tiles (640 tile) | Savings |
|------------|-------------|-------------|-------------------|---------|
| 4096x4096  | 96px        | 80px        | 64→56            | 12.5%   |
| 8192x8192  | 96px        | 80px        | ~260→~221        | ~15%    |

#### Optimization 2: Precomputed Gaussian Pyramid (T3 v2)

**Problem:** `frequency_enhance_pipeline` (T1+T2+sharpness+T3) called 12+ independent GaussianBlur operations. The extreme double-pass called 3 more.

**Fix:** Precompute 8 radii once, pass as `gauss_pyramid` dict:

```python
def _build_gaussian_pyramid(img_pil, radii):
    return {r: np.array(img.filter(GaussianBlur(radius=r))).astype(np.float32)
            for r in sorted(set(radii))}
```

Each T3 v2 function (`t3_highpass_detail_extraction_v2`, `t3_local_contrast_stretch_v2`, `t3_frequency_boost_v2`) accepts `gauss_pyramid=None` — reads from dict when provided, falls back to independent calc when None.

`frequency_enhance_pipeline` v4 adds:
- `use_pyramid=True` — enables precomputation
- `extra_round=False` — double-pass inside same function (replaces separate call)

**GaussianBlur calls:** 15 → **6** (-60%) for extreme double-pass mode.

#### Optimization 3: Smooth-Tile Skip in v3 Tiled Ensemble

Per-tile variance check on GPU. If `torch.var(tile_gray) < 0.002`, tile is smooth → single model only, no fusion.

```python
if torch.var(tile.mean(dim=1)) < 0.002:
    best_model = model_list[argmax(weights)]
    result = best_model(tile)  # single inference
else:
    # full multi-model spatial fusion
```

**Impact:** 50% smooth area → ~33% fewer inference passes (3→1 model on half the tiles).

#### Optimization 4: AuraSR Path Unified Post-Processing

Route AuraSR post-processing through same `frequency_enhance_pipeline` v4 with `extra_round` flag. Parameters adjusted for GAN-based output (less sharpening, more texture injection).

#### Efficiency Impact Summary

| Scenario | v7.2 Extreme | v7.3 Extreme | Improvement |
|----------|-------------|-------------|-------------|
| 512x512   | ~3-5s       | ~3-4.5s     | ~10%        |
| 4096x4096 | ~60-90s     | ~40-65s     | ~25-35%     |
| 4096+50% smooth | ~60-90s | ~35-55s | ~35-40% |
| Gaussian blur calls (double-pass) | 15 | 6 | -60% |

**Key insight:** Inference is 90%+ of cost. Only optimizations that reduce inference passes (smooth-tile skip, overlap fix) or reuse GPU results (pyramid precompute) matter. The spatial fusion overhead (clarity_map + softmax + weighted sum) is <0.1% of total compute — optimizing it would be meaningless.
