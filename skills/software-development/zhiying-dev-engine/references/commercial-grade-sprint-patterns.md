# 商用级工程化Sprint模式 — 无Docker约束下的生产化改造

## 适用场景

将工作原型(prototype)系统性地改造为生产就绪(production-ready)状态，技术约束为：
- 无Docker/无Kubernetes
- 无PostgreSQL/无Redis(但有pip包)
- 有SQLite + SQLAlchemy + APScheduler
- 纯Python + FastAPI单进程

## 8层商用级补齐清单

逐层检查，不可跳层：

| 层级 | 验证项 | 实现方式(无Docker) |
|------|--------|-------------------|
| 1. 安全 | argon2密码 | argon2-cffi |
|  | JWT refresh token | python-jose |
|  | 审计日志(追加写) | FastAPI中间件 + SQLite |
| 2. 可靠性 | 优雅关闭 | signal处理 + FastAPI lifespan |
|  | 健康检查 | /health + /ready端点 |
|  | 任务队列 | APScheduler + SQLiteJobStore |
| 3. API规范 | 统一响应格式 | 中间件包装 success/data/error |
|  | 统一错误处理 | exception_handler注册 |
|  | 统一分页 | paginated_response工具函数 |
|  | API版本 | /api/v1/ 前缀路由 |
| 4. 访问控制 | 限流 | slowapi(内存模式) |
|  | API Key管理 | 独立SQLite + 中间件验证 |
|  | 角色权限 | RBAC中间件 |
| 5. 可观测性 | 结构化日志 | structlog + request_id |
|  | 管道监控 | APScheduler状态 + WebSocket |
|  | 运营看板 | Metric卡片 + Canvas折线图 |
| 6. 数据能力 | 搜索 | SQLite FTS5 |
|  | 数据浏览器 | AG Grid风格分页表格 |
|  | 数据导入 | CSV/JSON/Excel |
|  | 增量交付 | 版本差分 + tar.gz patch |
|  | 缩略图/预览 | PIL + ffmpeg + pdf2image |
|  | 数据库迁移 | 版本化SQL迁移 |
| 7. AI集成 | AI预标注 | DeepSeek API + BBox叠加 |
|  | 质量断言 | Column/Table/Row断言框架 |
|  | 标注一致性 | Cohen Kappa + IoU |
| 8. 架构 | 节点化工作流 | 三层节点(Dimension/Capability/Function) + DAG引擎 |
|  | 统一导出中心 | POST /api/v1/export |
|  | 批量操作 | POST /api/v1/batch/* |

## 迭代顺序策略

### 最优Sprint划分

```
Sprint 1: 基础设施(无依赖,可并行)
  ├── 优雅关闭(signal) — 小,低风险
  ├── 健康检查 — 小,低风险
  ├── 结构化日志 — 小,低风险
  └── 数据库迁移 — 小,低风险

Sprint 2: 核心业务(依赖Sprint 1)
  ├── 密码加固(argon2) — 小,低风险
  ├── 审计日志 — 小,低风险
  ├── API版本控制 — 小,低风险
  ├── 限流(slowapi) — 小,低风险
  └── 任务队列(APScheduler) — 中,低风险

Sprint 3: 数据管道
  ├── 搜索(FTS5) — 中,低风险
  ├── 数据导入 — 中,中风险
  ├── 增量交付 — 小,低风险
  ├── 缩略图/预览 — 中,中风险
  └── 标注一致性评分 — 小,低风险

Sprint 4: AI+运营
  ├── AI预标注(DeepSeek) — 中,中风险
  ├── 管道监控 — 中,低风险
  ├── 数据浏览器(AG Grid) — 中,低风险
  └── 运营看板 — 中,低风险

Sprint 5: 统一规范
  ├── 统一响应+错误处理 — 中,低风险
  ├── API Key管理 — 中,低风险
  ├── 权限API级验证 — 中,中风险
  ├── 批量操作 — 小,低风险
  ├── 导出中心 — 中,低风险
  └── 审计日志前端面板 — 中,低风险

Sprint 6: 核心架构
  ├── 质量断言框架 — 中,中风险
  ├── 节点化工作流引擎 — 大,高风险
  └── 标注历史追踪 — 中,低风险
```

### 依赖规则
- 同一Sprint内可并行(无共享依赖)
- Sprint N依赖Sprint N-1完成
- 安全相关(Sprint 2)必须在任何对外暴露前完成
- 统一规范(Sprint 5)必须在第三方集成前完成

## 多子Agent并行实施模式

### 适用条件
- 任务清单已确定(10-20项独立功能)
- 每项功能代码量<500行
- 各功能间无共享文件依赖

### 实施流程
1. 父Agent列出所有功能和各自的目标文件路径
2. **关键原则：每个文件只交给一个子Agent修改**（避免覆盖冲突）
3. 对于同一个大文件（如canvas_web.py）的修改，串行执行或由同一个子Agent完成
4. 所有子Agent完成后，父Agent做全量语法验证
5. 启动服务做全量curl验证
6. 失败项逐个排查而非全部重写

### 排他性文件访问协议
当多个子Agent并行工作时，以下文件必须**串行访问**：
- `api/canvas_web.py` 或类似的主应用文件
- 任何在多个功能间共享的引擎文件（如engines下的模块）
- config/配置类文件
- 前端HTML模板（内联在Python中的）

可用策略：把对共享文件的所有修改打包给**一个**子Agent，其他子Agent只负责新建独立文件。

## 常见死链模式（路由注册失败）

| 症状 | 根因 | 修复 |
|------|------|------|
| 404 | APIRouter创建在app之后但不在同一加载路径 | 检查文件导入链 |
| 404 | include_router的import失败被静默捕获 | 检查try/except块 |
| 500 | 路由函数中tasks.items()但req是list | Pydantic模型类型不匹配 |
| 500 | execute是async但路由没await | 检查async def调用链 |
| 500 | Pydantic报dict_type错误 | 检查nodes字段是list还是dict |
| 异常退出 | search_router未定义被删成注释 | 清理重复代码时检查完整性 |

## 验证清单（每次服务重启后执行）

```bash
# 基础
curl -s http://localhost:8765/api/v1/health
curl -s http://localhost:8765/api/v1/ready

# 认证
curl -s -X POST http://localhost:8765/auth/register -H 'Content-Type: application/json' -d '{"username":"t","password":"T123!","role":"admin"}'
curl -s -X POST http://localhost:8765/auth/login -H 'Content-Type: application/json' -d '{"username":"t","password":"T123!"}'

# API Key
curl -s -X POST http://localhost:8765/api/v1/api-keys/create -H 'Content-Type: application/json' -d '{"name":"test"}'

# 核心业务
curl -s -X POST http://localhost:8765/api/requirements/create -H 'Content-Type: application/json' -d '{"title":"t","type":"t","priority":"P0"}'
curl -s -X POST http://localhost:8765/api/crowd/workers -H 'Content-Type: application/json' -d '{"name":"t","skills":["t"]}'

# 数据能力
curl -s -X POST http://localhost:8765/api/v1/search -H 'Content-Type: application/json' -d '{"user_input":"test"}'
curl -s http://localhost:8765/api/datasets?page=1
curl -s http://localhost:8765/api/v1/export/formats

# AI
curl -s -X POST http://localhost:8765/api/prelabel -H 'Content-Type: application/json' -d '{"image_desc":"test","task_type":"detection"}'

# 运营
curl -s http://localhost:8765/api/v1/audit-logs
curl -s http://localhost:8765/api/monitor/pipeline
curl -s http://localhost:8765/api/ops/overview

# 工作流
curl -s http://localhost:8765/api/workflow/templates
curl -s http://localhost:8765/api/workflow/nodes
curl -s -X POST http://localhost:8765/api/workflow/validate -H 'Content-Type: application/json' -d '{"nodes":[{"id":"n1","type":"text"}],"connections":[]}'
curl -s -X POST http://localhost:8765/api/workflow/execute -H 'Content-Type: application/json' -d '{"nodes":[{"id":"n1","type":"text"}],"connections":[]}'
```

## 常见陷阱

### 响应格式不统一
不同子Agent创建的路由可能使用不同的响应格式：
- 有的返回 `{"success":true,"data":...}` 
- 有的直接返回数据
- 有的返回Pydantic模型

**对策：** 统一响应格式必须在Sprint 5做，并在所有路由注册完成后加上自动包装中间件。

### 子Agent写入的文件位置错乱
子Agent可能在错误的工作目录创建文件（如 `/home/administrator/` 而不是项目根目录）。

**对策：** 子Agent的goal中必须包含确切的项目根路径。

### 重复代码积累
每次patch/修复都引入新代码，可能在同一文件留下多个重复版本（新旧函数并存）。

**对策：** 每次修改后检查文件是否有`return`之后还跟着代码的情况（dead code after return）。
