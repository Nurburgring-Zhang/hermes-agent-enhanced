# Ensemble Model Dilution & v3 Spatial Adaptive Fusion

## Session Context
- Date: 2026-05-24
- Node: UltraUltimateUpscale v7 (D:\ComfyUI\custom_nodes\UltraUltimateUpscale\)
- Problem: "极致(5算法Ensemble v2)" produced worse output than "高质量(自适应3算法)"
- Files modified: `__init__.py` (backup: `__init__.py.bak`)

## Available Models

From `/mnt/d/ComfyUI/models/upscale_models/`:

| File | Size | Architecture | Node Classification |
|------|------|-------------|-------------------|
| 4xNomos8kSCHAT-L.pth | 317MB | HAT-L (SCHAT) | "hat" |
| 4xNomos2_hq_drct-l.pth | 232MB | DRCT-L | "detail" |
| 4x-UltraSharpV2.safetensors | 134MB | DAT-like | "sharp" |
| 4x-UltraSharp.pth | 64MB | SwinIR-like | "sharp" |
| 4x_RealisticRescaler_100000_G.pth | 128MB | ESRGAN variant | "realistic" |
| RealESRGAN_x4plus.pth | 64MB | RRDB | "general" |
| x1_ITF_SkinDiffDetail_Lite_v1.pth | 20MB | Face-specific | "face" |

## Root Cause Analysis

### Cause 1: Top-5 Model Selection Dilution

Original logic: `max_m = 5 if 极致 else 3`

With 6 available models, top-3 picks: HAT(317MB) + DRCT(232MB) + UltraSharpV2(134MB) = **683MB total, good ratio**
Top-5 adds: RealESRGAN(64MB) + RealisticRescaler(128MB) = **192MB of weaker models** diluting ~30% of the blend

### Cause 2: Weighted Average (v2) is Spatially Blind

`ensemble_upscale_v2()` does:
```python
result = sum(model_output * global_weight for each model)
```

Same weights for texture, edges, and smooth regions. HAT's texture reconstruction gets diluted everywhere.

### Cause 3: Tiled Inference Artifact Stacking

`ensemble_upscale_v2_tiled()`: Each model does independent tiled inference → 5 sets of tile boundary artifacts → superimposed in final average.

## Fixes Applied

### Fix 1: Cap at top-3 for Both Modes
```python
max_m = 3  # both 极致 and 高质量 use top-3
```

### Fix 2: Replace v2 Weighted Average with v3 Spatial Adaptive Fusion

New functions added to `__init__.py`:

- `_local_clarity_map()` — per-pixel clarity heatmap using Laplacian variance
- `ensemble_spatial_fuse()` — softmax-based spatial selection across models
- `ensemble_upscale_v3_spatial()` — full-image spatial ensemble (no tiling)
- `ensemble_upscale_v3_tiled()` — per-tile spatial ensemble (fuse per tile, not per model)

Key parameters:
- `temperature=4.0` — controls softmax sharpness
- Mix ratio: `60% local clarity + 40% global weights`

### Fix 3: Extreme Mode Gets Double-Round Post-Processing

```python
if is_extreme_mode:
    # Round 1: 1.3x sharpness, 1.5x texture
    result_pil = frequency_enhance_pipeline(result_pil, sharpness=1.3x, texture=1.5x)
    # Round 2: frequency boost only (no re-sharpen)
    result_pil = t3_frequency_boost(result_pil, strength=texture * 0.6)
```

### Fix 4: Larger Overlap for Tiled Fused Mode
```python
overlap = max(overlap * 2, 64)  # double the overlap in extreme tiled mode
```

## Test Plan

1. Load same source image in both modes with identical settings (detail=0.3, texture=0.2)
2. Compare: "极致" should have visibly sharper textures, better edge resolution, comparable smooth regions
3. Check specific areas: hair/skin texture, building edges, sky gradients
4. Test both large images (>2K, triggers tiled mode) and small images (<1K, full inference)

## Key Code Snippet (v3 Fusion Core)

```python
def ensemble_spatial_fuse(results_list, model_archs, base_weights):
    # Align to max dimensions
    # Compute clarity map per model
    clarity_maps = [_local_clarity_map(r) for r in aligned]
    all_clarity = torch.stack(clarity_maps, dim=0)  # [n,1,H,W]
    
    # Softmax with temperature
    advantage = F.softmax(all_clarity * temperature, dim=0)
    
    # Blend with global weights for stability
    w_tensor = torch.tensor(base_weights).view(n, 1, 1, 1)
    advantage = advantage * 0.6 + w_tensor * 0.4
    advantage = advantage / advantage.sum(dim=0, keepdim=True)
    
    # Spatial adaptive blend
    stacked = torch.stack(aligned, dim=0)
    result = (stacked * advantage).sum(dim=0)
    return result.clamp(0, 1)
```
