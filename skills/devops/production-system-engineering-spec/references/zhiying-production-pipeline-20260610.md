# 智影数据工场生产管线实战实现记录（2026-06-10）

## 背景
基于 D:/ 的两份设计文档（功能设计19章+开发文档3251行），在 nanobot-factory 后端完整实现了全功能多模态训练数据生产与管理平台。

## 核心架构决策

### 为什么用内存管理而非SQLite（v1阶段）
- 13个模块快速迭代，内存存储避免schema迁移
- 所有模块接口设计为异步+可接数据库模式
- 后续可加 PostgreSQL 持久化层（eval_manager.governance有备份机制）

### 惰性导入模式的选择
- routes/v2_zhiying.py 35个端点全部用 `def _get_X()` 函数内导入
- 因为 server.py 在模块级调用 `register_all_routers(app)`，如果 routes 模块在导入时立刻 import server，会形成循环依赖
- 模式: `def _get_rm(): from core.requirement_manager import RequirementManager; return RequirementManager()`

### 算子双注册机制的Bug
- workflow_engine 有 DEFAULT_OPERATORS（22个预定义）
- operators_lib 有 OPERATOR_REGISTRY（44个完整算子）
- 两者 ID 字符串必须一致，否则 `add_node()` 返回 None（不抛异常！）
- 修复: 将 `source.local` 改为 `source.local_file`

## 数据管道对照表

| 功能设计章节 | 实现模块 | 关键类/函数 |
|-------------|---------|------------|
| 7.2 需求生命周期 | requirement_manager | RequirementManager.create/auto_decompose/update_status |
| 9.2 任务生命周期 | task_manager | TaskManager.create/publish/assign/submit/review/arbitrate |
| 8.3 可视化工作流 | workflow_engine | WorkflowEngine.add_node/add_edge/get_topological_order |
| 8.2 算子库(44个) | operators_lib | BaseOperator.process + 6大类子类 |
| 11.3 评测任务 | eval_manager | EvalManager.create_eval_task/add_metric/add_bad_case |
| 11.6 反馈闭环 | eval_manager | EvalManager.create_feedback_loop/complete_feedback_loop |
| 10.2-10.5 统计 | stats_manager | StatsManager.record_task_completed/get_global_stats/get_rankings |
| 12.1 血缘追踪 | governance | GovernanceManager.add_lineage/build_lineage_graph |
| 12.3 审计日志 | governance | GovernanceManager.log_audit/query_audit |
| 12.5 备份恢复 | governance | GovernanceManager.create_backup/restore_backup/cleanup_old_backups |
| 4.1-4.4 分类与组织 | asset_manager | AssetManager.create_folder/create_tag/create_smart_folder |
| 5.1-5.5 搜索与筛选 | asset_manager | AssetManager.search_assets/query_smart_folder |
| 1.4 Agent矩阵 | data_agents | 10 Agent子类 + AGENT_REGISTRY |
| 3.3 格式导出 | data_manager | DataManager.export_dataset(5种格式) |
| 9.6 批量生产 | batch_engine | BatchEngine.create_task/_run_batch |
| 12.4 权限角色 | multi_tenant | UserManager.create_user/check_permission/authenticate |

## 全链路验证输出（2026-06-10）
```
✅ 13个模块导入全部成功
✅ 需求: 自动拆解6子任务
✅ 任务: 发布→分配→提交→评审→完成(score=95)
✅ 工作流: 6节点/5边 DAG拓扑排序正确
✅ 算子: local_file(34718文件), export_llava
✅ Agent: 需求解析10万条
✅ 评测: 2指标, 1 BadCase, 反馈闭环
✅ 统计: 2用户/10000条目/2排行
✅ 治理: 2节点血缘图/审计日志/备份
✅ 资产: 2资产/1文件夹/智能文件夹
✅ 多租户: 2用户/1项目
✅ 批量: 2个输入任务
✅ 数据管理: 版本v0.0.1
✅ v2 API: 35个端点
```
