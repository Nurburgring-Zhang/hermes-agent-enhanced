# Phase 1-4: 增量式平台能力构建模式

## 来源
Nanobot Factory 2026-06-12 会话。从审核→修复→出规划→执行Phase 1-4的全流程。

## 背景
项目已有270+ API端点、86K行后端、20个Provider、25个节点系统。还需要补齐4个缺失领域能力。

## 四阶段能力构建模式

### 模式：并行子Agent实现 + 执行AI路由注册

每个Phase = 一个独立核心模块文件 + 6-11个API端点

| Phase | 核心文件 | API数 | 实现时长 | 核心概念 |
|-------|---------|-------|---------|---------|
| 1: ML Backend + 主动学习 | core/ml_backend.py | 6 | ~80分钟 | 模型注册/预标注/不确定性采样 |
| 2: 多模态标注 | core/multimodal_annotation.py + annotation_api.py | 7 | ~160分钟 | 视频帧提取/音频转写/CRUD |
| 3: RBAC多租户 | core/rbac.py | 8 | ~50分钟 | 组织-项目-用户三级+权限矩阵 |
| 4: 数据集版本管理 | core/dataset_version.py | 11 | ~20分钟 | git-like: commit/diff/branch/merge/tag/rollback |

### 实现协议

1. **每个Phase用delegate_task leaf subagent** — goal写清楚所有需要实现的代码和所有需要注册的路由
2. **subagent写代码+注册路由同时完成** — 让subagent同时创建core/文件和在server.py中添加路由
3. **执行AI不做代码修改** — 只在subagent完成后验证语法和API
4. **重启服务器验证** — 每个Phase必须要curl验证真实返回数据

### 核心模块结构模板

```
core/xxx.py          → 纯数据逻辑，无FastAPI依赖
                        - Enum定义
                        - classmethod + 类变量（单例模式）
                        - get_xxx() 全局访问函数
                        - 所有方法同步（非async），async在路由层封装

annotation_api.py    → FastAPI APIRouter（仅当路由太多时才独立文件）
                        - prefix="/api/v2/..."
                        - async def + request.json()
                        - try/except包住

server.py路由注册    → 直接在server.py的@app路由区域增加
                        - 从core模块导入全局函数
                        - @app.xxx /api/v2/xxx
                        - 返回 {"success": True, "data": ...}
```

### 路由注册验证

路由注册后出现404的根本原因排查顺序：
1. `grep -n 'from xxx import' server.py` — 确认导入存在
2. `grep -n '@app.xxx .*端点路径' server.py` — 确认路由装饰器存在
3. `kill + sleep 3 + 重启` — 确认无旧进程占用端口
4. 如果用了APIRouter，确认`app.include_router(xx_router)`已执行且没有被注释

### 三路交叉验证

每个Phase完成后做：
1. `curl` API端点 → 验证返回结构
2. `python3 -c "from core.xxx import X; print(X.method())"` → 验证模块可导入
3. `py_compile.compile('core/xxx.py')` → 验证语法

## 各Phase核心架构

### Phase 1: ML Backend + Active Learning
```
core/ml_backend.py:
  MLModelType (object_detection, classification, segmentation, caption, tag)
  MLModel (id, name, model_type, status, endpoint, api_key, accuracy)
  MLBackend (register, list, predict[HTTP/本地], active_learning[uncertainty/random])
  get_ml_backend() 单例

API:
  POST /api/v2/ml/models          — 注册模型
  GET  /api/v2/ml/models          — 列表(可选model_type过滤)
  DELETE /api/v2/ml/models/{id}   — 注销
  POST /api/v2/ml/models/{id}/predict — 执行预标注
  GET  /api/v2/ml/active-learning  — 主动学习采样
  POST /api/v2/ml/models/{id}/accuracy — 更新准确率
```

### Phase 2: Multimodal Annotation
```
core/multimodal_annotation.py:
  MediaType (IMAGE, VIDEO, AUDIO, TEXT)
  AnnotationType (BBOX, POLYGON, KEYPOINT, SEGMENTATION, TRANSCRIPT, CLASSIFICATION)
  VideoAnnotation (extract_frames[opencv], propagate_bbox)
  AudioAnnotation (transcribe[whisper], get_waveform[soundfile])
  MultimodalAnnotationManager (create/get/update/delete)
  get_annotation_manager() 单例

annotation_api.py: APIRouter(prefix="/api/v2/annotations")
  POST /video/extract-frames
  POST /audio/transcribe
  POST /audio/waveform (bonus)
  POST /create
  GET /{media_id}
  PUT /{ann_id}
  DELETE /{ann_id}
```

### Phase 3: RBAC Multi-Tenant
```
core/rbac.py:
  Role (ADMIN, ORG_OWNER, ORG_ADMIN, PROJECT_MANAGER, ANNOTATOR, REVIEWER, VIEWER)
  Permission (CREATE, READ, UPDATE, DELETE, ADMIN)
  ROLE_PERMISSIONS 矩阵
  Organization (org_id, name, owner, members)
  Project (project_id, name, org_id, members)
  RBACManager (create_org, add_member, create_project, check_permission)
  rbac = RBACManager() 单例

API:
  POST /api/v2/rbac/orgs
  GET  /api/v2/rbac/orgs
  POST /api/v2/rbac/orgs/{org_id}/members
  GET  /api/v2/rbac/orgs/{org_id}/members
  POST /api/v2/rbac/projects
  GET  /api/v2/rbac/projects
  POST /api/v2/rbac/projects/{project_id}/members
  POST /api/v2/rbac/check
```

### Phase 4: Dataset Versioning (git-like)
```
core/dataset_version.py:
  DatasetVersion (commit, checkout, checkout_branch, diff, create_branch, merge, tag, log, rollback)
    - _versions dict: version_id → snapshot
    - _branches dict: branch_name → head version_id
    - _tags dict: tag_name → version_id
    - commit() 生成基于hash的version_id + 记录parent
    - diff() 比较两个版本: added/removed/modified
    - merge() 支持ours/union策略
  DatasetVersionManager (get_or_create, list_datasets)
  get_version_manager() 单例

API:
  POST /api/v2/datasets/{id}/init
  GET  /api/v2/datasets
  POST /api/v2/datasets/{id}/rows
  POST /api/v2/datasets/{id}/commit
  GET  /api/v2/datasets/{id}/log
  POST /api/v2/datasets/{id}/checkout
  GET  /api/v2/datasets/{id}/diff?=a&b=b
  POST /api/v2/datasets/{id}/branch
  POST /api/v2/datasets/{id}/merge
  POST /api/v2/datasets/{id}/tag
  POST /api/v2/datasets/{id}/rollback
```

## 验证模板

```bash
# Phase 1
curl -s -X POST http://localhost:8001/api/v2/ml/models -d '{"name":"CLIP","model_type":"tag"}'
curl -s http://localhost:8001/api/v2/ml/models
curl -s "http://localhost:8001/api/v2/ml/active-learning?strategy=uncertainty&count=5"

# Phase 2
curl -s -X POST http://localhost:8001/api/v2/annotations/create -d '{"media_id":"test","media_type":"image","annotation_type":"bbox","data":{"x":1}}'
curl -s http://localhost:8001/api/v2/annotations/test

# Phase 3
curl -s -X POST http://localhost:8001/api/v2/rbac/orgs -d '{"name":"Org","owner":"admin"}'

# Phase 4
curl -s -X POST http://localhost:8001/api/v2/datasets/ds1/init -d '{"name":"Test"}'
curl -s -X POST http://localhost:8001/api/v2/datasets/ds1/commit -d '{"message":"v1","branch":"main"}'
curl -s "http://localhost:8001/api/v2/datasets/ds1/log?branch=main"
```
