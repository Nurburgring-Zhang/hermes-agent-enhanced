"""
Task Scheduler Skill
A comprehensive task scheduling system with priority queues, dependency resolution,
resource limits, and persistent storage.

Usage:
    from task_scheduler import (
        schedule_task, cancel_task, get_task_status, list_tasks, wait_for_task,
        TaskScheduler, TaskDefinition
    )

    # Schedule a task
    run_id = schedule_task(
        task_def=TaskDefinition(
            task_id="my-task",
            name="My Task",
            task_type="function",
            func="mymodule.my_function",
            args=[],
            kwargs={"param": "value"}
        ),
        priority=1,
        timeout=300
    )

    # Check status
    status = get_task_status(run_id)

    # Wait for completion
    final_status = wait_for_task(run_id, timeout=600)
"""

from .task_executor import ExecutorType, TaskExecutor
from .task_handlers import clear as clear_handlers
from .task_handlers import get as get_handler
from .task_handlers import list_handlers, register, unregister
from .task_monitor import TaskMonitor
from .task_queue import QueueItem, TaskQueue
from .task_scheduler import SchedulingStrategy, TaskScheduler
from .task_storage import TaskDefinition, TaskPriority, TaskRun, TaskStatus, TaskStorage

# Global instances (singleton pattern for process)
_storage: Optional[TaskStorage] = None
_queue: Optional[TaskQueue] = None
_executor: Optional[TaskExecutor] = None
_scheduler: Optional[TaskScheduler] = None
_monitor: Optional[TaskMonitor] = None


def initialize(
    db_path: Optional[str] = None,
    max_workers: int = 10,
    executor_type: ExecutorType = ExecutorType.THREAD,
    scheduling_strategy: SchedulingStrategy = SchedulingStrategy.PRIORITY_FIFO
) -> TaskScheduler:
    """
    Initialize the task scheduler system.

    Args:
        db_path: Path to SQLite database (default: ~/.hermes/task-scheduler/tasks.sqlite)
        max_workers: Maximum concurrent worker threads/processes
        executor_type: THREAD or PROCESS executor
        scheduling_strategy: Scheduling algorithm

    Returns:
        Initialized TaskScheduler instance
    """
    global _storage, _queue, _executor, _scheduler, _monitor

    if _scheduler is not None:
        return _scheduler  # Already initialized

    # Create storage
    _storage = TaskStorage(db_path=db_path)

    # Create queue
    _queue = TaskQueue(storage=_storage)

    # Create executor
    _executor = TaskExecutor(
        storage=_storage,
        task_queue=_queue,
        max_workers=max_workers,
        executor_type=executor_type
    )

    # Create monitor
    _monitor = TaskMonitor(
        storage=_storage,
        executor=_executor
    )

    # Create scheduler
    _scheduler = TaskScheduler(
        storage=_storage,
        queue=_queue,
        executor=_executor,
        strategy=scheduling_strategy
    )

    return _scheduler


def get_scheduler() -> Optional[TaskScheduler]:
    """Get global scheduler instance (must call initialize() first)."""
    return _scheduler


def get_storage() -> Optional[TaskStorage]:
    """Get global storage instance."""
    return _storage


def get_monitor() -> Optional[TaskMonitor]:
    """Get global monitor instance."""
    return _monitor


# High-level API functions

def schedule_task(
    task_def: TaskDefinition,
    priority: int = TaskPriority.MEDIUM.value,
    dependencies: Optional[List[str]] = None,
    timeout: Optional[int] = None,
    delay_seconds: Optional[float] = None,
    batch_key: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    resource_limits: Optional[Dict[str, Any]] = None,
    max_retries: Optional[int] = None
) -> Optional[str]:
    """
    Schedule a task for execution.

    Args:
        task_def: Task definition
        priority: Priority 0-9 (0 = highest)
        dependencies: List of run IDs that must complete first
        timeout: Override default timeout (seconds)
        delay_seconds: Delay execution by N seconds
        batch_key: Batch tasks with same key
        metadata: Additional execution metadata
        resource_limits: Resource constraints (cpu_percent, memory_mb)
        max_retries: Override default retries

    Returns:
        Run ID if scheduled successfully, None otherwise
    """
    global _scheduler

    if _scheduler is None:
        initialize()

    # Apply overrides
    if timeout is not None:
        task_def.timeout = timeout
    if max_retries is not None:
        task_def.max_retries = max_retries
    if resource_limits is not None:
        task_def.resource_limits = resource_limits

    return _scheduler.schedule(
        task_def=task_def,
        priority=priority,
        dependencies=dependencies,
        delay_seconds=delay_seconds,
        batch_key=batch_key,
        metadata=metadata
    )


def cancel_task(run_id: str) -> bool:
    """
    Cancel a scheduled or running task.

    Args:
        run_id: Run ID to cancel

    Returns:
        True if cancelled, False if not found or already completed
    """
    global _scheduler

    if _scheduler is None:
        initialize()

    return _scheduler.cancel(run_id)


def get_task_status(run_id: str) -> Optional[Dict[str, Any]]:
    """
    Get status of a task run.

    Args:
        run_id: Run ID

    Returns:
        Status dict with run details
    """
    global _scheduler

    if _scheduler is None:
        initialize()

    return _scheduler.get_status(run_id)


def list_tasks(
    status: Optional[str] = None,
    limit: int = 100,
    task_type: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    List task runs with optional filtering.

    Args:
        status: Filter by status (pending, running, completed, failed, etc.)
        limit: Maximum number of results
        task_type: Filter by task type

    Returns:
        List of task run summaries
    """
    global _scheduler

    if _scheduler is None:
        initialize()

    return _scheduler.list_tasks(status=status, limit=limit, task_type=task_type)


def wait_for_task(
    run_id: str,
    timeout: Optional[float] = None,
    poll_interval: float = 0.5
) -> Optional[TaskStatus]:
    """
    Wait for task to complete.

    Args:
        run_id: Run ID to wait for
        timeout: Maximum wait time (None = forever)
        poll_interval: How often to check status

    Returns:
        TaskStatus on completion, None if timeout
    """
    global _scheduler

    if _scheduler is None:
        initialize()

    return _scheduler.wait_for_task(run_id, timeout=timeout)


def get_task_logs(run_id: str, limit: int = 100, level: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Get logs for a task run.

    Args:
        run_id: Run ID
        limit: Maximum number of log entries
        level: Filter by log level (DEBUG, INFO, WARNING, ERROR)

    Returns:
        List of log entries
    """
    global _storage

    if _storage is None:
        initialize()

    return _storage.get_logs(run_id, limit=limit, level=level)


def get_dashboard() -> Dict[str, Any]:
    """
    Get current dashboard snapshot.

    Returns:
        Dashboard data with queue status, active tasks, statistics, etc.
    """
    global _monitor

    if _monitor is None:
        initialize()

    dashboard = _monitor.get_dashboard_data()
    return {
        "timestamp": dashboard.timestamp,
        "queue_sizes": dashboard.queue_sizes,
        "active_tasks": dashboard.active_tasks,
        "recent_runs": dashboard.recent_runs,
        "statistics": dashboard.statistics,
        "resource_usage": dashboard.resource_usage,
        "alerts": dashboard.alerts
    }


def get_statistics() -> Dict[str, Any]:
    """Get scheduler statistics."""
    global _scheduler

    if _scheduler is None:
        initialize()

    return _scheduler.get_statistics()


def get_performance_report(hours: int = 24) -> Dict[str, Any]:
    """Generate performance report."""
    global _monitor

    if _monitor is None:
        initialize()

    return _monitor.get_performance_report(hours=hours)


def shutdown(wait: bool = True):
    """
    Shutdown the scheduler gracefully.

    Args:
        wait: Wait for running tasks to complete
    """
    global _scheduler, _monitor

    if _scheduler is not None:
        _scheduler.stop()
        _scheduler = None

    if _monitor is not None:
        _monitor.stop()
        _monitor = None


# Task handler registration

# Use centralized handler registry from task_handlers module
# Re-export for backward compatibility
register_handler = register
unregister_handler = unregister
get_registered_handlers = list_handlers


__all__ = [
    # Core classes
    "TaskStorage",
    "TaskDefinition",
    "TaskRun",
    "TaskStatus",
    "TaskPriority",
    "TaskQueue",
    "TaskExecutor",
    "ExecutorType",
    "TaskScheduler",
    "SchedulingStrategy",
    "TaskMonitor",
    "CyclicDependencyError",

    # Initialization
    "initialize",
    "get_scheduler",
    "get_storage",
    "get_monitor",

    # API functions
    "schedule_task",
    "cancel_task",
    "get_task_status",
    "list_tasks",
    "wait_for_task",
    "get_task_logs",
    "get_dashboard",
    "get_statistics",
    "get_performance_report",
    "shutdown",

    # Handler registration
    "register_handler",
    "unregister_handler",
    "get_registered_handlers"
]
