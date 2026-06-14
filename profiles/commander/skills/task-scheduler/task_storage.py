"""
Task Storage Module
SQLite-backed persistent storage for task scheduler with full ACID compliance.
"""

import json
import pickle
import sqlite3
import threading
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any


class TaskStatus(Enum):
    """Task execution status."""
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"
    RETRYING = "retrying"


class TaskPriority(Enum):
    """Task priority levels (0 is highest)."""
    CRITICAL = 0
    HIGH = 1
    MEDIUM = 2
    LOW = 3
    BACKGROUND = 4


@dataclass
class TaskDefinition:
    """Task definition stored in database."""
    task_id: str
    name: str
    task_type: str  # 'function', 'shell', 'http', 'batch'
    func: str | None = None  # function reference or module.func
    args: dict[str, Any] | None = None
    kwargs: dict[str, Any] | None = None
    priority: int = 2  # MEDIUM
    max_retries: int = 3
    timeout: int = 300  # seconds
    resource_limits: dict[str, Any] | None = None  # cpu, memory, gpu
    dependencies: list[str] | None = None
    checkpoint: str | None = None  # checkpoint function
    template: str | None = None  # template name
    template_vars: dict[str, Any] | None = None
    created_at: str = None
    updated_at: str = None


@dataclass
class TaskRun:
    """Task execution run record."""
    run_id: str
    task_id: str
    status: str
    priority: int
    attempt: int = 0
    queued_at: str | None = None
    started_at: str | None = None
    completed_at: str | None = None
    timeout_at: str | None = None
    result: Any | None = None
    error: str | None = None
    traceback: str | None = None
    checkpoint_data: bytes | None = None
    worker_id: str | None = None
    resource_usage: dict[str, Any] | None = None  # cpu%, memory, etc.
    metadata: dict[str, Any] | None = None


@dataclass
class TaskLog:
    """Task execution log entry."""
    log_id: int
    run_id: str
    timestamp: str
    level: str  # DEBUG, INFO, WARNING, ERROR
    message: str
    structured_data: dict[str, Any] | None = None


class TaskStorage:
    """SQLite storage backend with transaction support."""

    SCHEMA_VERSION = 1

    def __init__(self, db_path: str | None = None):
        """Initialize storage with given database path."""
        if db_path is None:
            db_path = str(Path.home() / ".hermes" / "task-scheduler" / "tasks.sqlite")

        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._initialize_database()

    @contextmanager
    def connection(self):
        """Get database connection with automatic commit/rollback."""
        with self._lock:
            conn = sqlite3.connect(
                self.db_path,
                timeout=30,
                check_same_thread=False
            )
            conn.row_factory = sqlite3.Row
            try:
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()

    def _initialize_database(self):
        """Create database schema if not exists."""
        with self.connection() as conn:
            # Enable WAL mode for better concurrency
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA cache_size=10000")
            conn.execute("PRAGMA mmap_size=30000000000")

            # Version table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS schema_version (
                    version INTEGER PRIMARY KEY,
                    applied_at TEXT
                )
            """)

            # Task definitions table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS task_definitions (
                    task_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    task_type TEXT NOT NULL,
                    func TEXT,
                    args TEXT,  -- JSON
                    kwargs TEXT,  -- JSON
                    priority INTEGER DEFAULT 2,
                    max_retries INTEGER DEFAULT 3,
                    timeout INTEGER DEFAULT 300,
                    resource_limits TEXT,  -- JSON
                    dependencies TEXT,  -- JSON array
                    checkpoint TEXT,
                    template TEXT,
                    template_vars TEXT,  -- JSON
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    INDEX idx_priority (priority),
                    INDEX idx_task_type (task_type)
                )
            """)

            # Task runs table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS task_runs (
                    run_id TEXT PRIMARY KEY,
                    task_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    priority INTEGER NOT NULL,
                    attempt INTEGER DEFAULT 0,
                    queued_at TEXT,
                    started_at TEXT,
                    completed_at TEXT,
                    timeout_at TEXT,
                    result BLOB,  -- pickle
                    error TEXT,
                    traceback TEXT,
                    checkpoint_data BLOB,
                    worker_id TEXT,
                    resource_usage TEXT,  -- JSON
                    metadata TEXT,  -- JSON
                    created_at TEXT NOT NULL,
                    INDEX idx_task_id (task_id),
                    INDEX idx_status (status),
                    INDEX idx_queued_at (queued_at),
                    INDEX idx_priority_status (priority, status),
                    FOREIGN KEY (task_id) REFERENCES task_definitions(task_id)
                )
            """)

            # Task logs table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS task_logs (
                    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    level TEXT NOT NULL,
                    message TEXT NOT NULL,
                    structured_data TEXT,  -- JSON
                    INDEX idx_run_id (run_id),
                    INDEX idx_timestamp (timestamp),
                    FOREIGN KEY (run_id) REFERENCES task_runs(run_id) ON DELETE CASCADE
                )
            """)

            # Dependency graph table (for DAG tracking)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS task_dependencies (
                    task_id TEXT NOT NULL,
                    depends_on TEXT NOT NULL,
                    PRIMARY KEY (task_id, depends_on),
                    INDEX idx_depends_on (depends_on),
                    FOREIGN KEY (task_id) REFERENCES task_definitions(task_id),
                    FOREIGN KEY (depends_on) REFERENCES task_definitions(task_id)
                )
            """)

            # Resource quotas table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS resource_quotas (
                    resource_type TEXT PRIMARY KEY,  -- 'global_cpu', 'global_memory', etc.
                    limit_value REAL,  -- max value
                    current_usage REAL DEFAULT 0,  -- current usage
                    updated_at TEXT
                )
            """)

            # Insert initial resource quotas
            conn.execute("""
                INSERT OR IGNORE INTO resource_quotas (resource_type, limit_value, updated_at)
                VALUES
                    ('global_cpu', 100.0, ?),
                    ('global_memory', 100.0, ?),
                    ('global_concurrent_tasks', 100, ?)
            """, (datetime.utcnow().isoformat(), datetime.utcnow().isoformat(), datetime.utcnow().isoformat()))

            # Record schema version
            conn.execute(
                "INSERT OR IGNORE INTO schema_version (version, applied_at) VALUES (?, ?)",
                (self.SCHEMA_VERSION, datetime.utcnow().isoformat())
            )

            conn.commit()

    # Task Definition Operations
    def save_task_definition(self, task: TaskDefinition) -> bool:
        """Save or update task definition."""
        now = datetime.utcnow().isoformat()
        task.created_at = now if task.created_at is None else task.created_at
        task.updated_at = now

        with self.connection() as conn:
            # Save dependencies
            if task.dependencies:
                conn.execute(
                    "DELETE FROM task_dependencies WHERE task_id = ?",
                    (task.task_id,)
                )
                for dep in task.dependencies:
                    conn.execute(
                        "INSERT OR IGNORE INTO task_dependencies (task_id, depends_on) VALUES (?, ?)",
                        (task.task_id, dep)
                    )

            # Save task
            conn.execute("""
                INSERT OR REPLACE INTO task_definitions
                (task_id, name, task_type, func, args, kwargs, priority, max_retries,
                 timeout, resource_limits, dependencies, checkpoint, template, template_vars,
                 created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                task.task_id,
                task.name,
                task.task_type,
                task.func,
                json.dumps(task.args) if task.args else None,
                json.dumps(task.kwargs) if task.kwargs else None,
                task.priority,
                task.max_retries,
                task.timeout,
                json.dumps(task.resource_limits) if task.resource_limits else None,
                json.dumps(task.dependencies) if task.dependencies else None,
                task.checkpoint,
                task.template,
                json.dumps(task.template_vars) if task.template_vars else None,
                task.created_at,
                task.updated_at
            ))
            return True

    def load_task_definition(self, task_id: str) -> TaskDefinition | None:
        """Load task definition by ID."""
        with self.connection() as conn:
            row = conn.execute(
                "SELECT * FROM task_definitions WHERE task_id = ?",
                (task_id,)
            ).fetchone()

            if not row:
                return None

            return TaskDefinition(
                task_id=row["task_id"],
                name=row["name"],
                task_type=row["task_type"],
                func=row["func"],
                args=json.loads(row["args"]) if row["args"] else None,
                kwargs=json.loads(row["kwargs"]) if row["kwargs"] else None,
                priority=row["priority"],
                max_retries=row["max_retries"],
                timeout=row["timeout"],
                resource_limits=json.loads(row["resource_limits"]) if row["resource_limits"] else None,
                dependencies=json.loads(row["dependencies"]) if row["dependencies"] else None,
                checkpoint=row["checkpoint"],
                template=row["template"],
                template_vars=json.loads(row["template_vars"]) if row["template_vars"] else None,
                created_at=row["created_at"],
                updated_at=row["updated_at"]
            )

    def list_task_definitions(self, task_type: str | None = None) -> list[TaskDefinition]:
        """List all task definitions."""
        with self.connection() as conn:
            query = "SELECT * FROM task_definitions"
            params = []

            if task_type:
                query += " WHERE task_type = ?"
                params.append(task_type)

            query += " ORDER BY created_at DESC"

            rows = conn.execute(query, params).fetchall()

            tasks = []
            for row in rows:
                tasks.append(TaskDefinition(
                    task_id=row["task_id"],
                    name=row["name"],
                    task_type=row["task_type"],
                    func=row["func"],
                    args=json.loads(row["args"]) if row["args"] else None,
                    kwargs=json.loads(row["kwargs"]) if row["kwargs"] else None,
                    priority=row["priority"],
                    max_retries=row["max_retries"],
                    timeout=row["timeout"],
                    resource_limits=json.loads(row["resource_limits"]) if row["resource_limits"] else None,
                    dependencies=json.loads(row["dependencies"]) if row["dependencies"] else None,
                    checkpoint=row["checkpoint"],
                    template=row["template"],
                    template_vars=json.loads(row["template_vars"]) if row["template_vars"] else None,
                    created_at=row["created_at"],
                    updated_at=row["updated_at"]
                ))
            return tasks

    def delete_task_definition(self, task_id: str) -> bool:
        """Delete task definition."""
        with self.connection() as conn:
            conn.execute("DELETE FROM task_dependencies WHERE task_id = ?", (task_id,))
            conn.execute("DELETE FROM task_definitions WHERE task_id = ?", (task_id,))
            return conn.total_changes > 0

    # Task Run Operations
    def create_task_run(self, run: TaskRun) -> bool:
        """Create new task run record."""
        with self.connection() as conn:
            conn.execute("""
                INSERT INTO task_runs
                (run_id, task_id, status, priority, attempt, queued_at, created_at,
                 timeout_at, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                run.run_id,
                run.task_id,
                run.status,
                run.priority,
                run.attempt,
                run.queued_at or datetime.utcnow().isoformat(),
                datetime.utcnow().isoformat(),
                run.timeout_at,
                json.dumps(run.metadata) if run.metadata else None
            ))
            return True

    def update_task_run(self, run_id: str, **updates) -> bool:
        """Update task run fields."""
        if not updates:
            return False

        set_clause = ", ".join([f"{k} = ?" for k in updates])
        values = list(updates.values())
        values.append(run_id)

        with self.connection() as conn:
            conn.execute(
                f"UPDATE task_runs SET {set_clause} WHERE run_id = ?",
                values
            )
            return conn.total_changes > 0

    def load_task_run(self, run_id: str) -> TaskRun | None:
        """Load task run by ID."""
        with self.connection() as conn:
            row = conn.execute(
                "SELECT * FROM task_runs WHERE run_id = ?",
                (run_id,)
            ).fetchone()

            if not row:
                return None

            return self._row_to_task_run(row)

    def _row_to_task_run(self, row) -> TaskRun:
        """Convert SQL row to TaskRun object."""
        result = None
        if row["result"]:
            try:
                result = pickle.loads(row["result"])
            except Exception:
                result = row["result"]  # keep as raw

        checkpoint_data = None
        if row["checkpoint_data"]:
            checkpoint_data = row["checkpoint_data"]

        resource_usage = None
        if row["resource_usage"]:
            try:
                resource_usage = json.loads(row["resource_usage"])
            except Exception:
                pass

        metadata = None
        if row["metadata"]:
            try:
                metadata = json.loads(row["metadata"])
            except Exception:
                pass

        return TaskRun(
            run_id=row["run_id"],
            task_id=row["task_id"],
            status=row["status"],
            priority=row["priority"],
            attempt=row["attempt"],
            queued_at=row["queued_at"],
            started_at=row["started_at"],
            completed_at=row["completed_at"],
            timeout_at=row["timeout_at"],
            result=result,
            error=row["error"],
            traceback=row["traceback"],
            checkpoint_data=checkpoint_data,
            worker_id=row["worker_id"],
            resource_usage=resource_usage,
            metadata=metadata
        )

    def list_task_runs(
        self,
        task_id: str | None = None,
        status: TaskStatus | str | None = None,
        limit: int = 100,
        offset: int = 0
    ) -> list[TaskRun]:
        """List task runs with filtering."""
        with self.connection() as conn:
            query = "SELECT * FROM task_runs"
            params = []

            where_clauses = []
            if task_id:
                where_clauses.append("task_id = ?")
                params.append(task_id)
            if status:
                where_clauses.append("status = ?")
                params.append(status.value if isinstance(status, TaskStatus) else status)

            if where_clauses:
                query += " WHERE " + " AND ".join(where_clauses)

            query += " ORDER BY queued_at DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])

            rows = conn.execute(query, params).fetchall()
            return [self._row_to_task_run(row) for row in rows]

    def list_pending_runs(self, priority: int | None = None, limit: int = 100) -> list[TaskRun]:
        """List runs that are queued or pending execution."""
        with self.connection() as conn:
            query = """
                SELECT * FROM task_runs
                WHERE status IN ('pending', 'queued', 'retrying')
            """
            params = []

            if priority is not None:
                query += " AND priority = ?"
                params.append(priority)

            query += " ORDER BY priority ASC, queued_at ASC LIMIT ?"
            params.append(limit)

            rows = conn.execute(query, params).fetchall()
            return [self._row_to_task_run(row) for row in rows]

    def get_runs_for_dependency_check(self) -> list[TaskRun]:
        """Get runs that need dependency checking (queued runs with unsatisfied deps)."""
        with self.connection() as conn:
            rows = conn.execute("""
                SELECT tr.* FROM task_runs tr
                JOIN task_definitions td ON tr.task_id = td.task_id
                WHERE tr.status = 'queued'
                  AND td.dependencies IS NOT NULL
                  AND json_array_length(td.dependencies) > 0
            """).fetchall()
            return [self._row_to_task_run(row) for row in rows]

    # Log Operations
    def append_log(self, run_id: str, level: str, message: str, structured_data: dict | None = None):
        """Append log entry."""
        with self.connection() as conn:
            conn.execute("""
                INSERT INTO task_logs (run_id, timestamp, level, message, structured_data)
                VALUES (?, ?, ?, ?, ?)
            """, (
                run_id,
                datetime.utcnow().isoformat(),
                level,
                message,
                json.dumps(structured_data) if structured_data else None
            ))

    def get_logs(self, run_id: str, limit: int = 1000, level: str | None = None) -> list[dict]:
        """Get logs for a run."""
        with self.connection() as conn:
            query = """
                SELECT * FROM task_logs
                WHERE run_id = ?
            """
            params = [run_id]

            if level:
                query += " AND level = ?"
                params.append(level)

            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)

            rows = conn.execute(query, params).fetchall()

            logs = []
            for row in rows:
                log = dict(row)
                if log["structured_data"]:
                    try:
                        log["structured_data"] = json.loads(log["structured_data"])
                    except Exception:
                        pass
                logs.append(log)

            return logs

    # Dependency Operations
    def get_dependencies(self, task_id: str) -> list[str]:
        """Get task dependencies."""
        with self.connection() as conn:
            rows = conn.execute(
                "SELECT depends_on FROM task_dependencies WHERE task_id = ?",
                (task_id,)
            ).fetchall()
            return [row["depends_on"] for row in rows]

    def get_dependents(self, task_id: str) -> list[str]:
        """Get tasks that depend on this task."""
        with self.connection() as conn:
            rows = conn.execute(
                "SELECT task_id FROM task_dependencies WHERE depends_on = ?",
                (task_id,)
            ).fetchall()
            return [row["task_id"] for row in rows]

    # Resource Quota Operations
    def acquire_resource(self, resource_type: str, amount: float) -> bool:
        """Try to acquire resource quota."""
        with self.connection() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                row = conn.execute(
                    "SELECT limit_value, current_usage FROM resource_quotas WHERE resource_type = ?",
                    (resource_type,)
                ).fetchone()

                if not row:
                    return False

                new_usage = row["current_usage"] + amount
                if new_usage > row["limit_value"]:
                    return False

                conn.execute(
                    "UPDATE resource_quotas SET current_usage = ?, updated_at = ? WHERE resource_type = ?",
                    (new_usage, datetime.utcnow().isoformat(), resource_type)
                )
                conn.commit()
                return True
            except Exception:
                conn.rollback()
                raise

    def release_resource(self, resource_type: str, amount: float):
        """Release resource quota."""
        with self.connection() as conn:
            conn.execute(
                "UPDATE resource_quotas SET current_usage = current_usage - ?, updated_at = ? WHERE resource_type = ?",
                (amount, datetime.utcnow().isoformat(), resource_type)
            )

    def get_resource_usage(self) -> dict[str, dict[str, float]]:
        """Get current resource usage."""
        with self.connection() as conn:
            rows = conn.execute("SELECT * FROM resource_quotas").fetchall()
            return {
                row["resource_type"]: {
                    "limit": row["limit_value"],
                    "current": row["current_usage"],
                    "available": row["limit_value"] - row["current_usage"]
                }
                for row in rows
            }

    # Statistics
    def get_statistics(self) -> dict[str, Any]:
        """Get scheduler statistics."""
        with self.connection() as conn:
            stats = {}

            # Count by status
            cursor = conn.execute("""
                SELECT status, COUNT(*) as count
                FROM task_runs
                GROUP BY status
            """)
            stats["runs_by_status"] = {row["status"]: row["count"] for row in cursor}

            # Total tasks defined
            cursor = conn.execute("SELECT COUNT(*) as count FROM task_definitions")
            stats["total_task_definitions"] = cursor.fetchone()["count"]

            # Recent runs (last hour)
            cutoff = (datetime.utcnow() - timedelta(hours=1)).isoformat()
            cursor = conn.execute(
                "SELECT COUNT(*) as count FROM task_runs WHERE queued_at >= ?",
                (cutoff,)
            )
            stats["runs_last_hour"] = cursor.fetchone()["count"]

            # Success rate (last 24h)
            cutoff = (datetime.utcnow() - timedelta(days=1)).isoformat()
            cursor = conn.execute("""
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
                    SUM(CASE WHEN status IN ('failed', 'timeout') THEN 1 ELSE 0 END) as failed
                FROM task_runs
                WHERE queued_at >= ?
            """, (cutoff,))
            row = cursor.fetchone()
            if row["total"] > 0:
                stats["success_rate_24h"] = row["completed"] / row["total"]
                stats["failure_rate_24h"] = row["failed"] / row["total"]
            else:
                stats["success_rate_24h"] = 0.0
                stats["failure_rate_24h"] = 0.0

            # Average execution time (completed runs)
            cursor = conn.execute("""
                SELECT AVG(
                    (julianday(completed_at) - julianday(started_at)) * 86400
                ) as avg_seconds
                FROM task_runs
                WHERE status = 'completed' AND started_at IS NOT NULL AND completed_at IS NOT NULL
            """)
            avg = cursor.fetchone()["avg_seconds"]
            stats["avg_execution_seconds"] = avg or 0.0

            return stats

    def cleanup_old_runs(self, days: int = 30) -> int:
        """Cleanup old task run records."""
        cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
        with self.connection() as conn:
            # Get count first
            cursor = conn.execute(
                "SELECT COUNT(*) as count FROM task_runs WHERE queued_at < ? AND status IN ('completed', 'failed', 'cancelled', 'timeout')",
                (cutoff,)
            )
            count = cursor.fetchone()["count"]

            # Delete old runs (logs cascade)
            conn.execute(
                "DELETE FROM task_runs WHERE queued_at < ? AND status IN ('completed', 'failed', 'cancelled', 'timeout')",
                (cutoff,)
            )
            return count

    def reset_resource_quotas(self):
        """Reset all resource quotas to zero usage."""
        with self.connection() as conn:
            conn.execute(
                "UPDATE resource_quotas SET current_usage = 0, updated_at = ?",
                (datetime.utcnow().isoformat(),)
            )
