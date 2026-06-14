# 多用户批量生产体系实现记录 (2026-06-10)

## 背景
nanobot-factory 项目已有16个数据生产管线模块和45个REST API路由，但缺少：
- 多用户/租户隔离
- 批量生产引擎
- 数据生命周期管理
- 权限体系
- MLLM格式导出

## 实现方案

### 核心模块设计原则
- **惰性导入** 避免FastAPI循环依赖：`_get_state()` 函数内 `from server import state`
- **内存存储** 当前实现（后续可接PostgreSQL）
- **asyncio并发** BatchEngine使用 `asyncio.create_task` + `Semaphore` 控制并发度

### 文件结构
```
backend/
├── core/
│   ├── multi_tenant.py      # UserManager + Role/Quota/Project
│   ├── batch_engine.py      # BatchEngine + TaskStatus + PipelineType
│   └── data_manager.py      # DataManager + DataType + ExportFormat
├── routes/
│   └── production.py        # 15个 /api/v2/* 端点
```

### 关键设计决策
1. **API Key认证** — `nbk-{uuid}` 格式，UserManager.authenticate() 实现
2. **版本控制** — v0.0.0→v0.0.1 自动递增最后位
3. **权限层级** — ADMIN(0) < OPERATOR(1) < VIEWER(2)，roles.index() 比较
4. **PipelineType** — 9种类型可独立注册Worker
5. **Manifest** — 每次批量运行输出 manifest.json

### 测试覆盖
- test_multi_tenant.py: 12 tests (0.22s)
- test_batch_engine.py: 9 tests (1.44s)
- 端到端验证: 用户→项目→数据集→格式导出全链路

### 引用
- [多用户批量生产体系蓝图](../docs/多用户批量生产体系蓝图.md)
- DELIVERY_REPORT_V2.md
