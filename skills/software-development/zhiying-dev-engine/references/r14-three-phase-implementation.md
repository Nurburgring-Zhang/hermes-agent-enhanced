# R14 三阶段开发铁律 — 商用级实现参考
## 基于2026-06-12 rule_enforcer.py 改造实战

## 代码位置
`~/.hermes/scripts/rule_enforcer.py` → class `ThreePhaseDevEnforcer` (~1200行)

## 架构

### 两个拦截点

1. **pre_tool_block()** — 在pre_tool_intercept中调用。阻塞级别的阻断。
   - 第一阶段未完成 + 非规划类delegate_task → **block**（中断执行）
   - 第二阶段不足3轮 + 进入第三阶段delegate_task → **block**
   - 允许第一阶段规划类任务（含"调研""检索""搜索""research""规划""分析"关键词）通过

2. **post_response_intercept()** — 每次响应后自动检测阶段进展。
   - `_get_real_phase_declaration()` — 基于真实产出证据检测当前阶段
   - 自动标记第一阶段已完成步骤（按9步别名匹配+证据检查）
   - 状态持久化到 `scripts/.phase_state.json`

### 真实产出证据检查 (`_has_real_output_evidence()`)
必须满足以下至少一项：
- 文件/路径/URL引用（产出物引用）
- HTTP状态码/测试通过报告（运行结果）
- delegate_task/tool_call的实际调用记录（>=2次）
- `[Phase-N]` / `[阶段完成]` 标记

关键词匹配不再单独作为阶段完成的证据。

### 三阶段状态持久化
```json
{
  "current_phase": "phase1",
  "phase1": { "completed_steps": [{"step":"全网检索", "timestamp":"..."}], "completed": false },
  "phase2": { "rounds": 0, "last_benchmark": null, "completed": false },
  "phase3": { "rounds": 0, "completed": false }
}
```

## 使用方式

### 查看当前阶段状态
```python
from rule_enforcer import get_report
print(get_report())
```

### 重置状态（仅格林主人要求时）
```python
from rule_enforcer import ThreePhaseDevEnforcer
ThreePhaseDevEnforcer.reset()
```
注意：reset() 会删除 `scripts/.phase_state.json`

### SOUL.md对应部分
在SOUL.md中已有完整的三阶段描述（v3.2），位置在"智影开发引擎"之前。

## 实战教训

1. **f-string的转义陷阱**：在get_report()中的f-string嵌套三元表达式+字典访问时，反斜杠转义导致SyntaxError。
   解决方案：提前将嵌套值赋给局部变量。

2. **state引用必须在post_response_intercept中初始化**：R14的state是懒加载的，在post_response_intercept中要先调用
   `state = ThreePhaseDevEnforcer._get_state()` 再使用state变量。

3. **第一阶段自动标记不能覆盖已完成步骤**：alias匹配时，先检查 `existing` 列表中有没有同一步骤，有则跳过。
