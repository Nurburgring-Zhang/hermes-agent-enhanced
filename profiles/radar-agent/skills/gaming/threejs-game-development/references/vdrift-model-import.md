# VDrift Model Import Pipeline

## JOE03 Binary Format — Complete Specification

Parsed from VDrift C++ source (`model_joe03.cpp`).

### Header (16 bytes)
```
offset 0: uint32 magic = 'IDP2' (0x32504449)
offset 4: uint32 version = 3
offset 8: uint32 num_faces  ← NOTE: NOT num_verts! This is triangle count
offset 12: uint32 num_frames (almost always 1)
```

### Per-frame data (AFTER header, in this exact byte order):
1. **faces[num_faces]** — each face = 18 bytes (9 × uint16 little-endian)
   - vertexIndex[3]: indices into verts array
   - normalIndex[3]: indices into normals array  
   - textureIndex[3]: indices into texcoords array

2. **num_verts: uint32** — count of vertices
3. **num_texcoords: uint32** — count of UVs
4. **num_normals: uint32** — count of normals

5. **verts[num_verts]** — each = 3 × float32 (x, y, z) = 12 bytes
6. **normals[num_normals]** — each = 3 × float32 = 12 bytes  
7. **texcoords[num_texcoords]** — each = 2 × float32 (u, v) = 8 bytes

### Python Parser (validated on 13 VDrift models)
```python
import struct, json

def parse_joe_v3(filepath):
    with open(filepath, 'rb') as f:
        data = f.read()
    if data[0:4] != b'IDP2':
        return None
    
    num_faces = struct.unpack_from('<I', data, 8)[0]
    num_frames = struct.unpack_from('<I', data, 12)[0]
    offset = 16
    
    # Only process first frame (VDrift uses single-frame models)
    frame = 0
    faces_raw = data[offset:offset + num_faces * 18]
    offset += num_faces * 18
    
    faces = []
    for i in range(num_faces):
        v = struct.unpack_from('<9H', faces_raw, i * 18)
        faces.append({
            'verts': [v[0], v[1], v[2]],
            'normals': [v[3], v[4], v[5]], 
            'texcoords': [v[6], v[7], v[8]]
        })
    
    nv = struct.unpack_from('<I', data, offset)[0]; offset += 4
    nt = struct.unpack_from('<I', data, offset)[0]; offset += 4
    nn = struct.unpack_from('<I', data, offset)[0]; offset += 4
    
    verts = [struct.unpack_from('<3f', data, offset+i*12) for i in range(nv)]; offset += nv*12
    normals = [struct.unpack_from('<3f', data, offset+i*12) for i in range(nn)]; offset += nn*12
    uvs = [struct.unpack_from('<2f', data, offset+i*8) for i in range(nt)]; offset += nt*8
    
    # Unique vertex deduplication (CRITICAL)
    vert_map = {}
    uverts, unorms, uuvs = [], [], []
    indices = []
    
    for face in faces:
        for j in range(3):
            key = (face['verts'][j], face['texcoords'][j], face['normals'][j])
            if key not in vert_map:
                vert_map[key] = len(uverts)
                uverts.append(verts[face['verts'][j]])
                unorms.append(normals[face['normals'][j]])
                uuvs.append(uvs[face['texcoords'][j]] if face['texcoords'][j] < len(uvs) else (0,0))
            indices.append(vert_map[key])
    
    return {
        'verts': [v for vt in uverts for v in vt],
        'normals': [n for nm in unorms for n in nm],
        'uvs': [uv for uv in uuvs for uv in uv],
        'indices': indices,
        'numVerts': len(uverts),
        'numTris': len(indices) // 3,
    }
```

## Multi-Part Export (body + glass + interior)

Each VDrift car has separate `.joe` files for body, glass, and interior. Export as a single JSON with a `parts` map:

```python
merged = {
    'name': car_name,
    'verts': [], 'normals': [], 'uvs': [], 'indices': [],
    'parts': {},
    'numVerts': 0, 'numTris': 0,
}
vert_offset = 0

for part_name in ['body', 'glass', 'interior']:
    result = parse_joe_v3(f'{car_path}/{part_name}.joe')
    if not result: continue
    
    merged['verts'].extend(result['verts'])
    merged['normals'].extend(result['normals'])
    merged['uvs'].extend(result['uvs'])
    merged['indices'].extend([i + vert_offset for i in result['indices']])
    merged['parts'][part_name] = {
        'vertOffset': vert_offset,
        'vertCount': result['numVerts'],
        'triCount': result['numTris'],
        'indexCount': result['numTris'] * 3,
    }
    # NOTE: No 'indexOffset' field! The Three.js loader must compute
    # indexOffset by accumulating previous parts' indexCount values.
    vert_offset += result['numVerts']

merged['numVerts'] = vert_offset
merged['numTris'] = len(merged['indices']) // 3
```

**CRITICAL PITFALL — Missing `indexOffset` causes invisible meshes**: The JSON export does NOT include an `indexOffset` field in the parts. If the Three.js loader does `info.indexOffset` and gets `undefined`, then `carData.indices.slice(undefined, ...)` returns an empty array — the mesh has NO faces, and the car body is invisible.

**Fix in Three.js loader**: When `indexOffset` is missing, compute it by summing previous parts' indexCount:
```typescript
let iStart = 0;
if (typeof info.indexOffset !== 'undefined') {
    iStart = info.indexOffset;
} else {
    for (const [prevName, prevInfo] of Object.entries(carData.parts)) {
        if (prevName === partName) break;
        const pi = prevInfo as any;
        iStart += pi.indexCount || pi.triCount * 3;
    }
}
```

**Alternatively**, add `indexOffset` to the Python export:
```python
index_offset = 0
for part_name in ['body', 'glass', 'interior']:
    # ... parse ...
    merged['parts'][part_name] = {
        'vertOffset': vert_offset,
        'vertCount': result['numVerts'],
        'triCount': result['numTris'],
        'indexCount': result['numTris'] * 3,
        'indexOffset': index_offset,  # ← ADD THIS
    }
    vert_offset += result['numVerts']
    index_offset += result['numTris'] * 3
```

## Z-up to Y-up Conversion — CRITICAL: Understand VDrift Axis Orientation

**VDrift coordinate system** (VERIFIED against ATT model: x=±0.91, y=-1.97~1.98, z=-0.52~0.66):
- **x = 左右** (left/right, car width ~1.82m on ATT)
- **y = 前后** (front/back, car length ~3.95m on ATT)
- **z = 上下** (up/down, car height ~1.18m on ATT)

**CRITICAL — Which end is front?** In VDrift, **y+ (positive Y) is the FRONT of the car**:
- Y+ end (y>1.9): x range -0.33~0.33 (narrow — front nose)
- Y- end (y<-1.9): x range -0.47~0.47 (wider — rear bumper)

THIS IS CRITICAL — the conversion formula directly determines whether the car faces toward or away from the camera.

### Two valid approaches (DO NOT use both):

#### Approach A: Vertex-level conversion (PREFERRED — cleaner for wheels)
Transform coordinates BEFORE creating BufferGeometry. This puts everything in Y-up coordinates directly:
```python
# (x, y, z) → (x, z, -y)
#  x=左右 stays same
#  y(新) ← 原z (上下 → 新Y-up上下)
#  z(新) ← 原-y (前后 → 新Z前后, 取反让车头朝Z-)
for i in range(0, len(verts), 3):
    verts[i] = verts[i]       # x unchanged
    verts[i+1] = verts[i+2]   # y ← z (up)
    verts[i+2] = -verts[i+1]  # z ← -y (front goes to Z-)

# Same for normals
for i in range(0, len(normals), 3):
    normals[i] = normals[i]
    normals[i+1] = normals[i+2]
    normals[i+2] = -normals[i+1]
```

After this conversion, car front faces **Z- direction**. Three.js default camera looks from Z+ toward Z-, so the car faces the camera.

**CRITICAL — Movement code must match**: When the car front faces Z-, forward movement is:
```typescript
let moveZ = -Math.cos(playerAngle) * playerSpeed * delta;  // Z- is forward
// (Standard formula is +cos — negative because car faces Z-)
```

And car rotation at race start:
```typescript
this.playerCar.rotation.y = Math.atan2(tangent.x, -tangent.z);  // Z- front
this.aiCars[i].rotation.y = Math.atan2(tangent2.x, -tangent2.z);  // Z- front
```

**If you forget these direction flips, the car will drive BACKWARDS** (front faces wrong way, movement seems to work but visually it's tail-first).

#### Approach B: Group rotation (wheel alignment is harder)
Add a rotation to the body's parent group ONLY (leave wheels unrotated):
```typescript
const bodyGroup = new THREE.Group();
bodyGroup.rotation.x = -Math.PI / 2;  // Z-up → Y-up
group.add(bodyGroup);
// body meshes → bodyGroup
// wheels → group (NOT bodyGroup) — they need separate coordinate tracking
```

**Pitfall with Approach B**: After rotation, wheel positions must be in the rotated coordinate space. When bodyGroup has `rotation.x = -PI/2`, the wheel's Y becomes model-original Z (height), and wheel's Z becomes model-original -Y (front/back). If wheel positions are set in unrotated Y-up coordinates (y=0.2, z=±1.2), they'll be in the wrong spot. Approach A (vertex-level conversion) is simpler for wheel placement because all geometry shares the same coordinate space.

## Three.js Loading Pattern

```typescript
private vdriftModelCache: Map<string, any> = new Map();

private async loadVdriftModel(modelId: string): Promise<void> {
    if (this.vdriftModelCache.has(modelId)) return;
    const response = await fetch(`dist/models/${modelId}.json`);
    this.vdriftModelCache.set(modelId, await response.json());
}

private waitForModel(modelId: string): Promise<boolean> {
    return new Promise(resolve => {
        if (this.vdriftModelCache.has(modelId)) { resolve(true); return; }
        const check = setInterval(() => {
            if (this.vdriftModelCache.has(modelId)) { clearInterval(check); resolve(true); }
        }, 100);
        setTimeout(() => { clearInterval(check); resolve(false); }, 5000);
    });
}

private buildVDriftCar(group, carData, bodyColor, accentColor): void {
    const bodyMat = new THREE.MeshPhysicalMaterial({ color: bodyColor });
    const glassMat = new THREE.MeshPhysicalMaterial({ 
        color: 0x88ccff, transparent: true, opacity: 0.35, side: THREE.DoubleSide 
    });
    const interiorMat = new THREE.MeshStandardMaterial({ 
        color: 0x333333, side: THREE.DoubleSide 
    });
    
    // Vertex-level Z-up to Y-up conversion
    const rawVerts = new Float32Array(carData.verts);
    const verts = new Float32Array(rawVerts.length);
    for (let i = 0; i < rawVerts.length; i += 3) {
        verts[i] = rawVerts[i];
        verts[i+1] = rawVerts[i+2];
        verts[i+2] = -rawVerts[i+1];
    }
    
    for (const [partName, info] of Object.entries(carData.parts)) {
        const geo = new THREE.BufferGeometry();
        const mesh = new THREE.Mesh(geo, 
            partName === 'glass' ? glassMat : 
            partName === 'interior' ? interiorMat : bodyMat);
        group.add(mesh);
    }
}
```

## Available Models (13 cars, all validated)

| ID | Real Car | Tris | Parts | HP | TopSpeed | 0-100 | Weight |
|----|----------|------|-------|----|----------|-------|--------|
| 350Z | Nissan 350Z | 8452 | b+g+i | 287 | 250 | 5.7 | 1400 |
| 360 | Ferrari 360 Modena | 10011 | b+g+i | 400 | 295 | 4.5 | 1390 |
| ATT | Audi TT 3.2 | 2344 | b+g+i | 250 | 250 | 5.7 | 1380 |
| CO | Caterham 7 CSR | 9803 | b+g+i | 200 | 230 | 4.8 | 560 |
| CS | Corvette C6 | 4574 | b+g | 430 | 305 | 4.2 | 1470 |
| F1-02 | F1 2002 | 13394 | body | 900 | 350 | 2.5 | 600 |
| LE | Le Mans Prototype | 12154 | b+g+i | 650 | 340 | 2.8 | 900 |
| M3 | BMW M3 E46 | 8070 | b+g+i | 343 | 250 | 5.2 | 1550 |
| M7 | McLaren F1 | 4948 | b+g+i | 627 | 320 | 3.2 | 1140 |
| SV | Saleen S7 | 5035 | b+g+i | 550 | 330 | 3.3 | 1300 |
| TC6 | Toyota Celica GT-Four | 22154 | b+g+i | 252 | 245 | 5.8 | 1400 |
| TL2 | Toyota Supra 2JZ | 5618 | b+g+i | 320 | 260 | 5.0 | 1550 |
| XS | BMW M3 GTR | 4457 | b+g+i | 450 | 280 | 4.5 | 1350 |

## Key Pitfalls

1. **num_faces in header is triangle count, NOT vertex count** — reading it as verts will cause index overflow
2. **Unique vertex deduplication is CRITICAL** — without it, a 5524-vert body produces 16572+ vertices
3. **Z-up to Y-up must happen before normals computation** — call geo.computeVertexNormals() AFTER coordinate transform
4. **Wheels must NOT be in the rotated bodyGroup** — add them to the parent group so they stay Y-up aligned
5. **JSON files are 1-5MB each** — use async fetch + waitForModel; don't bundle into webpack
