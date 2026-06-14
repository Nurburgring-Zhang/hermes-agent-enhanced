"""
Workflow Storage Module
Handles persistence of workflow definitions and execution state using SQLite.
"""
import json
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from workflow_definitions import (
    StepStatus,
    Workflow,
    WorkflowStatus,
    WorkflowStep,
)


class WorkflowStorage:
    """
    SQLite-based storage for workflow definitions and execution state.
    Database file: ~/.hermes/workflows/registry.sqlite (or custom path)
    """

    def __init__(self, db_path: str = None):
        self.db_path = Path(db_path) if db_path else Path.home() / ".hermes" / "workflows" / "registry.sqlite"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize_database()

    def _initialize_database(self):
        """Create tables if they don't exist"""
        with self._connect() as conn:
            cursor = conn.cursor()

            # Workflow definitions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS workflows (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    version TEXT NOT NULL,
                    description TEXT,
                    definition_json TEXT NOT NULL,
                    tags TEXT,  -- JSON array
                    created_by TEXT,
                    created_at INTEGER NOT NULL,
                    updated_at INTEGER NOT NULL,
                    is_active INTEGER DEFAULT 1
                )
            """)

            # Indexes for workflows
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_workflows_active ON workflows(is_active)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_workflows_created_at ON workflows(created_at DESC)")

            # Workflow runs table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS flow_runs (
                    run_id TEXT PRIMARY KEY,
                    workflow_id TEXT NOT NULL,
                    revision INTEGER DEFAULT 0,
                    status TEXT NOT NULL,
                    notify_policy TEXT DEFAULT 'on_completion',
                    goal TEXT,
                    trigger_type TEXT DEFAULT 'manual',
                    trigger_by TEXT,
                    input_variables_json TEXT,
                    initial_context_json TEXT,
                    final_context_json TEXT,
                    error_message TEXT,
                    error_details TEXT,
                    started_at INTEGER NOT NULL,
                    updated_at INTEGER NOT NULL,
                    completed_at INTEGER,
                    FOREIGN KEY (workflow_id) REFERENCES workflows(id) ON DELETE RESTRICT
                )
            """)

            # Indexes for flow_runs
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_flow_runs_workflow_id ON flow_runs(workflow_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_flow_runs_status ON flow_runs(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_flow_runs_started_at ON flow_runs(started_at DESC)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_flow_runs_trigger_by ON flow_runs(trigger_by)")

            # Step executions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS flow_steps (
                    step_exec_id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL,
                    workflow_id TEXT NOT NULL,
                    step_id TEXT NOT NULL,
                    step_type TEXT NOT NULL,
                    step_name TEXT,
                    status TEXT NOT NULL,
                    parameters_json TEXT,
                    input_vars_json TEXT,
                    output_vars_json TEXT,
                    result_json TEXT,
                    error_message TEXT,
                    error_details TEXT,
                    retry_count INTEGER DEFAULT 0,
                    started_at INTEGER NOT NULL,
                    updated_at INTEGER NOT NULL,
                    completed_at INTEGER,
                    duration_ms INTEGER,
                    FOREIGN KEY (run_id) REFERENCES flow_runs(run_id) ON DELETE CASCADE
                )
            """)

            # Indexes for flow_steps
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_flow_steps_run_id ON flow_steps(run_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_flow_steps_status ON flow_steps(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_flow_steps_step_id ON flow_steps(step_id)")

            # Workflow templates table (for reusable templates)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS workflow_templates (
                    template_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    category TEXT,
                    definition_json TEXT NOT NULL,
                    tags TEXT,  -- JSON array
                    created_by TEXT,
                    created_at INTEGER NOT NULL,
                    updated_at INTEGER NOT NULL,
                    usage_count INTEGER DEFAULT 0
                )
            """)

            # Workflow events table (for audit and monitoring)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS workflow_events (
                    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL,
                    step_id TEXT,
                    event_type TEXT NOT NULL,  -- 'state_change', 'error', 'retry', 'timeout', 'compensation'
                    event_data TEXT,  -- JSON
                    timestamp INTEGER NOT NULL,
                    FOREIGN KEY (run_id) REFERENCES flow_runs(run_id) ON DELETE CASCADE
                )
            """)

            cursor.execute("CREATE INDEX IF NOT EXISTS idx_workflow_events_run_id ON workflow_events(run_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_workflow_events_timestamp ON workflow_events(timestamp DESC)")

            # Check and add missing columns (schema migrations)
            self._migrate_schema(conn)

            conn.commit()

    def _migrate_schema(self, conn):
        """Apply schema migrations as needed"""
        cursor = conn.cursor()

        # Get current schema
        cursor.execute("PRAGMA table_info(workflows)")
        workflow_columns = {col[1] for col in cursor.fetchall()}

        # Example: Add new columns if missing
        # (This can be expanded for future migrations)
        if "is_active" not in workflow_columns:
            cursor.execute("ALTER TABLE workflows ADD COLUMN is_active INTEGER DEFAULT 1")
            print("Migrated: Added is_active column to workflows")

    @contextmanager
    def _connect(self):
        """Get a database connection"""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row  # Return rows as dict-like objects
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    # ==================== Workflow Definitions ====================

    def save_workflow(self, workflow: Workflow) -> bool:
        """Save a workflow definition"""
        try:
            with self._connect() as conn:
                cursor = conn.cursor()
                now = int(time.time() * 1000)

                cursor.execute("""
                    INSERT OR REPLACE INTO workflows
                    (id, name, version, description, definition_json, tags,
                     created_by, created_at, updated_at, is_active)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    workflow.id,
                    workflow.name,
                    workflow.version,
                    workflow.description,
                    json.dumps(workflow.to_dict(), ensure_ascii=False),
                    json.dumps(workflow.tags) if workflow.tags else None,
                    workflow.created_by,
                    workflow.created_at or now,
                    now,
                    1
                ))
                return True
        except Exception as e:
            print(f"Error saving workflow: {e}")
            return False

    def load_workflow(self, workflow_id: str) -> Workflow | None:
        """Load a workflow definition by ID"""
        try:
            with self._connect() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT definition_json FROM workflows
                    WHERE id = ? AND is_active = 1
                """, (workflow_id,))
                row = cursor.fetchone()
                if row:
                    definition = json.loads(row["definition_json"])
                    return Workflow.from_dict(definition)
        except Exception as e:
            print(f"Error loading workflow {workflow_id}: {e}")
        return None

    def list_workflows(self, active_only: bool = True, tags: list[str] = None) -> list[dict]:
        """List all workflows with basic info"""
        try:
            with self._connect() as conn:
                cursor = conn.cursor()
                query = """
                    SELECT id, name, version, description, tags, created_by,
                           created_at, updated_at, is_active
                    FROM workflows
                """
                params = []
                if active_only:
                    query += " WHERE is_active = 1"
                if tags:
                    tag_conditions = " OR ".join(["tags LIKE ?"] * len(tags))
                    if active_only:
                        query += " AND (" + tag_conditions + ")"
                    else:
                        query += " WHERE " + tag_conditions
                    params.extend([f'%"{tag}"%' for tag in tags])

                query += " ORDER BY updated_at DESC"
                cursor.execute(query, params)
                rows = cursor.fetchall()

                result = []
                for row in rows:
                    result.append({
                        "id": row["id"],
                        "name": row["name"],
                        "version": row["version"],
                        "description": row["description"],
                        "tags": json.loads(row["tags"]) if row["tags"] else [],
                        "created_by": row["created_by"],
                        "created_at": row["created_at"],
                        "updated_at": row["updated_at"],
                        "is_active": bool(row["is_active"])
                    })
                return result
        except Exception as e:
            print(f"Error listing workflows: {e}")
            return []

    def delete_workflow(self, workflow_id: str) -> bool:
        """Soft delete a workflow (set is_active=0)"""
        try:
            with self._connect() as conn:
                cursor = conn.cursor()
                now = int(time.time() * 1000)
                cursor.execute("""
                    UPDATE workflows
                    SET is_active = 0, updated_at = ?
                    WHERE id = ?
                """, (now, workflow_id))
                return cursor.rowcount > 0
        except Exception as e:
            print(f"Error deleting workflow: {e}")
            return False

    # ==================== Workflow Runs ====================

    def create_run(self, workflow_id: str, run_id: str, goal: str = None,
                   trigger_type: str = "manual", trigger_by: str = None,
                   input_variables: dict = None, initial_context: dict = None) -> str | None:
        """Create a new workflow run record"""
        try:
            with self._connect() as conn:
                cursor = conn.cursor()
                now = int(time.time() * 1000)

                cursor.execute("""
                    INSERT INTO flow_runs
                    (run_id, workflow_id, status, notify_policy, goal,
                     trigger_type, trigger_by, input_variables_json,
                     initial_context_json, started_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    run_id,
                    workflow_id,
                    "running",
                    "on_completion",
                    goal,
                    trigger_type,
                    trigger_by,
                    json.dumps(input_variables) if input_variables else None,
                    json.dumps(initial_context) if initial_context else None,
                    now,
                    now
                ))
                return run_id
        except Exception as e:
            print(f"Error creating run: {e}")
        return None

    def update_run_status(self, run_id: str, status: WorkflowStatus,
                         error_message: str = None, error_details: str = None,
                         final_context: dict = None) -> bool:
        """Update workflow run status"""
        try:
            with self._connect() as conn:
                cursor = conn.cursor()
                now = int(time.time() * 1000)

                fields = ["status = ?", "updated_at = ?"]
                params = [status.value, now]

                if status in [WorkflowStatus.COMPLETED, WorkflowStatus.FAILED, WorkflowStatus.CANCELLED]:
                    fields.append("completed_at = ?")
                    params.append(now)
                    if final_context:
                        fields.append("final_context_json = ?")
                        params.append(json.dumps(final_context, ensure_ascii=False))

                if error_message:
                    fields.append("error_message = ?")
                    params.append(error_message)
                if error_details:
                    fields.append("error_details = ?")
                    params.append(error_details)

                params.append(run_id)
                query = f"UPDATE flow_runs SET {', '.join(fields)} WHERE run_id = ?"
                cursor.execute(query, params)
                return cursor.rowcount > 0
        except Exception as e:
            print(f"Error updating run {run_id}: {e}")
        return False

    def get_run(self, run_id: str) -> dict | None:
        """Get workflow run details"""
        try:
            with self._connect() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM flow_runs WHERE run_id = ?", (run_id,))
                row = cursor.fetchone()
                if row:
                    return dict(row)
        except Exception as e:
            print(f"Error getting run {run_id}: {e}")
        return None

    def list_runs(self, workflow_id: str = None, status: WorkflowStatus = None,
                  limit: int = 50, offset: int = 0) -> list[dict]:
        """List workflow runs with optional filters"""
        try:
            with self._connect() as conn:
                cursor = conn.cursor()
                query = "SELECT * FROM flow_runs"
                params = []
                conditions = []

                if workflow_id:
                    conditions.append("workflow_id = ?")
                    params.append(workflow_id)
                if status:
                    conditions.append("status = ?")
                    params.append(status.value)

                if conditions:
                    query += " WHERE " + " AND ".join(conditions)

                query += " ORDER BY started_at DESC LIMIT ? OFFSET ?"
                params.extend([limit, offset])

                cursor.execute(query, params)
                rows = cursor.fetchall()

                result = []
                for row in rows:
                    result.append(dict(row))
                return result
        except Exception as e:
            print(f"Error listing runs: {e}")
            return []

    def get_latest_run(self, workflow_id: str) -> dict | None:
        """Get the most recent run for a workflow"""
        runs = self.list_runs(workflow_id=workflow_id, limit=1)
        return runs[0] if runs else None

    # ==================== Step Executions ====================

    def create_step_execution(self, run_id: str, workflow_id: str, step_id: str,
                             step_type: str, step_name: str, parameters: dict = None) -> str:
        """Create a step execution record"""
        step_exec_id = f"step_{step_id}_{run_id}_{int(time.time() * 1000)}"
        try:
            with self._connect() as conn:
                cursor = conn.cursor()
                now = int(time.time() * 1000)

                cursor.execute("""
                    INSERT INTO flow_steps
                    (step_exec_id, run_id, workflow_id, step_id, step_type, step_name,
                     status, parameters_json, started_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    step_exec_id,
                    run_id,
                    workflow_id,
                    step_id,
                    step_type,
                    step_name,
                    "pending",
                    json.dumps(parameters) if parameters else None,
                    now,
                    now
                ))
                return step_exec_id
        except Exception as e:
            print(f"Error creating step execution: {e}")
        return None

    def start_step(self, step_exec_id: str, input_vars: dict = None) -> bool:
        """Mark a step as running"""
        try:
            with self._connect() as conn:
                cursor = conn.cursor()
                now = int(time.time() * 1000)

                cursor.execute("""
                    UPDATE flow_steps
                    SET status = ?, input_vars_json = ?, started_at = ?, updated_at = ?
                    WHERE step_exec_id = ?
                """, (
                    "running",
                    json.dumps(input_vars) if input_vars else None,
                    now,
                    now,
                    step_exec_id
                ))
                return cursor.rowcount > 0
        except Exception as e:
            print(f"Error starting step {step_exec_id}: {e}")
        return False

    def complete_step(self, step_exec_id: str, status: StepStatus,
                     output_vars: dict = None, result: Any = None,
                     error_message: str = None, error_details: str = None) -> bool:
        """Mark a step as completed (success or failure)"""
        try:
            with self._connect() as conn:
                cursor = conn.cursor()
                now = int(time.time() * 1000)

                # Get start time to calculate duration
                cursor.execute("SELECT started_at FROM flow_steps WHERE step_exec_id = ?", (step_exec_id,))
                row = cursor.fetchone()
                started_at = row["started_at"] if row else now
                duration_ms = (now - started_at) if started_at else 0

                cursor.execute("""
                    UPDATE flow_steps
                    SET status = ?,
                        output_vars_json = ?,
                        result_json = ?,
                        error_message = ?,
                        error_details = ?,
                        completed_at = ?,
                        duration_ms = ?,
                        updated_at = ?
                    WHERE step_exec_id = ?
                """, (
                    status.value,
                    json.dumps(output_vars) if output_vars else None,
                    json.dumps(result) if result else None,
                    error_message,
                    error_details,
                    now if status in [StepStatus.COMPLETED, StepStatus.FAILED, StepStatus.TIMEOUT, StepStatus.CANCELLED] else None,
                    duration_ms,
                    now,
                    step_exec_id
                ))
                return cursor.rowcount > 0
        except Exception as e:
            print(f"Error completing step {step_exec_id}: {e}")
        return False

    def get_step_executions(self, run_id: str) -> list[dict]:
        """Get all step executions for a run"""
        try:
            with self._connect() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM flow_steps
                    WHERE run_id = ?
                    ORDER BY started_at ASC
                """, (run_id,))
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            print(f"Error getting step executions for {run_id}: {e}")
        return []

    def get_step_execution(self, step_exec_id: str) -> dict | None:
        """Get a specific step execution"""
        try:
            with self._connect() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM flow_steps WHERE step_exec_id = ?", (step_exec_id,))
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            print(f"Error getting step execution {step_exec_id}: {e}")
        return None

    # ==================== Workflow Templates ====================

    def save_template(self, template_id: str, name: str, definition: dict,
                     description: str = "", category: str = None,
                     tags: list[str] = None, created_by: str = None) -> bool:
        """Save a workflow template"""
        try:
            with self._connect() as conn:
                cursor = conn.cursor()
                now = int(time.time() * 1000)

                cursor.execute("""
                    INSERT OR REPLACE INTO workflow_templates
                    (template_id, name, description, category, definition_json,
                     tags, created_by, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    template_id,
                    name,
                    description,
                    category,
                    json.dumps(definition, ensure_ascii=False),
                    json.dumps(tags) if tags else None,
                    created_by,
                    now,
                    now
                ))
                return True
        except Exception as e:
            print(f"Error saving template: {e}")
        return False

    def load_template(self, template_id: str) -> dict | None:
        """Load a workflow template"""
        try:
            with self._connect() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT definition_json FROM workflow_templates WHERE template_id = ?", (template_id,))
                row = cursor.fetchone()
                if row:
                    return json.loads(row["definition_json"])
        except Exception as e:
            print(f"Error loading template {template_id}: {e}")
        return None

    def increment_template_usage(self, template_id: str):
        """Increment usage count for a template"""
        try:
            with self._connect() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE workflow_templates
                    SET usage_count = usage_count + 1
                    WHERE template_id = ?
                """, (template_id,))
        except Exception as e:
            print(f"Error incrementing template usage: {e}")

    # ==================== Events ====================

    def log_event(self, run_id: str, event_type: str, step_id: str = None,
                  event_data: dict = None) -> bool:
        """Log a workflow event for audit/monitoring"""
        try:
            with self._connect() as conn:
                cursor = conn.cursor()
                now = int(time.time() * 1000)

                cursor.execute("""
                    INSERT INTO workflow_events (run_id, step_id, event_type, event_data, timestamp)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    run_id,
                    step_id,
                    event_type,
                    json.dumps(event_data) if event_data else None,
                    now
                ))
                return True
        except Exception as e:
            print(f"Error logging event: {e}")
        return False

    def get_run_events(self, run_id: str, limit: int = 100) -> list[dict]:
        """Get events for a run"""
        try:
            with self._connect() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM workflow_events
                    WHERE run_id = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (run_id, limit))
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            print(f"Error getting events for {run_id}: {e}")
        return []

    # ==================== Statistics ====================

    def get_statistics(self) -> dict:
        """Get workflow execution statistics"""
        try:
            with self._connect() as conn:
                cursor = conn.cursor()

                stats = {}

                # Total counts
                cursor.execute("SELECT COUNT(*) as count FROM workflows WHERE is_active = 1")
                stats["total_workflows"] = cursor.fetchone()["count"]

                cursor.execute("SELECT COUNT(*) as count FROM flow_runs")
                stats["total_runs"] = cursor.fetchone()["count"]

                # Runs by status
                cursor.execute("SELECT status, COUNT(*) as count FROM flow_runs GROUP BY status")
                stats["runs_by_status"] = {row["status"]: row["count"] for row in cursor.fetchall()}

                # Recent activity
                week_ago = int(time.time() * 1000) - (7 * 24 * 60 * 60 * 1000)
                cursor.execute("SELECT COUNT(*) as count FROM flow_runs WHERE started_at > ?", (week_ago,))
                stats["runs_last_week"] = cursor.fetchone()["count"]

                # Average run duration
                cursor.execute("""
                    SELECT AVG(
                        (COALESCE(completed_at, ?) - started_at) / 1000.0
                    ) as avg_duration
                    FROM flow_runs
                    WHERE status IN ('completed', 'failed')
                """, (int(time.time() * 1000),))
                stats["avg_duration_sec"] = round(cursor.fetchone()["avg_duration"] or 0, 2)

                return stats
        except Exception as e:
            print(f"Error getting statistics: {e}")
            return {}


if __name__ == "__main__":
    # Test storage
    storage = WorkflowStorage("/tmp/test_workflows.sqlite")
    print("Database initialized at:", storage.db_path)

    # Test save and load
    from workflow_definitions import StepType, Workflow, WorkflowStep

    wf = Workflow(
        id="test_wf",
        name="Test Workflow",
        start_step_id="step1",
        steps={
            "step1": WorkflowStep(
                id="step1",
                type=StepType.TASK,
                name="Step 1",
                action="test_action"
            )
        }
    )

    success = storage.save_workflow(wf)
    print(f"Save workflow: {success}")

    loaded = storage.load_workflow("test_wf")
    print(f"Loaded workflow: {loaded.name if loaded else None}")

    stats = storage.get_statistics()
    print(f"Statistics: {stats}")
