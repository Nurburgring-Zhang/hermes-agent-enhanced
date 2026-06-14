# Hermes 系统底层插件架构概述

## 插件作为"技术锁"

Hermes 的插件系统通过 hook 机制注入到 Agent 主循环。这是**唯一能让规则变成强制执行的路径**。

## 当前已注册的系统级插件

| 插件 | Hook | 功能 | 创建时间 |
|------|------|------|----------|
| `dual_review` | pre_tool_call | 双AI互审 | 较早 |
| `model_router` | post_tool_call | 模型路由自动切换 | 2026-06-11 |
| `force_compressor` | pre_context_load + post_tool_call | 强制上下文压缩 | 2026-06-11 |

## 插件文件位置

所有插件都在 `~/.hermes/plugins/<name>/__init__.py`。每个插件有独立的日志目录 `~/.hermes/logs/<name>/`。

## 插件激活生命周期

1. 插件文件存在 → Hermes 启动时自动加载 `register()` 函数
2. `register()` 调用 `ctx.register_hook(hook_name, handler)` → hook 注入
3. 每次触发 hook → handler 被调用 → 决定是否拦截/转换/记录
4. cron 定时检测 → 如果发现插件未激活(日志文件过期)，告警

## 关键原则

- **规则写进SOUL.md ≠ 已执行。** 必须有对应的插件代码或 cron 脚本。
- **SOUL.md 中的"不可绕过"条款只对 Agent 有约束力，对系统层面无效。** 真正的"不可绕过"是 cron 每1分钟检测插件文件是否存在+日志新鲜度。
- **先写插件代码，再写规则文档。** 插件是执行层，SOUL.md 是文档层。
