# UltraUltimateUpscale v5 — Spandrel-Based Real Upscaling

## Session: 2026-05-20, Three-Generation Evolution

## The Problem: Random Weights

**Phenomenon:** After upscaling, resolution increases but NO new detail appears. The image is
just bigger with blurry/pixelated content.

**Root cause:** The model is running with **randomly initialized weights**, not real pretrained ones.
This happens when:
1. `SwinIRModel()` / `HATModel()` is created with `state_dict=None` (all random)
2. `load_state_dict(state_dict, strict=False)` silently drops mismatched layers
3. The custom architecture definition (e.g., dim=180) doesn't match the pretrained .pth

**Diagnosis:** Check load output for `size mismatch` warnings. Each mismatched layer means
random init for that layer:
```
[UUU] size mismatch for conv_first.weight:
  copying a param with shape torch.Size([180, 3, 3, 3]) from checkpoint,
  the shape in current model is torch.Size([64, 3, 3, 3]).
```

### Generation Comparison

| Generation | Approach | Detail Quality | Why |
|-----------|----------|---------------|-----|
| v1–v3 | GenericUpscaler (manual conv2d) | Poor | Hardcoded conv loops, <50% weight use |
| v4 | Real Architectures (SwinIR/HAT/RRDB classes) | Better but inconsistent | strict=False skips mismatched layers |
| **v5** | **Spandrel auto-loader** | **Real detail** | Auto-detects exact architecture from .pt file |

## v5 Architecture

```
input image (PIL)
  → model = load_model(path, device)        # Spandrel or native RRDB
  → upscale(upscale_image_v4(img, model))   # Real weight inference
  → enhance_pipeline(result, sharpness)      # FFT + USM + adaptive + CLAHE + de-ring
  → output (PIL)
```

### Spandrel Loader

```python
def load_model(path, device='cpu'):
    try:
        from spandrel import ModelLoader
        raw = torch.load(path, map_location='cpu', weights_only=True)
        sd = raw
        if isinstance(raw, dict):
            for k in ['params_ema', 'params', 'state_dict', 'model', 'net', 'state']:
                if k in raw and isinstance(raw[k], dict): sd = raw[k]; break
        model = ModelLoader().load_from_state_dict(sd)
        if hasattr(model, 'model'): model.model = model.model.to(device).eval()
        return model
    except ImportError:
        # Fallback: native RRDBNet
        from spandrel.architectures.RRDBNet import RRDBNet
        model = RRDBNet(nf=nf, nb=nb).to(device).eval()
        model.load_state_dict(cleaned, strict=False)
        return model
```

### Detail Enhancement Pipeline (Why it actually adds detail)

The pipeline doesn't just sharpen — it **recovers** detail through multiple complementary mechanisms:

1. **FFT Bandpass Enhancement** — Transforms image to frequency domain, amplifies mid/high frequencies, transforms back. This recovers spatial frequency content that AI upscalers often suppress.
2. **Unsharp Mask (USM)** — Classic photographic sharpening: extract high-frequency detail by subtracting Gaussian blur, amplify it, add back to original.
3. **Adaptive Detail Enhancement** — Computes edge map (gradient magnitude) + texture map (local standard deviation). Only enhances regions with actual detail. Flat areas (sky, skin) remain untouched.
4. **CLAHE** — Adaptive histogram equalization on the L channel only. Reveals textures hidden in low-contrast regions without changing color.
5. **De-ringing** — Detects Gibbs ringing artifacts (halos around edges from Transformer upscalers) via Laplacian. Blends ring regions with Gaussian-blurred version.

### User-Facing Parameters (All Chinese)

| Parameter | Type | Values | Effect |
|-----------|------|--------|--------|
| `放大倍率` | INT 1-8 | 4 | Factor to upscale |
| `增强强度` | FLOAT 0-3 | 1.0 | Master intensity control |
| `增强模式` | dropdown | 极致FFT+USM+CLAHE / 高质量USM自适应 / 快速仅锐化 / 不增强 | Pipeline selection |
| `降噪` | INT 0-3 | 0 | Median filter passes after enhancement |
| `手动选模型` | model list | [AUTO] or specific .pth | Override model selection |

### Content Analyzer Edge Detection Fix

```python
# SAFE pattern for np.diff broadcast:
diff_h = np.abs(np.diff(arr, axis=1))  # shape (h, w-1)
diff_w = np.abs(np.diff(arr, axis=0))  # shape (h-1, w)
min_s = min(diff_h.shape[0], diff_w.shape[0],
            diff_h.shape[1], diff_w.shape[1])
edges = diff_h[:min_s,:min_s] + diff_w[:min_s,:min_s]
```

### NODE_CLASS_MAPPINGS Prefix Consistency

**CRITICAL:** When renaming classes, the NODE_CLASS_MAPPINGS dict and the class definition
must use IDENTICAL names. A common mistake is:
```python
# v4 code had class FU_ImageUpscale_v4 but registration said:
NODE_CLASS_MAPPINGS = {"UUU_ImageUpscale_v4": UUU_ImageUpscale_v4}  # UUU_ doesn't exist!
```
ComfyUI reports `Import OK` (because the file parses) but no nodes appear in the menu
(because the dict references undefined names).

**Fix:** Keep class names and registration names synchronized during refactoring.

### CATEGORY Discoverability

ComfyUI users find nodes by:
1. Searching in the "Add Node" dialog
2. Browsing the category menu

**Rule:** CATEGORY must contain at least one easily-searchable keyword. `/` creates sub-menus.
```python
# BAD: CATEGORY = "FinalUltraFusion v4"   → user searches "Ultra" → NOT FOUND
# GOOD: CATEGORY = "UltraUltimateUpscale"  → user searches "Ultra" → FOUND
# BETTER: CATEGORY = "UltraUltimateUpscale" with DISPLAY_NAME containing the keyword
```

### v5 Export Checklist

- [ ] Spandrel installed (`pip install spandrel`)
- [ ] No bare `except:` — always `except Exception:`
- [ ] No `eval()` — only `model.eval()` (check via regex)
- [ ] `if seed is not None:` — not `if seed:` (seed=0 is valid)
- [ ] Real .pth weights in `ComfyUI/models/upscale_models/` (auto-downloaded)
- [ ] CATEGORY includes searchable keywords
- [ ] All visible strings in Chinese
- [ ] Parameter names don't contain `(` `)` `=` (can't be Python kwargs)
- [ ] NODE_CLASS_MAPPINGS names match class definitions exactly
