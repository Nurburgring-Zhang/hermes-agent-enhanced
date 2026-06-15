# Hermes Enhanced Pack vs GitHub 仓库对比

> 来源: 2026-06-15 — M:\hermes-enhanced-pack 与 github.com/Nurburgring-Zhang/hermes-agent-enhanced 交叉对比

## 规模对比

| 指标 | 本地Pack | GitHub仓库 |
|------|---------|-----------|
| 总文件 | 7,154 | ~3,000 |
| Python文件 | 544 | ~340 |
| Skills | 174 | 180+ |
| Plugins | 6 | 3+commercial_grade_enforcer |
| Services | 2 systemd | 0 |
| Commits | — | 10 |

## 本地Pack独有（GitHub仓库完全缺失的18大系统）

### 1. 三层认知架构 (core/agent/)
- `model_router.py` (255行) — 智能模型路由(E0/E1/E2任务分级)
- `monitor.py` (193行) — 监控引擎(CONTINUE/CHECKPOINT/REFLECT/RECOVER/ABORT信号)
- `reflector.py` (303行) — 三轮递进反思(执行→策略→元认知，Reflexion+华为IPD TR)

### 2. 自主引擎 (core/auto_engine/)
- `master_integration_hub.py` (468行) — 主集成中枢v2.0
- `multi_agent_orchestrator.py` (443行) — 层级/并行/顺序/扇出入编排
- `self_evolution_engine.py` (667行) — 观察→分析→识别→生成→执行→验证循环
- `capability_registry.py` — 能力→Agent映射

### 3. 进化V3系统 (core/evolution_v3/ — 18模块)
- `v3_daemon.py` — 全自动守护进程
- `self_enhancement_v3_loop.py` — V3.1七通道/IFC/DPW集成
- `task_engine.py` — 双规划器+见证者+3级纠偏
- `experience_engine.py` — 经验自动提取+跨任务复用
- `semantic_engine_v2.py` — 语义嵌入v2+双语漂移检测
- `seven_channel_memory.py` — 七通道并行检索
- `channels_v2.py` — 扩散激活+实体图+Hopfield
- `memory_lifecycle.py` — 长期记忆数据生命周期
- `self_check_engine.py` — 全系统自检与自维护
- `hooks_engine.py` — 六事件Hooks引擎
- `subagent_manager.py` — 子Agent自动管理
- `information_fidelity_core.py` / `ifc_core_v2.py` — IFC v1/v2(DFloat11+Blosc2)
- `gepa_optimizer.py` — GEPA遗传优化器+Merkle树验证
- `hash_chain_auditor.py` — 链式哈希审计
- `commercial_test.py` — 极端多条件商业级评估
- `full_system_test_v3.py` — V3全量集成测试

### 4. 生产循环引擎 (core/production_loop/ — 8模块)
- `engine.py` — 统一入口
- `main_loop.py` (613行) — 确定性主循环(10种终止条件)
- `loop_state.py` — FileBasedStateStore
- `dag_manager.py` — DAG任务图+GlobalConstraintManager
- `agent_committee.py` — CriticAgent+ThreeLayerReflection+SubAgentOrchestrator
- `verification.py` — StepVerifier+DegradationPreventer
- `security.py` — SevenLayerPermissionSystem
- `__init__.py`

### 5-18: 其他独有系统
- systemd服务(hermes-gateway/hermes-eternal)
- Docker部署(Dockerfile+entrypoint+GitHub Actions)
- LINE Works插件
- CLI工具(RAG+语音命令)
- install.sh + install-windows.bat
- crontab_backup.txt(50+定时任务)
- topology.yaml
- config/目录(独立AGENTS.md/SOUL.md/USER.md)

## GitHub仓库独有（本地Pack无）

- 安全三模块: security_sandbox.py/prompt_guard.py/secret_manager.py
- P2功能: api_gateway.py/git_workflow.py/plugin_manager.py
- P3性能: performance_profiler.py/stress_tester.py/health_monitor.py
- 12个新测试文件(guardian/auto_ci/gear_full/memory_full等)
- 部署文件(requirements.txt/LICENSE/CONTRIBUTING.md)
- task-execution skills(6个)

## 迁移建议

优先级排序:
1. P0: core/evolution_v3/ → 进化引擎核心(18模块)
2. P0: core/production_loop/ → 生产循环(8模块)
3. P1: core/agent/ → 三层认知(3模块)
4. P1: core/auto_engine/ → 自主引擎(4模块)
5. P2: services/ config/ install脚本
6. P2: extras/
