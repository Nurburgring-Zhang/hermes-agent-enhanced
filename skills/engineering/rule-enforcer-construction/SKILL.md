---
name: rule-enforcer-construction
description: SOUL.md规则强制执行引擎构建方法 — 将文字规则转化为可执行的代码级拦截逻辑。覆盖规则分析→检测模式设计→注入点选择→返回值类型验证→全链路测试的完整工作流。适用于所有需要"规则写了就必须真执行"的场景。
triggers:
  - 用户要求"把技能固化成代码"
  - 用户要求"规则不能只是声明，必须代码强制"
  - 构建规则强制执行引擎
  - 将SOUL.md/AGENTS.md中的规则逐个实现为可运行代码
  - 用户说"规则写了但没执行=没写"
  - 审计发现声明性规则未被实际执行
---

# 规则强制执行引擎构建方法

## 核心理念

**SOUL.md/AGENTS.md中的每条规则，必须有代码级别的强制执行。** 纯文字声明=没写。

规则强制执行引擎 = 检测逻辑（发现违规）+ 注入点（触发检测）+ 响应机制（拦截/警告/记录）

## 总体架构

```
SOUL.md规则
    ↓ 分析 → 每条规则定义检测逻辑
    ↓ 设计 → 确定注入点（何时触发检测）
    ↓ 实现 → 写Python检测函数
    ↓ 注入 → 挂到系统生命周期钩子上
    ↓ 验证 → 确保检测真实触发且不影响正常操作
```

## 第一步：规则分析（从文字到检测模式）

每条SOUL.md规则需要明确3件事：

| 问题 | 产出 |
|------|------|
| 这条规则"禁止什么"或"要求什么"? | 检测条件 |
| 违规时应该怎么办？ | 响应级别：block/warn/alert |
| 在什么时候检测最合适？ | 注入点选择 |

### 典型规则映射模式

**模式1: 关键词/模式检测** → 适用于沟通风格、禁用词、AI味检测
- 设计：编译正则表达式列表 → 在输出前扫一遍文本
- 示例：R6沟通风格 — `r'赋能|助力|抓手'` → 37个禁用词+4种模糊模式

**模式2: 工具安全分级** → 适用于自主边界、安全操作
- 设计：列出所有敏感工具（rm/del/drop/etc）→ 按危险程度分级
- 示例：R7自主边界 — block级(rm -rf/drop table) / warn级(rm/delete) / alert级(chmod 777)

**模式3: 调用链验证** → 适用于问责、交付验证
- 设计：记录unused outputs → 在交付时检查是否有未使用的产出
- 示例：R8问责 — `_unused_outputs`列表→deliver阶段检查

**模式4: 配置对比** → 适用于双AI互审、模型路由
- 设计：从配置文件中读取实际配置 → 对比预期值
- 示例：R9双模型 — 读取config.yaml的provider列表 → 检查是否有≥2个provider

**模式5: 代码模式扫描** → 适用于降级实现检测
- 设计：识别占位符模式/假实现的代码模式
- 示例：R10真实实现 — `random.uniform|placeholder|TODO|mock|pass|return None|return []`

**模式6: 循环监控** → 适用于循环检测
- 设计：记录工具调用序列 → 检测重复模式
- 示例：R11循环 — 保留最近20条调用记录 → 检查是否有相同name+args重复≥3次

**模式7: 流程步骤检查** → 适用于开发流程
- 设计：检查用户消息中的关键步骤关键词
- 示例：R12智影SDLC — 检查用户消息中是否包含7步SDLC步骤

## 第二步：注入点选择

| 注入点 | 触发时机 | 适用规则 |
|--------|---------|---------|
| `pre_tool_intercept` | 每次工具调用前 | R1反幻觉、R7安全、R11循环 |
| `post_tool_intercept` | 每次工具调用后 | R8问责、R11循环记录 |
| `pre_context_load` | 对话加载时 | R2前置三查 |
| `post_response_intercept` | 每次回复生成后 | R6沟通风格、R10降级检测 |
| `agent_enhancement_manager` plugin | 插件加载生命周期 | R13技能加载 |
| `model_tools.py` 进程启动层 | 服务启动时 | 所有规则的注册加载 |

### 常见注入点陷阱

**陷阱1: 注册了但没加载**
在 `agent_enhancement_manager.py` 的PLUGIN_REGISTRY中添加条目 ≠ 该插件会被加载。
需要在 `safe_hook_pre_conversation()` 或类似方法中显式调用 `_try_load("module_name")`。

**陷阱2: 只注册了一个"主"插件但子规则没对应函数**
所有检测逻辑都应该在同一个文件中定义，但每条规则需要一个独立的函数入口：
```python
def check_communication_style(text): ...
def check_boundary_security(args): ...
def check_accountability(history): ...
```

**陷阱3: 返回值类型不匹配**
**这是最常见的bug！** 如果函数返回 `dict`（如 `{"action":"pass","reason":""}`），调用方必须用 `.get("action")` 提取值再比较，不能用 `!= "pass"` 直接比较（dict永远≠"pass"）。

## 第三步：检测逻辑编程

### 模式1实现：正则检测
```python
import re

# 禁用词列表（精确匹配）
DISABLED_PATTERNS = [
    r'赋能', r'助力', r'抓手', r'闭环', r'颗粒度', r'底层逻辑',
    r'多维度', r'全链路', r'对齐', r'倒逼', r'组合拳', r'方法论',
    r'AIGC', r'垂直领域', r'打造', r'势能', r'壁垒', r'降维打击',
    r'破局', r'私域', r'公域', r'精细化', r'体感',
    r'场景化', r'矩阵', r'高频', r'高质量', r'生态', r'复用',
    r'联动', r'反哺', r'长尾', r'抓手', r'拉动',
    r'一体化', r'双轮驱动',
]

# 模糊模式（非精确匹配）
VAGUE_PATTERNS = [
    r'(经过|多次|反复)(测试|验证|优化|迭代)',  # "经过测试验证"
    r'(很大|极大|显著|明显)(提升|优化|改进|改善)',
    r'(行业|业界)(领先|一流|顶级|前沿)',
    r'(经过|进行)(测试|验证|确认)',
]
```

### 模式2实现：工具安全分级
```python
BLOCK_TOOLS = [
    (r'rm.*\s+-rf', '完全删除'),
    (r'drop\s+table', '删除数据库表'),
    (r'drop\s+database', '删除数据库'),
    (r'mkfs', '格式化磁盘'),
    (r'dd\s+if=', '直接磁盘写入'),
    (r'crontab\s+-r', '删除全部cron'),
    (r'kill\s+-9\s+\-1', '杀死所有进程'),
]

WARN_TOOLS = [
    (r'rm[^_]', '删除文件'),
    (r'delete\b', '删除操作'),
    (r'remove\b', '移除操作'),
    (r'passwd\b', '密码修改'),
    (r'chmod\s+777', '过度权限'),
    (r'useradd', '添加用户'),
    (r'sudo\s+usermod', '用户权限提升'),
    (r'iptables\s+-F', '防火墙清空'),
]

ALERT_TOOLS = [
    (r'wget|curl.*-o', '下载外部文件'),
    (r'systemctl\s+stop', '停止服务'),
    (r'ufw\s+disable', '关闭防火墙'),
    (r'setenforce\s+0', '关闭SELinux'),
]
```

### 模式5实现：降级实现检测
```python
DOWNGRADE_PATTERNS = [
    r'random\.(uniform|randint|random|choice)',
    r'placeholder',
    r'TODO|FIXME|HACK',
    r'mock',
    r'(未实现|待实现|开发中|尚未实现)',
    r'pass\s*#\s*TODO',
    r'return\s+None\s*#\s*TODO',
    r'return\s+\[\]\s*#\s*TODO',
    r'return\s+\{\}\s*#\s*TODO',
    r'return\s+\"\"\s*#\s*TODO',
]
```

## 第四步：注入实现

### pre_tool_intercept 模板
```python
def pre_tool_intercept(tool_name: str, tool_args: dict):
    """在所有工具调用前执行。返回建议action。"""
    # R7: 安全检查
    full_cmd = str(tool_args)
    for pattern, desc in BLOCK_TOOLS:
        if re.search(pattern, full_cmd, re.IGNORECASE):
            return {"action": "block", "reason": f"安全拦截: {desc}",
                    "rule": "R7"}
    for pattern, desc in WARN_TOOLS:
        if re.search(pattern, full_cmd, re.IGNORECASE):
            return {"action": "warn", "reason": f"敏感操作: {desc}",
                    "rule": "R7"}

    # R11: 循环检测
    call_key = f"{tool_name}:{str(tool_args)[:200]}"
    _recent_calls.append((call_key, time.time()))
    similar = sum(1 for c, _ in _recent_calls if c == call_key)
    if similar >= 3:
        return {"action": "warn", "reason": f"检测到循环: {tool_name} 重复{similar}次",
                "rule": "R11"}

    return {"action": "pass", "reason": ""}
```

### post_tool_intercept 模板
```python
def post_tool_intercept(tool_name: str, result: dict):
    """在所有工具调用后执行。记录结果。"""
    # R8: 记录未使用的产出
    if result.get("success") and tool_name in ("write_file", "create_file"):
        _unused_outputs.append({
            "tool": tool_name,
            "time": time.time(),
            "result": result.get("path", "unknown")
        })

    # R11: 记录失败
    if not result.get("success"):
        _recent_calls.append((f"FAIL:{tool_name}", time.time()))
```

### post_response_intercept 模板
```python
def post_response_intercept(response: str):
    """在每次回复生成后执行。检查输出质量。"""
    issues = []

    # R6: 沟通风格检查
    for pattern in DISABLED_PATTERNS:
        if re.search(pattern, response):
            issues.append(f"[R6] 发现禁用词: '{pattern}'")
            break  # 一个就够了

    # R10: 降级检测
    for pattern in DOWNGRADE_PATTERNS:
        if re.search(pattern, response, re.IGNORECASE):
            issues.append(f"[R10] 发现降级表达: '{pattern}'")
            break

    return issues
```

## 第五步：插件注册

在 `agent_enhancement_manager.py` 中注册：

```python
PLUGIN_REGISTRY = [
    # ... 已有67个插件 ...
    ("rule_enforcer", "SOUL.md 规则强制执行引擎（R1-R13）"),
]

# 同时需要在 safe_hook_pre_conversation 中添加：
def safe_hook_pre_conversation(name, content):
    _try_load("rule_enforcer")
    if "rule_enforcer" in sys.modules:
        import rule_enforcer
        if hasattr(rule_enforcer, 'pre_conversation_hook'):
            return rule_enforcer.pre_conversation_hook(name, content)
    return content
```

**不可跳过：** 注册+加载+拦截点 三处都必须有代码。只做注册不做加载=死代码。

## 第六步：全链路验证

### 验证清单

1. ✅ **语法检查** — `python3 -c "import py_compile; py_compile.compile('rule_enforcer.py', doraise=True)"`
2. ✅ **模块导入** — `python3 -c "import sys; sys.path.insert(0,'scripts'); from rule_enforcer import pre_tool_intercept, post_tool_intercept, post_response_intercept"`
3. ✅ **函数可调用** — 调用每个函数并验证返回值类型是dict
4. ✅ **返回值类型匹配** — 上游调用方用 `.get("action")` 而非 `!= "pass"` 比较
5. ✅ **重启验证** — 杀死旧进程 → 启动新进程 → 测试工具调用是否正常
6. ✅ **规则验证** — 逐一测试每条规则的检测逻辑
7. ✅ **不影响正常使用** — 执行 `echo test`、`ls` 等正常命令，确认不被错误拦截

### 测试模板
```python
def test_rule_enforcer():
    import sys
    sys.path.insert(0, 'scripts')
    from rule_enforcer import (
        pre_tool_intercept, post_tool_intercept,
        post_response_intercept, check_communication_style,
        check_boundary_security, check_downgrade
    )

    # R6: 应该检测到AI味
    issues = check_communication_style("赋能产业链数字化转型")
    assert len(issues) > 0, "R6应该检测到'赋能'"

    issues = check_communication_style("今天天气真好")
    assert len(issues) == 0, "R6不应该误报正常文本"

    # R7: 应该拦截危险命令
    result = check_boundary_security("rm -rf /")
    action = result.get("action") if isinstance(result, dict) else "pass"
    assert action in ("block", "warn"), "R7应该拦截rm -rf"

    result = check_boundary_security("echo hello")
    action = result.get("action") if isinstance(result, dict) else "pass"
    assert action == "pass", "R7不应该拦截正常命令"

    # R10: 应该检测到降级实现
    issues = check_downgrade("使用random.uniform生成随机评分")
    assert len(issues) > 0, "R10应该检测到random.uniform"

    print("全部规则验证通过!")
```

## 常见陷阱

### 🔴 陷阱1: 注册表有条目但无加载路径
`PLUGIN_REGISTRY` 中加了条目 ≠ 插件会被加载。必须同时确保：
- `safe_hook_pre_conversation()` 中有 `_try_load("rule_enforcer")`
- 或者 `model_tools.py` 的进程启动层中有 import

**验证**: `grep -rn 'rule_enforcer' agent_enhancement_manager.py | grep -v 'registry\|PLUGIN'`

### 🔴 陷阱2: 返回值类型不匹配（最常见）
如果 `pre_tool_intercept` 返回 `dict`，调用方必须用 `.get("action")` 取值：
```python
# ❌ 错误的比较方式（永远为True）
if result != "pass":
    ...

# ✅ 正确的比较方式
action = result.get("action", "pass") if isinstance(result, dict) else result
if action in ("warn", "block"):
    ...
```

### 🔴 陷阱3: 不重启验证
Python 进程缓存模块。修改文件后不重启 = 旧代码仍在运行。
**必须**: `kill $(lsof -ti) && python3 ...`

### 🔴 陷阱4: 一次性注册太多插件
`agent_enhancement_manager.py` 的 `_try_load` 函数可能被并发调用的 `safe_hook_pre_conversation` 频繁触发。每个插件的 `import` 和 `exec_module` 都有开销。
建议：将多条规则放在同一个 .py 文件中（如 rule_enforcer.py），只注册一个插件入口。

## 已知的规则引擎设计模式

### 三级响应
| 级别 | 含义 | 响应 | 示例 |
|------|------|------|------|
| `block` | 必须阻止 | 返回error，不执行工具 | rm -rf, drop table |
| `warn` | 警告但放行 | 输出warning到log | rm file, delete record |
| `alert` | 通知但放行 | 写入alert队列 | wget, systemctl stop |

### 调用链验证
```
指令 → pre_intercept(检查) → 执行 → post_intercept(记录) → 响应生成 → post_response(审计)
   ↑                       ↑                       ↑
   R7安全检查              R8记录产出              R6/R10检查输出
   R11循环检测                                     R12流程检查
```

### 配套参考

- `references/env-secure-credential-pattern.md` — 审计中发现的API密钥明文存储问题的标准修复方案（${ENV_VAR} + env_loader.py 模式）。适用于所有"config.yaml里有明文密钥"的修复场景。

