# Tile Stitch Weight Bug Debugging Pattern

## Symptom Recognition

When debugging image upscaling and you see:

| Symptom | Likely Cause |
|---------|-------------|
| **Top half looks upscaled but dark. Bottom half is pure white.** | Weight accumulation index bug (this pattern) |
| Horizontal dividing line at 50% | Each tile's weight written to wrong vertical slice |
| Overall detail poor even in working region | Tile stitch overlap too small (< 15% of tile_size) |
| Seams visible at tile boundaries | Weight blending not applied or wrong blending kernel |

## The Root Cause Pattern

This is a **copy-paste error** that happens when writing tiled inference loops.

### Normal pattern (what you expect):
```python
for each tile at (ys, ye) in input space:
    oys = int(ys * scale), oye = int(ye * scale)    # output space coordinates
    oc = model(tile)                                 # upscaled tile
    ww = build_weight_mask(ah, aw)                   # blending weights
    
    out[:, :, oys:oye, oxs:oxe] += oc * ww           # accumulate pixel data
    wt[:, :, oys:oye, oxs:oxe] += ww                 # accumulate weights
```

### Bug pattern (what breaks):
```python
    out[:, :, oys:oye, oxs:oxe] += oc * ww           # CORRECT — uses oys:oye
    wt[:, :, :ah, oxs:oxe] += ww[0, :, :ah, :]      # BUG — uses :ah (local tile size) instead of oys:oye

    # :ah is correct for tile 0 (ys=0 → oys=0)
    # :ah is WRONG for tile 1+ (ys>0 → oys>0) — writes to wrong row!
```

### Why First Tile Works But Second Breaks

| Tile | Input (ys:ye) | Output (oys:oye) | Bug writes to | Effect |
|------|--------------|-----------------|---------------|--------|
| 1st | 0:512 | 0:2048 | `wt[:, :, 0:2048, ...]` | **Correct** (oys=0, :ah=0:2048 — same!) |
| 2nd | 464:976 | 1856:3904 | `wt[:, :, 0:2048, ...]` | **Wrong!** (overwrites tile 1's weights) |
| 3rd | 928:1440 | 3712:5760 | `wt[:, :, 0:2048, ...]` | **Wrong!** (overwrites more) |

The weight map `wt` never accumulates at the correct rows. Half the pixels have wt=0 → division by near-zero → pure white.

## Quick Diagnosis

```bash
# Find the bug in any file
grep -n 'wt\[.*:.*:.*:ah' *.py
# or
grep -n 'wt\[.*:.*:.*:.*ah.*\].*+\=' *.py

# Expected output: nothing
# Bug output: wt[:, :, :ah, oxs:oxe] += ...
```

## Fix Pattern

```python
# Change this:
wt[:, :, :ah, oxs:oxe] += ww[0, :, :ah, :]

# To this:
wt[:, :, oys:oye, oxs:oxe] += ww
```

Always verify that `wt` uses the **same slice indices** as `out` on the previous line.

## Prevention Checklist for New Tiled Upscale Code

- [ ] `out[...]` and `wt[...]` use **identical slice indices**
- [ ] Both use `oys:oye` and `oxs:oxe` (not `:ah` or `:aw`)
- [ ] Weight mask `ww` is accumulated without being sliced (unless intentional)
- [ ] Test with a small image (256×256) first — the horizontal line is very visible
- [ ] Test with tile_size set to image_size/2 — should produce no artifacts
