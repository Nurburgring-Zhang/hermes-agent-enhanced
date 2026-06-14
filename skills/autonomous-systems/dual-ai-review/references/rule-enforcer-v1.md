# 规则强制执行引擎 v1 — 设计与注入记录

## 背景

2026-06-12 审计发现：SOUL.md 和 AGENTS.md 中的"反幻觉铁律""前置三查""改前备份"
"交付铁律""深度审核"只有文字说明，无代码强制。执行AI遵守靠自觉 → 经常失效。

## 架构：4层注入强制链

```
model_tools.py (进程启动)
    └→ 任何Hermes进程 import 时自动加载 rule_enforcer
    └→ 不依赖对话/cron/子Agent等特定路径
            ↓
conversation_loop.py (对话前PRE)
    └→ 每次LLM调用前执行 R2 前置三查
    └→ 结果注入到 effective_system
            ↓
run_agent.py (对话后POST)
    └→ 每次对话完成后执行 R1+R4 检查
    └→ 记录到日志，不作拦截（不破坏用户体验）
            ↓
agent_enhancement_manager.py (插件注册)
    └→ 注册为第67个插件(both模式)
    └→ 所有对话都触发
```

## 注入点精确坐标

### model_tools.py
行 ~1295（文件末尾）：`_force_init_all_enhancements()` 函数的第5段。使用
`importlib.util.spec_from_file_location` 加载 `rule_enforcer.py`。运行日志：
`logger.info("rule_enforcer loaded — 5 rules active: R1反幻觉 R2前置三查 R3改前备份 R4交付铁律 R5深度审核")`

### conversation_loop.py
行 ~680（在 existing PRE hook 之后）：
```python
# ── R2: 前置三查 ──
try:
    _sys.path.insert(0, str(Path.home() / ".hermes" / "scripts"))
    from rule_enforcer import pre_conversation_hook as _r2_hook
    _r2_text = _r2_hook(user_message)
    if _r2_text:
        effective_system = (effective_system + "\n\n" + "[" + _r2_text + "]").strip()
except Exception:
    pass
```

### run_agent.py
行 ~5135（在 existing POST hook 之后）：
```python
# ── R1+R4: 反幻觉+交付铁律 — 对话后强制检查 ──
try:
    import sys as _sys2; from pathlib import Path as _Path2
    _sys2.path.insert(0, str(_Path2.home() / ".hermes" / "scripts"))
    from rule_enforcer import post_conversation_hook as _r_hook
    _final_response = result.get("final_response", "")
    _r_hook(user_message, _final_response)
except Exception:
    pass
```

## 规则详细信息

### R1 反幻觉铁律
- 类: `AntiHallucination`
- 拦截点: `post_tool_intercept` + `post_response_intercept`
- 检测模式:
  - 推测性语言正则: "应该(是|有|在)"、"可能(是|有|在)"、"理论上"、"据我所知"
  - 路径/版本号声明但无来源说明
  - 声称采集N条数据但无对应工具调用
- 处理: warn（记录到日志）

### R2 前置三查
- 类: `PreCheck`
- 拦截点: `pre_conversation_hook`
- 实际执行:
  - `hermes sessions list --limit 10` → 返回历史会话数
  - 检查 `~/.hermes/memories/*.json` 记忆文件
  - skills目录关键词匹配
- 处理: inject到system prompt

### R3 改前备份
- 类: `BackupGuard`
- 拦截点: `pre_tool_intercept` + `post_tool_intercept`
- 保护目录: `hermes-agent/`, `scripts/`, `skills/`, `agent/`, `tools/`
- 写工具列表: write_file, patch, delete_file, rename, move, copy, sed, replace
- 处理: 修改前自动cp + SHA256校验 → 验证

### R4 交付铁律
- 类: `DeliveryEnforcer`
- 拦截点: `post_response_intercept`
- 检测模式:
  - "已完成/已实现/全部完成" 声明必须有URL/HTTP状态码/测试结果
  - "已验证"声明必须说明验证方法
  - 无工具调用+200字以上输出(非hello消息)
- 处理: warn

### R5 深度审核
- 类: `DeepAuditEnforcer`
- 拦截点: `post_tool_intercept`
- 检测模式:
  - 审核类tool_name/args（audit/review/审核/审计）必须有 pytest/浏览器/curl等实际运行
  - 仅有代码/结构/格式审查而无运行测试 → warn
- 处理: warn

## 验证结果（2026-06-12）

```bash
# 自检
python3 ~/.hermes/scripts/rule_enforcer.py

# 输出:
# 规则引擎状态: 启用=True | 统计: pass=0 block=0 warn=0
# 5条规则全部注入并激活
# R1反幻觉: 推测性语言→warn
# R2前置三查: session=✅ memory=✅ skill=❌(无匹配)
# R3改前备份: /tmp→pass(非保护目录)
# R4交付铁律: 无证据→warn / 有HTTP状态→pass
# R5深度审核: 仅有代码审查→warn / 含pytest→pass

# 语法检查（5个注入文件全部通过）:
# rule_enforcer.py ✅ model_tools.py ✅
# conversation_loop.py ✅ run_agent.py ✅
# agent_enhancement_manager.py ✅
```

## 已知限制

1. **R2前置三查中skill匹配为关键词模糊匹配** — 未做到语义匹配，依赖文件名包含关键词
2. **R5深度审核只判断tool_name/args中的"审核"类关键词** — 可能会漏掉未用关键词的隐式审核任务
3. **R1的tool_call记录检查只在post_response有效** — 但tool_calls在对话后无法获取全量
4. **备份在shutil.copy2层面** — 对大二进制文件(directory/tarball)需要手动备份，不会自动覆盖


## v1.0补丁记录（2026-06-12）

### 补丁1: tool_executor.py 动态import修复

**问题**: 子Agent在tool_executor.py中写死了 `from agent.rule_enforcer import rule_enforcer`，
但rule_enforcer.py不在agent/目录下（在scripts/下）。运行时报 `ModuleNotFoundError: No module named 'agent.rule_enforcer'`，
导致所有terminal工具调用失败。

**修复**: 改用 importlib.util.spec_from_file_location 动态加载：
```python
from pathlib import Path
import importlib.util
_rule_enforcer_spec = importlib.util.spec_from_file_location(
    "rule_enforcer",
    str(Path.home() / ".hermes" / "scripts" / "rule_enforcer.py")
)
if _rule_enforcer_spec and _rule_enforcer_spec.loader:
    _rule_enforcer_mod = importlib.util.module_from_spec(_rule_enforcer_spec)
    _rule_enforcer_spec.loader.exec_module(_rule_enforcer_mod)
    rule_enforcer = _rule_enforcer_mod
else:
    rule_enforcer = None
```
Pyright警告`rule_enforcer可能为None`（pre_tool_intercept/post_tool_intercept的member access）是正常的，
运行时脚本路径一定存在，不会走到None分支。

### 补丁2: pre_tool_intercept/post_tool_intercept返回值比较修复

**问题**: rule_enforcer.pre_tool_intercept()返回dict（如 `{"action": "pass"}`），
但tool_executor.py中比较写成了 `_pre_result != "pass"`（字符串与dict比较永远为真）。
导致每次工具调用都触发 `RuntimeError("Tool blocked by rule")`。

**修复**: 在4个并发路径和2个顺序路径的共6处拦截点中，将比较逻辑改为：
```python
_pre_action = _pre_result.get("action", "pass") if isinstance(_pre_result, dict) else "pass"
if _pre_action in ("warn", "block"):
    # 拦截
```

**教训**: 当系统中有"规则引擎"这类模块时，三件事必须同时验证：
1. import路径正确（否则ModuleNotFoundError）
2. 返回值类型匹配（否则所有调用都报错/都通过）
3. 拦截逻辑是正向逻辑（pass才放行）而非反向逻辑（非pass才拦截）

## 关于"文档规则 vs 代码强制"的经验

**核心教训（2026-06-11 paradigm shift）：**

以前认为"把规则写进SOUL.md，执行AI会主动遵守"。
实际发现：执行AI赶进度时会跳过、会忘记、会给自己豁免。

2026-06-12 范式转换：
- SOUL.md中的每一条"必须遵守"的规则 ≈ 一条待实现的代码hook
- 规则转化成 `pre_tool_intercept` / `post_tool_intercept` / `post_response_intercept`
  / `pre_conversation_hook` / `post_conversation_hook` 之一
- 如果一条规则写进SOUL.md后需要执行AI"记住"才能遵守 → 它迟早会失效
- 如果一条规则写成系统插件hook → 不需要任何人记住，它自动生效

**判断方法：**
- 犹豫"这个要不要守" → 说明应该写成hook不是文字
- "忘记执行"一条规则 → 说明需要一条新的强制代码路径
