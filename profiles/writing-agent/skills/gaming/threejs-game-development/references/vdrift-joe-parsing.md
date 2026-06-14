# VDrift .joe 二进制3D模型格式解析

## 格式规范（从C++源码逆向）

VDrift使用`.joe`（JOEditor格式 v3）存储3D模型。文件扩展名`.joe`，二进制格式。

### 文件头部（16字节）
```
offset 0: magic[4] = "IDP2" (4字节)
offset 4: version[4] = uint32 little-endian (应为3)
offset 8: num_faces[4] = uint32 (三角面数量)
offset 12: num_frames[4] = uint32 (帧数量，静态模型=1)
```

### 每帧数据（按顺序）
```
1. Faces: num_faces × 18字节
   每个face = 9 × uint16 little-endian:
     vertexIndex[0..2]   — 顶点索引
     normalIndex[0..2]   — 法线索引
     textureIndex[0..2]  — UV索引

2. num_verts[4]  = uint32
3. num_texcoords[4] = uint32
4. num_normals[4] = uint32

5. Verts: num_verts × 12字节
   每个vert = 3 × float32 (x, y, z)

6. Normals: num_normals × 12字节
   每个normal = 3 × float32 (nx, ny, nz)

7. Texcoords: num_texcoords × 8字节
   每个texcoord = 2 × float32 (u, v)
```

### 唯一顶点去重（关键步骤）

VDrift源码使用 `unordered_map<Vert, uint>` 做顶点唯一化，其中 `Vert = (vertexIndex, texcoordIndex, normalIndex)`：

```python
vert_map = {}
unique_verts = []
unique_normals = []
unique_uvs = []
indices = []

for face in faces:
    for j in range(3):
        key = (face['verts'][j], face['texcoords'][j], face['normals'][j])
        if key not in vert_map:
            vert_map[key] = len(unique_verts)
            unique_verts.append(verts[face['verts'][j]])
            unique_normals.append(normals[face['normals'][j]])
            unique_uvs.append(uvs[face['texcoords'][j]])
        indices.append(vert_map[key])
```

### 坐标系统

VDrift使用 **Z-up** 坐标系（Z轴向上）。Three.js使用 **Y-up**。模型加载后需要旋转：
```javascript
mesh.rotation.x = -Math.PI / 2;
```

### 完整Python解析器

```python
import struct

def parse_joe_v3(filepath):
    with open(filepath, 'rb') as f:
        data = f.read()
    
    if data[0:4] != b'IDP2':
        return None
    
    num_faces = struct.unpack_from('<I', data, 8)[0]
    num_frames = struct.unpack_from('<I', data, 12)[0]
    
    offset = 16
    all_data = {'verts': [], 'normals': [], 'uvs': [], 'indices': []}
    
    for frame_idx in range(num_frames):
        # 读取faces
        faces = []
        for i in range(num_faces):
            off = offset + i * 18
            v = struct.unpack_from('<9H', data, off)
            faces.append({
                'verts': [v[0], v[1], v[2]],
                'normals': [v[3], v[4], v[5]],
                'texcoords': [v[6], v[7], v[8]]
            })
        offset += num_faces * 18
        
        nv = struct.unpack_from('<I', data, offset)[0]; offset += 4
        nt = struct.unpack_from('<I', data, offset)[0]; offset += 4
        nn = struct.unpack_from('<I', data, offset)[0]; offset += 4
        
        verts = [struct.unpack_from('<3f', data, offset + i*12) for i in range(nv)]
        offset += nv * 12
        normals = [struct.unpack_from('<3f', data, offset + i*12) for i in range(nn)]
        offset += nn * 12
        uvs = [struct.unpack_from('<2f', data, offset + i*8) for i in range(nt)]
        offset += nt * 8
        
        # 唯一化
        vmap, uverts, unorms, uuvs, idxs = {}, [], [], [], []
        for face in faces:
            for j in range(3):
                key = (face['verts'][j], face['texcoords'][j], face['normals'][j])
                if key not in vmap:
                    vmap[key] = len(uverts)
                    uverts.append(verts[face['verts'][j]])
                    unorms.append(normals[face['normals'][j]])
                    uuvs.append(uvs[face['texcoords'][j]] if face['texcoords'][j] < len(uvs) else (0,0))
                idxs.append(vmap[key])
        
        all_data['verts'].extend([v for vt in uverts for v in vt])
        all_data['normals'].extend([n for nm in unorms for n in nm])
        all_data['uvs'].extend([uv for uv in uuvs for uv in uv])
        all_data['indices'].extend(idxs)
    
    return all_data
```

## 导出为Three.js JSON格式

输出JSON应包含：
```json
{
    "name": "350Z",
    "verts": [x,y,z, x,y,z, ...],
    "normals": [nx,ny,nz, nx,ny,nz, ...],
    "uvs": [u,v, u,v, ...],
    "indices": [i1,i2,i3, i1,i2,i3, ...],
    "parts": {
        "body": {"vertOffset": 0, "vertCount": 4158, "triCount": 5524, "indexCount": 16572},
        "glass": {"vertOffset": 4158, "vertCount": 692, "triCount": 692, "indexCount": 2076},
        "interior": {"vertOffset": 4850, "vertCount": 2236, "triCount": 2236, "indexCount": 6708}
    },
    "numVerts": 7086,
    "numTris": 8452
}
```

`parts`字段是可选的，用于区分不同材质的部件。

## Three.js多部件渲染

```typescript
async function loadVDriftModel(modelId: string): Promise<void> {
    const response = await fetch(`dist/models/${modelId}.json`);
    const data = await response.json();
    
    const verts = new Float32Array(data.verts);
    const uvs = new Float32Array(data.uvs);
    const normals = new Float32Array(data.normals);
    
    if (data.parts) {
        for (const [partName, info] of Object.entries(data.parts)) {
            const geo = new THREE.BufferGeometry();
            let mat: THREE.Material;
            if (partName === 'glass') {
                mat = new THREE.MeshPhysicalMaterial({ transparent: true, opacity: 0.35, side: THREE.DoubleSide });
            } else if (partName === 'interior') {
                mat = new THREE.MeshStandardMaterial({ color: 0x333333, side: THREE.DoubleSide });
            } else {
                mat = new THREE.MeshPhysicalMaterial({ color: bodyColor, metalness, roughness });
            }
            const mesh = new THREE.Mesh(geo, mat);
            mesh.rotation.x = -Math.PI / 2;  // Z-up → Y-up
            group.add(mesh);
        }
    }
}
```

## 可用车型列表

| ID | 真实车型 | body面数 | glass面数 | interior面数 | 备注 |
|----|---------|---------|----------|------------|------|
| 350Z | 日产350Z (2003) | 5524 | 692 | 2236 | 完整 |
| 360 | 法拉利360 Modena | 7726 | 556 | 1729 | 完整 |
| ATT | 奥迪TT 3.2 | 1366 | 128 | 850 | 完整 |
| CO | Caterham 7 CSR | 8042 | 250 | 1511 | 完整 |
| CS | Corvette C6 | 4470 | 104 | — | 无内饰 |
| F1-02 | F1 2002 | 13394 | — | — | 仅车身 |
| LE | 勒芒原型车 | 8008 | 1028 | 3118 | 完整 |
| M3 | 宝马M3 E46 | 5752 | 50 | 2268 | 完整 |
| M7 | 迈凯伦F1 | 4200 | 186 | 562 | 完整 |
| SV | Saleen S7 | 4607 | 204 | 224 | 完整 |
| TC6 | 丰田Celica GT-Four | 14795 | 986 | 6373 | 最大 |
| TL2 | 丰田Supra 2JZ | 4916 | 92 | 610 | 完整 |
| XS | 宝马M3 GTR | 3875 | 108 | 474 | 完整 |

## VDrift资源来源

- 项目主页: https://sourceforge.net/projects/vdrift/
- 最新稳定版: v2014-10-20 (484MB完整源码包)
- 模型在源码包的 `data/` 目录下
- 官方源码格式定义: `src/graphics/model_joe03.cpp`
- 赛道格式: `.trk` (道路数据) + `.jpk` (编译物体包)
