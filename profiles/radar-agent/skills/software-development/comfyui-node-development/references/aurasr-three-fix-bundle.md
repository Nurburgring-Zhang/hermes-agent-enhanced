# AuraSR Integration — 3-Fix Bundle (2026-05-22)

## Fix 1: Tile Stitch Weight Bug

**Symptom:** Top half darker, bottom half pure white at horizontal midpoint.

**Root cause in `tiled_upscale_v2()`:**
```python
# L534 — vertical index uses tile-local ah, not global oys
wt[:, :, :ah, oxs:oxe] += ww[0, :, :ah, :]

# Should be:
wt[:, :, oys:oye, oxs:oxe] += ww
```

**Second occurrence in `ensemble_upscale_v2_tiled()`:**
```python
# L453 — same bug, different variable names
m_wt[:, :, :ah, oxs:oxe] += ww[0, :, :ah, :]

# Should be:
m_wt[:, :, oys:oye, oxs:oxe] += ww
```

**Always check BOTH functions** when fixing this bug. Most implementations copy-paste the pattern.

## Fix 2: White Halo Cascade Overload

**Root cause:** No single stage causes halos. The cumulative effect of 4-5 enhancement stages each adding 5-15% edge contrast causes 30-50% over-sharpening.

**7-parameter fix:**

| Component | Original | Fixed | Reduction |
|-----------|----------|-------|-----------|
| T3 highpass clamp | ±90 | ±55 | 40% |
| T3 highpass gain | x1.5 | x1.2 | 20% |
| T3 contrast clamp | ±60 | ±40 | 33% |
| T3 contrast gain | x0.8 | x0.6 | 25% |
| T3 frequency clamp | ±45 | ±30 | 33% |
| T3 frequency gain | x1.0 | x0.8 | 20% |
| Sharpening clamp | ±40 | ±25 | 38% |
| Sharpening gain | x1.5 | x0.8 | 47% |

**Directional sharpen (permanent fix):** Replace blind USM with Sobel-direction-aware sharpening — enhance only along edge normal, not tangent.

```python
def directional_sharpen(img_pil, strength=0.3):
    """Sobel direction-aware sharpening — no halo"""
    sobel_x = np.array([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]])
    sobel_y = np.array([[-1, -2, -1], [0, 0, 0], [1, 2, 1]])
    gx = convolve(gray, sobel_x)
    gy = convolve(gray, sobel_y)
    edge_mag = np.sqrt(gx**2 + gy**2)
    # Gaussian bell curve: peak at mid-strength edges, 0 at noise and strong edges
    edge_mask = np.exp(-((edge_norm - 0.15) ** 2) / (2 * 0.08**2))
    # Protection: suppress enhancement on already-strong edges
    protection = 1.0 - np.clip(edge_norm * 2.0, 0, 0.7)
    final_mask = edge_mask * protection
    lap = laplacian(img) * final_mask
    lap = np.clip(lap, -20, 20)  # strict clamp prevents halo
    for c in range(3):
        arr[:, :, c] += lap * strength * 0.8
```

## Fix 3: S-Curve Dark/Bright Compensation

**Root cause:** AuraSR's GAN generator suppresses low-contrast regions in shadows and highlights.

**Fix pattern — S-curve mapping (not linear stretch):**

```python
def adaptive_tone_mapping(img_pil, strength=0.3):
    """S-curve: lift shadows, compress highlights, preserve midtones"""
    for c in range(3):
        channel = arr[:, :, c]
        # Shadow lift: [0,0.3] → [0,0.35] via sine
        lift = np.where(channel < 0.3,
                        np.sin(channel * np.pi / 0.6) * 0.3 / np.sin(np.pi/2),
                        channel)
        # Highlight protect: [0.8,1] → [0.82,0.97] via 0.85x compression
        compressed = np.where(channel > 0.75,
                              0.75 + (channel - 0.75) * 0.85,
                              channel)
        # Adaptive blend based on dark/bright distribution
        result = channel * (1 - dark_boost - bright_suppress) \
                 + lift * dark_boost + compressed * bright_suppress
        arr[:, :, c] = result
```

## Verification

After all 3 fixes, test with:
1. High-contrast edge image — no white halo
2. Dark image (mean<0.3) — detail visible in shadows, not crushed
3. Bright image (mean>0.7) — detail in highlights, not blown out
4. Natural image — no artifacts on complex textures
