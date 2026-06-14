# UltraUltimateUpscale v7.0 — Multi-Model Ensemble Upscale + Content-Adaptive Pipeline (2026-05-20)

**Updated to v7.0:** See also `references/upscale-content-adaptive-v7-20260520.md` for the complete content analysis, frequency-aware enhancement, and quality estimation patterns.

See also: `references/upscale-content-adaptive-v7-20260520.md` for the complete content analysis, frequency-aware enhancement, and quality estimation patterns.

## Architecture

```
IMAGE → model_selector → Spandrel auto-load → ensemble_inference → natural_enhance → IMAGE
                                                      │
                                                      ├── HAT (detail/texture, 0.5 weight)
                                                      ├── DRCT (structural clarity, 0.3 weight)
                                                      └── ESRGAN (sharpness, 0.2 weight)
```

## Model Auto-Detection

Spandrel's `ModelLoader().load_from_state_dict(sd)` auto-identifies architecture from weight keys.
Since ImageModelDescriptor has no `.model` setter, use `.to(device)`:

```python
from spandrel import ModelLoader
raw = torch.load(path, map_location='cpu', weights_only=True)
sd = raw
# Unwrap common wrappers
for k in ['params_ema', 'params', 'state_dict', 'model']:
    if k in raw and isinstance(raw[k], dict):
        sd = raw[k]; break
model = ModelLoader().load_from_state_dict(sd)
model = model.to(device).eval()  # ✅ NOT model.model = model.model.to(device)
```

## Scale Auto-Detection

```python
def _detect_scale(model_path):
    """Detect upscale factor from filename or weight shape"""
    name = os.path.splitext(os.path.basename(model_path))[0]
    # Filename patterns
    m = re.search(r'[xX](\d+)(?:_|[._\s]|$)', name)
    if m: return int(m.group(1))
    m = re.search(r'(\d+)[xX](?:_|[._\s]|$)', name)
    if m: return int(m.group(1))
    # Weight-based heuristic
    weights = torch.load(model_path, map_location='cpu', weights_only=True)
    sd = next((v for k,v in weights.items() if isinstance(v, dict) and 'weight' in str(type(v))), weights)
    for key in sd:
        if 'weight' in key and sd[key].dim() >= 4:
            shape = sd[key].shape
            if shape[1] == 3: return shape[0] // 3  # RGB → RGB channels
            if shape[0] == 3: return shape[1] // 3
            return int(round((shape[0] / 3) ** 0.5))  # fallback
    return 4  # default
```

## Multi-Model Ensemble Inference

```python
def _upscale_with_models(self, image_tensor, models, weights, device):
    """Run multiple models and ensemble via weighted sum"""
    results = []
    total_weight = sum(weights)
    for model, weight in zip(models, weights):
        with torch.inference_mode():
            output = model(image_tensor)
            results.append(output * (weight / total_weight))
    # Weighted sum ensemble
    return torch.stack(results).sum(dim=0).clamp(0, 1)
```

**Key requirement:** All models must output the SAME spatial dimensions. Use target scale (max of all models) and resize mismatches.

## Natural Enhancement Pipeline (replaces brute-force USM)

```python
def _enhance_natural(self, tensor, strength=0.15, texture=0.1):
    """Apply gentle, localized enhancement that preserves texture"""
    # 1. Gentle Unsharp Mask (USM) with local std mask
    blur = gaussian_blur(tensor, kernel_size=3, sigma=1.0)
    detail = tensor - blur
    local_std = torch.std(tensor, dim=(2,3), keepdim=True)  # spatial variation
    mask = torch.sigmoid((local_std - 0.05) * 20)  # edge regions → 1, flat → 0
    enhanced = tensor + detail * strength * mask

    # 2. Mild texture boost
    high_pass = tensor - gaussian_blur(tensor, kernel_size=5, sigma=2.0)
    enhanced = enhanced + high_pass * texture * mask

    # 3. Gentle denoise (only in flat regions)
    denoise_strength = (1 - mask) * 0.1
    enhanced = gaussian_blur(enhanced, kernel_size=3, sigma=denoise_strength)
    
    return enhanced.clamp(0, 1)
```

## Quality Mode Settings

| Mode | Detail Strength | Texture | Denoise | Use Case |
|------|----------------|---------|---------|----------|
| 高质量(默认) | 0.15 | 0.1 | auto | General |
| 极致细节 | 0.30 | 0.2 | minimal | Architecture, text |
| 自然写真 | 0.08 | 0.05 | stronger | Portraits |
| 高速预览 | 0.0 | 0.0 | none | Quick test (single model only) |

## ComfyUI IS_CHANGED for Upscale Nodes

For nodes that upscale to a fixed dimension (same input size → same output), add IS_CHANGED:

```python
@classmethod
def IS_CHANGED(cls, **kwargs):
    return time.time()
```

Without this, ComfyUI caches results by input hash → same image input always returns the same upscaled output → user sees no improvement after parameter changes.

## Common Failures

### weights_only=True with .safetensors
PyTorch 2.6+ defaults to `weights_only=True`. Some .safetensors files require `weights_only=False`:
```python
# ✅ Works for all .pth and .safetensors
torch.load(path, map_location='cpu', weights_only=False)
```

But for trusted-only envs, use `weights_only=True` with safe fallback:
```python
try:
    raw = torch.load(path, map_location='cpu', weights_only=True)
except Exception:
    raw = torch.load(path, map_location='cpu', weights_only=False)
```

### Spandrel warns but still works
Spandrel uses `warnings.warn("v2.0…")` for deprecated args. These are non-fatal — the model loads and infers correctly.

### Ensemble dimension mismatch
Two models with different output scales (e.g. x2 vs x4) cannot be naively blended. Solution: compute all outputs at native scale, then resize to match the largest before blending.
