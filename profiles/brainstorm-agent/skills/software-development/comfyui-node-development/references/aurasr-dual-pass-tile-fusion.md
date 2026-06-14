# AuraSR Dual-Pass Checkerboard Tile Fusion

Reference architecture from [fal-ai/aura-sr](https://github.com/fal-ai/aura-sr) for reducing seam artifacts in tiled super-resolution.

## Core Concept

Instead of a single tiled forward pass with overlap weighting (sin/cosine), AuraSR does **two passes with a spatial offset** and averages them using **checkerboard weights**.

```
Pass 1: tile from (0,0) with tile_size=256
  → result1 = merge_tiles(tiles1)

Pass 2: tile from (offset, offset) with offset=tile_size//2
  → first pad image by offset on all sides (reflect mode)
  → tile from padded image
  → result2 = merge_tiles(tiles2)
  → crop result2 back to original size (remove offset×4 pixels)

Final = result1 × W1 + result2_interior × W2
```

## Why Checkerboard Weights

Checkerboard weighting naturally handles the 4-corner overlapping pattern created by dual-pass tiling:

```
W1 (checkerboard):
  ┌───┬───┬───┐
  │1.0│0.5│1.0│  ← tile boundaries at half-weight
  ├───┼───┼───┤
  │0.5│0.0│0.5│  ← center weights shifted
  └───┴───┴───┘

W2 = 1.0 - W1 (inverted checkerboard)
```

This means each pixel gets contribution from both passes, with weights that naturally blend across tile boundaries.

## Implementation Pattern (Python/PyTorch)

```python
def create_checkerboard_weights(tile_size):
    """Create checkerboard weight tile"""
    weight = torch.ones(1, tile_size, tile_size)
    half = tile_size // 2
    # Top-left and bottom-right = 0.5
    weight[:, :half, :half] = 0.5
    weight[:, half:, half:] = 0.5
    return weight

def create_offset_weights(weight_tile, shape):
    """Create repeating weights matching image shape"""
    h, w = shape
    wt = weight_tile.repeat(
        (h + weight_tile.shape[0] - 1) // weight_tile.shape[0],
        (w + weight_tile.shape[1] - 1) // weight_tile.shape[1]
    )[:h, :w]
    return wt

def repeat_weights(weight_tile, shape):
    """Inverted weights for second pass"""
    wt = create_offset_weights(weight_tile, shape)
    return 1.0 - wt  # invert
```

## AuraSR Tile Functions (Reference)

```python
def tile_image(image, chunk_size=256):
    """Split image into non-overlapping tiles"""
    c, h, w = image.shape
    tiles = []
    h_chunks = math.ceil(h / chunk_size)
    w_chunks = math.ceil(w / chunk_size)
    for i in range(h_chunks):
        for j in range(w_chunks):
            tile = image[
                :,
                i * chunk_size : min((i + 1) * chunk_size, h),
                j * chunk_size : min((j + 1) * chunk_size, w),
            ]
            # Pad tile to chunk_size if needed
            pad_h = chunk_size - tile.shape[1]
            pad_w = chunk_size - tile.shape[2]
            if pad_h > 0 or pad_w > 0:
                tile = F.pad(tile, (0, pad_w, 0, pad_h), mode="reflect")
            tiles.append(tile)
    return tiles, h_chunks, w_chunks

def merge_tiles(tiles, h_chunks, w_chunks, output_size):
    """Place upscaled tiles into output canvas"""
    c = tiles[0].shape[0]
    merged = torch.zeros(c, output_size, output_size)
    for idx, tile in enumerate(tiles):
        i = idx // w_chunks
        j = idx % w_chunks
        h_start = i * chunk_size  # chunk_size * scale_factor
        w_start = j * chunk_size
        tile_h, tile_w = tile.shape[1:]
        merged[:, h_start:h_start+tile_h, w_start:w_start+tile_w] = tile
    return merged
```

## Differences from Sin/Cosine Weighted Fusion

| Aspect | Sin/Cosine Weighted (UUU) | AuraSR Dual-Pass Checkerboard |
|--------|--------------------------|-------------------------------|
| Number of passes | 1 | 2 |
| Overlap required | Yes (stride < tile_size) | No (exact tile, offset by half) |
| Weight function | sin((k+1)/(ov+1)×π/2) | Checkerboard binary (0.5/1.0) |
| Computational cost | 1× per tile | 2× (doubled) |
| Seam quality | Good with large overlap | Excellent, no visible seams |
| Implementation complexity | Higher (weight calc + normalization) | Lower (simple weight tiles) |
| Edge handling | Tapered sin weights | Hard weight boundary at edges |

## When to Use Which

- **Upscale the full image in one shot**: Use AuraSR dual-pass if you can afford 2× compute and want seam-free results
- **Tile-by-tile streaming (memory constrained)**: Use sin/cosine overlap because you can't hold the offset pass in memory
- **Very large images (16K+)**: AuraSR dual-pass can be combined with sin/cosine overlap for best results at higher memory cost
