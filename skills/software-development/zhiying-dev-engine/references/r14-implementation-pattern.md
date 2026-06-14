# R14 三阶段开发铁律 — 代码级实现模式

## 架构概述

R14 通过 `rule_enforcer.py` 中的 `ThreePhaseDevEnforcer` 类实现。它不是关键词匹配，而是基于真实产出证据的阶段验证 + pre_tool级别阻断。

## 核心设计模式

### 1. 类结构

```python
class ThreePhaseDevEnforcer:
    PHASE_1_STEPS = [...]           # 9步定义
    PHASE_2_MIN_ROUNDS = 3          # 第二阶段最少3轮
    STATE_FILE = HERMES / "scripts" / ".phase_state.json"
    _state = None                   # 懒加载
    
    @staticmethod
    def _get_state() -> dict        # 懒加载状态（JSON文件）
    def _save_state()               # 持久化到文件
    def _has_real_output_evidence(response, tool_calls) -> bool  # 真实证据核验
    def pre_tool_block(tool_name, args, task) -> dict  # 前置阻断
    def complete_step(step_name, response, tool_calls) -> dict  # 标记步骤
    def complete_phase1(response, tool_calls) -> dict   # 完成阶段一
    def advance_phase2_round(response, tool_calls) -> dict  # 推进阶段二
    def complete_phase3(response, tool_calls) -> dict   # 完成阶段三
    def get_status() -> dict        # 报告状态
    def reset()                     # 重置（仅格林主人要求时）
```

### 2. 证据检查正则

`_has_real_output_evidence()` 检测四种证据类型：

```python
# ① 产出物引用（文件路径/URL）
r'(?:已写入|已保存|已创建|已生成|已拆解|文件.*?:.*?/[\w/.\-]+|http[s]?://)'
# ② 运行结果（状态码/测试通过/exit_code）
r'(状态码|HTTP.*\d{3}|\d+/\d+.*通过|✅|❌|passed|failed|exit_code)'
# ③ 工具调用（>=2次）
len(tool_calls) >= 2
# ④ 阶段标记
r'\[Phase-\d|\[阶段.完成\]|阶段.*完成|phase.*complete'
```

任一项为True即通过。这取代了旧的关键词扫描。

### 3. pre_tool阻断

注入在 `pre_tool_intercept()` 中，在R7阻断之后、R3备份之前执行。

两条阻断规则：
- **delegate_task + 第一阶段未完成 + 非规划类 → block**
- **delegate_task + 当前是phase3 + phase2不足3轮 → block**

规划类delegate_task（含"调研""检索""规划""分析"）放行。

### 4. post_response自动标记

注入在 `post_response_intercept()` 中，每次LLM响应后：
1. 调用 `_get_real_phase_declaration()` 检测当前阶段（基于真实证据）
2. 如果检测到phase1内容，自动匹配步骤别名并调用 `complete_step()`
3. 日志输出当前阶段

## 注入点

| 注入位置 | 文件 | 函数 | 作用 |
|---------|------|------|------|
| pre_tool | rule_enforcer.py | `pre_tool_intercept()` | delegate_task阻断 |
| post_response | rule_enforcer.py | `post_response_intercept()` | 自动标记+阶段检测 |

## 状态持久化

`.phase_state.json` 结构：
```json
{
    "current_phase": "phase1_complete",
    "phase1": {
        "completed_steps": [{"step": "全网检索", "timestamp": "..."}],
        "completed": true,
        "completed_at": "2026-06-12T22:00:00"
    },
    "phase2": {"rounds": 0, "completed": false},
    "phase3": {"rounds": 0, "completed": false},
    "version": 2
}
```

## 已知陷阱

1. **f-string反斜杠** — `f"...{s['key']}..."` 在Python 3.11+中不允许在f-string的 `{}` 内使用反斜杠转义
   - 修复：先提取变量再拼接：`v = s['key']; f"...{v}..."`
2. **正则转义路径** — `Path("/home/administrator")` 在正则中 `.` 需要转义
3. **evidence检查过于严格** — 如果只做了操作没说"已写入"，可能过不了check。在输出中必须包含产出物路径或运行状态码
4. **日志卷标错误** — `get_report()` 中的 `get_status()` 返回的是 `completed_steps` number（整数），在f-string中可以直接用
