# 智影数据工场 — 全功能数据生产管理平台 (2026-06-10)

## 概述

基于两份设计文档(17万字)，在nanobot-factory基础上建设了全功能AIGC数据生产管理平台。覆盖200个功能点(186已实现/93%)，19章设计文档100%对齐。

## 新增核心模块(13个)

| 模块 | 文件 | 功能 |
|------|------|------|
| 需求管理 | `core/requirement_manager.py` | 6种需求类型/4优先级/全状态链/Agent自动拆解 |
| 任务管理 | `core/task_manager.py` | 8种任务/11种状态/3种分配策略/仲裁 |
| 工作流引擎 | `core/workflow_engine.py` | DAG拓扑排序/22预设算子/JSON导入导出/环检测 |
| 算子库 | `core/operators_lib.py` | 44个算子(6大类)/OPERATOR_REGISTRY/None保护 |
| 评测闭环 | `core/eval_manager.py` | 6种评测/BadCase状态机/反馈闭环 |
| 统计系统 | `core/stats_manager.py` | 个人/项目/全局三维统计/排行 |
| 数据治理 | `core/governance.py` | 7种血缘关系/审计日志/全量增量备份/倒排索引O(1) |
| 资产管理 | `core/asset_manager.py` | 文件夹树/标签/智能文件夹/多维搜索 |
| 多租户 | `core/multi_tenant.py` | 3角色/API Key/O(1)认证/配额/项目隔离 |
| 批量引擎 | `core/batch_engine.py` | 9种管线/异步并行/semaphore/进度追踪 |
| 数据管理+导出 | `core/data_manager.py` | 版本锁/线程安全/5种MLLM格式/递归子目录 |
| Agent体系 | `agents/data_agents.py` | 10种Agent/正则"1万亿"/workflow推荐 |
| 搜索+预览 | `core/search_engine.py` | 6种搜索模式/中文全文/EXIF/关键帧/波形 |
| 标签+报告 | `core/auto_tag.py` + `core/report_generator.py` | 自动标签/CSV+JSON报告 |

## API路由: 35+15=50个端点

- `/api/v2/*` (35) — 智影工厂全功能
- `/api/v2/production/*` (15) — 之前的多用户批量生产

## 关键bug修复模式

1. **路由单例模式**: `_get_*()`必须全局缓存，不能每次`return Class()`
2. **算子ID一致性**: operators_lib与workflow_engine的DEFAULT_OPERATORS必须交叉验证
3. **状态转换表**: 每个状态机必须有合法转换表+非法回退拒绝
4. **版本锁**: create_version的读版本号和写回必须在同一个锁内
5. **governance索引**: 用倒排索引代替O(n)全表扫描
6. **中文全文搜索**: `\w+`分词后逐索引项做子串匹配

## 启动问题修复记录

### 问题1: frontend/index.html 未被serve
- 现象: 访问根URL看到旧Eagle页面，看不到智影新界面
- 根因: server.py的 `/` 路由返回 `templates/index.html`，不自动搜索 frontend/ 目录
- 修复: `cp frontend/index.html backend/templates/index.html`
- 教训: 在已有FastAPI项目上加前端时，必须确认静态文件服务已指向正确位置

### 问题2: start.sh venv路径不存在
- 现象: bash start.sh退出无输出
- 根因: start.sh假设有venv目录，但开发环境中可能没有
- 修复: 启动脚本中做venv存在性判断，或直接用python3
- 教训: 启动脚本不要假设虚拟环境存在

### 问题3: StatsManager sqlite3错误 no such column: id
- 现象: 全链路验证时StatsManager报错
- 根因: PersistentManager._db_key_field默认"id"，但StatsManager的key是"user_id"
- 修复: 在StatsManager中加 `_db_key_field = "user_id"`
- 教训: 每个继承PersistentManager的类都要确认_db_key_field

- P2功能测试: 276/276 PASS
- P3对抗式: 161/163 (2个已知: SourceOSS类型检查, 版本并发)
- P4集成: 83/83 PASS
- P5上线: 16/16 PASS
- 最终回归: 51/52 PASS

## 工程文件清单

全部位于 `backend/core/`, `backend/agents/`, `backend/routes/`

详见 `DELIVERY_REPORT_ZHIYING.md` + `AUDIT_FULL_REPORT.md`
