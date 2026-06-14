"""
Task Monitor Module
Real-time monitoring, progress reporting, and performance statistics.
"""

import threading
import time
from collections import defaultdict, deque
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from task_storage import TaskStorage


@dataclass
class MetricSample:
    """Single metric sample."""
    timestamp: float
    value: float
    labels: dict[str, str] = None


@dataclass
class DashboardData:
    """Dashboard snapshot data."""
    timestamp: str
    queue_sizes: dict[str, int]
    active_tasks: list[dict[str, Any]]
    recent_runs: list[dict[str, Any]]
    statistics: dict[str, Any]
    resource_usage: dict[str, dict[str, float]]
    alerts: list[dict[str, Any]]


class TaskMonitor:
    """
    Real-time task monitoring with metrics collection and alerting.
    """

    def __init__(
        self,
        storage: TaskStorage,
        executor: Any,  # TaskExecutor
        metrics_retention_minutes: int = 60,
        alert_handlers: list[Callable] | None = None
    ):
        """Initialize monitor."""
        self.storage = storage
        self.executor = executor
        self.metrics_retention_minutes = metrics_retention_minutes
        self.alert_handlers = alert_handlers or []

        self._lock = threading.RLock()
        self._running = True
        self._metrics_history: dict[str, deque] = defaultdict(
            lambda: deque(maxlen=metrics_retention_minutes * 60)  # 1 sample per second
        )
        self._alerts: list[dict[str, Any]] = []
        self._alert_rules: list[dict[str, Any]] = self._default_alert_rules()

        # Start monitoring thread
        self._monitor_thread = threading.Thread(
            target=self._collect_metrics,
            daemon=True,
            name="TaskMonitor-Collector"
        )
        self._monitor_thread.start()

    def _default_alert_rules(self) -> list[dict[str, Any]]:
        """Default alert rules."""
        return [
            {
                "name": "queue_size_high",
                "condition": lambda m: m.get("queue_size", 0) > 1000,
                "severity": "warning",
                "message": "Queue size exceeds 1000 tasks"
            },
            {
                "name": "failure_rate_high",
                "condition": lambda m: m.get("failure_rate", 0) > 0.5,
                "severity": "critical",
                "message": "Failure rate exceeds 50%"
            },
            {
                "name": "executor_saturated",
                "condition": lambda m: m.get("active_tasks", 0) >= m.get("max_workers", 10) * 0.95,
                "severity": "warning",
                "message": "Executor is nearly saturated"
            }
        ]

    def _collect_metrics(self):
        """Background thread collecting metrics."""
        while self._running:
            try:
                metrics = self._collect_current_metrics()
                self._store_metrics(metrics)
                self._check_alerts(metrics)
                time.sleep(1.0)  # 1 second interval
            except Exception as e:
                # Log error but continue
                try:
                    self.storage.append_log(
                        "monitor",
                        "ERROR",
                        f"Metrics collection error: {e}"
                    )
                except:
                    pass
                time.sleep(5.0)

    def _collect_current_metrics(self) -> dict[str, Any]:
        """Collect current metrics snapshot."""
        stats = self.storage.get_statistics()
        queue_sizes = self.executor.task_queue.queue_size() if hasattr(self.executor, "task_queue") else {}
        active_tasks = self.executor.get_active_tasks() if hasattr(self.executor, "get_active_tasks") else []
        resource_usage = self.storage.get_resource_usage()

        return {
            "timestamp": time.time(),
            "queue_size": queue_sizes.get("total", 0),
            "ready_queue": queue_sizes.get("ready", 0),
            "delayed_queue": queue_sizes.get("delayed", 0),
            "pending_dependencies": queue_sizes.get("pending_dependencies", 0),
            "active_tasks": len(active_tasks),
            "completed_count": stats.get("total_task_definitions", 0),
            "success_rate": stats.get("success_rate_24h", 0.0),
            "failure_rate": stats.get("failure_rate_24h", 0.0),
            "avg_execution_seconds": stats.get("avg_execution_seconds", 0.0),
            "runs_last_hour": stats.get("runs_last_hour", 0),
            "max_workers": self.executor.max_workers if hasattr(self.executor, "max_workers") else 10,
            "resource_usage": resource_usage
        }

    def _store_metrics(self, metrics: dict[str, Any]):
        """Store metrics in history."""
        timestamp = metrics.pop("timestamp")

        with self._lock:
            for key, value in metrics.items():
                if isinstance(value, (int, float)):
                    self._metrics_history[key].append(MetricSample(
                        timestamp=timestamp,
                        value=value
                    ))

    def _check_alerts(self, metrics: dict[str, Any]):
        """Check alert rules."""
        with self._lock:
            for rule in self._alert_rules:
                try:
                    if rule["condition"](metrics):
                        alert = {
                            "rule": rule["name"],
                            "severity": rule["severity"],
                            "message": rule["message"],
                            "timestamp": datetime.utcnow().isoformat(),
                            "metrics": {k: v for k, v in metrics.items() if isinstance(v, (int, float))}
                        }

                        # Avoid duplicate alerts (same rule within 5 minutes)
                        recent_alert = None
                        for a in self._alerts:
                            if a["rule"] == rule["name"]:
                                alert_time = datetime.fromisoformat(a["timestamp"])
                                if datetime.utcnow() - alert_time < timedelta(minutes=5):
                                    recent_alert = a
                                    break

                        if not recent_alert:
                            self._alerts.append(alert)
                            self._trigger_alert(alert)

                except Exception:
                    pass

    def _trigger_alert(self, alert: dict[str, Any]):
        """Trigger alert handlers."""
        for handler in self.alert_handlers:
            try:
                handler(alert)
            except Exception:
                pass

    def get_dashboard_data(self) -> DashboardData:
        """Get current dashboard snapshot."""
        stats = self.storage.get_statistics()
        queue_sizes = self.executor.task_queue.queue_size() if hasattr(self.executor, "task_queue") else {}
        active_tasks = self.executor.get_active_tasks() if hasattr(self.executor, "get_active_tasks") else []

        # Get recent runs
        recent_runs = self.storage.list_task_runs(limit=20)
        recent_runs_data = []
        for run in recent_runs:
            recent_runs_data.append({
                "run_id": run.run_id,
                "task_id": run.task_id,
                "status": run.status,
                "priority": run.priority,
                "queued_at": run.queued_at,
                "started_at": run.started_at,
                "completed_at": run.completed_at,
                "attempt": run.attempt
            })

        # Get active task details
        active_tasks_data = []
        for task in active_tasks:
            task_def = self.storage.load_task_definition(task["task_id"])
            active_tasks_data.append({
                "run_id": task["run_id"],
                "task_id": task["task_id"],
                "task_name": task_def.name if task_def else "Unknown",
                "worker_id": task["worker_id"],
                "elapsed_seconds": task["elapsed"],
                "priority": task.get("priority", 0)
            })

        # Get alerts (last 10)
        with self._lock:
            alerts_data = self._alerts[-10:]

        return DashboardData(
            timestamp=datetime.utcnow().isoformat(),
            queue_sizes=queue_sizes,
            active_tasks=active_tasks_data,
            recent_runs=recent_runs_data,
            statistics=stats,
            resource_usage=self.storage.get_resource_usage(),
            alerts=alerts_data
        )

    def get_run_summary(self, run_id: str) -> dict[str, Any] | None:
        """Get detailed summary for a specific run."""
        run = self.storage.load_task_run(run_id)
        if not run:
            return None

        task_def = self.storage.load_task_definition(run.task_id)
        logs = self.storage.get_logs(run_id, limit=100)

        return {
            "run_id": run.run_id,
            "task_id": run.task_id,
            "task_name": task_def.name if task_def else "Unknown",
            "task_type": task_def.task_type if task_def else "Unknown",
            "status": run.status,
            "priority": run.priority,
            "attempt": run.attempt,
            "queued_at": run.queued_at,
            "started_at": run.started_at,
            "completed_at": run.completed_at,
            "execution_time_seconds": (
                (datetime.fromisoformat(run.completed_at) - datetime.fromisoformat(run.started_at)).total_seconds()
                if run.started_at and run.completed_at else None
            ),
            "error": run.error,
            "traceback": run.traceback,
            "resource_usage": run.resource_usage,
            "checkpoint_data": bool(run.checkpoint_data),
            "logs": logs[:20]  # last 20 logs
        }

    def get_metrics_history(
        self,
        metric_name: str,
        start_time: float | None = None,
        end_time: float | None = None
    ) -> list[MetricSample]:
        """Get historical metrics for a specific metric."""
        with self._lock:
            if metric_name not in self._metrics_history:
                return []

            samples = list(self._metrics_history[metric_name])

            if start_time:
                samples = [s for s in samples if s.timestamp >= start_time]
            if end_time:
                samples = [s for s in samples if s.timestamp <= end_time]

            return samples

    def get_performance_report(self, hours: int = 24) -> dict[str, Any]:
        """Generate performance report over time window."""
        cutoff = datetime.utcnow() - timedelta(hours=hours)

        with self.storage.connection() as conn:
            # throughput over time (by hour)
            cursor = conn.execute("""
                SELECT
                    strftime('%Y-%m-%d %H:00:00', queued_at) as hour,
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
                    SUM(CASE WHEN status IN ('failed', 'timeout') THEN 1 ELSE 0 END) as failed
                FROM task_runs
                WHERE queued_at >= ?
                GROUP BY hour
                ORDER BY hour
            """, (cutoff.isoformat(),))

            throughput = []
            for row in cursor:
                throughput.append({
                    "hour": row["hour"],
                    "total": row["total"],
                    "completed": row["completed"],
                    "failed": row["failed"],
                    "success_rate": row["completed"] / row["total"] if row["total"] > 0 else 0.0
                })

            # Task type distribution
            cursor = conn.execute("""
                SELECT
                    td.task_type,
                    COUNT(tr.run_id) as count,
                    SUM(CASE WHEN tr.status = 'completed' THEN 1 ELSE 0 END) as completed
                FROM task_definitions td
                LEFT JOIN task_runs tr ON td.task_id = tr.task_id
                WHERE tr.queued_at >= ? OR tr.queued_at IS NULL
                GROUP BY td.task_type
            """, (cutoff.isoformat(),))

            task_distribution = []
            for row in cursor:
                task_distribution.append({
                    "task_type": row["task_type"],
                    "count": row["count"],
                    "completed": row["completed"],
                    "success_rate": row["completed"] / row["count"] if row["count"] > 0 else 0.0
                })

            # Priority distribution
            cursor = conn.execute("""
                SELECT
                    priority,
                    COUNT(*) as count,
                    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed
                FROM task_runs
                WHERE queued_at >= ?
                GROUP BY priority
                ORDER BY priority
            """, (cutoff.isoformat(),))

            priority_distribution = []
            for row in cursor:
                priority_distribution.append({
                    "priority": row["priority"],
                    "count": row["count"],
                    "completed": row["completed"],
                    "success_rate": row["completed"] / row["count"] if row["count"] > 0 else 0.0
                })

        return {
            "period_hours": hours,
            "generated_at": datetime.utcnow().isoformat(),
            "throughput_by_hour": throughput,
            "task_type_distribution": task_distribution,
            "priority_distribution": priority_distribution,
            "summary": self.storage.get_statistics()
        }

    def add_alert_rule(self, rule: dict[str, Any]):
        """Add custom alert rule."""
        with self._lock:
            self._alert_rules.append(rule)

    def clear_alerts(self):
        """Clear alert history."""
        with self._lock:
            self._alerts.clear()

    def get_alerts(self, severity: str | None = None) -> list[dict[str, Any]]:
        """Get alert history."""
        with self._lock:
            if severity:
                return [a for a in self._alerts if a["severity"] == severity]
            return list(self._alerts)

    def stop(self):
        """Stop monitoring thread."""
        self._running = False
        self._monitor_thread.join(timeout=5)
