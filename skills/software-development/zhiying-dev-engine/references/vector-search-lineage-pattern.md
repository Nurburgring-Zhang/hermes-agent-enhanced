# 向量搜索+数据血缘双引擎模式（2026-06-15实战）

## 向量搜索（core/vector_search.py）
- 基于CLIP embedding的语义检索
- 余弦相似度排序
- 支持类型过滤(min_score/filter_type)
- 文本 → CLIP embedding
- 图片 → CLIP embedding via PIL
- fallback: 512维随机向量（开发模式）

### API
```
POST /api/v2/search/vector   — 语义搜索(query/filter_type/top_k)
POST /api/v2/search/index    — 索引资产(asset_id/embedding/metadata)
```

## 数据血缘追踪（core/data_lineage.py）
- 记录数据行级变换（source→operation→target）
- 上游追踪（get_upstream）
- 下游追踪（get_downstream）
- 递归血缘图（get_lineage_graph，depth参数）
- 以asset_id为节点的DAG

### API
```
POST /api/v2/lineage/record          — 记录变换(source/target/operation)
GET  /api/v2/lineage/{asset_id}       — 完整血缘图(含depth)
GET  /api/v2/lineage/{asset_id}/upstream   — 上游来源
GET  /api/v2/lineage/{asset_id}/downstream — 下游去向
```
