# Ultra Upscale Tile Stitch Weight Bug — "Half White" Pattern

## Symptom

- Image upscaled, but **top half is darker** and **bottom half is pure white** (or vice versa)
- A horizontal dividing line separates normal output from white region
- Overall detail is less than expected

## Root Cause

The **weight accumulation tensor `wt`** in the tiled upscale loop has an **incorrect vertical index**.

### The Bug

```python
# BUG: writes wt to wrong slice — always starts at row 0 instead of oys
wt[:, :, :ah, oxs:oxe] += ww[0, :, :ah, :]

# wt accumulates at rows [0, ah) instead of [oys, oye)
# Second tile's weights overwrite first tile's at the overlap region
# Unweighted pixels → near-zero divisor → pure white
```

### The Fix

```python
# FIX: use the correct output-space coordinates
wt[:, :, oys:oye, oxs:oxe] += ww
```

## Where This Bug Appears

This pattern appears in **every tiled upscale function** that manually accumulates weight maps. The three locations to check:

1. **tiled_upscale_v2()** — single-model tiled upscale
2. **ensemble_upscale_v2_tiled()** — multi-model ensemble tiled upscale
3. Any function with pattern: `m_out[:, :, oys:oye, oxs:oxe] += oc * ww` followed by `m_wt[:, :, ..., ...] += ...`

## Why It Happens

The tiled upscale pattern:
```
for each tile (ys, ye) in input space:
    model(tile) → out_tile               # model upscales by scale factor
    oys = ys * scale, oye = ye * scale   # output space coordinates
    oc = out_tile[:, :, :ah, :aw]        # crop to valid region
    
    # Build weight mask ww (1D sine blend at edges)
    ww = ones(ah, aw)
    # apply sine falloff at edges of ww
    
    # ACCUMULATE: add weighted tile to output
    out[:, :, oys:oye, oxs:oxe] += oc * ww
    
    # BUG HERE: must use same oys:oye, oxs:oxe!
    wt[:, :, :ah, oxs:oxe] += ww      # WRONG: uses :ah instead of oys:oye
                                       # ah = ah (local), oys = ys*scale (global)
```

The confusion is between **local tile size** (`ah`) and **global output position** (`oys`). For the first tile (ys=0), `oys=0` and `:ah` happens to be correct. For all subsequent tiles (ys>0), `:ah` always writes to the top of the weight map, corrupting previously accumulated weights.

## Diagnosis Script

```python
# Check if wt accumulation has the bug
grep -n 'wt.*\[:.*:.*:.*ah.*\]' __init__.py
# Look for pattern: wt[:, :, :ah, ...] or m_wt[:, :, :ah, ...]

# Expected: wt[:, :, oys:oye, ...]
# Bug:      wt[:, :, :ah, ...]
```

## Prevention When Writing Tiled Upscale

1. **Copy-paste symmetry rule:** Every `out[...] += oc * ww` must be followed by `wt[...] += ww` using the **exact same slice indices**.
2. **Never use local variable `ah`/`aw` in the weight accumulation** — these are local tile sizes, not global output positions.
3. **Use `oys:oye` and `oxs:oxe` consistently** — these are the global output-space coordinates computed from input-space `ys:ye` and `xs:xe`.

## Related: Detail Loss in Tiled Inference

Even with correct stitching, tile-based upscale loses detail at tile boundaries because:
- Each tile is processed independently — the model has no context across boundaries
- The sine-weight blending smooths the transition, which also smooths detail

**Mitigations:**
- Increase `overlap` from 48 to 128 (25% of tile_size)
- Post-process with gentle sharpen (0.3 strength)
- Multi-scale texture enhancement (3-level Laplacian pyramid)
