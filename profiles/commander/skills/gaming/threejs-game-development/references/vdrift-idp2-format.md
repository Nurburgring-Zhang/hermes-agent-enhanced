# VDrift IDP2 Model Format (Binary)

## Header (20 bytes)
| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0 | 4 | magic | "IDP2" |
| 4 | 4 | version | 3 |
| 8 | 4 | num_verts | Number of vertices in file |
| 12 | 4 | num_tris | Number of triangles |
| 16 | 4 | flags | Format flags |

## Vertex Data (32 bytes per vertex)
After 20B header, `num_verts` vertices of 32 bytes each:
- position: float32 × 3 = 12B
- normal: float32 × 3 = 12B  
- texcoord: float32 × 2 = 8B

## JOE Face Data (18 bytes per face)
After vertex data, sequential faces. Each face: 9 × uint16 = 18B:
```
v0, v1, v2, n0, n1, n2, t0, t1, t2
```
- v0/v1/v2: LOCAL vertex indices (0,1,2 for face N's 3 vertices)
- n0/n1/n2: GLOBAL normal indices (point into normal array)
- t0/t1/t2: GLOBAL texcoord indices

## Face → Global Vertex Mapping
For face `fi`:
```
global_vi = fi * 3 + local_idx  (local_idx = 0,1,2)
norm_ni = [n0,n1,n2][local_idx]  (from face data, GLOBAL)
tex_ti = [t0,t1,t2][local_idx]   (from face data, GLOBAL)
```

## Dedup Key
```
unique_key = (global_vi, norm_ni, tex_ti)
```

## NaN Protection
JOE Face normal/tex indices CAN exceed the actual count of normals/texcoords.
Always guard:
```python
v = verts[global_vi] if global_vi < len(verts) else (0,0,0)
if v[0] != v[0] or v[1] != v[1] or v[2] != v[2]: v = (0,0,0)
n = norms[ni] if ni < len(norms) else (0,0,0)
if n[0] != n[0] or n[1] != n[1] or n[2] != n[2]: n = (0,0,1)
```

## File Locations
- Source JOE files: `/tmp/vdrift/data/cars/{MODEL_ID}/body.joe`, `glass.joe`, `interior.joe`
- Output JSON: `dist/models/{MODEL_ID}.json`
- Converter: `scripts/convert_v8.py`

## 13 Car Models
350Z, 360, ATT, CO, CS, F1-02, LE, M3, M7, SV, TC6, TL2, XS
