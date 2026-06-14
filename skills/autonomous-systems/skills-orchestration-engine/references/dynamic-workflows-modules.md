# Dynamic Workflows 模块索引（v6 — 18模块/18万+字节）

## 完整模块列表

| #  | 文件名                    | 大小   | 作用                              | 波次 | 主动运行 |
|----|--------------------------|--------|-----------------------------------|------|---------|
| 1  | types.py                 | 6.7KB  | 核心类型定义                       | 1    | 被调用 |
| 2  | storage.py               | 17.8KB | SQLite持久化+checkpoint            | 1    | 被调用 |
| 3  | executor.py              | 7.9KB  | delegate_task调度+SDLC+Company注入  | 1+4  | 被调用 |
| 4  | scheduler.py             | 15.0KB | 4种调度形态                          | 1    | 被调用 |
| 5  | runtime.py               | 24.1KB | Workflow Runtime+preflight+齿轮+复盘+进化 | 1+3+4+5 | 被调用 |
| 6  | dsl.py                   | 12.8KB | Python DSL+3内置模板                | 2    | 被调用 |
| 7  | adversarial.py           | 9.4KB  | 4角色对抗式验证                     | 2    | 被调用 |
| 8  | recover.py               | 5.4KB  | 断点恢复引擎                       | 2    | 被调用 |
| 9  | bridge.py                | 2.4KB  | 编排引擎桥接                       | 2    | 被调用 |
| 10 | preflight.py             | 11.1KB | 执行前强制三查                      | 3    | runtime注入 |
| 11 | gear_integration.py      | 9.6KB  | 齿轮G0/G1/G6对接                    | 3    | runtime注入 |
| 12 | retrospect_integration.py| 4.6KB  | 复盘+Hy-Memory对接                  | 3    | runtime注入 |
| 13 | active_engine.py         | 10.4KB | SDLC强制+cron自激活+全能力融合       | 4    | 被调用 |
| 14 | company_matcher.py       | 14.2KB | Agent Company匹配(117员工+身份注入)  | 4    | executor注入 |
| 15 | cron_activate.py         | 1.5KB  | cron自激活脚本(每15分钟)            | 4    | cron */15 |
| 16 | evolution_durable.py     | 20.4KB | 进化桥接+Durable Engine+强化矩阵    | 5    | runtime+ cron */
| 17 | daemon.py                | 10.0KB | 守护进程：健康扫描+联合唤醒+stuck检测 | 5    | cron */5 |
| 18 | dual_review plugin | 3.5KB | 插件注入Hermes主Agent(pre_tool_call hook) | 5+ | Hermes主Agent启动 |

## crontab 注入的3条主动运行任务

| Cron | 脚本 | 做什么 |
|------|------|--------|
| `*/5 * * * *` | workflows/daemon.py | 16模块健康扫描 + pending激活 + stuck检测 + 联合唤醒齿轮/生产监控 |
| `*/30 * * * *` | EvolutionBridge.trigger_evolution() | 检查retro_candidates表，>=3个时触发self_evolve_cluster |
| `0 18 * * *` | workflows/daemon.py --report | 每日workflow执行汇总报告 |

## AGENTS.md 固化的14条规则

| # | 规则 | 固化日期 | 监管 |
|---|------|---------|------|
| 1 | 执行前强制三查 | 2026-06-09 | preflight.py |
| 2 | 齿轮系统强制对接 | 2026-06-09 | gear_integration.py |
| 3 | Agent Company强制匹配 | 2026-06-09 | company_matcher.py |
| 4 | SDLC流程强制 | 2026-06-09 | active_engine.py |
| 5 | DW cron自激活 | 2026-06-09 | cron_activate.py |
| 6 | 全能力融合 | 2026-06-09 | active_engine.py |
| 7 | 复盘反思（加强） | 2026-06-09 | retrospect_integration.py |
| 8 | 进化循环 | 2026-06-09 | evolution_durable.py |
| 9 | Durable Execution | 2026-06-09 | evolution_durable.py |
| 10 | 全能力互相强化 | 2026-06-09 | evolution_durable.py(CapabilityReinforcer) |
| 11 | 守护进程 | 2026-06-09 | daemon.py |

## 全能力执行链路（守护进程版）

```
cron */5(m)    daemon.py → 16模块健康扫描 + 联合唤醒 gear_registry + production_monitor
     ↓
cron */15(m)   cron_activate.py → 检查pending/stuck workflow
     ↓
workflow启动    G0齿轮注册(gear_vault.register_task)
     ↓
[每个Phase]
     → preflight强制三查(session_search+memory+fact_store+skill预载+web_search+架构师评估)
     → G1唤醒更新(wake_guide.json)
     → checkpoint写入SQLite
     ↓
[每个Task]
     → SDLC流程强制注入(executor.py)
     → Agent Company匹配(company_matcher.py: 117员工, 部门匹配→技能评分→身份prompt)
     → delegate_task调度(subagent)
     ↓
workflow完成    G6验证(gear_integration.run_validator)
     → 复盘反思(retrospect: 5步结构化)
     → 进化候选(evolution_bridge.feed_retrospect → retro_candidates表)
     → Hy-Memory提取(extract_to_memory)
     ↓
cron */30(m)   EvolutionBridge.trigger_evolution() → 候选>=3触发self_evolve_cluster
     ↓
每天03:00       self_evolve_cluster → skill进化 + 记忆压缩 + 能力调优
     ↓
每天18:00       daemon.py --report → 当日所有workflow执行汇总
     ↓
下次workflow    skill更准 + preflight更全 + SDLC更严 ← 进化闭环
```

## 关键注入点（不可绕过）

1. **runtime.py line 165**: `run()`中每个phase前调用`run_preflight()` — 强制执行前检查
2. **runtime.py line 150**: `run()`开头调用`register_to_gear_vault()` — 强制G0注册
3. **runtime.py line 265**: `finally`块中调用`run_retrospect()` + `feed_retrospect()` — 强制复盘+进化
4. **executor.py line 85**: `execute_task()`中调用`CompanyMatcher.match()` — 强制员工匹配
5. **executor.py line 97**: `execute_task()`中注入`SDLCEnforcer.build_execution_context()` — 强制SDLC流程

## 边缘情况处理

| 问题 | 原因 | 处理方式 |
|------|------|---------|
| 员工技能名为空字符串 | yaml中skill条目缺name字段 | `if not skill_name: continue` 跳过 |
| proficiency='5/5' | 格式不统一 | `int(str(raw_prof).split('/')[0])` 取第一部分 |
| tools.yaml是{}+词典 | 格式不一致 | `raw.get("tools",[]) if isinstance(raw,dict)` 双兼容 |
| 员工身份注入超长 | 中文描述+多个前公司 | 截断到200字以内 |
| preflight没有delegate_task | runtime未配置 | log记录, 继续执行不阻塞 |
| 进化候选写入异常 | DB连接/表不存在 | try/except 忽略, 不影响workflow主流程 |
