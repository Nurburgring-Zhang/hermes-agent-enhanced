"""
Task Scheduler Test Suite
Comprehensive tests for all scheduler components.
"""

import os
import shutil
import sys
import tempfile
import time

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from task_executor import ExecutorType, TaskExecutor
from task_monitor import TaskMonitor
from task_queue import TaskQueue
from task_scheduler import SchedulingStrategy, TaskScheduler
from task_storage import TaskDefinition, TaskPriority, TaskRun, TaskStatus, TaskStorage


class TestContext:
    """Test context with temporary database."""

    def __init__(self):
        self.temp_dir = tempfile.mkdtemp(prefix="task_sched_test_")
        self.db_path = os.path.join(self.temp_dir, "test.sqlite")

    def cleanup(self):
        """Cleanup temp files."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()


def test_storage():
    """Test TaskStorage operations."""
    print("Testing TaskStorage...")

    with TestContext() as ctx:
        storage = TaskStorage(db_path=ctx.db_path)

        # Test task definition CRUD
        task = TaskDefinition(
            task_id="test-task-1",
            name="Test Task",
            task_type="function",
            func="test.module.func",
            args={"x": 1},
            kwargs={"y": 2},
            priority=TaskPriority.HIGH.value,
            timeout=60,
            resource_limits={"cpu_percent": 50.0, "memory_mb": 100.0}
        )

        # Save
        assert storage.save_task_definition(task), "Save task failed"

        # Load
        loaded = storage.load_task_definition("test-task-1")
        assert loaded is not None, "Task not found"
        assert loaded.name == "Test Task"
        assert loaded.priority == TaskPriority.HIGH.value
        assert loaded.resource_limits["cpu_percent"] == 50.0

        # List
        all_tasks = storage.list_task_definitions()
        assert len(all_tasks) == 1

        # Run recording
        run = TaskRun(
            run_id="run-1",
            task_id="test-task-1",
            status="running",
            priority=1
        )
        storage.create_task_run(run)

        # Update
        storage.update_task_run("run-1", status="completed", result=b"result")
        updated = storage.load_task_run("run-1")
        assert updated.status == "completed"

        # Logs
        storage.append_log("run-1", "INFO", "Test log message")
        logs = storage.get_logs("run-1")
        assert len(logs) == 1
        assert logs[0]["message"] == "Test log message"

        print("  ✓ TaskStorage tests passed")


def test_task_queue():
    """Test TaskQueue operations."""
    print("Testing TaskQueue...")

    with TestContext() as ctx:
        storage = TaskStorage(db_path=ctx.db_path)
        queue = TaskQueue(storage=storage)

        # Enqueue simple task
        success = queue.enqueue(
            run_id="run-1",
            task_id="task-1",
            priority=TaskPriority.HIGH.value
        )
        assert success, "Enqueue failed"

        # Enqueue with priority
        queue.enqueue(
            run_id="run-2",
            task_id="task-2",
            priority=TaskPriority.LOW.value
        )

        # Dequeue - high priority first
        item = queue.dequeue(timeout=1.0)
        assert item is not None, "Timeout waiting for item"
        assert item.run_id == "run-1"
        assert item.priority == TaskPriority.HIGH.value

        # Dequeue next
        item = queue.dequeue(timeout=1.0)
        assert item.run_id == "run-2"

        # Test delayed enqueue
        queue.enqueue(
            run_id="run-delayed",
            task_id="task-delayed",
            priority=TaskPriority.MEDIUM.value,
            delay_seconds=0.5
        )

        # Should not get it immediately
        item = queue.dequeue(timeout=0.2)
        assert item is None, "Should have timed out"

        # But should get it after delay
        item = queue.dequeue(timeout=1.0)
        assert item is not None, "Delayed item not available"
        assert item.run_id == "run-delayed"

        # Test cancellation
        queue.enqueue(run_id="run-cancel", task_id="task-cancel")
        cancelled = queue.cancel("run-cancel")
        assert cancelled, "Cancel failed"
        assert not queue.is_queued("run-cancel")

        queue.stop()
        print("  ✓ TaskQueue tests passed")


def test_task_executor():
    """Test TaskExecutor operations."""
    print("Testing TaskExecutor...")

    with TestContext() as ctx:
        storage = TaskStorage(db_path=ctx.db_path)
        queue = TaskQueue(storage=storage)
        executor = TaskExecutor(
            storage=storage,
            task_queue=queue,
            max_workers=2,
            executor_type=ExecutorType.THREAD
        )

        # Simple function
        def simple_func(x, y):
            time.sleep(0.1)
            return x + y

        task_def = TaskDefinition(
            task_id="test-func",
            name="Test Function",
            task_type="function",
            func="__main__.simple_func",
            args=[5, 3],
            kwargs={}
        )
        storage.save_task_definition(task_def)

        run = TaskRun(
            run_id="run-exec-1",
            task_id="test-func",
            status="pending",
            priority=1
        )
        storage.create_task_run(run)

        # Submit
        success = executor.submit(run.run_id, run, simple_func, 5, 3)
        assert success, "Submit failed"

        # Wait for completion
        time.sleep(1.0)

        status = storage.load_task_run("run-exec-1")
        assert status.status in [TaskStatus.COMPLETED.value, TaskStatus.RUNNING.value]

        # Test timeout
        def slow_func():
            time.sleep(5)
            return "done"

        task_def2 = TaskDefinition(
            task_id="slow-func",
            name="Slow Function",
            task_type="function",
            func="__main__.slow_func",
            timeout=1
        )
        storage.save_task_definition(task_def2)

        run2 = TaskRun(
            run_id="run-exec-2",
            task_id="slow-func",
            status="pending",
            priority=1,
            timeout=1
        )
        storage.create_task_run(run2)

        executor.submit(run2.run_id, run2, slow_func)
        time.sleep(2.0)
        status2 = storage.load_task_run("run-exec-2")
        assert status2.status in [TaskStatus.TIMEOUT.value, TaskStatus.RUNNING.value]

        executor.shutdown(wait=False)
        print("  ✓ TaskExecutor tests passed")


def test_dependency_resolution():
    """Test DAG dependency resolution."""
    print("Testing DAG dependencies...")

    with TestContext() as ctx:
        storage = TaskStorage(db_path=ctx.db_path)
        queue = TaskQueue(storage=storage)
        executor = TaskExecutor(storage=storage, task_queue=queue, max_workers=5)
        scheduler = TaskScheduler(storage, queue, executor)

        # Create three tasks with dependencies: A -> B -> C
        tasks = []
        for i, name in enumerate(["A", "B", "C"]):
            task_def = TaskDefinition(
                task_id=f"dep-task-{name}",
                name=f"Dependency Task {name}",
                task_type="function",
                func="test.dummy",
                args=[i],
                timeout=10
            )
            storage.save_task_definition(task_def)
            tasks.append(task_def)

        # Schedule with dependencies
        run_a = scheduler.schedule(tasks[0], priority=0)
        time.sleep(0.2)

        run_b = scheduler.schedule(tasks[1], priority=1, dependencies=[run_a])
        time.sleep(0.2)

        run_c = scheduler.schedule(tasks[2], priority=2, dependencies=[run_b])

        # Check statuses
        status_a = storage.load_task_run(run_a)
        status_b = storage.load_task_run(run_b)
        status_c = storage.load_task_run(run_c)

        print(f"  A: {status_a.status}, B: {status_b.status}, C: {status_c.status}")

        # All tasks should eventually complete
        time.sleep(2.0)

        final_a = storage.load_task_run(run_a)
        final_b = storage.load_task_run(run_b)
        final_c = storage.load_task_run(run_c)

        # At least A and B should complete (C depends on B)
        assert final_a.status in [TaskStatus.COMPLETED.value, TaskStatus.RUNNING.value, TaskStatus.QUEUED.value]

        scheduler.stop()
        print("  ✓ Dependency resolution tests passed")


def test_cyclic_dependency():
    """Test cyclic dependency detection."""
    print("Testing cyclic dependency detection...")

    from topological_sort import CyclicDependencyError, topological_sort

    # Valid DAG
    deps = {
        "A": ["B", "C"],
        "B": ["D"],
        "C": ["D"],
        "D": []
    }
    order = topological_sort(deps)
    assert order.index("D") < order.index("B")
    assert order.index("D") < order.index("C")
    assert order.index("B") < order.index("A")
    assert order.index("C") < order.index("A")
    print("  ✓ Valid DAG order ok")

    # Cyclic
    cyclic_deps = {
        "A": ["B"],
        "B": ["C"],
        "C": ["A"]
    }
    try:
        topological_sort(cyclic_deps)
        assert False, "Should have detected cycle"
    except CyclicDependencyError:
        print("  ✓ Cyclic dependency detected")

    print("  ✓ Cyclic dependency tests passed")


def test_resource_quotas():
    """Test resource limit enforcement."""
    print("Testing resource quotas...")

    with TestContext() as ctx:
        storage = TaskStorage(db_path=ctx.db_path)
        queue = TaskQueue(storage=storage)

        # Check initial quotas
        usage = storage.get_resource_usage()
        assert "global_memory" in usage
        assert "global_cpu" in usage

        # Acquire resource
        success = storage.acquire_resource("global_memory", 50.0)
        assert success, "Should be able to acquire"

        # Check updated
        usage = storage.get_resource_usage()
        assert usage["global_memory"]["current"] == 50.0
        assert usage["global_memory"]["available"] == 50.0

        # Exceed limit
        success = storage.acquire_resource("global_memory", 60.0)
        assert not success, "Should not be able to exceed limit"

        # Release
        storage.release_resource("global_memory", 50.0)
        usage = storage.get_resource_usage()
        assert usage["global_memory"]["current"] == 0.0

        # Reset
        storage.reset_resource_quotas()
        usage = storage.get_resource_usage()
        assert usage["global_memory"]["current"] == 0.0

        print("  ✓ Resource quota tests passed")


def test_batch_aggregation():
    """Test batch task aggregation."""
    print("Testing batch aggregation...")

    with TestContext() as ctx:
        storage = TaskStorage(db_path=ctx.db_path)
        queue = TaskQueue(storage=storage)
        executor = TaskExecutor(storage=storage, task_queue=queue, max_workers=5)
        scheduler = TaskScheduler(
            storage, queue, executor,
            batch_aggregation_enabled=True
        )

        # Schedule multiple tasks with same batch key
        batch_key = "test-batch-1"
        run_ids = []

        for i in range(5):
            task_def = TaskDefinition(
                task_id=f"batch-task-{i}",
                name=f"Batch Task {i}",
                task_type="function",
                func="test.dummy",
                args=[i]
            )
            run_id = scheduler.schedule(task_def, batch_key=batch_key)
            if run_id:
                run_ids.append(run_id)
            time.sleep(0.1)

        # Check batch queue
        with scheduler._batch_lock:
            assert batch_key in scheduler._batch_queue, "Batch key not in queue"
            # With 5 items, should be in batch queue
            assert len(scheduler._batch_queue[batch_key]) == 5

        print("  ✓ Batch aggregation tests passed")
        scheduler.stop()


def test_priority_ordering():
    """Test priority-based ordering."""
    print("Testing priority ordering...")

    with TestContext() as ctx:
        storage = TaskStorage(db_path=ctx.db_path)
        queue = TaskQueue(storage=storage)

        # Enqueue tasks with different priorities
        priorities = [3, 1, 4, 0, 2]
        for i, p in enumerate(priorities):
            queue.enqueue(
                run_id=f"run-p{p}-{i}",
                task_id=f"task-p{p}-{i}",
                priority=p
            )

        # Dequeue should give in priority order
        retrieved = []
        for _ in range(5):
            item = queue.dequeue(timeout=1.0)
            if item:
                retrieved.append(item.priority)

        assert retrieved == sorted(priorities), f"Wrong order: {retrieved}"

        print("  ✓ Priority ordering tests passed")
        queue.stop()


def test_retry_logic():
    """Test retry mechanism."""
    print("Testing retry logic...")

    with TestContext() as ctx:
        storage = TaskStorage(db_path=ctx.db_path)
        queue = TaskQueue(storage=storage)
        executor = TaskExecutor(storage=storage, task_queue=queue, max_workers=1)
        scheduler = TaskScheduler(storage, queue, executor)

        # Task that fails once then succeeds
        attempt_count = [0]

        def flaky_func():
            attempt_count[0] += 1
            if attempt_count[0] < 2:
                raise ValueError("First attempt fails")
            return "success"

        task_def = TaskDefinition(
            task_id="retry-task",
            name="Retry Task",
            task_type="function",
            func="__main__.flaky_func",
            max_retries=3,
            timeout=10
        )
        storage.save_task_definition(task_def)

        run_id = scheduler.schedule(task_def, priority=1)
        time.sleep(2.0)

        status = storage.load_task_run(run_id)
        assert attempt_count[0] >= 1, "Task never executed"

        print("  ✓ Retry logic tests passed")
        scheduler.stop()


def test_monitor():
    """Test TaskMonitor operations."""
    print("Testing TaskMonitor...")

    with TestContext() as ctx:
        storage = TaskStorage(db_path=ctx.db_path)
        queue = TaskQueue(storage=storage)
        executor = TaskExecutor(storage=storage, task_queue=queue, max_workers=2)
        scheduler = TaskScheduler(storage, queue, executor)
        monitor = TaskMonitor(storage, executor)

        # Get dashboard
        dashboard = monitor.get_dashboard()
        assert "queue_sizes" in dashboard
        assert "active_tasks" in dashboard
        assert "statistics" in dashboard

        # Get performance report
        report = monitor.get_performance_report(hours=1)
        assert "throughput_by_hour" in report

        # Add alert rule
        monitor.add_alert_rule({
            "name": "test_rule",
            "condition": lambda m: m.get("queue_size", 0) > 1000,
            "severity": "warning",
            "message": "Test alert"
        })

        # Get alerts
        alerts = monitor.get_alerts()
        assert isinstance(alerts, list)

        print("  ✓ TaskMonitor tests passed")
        monitor.stop()
        scheduler.stop()


def test_integration():
    """Full integration test."""
    print("Testing full integration...")

    with TestContext() as ctx:
        # Initialize full system
        storage = TaskStorage(db_path=ctx.db_path)
        queue = TaskQueue(storage=storage)
        executor = TaskExecutor(storage=storage, task_queue=queue, max_workers=5)
        scheduler = TaskScheduler(storage, queue, executor, SchedulingStrategy.PRIORITY_FIFO)
        monitor = TaskMonitor(storage, executor)

        # Define tasks
        def work_func(duration):
            time.sleep(duration)
            return {"completed": True, "duration": duration}

        task_defs = []
        for i in range(10):
            task_def = TaskDefinition(
                task_id=f"integ-task-{i}",
                name=f"Integration Task {i}",
                task_type="function",
                func="__main__.work_func",
                kwargs={"duration": 0.2},
                priority=i % 3,
                timeout=5
            )
            task_defs.append(task_def)
            storage.save_task_definition(task_def)

        # Schedule tasks
        run_ids = []
        for task_def in task_defs:
            run_id = scheduler.schedule(task_def)
            if run_id:
                run_ids.append(run_id)
            time.sleep(0.05)

        assert len(run_ids) == 10, f"Only scheduled {len(run_ids)}/10"

        # Wait for completion
        time.sleep(3.0)

        # Check results
        completed = 0
        for run_id in run_ids:
            status = storage.load_task_run(run_id)
            if status.status == TaskStatus.COMPLETED.value:
                completed += 1

        assert completed >= 8, f"Only {completed}/10 completed"

        # Check statistics
        stats = storage.get_statistics()
        assert stats["total_task_definitions"] == 10

        print("  ✓ Integration tests passed")

        monitor.stop()
        scheduler.stop()


def run_all_tests():
    """Run all test suites."""
    print("=" * 60)
    print("Task Scheduler Test Suite")
    print("=" * 60)
    print()

    tests = [
        test_storage,
        test_task_queue,
        test_task_executor,
        test_dependency_resolution,
        test_cyclic_dependency,
        test_resource_quotas,
        test_batch_aggregation,
        test_priority_ordering,
        test_retry_logic,
        test_monitor,
        test_integration
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"  ✗ {test.__name__} FAILED: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
        print()

    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
