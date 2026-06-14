# Hermes Agent 增强系统完整架构

## 八层系统架构

```
用户层: config.yaml(845行) / SOUL.md / AGENTS.md / USER.md
执行层: conversation_loop / tool_executor / run_agent / model_tools(已注入rule_enforcer)
插件层: dual_review / model_router / force_compressor / auto_compressor / auto_workflow
规则层: R1-R14 代码强制(rule_enforcer.py 1459行) + R14三阶段开发铁律(phase_state.json持久化)
弹性层: CircuitBreaker/Retry/Timeout/RateLimiter/Fallback/AuditLog/Metrics/HotReload/DryRun
子系统: Agent Company(117人) / Expert System(390专家) / 六部Actor / CAI/CD / 审计系统 / 错误处理
齿轮层: G0-G8 八层可靠性链(1min~1day全覆盖)
记忆层: Hy-Memory L1/L2/L3 + 三级上下文压缩 + 段切换 + 任务断点续跑
```

## 规则引擎层级（R1-R14）

| 层 | 规则 | 拦截位 |
|----|------|--------|
| 输入层 | R2前置三查 / R7自主边界 / R14pre_block | pre_tool |
| 执行层 | R3改前备份 / R1反幻觉 | pre+post |
| 输出层 | R4交付铁律 / R5深度审核 / R6沟通风格 / R10真实实现 | post_response |
| 验收层 | R8问责 / R9双模型 / R11循环 / R12SDLC / R13技能 / R14阶段 | post_response |

## 关键infrastructure

| 组件 | 文件 | 行数 | 用途 |
|------|------|------|------|
| rule_enforcer | rule_enforcer.py | 1459 | 14条规则代码级强制 |
| env_loader | env_loader.py | 101 | .env安全加载+${ENV}解析 |
| resilience_patterns | resilience_patterns.py | 442 | 10组件弹性模式(熔断/重试/限流/降级/审计/指标/热加载/干跑) |
| audit_system | audit_system.py | 866 | Scale AI级审计追踪(JSONL/CloudTrail/多线程) |
| error_framework | error_framework.py | 551 | RFC 7807统一错误处理(6子类+装饰器) |
| ministry_abc | ministry_abc.py | 919 | 六部ABC+RoleOrchestrator+WorkflowStateMachine |
| gongbu_impl | gongbu_impl.py | 284 | 工部Playwright真实实现 |
| test suite | 15 test_*.py | -- | 686个pytest 全部通过 |
