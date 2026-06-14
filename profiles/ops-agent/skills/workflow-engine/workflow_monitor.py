"""
Workflow Monitor Module
Provides monitoring, logging, metrics, and visualization capabilities.
"""
import json
import statistics
import threading
import time
from collections import defaultdict, deque
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any


class WorkflowMonitor:
    """
    Monitors workflow executions in real-time.
    Features:
    - Live status tracking
    - Performance metrics
    - Event streaming
    - Log aggregation
    - Alerting
    """

    def __init__(self, storage: "WorkflowStorage", engine: "WorkflowEngine" = None):
        self.storage = storage
        self.engine = engine
        self._listeners: list[Callable] = []
        self._event_buffer = deque(maxlen=1000)
        self._metrics_lock = threading.RLock()
        self._metrics = self._init_metrics()
        self._running = False
        self._monitor_thread: threading.Thread | None = None

        # Register event listener if engine provided
        if engine:
            engine.add_event_listener(self._on_event)

    def _init_metrics(self) -> dict:
        """Initialize metrics"""
        return {
            "total_runs": 0,
            "active_runs": 0,
            "completed_runs": 0,
            "failed_runs": 0,
            "cancelled_runs": 0,
            "avg_duration_sec": 0.0,
            "step_success_rate": defaultdict(lambda: {"total": 0, "success": 0}),
            "recent_runs": deque(maxlen=100),
            "errors_by_type": defaultdict(int),
            "throughput_per_minute": deque(maxlen=60),  # rolling 1-hour
        }

    def start_monitoring(self, refresh_interval: float = 1.0):
        """Start background monitoring thread"""
        if self._running:
            return
        self._running = True
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            args=(refresh_interval,),
            daemon=True,
            name="workflow-monitor"
        )
        self._monitor_thread.start()

    def stop_monitoring(self):
        """Stop monitoring thread"""
        self._running = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=2)

    def _monitor_loop(self, interval: float):
        """Background monitoring loop"""
        while self._running:
            try:
                self._refresh_metrics()
            except Exception as e:
                print(f"Monitor error: {e}")
            time.sleep(interval)

    def _refresh_metrics(self):
        """Refresh all metrics from storage"""
        with self._metrics_lock:
            # Get statistics from storage
            stats = self.storage.get_statistics()

            self._metrics["total_runs"] = stats.get("total_runs", 0)

            # Count runs by status
            status_counts = stats.get("runs_by_status", {})
            self._metrics["completed_runs"] = status_counts.get("completed", 0)
            self._metrics["failed_runs"] = status_counts.get("failed", 0)
            self._metrics["cancelled_runs"] = status_counts.get("cancelled", 0)
            self._metrics["active_runs"] = self._metrics["total_runs"] - (
                self._metrics["completed_runs"] +
                self._metrics["failed_runs"] +
                self._metrics["cancelled_runs"]
            )
            self._metrics["avg_duration_sec"] = stats.get("avg_duration_sec", 0.0)

            # Get recent runs for throughput calculation
            recent = self.storage.list_runs(limit=60)
            now = time.time()
            runs_last_hour = sum(
                1 for r in recent
                if r["started_at"] / 1000 > now - 3600
            )
            self._metrics["throughput_per_minute"].append(runs_last_hour / 60.0)

            # Active runs count if engine is running
            if self.engine:
                with self.engine._lock:
                    self._metrics["active_runs"] = len(self.engine._running_runs)

    def _on_event(self, event: dict):
        """Handle incoming event from engine"""
        self._event_buffer.append(event)
        # Notify listeners
        for listener in self._listeners:
            try:
                listener(event)
            except Exception as e:
                print(f"Monitor listener error: {e}")

    def add_listener(self, listener: Callable):
        """Add an event listener"""
        self._listeners.append(listener)

    def get_recent_events(self, limit: int = 50, event_type: str = None) -> list[dict]:
        """Get recent events, optionally filtered by type"""
        events = list(self._event_buffer)
        if event_type:
            events = [e for e in events if e["event_type"] == event_type]
        return events[-limit:]

    def get_metrics(self) -> dict:
        """Get current metrics snapshot"""
        with self._metrics_lock:
            return {
                "timestamp": time.time(),
                "runs": {
                    "total": self._metrics["total_runs"],
                    "active": self._metrics["active_runs"],
                    "completed": self._metrics["completed_runs"],
                    "failed": self._metrics["failed_runs"],
                    "cancelled": self._metrics["cancelled_runs"]
                },
                "performance": {
                    "avg_duration_sec": self._metrics["avg_duration_sec"],
                    "throughput_per_minute": statistics.mean(self._metrics["throughput_per_minute"]) if self._metrics["throughput_per_minute"] else 0.0
                },
                "step_success_rate": dict(self._metrics["step_success_rate"]),
                "errors_by_type": dict(self._metrics["errors_by_type"])
            }

    def get_run_timeline(self, run_id: str) -> list[dict]:
        """Get detailed timeline for a specific run"""
        events = self.storage.get_run_events(run_id, limit=200)
        steps = self.storage.get_step_executions(run_id)

        timeline = []

        # Add step events
        for step in steps:
            timeline.append({
                "timestamp": step["started_at"],
                "type": "step_start",
                "step_id": step["step_id"],
                "step_name": step.get("step_name", step["step_id"])
            })
            if step["completed_at"]:
                timeline.append({
                    "timestamp": step["completed_at"],
                    "type": "step_end",
                    "step_id": step["step_id"],
                    "duration_ms": step.get("duration_ms"),
                    "status": step["status"]
                })

        # Add workflow events
        for event in events:
            timeline.append({
                "timestamp": event["timestamp"],
                "type": "event",
                "event_type": event["event_type"],
                "step_id": event.get("step_id")
            })

        # Sort by timestamp
        timeline.sort(key=lambda x: x["timestamp"])

        return timeline

    def get_run_summary(self, run_id: str) -> dict | None:
        """Get comprehensive summary of a workflow run"""
        run_data = self.storage.get_run(run_id)
        if not run_data:
            return None

        steps = self.storage.get_step_executions(run_id)
        events = self.storage.get_run_events(run_id, limit=100)

        # Calculate statistics
        total_duration = 0
        step_stats = []
        for step in steps:
            duration = step.get("duration_ms", 0) / 1000.0
            total_duration += duration
            step_stats.append({
                "step_id": step["step_id"],
                "step_name": step.get("step_name", step["step_id"]),
                "status": step["status"],
                "duration_sec": duration,
                "retry_count": step.get("retry_count", 0)
            })

        return {
            "run_id": run_id,
            "workflow_id": run_data["workflow_id"],
            "status": run_data["status"],
            "goal": run_data.get("goal"),
            "started_at": run_data["started_at"],
            "completed_at": run_data.get("completed_at"),
            "total_duration_sec": total_duration / 1000.0 if steps else None,
            "steps": step_stats,
            "num_steps": len(steps),
            "errors": [e for e in events if e.get("event_type") == "step_failed"],
            "error_count": sum(1 for s in steps if s["status"] == "failed")
        }

    def tail_logs(self, run_id: str = None, follow: bool = False,
                  limit: int = 50) -> list[dict]:
        """Tail log-like events (errors, warnings, info)"""
        if run_id:
            events = self.storage.get_run_events(run_id, limit=1000)
        else:
            events = list(self._event_buffer)

        # Filter log events
        log_events = []
        for e in events[-limit:]:
            if e["event_type"] in ["workflow_started", "workflow_completed",
                                   "workflow_failed", "step_completed",
                                   "step_failed", "step_retry"]:
                log_events.append({
                    "timestamp": datetime.fromtimestamp(e["timestamp"]).strftime("%H:%M:%S"),
                    "type": e["event_type"],
                    "step_id": e.get("step_id"),
                    "data": e.get("event_data", {})
                })

        return log_events

    def get_dashboard_data(self) -> dict:
        """Get data for a dashboard view"""
        metrics = self.get_metrics()

        # Get top workflows by run count
        top_workflows = self._get_top_workflows(limit=10)

        # Get recent runs
        recent_runs = self.storage.list_runs(limit=20)

        # Get current active runs details
        active_runs = []
        if self.engine:
            with self.engine._lock:
                for run_id, exec_obj in self.engine._running_runs.items():
                    active_runs.append({
                        "run_id": run_id,
                        "workflow_id": exec_obj.workflow.id,
                        "workflow_name": exec_obj.workflow.name,
                        "current_step": exec_obj.context.current_step_id,
                        "elapsed_sec": time.time() - exec_obj.context.started_at
                    })

        return {
            "metrics": metrics,
            "top_workflows": top_workflows,
            "recent_runs": recent_runs,
            "active_runs": active_runs,
            "timestamp": datetime.now().isoformat()
        }

    def _get_top_workflows(self, limit: int = 10) -> list[dict]:
        """Get top workflows by run count"""
        try:
            with self.storage._connect() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT workflow_id, COUNT(*) as run_count,
                           SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
                           SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed
                    FROM flow_runs
                    WHERE started_at > ?
                    GROUP BY workflow_id
                    ORDER BY run_count DESC
                    LIMIT ?
                """, (int((time.time() - 86400) * 1000), limit))  # Last 24 hours

                results = []
                for row in cursor.fetchall():
                    total = row["run_count"]
                    results.append({
                        "workflow_id": row["workflow_id"],
                        "runs": total,
                        "success_rate": (row["completed"] or 0) / total if total > 0 else 0,
                        "failed": row["failed"] or 0
                    })
                return results
        except Exception as e:
            print(f"Error getting top workflows: {e}")
            return []

    def export_run_report(self, run_id: str, output_path: str = None) -> str | None:
        """Export a detailed run report as JSON/Markdown"""
        summary = self.get_run_summary(run_id)
        if not summary:
            return None

        if not output_path:
            output_path = f"./workflow_report_{run_id}.json"

        with open(output_path, "w") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)

        return output_path

    def generate_html_report(self, run_id: str, output_path: str = None) -> str | None:
        """Generate an HTML report for a run"""
        summary = self.get_run_summary(run_id)
        if not summary:
            return None

        # Simple HTML template
        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Workflow Run Report: {run_id}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background: #f5f5f5; padding: 15px; border-radius: 5px; }}
        .metric {{ display: inline-block; margin: 10px; }}
        .metric-value {{ font-size: 24px; font-weight: bold; }}
        .steps {{ margin-top: 20px; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }}
        .success {{ background-color: #d4edda; }}
        .failed {{ background-color: #f8d7da; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Workflow Run Report</h1>
        <div class="metric">
            <div>Run ID</div>
            <div class="metric-value">{run_id}</div>
        </div>
        <div class="metric">
            <div>Status</div>
            <div class="metric-value">{summary['status']}</div>
        </div>
        <div class="metric">
            <div>Total Duration</div>
            <div class="metric-value">{summary['total_duration_sec']:.2f}s</div>
        </div>
        <div class="metric">
            <div>Steps</div>
            <div class="metric-value">{summary['num_steps']}</div>
        </div>
    </div>

    <div class="steps">
        <h2>Step Details</h2>
        <table>
            <tr>
                <th>Step</th>
                <th>Status</th>
                <th>Duration (s)</th>
                <th>Retries</th>
            </tr>
"""

        for step in summary["steps"]:
            status_class = "success" if step["status"] == "completed" else "failed" if step["status"] == "failed" else ""
            html += f"""
            <tr class="{status_class}">
                <td>{step['step_name']} ({step['step_id']})</td>
                <td>{step['status']}</td>
                <td>{step['duration_sec']:.3f}</td>
                <td>{step.get('retry_count', 0)}</td>
            </tr>
"""

        html += """
        </table>
    </div>
</body>
</html>
"""

        if not output_path:
            output_path = f"./workflow_report_{run_id}.html"

        with open(output_path, "w") as f:
            f.write(html)

        return output_path


class LogAggregator:
    """Aggregates logs from multiple sources for workflows"""

    def __init__(self, log_dir: str = None):
        self.log_dir = Path(log_dir) if log_dir else Path.home() / ".hermes" / "logs" / "workflows"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self._file_handles: dict[str, Any] = {}

    def write_log(self, run_id: str, message: str, level: str = "INFO",
                  step_id: str = None, **kwargs):
        """Write a log entry for a run"""
        log_entry = {
            "timestamp": time.time(),
            "run_id": run_id,
            "level": level,
            "message": message,
            "step_id": step_id,
            **kwargs
        }

        log_line = json.dumps(log_entry, ensure_ascii=False)

        # Write to file
        log_file = self.log_dir / f"run_{run_id}.jsonl"
        with open(log_file, "a") as f:
            f.write(log_line + "\n")

        # Also maintain a combined recent log
        recent_log = self.log_dir / "recent.jsonl"
        with open(recent_log, "a") as f:
            f.write(log_line + "\n")

        # Rotate recent log if too large
        if recent_log.stat().st_size > 10 * 1024 * 1024:  # 10 MB
            self._rotate_recent_log()

    def _rotate_recent_log(self):
        """Rotate the recent log file"""
        recent_log = self.log_dir / "recent.jsonl"
        archived = self.log_dir / f"recent_{int(time.time())}.jsonl"
        recent_log.rename(archived)
        # Create new empty recent log
        open(recent_log, "w").close()

    def get_run_logs(self, run_id: str, level: str = None,
                     limit: int = 100) -> list[dict]:
        """Get logs for a specific run"""
        log_file = self.log_dir / f"run_{run_id}.jsonl"
        if not log_file.exists():
            return []

        logs = []
        with open(log_file) as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    if level and entry.get("level") != level:
                        continue
                    logs.append(entry)
                except:
                    continue

        return logs[-limit:]

    def search_logs(self, query: str, run_id: str = None,
                    limit: int = 100) -> list[dict]:
        """Search logs by message content"""
        results = []
        log_files = []

        if run_id:
            log_file = self.log_dir / f"run_{run_id}.jsonl"
            if log_file.exists():
                log_files.append(log_file)
        else:
            # Search all run logs
            log_files = list(self.log_dir.glob("run_*.jsonl"))

        for log_file in log_files:
            try:
                with open(log_file) as f:
                    for line in f:
                        try:
                            entry = json.loads(line.strip())
                            if query.lower() in entry.get("message", "").lower():
                                results.append(entry)
                                if len(results) >= limit:
                                    break
                        except:
                            continue
            except:
                continue

        return results


if __name__ == "__main__":
    # Quick test
    from workflow_storage import WorkflowStorage
    storage = WorkflowStorage("/tmp/test_monitor.sqlite")
    monitor = WorkflowMonitor(storage)
    monitor.start_monitoring()

    print("Monitor started. Metrics:", monitor.get_metrics())

    time.sleep(2)
    monitor.stop_monitoring()
    print("Monitor stopped")
