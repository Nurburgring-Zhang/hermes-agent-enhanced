# Hermes SDLC Enforcer — Dynamic Workflows集成参考

## 概述
从2026-06-09起，Hermes Dynamic Workflows自动向每个task注入SDLC流程强制。
代码位置：`workflows/active_engine.py` 的 `SDLCEnforcer` 类。
注入点：`workflows/executor.py` 的 `execute_task()` 函数（params.update(sdlc_context)）。

## 自动SDLC流程

| 任务类型 | 触发关键字 | SDLC阶段 |
|---------|-----------|---------|
| 修复类 | bug/fix/修复/补丁 | 调研→修复→测试→交付(4步) |
| 新建类 | new/create/新建/写/实现 | 调研→设计→编码→测试→审核→完善→交付(7步) |
| 审核类 | review/审核/审计/检查 | 审核→报告(2步) |
| 调研类 | search/调研/研究 | 调研→报告(2步) |
| 默认类 | 其他 | 完整7步SDLC |

## 注入内容

每个task的context中自动注入：
```json
{
  "_sdlc_enforced": true,
  "_sdlc_flow": "调研阶段...设计阶段...编码阶段...测试阶段...审核阶段...完善阶段...交付阶段",
  "_mandatory_rules": "执行前先调研...先出方案再编码...写测试...自审核...至少完善一轮...最终验证"
}
```

## 与手动SDLC的关系

- **手动SDLC**（本skill描述的）: 当Hermes主Agent直接执行软件工程任务时使用
- **自动SDLC**（active_engine.py的SDLCEnforcer）: 当Dynamic Workflows的task执行时自动注入
- **两者互补**：自动SDLC是手动SDLC的编程化强制版本

## preflight强制三查补充

Dynamic Workflows的每个phase执行前自动运行preflight.py，执行：
1. session_search历史回顾
2. memory/fact_store经验检查
3. skill自动预加载（基于类别映射）
4. web_search全网方案检索
5. delegate_task架构师评估

这5步应在手动SDLC的"调研阶段"之前自动完成。
