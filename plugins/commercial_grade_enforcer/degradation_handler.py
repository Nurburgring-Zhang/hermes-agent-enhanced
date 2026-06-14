"""
R15: 优雅降级处理 — post_tool_call hook
============================================
方法论依据: 二.4 失败处理与韧性
"优雅降级：子任务失败不阻塞全局，尽可能返回部分结果"
+ 三.5 超时与断路器

五级降级策略:
  Level 1: retry_with_backoff（指数退避，max 3次）
  Level 2: degrade — 返回部分结果，不阻塞全局
  Level 3: skip — 非关键子任务跳过
  Level 4: escalate — 升级到HITL人工干预队列
  Level 5: circuit_break — 熔断，停止该模块所有操作
"""

import json
import logging
import sqlite3
import time
from datetime import datetime, timezone
from enum import IntEnum
from pathlib import Path

logger = logging.getLogger(__name__)

HITL_QUEUE_DB = Path("~/.hermes/data/hitl_queue.db").expanduser()
DEGRADATION_LOG = Path("~/.hermes/logs/degradation.jsonl").expanduser()


class DegradationLevel(IntEnum):
    """降级级别"""
    RETRY = 1       # 指数退避重试(max 3次)
    DEGRADE = 2     # 返回部分结果
    SKIP = 3        # 跳过非关键子任务
    ESCALATE = 4    # 升级到HITL人工干预
    BREAK = 5       # 熔断


# ── 关键工具列表（影响全局的工具，不可跳过）──
CRITICAL_TOOLS = {
    "delegate_task",  # 子Agent调用
    "read_file",       # 关键: 读取文件是后续操作的基础
    "terminal",        # 终端命令可能影响系统状态
}

# ── 可降级的工具（非关键，失败可返回部分结果或跳过）──
DEGRADABLE_TOOLS = {
    "write_file",   # 可缓存后重试
    "patch",         # 可回退
    "search_files",  # 可降级为本地搜索
    "process",       # 可超时处理
}


def _init_hitl_db():
    """初始化HITL队列数据库"""
    HITL_QUEUE_DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(HITL_QUEUE_DB))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS hitl_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id TEXT NOT NULL,
            tool_name TEXT NOT NULL,
            error_message TEXT,
            degradation_level INTEGER DEFAULT 4,
            status TEXT DEFAULT 'pending',  -- pending/acknowledged/resolved/expired
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            acknowledged_at TIMESTAMP,
            resolved_at TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_hitl_status
        ON hitl_queue(status, created_at)
    """)
    conn.commit()
    conn.close()


def _push_to_hitl(ctx, tool_name: str, error_msg: str, level: DegradationLevel):
    """将任务推入HITL人工干预队列"""
    _init_hitl_db()
    task_id = getattr(ctx, "task_id", "unknown")

    conn = sqlite3.connect(str(HITL_QUEUE_DB))
    conn.execute(
        """INSERT INTO hitl_queue (task_id, tool_name, error_message, degradation_level)
           VALUES (?, ?, ?, ?)""",
        (task_id, tool_name, error_msg[:500], int(level))
    )
    conn.commit()
    conn.close()

    logger.warning(
        f"[R15-HITL] 已加入人工干预队列: task={task_id} "
        f"tool={tool_name} level={level.name}"
    )


def _log_degradation(ctx, tool_name: str, level: DegradationLevel,
                     error_msg: str, action_taken: str):
    """记录降级事件"""
    DEGRADATION_LOG.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "task_id": getattr(ctx, "task_id", "unknown"),
        "tool": tool_name,
        "degradation_level": level.value,
        "degradation_name": level.name,
        "error": error_msg[:200],
        "action": action_taken,
    }
    with open(DEGRADATION_LOG, "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def handle_failure(ctx, tool_name: str, result):
    """
    post_tool_call hook: 工具调用失败时执行结构化降级策略。
    检查result是否包含错误/异常。
    """
    # 检查是否有错误
    if result is None:
        return None

    result_dict = _extract_error(result)
    if not result_dict:
        return None  # 无错误，放行

    error_msg = result_dict.get("error", str(result))
    task_id = getattr(ctx, "task_id", "unknown")

    # 累加连续失败计数
    consecutive_failures = getattr(ctx, "_consecutive_failures", 0) + 1
    ctx._consecutive_failures = consecutive_failures

    logger.warning(
        f"[R15-降级] tool={tool_name} error='{error_msg[:100]}' "
        f"consecutive_failures={consecutive_failures}"
    )

    # ── 判断降级级别 ──

    # Level 1: RETRY — 尝试重试（前3次失败）
    if consecutive_failures <= 3:
        retry_count = getattr(ctx, f"_retry_count_{tool_name}", 0)
        if retry_count < 3:
            delay = 2 ** retry_count  # 指数退避: 1s, 2s, 4s
            ctx.__setattr__(f"_retry_count_{tool_name}", retry_count + 1)

            _log_degradation(ctx, tool_name, DegradationLevel.RETRY,
                             error_msg, f"指数退避重试(第{retry_count + 1}次, delay={delay}s)")

            logger.info(f"[R15-降级] Level 1 RETRY: {tool_name} -> 第{retry_count + 1}次重试(delay={delay}s)")
            time.sleep(min(delay, 4))  # max delay 4s

            return {
                "retry": True,
                "retry_count": retry_count + 1,
                "delay": delay,
                "original_error": error_msg,
            }

    # Level 2: DEGRADE — 返回部分结果（对于可降级工具）
    if tool_name in DEGRADABLE_TOOLS:
        _log_degradation(ctx, tool_name, DegradationLevel.DEGRADE,
                         error_msg, "返回部分结果/缓存数据")
        logger.info(f"[R15-降级] Level 2 DEGRADE: {tool_name} -> 返回部分结果")
        return {
            "degraded": True,
            "partial_result": True,
            "message": f"{tool_name} 执行失败，已返回部分可用结果",
            "original_error": error_msg,
        }

    # Level 3: SKIP — 跳过非关键工具
    if tool_name not in CRITICAL_TOOLS:
        _log_degradation(ctx, tool_name, DegradationLevel.SKIP,
                         error_msg, "跳过非关键子任务")
        logger.info(f"[R15-降级] Level 3 SKIP: {tool_name} -> 跳过(非关键)")
        return {
            "skipped": True,
            "message": f"{tool_name} 执行失败但已跳过(非关键路径)",
            "original_error": error_msg,
        }

    # Level 4: ESCALATE — 升级到HITL人工干预
    if consecutive_failures >= 3 or tool_name in CRITICAL_TOOLS:
        _push_to_hitl(ctx, tool_name, error_msg, DegradationLevel.ESCALATE)
        _log_degradation(ctx, tool_name, DegradationLevel.ESCALATE,
                         error_msg, "升级到HITL人工干预队列")

        # 检查是否需要熔断
        if consecutive_failures >= 10:
            logger.critical(
                f"[R15-降级] Level 5 BREAK: 连续{consecutive_failures}次失败，触发熔断"
            )
            _log_degradation(ctx, tool_name, DegradationLevel.BREAK,
                             error_msg, f"熔断(连续{consecutive_failures}次失败)")

            # 标记上下文为熔断状态
            ctx._circuit_broken = True
            ctx._circuit_break_reason = f"连续{consecutive_failures}次失败"

            return {
                "block": True,
                "circuit_broken": True,
                "reason": (
                    f"连续{consecutive_failures}次失败，{tool_name}模块已熔断。"
                    f"请人工介入修复后重启。"
                ),
            }

        logger.warning(
            f"[R15-降级] Level 4 ESCALATE: {tool_name} -> 需要人工干预"
        )
        return {
            "hitl_required": True,
            "message": (
                f"{tool_name} 连续{consecutive_failures}次失败，"
                f"已加入人工干预队列。请检查并处理。"
            ),
            "original_error": error_msg,
        }

    return None


def _extract_error(result) -> dict | None:
    """从result中提取错误信息"""
    if isinstance(result, dict):
        if result.get("error"):
            return {"error": str(result["error"])}
        if result.get("block"):
            return {"error": result.get("reason", "操作被阻止")}
        if result.get("exit_code", 0) != 0:
            return {"error": result.get("stderr", result.get("output", "命令执行失败"))}  # Fixed typo
    if isinstance(result, Exception):
        return {"error": str(result)}
    if isinstance(result, str) and ("error" in result.lower() or "traceback" in result.lower()):
        return {"error": result[:200]}
    return None
