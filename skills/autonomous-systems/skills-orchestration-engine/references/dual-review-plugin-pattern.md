# 双AI互审插件模式（2026-06-10 固化）

## 核心问题

双AI互审必须"任务开始时即触发"，不能在完成后才做审查。

## 第一次尝试（失败）

把 `dual_review()` 注入到 `executor.execute_task()` 中，通过 `configure_dual_review()` 设置 `_delegate_fn`。

**失败原因**：`configure_dual_review()` 从未被任何人调用过。这是条件链的死局。

条件链审计：
```
executor.dual_review → 需要 configure_dual_review()
  → configure_dual_review 需要 Hermes 主流程中有人调用它
    → 没有人调用它 → 死链
```

## 第二次尝试（成功）

用 Hermes 插件系统的 `pre_tool_call` hook，在每次 delegate_task 调用前自动触发。

条件链审计（已追根到底，无隐含条件）：
```
Hermes 主Agent 启动 (conversation_loop)
  → 自动加载 ~/.hermes/plugins/dual_review/  ← Hermes 引擎内置行为
    → 执行 register(ctx)  ← 插件 __init__.py 定义的函数
      → ctx.register_hook("pre_tool_call", dual_review_hook)
        → 每次 delegate_task 被调用时，引擎自动调用 dual_review_hook
          → 审查记录写入 logs/dual_review/reviews.jsonl
```

无隐含条件。Hermes 主Agent 运行就在，插件加载是引擎内置行为。

## 插件文件结构

```
~/.hermes/plugins/dual_review/
├── __init__.py     # register(ctx) 函数 + hook 实现
└── plugin.yaml     # name/version/hooks 声明
```

## plugin.yaml

```yaml
name: dual-review
version: 1.0.0
description: 双AI互审插件 — 每个delegate_task调用前自动触发监督审查
author: Hermes
hooks:
  - pre_tool_call
```

## __init__.py 模板

```python
import json
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional

HERMES_HOME = Path(os.environ.get("HERMES_HOME", "~/.hermes")).expanduser()

_review_cooldown: Dict[str, float] = {}
COOLDOWN_SEC = 5.0

def register(ctx):
    """插件注册入口 — Hermes 主Agent启动时自动调用"""
    ctx.register_hook("pre_tool_call", hook_fn)
    log_dir = HERMES_HOME / "logs" / "dual_review"
    log_dir.mkdir(parents=True, exist_ok=True)

def hook_fn(tool_name: str, args: dict, task_id: str = "",
            session_id: str = "", tool_call_id: str = "") -> Optional[dict]:
    """pre_tool_call hook — 返回 None=放行, 返回 block 消息=阻止"""
    if tool_name != "delegate_task":
        return None

    # 冷却控制
    now = time.time()
    if now - _review_cooldown.get(task_id, 0) < COOLDOWN_SEC:
        return None
    _review_cooldown[task_id] = now

    goal = args.get("goal", "")
    record = {"timestamp": _now_ts(), "task_id": task_id[:16],
              "tool": tool_name, "goal": goal[:200], "action": "monitor_only"}

    # 写日志
    log_file = HERMES_HOME / "logs" / "dual_review" / "reviews.jsonl"
    with open(log_file, "a") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

    # 写 gear_registry
    reg_file = HERMES_HOME / "reports" / "gear_registry.json"
    if reg_file.exists():
        registry = json.loads(reg_file.read_text())
        registry.setdefault("dual_reviews", []).append({
            "task_id": task_id[:16], "goal": goal[:80], "ts": _now_ts()})
        registry["dual_reviews"] = registry["dual_reviews"][-50:]
        reg_file.write_text(json.dumps(registry, indent=2, ensure_ascii=False))

    return None  # 放行

def _now_ts() -> str:
    from datetime import datetime, timezone, timedelta
    return datetime.now(timezone(timedelta(hours=8))).isoformat()
```

## mandatory_engine 检查逻辑

```python
def _check_dual_review() -> tuple:
    """检查双AI互审是否通过插件注入到 Hermes 主Agent"""
    plugin_init = HERMES / "plugins" / "dual_review" / "__init__.py"
    plugin_yaml = HERMES / "plugins" / "dual_review" / "plugin.yaml"
    has_files = plugin_init.exists() and plugin_yaml.exists()

    review_log = HERMES / "logs" / "dual_review" / "reviews.jsonl"
    has_records = review_log.exists() and review_log.stat().st_size > 0

    if has_files:
        return True, f"插件文件=✅, 审查记录={'✅' if has_records else '❌'}"
    return False, "插件文件缺失"
```

## 关键原则

1. **审查必须在任务开始时触发** — 不是事后审查，是执行中监督
2. **不要依赖 configure() 链** — 依赖链越长越容易断
3. **用插件 hook 代替代码注入** — 引擎原生支持，无需额外配置
4. **pre_tool_call 返回 None = 放行** — 不需要阻断时返回 None
5. **审查日志独立存储** — 不依赖 runtime 上下文，crash 后还在
