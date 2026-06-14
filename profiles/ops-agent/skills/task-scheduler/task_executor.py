"""
Task Executor Module
Asynchronous executor with thread/process pools, timeout control, and resource limits.
"""

import json
import pickle
import resource
import threading
import time
import traceback
from collections.abc import Callable
from concurrent.futures import Future, ProcessPoolExecutor, ThreadPoolExecutor
from dataclasses import dataclass
from enum import Enum
from typing import Any

import psutil
from task_queue import TaskQueue
from task_storage import TaskRun, TaskStatus, TaskStorage


class ExecutorType(Enum):
    """Executor type."""
    THREAD = "thread"
    PROCESS = "process"


@dataclass
class ResourceUsage:
    """Resource usage metrics."""
    cpu_percent: float = 0.0
    memory_mb: float = 0.0
    peak_memory_mb: float = 0.0
    thread_count: int = 0
    max_fds: int = 0


class TaskExecutor:
    """
    Asynchronous task executor with resource limits and timeout control.
    Supports both thread and process pools.
    """

    def __init__(
        self,
        storage: TaskStorage,
        task_queue: "TaskQueue",  # Avoid circular import with forward ref
        max_workers: int = 10,
        executor_type: ExecutorType = ExecutorType.THREAD,
        resource_monitoring: bool = True
    ):
        """Initialize executor."""
        self.storage = storage
        self.task_queue = task_queue
        self.max_workers = max_workers
        self.executor_type = executor_type
        self.resource_monitoring = resource_monitoring

        self._lock = threading.RLock()
        self._running = True
        self._active_tasks: dict[str, dict[str, Any]] = {}  # run_id -> {future, start_time, worker_id}
        self._shutdown = False

        # Create executor
        if executor_type == ExecutorType.THREAD:
            self._executor = ThreadPoolExecutor(
                max_workers=max_workers,
                thread_name_prefix="TaskExecutor-Worker"
            )
        else:
            self._executor = ProcessPoolExecutor(
                max_workers=max_workers,
                mp_context=None  # default
            )

        # Monitoring thread
        self._monitor_thread = threading.Thread(
            target=self._monitor_tasks,
            daemon=True,
            name="TaskExecutor-Monitor"
        )
        self._monitor_thread.start()

    def submit(self, run_id: str, task_run: TaskRun, func: Callable, *args, **kwargs) -> bool:
        """
        Submit task for execution.

        Args:
            run_id: Run ID
            task_run: Task run record
            func: Function to execute
            *args, **kwargs: Function arguments

        Returns:
            True if submitted successfully
        """
        if self._shutdown:
            return False

        # Check resource limits
        if not self._check_resource_availability(task_run.resource_limits):
            return False

        worker_id = f"worker-{threading.current_thread().ident}-{time.time()}"

        # Update storage
        self.storage.update_task_run(
            run_id,
            status="running",
            started_at=datetime.utcnow().isoformat(),
            worker_id=worker_id
        )

        # Submit to executor
        future = self._executor.submit(self._run_with_timeout, run_id, task_run, func, *args, **kwargs)

        with self._lock:
            self._active_tasks[run_id] = {
                "future": future,
                "start_time": time.time(),
                "worker_id": worker_id,
                "task_run": task_run,
                "resource_limits": task_run.resource_limits
            }

        # Callback for completion
        future.add_done_callback(lambda f: self._on_task_complete(run_id))

        return True

    def _run_with_timeout(self, run_id: str, task_run: TaskRun, func: Callable, *args, **kwargs):
        """Execute function with timeout and resource limits."""
        start_time = time.time()
        process = None
        original_limits = None

        try:
            # Set resource limits if needed
            if task_run.resource_limits:
                self._apply_resource_limits(task_run.resource_limits)

            # Execute with timeout
            timeout = task_run.timeout or None

            if self.executor_type == ExecutorType.PROCESS:
                # For process, timeout is handled differently
                result = func(*args, **kwargs)
            else:
                # For threads, we need custom timeout handling
                result = self._execute_with_timeout(func, timeout, *args, **kwargs)

            execution_time = time.time() - start_time

            # Collect resource usage
            resource_usage = self._collect_resource_usage()

            return {
                "result": result,
                "execution_time": execution_time,
                "resource_usage": resource_usage,
                "status": "completed"
            }

        except TimeoutError:
            execution_time = time.time() - start_time
            resource_usage = self._collect_resource_usage()

            return {
                "error": f"Task timed out after {task_run.timeout} seconds",
                "execution_time": execution_time,
                "resource_usage": resource_usage,
                "status": "timeout"
            }

        except Exception as e:
            execution_time = time.time() - start_time
            resource_usage = self._collect_resource_usage()
            tb = traceback.format_exc()

            return {
                "error": str(e),
                "traceback": tb,
                "execution_time": execution_time,
                "resource_usage": resource_usage,
                "status": "failed"
            }

        finally:
            # Restore original limits
            if original_limits:
                self._restore_resource_limits(original_limits)

    def _execute_with_timeout(self, func: Callable, timeout: float | None, *args, **kwargs):
        """Execute function with timeout (for thread pool)."""
        if timeout is None:
            return func(*args, **kwargs)

        # Use threading.Timer for timeout
        result = [None]
        exception = [None]
        timeout_raised = [False]

        def target():
            try:
                result[0] = func(*args, **kwargs)
            except Exception as e:
                exception[0] = e

        thread = threading.Thread(target=target, daemon=True)
        thread.start()
        thread.join(timeout=timeout)

        if thread.is_alive():
            # Create exception to raise in main thread
            raise TimeoutError(f"Function execution exceeded {timeout} seconds")

        if exception[0]:
            raise exception[0]

        return result[0]

    def _apply_resource_limits(self, limits: dict[str, Any]):
        """Apply resource limits to current process/thread."""
        # Note: Most resource limits only work on processes, not threads
        if self.executor_type == ExecutorType.PROCESS:
            # RLIMIT_AS (address space) for memory
            if "memory_mb" in limits:
                mem_bytes = limits["memory_mb"] * 1024 * 1024
                resource.setrlimit(resource.RLIMIT_AS, (mem_bytes, mem_bytes))

            # RLIMIT_CPU for CPU time
            if "cpu_seconds" in limits:
                resource.setrlimit(resource.RLIMIT_CPU, (limits["cpu_seconds"], limits["cpu_seconds"]))

    def _restore_resource_limits(self, original_limits):
        """Restore original resource limits."""
        if self.executor_type == ExecutorType.PROCESS:
            for lim_type, (soft, hard) in original_limits.items():
                resource.setrlimit(lim_type, (soft, hard))

    def _check_resource_availability(self, limits: dict[str, Any] | None) -> bool:
        """Check if resource limits can be satisfied."""
        if not limits:
            return True

        with self._lock:
            current_usage = self.storage.get_resource_usage()

            # Check memory
            if "memory_mb" in limits:
                avail = current_usage.get("global_memory", {}).get("available", 0)
                if limits["memory_mb"] > avail:
                    return False

            # Check CPU (percentage)
            if "cpu_percent" in limits:
                avail = current_usage.get("global_cpu", {}).get("available", 0)
                if limits["cpu_percent"] > avail:
                    return False

            return True

    def _collect_resource_usage(self) -> dict[str, float]:
        """Collect resource usage metrics for current process."""
        if not self.resource_monitoring:
            return {}

        try:
            process = psutil.Process()
            with process.oneshot():
                usage = {
                    "cpu_percent": process.cpu_percent(interval=0.1),
                    "memory_mb": process.memory_info().rss / 1024 / 1024,
                    "thread_count": process.num_threads(),
                    "peak_memory_mb": process.memory_info().vms / 1024 / 1024
                }
                return usage
        except Exception:
            return {}

    def _on_task_complete(self, run_id: str):
        """Handle task completion."""
        try:
            if run_id not in self._active_tasks:
                return

            task_info = self._active_tasks[run_id]
            future: Future = task_info["future"]

            # Get result
            try:
                result_data = future.result(timeout=1.0)
            except Exception as e:
                result_data = {
                    "error": str(e),
                    "traceback": traceback.format_exc(),
                    "status": "failed"
                }

            # Determine final status
            status = result_data.get("status", "failed")
            if status == "completed":
                final_status = TaskStatus.COMPLETED.value
            elif status == "timeout":
                final_status = TaskStatus.TIMEOUT.value
            else:
                final_status = TaskStatus.FAILED.value

            # Update storage
            updates = {
                "status": final_status,
                "completed_at": datetime.utcnow().isoformat(),
                "result": pickle.dumps(result_data.get("result")) if "result" in result_data else None,
                "error": result_data.get("error"),
                "traceback": result_data.get("traceback"),
                "resource_usage": json.dumps(result_data.get("resource_usage", {})) if "resource_usage" in result_data else None
            }

            # Remove nans
            for k, v in list(updates.items()):
                if v is None:
                    del updates[k]

            self.storage.update_task_run(run_id, **updates)

            # Release resources
            if "resource_limits" in task_info:
                limits = task_info["resource_limits"]
                if "memory_mb" in limits:
                    self.storage.release_resource("global_memory", limits["memory_mb"])
                if "cpu_percent" in limits:
                    self.storage.release_resource("global_cpu", limits["cpu_percent"])

            # Remove from active tasks
            with self._lock:
                if run_id in self._active_tasks:
                    del self._active_tasks[run_id]

            # Notify queue about dependency resolution
            if final_status in ["completed", "failed", "timeout"]:
                self.task_queue.mark_dependencies_met(run_id)

        except Exception as e:
            # Log error
            try:
                self.storage.append_log(run_id, "ERROR", f"Executor completion handler error: {e}")
            except:
                pass

    def _monitor_tasks(self):
        """Background monitoring thread."""
        while self._running and not self._shutdown:
            try:
                time.sleep(5)  # Check every 5 seconds

                now = time.time()
                with self._lock:
                    for run_id, task_info in list(self._active_tasks.items()):
                        future: Future = task_info["future"]
                        start_time = task_info["start_time"]
                        task_run: TaskRun = task_info["task_run"]

                        # Check for timeout (additional check beyond _run_with_timeout)
                        elapsed = now - start_time
                        if elapsed > (task_run.timeout or 3600):
                            # Force cancel
                            future.cancel()
                            self.storage.update_task_run(
                                run_id,
                                status=TaskStatus.TIMEOUT.value,
                                completed_at=datetime.utcnow().isoformat(),
                                error=f"Task exceeded timeout of {task_run.timeout} seconds"
                            )

            except Exception:
                pass

    def get_active_tasks(self) -> list[dict[str, Any]]:
        """Get list of currently executing tasks."""
        with self._lock:
            return [
                {
                    "run_id": run_id,
                    "task_id": info["task_run"].task_id,
                    "worker_id": info["worker_id"],
                    "elapsed": time.time() - info["start_time"]
                }
                for run_id, info in self._active_tasks.items()
            ]

    def get_statistics(self) -> dict[str, Any]:
        """Get executor statistics."""
        with self._lock:
            completed_count = 0
            failed_count = 0

            # Count recent runs from storage
            stats = self.storage.get_statistics()
            runs_by_status = stats.get("runs_by_status", {})
            completed_count = runs_by_status.get("completed", 0)
            failed_count = runs_by_status.get("failed", 0) + runs_by_status.get("timeout", 0)

            return {
                "max_workers": self.max_workers,
                "active_tasks": len(self._active_tasks),
                "executor_type": self.executor_type.value,
                "total_completed": completed_count,
                "total_failed": failed_count,
                "resource_monitoring": self.resource_monitoring
            }

    def shutdown(self, wait: bool = True):
        """Shutdown executor."""
        self._shutdown = True
        self._running = False

        # Shutdown executor
        self._executor.shutdown(wait=wait, cancel_futures=True)

        # Wait for monitor thread
        self._monitor_thread.join(timeout=5)
