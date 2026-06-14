---
name: force-compressor
description: 强制上下文压缩插件 — 通过pre_context_load + post_tool_call双hook注入，每轮对话开始前强制注入context_packer压缩指令集，每5轮/每30分/每日03:00三级压缩。不可绕过。
version: 1.0.0
tags: [compression, context-optimization, token-saving, plugin, hook, pre-context-load]
domain: autonomous-systems
triggers:
  - "压缩"
  - "上下文"
  - "token"
  - "记忆压缩"
  - "force_compressor"
  - "context_packer"
  - "上下文超限"
  - "对话被截断"
  - "无损压缩"
---

# 强制上下文压缩系统 v1.0

## 核心原则

**压缩不是"需要时再做"，是每轮对话开始前自动执行。**

## 架构

### 双hook注入路径

```
pre_context_load → 对话开始前: 强制读 context_packer.py 产出, 注入压缩指令集
post_tool_call  → 每5轮: 差分压缩 | 每30分: 统计压缩 | 每日03:00: 归档压缩
```

### 插件文件

位置：`~/.hermes/plugins/force_compressor/__init__.py`

```python
def register(ctx):
    ctx.register_hook("pre_context_load", force_compress_context_hook)
    ctx.register_hook("post_tool_call", post_tool_compress_hook)
```

### 三级压缩策略

| 级别 | 触发 | 方法 | 延迟要求 |
|------|------|------|---------|
| Level 1 | 每5轮对话 | 差分压缩(仅存变化部分) | <50ms |
| Level 2 | 每30分钟 | 基于频率和重要性的选择性压缩 | <200ms |
| Level 3 | 每日03:00 | 完整归档+老化清理(7天) | 可接受较长延迟 |

### 无损保证

每次压缩生成 SHA256 校验和。下次加载时验证校验和，发现不一致自动回滚。

## 前置依赖

`context_packer.py` 脚本必须存在且可运行：

```bash
ls -la ~/.hermes/scripts/context_packer.py
# crontab 中应有: * * * * * python3 scripts/context_packer.py general
```

`force_compressor` 插件不直接生成压缩包——它读取 `context_packer.py` 的产出(`reports/context_pack.json`)并注入到对话上下文中。

## 验证

```bash
# 插件是否激活
test -f ~/.hermes/logs/compressor/plugin_activated.log && echo "ACTIVE" || echo "NOT ACTIVE"

# compression日志
tail -3 ~/.hermes/logs/compressor/compress_events.log 2>/dev/null

# context_packer是否在运行(每1分钟)
cat ~/.hermes/reports/context_pack.json 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'规则:{len(d.get(\"rules\",[]))}, token:{d.get(\"packed_tokens\",d.get(\"estimated_tokens\",0))}')"

# cron心跳
hermes cron list | grep -i compress
```

## 集成位置

- 插件：`~/.hermes/plugins/force_compressor/__init__.py`
- 日志：`~/.hermes/logs/compressor/`
- 压缩包：`~/.hermes/reports/context_pack.json`
- 配置文件：`~/.hermes/config.yaml` -> compression 节

## 已知陷阱

### 🔴 陷阱1：压缩脚本在跑但产出没人用

之前的 context_packer.py 通过 cron 每1分钟正确运行，产出 context_pack.json。但没有任何机制把这个产出注入到 Hermes 的 token 预算中——压缩包生成得很好，但 Hermes 从不读它。

修复：force_compressor 插件通过 pre_context_load hook 在每轮对话开始前强制读取压缩包并注入。

### 🔴 陷阱2：skill定义很好的压缩方案但系统不执行

lossless-claw-compression 和 lossless-claw-v2 skill 定义了完整的压缩策略——但它们是 SKILL.md 文件（给执行AI看的规则手册），不是系统代码。除非执行AI主动加载这些 skill，否则压缩不会发生。

修复：把压缩逻辑写成系统插件 hook（force_compressor），不需要执行AI"记住"加载 skill。

### 🔴 陷阱3：记忆满了但自动压缩不触发

记忆只有 2,200 字符上限。满了之后 `memory.add()` 操作全部失败。force_compressor 的 post_response hook 在记忆超过 80% 时触发记忆紧凑化——但紧凑化只能删除最旧条目，不能自动合并去重。

修复：当记忆满时手动删除无用的旧条目用 `memory(action="remove")`。这不是插件能力而是用户操作。
