# IDP2 Format v13 Discovery (Session 2026-06-01)

## The Core Bug That Took 5+ Parse Attempts To Fix

### v8-v12 Bug: `vmap[key] = len(out_verts)` used float count, not vertex count

```python
# WRONG (v8-v12):
vmap[key] = len(out_verts)  # out_verts has 3 floats per vertex
# Result: indices are [0, 3, 6, 9, ...] with step 3
# max_idx = 20919 but only 6974 unique indices, nv = 6974
# → 67% of indices OOB → garbage geometry

# CORRECT (v13):
vmap[key] = len(out_verts) // 3  # divide by 3 = vertex count
# Result: indices are [0, 1, 2, 3, ...] continuous
# max_idx = 6973 with nv = 6974
# → 0% OOB → clean geometry
```

**Verification** (run after every conversion):
```python
d = json.load(open('dist/models/SV.json'))
nv = d['numVerts']
mi = max(d['indices'])
print(f'OOB = {mi >= nv}')  # Must be False
```

## The Third uint32 Myth

Early parsers read 3 uint32s after faces. The 3rd uint32 is actually the **first float of the normal data** being interpreted as LE uint32:

```
[faces] [nverts(uint32)] [ntex(uint32)] [FIRST_NORMAL_FLOAT 4B mistaken as 3rd uint32] [normals...] [tex...]
```

**Fix**: Only read 2 uint32s. Compute num_normals from max face normal index + 1.

## Coordinate System — The Three-Way Confusion

| Source | Claimed | Reality |
|--------|---------|---------|
| C++ struct | `float vertex[3]` | No semantics |
| File data | x=[-1,1] y=[-2.2,2.2] z=[-1,1] | y=前后(4.4m), z=上下(2m) |
| Three.js | Y-up: x=右, y=上, z=前 | Need y⇔z swap |

**Correct transform**: `new(x,y,z) = (raw.x, raw.z, -raw.y)`

## File Layout (Final, Verified By 13 Models)

```
Offset 0:   magic "IDP2" (4B LE)     → 0x32504449
Offset 4:   version (4B LE)           → 3
Offset 8:   num_faces (4B LE)
Offset 12:  num_frames (4B LE)        → 1 for body.joe
Offset 16:  flags (4B LE)
Offset 20:  Face data: num_faces × 18 bytes
            Each face: 9 × uint16 LE = (v0,v1,v2, n0,n1,n2, t0,t1,t2)
After faces: nverts (4B LE), ntex (4B LE)
             Vertices: nverts × 12B = (3 × float LE: x,y,z)
             Normals:  ntex × 12B (num_normals ≈ ntex)
             TexCoords: ntex × 8B  (2 × float LE: u,v)
```

## OOB Face Index Handling

VDrift body.joe files commonly have face vertexIndex values exceeding nverts. 
- XS: 3875 faces, 1540 nverts, 1095 OOB faces skipped (28%)
- This is NORMAL — VDrift engine has assert checks that catch this
- Solution: **skip OOB faces** (don't try to create dummy vertices)

