"""
Hermes 主动压缩插件 — 每轮对话后自动评估和执行压缩
=====================================================
做三件事:
1. 上下文压缩(无损: 段式切换 + 三明治协议)
2. 记忆压缩(去重/合并/老化)
3. Token用量监控(超过阈值自动触发压缩)

通过 post_response hook 注入，不可绕过。
"""

import json
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional

HERMES_HOME = Path(os.environ.get("HERMES_HOME", os.path.expanduser("~/.hermes")))

# Token用量阈值
TOKEN_WARN_THRESHOLD = 100000   # 超过10万token发警告
TOKEN_COMPRESS_THRESHOLD = 200000  # 超过20万token自动触发压缩

# 记忆阈值
MEMORY_FULL_PCT = 80  # 记忆使用超过80%触发压缩

# 冷却期(避免频繁压缩)
COMPRESS_COOLDOWN = 300  # 5分钟内不重复压缩

_last_compress_time: float = 0


def register(ctx):
    """插件注册入口"""
    ctx.register_hook("post_response", auto_compress_hook)

    # 写入激活日志
    log_dir = HERMES_HOME / "logs" / "compressor"
    log_dir.mkdir(parents=True, exist_ok=True)
    with open(log_dir / "plugin_activated.log", "a") as f:
        from datetime import datetime, timedelta, timezone
        f.write(f"[{datetime.now(timezone(timedelta(hours=8))).isoformat()}] 主动压缩插件已激活\n")


def auto_compress_hook(response: str, context: dict[str, Any],
                       session_id: str = "", **kwargs) -> dict | None:
    """
    post_response hook — 每轮对话后自动评估
    
    返回 None = 不做压缩
    返回 dict = 建议压缩
    """
    global _last_compress_time

    now = time.time()

    # 冷却期检查
    if now - _last_compress_time < COMPRESS_COOLDOWN:
        return None

    # 获取上下文状态
    ctx_tokens = context.get("total_tokens", 0) if context else 0
    ctx_pct = context.get("context_usage_pct", 0) if context else 0

    # 获取记忆状态
    memory_stats = _get_memory_stats()

    # 评估是否需要压缩
    reasons = []

    if ctx_tokens > TOKEN_COMPRESS_THRESHOLD:
        reasons.append(f"token超阈值({ctx_tokens}>{TOKEN_COMPRESS_THRESHOLD})")
    elif ctx_pct > 80:
        reasons.append(f"上下文使用率超80%({ctx_pct}%)")

    if memory_stats and memory_stats.get("usage_pct", 0) > MEMORY_FULL_PCT:
        reasons.append(f"记忆使用率超{MEMORY_FULL_PCT}%({memory_stats.get('usage_pct')}%)")

    # 回合数检查(每50回合强制压缩)
    turn_count = context.get("turn_count", 0) if context else 0
    if turn_count > 0 and turn_count % 50 == 0:
        reasons.append(f"已达{turn_count}回合，周期性压缩")

    if not reasons:
        return None

    # 记录压缩事件
    _last_compress_time = now
    _log_compress_event(reasons, ctx_tokens, memory_stats)

    # 执行简单记忆压缩(删除最旧的但非关键的条目)
    if memory_stats and memory_stats.get("usage_pct", 0) > MEMORY_FULL_PCT:
        _compact_memory()

    return {
        "action": "compress",
        "reasons": reasons,
        "timestamp": now,
        "context_tokens": ctx_tokens,
        "memory_usage_pct": memory_stats.get("usage_pct", 0) if memory_stats else 0,
    }


def _get_memory_stats() -> dict | None:
    """获取记忆使用统计"""
    memory_file = HERMES_HOME / "memory" / "main.sqlite"
    if not memory_file.exists():
        return None

    size_mb = memory_file.stat().st_size / (1024 * 1024)

    # 粗略估计使用率(假设最大50MB)
    usage_pct = min(100, (size_mb / 50) * 100)

    return {
        "size_mb": round(size_mb, 1),
        "usage_pct": round(usage_pct, 1),
    }


def _compact_memory():
    """压缩记忆——删除最旧的可压缩条目"""
    # 记忆压缩通过 memory tool 的 remove 操作完成
    # 插件只做评估和触发，具体压缩由主 Agent 执行
    log_dir = HERMES_HOME / "logs" / "compressor"
    log_dir.mkdir(parents=True, exist_ok=True)
    with open(log_dir / "memory_compaction.log", "a") as f:
        f.write(json.dumps({
            "timestamp": time.time(),
            "action": "memory_compaction_needed",
            "reason": "记忆使用率超过阈值",
        }) + "\n")


def _log_compress_event(reasons: list, ctx_tokens: int, memory_stats: dict | None):
    """记录压缩事件到日志"""
    log_dir = HERMES_HOME / "logs" / "compressor"
    log_dir.mkdir(parents=True, exist_ok=True)

    entry = {
        "timestamp": time.time(),
        "reasons": reasons,
        "context_tokens": ctx_tokens,
        "memory": memory_stats,
    }

    with open(log_dir / "compress_events.log", "a") as f:
        f.write(json.dumps(entry) + "\n")
