# VDrift 3D Model Coordinate System Extraction

## How to Determine Coordinate Axes
VDrift `.joe` file format uses Z-up. To determine exact axis mapping from a model JSON:

1. Read vertex data from the JSON file's `verts` array: `[x0, y0, z0, x1, y1, z1, ...]`
2. Compute min/max for each axis:
```python
min_x, max_x = min(verts[0::3]), max(verts[0::3])
min_y, max_y = min(verts[1::3]), max(verts[1::3])
min_z, max_z = min(verts[2::3]), max(verts[2::3])
```
3. Determine which axis is car length (largest range) — that's the forward axis
4. Determine which axis is height (smallest at top is ground) — that's the up axis
5. Find the "front" end: search for vertices at the extreme of the length axis
   - Check x-width at both ends: **narrower end = front** (nose), **wider end = rear** (bumper)
   - Car length ~3.5-4.5m, width ~1.7-2.0m, height ~1.0-1.4m

## ATT Model (Audi TT) Reference
```
原始坐标范围:
  X: -0.91 ~ 0.91 (宽 1.82m)  → 左右轴 ✓
  Y: -1.97 ~ 1.98 (长 3.95m)  → 前后轴 ✓ (Y+ = 车头端, narrower: -0.33~0.33)
  Z: -0.52 ~ 0.66 (高 1.18m)  → 上下轴 ✓

车轮位置 (z≈0.05-0.15, 地面附近):
  前轮 (y≈1.89): x=[-0.70, 0.70], 轮距1.40m
  后轮 (y≈-1.97): x=[-0.72, 0.72], 轮距1.44m
  轴距: 1.89 - (-1.97) = 3.86m
```

## Conversion to Three.js Y-up
**Preferred method: Group rotation, NOT vertex transform**
```typescript
bodyGroup.rotation.x = -Math.PI / 2;  // Z-up → Y-up (z→y, y→-z)
bodyGroup.rotation.y = Math.PI;        // Flip Y+ front → Z+ front
```
This maps: `original(x, y, z) → transformed(-x, z, y)`
- No data copying needed
- Normals/UVs preserved automatically
- Children (wheels, etc.) in the same coordinate space

## Parts with Missing indexOffset
VDrift JSON export often omits `indexOffset` in parts. Calculate from cumulative triCount:
```
indexOffset_partN = sum(indexCount for part_0..part_N-1)
```
Where `indexCount = triCount * 3` if not explicitly provided.
