"""
R11: Checkpoint强制守卫 — pre_tool_call hook
=================================================
方法论依据: 三.1 Checkpointing（检查点）模式
"任务执行到关键节点时保存完整状态快照
失败恢复：从最近的 Checkpoint 恢复，而非从头重跑"
"""

import hashlib
import json
import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

CHECKPOINT_DB = Path("~/.hermes/data/checkpoints.db").expanduser()
CHECKPOINT_JSON_DIR = Path("~/.hermes/checkpoints/").expanduser()

# ── 阈值配置 ──
HIGH_CHECKPOINT_INTERVAL = 3   # >20步任务每3步保存
MED_CHECKPOINT_INTERVAL = 5    # >10步任务每5步保存
CHECKPOINT_THRESHOLD = 10       # 超过10步的任务强制开checkpoint


def _init_db():
    """初始化Checkpoint数据库"""
    CHECKPOINT_DB.parent.mkdir(parents=True, exist_ok=True)
    CHECKPOINT_JSON_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(CHECKPOINT_DB))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS checkpoints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id TEXT NOT NULL,
            step_index INTEGER NOT NULL,
            checkpoint_hash TEXT NOT NULL,
            json_path TEXT NOT NULL,
            state_snapshot TEXT,  -- JSON mini-summary
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_checkpoint_task
        ON checkpoints(task_id, step_index)
    """)
    conn.commit()
    conn.close()


def _save_checkpoint(ctx, step_index: int) -> str:
    """保存当前状态快照到JSON + SQLite"""
    _init_db()

    task_id = getattr(ctx, "task_id", "unknown")
    snapshot = {
        "task_id": task_id,
        "step_index": step_index,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "summary": getattr(ctx, "last_summary", ""),
        "tool_count": getattr(ctx, "_tool_call_count", 0),
    }

    # 写入JSON文件
    json_str = json.dumps(snapshot, ensure_ascii=False, indent=2)
    ckpt_hash = hashlib.sha256(json_str.encode()).hexdigest()[:12]
    json_path = CHECKPOINT_JSON_DIR / f"{task_id}_{step_index}_{ckpt_hash}.json"
    json_path.write_text(json_str, encoding="utf-8")

    # 写入SQLite索引
    conn = sqlite3.connect(str(CHECKPOINT_DB))
    conn.execute(
        """INSERT INTO checkpoints (task_id, step_index, checkpoint_hash, json_path, state_snapshot)
           VALUES (?, ?, ?, ?, ?)""",
        (task_id, step_index, ckpt_hash, str(json_path),
         json.dumps(snapshot, ensure_ascii=False))
    )
    conn.commit()
    conn.close()

    logger.info(f"[R11-Checkpoint] 已保存: task={task_id} step={step_index} hash={ckpt_hash}")
    return ckpt_hash


def safepoint_check(ctx, tool_name: str, kwargs: dict):
    """
    pre_tool_call hook: 检查是否需要保存checkpoint。
    返回 None = 放行 | 对工具调用本身不阻止
    """
    task_id = getattr(ctx, "task_id", None)
    if not task_id:
        return None

    # 获取任务元信息
    task_total_steps = getattr(ctx, "task_total_steps", 0)
    current_step = getattr(ctx, "step_index", 0)
    last_checkpoint_step = getattr(ctx, "_last_checkpoint_step", 0)

    # 步骤不足阈值不处理
    if task_total_steps < CHECKPOINT_THRESHOLD:
        return None

    # 确定checkpoint间隔
    if task_total_steps > 20:
        interval = HIGH_CHECKPOINT_INTERVAL
    else:
        interval = MED_CHECKPOINT_INTERVAL

    # 检查是否到达checkpoint点
    if current_step - last_checkpoint_step >= interval:
        _save_checkpoint(ctx, current_step)
        ctx._last_checkpoint_step = current_step

    return None  # 不阻止工具调用


def restore_from_checkpoint(task_id: str) -> dict | None:
    """从最近的checkpoint恢复状态"""
    _init_db()
    conn = sqlite3.connect(str(CHECKPOINT_DB))
    cursor = conn.execute(
        """SELECT step_index, json_path, state_snapshot
           FROM checkpoints
           WHERE task_id = ?
           ORDER BY step_index DESC LIMIT 1""",
        (task_id,)
    )
    row = cursor.fetchone()
    conn.close()

    if not row:
        logger.warning(f"[R11-Checkpoint] 未找到checkpoint: task={task_id}")
        return None

    step_index, json_path, snapshot_str = row
    logger.info(f"[R11-Checkpoint] 恢复: task={task_id} from_step={step_index}")

    # 尝试从JSON文件恢复
    json_path = Path(json_path)
    if json_path.exists():
        return json.loads(json_path.read_text(encoding="utf-8"))

    # fallback到SQLite中的快照
    return json.loads(snapshot_str) if snapshot_str else None
