# Nanobot Factory 2026-06-12 完整会话记录

## 会话范围
- 全项目~145,000行极端深度逐行审核（285个问题修复）
- A-E 6大模块修复（agent接入/functions/enterprise/integrations/前端）
- Phase 1-4 新功能构建
  - Phase 1: ML Backend + 主动学习 (core/ml_backend.py)
  - Phase 2: 多模态标注 (core/multimodal_annotation.py + annotation_api.py)
  - Phase 3: RBAC多租户 (core/rbac.py)
  - Phase 4: 数据集版本管理(git-like) (core/dataset_version.py)
- 三AI互审模式实践
- UI架构设计（对标Scale AI/Labelbox）

## 核心教训

### 子Agent超时处理
>8000行大文件永远不要用子Agent。直接用patch做2-3个精确定位修改。

### 分段patch策略
大HTML/JS文件增强必须分段patch，禁止一次性塞给子Agent。

### 三AI互审启动模板
```python
tasks = [
    {"goal": "全网检索竞品对标，找出功能差距", "toolsets": ["web"]},
    {"goal": "设计可组合功能节点体系", "toolsets": ["terminal","file"]},
    {"goal": "审核代码质量+真实性", "toolsets": ["terminal","file"]}
]
```

### 强制前置流程
用户要求的5步门控流程：
1. 全局观念建立
2. 深度思考分析
3. 完整规划方案
4. 软件工程流程执行
5. 三AI互审互查

缺少任何一步用户都会打断。

## 新功能API端点

### ML Backend
- POST/GET /api/v2/ml/models — 注册/列表
- DELETE /api/v2/ml/models/{id} — 注销
- POST /api/v2/ml/models/{id}/predict — 预标注
- GET /api/v2/ml/active-learning — 主动学习样本

### 多模态标注
- POST /api/v2/annotations/video/extract-frames — 视频帧
- POST /api/v2/annotations/audio/transcribe — 音频转写
- POST/GET/PUT/DELETE /api/v2/annotations/* — CRUD

### RBAC
- POST/GET /api/v2/rbac/orgs — 组织
- POST/GET /api/v2/rbac/orgs/{id}/members — 成员
- POST/GET /api/v2/rbac/projects — 项目
- POST /api/v2/rbac/check — 权限检查

### 数据集版本
- POST /api/v2/datasets/{id}/init — 初始化
- POST /api/v2/datasets/{id}/commit — 提交
- GET /api/v2/datasets/{id}/log — 日志
- POST /api/v2/datasets/{id}/checkout — 签出
- GET /api/v2/datasets/{id}/diff — 差异
- POST /api/v2/datasets/{id}/branch — 分支
- POST /api/v2/datasets/{id}/merge — 合并
- POST /api/v2/datasets/{id}/tag — 打标签
- POST /api/v2/datasets/{id}/rollback — 回滚

### 用户认证
- POST /api/v2/auth/login — 登录
- GET /api/v2/auth/me — 当前用户

### Pipeline状态机
- POST/GET /api/v2/pipelines — 创建/列表
- GET /api/v2/pipelines/{id} — 详情
- POST /api/v2/pipelines/{id}/advance — 推进
- POST /api/v2/pipelines/{id}/fail — 失败
- POST /api/v2/pipelines/{id}/complete — 完成
- POST /api/v2/pipelines/{id}/reset — 重置

### 质量中心（已有）
- GET /api/v2/quality/overview — 质量总览
- GET /api/v2/quality/anomalies — 异常列表
- GET /api/v2/quality/distribution — 分布
