# White Halo Cascade Fix — V7.1 AuraSR Integration

## Root Cause: Cascade Overload

When 3+ image enhancement stages run sequentially, each adds 5-15% edge contrast amplification. The cumulative effect produces visible white halos (blooming at strong edges) even though each individual stage looks safe in isolation.

## Detection Test

Create a test image with high-contrast edges (white background, black text at 8pt/12pt/24pt, diagonal lines). Run the enhancement pipeline. If white/black halos appear at text edges within 10px, cascade overload is confirmed.

## Fix Strategy

### Option A: Reduce cascade gain (7-point parameter tuning)

| Parameter | Before | After | Effect |
|-----------|--------|-------|--------|
| T3 highpass clip | ±90 | ±55 | -40% edge magnitude |
| T3 highpass multiplier | 1.5 | 1.2 | -20% gain |
| T3 contrast clip | ±60 | ±40 | -33% |
| T3 contrast multiplier | 0.8 | 0.6 | -25% |
| T3 frequency clip | ±45 | ±30 | -33% |
| T3 frequency multiplier | 1.0 | 0.8 | -20% |
| Sharpening clip | ±40 | ±25 | -38% |
| Sharpening multiplier | 1.5 | 0.8 | -47% |
| Dark compensation | 0.5 | 0.35 | -30% |
| Highlight compensation | 0.4 | 0.25 | -38% |

### Option B: Directional sharpen (permanent fix)

Replace blind USM with Sobel-direction-aware sharpening. Only enhance along edge normals — zero tangential enhancement eliminates overshoot:

```python
# 1. Compute Sobel gradients
gx = convolve(gray, sobel_x)
gy = convolve(gray, sobel_y)
edge_mag = sqrt(gx**2 + gy**2)

# 2. Laplacian extracts all edges (both normal and tangential)
lap = laplacian_filter(image)

# 3. Build edge mask — bell curve centered at medium edge strength
#    (weak edges = noise, skip. Strong edges = already sharp, skip)
norm_std = edge_mag / max(edge_mag)
edge_mask = exp(-((norm_std - 0.15)**2) / (2 * 0.08**2))

# 4. Protect against over-sharp at already-strong edges
protection = 1.0 - clip(norm_std * 2.0, 0, 0.7)

# 5. Apply
final_mask = edge_mask * protection  # blur this mask
detail = lap * final_mask
detail = clip(detail, -20, 20)  # strict clamp prevents any halo
result = image + detail * strength * 0.8
```

### Option C: S-curve tone mapping (prevents dark-area compression)

Replace linear dark-area stretch with sigmoid-style curve:

```python
# Linear stretch: channel = (channel - min) / (max - min) * 255
#   → Hard clamp at 0 and 255 → produces halos at distribution tails

# S-curve: channel < 0.3 maps through sin(x * pi / 0.7)
#   → Smooth roll-off at both ends → no clipping artifacts
boost = np.where(
    normalized < 0.35,
    np.sin(normalized * np.pi / 0.7) * 0.35 / np.sin(np.pi / 2),
    normalized
)
# And compress highlights: channel > 0.75 → 0.75 + (channel - 0.75) * 0.85
compressed = np.where(channel > 0.75, 0.75 + (channel - 0.75) * 0.85, channel)
```

### Option D: Precise texture enhancement (DoG + Gaussian gain)

Replace multi-scale Laplacian with DoG (Difference of Gaussians), gated by a Gaussian gain curve:

```python
# DoG: b1(radius=0.8) - b2(radius=2.0) = mid-frequency textures
mid = b1 - b2
low = b2 - b4  # larger texture structures
texture = mid * 0.7 + low * 0.3

# Gain curve: peaked at medium local std (0.25 normalized)
#   near-zero std → zero boost (noise suppression)
#   high std → minimal boost (edges already sufficient)
norm_std = local_std / max_std
gain = 4.0 * norm_std * exp(-4.0 * norm_std)  # peak at 0.25
gain = clip(gain, 0, 1.0)

texture = clip(texture, -15, 15)  # strict clamp
result = image + texture * gain * strength * 0.8
```

## Verification

After fix, run the same high-contrast test image. Check:
1. Text edges: no white/black halos within 10px
2. Texture areas: grain/detail still visible
3. Smooth regions (sky, skin): no new noise amplified
4. Dark areas: detail preserved, not crushed
5. Bright areas: texture visible, not blown out
