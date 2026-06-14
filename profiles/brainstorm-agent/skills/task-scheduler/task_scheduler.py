"""
Task Scheduler Module
Main scheduler with dependency resolution, load balancing, and scheduling strategies.
"""

import importlib
import threading
import time
import uuid
from collections import defaultdict
from collections.abc import Callable
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

from task_executor import TaskExecutor
from task_handlers import get as get_handler
from task_queue import TaskQueue
from task_storage import TaskDefinition, TaskPriority, TaskRun, TaskStatus, TaskStorage


class SchedulingStrategy(Enum):
    """Scheduling strategies."""
    PRIORITY_FIFO = "priority_fifo"  # Priority then FIFO
    SHORTEST_JOB_FIRST = "shortest_job_first"
    LEAST_LOADED = "least_loaded"  # Balance load across workers
    DEPENDENCY_ORDER = "dependency_order"  # Respect DAG ordering


class TaskScheduler:
    """
    Central task scheduler with dependency resolution and load balancing.
    """

    def __init__(
        self,
        storage: TaskStorage,
        queue: TaskQueue,
        executor: TaskExecutor,
        strategy: SchedulingStrategy = SchedulingStrategy.PRIORITY_FIFO,
        max_concurrent_per_task: int = 5,
        batch_aggregation_enabled: bool = True
    ):
        """Initialize scheduler."""
        self.storage = storage
        self.queue = queue
        self.executor = executor
        self.strategy = strategy
        self.max_concurrent_per_task = max_concurrent_per_task
        self.batch_aggregation_enabled = batch_aggregation_enabled

        self._lock = threading.RLock()
        self._running = True
        self._scheduler_thread = threading.Thread(
            target=self._scheduler_loop,
            daemon=True,
            name="TaskScheduler-Loop"
        )
        self._scheduler_thread.start()

        # Statistics
        self._scheduled_count = 0
        self._rejected_count = 0
        self._dependency_wait_count = 0

        # Batch aggregation
        self._batch_queue: dict[str, list[str]] = defaultdict(list)  # task_id -> run_ids
        self._batch_lock = threading.RLock()

    def schedule(
        self,
        task_def: TaskDefinition,
        priority: int = TaskPriority.MEDIUM.value,
        dependencies: list[str] | None = None,
        delay_seconds: float | None = None,
        batch_key: str | None = None,
        metadata: dict[str, Any] | None = None
    ) -> str | None:
        """
        Schedule a task for execution.

        Args:
            task_def: Task definition
            priority: Priority (0-9, lower is higher)
            dependencies: List of task IDs that must complete first
            delay_seconds: Delay execution by N seconds
            batch_key: Key for batch aggregation (same key tasks batched together)
            metadata: Additional metadata

        Returns:
            Run ID if scheduled successfully, None otherwise
        """
        run_id = str(uuid.uuid4())

        # Save task definition
        task_def.task_id = task_def.task_id or str(uuid.uuid4())
        task_def.priority = priority
        if dependencies:
            task_def.dependencies = dependencies
        self.storage.save_task_definition(task_def)

        # Create run record
        run = TaskRun(
            run_id=run_id,
            task_id=task_def.task_id,
            status="pending",
            priority=priority,
            queued_at=datetime.utcnow().isoformat(),
            timeout_at=(
                (datetime.utcnow() + timedelta(seconds=task_def.timeout)).isoformat()
                if task_def.timeout else None
            ),
            attempt=0,
            metadata=metadata
        )
        self.storage.create_task_run(run)

        # Handle batching
        if batch_key and self.batch_aggregation_enabled:
            with self._batch_lock:
                self._batch_queue[batch_key].append(run_id)

            # Check if batch is ready (e.g., 10 items or 5 seconds)
            batch_size = len(self._batch_queue[batch_key])
            if batch_size >= 10:
                return run_id  # batch will be processed
            return run_id

        # Enqueue immediately
        if self._can_enqueue(task_def):
            success = self.queue.enqueue(
                run_id=run_id,
                task_id=task_def.task_id,
                priority=priority,
                delay_seconds=delay_seconds,
                dependencies=dependencies,
                attempt=0,
                metadata=metadata
            )
            if success:
                with self._lock:
                    self._scheduled_count += 1
                return run_id
            self.storage.update_task_run(run_id, status="failed", error="Failed to enqueue")
            return None
        # Queue is full or resources unavailable
        self._rejected_count += 1
        return None

    def _can_enqueue(self, task_def: TaskDefinition) -> bool:
        """Check if task can be enqueued (resource limits, concurrency)."""
        # Check resource availability
        if task_def.resource_limits:
            usage = self.storage.get_resource_usage()

            if "memory_mb" in task_def.resource_limits:
                avail = usage.get("global_memory", {}).get("available", 0)
                if task_def.resource_limits["memory_mb"] > avail:
                    return False

            if "cpu_percent" in task_def.resource_limits:
                avail = usage.get("global_cpu", {}).get("available", 0)
                if task_def.resource_limits["cpu_percent"] > avail:
                    return False

        # Check concurrent limit for this task type
        concurrent_count = self._count_running_for_task(task_def.task_id)
        if concurrent_count >= self.max_concurrent_per_task:
            return False

        return True

    def _count_running_for_task(self, task_id: str) -> int:
        """Count currently running executions for a task."""
        runs = self.storage.list_task_runs(
            task_id=task_id,
            status=TaskStatus.RUNNING.value,
            limit=100
        )
        return len(runs)

    def cancel(self, run_id: str) -> bool:
        """Cancel a scheduled task."""
        # Try to cancel in queue first
        if self.queue.cancel(run_id):
            self.storage.update_task_run(
                run_id,
                status=TaskStatus.CANCELLED.value,
                completed_at=datetime.utcnow().isoformat()
            )
            # Release any reserved resources
            run = self.storage.load_task_run(run_id)
            if run and run.metadata and "resource_limits" in run.metadata:
                limits = run.metadata["resource_limits"]
                if "memory_mb" in limits:
                    self.storage.release_resource("global_memory", limits["memory_mb"])
                if "cpu_percent" in limits:
                    self.storage.release_resource("global_cpu", limits["cpu_percent"])
            return True
        return False

    def get_status(self, run_id: str) -> dict[str, Any] | None:
        """Get task run status."""
        run = self.storage.load_task_run(run_id)
        if not run:
            return None

        task_def = self.storage.load_task_definition(run.task_id)

        return {
            "run_id": run.run_id,
            "task_id": run.task_id,
            "task_name": task_def.name if task_def else "Unknown",
            "status": run.status,
            "priority": run.priority,
            "queued_at": run.queued_at,
            "started_at": run.started_at,
            "completed_at": run.completed_at,
            "attempt": run.attempt,
            "error": run.error,
            "in_queue": self.queue.is_queued(run_id),
            "active": run_id in [t["run_id"] for t in self.executor.get_active_tasks()]
        }

    def list_tasks(
        self,
        status: str | None = None,
        limit: int = 100,
        task_type: str | None = None
    ) -> list[dict[str, Any]]:
        """List tasks with filtering."""
        runs = self.storage.list_task_runs(
            task_id=None,
            status=status,
            limit=limit
        )

        result = []
        for run in runs:
            task_def = self.storage.load_task_definition(run.task_id)

            if task_type and task_def.task_type != task_type:
                continue

            result.append({
                "run_id": run.run_id,
                "task_id": run.task_id,
                "task_name": task_def.name if task_def else "Unknown",
                "task_type": task_def.task_type if task_def else "Unknown",
                "status": run.status,
                "priority": run.priority,
                "queued_at": run.queued_at,
                "started_at": run.started_at,
                "completed_at": run.completed_at,
                "attempt": run.attempt,
                "has_error": bool(run.error)
            })

        return result

    def wait_for_task(self, run_id: str, timeout: float | None = None) -> TaskStatus | None:
        """
        Wait for task completion.

        Args:
            run_id: Run ID to wait for
            timeout: Maximum time to wait (seconds)

        Returns:
            Final TaskStatus or None if timeout
        """
        start_time = time.time()
        deadline = None if timeout is None else start_time + timeout

        while True:
            run = self.storage.load_task_run(run_id)
            if not run:
                return None

            if run.status in [TaskStatus.COMPLETED.value, TaskStatus.FAILED.value,
                            TaskStatus.TIMEOUT.value, TaskStatus.CANCELLED.value]:
                return TaskStatus(run.status)

            # Check timeout
            if deadline and time.time() > deadline:
                return None

            time.sleep(0.5)  # Poll interval

    def _scheduler_loop(self):
        """Main scheduler loop."""
        while self._running:
            try:
                # Process batch aggregation
                self._process_batches()

                # Pull items from queue and submit to executor
                self._dispatch_tasks()

                # Check for completed dependencies
                self._check_dependencies()

                time.sleep(0.1)  # 100ms polling interval

            except Exception as e:
                self.storage.append_log("scheduler", "ERROR", f"Scheduler loop error: {e}")
                time.sleep(1.0)

    def _process_batches(self):
        """Process batched tasks."""
        with self._batch_lock:
            for batch_key, run_ids in list(self._batch_queue.items()):
                if len(run_ids) >= 10:  # batch size threshold
                    # Process batch
                    for run_id in run_ids:
                        run = self.storage.load_task_run(run_id)
                        task_def = self.storage.load_task_definition(run.task_id)
                        if run and task_def and self._can_enqueue(task_def):
                            self.queue.enqueue(
                                run_id=run_id,
                                task_id=task_def.task_id,
                                priority=run.priority,
                                dependencies=task_def.dependencies,
                                attempt=run.attempt
                            )
                    del self._batch_queue[batch_key]
                elif len(run_ids) > 0:
                    # Check age of oldest item
                    oldest_run = self.storage.load_task_run(run_ids[0])
                    if oldest_run and oldest_run.queued_at:
                        age = (datetime.utcnow() - datetime.fromisoformat(oldest_run.queued_at)).total_seconds()
                        if age > 5:  # 5 second timeout for small batches
                            for run_id in run_ids:
                                run = self.storage.load_task_run(run_id)
                                task_def = self.storage.load_task_definition(run.task_id)
                                if run and task_def and self._can_enqueue(task_def):
                                    self.queue.enqueue(
                                        run_id=run_id,
                                        task_id=task_def.task_id,
                                        priority=run.priority,
                                        dependencies=task_def.dependencies,
                                        attempt=run.attempt
                                    )
                            del self._batch_queue[batch_key]

    def _dispatch_tasks(self):
        """Dispatch ready tasks from queue to executor."""
        while True:
            item = self.queue.dequeue(timeout=0.1)
            if not item:
                break

            # Load task definition
            task_def = self.storage.load_task_definition(item.task_id)
            if not task_def:
                self.storage.update_task_run(
                    item.run_id,
                    status=TaskStatus.FAILED.value,
                    error="Task definition not found"
                )
                continue

            # Load task function
            func = self._load_task_function(task_def)
            if not func:
                self.storage.update_task_run(
                    item.run_id,
                    status=TaskStatus.FAILED.value,
                    error=f"Could not load task function: {task_def.func}"
                )
                continue

            # Prepare arguments
            args = task_def.args or []
            kwargs = task_def.kwargs or {}

            # Inject template variables
            if task_def.template and task_def.template_vars:
                # Apply template substitutions
                kwargs = self._apply_template_vars(kwargs, task_def.template_vars)

            # Submit to executor
            success = self.executor.submit(
                item.run_id,
                self.storage.load_task_run(item.run_id),
                func,
                *args,
                **kwargs
            )

            if not success:
                # Could not submit (resource limits), requeue
                self.queue.requeue(item.run_id, delay_seconds=1.0)
                self._rejected_count += 1

    def _load_task_function(self, task_def: TaskDefinition) -> Callable | None:
        """Load task function from definition."""
        if task_def.task_type == "shell":
            return self._shell_runner
        if task_def.task_type == "http":
            return self._http_runner
        if task_def.task_type == "batch":
            return self._batch_runner
        if task_def.func:
            try:
                parts = task_def.func.rsplit(".", 1)
                if len(parts) == 2:
                    module_name, func_name = parts
                    module = importlib.import_module(module_name)
                    return getattr(module, func_name)
                # Assume it's a registered handler in global registry
                return self._get_registered_handler(task_def.func)
            except Exception as e:
                self.storage.append_log(
                    "scheduler",
                    "ERROR",
                    f"Failed to load function {task_def.func}: {e}"
                )
                return None
        return None

    def _get_registered_handler(self, name: str) -> Callable | None:
        """Get registered handler function."""
        return get_handler(name)

    def _shell_runner(self, command: str, cwd: str | None = None) -> dict[str, Any]:
        """Run shell command."""
        import subprocess
        result = subprocess.run(
            command,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=300
        )
        return {
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr
        }

    def _http_runner(self, url: str, method: str = "GET", **kwargs) -> dict[str, Any]:
        """Make HTTP request."""
        import requests
        response = requests.request(method, url, **kwargs)
        return {
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "content": response.text
        }

    def _batch_runner(self, tasks: list[dict[str, Any]]) -> dict[str, Any]:
        """Run batch of tasks."""
        results = []
        for task in tasks:
            try:
                # Execute subtask
                result = task["func"](*task.get("args", []), **task.get("kwargs", {}))
                results.append({"success": True, "result": result})
            except Exception as e:
                results.append({"success": False, "error": str(e)})

        return {
            "total": len(results),
            "successful": sum(1 for r in results if r["success"]),
            "failed": sum(1 for r in results if not r["success"]),
            "results": results
        }

    def _get_registered_handler(self, name: str) -> Callable | None:
        """Get registered handler function."""
        # This would be populated by task_register_handler
        # For now, return None (handlers must be fully qualified module.func)
        return None

    def _apply_template_vars(self, kwargs: dict[str, Any], template_vars: dict[str, Any]) -> dict[str, Any]:
        """Apply template variable substitutions."""
        result = {}
        for key, value in kwargs.items():
            if isinstance(value, str):
                for var_name, var_value in template_vars.items():
                    placeholder = f"${{{var_name}}}"
                    if placeholder in value:
                        value = value.replace(placeholder, str(var_value))
            result[key] = value
        return result

    def _check_dependencies(self):
        """Check dependency satisfaction and notify queue."""
        # This is called periodically to check if any queued tasks can proceed

    def get_statistics(self) -> dict[str, Any]:
        """Get scheduler statistics."""
        with self._lock:
            stats = self.storage.get_statistics()
            stats.update({
                "executor_active": len(self.executor.get_active_tasks()),
                "queue_sizes": self.queue.queue_size(),
                "total_scheduled": self._scheduled_count,
                "total_rejected": self._rejected_count,
                "batching_enabled": self.batch_aggregation_enabled
            })
            return stats

    def stop(self):
        """Stop scheduler."""
        self._running = False
        if self._scheduler_thread.is_alive():
            self._scheduler_thread.join(timeout=5)
        self.queue.stop()
        self.executor.shutdown(wait=False)
