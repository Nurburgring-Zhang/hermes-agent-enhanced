"""
Task Queue Module
Multi-priority queue with delayed tasks and persistence.
"""

import heapq
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

from task_storage import TaskPriority, TaskStorage


class QueueStatus(Enum):
    """Queue item status."""
    WAITING = "waiting"
    READY = "ready"
    DELAYED = "delayed"
    FAILED = "failed"


@dataclass
class QueueItem:
    """Item in the queue."""
    run_id: str
    task_id: str
    priority: int
    enqueued_at: float
    scheduled_time: float | None = None  # for delayed tasks
    dependencies_met: bool = False
    attempt: int = 0
    metadata: dict[str, Any] | None = None

    def __lt__(self, other):
        """Compare for priority queue (priority first, then time)."""
        # Lower priority number = higher priority
        if self.priority != other.priority:
            return self.priority < other.priority
        # Same priority: earlier enqueued first
        return self.enqueued_at < other.enqueued_at


class TaskQueue:
    """
    Multi-priority task queue with support for delayed execution.
    Uses heap-based priority queue with O(log n) enqueue/dequeue.
    """

    def __init__(self, storage: TaskStorage):
        """Initialize queue."""
        self.storage = storage
        self._lock = threading.RLock()
        self._ready_queue = []  # heap queue of ready items
        self._delayed_queue = []  # heap of (scheduled_time, item)
        self._item_by_run_id: dict[str, QueueItem] = {}
        self._pending_runs: list[str] = []  # run_ids waiting on dependencies
        self._condition = threading.Condition(self._lock)
        self._running = True
        self._queue_thread = threading.Thread(
            target=self._queue_manager,
            daemon=True,
            name="TaskQueue-Manager"
        )
        self._queue_thread.start()

    def enqueue(
        self,
        run_id: str,
        task_id: str,
        priority: int = TaskPriority.MEDIUM.value,
        delay_seconds: float | None = None,
        dependencies: list[str] | None = None,
        attempt: int = 0,
        metadata: dict[str, Any] | None = None
    ) -> bool:
        """
        Enqueue a task run.

        Args:
            run_id: Unique run identifier
            task_id: Task definition ID
            priority: Priority (0-4, lower is higher)
            delay_seconds: Delay execution by N seconds
            dependencies: List of task_ids that must complete first
            attempt: Current retry attempt
            metadata: Additional metadata

        Returns:
            True if enqueued successfully
        """
        with self._lock:
            if run_id in self._item_by_run_id:
                return False  # already enqueued

            now = time.time()
            scheduled_time = now + delay_seconds if delay_seconds else now

            item = QueueItem(
                run_id=run_id,
                task_id=task_id,
                priority=priority,
                enqueued_at=now,
                scheduled_time=scheduled_time,
                dependencies_met=not bool(dependencies),  # true if no deps
                attempt=attempt,
                metadata=metadata
            )

            # Check dependencies if provided
            if dependencies:
                if self._are_dependencies_met(dependencies):
                    item.dependencies_met = True
                else:
                    self._pending_runs.append(run_id)

            # Store in appropriate queue
            if item.dependencies_met and (delay_seconds is None or delay_seconds <= 0):
                heapq.heappush(self._ready_queue, item)
            else:
                heapq.heappush(self._delayed_queue, (scheduled_time, item))

            self._item_by_run_id[run_id] = item
            self._condition.notify()

            # Update storage status
            self.storage.update_task_run(run_id, status="queued", queued_at=datetime.utcnow().isoformat())

            return True

    def dequeue(self, timeout: float | None = None) -> QueueItem | None:
        """
        Dequeue next ready task (blocks until item available).

        Args:
            timeout: Maximum time to wait (None = forever)

        Returns:
            Next ready QueueItem or None if timeout
        """
        deadline = None if timeout is None else time.time() + timeout

        with self._condition:
            while self._running:
                # Check for ready items
                while self._ready_queue and self._ready_queue[0].dependencies_met:
                    item = heapq.heappop(self._ready_queue)
                    if item.run_id in self._item_by_run_id:
                        del self._item_by_run_id[item.run_id]
                        if item.run_id in self._pending_runs:
                            self._pending_runs.remove(item.run_id)
                        return item

                # Process delayed items that may be ready now
                current_time = time.time()
                while self._delayed_queue and self._delayed_queue[0][0] <= current_time:
                    scheduled_time, item = heapq.heappop(self._delayed_queue)
                    if item.dependencies_met:
                        heapq.heappush(self._ready_queue, item)
                    else:
                        # Still waiting on deps, put back with None time
                        heapq.heappush(self._delayed_queue, (None, item))

                # If no items ready, wait
                if deadline is not None and time.time() >= deadline:
                    return None

                wait_time = None
                if deadline is not None:
                    wait_time = min(1.0, deadline - time.time())
                    if wait_time <= 0:
                        return None

                self._condition.wait(wait_time)

            return None

    def mark_dependencies_met(self, completed_run_id: str):
        """
        Mark tasks that depend on this run as ready if all deps satisfied.

        Args:
            completed_run_id: Run ID that just completed
        """
        with self._lock:
            dependents = self.storage.get_dependents(completed_run_id)

            for run_id in self._pending_runs[:]:  # copy list to allow modification
                if run_id not in self._item_by_run_id:
                    self._pending_runs.remove(run_id)
                    continue

                item = self._item_by_run_id[run_id]
                task_deps = self.storage.get_dependencies(item.task_id)

                if all(dep in [completed_run_id] or self._is_task_completed(dep)
                      for dep in task_deps):
                    # All dependencies met
                    item.dependencies_met = True
                    self._pending_runs.remove(run_id)
                    if item.scheduled_time and item.scheduled_time > time.time():
                        heapq.heappush(self._delayed_queue, (item.scheduled_time, item))
                    else:
                        heapq.heappush(self._ready_queue, item)
                        self._condition.notify()

    def _is_task_completed(self, task_id: str) -> bool:
        """Check if all runs for a task have completed successfully."""
        # Check latest run for task
        runs = self.storage.list_task_runs(task_id=task_id, limit=1)
        if not runs:
            return False
        return runs[0].status in ["completed"]

    def _are_dependencies_met(self, dependencies: list[str]) -> bool:
        """Check if all dependencies are satisfied."""
        for dep in dependencies:
            runs = self.storage.list_task_runs(task_id=dep, limit=1)
            if not runs or runs[0].status != "completed":
                return False
        return True

    def requeue(self, run_id: str, priority: int | None = None, delay_seconds: float | None = None):
        """Re-queue a failed task (for retries)."""
        with self._lock:
            if run_id not in self._item_by_run_id:
                return False

            item = self._item_by_run_id[run_id]
            if priority is not None:
                item.priority = priority
            if delay_seconds:
                item.scheduled_time = time.time() + delay_seconds
                item.attempt += 1

            # Reinsert into appropriate queue
            if item.dependencies_met:
                if item.scheduled_time and item.scheduled_time > time.time():
                    heapq.heappush(self._delayed_queue, (item.scheduled_time, item))
                else:
                    heapq.heappush(self._ready_queue, item)
                    self._condition.notify()
            else:
                heapq.heappush(self._delayed_queue, (item.scheduled_time, item))

            return True

    def cancel(self, run_id: str) -> bool:
        """Cancel a queued task."""
        with self._lock:
            if run_id not in self._item_by_run_id:
                return False

            item = self._item_by_run_id[run_id]
            del self._item_by_run_id[run_id]

            if run_id in self._pending_runs:
                self._pending_runs.remove(run_id)

            # Remove from queues (linear search, but queues are small-ish)
            self._ready_queue = [i for i in self._ready_queue if i.run_id != run_id]
            heapq.heapify(self._ready_queue)

            self._delayed_queue = [(t, i) for t, i in self._delayed_queue if i.run_id != run_id]
            heapq.heapify(self._delayed_queue)

            return True

    def is_queued(self, run_id: str) -> bool:
        """Check if run is currently queued."""
        with self._lock:
            return run_id in self._item_by_run_id

    def queue_size(self) -> dict[str, int]:
        """Get queue sizes."""
        with self._lock:
            return {
                "ready": len(self._ready_queue),
                "delayed": len(self._delayed_queue),
                "pending_dependencies": len(self._pending_runs),
                "total": len(self._item_by_run_id)
            }

    def get_queued_runs(self) -> list[str]:
        """Get list of all queued run IDs."""
        with self._lock:
            return list(self._item_by_run_id.keys())

    def _queue_manager(self):
        """Background thread that monitors delayed queue and promotes items."""
        while self._running:
            try:
                time.sleep(0.1)  # Check every 100ms

                with self._lock:
                    current_time = time.time()

                    # Check delayed queue
                    while self._delayed_queue and self._delayed_queue[0][0] <= current_time:
                        scheduled_time, item = heapq.heappop(self._delayed_queue)

                        if item.run_id not in self._item_by_run_id:
                            continue  # item was cancelled

                        if item.dependencies_met:
                            heapq.heappush(self._ready_queue, item)
                            self._condition.notify()
                        else:
                            # Put back with None (still waiting on deps)
                            heapq.heappush(self._delayed_queue, (None, item))

            except Exception as e:
                # Log error but continue
                try:
                    from task_logger import TaskLogger
                    TaskLogger.log_error(f"Queue manager error: {e}")
                except:
                    pass
                time.sleep(1.0)

    def drain(self) -> list[QueueItem]:
        """Drain all items from ready queue (for shutdown)."""
        with self._lock:
            items = list(self._ready_queue)
            self._ready_queue.clear()
            self._item_by_run_id.clear()
            self._pending_runs.clear()
            self._delayed_queue.clear()
            return items

    def stop(self):
        """Stop the queue manager thread."""
        self._running = False
        with self._condition:
            self._condition.notify_all()
        self._queue_thread.join(timeout=5)
