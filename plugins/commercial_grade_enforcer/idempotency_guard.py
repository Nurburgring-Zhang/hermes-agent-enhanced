"""
R10: 幂等键守卫 — pre_tool_call hook
=========================================
方法论依据: 三.3 幂等性与去重
"所有长程任务的状态变更操作必须幂等（执行N次结果一致）
使用唯一幂等键（Idempotency Key）去重，防止重试导致双重执行"
"""

import hashlib
import sqlite3
import logging
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

# ── 幂等键数据库 ──
IDEMPOTENCY_DB = Path("~/.hermes/data/idempotency.db").expanduser()

# ── 有副作用的工具（需要幂等保护）──
MUTATING_TOOLS = {
    "write_file",   # 文件写入
    "patch",        # 文件修改
    "terminal",     # 终端命令（可能有副作用）
    "process",      # 进程操作（可能有副作用）
}

# ── 只读工具（跳过幂等检查）──
READONLY_TOOLS = {
    "read_file",
    "search_files",
}


def _init_db():
    """初始化幂等键数据库"""
    IDEMPOTENCY_DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(IDEMPOTENCY_DB))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS idempotency_log (
            key TEXT PRIMARY KEY,
            tool TEXT NOT NULL,
            task_id TEXT,
            step_index INTEGER,
            status TEXT DEFAULT 'pending',  -- pending/completed/expired
            result_hash TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_idempotency_status
        ON idempotency_log(status, created_at)
    """)
    conn.commit()
    conn.close()


def _generate_key(task_id: str, step_index: int, tool_name: str, kwargs: dict) -> str:
    """生成唯一幂等键: SHA256(task_id + step_index + tool_name + args_hash)"""
    # 取kwargs的关键字段做哈希（避免不确定字段干扰）
    stable_args = {k: v for k, v in kwargs.items()
                   if k not in ("_timestamp", "_random", "_nonce")}
    key_raw = f"{task_id or 'default'}:{step_index or 0}:{tool_name}:{sorted(stable_args.items())}"
    return hashlib.sha256(key_raw.encode()).hexdigest()[:16]


def inject_idempotency_key(ctx, tool_name: str, kwargs: dict):
    """
    pre_tool_call hook: 对有副作用的操作生成并检查幂等键。
    返回 None = 放行 | 返回 {block: True} = 阻止
    """
    # 只读工具不处理
    if tool_name in READONLY_TOOLS:
        return None

    # 非变更操作不处理
    if tool_name not in MUTATING_TOOLS:
        return None

    _init_db()

    task_id = getattr(ctx, "task_id", "default")
    step_index = getattr(ctx, "step_index", 0)

    idempotency_key = _generate_key(task_id, step_index, tool_name, kwargs)

    conn = sqlite3.connect(str(IDEMPOTENCY_DB))
    try:
        # 检查是否已执行
        cursor = conn.execute(
            "SELECT status, result_hash FROM idempotency_log WHERE key = ?",
            (idempotency_key,)
        )
        row = cursor.fetchone()

        if row and row[0] == "completed":
            logger.warning(
                f"[R10-幂等键] 重复操作被阻止: key={idempotency_key} "
                f"tool={tool_name} task={task_id}"
            )
            return {
                "block": True,
                "reason": (
                    f"幂等键 {idempotency_key} 已执行完毕。"
                    f"重复执行被阻止以保护数据一致性。"
                ),
                "idempotency_key": idempotency_key,
            }

        # 记录为pending
        conn.execute(
            """INSERT OR IGNORE INTO idempotency_log
               (key, tool, task_id, step_index, status)
               VALUES (?, ?, ?, ?, 'pending')""",
            (idempotency_key, tool_name, task_id, step_index)
        )
        conn.commit()

        # 注入幂等键到kwargs，供下游使用
        kwargs["_idempotency_key"] = idempotency_key

        logger.debug(f"[R10-幂等键] 已注入: key={idempotency_key} tool={tool_name}")
        return None  # 放行

    finally:
        conn.close()


def mark_completed(idempotency_key: str, result_hash: str = ""):
    """post_tool_call: 标记幂等键操作已完成"""
    conn = sqlite3.connect(str(IDEMPOTENCY_DB))
    try:
        conn.execute(
            """UPDATE idempotency_log
               SET status = 'completed', result_hash = ?, completed_at = ?
               WHERE key = ? AND status = 'pending'""",
            (result_hash, datetime.now(timezone.utc).isoformat(), idempotency_key)
        )
        conn.commit()
    finally:
        conn.close()
