#!/usr/bin/env python3
"""
Task Scheduler CLI
Command-line interface for managing the task scheduler.

Commands:
    task-scheduler-cli schedule <task_type> [options]   Schedule a task
    task-scheduler-cli cancel <run_id>                 Cancel a task
    task-scheduler-cli status <run_id>                Get task status
    task-scheduler-cli list [options]                 List tasks
    task-scheduler-cli queue                          Show queue status
    task-scheduler-cli monitor                        Live monitoring
    task-scheduler-cli stats                          Show statistics
    task-scheduler-cli logs <run_id>                  Show task logs
    task-scheduler-cli shutdown                       Shutdown scheduler
    task-scheduler-cli shell                          Open interactive shell
"""

import argparse
import json

# Add parent directory to path for imports
import os
import sys
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from . import (
    TaskDefinition,
    TaskPriority,
    cancel_task,
    get_dashboard,
    get_performance_report,
    get_statistics,
    get_task_logs,
    get_task_status,
    initialize,
    list_tasks,
    schedule_task,
    shutdown,
)


def cmd_schedule(args):
    """Schedule a new task."""
    task_type = args.type
    task_def = TaskDefinition(
        task_id=args.task_id or f"task-{int(time.time())}",
        name=args.name or f"Task {args.task_id or 'unknown'}",
        task_type=task_type,
        func=args.func,
        args=json.loads(args.args) if args.args else {},
        kwargs=json.loads(args.kwargs) if args.kwargs else {},
        timeout=args.timeout,
        max_retries=args.retries,
        priority=getattr(TaskPriority, args.priority.upper()).value if hasattr(TaskPriority, args.priority.upper()) else 2
    )

    # Add resource limits if specified
    if args.cpu or args.memory:
        task_def.resource_limits = {}
        if args.cpu:
            task_def.resource_limits["cpu_percent"] = args.cpu
        if args.memory:
            task_def.resource_limits["memory_mb"] = args.memory

    # Add dependencies if specified
    if args.dependencies:
        task_def.dependencies = args.dependencies.split(",")

    # Initialize scheduler
    initialize()

    # Schedule
    run_id = schedule_task(
        task_def=task_def,
        priority=task_def.priority,
        dependencies=task_def.dependencies,
        batch_key=args.batch_key,
        metadata={"cli": True, "user": args.user} if args.user else {"cli": True}
    )

    if run_id:
        print(f"✓ Scheduled task: {run_id}")
        print(f"  Task ID: {task_def.task_id}")
        print(f"  Type: {task_type}")
        print(f"  Priority: {task_def.priority}")
        print(f"  Status: {get_task_status(run_id)['status']}")
        return 0
    print("✗ Failed to schedule task")
    return 1


def cmd_cancel(args):
    """Cancel a task."""
    initialize()
    success = cancel_task(args.run_id)
    if success:
        print(f"✓ Cancelled task: {args.run_id}")
        return 0
    print(f"✗ Could not cancel task: {args.run_id} (not found or already completed)")
    return 1


def cmd_status(args):
    """Show task status."""
    initialize()
    status = get_task_status(args.run_id)
    if not status:
        print(f"✗ Task not found: {args.run_id}")
        return 1

    print(f"Task Status: {status['status']}")
    print(f"  Run ID: {status['run_id']}")
    print(f"  Task: {status['task_name']} ({status['task_id']})")
    print(f"  Priority: {status['priority']}")
    print(f"  Attempt: {status['attempt']}")
    print(f"  Queued: {status['queued_at']}")
    print(f"  Started: {status['started_at']}")
    print(f"  Completed: {status['completed_at']}")
    print(f"  In queue: {status['in_queue']}")
    print(f"  Active: {status['active']}")
    if status["error"]:
        print(f"  Error: {status['error'][:200]}")
    return 0


def cmd_list(args):
    """List tasks."""
    initialize()
    tasks = list_tasks(
        status=args.status,
        limit=args.limit,
        task_type=args.type
    )

    if not tasks:
        print("No tasks found.")
        return 0

    # Print header
    print(f"{'Run ID':<36} {'Task':<20} {'Status':<12} {'Priority':<8} {'Age':<12}")
    print("-" * 100)

    now = datetime.utcnow()
    for task in tasks:
        run_id = task["run_id"][:36]
        name = task["task_name"][:20]
        status = task["status"][:12]
        priority = str(task["priority"])[:8]

        # Calculate age
        if task["completed_at"]:
            age = "completed"
        elif task["started_at"]:
            start = datetime.fromisoformat(task["started_at"])
            age_sec = (now - start).total_seconds()
            age = f"{int(age_sec)}s"
        else:
            start = datetime.fromisoformat(task["queued_at"])
            age_sec = (now - start).total_seconds()
            if age_sec < 60:
                age = f"{int(age_sec)}s"
            elif age_sec < 3600:
                age = f"{int(age_sec/60)}m"
            else:
                age = f"{int(age_sec/3600)}h"

        print(f"{run_id:<36} {name:<20} {status:<12} {priority:<8} {age:<12}")

    print(f"\nTotal: {len(tasks)} tasks")
    return 0


def cmd_queue(args):
    """Show queue status."""
    initialize()
    dashboard = get_dashboard()

    queue = dashboard["queue_sizes"]
    print("Queue Status")
    print("-" * 40)
    print(f"  Ready:      {queue.get('ready', 0):6d}")
    print(f"  Delayed:    {queue.get('delayed', 0):6d}")
    print(f"  Pending:    {queue.get('pending_dependencies', 0):6d}")
    print(f"  Total:      {queue.get('total', 0):6d}")

    active = dashboard["active_tasks"]
    print(f"\nActive Tasks: {len(active)}")
    if active:
        for task in active[:10]:  # Show top 10
            print(f"  {task['run_id'][:12]}... {task['task_name']} ({task['elapsed_seconds']:.1f}s)")
        if len(active) > 10:
            print(f"  ... and {len(active) - 10} more")

    return 0


def cmd_monitor(args):
    """Live monitoring dashboard."""
    if not args.continuous:
        initialize()
        dashboard = get_dashboard()
        print_monitor_dashboard(dashboard)
        return 0

    try:
        initialize()
        while True:
            print("\033[2J\033[H")  # Clear screen
            dashboard = get_dashboard()
            print_monitor_dashboard(dashboard)
            time.sleep(args.refresh or 2)
    except KeyboardInterrupt:
        print("\nStopped.")
        return 0


def print_monitor_dashboard(dashboard):
    """Print formatted dashboard."""
    print("=" * 60)
    print(f"Task Scheduler Monitor - {dashboard['timestamp']}")
    print("=" * 60)

    # Queue section
    queue = dashboard["queue_sizes"]
    print(f"\n📤 Queue: Ready={queue.get('ready', 0)} Delayed={queue.get('delayed', 0)} Pending={queue.get('pending_dependencies', 0)} Total={queue.get('total', 0)}")

    # Active tasks
    active = dashboard["active_tasks"]
    print(f"\n🏃 Active Tasks: {len(active)}")
    if active:
        for task in active[:15]:
            print(f"  • {task['task_name']} ({task['run_id'][:12]}...) - {task['elapsed_seconds']:.1f}s")
        if len(active) > 15:
            print(f"  ... and {len(active) - 15} more")

    # Recent runs
    recent = dashboard["recent_runs"][:10]
    print("\n📋 Recent Runs:")
    for run in recent:
        status_icon = {
            "completed": "✓",
            "failed": "✗",
            "running": "🏃",
            "queued": "⏳",
            "pending": "⏳"
        }.get(run["status"], "?")
        print(f"  {status_icon} {run['run_id'][:12]}... {run['task_name']} - {run['status']}")

    # Statistics
    stats = dashboard["statistics"]
    print("\n📊 Statistics:")
    print(f"  Scheduled: {stats.get('total_scheduled', 0)}")
    print(f"  Success Rate (24h): {stats.get('success_rate_24h', 0)*100:.1f}%")
    print(f"  Avg Execution: {stats.get('avg_execution_seconds', 0):.1f}s")

    # Resources
    resources = dashboard["resource_usage"]
    if resources:
        print("\n💾 Resources:")
        for rtype, usage in resources.items():
            available = usage["available"]
            used = usage["current"]
            total = usage["limit"]
            print(f"  {rtype}: {used}/{total} ({available} available)")

    # Alerts
    alerts = dashboard["alerts"]
    if alerts:
        print("\n⚠️  Alerts:")
        for alert in alerts[-5:]:
            print(f"  [{alert['severity']}] {alert['message']}")


def cmd_stats(args):
    """Show statistics."""
    initialize()

    if args.detailed:
        report = get_performance_report(hours=args.hours)
        print(json.dumps(report, indent=2, default=str))
    else:
        stats = get_statistics()
        print("Scheduler Statistics")
        print("=" * 50)
        print(f"Total Task Definitions: {stats.get('total_task_definitions', 0)}")
        print(f"Total Scheduled: {stats.get('total_scheduled', 0)}")
        print(f"Total Rejected: {stats.get('total_rejected', 0)}")
        print(f"Success Rate (24h): {stats.get('success_rate_24h', 0)*100:.1f}%")
        print(f"Failure Rate (24h): {stats.get('failure_rate_24h', 0)*100:.1f}%")
        print(f"Runs Last Hour: {stats.get('runs_last_hour', 0)}")
        print(f"Avg Execution Time: {stats.get('avg_execution_seconds', 0):.1f}s")
        print("\nQueue Sizes:")
        for key, value in stats.get("queue_sizes", {}).items():
            print(f"  {key}: {value}")
        print("\nExecutor:")
        print(f"  Max Workers: {stats.get('max_workers', 0)}")
        print(f"  Active Tasks: {stats.get('executor_active', 0)}")
        print(f"  Batching Enabled: {stats.get('batching_enabled', False)}")


def cmd_logs(args):
    """Show task logs."""
    initialize()
    logs = get_task_logs(args.run_id, limit=args.limit, level=args.level)

    if not logs:
        print(f"No logs for task: {args.run_id}")
        return 0

    # Sort by timestamp
    logs.sort(key=lambda x: x["timestamp"], reverse=(args.reverse))

    for log in logs:
        timestamp = log["timestamp"][:19]
        level = log["level"][:5]
        msg = log["message"][:100]
        print(f"[{timestamp}] [{level:5}] {msg}")

        if args.verbose and "structured_data" in log and log["structured_data"]:
            print(f"  Data: {json.dumps(log['structured_data'], default=str)}")

    print(f"\nTotal: {len(logs)} log entries")
    return 0


def cmd_shutdown(args):
    """Shutdown scheduler."""
    print("Shutting down task scheduler...")
    shutdown(wait=not args.force)
    print("Done.")
    return 0


def cmd_shell(args):
    """Open interactive Python shell with scheduler context."""
    initialize()
    import code
    namespace = {
        "scheduler": get_scheduler(),
        "storage": get_storage(),
        "monitor": get_monitor(),
        "schedule_task": schedule_task,
        "cancel_task": cancel_task,
        "get_task_status": get_task_status,
        "list_tasks": list_tasks,
        "get_dashboard": get_dashboard,
        "get_statistics": get_statistics,
    }
    print("Task Scheduler Interactive Shell")
    print("Available variables: scheduler, storage, monitor, schedule_task, cancel_task, etc.")
    code.interact(local=namespace)
    return 0


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Task Scheduler CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    subparsers = parser.add_subparsers(dest="command", help="Command")

    # Schedule command
    schedule_parser = subparsers.add_parser("schedule", help="Schedule a new task")
    schedule_parser.add_argument("type", choices=["function", "shell", "http", "batch"],
                                 help="Task type")
    schedule_parser.add_argument("--task-id", help="Custom task ID")
    schedule_parser.add_argument("--name", help="Task name")
    schedule_parser.add_argument("--func", help="Function to execute (module.function)")
    schedule_parser.add_argument("--args", help="JSON arguments array")
    schedule_parser.add_argument("--kwargs", help="JSON arguments dict")
    schedule_parser.add_argument("--timeout", type=int, default=300,
                                 help="Timeout in seconds")
    schedule_parser.add_argument("--retries", type=int, default=3,
                                 help="Max retries")
    schedule_parser.add_argument("--priority", default="medium",
                                 choices=["critical", "high", "medium", "low", "background"],
                                 help="Priority level")
    schedule_parser.add_argument("--dependencies", help="Comma-separated run IDs")
    schedule_parser.add_argument("--batch-key", help="Batch key for aggregation")
    schedule_parser.add_argument("--cpu", type=float, help="CPU limit %")
    schedule_parser.add_argument("--memory", type=float, help="Memory limit MB")
    schedule_parser.add_argument("--user", help="User identifier")

    # Cancel command
    cancel_parser = subparsers.add_parser("cancel", help="Cancel a task")
    cancel_parser.add_argument("run_id", help="Run ID to cancel")

    # Status command
    status_parser = subparsers.add_parser("status", help="Show task status")
    status_parser.add_argument("run_id", help="Run ID")

    # List command
    list_parser = subparsers.add_parser("list", help="List tasks")
    list_parser.add_argument("--status", help="Filter by status")
    list_parser.add_argument("--type", help="Filter by task type")
    list_parser.add_argument("--limit", type=int, default=100, help="Max results")

    # Queue command
    queue_parser = subparsers.add_parser("queue", help="Show queue status")

    # Monitor command
    monitor_parser = subparsers.add_parser("monitor", help="Live monitoring")
    monitor_parser.add_argument("--continuous", "-c", action="store_true",
                                help="Continuous mode")
    monitor_parser.add_argument("--refresh", type=float, default=2,
                                help="Refresh interval seconds")

    # Stats command
    stats_parser = subparsers.add_parser("stats", help="Show statistics")
    stats_parser.add_argument("--detailed", "-d", action="store_true",
                              help="Detailed report")
    stats_parser.add_argument("--hours", type=int, default=24,
                              help="Time window hours")

    # Logs command
    logs_parser = subparsers.add_parser("logs", help="Show task logs")
    logs_parser.add_argument("run_id", help="Run ID")
    logs_parser.add_argument("--limit", type=int, default=100,
                             help="Max log entries")
    logs_parser.add_argument("--level", help="Filter by level")
    logs_parser.add_argument("--reverse", "-r", action="store_true",
                             help="Reverse order (newest first)")
    logs_parser.add_argument("--verbose", "-v", action="store_true",
                             help="Show structured data")

    # Shutdown command
    shutdown_parser = subparsers.add_parser("shutdown", help="Shutdown scheduler")
    shutdown_parser.add_argument("--force", "-f", action="store_true",
                                 help="Force shutdown (do not wait)")

    # Shell command
    shell_parser = subparsers.add_parser("shell", help="Interactive shell")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    try:
        if args.command == "schedule":
            return cmd_schedule(args)
        if args.command == "cancel":
            return cmd_cancel(args)
        if args.command == "status":
            return cmd_status(args)
        if args.command == "list":
            return cmd_list(args)
        if args.command == "queue":
            return cmd_queue(args)
        if args.command == "monitor":
            return cmd_monitor(args)
        if args.command == "stats":
            return cmd_stats(args)
        if args.command == "logs":
            return cmd_logs(args)
        if args.command == "shutdown":
            return cmd_shutdown(args)
        if args.command == "shell":
            return cmd_shell(args)
        parser.print_help()
        return 1
    except KeyboardInterrupt:
        print("\nInterrupted.")
        return 130
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
