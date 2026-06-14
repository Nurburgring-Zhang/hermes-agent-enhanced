# Spandrel Integration Debug Notes (2026-05-20)

## Installation

```bash
pip install spandrel --break-system-packages
```

This also upgrades torch and related CUDA packages. 42 architectures supported.

## Three Ways to Load a Model (in order)

### 1. Spandrel (best)
```python
from spandrel import ModelLoader
raw = torch.load(path, map_location='cpu', weights_only=True)
sd = raw
# Extract innermost state_dict
for k in ['params_ema', 'params', 'state_dict', 'model', 'net', 'state']:
    if k in raw and isinstance(raw[k], dict): sd = raw[k]; break
model = ModelLoader().load_from_state_dict(sd)
# CRITICAL: ImageModelDescriptor has no .model setter!
model = model.to(device).eval()     # ✅ works
model.model = model.model.to(device)  # ❌ AttributeError: no setter
```

### 2. Direct RRDBNet (works for Real-ESRGAN weights)
```python
from spandrel.architectures.RRDBNet import RRDBNet
# Auto-detect architecture dimensions
nf = sd['conv_first.weight'].shape[0]  # number of filters
nb = sum(1 for k in sd if 'body.' in k and '.weight' in k and 'convs.' not in k)
model = RRDBNet(nf=nf, nb=nb)
missing, unexpected = model.load_state_dict(cleaned, strict=False)
# Validate: if >30% keys missing, weights are random — reject
if len(missing) > len(cleaned) * 0.3:
    return None  # don't use random weights
```

### 3. Custom architecture (avoid unless you trained the model)
Defining your own SwinIR/HAT/RRDBNet classes and loading external .pth files with `strict=False` is a **trap** — most weights stay random.

## Quality Degradation Root Cause Chain

```
User: "no detail added, just larger"
1. Spandrel not installed → falls back to RRDBNet
2. RRDB loads HAT weight (conv_first.weight shape matches, but internal keys differ)
3. strict=False → most weights silently skipped
4. Model runs but produces random-weight output
5. Smaller image replaced by larger blurry mess
6. Post-processing (FFT+USM+CLAHE+dering) applied on top of garbage → further degrades
```

## The .tmp Download Bug

```python
# BUG: interrupted download leaves .tmp file, scan_models ignores .tmp
urllib.request.urlretrieve(url, tmp)  # → file.pth.tmp
os.rename(tmp, fp)  # never reached → .pth never created, model not found

# FIX: validate before rename
tmp = fp + '.tmp'
urllib.request.urlretrieve(m['url'], tmp)
if os.path.getsize(tmp) < 1000:
    os.remove(tmp)
    continue  # signal failure
os.rename(tmp, fp)
```

## ComfyUI IS_CHANGED Mechanism

PromptLibraryNode has no changing inputs (folder path stays the same). Without `IS_CHANGED`, ComfyUI caches the first execution result and returns it forever.

```python
@classmethod
def IS_CHANGED(cls, **kwargs):
    return time.time()  # always different → never cache
```

## Compat Layer for Old Workflow Values

When switching from dropdown to STRING input, old workflows have saved values like `'Random'` instead of `'随机抽取'`. ComfyUI's validator rejects these before the function runs.

**Fix:** Add value mapping at the top of the processing function:
```python
if 读取模式 not in ["随机抽取","顺序循环","洗牌遍历","权重随机"]:
    mode_map = {"Random":"随机抽取","Sequential":"顺序循环","Shuffle":"洗牌遍历","Weighted":"权重随机"}
    读取模式 = mode_map.get(读取模式, "随机抽取")
```
