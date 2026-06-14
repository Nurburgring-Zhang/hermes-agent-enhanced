# 商用级强制执行框架 R9-R15

基于《商用级软件开发与任务执行方法论》（255行，7主题全网调研），Hermes新增7条代码级强制规则。

## 插件架构

```
commercial_grade_enforcer/
├── __init__.py              # 入口: register(ctx) 注册8个hook
├── wbs_injector.py          # R9: WBS分解注入 (pre_task_start)
├── idempotency_guard.py     # R10: SHA256幂等键+SQLite去重 (pre_tool_call)
├── checkpoint_guard.py      # R11: 状态快照+断点恢复 (post_tool_call)
├── quality_gate.py          # R12: 5道门禁 (post_tool_call)
├── verifier_agent.py        # R13: 模型家族检测 (pre_tool_call)
├── acceptance_checklist.py  # R14: ATDD验收清单 (post_task_complete)
├── degradation_handler.py   # R15: 5级降级 (post_tool_call)
├── metrics_collector.py     # 后台线程: 4项核心指标
└── plugin.yaml              # 插件元数据
```

## 验证结果（2026-06-16）

全部8个模块可导入: 通过
全部8个模块注册到config.yaml: 通过
IMDF首次验收: 25/25
IMDF二次验收: 8/8核心API

## R9 WBS注入模式

wbs_injector.inject_wbs(ctx, task_description, task_steps) — 自动构建Epic→Feature→Story→Task树，MoSCoW优先级标注。

## R10 幂等键模式

idempotency_guard.inject_idempotency_key(ctx, tool_name, kwargs) — SHA256(url+body+timestamp)生成幂等键，SQLite去重。

## R12 质量门禁序列

quality_gate.check_gates(ctx, tool_name, result) — 依次执行: lint → type → security → test → performance，任一门失败=BLOCKED。

## 主动能力使用规则（最高优先级）

1. **模型切换** — 当前模型降级时，开子Agent指定目标模型
2. **上下文压缩** — >15万token或80%使用率时主动压缩
3. **长期记忆** — 每次学到新东西立即更新memory+skill
4. **多子Agent并行** — 独立Phase用tasks数组(最多3个)并行
5. **任务拆分** — 复杂任务先拆分为独立子任务再分批并行
