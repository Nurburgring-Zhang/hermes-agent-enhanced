"""
Loop Checkpoint & Memory — Hermes Loop Engineering 检查点与记忆
==================================================================
基于 Loop Engineering 范式：

持久化状态：JSON / SQLite checkpoint
记录内容：
  - 做了什么 (completed actions)
  - 失败什么 (failures with context)
  - 哪些已确认 (verified items)
  - 哪些需人工 (human-required items)

恢复：从检查点恢复中断的 loop
摘要：生成人类可读的进度报告
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import time
from dataclasses import asdict, dataclass, field, fields
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union


# ─── 检查点数据模型 ────────────────────────────────────────────


@dataclass
class CheckpointEntry:
    """单个检查点条目"""
    checkpoint_id: str = ""
    loop_id: str = ""
    session_id: str = ""
    checkpoint_type: str = "auto"  # auto | manual | recovery | pre_risky | completion
    seq_number: int = 0
    phase: str = ""

    # 状态快照
    loop_def_snapshot: dict = field(default_factory=dict)
    task_graph_state: dict = field(default_factory=dict)

    # 执行进度
    completed_nodes: List[str] = field(default_factory=list)
    failed_nodes: List[dict] = field(default_factory=list)
    skipped_nodes: List[dict] = field(default_factory=list)
    pending_nodes: List[str] = field(default_factory=list)
    current_node_id: str = ""
    overall_progress: float = 0.0

    # 验证状态
    verified_items: List[str] = field(default_factory=list)
    verification_failures: List[dict] = field(default_factory=list)

    # 人工交互
    human_required: List[dict] = field(default_factory=list)
    human_approved: List[dict] = field(default_factory=list)

    # 环境信息
    work_dir: str = ""
    env_snapshot: dict = field(default_factory=dict)

    # 成本信息
    token_usage: dict = field(default_factory=dict)
    elapsed_seconds: float = 0.0
    turn_count: int = 0

    # 元数据
    created_at: str = ""
    created_by: str = "hermes"
    checksum: str = ""

    def compute_checksum(self) -> str:
        """计算状态哈希用于完整性校验"""
        payload = json.dumps({
            "loop_id": self.loop_id,
            "session_id": self.session_id,
            "completed_nodes": sorted(self.completed_nodes),
            "failed_nodes": sorted(f.get("node_id", "") for f in self.failed_nodes),
            "pending_nodes": sorted(self.pending_nodes),
            "overall_progress": self.overall_progress,
            "turn_count": self.turn_count,
        }, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(payload.encode()).hexdigest()[:16]

    def validate(self) -> bool:
        """验证检查点完整性"""
        expected = self.compute_checksum()
        return self.checksum == expected

    def to_dict(self) -> dict:
        d = asdict(self)
        d.pop("checksum", None)
        d["checksum"] = self.compute_checksum()
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "CheckpointEntry":
        filtered = {k: v for k, v in data.items()
                    if k in {f.name for f in fields(cls)}}
        return cls(**filtered)


@dataclass
class ActionRecord:
    """操作记录 — 记录做了什么"""
    record_id: str = ""
    session_id: str = ""
    node_id: str = ""
    action_type: str = ""  # tool_call | decision | human_input | recovery
    action_name: str = ""
    action_params: dict = field(default_factory=dict)
    action_result: dict = field(default_factory=dict)
    success: bool = False
    error_message: str = ""
    duration_seconds: float = 0.0
    retry_count: int = 0
    verified: bool = False
    verified_by: str = ""
    timestamp: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "ActionRecord":
        filtered = {k: v for k, v in data.items()
                    if k in {f.name for f in fields(cls)}}
        return cls(**filtered)


@dataclass
class ProgressReport:
    """进度报告"""
    loop_id: str = ""
    loop_name: str = ""
    session_id: str = ""
    status: str = ""  # running | completed | failed | paused | recovered
    progress_percent: float = 0.0
    total_nodes: int = 0
    completed_nodes: int = 0
    failed_nodes: int = 0
    pending_nodes: int = 0
    human_blocked: int = 0
    total_turns: int = 0
    total_errors: int = 0
    elapsed_time: str = ""
    estimated_remaining: str = ""
    last_checkpoint_at: str = ""
    next_steps: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    summary: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    def format_text(self) -> str:
        """生成人类可读的文本报告"""
        lines = [
            "=" * 60,
            f"Loop Progress Report",
            "=" * 60,
            f"Loop:       {self.loop_name} ({self.loop_id})",
            f"Session:    {self.session_id}",
            f"Status:     {self.status.upper()}",
            f"Progress:   {self.progress_percent:.1%} "
            f"({self.completed_nodes}/{self.total_nodes} nodes)",
            "-" * 40,
            f"  Completed:  {self.completed_nodes}",
            f"  Failed:     {self.failed_nodes}",
            f"  Pending:    {self.pending_nodes}",
            f"  Need Human: {self.human_blocked}",
            "-" * 40,
            f"Turns:      {self.total_turns}",
            f"Errors:     {self.total_errors}",
            f"Time:       elapsed {self.elapsed_time}"
            + (f", est. remaining {self.estimated_remaining}"
               if self.estimated_remaining else ""),
            f"Checkpoint: {self.last_checkpoint_at or 'none'}",
        ]
        if self.next_steps:
            lines.append("-" * 40)
            lines.append("Next Steps:")
            for step in self.next_steps:
                lines.append(f"  * {step}")
        if self.warnings:
            lines.append("-" * 40)
            lines.append("Warnings:")
            for w in self.warnings:
                lines.append(f"  ! {w}")
        if self.summary:
            lines.append("-" * 40)
            lines.append(f"Summary: {self.summary}")
        lines.append("=" * 60)
        return "\n".join(lines)


# ─── 检查点存储引擎 ────────────────────────────────────────────


class CheckpointStore:
    """
    检查点存储 — 支持 JSON 文件和 SQLite 双模式

    JSON:   ~/.hermes/state/checkpoints/<loop_id>/<checkpoint_id>.json
    SQLite: ~/.hermes/state/checkpoints.db
    """

    DEFAULT_BASE_DIR = os.path.expanduser("~/.hermes/state/checkpoints")
    DEFAULT_DB_PATH = os.path.expanduser("~/.hermes/state/checkpoints.db")
    DEFAULT_ACTIONS_DB = os.path.expanduser("~/.hermes/state/actions.db")

    MAX_CHECKPOINTS_PER_LOOP = 50
    RETENTION_DAYS = 30

    def __init__(self, base_dir: str = None, db_path: str = None,
                 actions_db: str = None, max_checkpoints: int = None,
                 retention_days: int = None):
        self.base_dir = base_dir or self.DEFAULT_BASE_DIR
        self.db_path = db_path or self.DEFAULT_DB_PATH
        self.actions_db = actions_db or self.DEFAULT_ACTIONS_DB
        self.max_checkpoints = max_checkpoints or self.MAX_CHECKPOINTS_PER_LOOP
        self.retention_days = retention_days or self.RETENTION_DAYS

        os.makedirs(self.base_dir, exist_ok=True)
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        os.makedirs(os.path.dirname(self.actions_db), exist_ok=True)
        self._init_db()

    def _get_sqlite_conn(self, db_path: str = None) -> sqlite3.Connection:
        conn = sqlite3.connect(db_path or self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _init_db(self):
        """初始化 SQLite 表"""
        conn = self._get_sqlite_conn()
        try:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS checkpoints (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    checkpoint_id TEXT UNIQUE NOT NULL,
                    loop_id TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    checkpoint_type TEXT NOT NULL,
                    seq_number INTEGER NOT NULL,
                    phase TEXT,
                    completed_nodes TEXT,
                    failed_nodes TEXT,
                    pending_nodes TEXT,
                    overall_progress REAL,
                    current_node_id TEXT,
                    is_latest INTEGER DEFAULT 0,
                    turn_count INTEGER DEFAULT 0,
                    checksum TEXT,
                    raw_json TEXT NOT NULL,
                    created_at TEXT DEFAULT (datetime('now'))
                );
                CREATE INDEX IF NOT EXISTS idx_cp_loop_session
                    ON checkpoints(loop_id, session_id, seq_number);
                CREATE INDEX IF NOT EXISTS idx_cp_latest
                    ON checkpoints(loop_id, session_id, is_latest);
                CREATE INDEX IF NOT EXISTS idx_cp_created
                    ON checkpoints(created_at);

                CREATE TABLE IF NOT EXISTS action_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    record_id TEXT UNIQUE NOT NULL,
                    session_id TEXT NOT NULL,
                    node_id TEXT,
                    action_type TEXT NOT NULL,
                    action_name TEXT NOT NULL,
                    action_params TEXT,
                    action_result TEXT,
                    success INTEGER NOT NULL,
                    error_message TEXT,
                    duration_seconds REAL,
                    retry_count INTEGER DEFAULT 0,
                    verified INTEGER DEFAULT 0,
                    verified_by TEXT,
                    timestamp TEXT DEFAULT (datetime('now'))
                );
                CREATE INDEX IF NOT EXISTS idx_actions_session
                    ON action_records(session_id, timestamp);
                CREATE INDEX IF NOT EXISTS idx_actions_node
                    ON action_records(node_id);

                CREATE TABLE IF NOT EXISTS human_interactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    node_id TEXT NOT NULL,
                    interaction_type TEXT NOT NULL,
                    description TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    response TEXT,
                    created_at TEXT DEFAULT (datetime('now')),
                    resolved_at TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_human_session
                    ON human_interactions(session_id, status);
            """)
            conn.commit()
        finally:
            conn.close()

    # ─── 保存检查点 ─────────────────────────────────────────

    def save_checkpoint(self, entry: CheckpointEntry) -> str:
        """
        保存检查点到 JSON 文件和 SQLite

        返回 checkpoint_id
        """
        if not entry.checkpoint_id:
            entry.checkpoint_id = (
                f"ck_{entry.loop_id}_{entry.session_id}_{int(time.time())}"
            )
        if not entry.created_at:
            entry.created_at = datetime.now().isoformat()
        if not entry.checksum:
            entry.checksum = entry.compute_checksum()

        entry_dict = entry.to_dict()

        # JSON 文件
        loop_dir = os.path.join(self.base_dir, entry.loop_id)
        os.makedirs(loop_dir, exist_ok=True)
        json_path = os.path.join(loop_dir, f"{entry.checkpoint_id}.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(entry_dict, f, ensure_ascii=False, indent=2)

        # SQLite
        conn = self._get_sqlite_conn()
        try:
            # 清除旧 latest 标记
            conn.execute(
                """UPDATE checkpoints SET is_latest = 0
                   WHERE loop_id = ? AND session_id = ?""",
                (entry.loop_id, entry.session_id)
            )
            conn.execute(
                """INSERT OR REPLACE INTO checkpoints
                   (checkpoint_id, loop_id, session_id, checkpoint_type,
                    seq_number, phase, completed_nodes, failed_nodes,
                    pending_nodes, overall_progress, current_node_id,
                    is_latest, turn_count, checksum, raw_json)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?)""",
                (entry.checkpoint_id, entry.loop_id, entry.session_id,
                 entry.checkpoint_type, entry.seq_number, entry.phase,
                 json.dumps(entry.completed_nodes),
                 json.dumps(entry.failed_nodes),
                 json.dumps(entry.pending_nodes),
                 entry.overall_progress, entry.current_node_id,
                 entry.turn_count, entry.checksum,
                 json.dumps(entry_dict, ensure_ascii=False))
            )
            conn.commit()
        finally:
            conn.close()

        # 清理旧检查点
        self._evict_old_checkpoints(entry.loop_id)

        return entry.checkpoint_id

    def _evict_old_checkpoints(self, loop_id: str):
        """超出上限或过期时清理旧检查点"""
        loop_dir = os.path.join(self.base_dir, loop_id)
        if not os.path.isdir(loop_dir):
            return

        files = sorted(
            [f for f in os.listdir(loop_dir) if f.endswith(".json")],
            key=lambda x: os.path.getmtime(os.path.join(loop_dir, x)),
        )

        # 按数量清理
        while len(files) > self.max_checkpoints:
            oldest = files.pop(0)
            try:
                os.remove(os.path.join(loop_dir, oldest))
            except OSError:
                pass

        # 按时间清理
        cutoff = time.time() - self.retention_days * 86400
        for fname in list(files):
            fpath = os.path.join(loop_dir, fname)
            if os.path.getmtime(fpath) < cutoff:
                try:
                    os.remove(fpath)
                except OSError:
                    pass

    # ─── 加载检查点 ─────────────────────────────────────────

    def load_latest_checkpoint(self, loop_id: str,
                               session_id: str = None) -> Optional[CheckpointEntry]:
        """加载最新检查点"""
        conn = self._get_sqlite_conn()
        try:
            if session_id:
                row = conn.execute(
                    """SELECT raw_json FROM checkpoints
                       WHERE loop_id = ? AND session_id = ?
                       ORDER BY id DESC LIMIT 1""",
                    (loop_id, session_id)
                ).fetchone()
            else:
                row = conn.execute(
                    """SELECT raw_json FROM checkpoints
                       WHERE loop_id = ? AND is_latest = 1
                       ORDER BY id DESC LIMIT 1""",
                    (loop_id,)
                ).fetchone()

            if row:
                data = json.loads(row["raw_json"])
                return CheckpointEntry.from_dict(data)
        finally:
            conn.close()

        # 回退到 JSON 文件
        loop_dir = os.path.join(self.base_dir, loop_id)
        if os.path.isdir(loop_dir):
            files = sorted(
                [f for f in os.listdir(loop_dir) if f.endswith(".json")],
                key=lambda x: os.path.getmtime(os.path.join(loop_dir, x)),
                reverse=True,
            )
            for fname in files:
                fpath = os.path.join(loop_dir, fname)
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    entry = CheckpointEntry.from_dict(data)
                    if not session_id or entry.session_id == session_id:
                        return entry
                except Exception:
                    pass

        return None

    def load_checkpoint_by_id(self, checkpoint_id: str) -> Optional[CheckpointEntry]:
        """按 ID 加载检查点"""
        conn = self._get_sqlite_conn()
        try:
            row = conn.execute(
                "SELECT raw_json FROM checkpoints WHERE checkpoint_id = ?",
                (checkpoint_id,)
            ).fetchone()
            if row:
                return CheckpointEntry.from_dict(json.loads(row["raw_json"]))
        finally:
            conn.close()
        return None

    def list_checkpoints(self, loop_id: str,
                         session_id: str = None,
                         limit: int = 20) -> List[dict]:
        """列出检查点"""
        conn = self._get_sqlite_conn()
        try:
            if session_id:
                rows = conn.execute(
                    """SELECT checkpoint_id, checkpoint_type, seq_number,
                              overall_progress, turn_count, created_at
                       FROM checkpoints
                       WHERE loop_id = ? AND session_id = ?
                       ORDER BY id DESC LIMIT ?""",
                    (loop_id, session_id, limit)
                ).fetchall()
            else:
                rows = conn.execute(
                    """SELECT checkpoint_id, checkpoint_type, seq_number,
                              overall_progress, turn_count, created_at
                       FROM checkpoints
                       WHERE loop_id = ?
                       ORDER BY id DESC LIMIT ?""",
                    (loop_id, limit)
                ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    # ─── 操作记录 ───────────────────────────────────────────

    def record_action(self, record: ActionRecord) -> str:
        """记录操作"""
        if not record.record_id:
            record.record_id = f"act_{int(time.time())}_{os.urandom(4).hex()}"
        if not record.timestamp:
            record.timestamp = datetime.now().isoformat()

        conn = self._get_sqlite_conn(self.actions_db)
        try:
            conn.execute(
                """INSERT OR REPLACE INTO action_records
                   (record_id, session_id, node_id, action_type, action_name,
                    action_params, action_result, success, error_message,
                    duration_seconds, retry_count, verified, verified_by)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (record.record_id, record.session_id, record.node_id,
                 record.action_type, record.action_name,
                 json.dumps(record.action_params),
                 json.dumps(record.action_result),
                 1 if record.success else 0,
                 record.error_message, record.duration_seconds,
                 record.retry_count,
                 1 if record.verified else 0,
                 record.verified_by)
            )
            conn.commit()
        finally:
            conn.close()

        return record.record_id

    def get_actions(self, session_id: str,
                    limit: int = 100) -> List[ActionRecord]:
        """获取会话的操作记录"""
        conn = self._get_sqlite_conn(self.actions_db)
        try:
            rows = conn.execute(
                """SELECT * FROM action_records
                   WHERE session_id = ?
                   ORDER BY id ASC LIMIT ?""",
                (session_id, limit)
            ).fetchall()
            return [ActionRecord.from_dict(dict(r)) for r in rows]
        finally:
            conn.close()

    def get_failed_actions(self, session_id: str) -> List[ActionRecord]:
        """获取失败的操作记录"""
        conn = self._get_sqlite_conn(self.actions_db)
        try:
            rows = conn.execute(
                """SELECT * FROM action_records
                   WHERE session_id = ? AND success = 0
                   ORDER BY id ASC""",
                (session_id,)
            ).fetchall()
            return [ActionRecord.from_dict(dict(r)) for r in rows]
        finally:
            conn.close()

    # ─── 人工交互 ───────────────────────────────────────────

    def record_human_required(self, session_id: str, node_id: str,
                              description: str, req_type: str = "approval") -> int:
        """记录需要人工处理的事项"""
        conn = self._get_sqlite_conn(self.actions_db)
        try:
            cursor = conn.execute(
                """INSERT INTO human_interactions
                   (session_id, node_id, interaction_type, description)
                   VALUES (?, ?, ?, ?)""",
                (session_id, node_id, req_type, description)
            )
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    def resolve_human_required(self, interaction_id: int,
                               response: str = "approved"):
        """标记人工事项已解决"""
        conn = self._get_sqlite_conn(self.actions_db)
        try:
            conn.execute(
                """UPDATE human_interactions
                   SET status = 'resolved', response = ?,
                       resolved_at = datetime('now')
                   WHERE id = ?""",
                (response, interaction_id)
            )
            conn.commit()
        finally:
            conn.close()

    def get_pending_human(self, session_id: str = None) -> List[dict]:
        """获取待处理的人工事项"""
        conn = self._get_sqlite_conn(self.actions_db)
        try:
            if session_id:
                rows = conn.execute(
                    """SELECT * FROM human_interactions
                       WHERE session_id = ? AND status = 'pending'
                       ORDER BY created_at ASC""",
                    (session_id,)
                ).fetchall()
            else:
                rows = conn.execute(
                    """SELECT * FROM human_interactions
                       WHERE status = 'pending'
                       ORDER BY created_at ASC"""
                ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()


# ─── Loop 恢复引擎 ─────────────────────────────────────────────


class LoopRecoveryEngine:
    """
    Loop 恢复引擎 — 从检查点恢复中断的 loop

    恢复流程:
      1. 加载最新检查点
      2. 验证检查点完整性
      3. 分析已完成/失败/待处理节点
      4. 重建执行上下文
      5. 从未完成节点继续执行
    """

    def __init__(self, checkpoint_store: CheckpointStore = None):
        self.store = checkpoint_store or CheckpointStore()

    def can_recover(self, loop_id: str,
                    session_id: str = None) -> Tuple[bool, str]:
        """
        检查是否可以从检查点恢复

        返回 (can_recover, reason)
        """
        entry = self.store.load_latest_checkpoint(loop_id, session_id)
        if not entry:
            return False, "No checkpoint found"

        if not entry.validate():
            return False, "Checkpoint integrity check failed"

        if not entry.pending_nodes and entry.overall_progress >= 1.0:
            return False, "Loop already completed"

        if not entry.pending_nodes:
            return False, "No pending nodes to resume"

        return True, f"Found checkpoint with {len(entry.pending_nodes)} pending nodes"

    def get_recovery_state(self, loop_id: str,
                           session_id: str = None) -> Optional[dict]:
        """
        获取恢复状态 — 返回需要继续执行的上下文
        """
        entry = self.store.load_latest_checkpoint(loop_id, session_id)
        if not entry:
            return None

        return {
            "checkpoint_id": entry.checkpoint_id,
            "loop_id": entry.loop_id,
            "session_id": entry.session_id,
            "phase_at_interruption": entry.phase,
            "completed_nodes": entry.completed_nodes,
            "failed_nodes": entry.failed_nodes,
            "pending_nodes": entry.pending_nodes,
            "current_node_id": entry.current_node_id,
            "overall_progress": entry.overall_progress,
            "turn_count": entry.turn_count,
            "human_required": entry.human_required,
            "token_usage": entry.token_usage,
            "work_dir": entry.work_dir,
            "recovery_valid": entry.validate(),
        }

    def build_recovery_plan(self, loop_id: str,
                            session_id: str = None) -> Optional[dict]:
        """生成恢复执行计划"""
        state = self.get_recovery_state(loop_id, session_id)
        if not state:
            return None

        # 清理已完成节点（跳过）
        skip_nodes = set(state["completed_nodes"])

        # 重新评估失败节点（可能需要重试或跳过）
        retry_nodes = []
        skip_failed = []
        for failed in state.get("failed_nodes", []):
            node_id = failed.get("node_id", "")
            retry_count = failed.get("retry_count", 0)
            max_retries = failed.get("max_retries", 3)
            if retry_count < max_retries:
                retry_nodes.append(node_id)
            else:
                skip_failed.append(node_id)

        # 待处理节点
        pending = state["pending_nodes"]

        # 需要人工处理的节点
        human_blocked = [
            h.get("node_id", "") for h in state.get("human_required", [])
        ]

        return {
            "checkpoint_id": state["checkpoint_id"],
            "resume_from": state["current_node_id"],
            "nodes_to_retry": retry_nodes,
            "nodes_pending": pending,
            "nodes_skip_failed": skip_failed,
            "human_blocked": human_blocked,
            "total_remaining": len(pending) + len(retry_nodes),
            "estimated_turns": len(pending) + len(retry_nodes),
        }


# ─── 进度报告生成器 ──────────────────────────────────────────


class ProgressReporter:
    """
    进度报告生成器 — 生成人类可读的进度摘要
    """

    def __init__(self, checkpoint_store: CheckpointStore = None):
        self.store = checkpoint_store or CheckpointStore()

    def generate_report(self, loop_id: str,
                        loop_name: str = "",
                        session_id: str = None) -> ProgressReport:
        """
        生成完整进度报告

        合并检查点状态和操作记录，生成单页概览
        """
        entry = self.store.load_latest_checkpoint(loop_id, session_id)
        if not entry:
            return ProgressReport(
                loop_id=loop_id, loop_name=loop_name,
                session_id=session_id or "", status="not_found",
                summary="No checkpoint data available"
            )

        sess_id = entry.session_id

        # 获取操作记录
        actions = self.store.get_actions(sess_id)
        failed_actions = self.store.get_failed_actions(sess_id)
        pending_human = self.store.get_pending_human(sess_id)

        # 确定状态
        if entry.overall_progress >= 1.0 and len(entry.failed_nodes) == 0:
            status = "completed"
        elif len(entry.failed_nodes) > 0 and not entry.pending_nodes:
            status = "failed"
        elif pending_human:
            status = "paused"
        elif entry.checkpoint_type == "recovery":
            status = "recovered"
        else:
            status = "running"

        total_nodes = len(entry.completed_nodes) + len(entry.failed_nodes) + \
                      len(entry.pending_nodes)
        total_nodes = max(total_nodes, 1)

        # 计算剩余时间
        avg_time_per_node = (
            entry.elapsed_seconds / max(entry.turn_count, 1)
            if entry.turn_count > 0 else 0
        )
        remaining_seconds = len(entry.pending_nodes) * avg_time_per_node
        estimated_remaining = (
            str(timedelta(seconds=int(remaining_seconds)))
            if remaining_seconds > 0 else ""
        )

        # 生成下一步建议
        next_steps = []
        if pending_human:
            next_steps.append(
                f"Human action needed on {len(pending_human)} item(s)"
            )
        if entry.pending_nodes:
            next_node = entry.pending_nodes[0] if entry.pending_nodes else ""
            next_steps.append(f"Next node to execute: {next_node}")
        if entry.failed_nodes:
            for fnode in entry.failed_nodes[:3]:
                next_steps.append(
                    f"Retry or skip failed: {fnode.get('node_id', '?')}"
                )

        # 生成警告
        warnings = []
        if len(entry.failed_nodes) > 2:
            warnings.append(f"High failure count: {len(entry.failed_nodes)} failures")
        if entry.token_usage.get("budget_exceeded"):
            warnings.append("Token budget exceeded!")
        if pending_human:
            warnings.append(
                f"Blocked on {len(pending_human)} human-required items"
            )

        # 摘要
        summary_parts = []
        if status == "completed":
            summary_parts.append("Loop completed successfully")
        elif status == "failed":
            summary_parts.append(
                f"Loop failed with {len(entry.failed_nodes)} failures"
            )
        elif status == "paused":
            summary_parts.append(
                f"Paused — waiting for human input on {len(pending_human)} items"
            )
        else:
            summary_parts.append(
                f"In progress ({entry.overall_progress:.0%} complete)"
            )
        summary_parts.append(
            f"{len(actions)} actions executed, "
            f"{len(failed_actions)} errors"
        )

        return ProgressReport(
            loop_id=loop_id,
            loop_name=loop_name or entry.loop_def_snapshot.get("name", loop_id),
            session_id=sess_id,
            status=status,
            progress_percent=entry.overall_progress,
            total_nodes=total_nodes,
            completed_nodes=len(entry.completed_nodes),
            failed_nodes=len(entry.failed_nodes),
            pending_nodes=len(entry.pending_nodes),
            human_blocked=len(pending_human),
            total_turns=entry.turn_count,
            total_errors=len(failed_actions),
            elapsed_time=str(timedelta(seconds=int(entry.elapsed_seconds))),
            estimated_remaining=estimated_remaining,
            last_checkpoint_at=entry.created_at[:19] if entry.created_at else "",
            next_steps=next_steps,
            warnings=warnings,
            summary=" | ".join(summary_parts),
        )

    def generate_session_summary(self, session_id: str) -> str:
        """
        生成纯文本会话摘要

        适合直接展示给用户或写入日志
        """
        actions = self.store.get_actions(session_id)

        if not actions:
            return "No actions recorded for this session."

        lines = [
            f"Session: {session_id}",
            f"Total actions: {len(actions)}",
            "",
            "Actions:",
        ]

        for act in actions:
            status_icon = "OK" if act.success else "FAIL"
            verified_mark = " [verified]" if act.verified else ""
            error_info = f" - {act.error_message}" if act.error_message else ""
            lines.append(
                f"  [{status_icon}] {act.action_type}: {act.action_name}"
                f" ({act.duration_seconds:.1f}s){verified_mark}{error_info}"
            )

        failures = [a for a in actions if not a.success]
        if failures:
            lines.append("")
            lines.append(f"Failures ({len(failures)}):")
            for fail in failures:
                lines.append(
                    f"  * {fail.action_name} (attempt #{fail.retry_count}): "
                    f"{fail.error_message}"
                )

        return "\n".join(lines)


# ─── 便捷工具 ────────────────────────────────────────────────


def create_checkpoint_entry(
    loop_id: str,
    session_id: str,
    checkpoint_type: str = "auto",
    completed_nodes: List[str] = None,
    failed_nodes: List[dict] = None,
    pending_nodes: List[str] = None,
    current_node_id: str = "",
    overall_progress: float = 0.0,
    turn_count: int = 0,
    elapsed_seconds: float = 0.0,
    human_required: List[dict] = None,
    **kwargs,
) -> CheckpointEntry:
    """快速创建检查点条目"""
    entry = CheckpointEntry(
        loop_id=loop_id,
        session_id=session_id,
        checkpoint_type=checkpoint_type,
        seq_number=int(time.time()),
        completed_nodes=completed_nodes or [],
        failed_nodes=failed_nodes or [],
        pending_nodes=pending_nodes or [],
        current_node_id=current_node_id,
        overall_progress=overall_progress,
        turn_count=turn_count,
        elapsed_seconds=elapsed_seconds,
        human_required=human_required or [],
        **kwargs,
    )
    entry.checksum = entry.compute_checksum()
    return entry


def create_action_record(
    session_id: str,
    node_id: str,
    action_type: str,
    action_name: str,
    success: bool = True,
    **kwargs,
) -> ActionRecord:
    """快速创建操作记录"""
    return ActionRecord(
        record_id=f"act_{int(time.time())}_{os.urandom(2).hex()}",
        session_id=session_id,
        node_id=node_id,
        action_type=action_type,
        action_name=action_name,
        success=success,
        timestamp=datetime.now().isoformat(),
        **kwargs,
    )


# ─── CLI ──────────────────────────────────────────────────────


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Loop Checkpoint Manager")
    parser.add_argument("action", choices=[
        "save", "load", "list", "report", "recover", "clean",
        "actions", "summary"
    ])
    parser.add_argument("--loop-id", help="Loop ID")
    parser.add_argument("--session-id", help="Session ID")
    parser.add_argument("--checkpoint-id", help="Checkpoint ID")
    parser.add_argument("--limit", type=int, default=20)

    args = parser.parse_args()
    store = CheckpointStore()
    recovery = LoopRecoveryEngine(store)
    reporter = ProgressReporter(store)

    if args.action == "list":
        if not args.loop_id:
            print("Error: --loop-id required")
            return
        cps = store.list_checkpoints(args.loop_id, args.session_id,
                                     args.limit)
        print(f"Checkpoints for {args.loop_id} ({len(cps)}):")
        for cp in cps:
            print(f"  [{cp['created_at']}] {cp['checkpoint_id']} "
                  f"type={cp['checkpoint_type']} "
                  f"progress={cp['overall_progress']:.1%} "
                  f"turns={cp['turn_count']}")

    elif args.action == "load":
        if not args.loop_id:
            print("Error: --loop-id required")
            return
        entry = store.load_latest_checkpoint(args.loop_id, args.session_id)
        if entry:
            print(f"Loaded checkpoint: {entry.checkpoint_id}")
            print(f"  Completed: {entry.completed_nodes}")
            print(f"  Failed: {[f.get('node_id') for f in entry.failed_nodes]}")
            print(f"  Pending: {entry.pending_nodes}")
            print(f"  Progress: {entry.overall_progress:.1%}")
            print(f"  Valid: {entry.validate()}")
        else:
            print("No checkpoint found")

    elif args.action == "report":
        if not args.loop_id:
            print("Error: --loop-id required")
            return
        report = reporter.generate_report(args.loop_id, "", args.session_id)
        print(report.format_text())

    elif args.action == "recover":
        if not args.loop_id:
            print("Error: --loop-id required")
            return
        can, reason = recovery.can_recover(args.loop_id, args.session_id)
        print(f"Recoverable: {can}")
        print(f"Reason: {reason}")
        if can:
            plan = recovery.build_recovery_plan(args.loop_id, args.session_id)
            if plan:
                print(f"  To retry: {plan['nodes_to_retry']}")
                print(f"  Pending: {plan['nodes_pending']}")
                print(f"  Estimated turns: {plan['estimated_turns']}")

    elif args.action == "clean":
        if args.loop_id:
            print(f"Cleaning old checkpoints for {args.loop_id}...")
        else:
            print("Cleaning all old checkpoints...")
            # 扫描 base_dir
            base_dir = store.base_dir
            for dirname in os.listdir(base_dir):
                store._evict_old_checkpoints(dirname)

    elif args.action == "actions":
        if not args.session_id:
            print("Error: --session-id required")
            return
        acts = store.get_actions(args.session_id, args.limit)
        print(f"Actions for {args.session_id} ({len(acts)}):")
        for act in acts:
            icon = "+" if act.success else "-"
            print(f"  [{icon}] {act.action_type}: {act.action_name} "
                  f"({act.duration_seconds:.1f}s)")

    elif args.action == "summary":
        if not args.session_id:
            print("Error: --session-id required")
            return
        print(reporter.generate_session_summary(args.session_id))


if __name__ == "__main__":
    main()
