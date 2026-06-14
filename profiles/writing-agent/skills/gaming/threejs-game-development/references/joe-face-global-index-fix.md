# JOE Face 全局索引解析 (v9 修复)

## 背景
VDrift 二进制 IDP2 格式的 JOE Face 部分，每个面 9 个 uint16：
- `v0, v1, v2` — **全局顶点索引**（指向整个 verts 数组）
- `n0, n1, n2` — 全局法线索引
- `t0, t1, t2` — 全局纹理索引

## v8 错误（导致模型"一团黑"）
v8 解析器错误地假设 vertex index 是 local 的（每面 3 个连续顶点），代码：
```python
# 错误：面fi的第j个顶点 = fi*3 + j
global_vi = fi * 3 + j
vi = [v0, v1, v2][j]     # 这里的vi被忽略，用的是fi*3+j
key = (global_vi, ni, ti)
```

后果：
- 顶点索引完全错位，face 指向错误的 vertex data
- vmap 去重后顶点数**膨胀**（去重后反而更大，因为每个face的local索引指向不同顶点）
- 如 XS 模型：正确=573v，错误=2343v（4倍膨胀）
- 所有 13 个模型的 JSON 都错了

## v9 正确解析
```python
for j in range(3):
    vi = [v0, v1, v2][j]   # 直接使用JOE Face中的全局索引
    ni = [n0, n1, n2][j]
    ti = [t0, t1, t2][j]
    key = (vi, ni, ti)      # 去重键直接用全局索引
```

### 关键验证
原始 JOE Face 始终存在 `v0 == v1 == v2`（三角形纹理坐标相同的情况），但如果 `v0` 是全局索引，它们**可以不相同**。在 v8 错误解析中，这些值被丢弃了。

### 执行验证
转换后检查：`python3 -c "import json; d=json.load(open('dist/models/XS.json')); print('verts:', d['numVerts'], 'tris:', d['numTris'], 'indices max:', max(d['indices'])); assert max(d['indices']) < d['numVerts']*3"`

## 模型对比（v8 vs v9）

| 模型 | v8 verts | v9 verts (正确) | 三角形 |
|------|----------|-----------------|--------|
| XS | 2343 | **573** ✅ | 781 |
| F1-02 | 11622 | **1950** ✅ | 3874 |
| TC6 | 17637 | **3389** ✅ | 5879 |
| 350Z | 6267 | **1541** ✅ | 2089 |
