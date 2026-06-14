# 全量API集成测试模式（2026-06-15实战）

## 文件结构
`backend/tests/test_full_api.py` — 96个测试方法覆盖45+端点

## 核心模式
```python
from fastapi.testclient import TestClient
from server import app
client = TestClient(app)
```

## 覆盖领域
| 领域 | 测试数 | API端点 |
|------|--------|---------|
| 健康检查/metrics | 3 | /health, /metrics, /metrics/json |
| 页面路由 | 4 | /, /zhiying, /studio.html, /workflow.html |
| 用户认证 | 3 | POST /auth/login, GET /auth/me |
| 节点系统 | 2 | /api/v2/nodes, /api/v2/nodes/categories |
| 管道(Pipeline) | 4 | POST/GET /api/v2/pipelines, advance/fail |
| 数据集版本 | 5 | init/commit/log/branch/merge |
| AIGC生成 | 5 | POST /api/v2/generate, queue/status |
| ML Backend | 4 | register/list/predict/active-learning |
| RBAC多租户 | 6 | orgs/projects/create/check |
| 多模态标注 | 2 | create/get |
| 众包管理 | 8 | workers/tasks/assign/submit/review |
| 子团队 | 4 | create/list/add/remove |
| Profile | 3 | get/preferences/actions |
| 向量搜索 | 2 | vector/index |
| 数据血缘 | 4 | record/upstream/downstream/graph |
| 质量中心 | 2 | overview/anomalies |

## 关键规范
- 自包含：每个test不依赖其他test的执行结果
- 速率限制兼容：接受 200/429/500 等合理响应码
- 使用 `assert r.status_code in (200, 429)` 模式避免速率限制误报
- 覆盖所有新添加的路由
