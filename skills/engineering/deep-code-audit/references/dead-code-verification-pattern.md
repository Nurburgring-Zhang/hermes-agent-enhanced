# 死代码验证模式（Dead-Code Verification Pattern）

## 问题

审计发现大量"已实现但从未执行"的代码。典型情况：
- `rule_enforcer.py`: 27KB, 13条规则, 全部编译通过 — 但没有任何运行时路径调用它
- `tool_executor.py`: 插入了`pre_tool_intercept()`调用但返回值比较逻辑是`!= "pass"`而非`dict.get("action")`——导致所有工具被错误拦截

根本原因：代码能编译通过 + 逻辑看起来完整 ≠ 实际执行路径中存在。

## 验证方法

### 1. 调用链追溯

```
模块A.import → import语句 → 模块B被导入
模块A.调用 → 函数调用 → 模块B.方法被执行
```

对每个疑似假实现，沿着调用链向上追溯：
```bash
# 找到谁调用了这个函数
grep -rn "pre_tool_intercept\|rule_enforcer" . --include="*.py" | grep -v __pycache__
# 如果只有定义的文件自己引用自己 → 死代码
# 如果有其他文件import了 → 检查是否真的执行了该import路径
```

### 2. 三路信号确认

| 信号 | 方法 | 假阳条件 |
|------|------|---------|
| import存在 | `grep -rn 'from X import Y'` | 模块从未被主入口加载 |
| 模块被加载 | `python3 -c "from X import Y; print(Y.__name__)"` | 导入了但从未调用 |
| 方法被执行 | 插入日志/print后运行真实场景 | 分支条件为假导致跳过 |

### 3. 代码规模 vs 调用深度检查

```bash
# 发现大文件但调用者很少的模式
for f in $(find . -name "*.py" -size +10k | sort); do
  module=$(basename $f .py)
  calls=$(grep -rn "$module" . --include="*.py" | grep -v __pycache__ | grep -v "$f" | wc -l)
  [ "$calls" -lt 3 ] && echo "⚠️ $module: $(wc -c < $f)bytes 仅$calls个外部引用"
done
```

### 4. 注入点返回值格式验证

这是最容易被忽略的——函数**定义了**但**返回值类型假设错误**。

```python
# ❌ 错误假设: pre_tool_intercept返回字符串
if _pre_result != "pass":  # 实际返回的是dict: {"action":"pass","reason":""}
    # 永远为真! 所有工具都被拦截

# ✅ 验证返回值格式
result = rule_enforcer.pre_tool_intercept(name, args)
action = result.get("action", "pass") if isinstance(result, dict) else "pass"
if action in ("warn", "block"):
    # 正确的拦截逻辑
```

### 5. 重启验证（最重要）

Python进程会缓存已导入的模块。即使你修复了文件，如果服务没有重启，**旧代码仍在运行**。

```bash
# 必须: 完全杀死旧进程
kill $(lsof -ti:PORT) 2>/dev/null
sleep 2  # 等待端口释放

# 然后: 启动新进程验证
python3 -c "import uvicorn; uvicorn.run(app, host='127.0.0.1', port=PORT)"

# 最后: curl所有端点验证200
for path in / /api/v1/health /api/xxx; do
  curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:PORT$path
done
```

**不重启就测试 = 测试旧代码。** 即使文件已经patch了，Python活的进程不会重新加载。

## 实战案例

### 案例1: rule_enforcer.py 27KB死代码

SOUL.md声明了R1-R5 5条规则全部代码强制，
但整个27KB的`rule_enforcer.py`从未被任何import路径加载。

**追溯链**:
```
model_tools.py(进程启动层): 加载了dual_review_engine, agent_enhancement_manager
                         但没加载rule_enforcer

agent_enhancement_manager.py(67插件注册表): 注册了"rule_enforcer"
                                         但safe_hook_pre_conversation()不做_try_load

conversation_loop.py(R2注入): import rule_enforcer → 文件名在系统路径找不到
                             静默失败(except: pass) → 无日志
```

**修复**: 在agent_enhancement_manager和model_tools的启动加载链中分别添加 `_try_load("rule_enforcer")`。

### 案例2: tool_executor.py pre_tool_intercept返回值错误

修复了rule_enforcer的加载后，所有工具报错`{"error": {"action": "pass"}}`。

**根因**: `pre_tool_intercept`返回`dict{"action":"pass"}`，但比较逻辑是`if _pre_result != "pass"` — dict永远不等于"pass"，所以所有工具被拦截。

**修复**: 改为提取dict中action值再比较。

## 总结清单

修复"死代码强制执行"后，必须依次验证：
1. ✅ 语法检查通过
2. ✅ import路径可达
3. ✅ 方法签名匹配
4. ✅ 返回值类型匹配调用方的期望
5. ✅ 重启进程（必须！清理缓存）
6. ✅ curl所有端点返回200
