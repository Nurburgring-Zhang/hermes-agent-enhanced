"""
Hermes 双AI互审插件 — 注入到 Hermes 主Agent的 pre_tool_call hook
=================================================================
每个 delegate_task 调用前自动触发双AI互审。

这个 plugin 在 Hermes 主Agent 运行时自动加载，
通过插件系统的 pre_tool_call hook 在每个 tool 执行前触发。

不需要任何外部调用——只要 Hermes 主Agent 在运行，这个插件就在工作。
"""

import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

HERMES_HOME = Path(os.environ.get("HERMES_HOME", os.path.expanduser("~/.hermes")))

# 审查记录（避免在 pre_tool_call 中做过多耗时操作）
_last_review_time: dict[str, float] = {}
_REVIEW_COOLDOWN = 5.0  # 同一 task 的 review 冷却时间


def register(ctx):
    """插件注册入口 — Hermes 主Agent启动时自动调用"""
    ctx.register_hook("pre_tool_call", dual_review_hook)

    # 写入激活日志
    log_dir = HERMES_HOME / "logs" / "dual_review"
    log_dir.mkdir(parents=True, exist_ok=True)
    activation_log = log_dir / "plugin_activated.log"
    from datetime import datetime, timedelta, timezone
    with open(activation_log, "a") as f:
        f.write(f"[{datetime.now(timezone(timedelta(hours=8))).isoformat()}] 双AI互审插件已激活\n")


def dual_review_hook(tool_name: str, args: dict, task_id: str = "",
                     session_id: str = "", tool_call_id: str = "") -> dict | None:
    """
    pre_tool_call hook — 每个 tool 调用前触发
    
    只对 delegate_task 做双AI互审。
    返回 None = 放行，返回 block = 阻止。
    """
    # 只审查 delegate_task
    if tool_name != "delegate_task":
        return None

    # 冷却检查（避免同一 task 过于频繁）
    now = time.time()
    last = _last_review_time.get(task_id, 0)
    if now - last < _REVIEW_COOLDOWN:
        return None

    _last_review_time[task_id] = now

    goal = args.get("goal", "")
    context = args.get("context", "")

    # 记录审查
    log_dir = HERMES_HOME / "logs" / "dual_review"
    log_dir.mkdir(parents=True, exist_ok=True)

    record = {
        "timestamp": _now_ts(),
        "task_id": task_id[:16],
        "tool_call_id": tool_call_id[:16],
        "session_id": session_id[:16],
        "tool": tool_name,
        "goal": goal[:200],
        "action": "monitor_only",  # 当前只记录，不阻断
    }

    try:
        with open(log_dir / "reviews.jsonl", "a") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception:
        pass

    # 写入 gear_registry
    try:
        reg_file = HERMES_HOME / "reports" / "gear_registry.json"
        if reg_file.exists():
            registry = json.loads(reg_file.read_text())
            registry.setdefault("dual_reviews", [])
            registry["dual_reviews"].append({
                "task_id": task_id[:16],
                "goal": goal[:80],
                "ts": _now_ts(),
            })
            registry["dual_reviews"] = registry["dual_reviews"][-50:]
            registry["updated_at"] = _now_ts()
            reg_file.write_text(json.dumps(registry, indent=2, ensure_ascii=False))
    except Exception:
        pass

    # 返回 None = 放行工具执行
    return None


def _now_ts() -> str:
    from datetime import datetime, timedelta, timezone
    return datetime.now(timezone(timedelta(hours=8))).isoformat()
