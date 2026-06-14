# VDrift IDP2 Binary Format — Correct Parser (v12, 2026-06-01)

## Format Specification

Based on analysis of 13 VDrift car body.joe files and cross-reference with VDrift C++ source (`model_joe03.cpp`).

### Header (20 bytes, Little-Endian)
```
offset 0: uint32 magic = 0x32504449 ("IDP2" as LE)
offset 4: uint32 version = 3
offset 8: uint32 num_faces
offset 12: uint32 num_frames (always 1 for car models)
offset 16: uint32 flags (not used)
```

### Data per Frame (repeat num_frames times)

#### 1. JoeFace data (num_faces × 18 bytes)
Each face = 9 × uint16 (LE):
```
uint16 vertexIndex[3]   — GLOBAL vertex indices into verts array
uint16 normalIndex[3]   — GLOBAL normal indices into norms array
uint16 textureIndex[3]  — GLOBAL texcoord indices into uvs array
```

#### 2. Counters (ONLY 2 uint32, NOT 3!)
```
uint32 num_verts   ← ACTUAL vertex count (≈ texture count)
uint32 num_texcoords
```
**CRITICAL:** There is NO third uint32. The next 4 bytes after these 2 are the FIRST FLOAT of normal data, which if read as uint32 produces a garbage value (~3.2 billion).

#### 3. Vertex data (num_verts × 12 bytes = 3 × float32 LE)
```
float x  — left/right (negative = left)
float y  — ??? (see coordinate discussion below)
float z  — ??? 
```
After reading, `pos += num_verts * 12`.

#### 4. Normal data (remaining mostly × 12 bytes)
Normals are read until remaining bytes can't form a full 12-byte triplet.
The normal count is determined by `(remaining_bytes) / 12`.
Normal values are in range [-1, 1] (unit vectors).

#### 5. Texcoord data (remaining after normals × 8 bytes)
If remaining is 0, texture coords are optional — default to (0, 0).

### num_verts vs Actual Vertex Count

**CRITICAL FINDING:** The JOE Face vertex indices (0 to max_vi) often exceed num_verts. The actual usable vertex count is `num_texcoords` (second uint32), NOT `num_verts`.

Example (XS body.joe):
```
num_verts = 1540    ← WRONG/truncated
num_texcoords = 2462 ← ACTUAL vertex count (also = max_vi + 1)
face vertexIndex range: 0-2461
```

**Fix:** Always use `num_texcoords` as the vertex count:
```python
actual_verts = num_texcoords  # second uint32
```

### Coordinate System

This is the most debated part of the format. Based on vertex range analysis:

**VDrift file format (stored order):** `(x, ???, ???)`

Analysis of XS model:
```
Vertex range: x=[-2.153, 1.937], y=[-0.571, 0.318], z=[-0.890, 0.888]
face vertexIndex range: 0-2461 (num_verts=1540, actual=2462)
```

If using `num_texcoords` (2462) as vertex count:
```
x=[-1.000, 1.000], y=[-1.000, 1.000], z=[-1.000, 1.000]
```
This means the vertices are normalized to [-1, 1] in ALL axes — a unit cube.

The real-world car dimensions are obtained by VDrift's MODEL_SCALE (1.0 in code) and per-mesh transforms. 

**Three.js Conversion** — apply AFTER dedup:
```typescript
// rawVerts from JSON: (x_leftRight, y_unknown, z_unknown)
verts[i] = rawVerts[i];         // x unchanged
verts[i+1] = rawVerts[i+2];     // y ← raw z
verts[i+2] = -rawVerts[i+1];    // z ← -raw y
```

This transformation was validated through 3 iterations in the 2026-06-01 session and produces visually correct car meshes.

### Normals Handling

The third "uint32" in the header is actually the first float of the normal data. When read as uint32 LE, it gives a garbage value (~3.2 billion).

**Detect and fix:**
```python
if num_normals > 100000 or num_normals <= 0:
    num_normals = num_texcoords  # fallback
```

Better yet: DON'T read a third uint32 at all. Just read 2, then read vertices, then detect normals from remaining bytes.

### Parser Failure Modes

| Symptom | Root Cause | Fix |
|---------|-----------|-----|
| Vertex range [-1,1] in all axes | num_verts truncated; used first uint32 instead of second | Use `num_texcoords` as vertex count |
| Model has 3D data but renders flat/dot | Read 3 uint32, third consumed first normal float → vert data read shifted | Read only 2 uint32 |
| "model is a vertical line" (bbox y=2.3, x=0, z=0) | Vertex conversion formula was `(x,z,-y)` but raw data was already `(x,y,z)` | Changed to `(x,raw_y,raw_z)` with no swap |
| indices_max > numVerts | `num_verts` from first uint32 is smaller than actual vertex count | Use num_texcoords as actual vertex count |
| Nan vertices in output | JOE Face normal/tex indices out of bounds → reading wrong floats | Bounds check + NaN protection in dedup |
| `nnorm` = ~3.2 billion | Third uint32 is actually first normal float | Only read 2 uint32 |
| Glass/interior merge corrupts indices | After cleanup, indices need remapping | Re-map through vertMap for merged data too |

### dedup Implementation (correct)

```python
vmap = {}
for fi, face in enumerate(faces):
    v0,v1,v2,n0,n1,n2,t0,t1,t2 = face
    # Bounds check before processing
    if v0 >= num_verts or v1 >= num_verts or v2 >= num_verts:
        continue
    if n0 >= num_normals or n1 >= num_normals or n2 >= num_normals:
        continue
    for j in range(3):
        vi = [v0,v1,v2][j]
        ni = [n0,n1,n2][j]
        ti = [t0,t1,t2][j]
        key = (vi, ni, ti)
        if key not in vmap:
            vmap[key] = len(out_verts)
            out_verts.extend(verts[vi])
            out_norms.extend(norms[ni])
            t = uvs[ti] if ti < len(uvs) else (0,0)
            out_uvs.extend([t[0], 1.0 - t[1]])
        out_indices.append(vmap[key])
```

### Convert Script History

| Version | Type | Major Change | Result |
|---------|------|-------------|--------|
| v8 | Python | First correct JOE Face global indexing | Wrong vertex count, model flat |
| v9 | Python | Added NaN protection + cleanup | Too few tris, indices OOB |
| v10 | Python | Based on C++ ReadData with 3 uint32 | nnorm=3.2B, many file OOB reads |
| v11 | Python | OBJ export for debugging | Confirmed nnorm issue |
| v12 | Python | 2 uint32 only, auto-detect normals, bounds check | ALL 13 cars converted, correct tris count |
