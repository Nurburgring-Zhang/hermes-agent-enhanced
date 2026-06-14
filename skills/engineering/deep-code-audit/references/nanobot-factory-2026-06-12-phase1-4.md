# Nanobot Factory 2026-06-12 — Phase 1-4 新功能构建案例

## 背景
之前完成了全项目143K行深度审核+7个P0假实现修复。本次Phase 1-4目标是补齐商用级功能差距。

## Phase 1: ML Backend + 主动学习
**对标**: Label Studio ML Backend / Scale AI Model Foundry

### 核心模块: core/ml_backend.py (7.5KB)
- 模型注册表: MLModel(id/name/type/endpoint/api_key/status/accuracy)
- 枚举: MLModelStatus(6态) + MLModelType(5种: object_detection/classification/segmentation/caption/tag)
- 预标注: predict() 支持HTTP调用(如果endpoint配置) + 本地fallback(CLIP/BLIP via ai_models)
- 主动学习: get_active_learning_samples() 基于置信度排序(越低越需要标注)
- 准确率更新: update_model_accuracy() 基于人工审核反馈

### API端点 (6个，注册在server.py)
| 方法 | 路径 | 功能 |
|------|------|------|
| GET | /api/v2/ml/models | 列出模型(可按type过滤) |
| POST | /api/v2/ml/models | 注册模型 |
| DELETE | /api/v2/ml/models/{id} | 注销模型 |
| POST | /api/v2/ml/models/{id}/predict | 预标注 |
| GET | /api/v2/ml/active-learning | 主动学习采样 |
| POST | /api/v2/ml/models/{id}/accuracy | 更新准确率 |

### 设计经验
- 用classmethods而非实例——跨请求共享状态
- 本地模型用lazy import（openai/aiohttp/whisper等）
- active_learning的策略可以扩展（当前只有uncertainty，可加random/diversity）

## Phase 2: 多模态标注
**对标**: CVAT / Label Studio

### 核心模块: core/multimodal_annotation.py
- VideoAnnotation: extract_frames(video_path, interval=30) + propagate_bbox(frames, start, bbox)
- AudioAnnotation: transcribe(audio_path, via whisper) + get_waveform(audio_path, samples=200)
- MultimodalAnnotationManager: create/get/update/delete 四件套
- 枚举: AnnotationType(6种) + MediaType(4种)

### API端点 (7个，由独立annotation_api.py路由模块注册)
| 方法 | 路径 | 功能 |
|------|------|------|
| POST | /api/v2/annotations/video/extract-frames | 视频帧提取 |
| POST | /api/v2/annotations/audio/transcribe | 音频转写 |
| POST | /api/v2/annotations/audio/waveform | 波形提取 |
| POST | /api/v2/annotations/create | 创建标注 |
| GET | /api/v2/annotations/{media_id} | 获取标注列表 |
| PUT | /api/v2/annotations/{ann_id} | 更新标注 |
| DELETE | /api/v2/annotations/{ann_id} | 删除标注 |

### 设计经验
- 创建独立 annotation_api.py 作为APIRouter，用 app.include_router 注册
- opencv-python和whisper作为可选依赖(try/except包装)
- 标注数据用dict格式而不是强类型——灵活但需要前端schema验证

## Phase 3: RBAC多租户
**对标**: Scale AI / Labelbox

### 核心模块: core/rbac.py (5KB)
- 角色层级: ADMIN → ORG_OWNER → ORG_ADMIN → PROJECT_MANAGER → ANNOTATOR → REVIEWER → VIEWER
- 权限映射: 每个角色对应一组Permission(CREATE/READ/UPDATE/DELETE/ADMIN)
- 组织: Organization(org_id/name/owner/members)
- 项目: Project(project_id/name/org_id/members)
- RBACManager: 组织CRUD + 项目CRUD + 成员管理 + 权限检查

### API端点 (8个)
| 方法 | 路径 |
|------|------|
| POST/GET | /api/v2/rbac/orgs |
| POST | /api/v2/rbac/orgs/{org_id}/members |
| GET | /api/v2/rbac/orgs/{org_id}/members |
| POST/GET | /api/v2/rbac/projects |
| POST | /api/v2/rbac/projects/{project_id}/members |
| POST | /api/v2/rbac/check |

### 设计经验
- admin用户始终有权限（hardcoded bypass）
- 权限检查链: 项目级→组织级（短路评估）
- 用classmethod而非db持久化——生产环境需迁移到SQLite/PostgreSQL

## Phase 4: 数据集版本管理(git-like)
**对标**: HuggingFace Datasets

### 核心模块: core/dataset_version.py (7.7KB)
- DatasetVersion: commit/diff/branch/merge/tag/log/rollback/checkout
- DatasetVersionManager: 管理多个数据集的版本
- 版本存储: 内存dict(可序列化为JSON)
- diff: added/removed/modified计数+前5条示例
- merge: 支持"ours"和"union"两种策略

### API端点 (11个)
| 方法 | 路径 |
|------|------|
| POST | /api/v2/datasets/{id}/init |
| GET | /api/v2/datasets |
| POST | /api/v2/datasets/{id}/rows |
| POST | /api/v2/datasets/{id}/commit |
| GET | /api/v2/datasets/{id}/log |
| POST | /api/v2/datasets/{id}/checkout |
| GET | /api/v2/datasets/{id}/diff |
| POST | /api/v2/datasets/{id}/branch |
| POST | /api/v2/datasets/{id}/merge |
| POST | /api/v2/datasets/{id}/tag |
| POST | /api/v2/datasets/{id}/rollback |

## 通用构建模式

### 4个核心模块的共同设计模式
1. **全classmethod** — 无需实例化，跨请求共享状态
2. **内存存储** — 快速原型，生产级需迁移到SQLite/PostgreSQL持久化
3. **try/except Optional依赖** — opencv/whisper/aiohttp等非核心依赖用ImportError捕获
4. **Pydantic models** — 输入验证 + 输出序列化
5. **async endpoints** — 所有路由用async def + await request.json()

### server.py注册模式
```python
try:
    from annotation_api import router as annotation_router
    app.include_router(annotation_router)
    logger.info("Multimodal annotation routes registered")
except ImportError as e:
    logger.warning(f"Annotation API not available: {e}")
```

### 全链路验证命令模板
```bash
# 验证每个新功能
curl -s -X POST http://localhost:8001/api/v2/端点 \
  -H "Content-Type: application/json" \
  -d '{"json":"payload"}' | python3 -m json.tool

# 核心API验证
for url in /health /api/v2/nodes /workflow.html /studio.html /zhiying; do
    curl -s -o /dev/null -w "%{http_code} %{url_effective}\n" "http://localhost:8001$url"
done
```
