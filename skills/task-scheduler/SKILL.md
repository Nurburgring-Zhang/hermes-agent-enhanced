---
name: task-scheduler
description: High-performance task scheduler with priority queues, DAG dependencies, resource limits, and persistent storage
version: 1.0.0
author: Hermes Research
license: MIT
metadata:
  hermes:
    tags: [scheduler, tasks, async, priority-queue, dag, dependencies, resource-management, retry, checkpoint]
    related_skills: [workflow-engine, autonomous-ai-agents]
---

# Task Scheduler Skill

A comprehensive, production-ready task scheduling system for Hermes that provides asynchronous task execution with priority queues, DAG dependency resolution, resource quotas, retry logic, and full persistence.

## Features

## 触发条件
- 用户提及此功能相关关键词时
- 遇到此领域的标准问题时
- 需要执行该领域的标准操作时


### Core Scheduling
- **Multi-Priority Queue**: 5 priority levels (0-4, 0=critical) with FIFO ordering within priority
- **DAG Dependencies**: Automatic topological sorting with cycle detection
- **Resource Quotas**: CPU, memory, concurrency limits with enforcement
- **Timeout Control**: Per-task timeout with automatic cancellation
- **Retry Logic**: Exponential backoff configurable per task
- **Checkpointing**: Save/restore state for long-running tasks
- **Batch Aggregation**: Combine similar tasks for efficiency

### Persistence & Reliability
- **SQLite Storage**: Full ACID compliance with WAL mode
- **Transaction Safety**: All operations atomic with rollback
- **Crash Recovery**: Queues and run state survive restarts
- **Audit Logging**: Complete execution history with structured logs

### Monitoring & Management
- **Real-time Dashboard**: Queue status, active tasks, resource usage
- **Metrics History**: Time-series metrics (configurable retention)
- **Alerting**: Custom alert rules with handlers
- **Performance Reports**: Throughput, success rate, execution times

### APIs
- **Python API**: Simple function-based interface (`schedule_task`, `cancel_task`, etc.)
- **CLI**: Full command-line interface for administration
- **Hermes Integration**: Message-based task creation and management

---

## Quick Start

### 1. Install Dependencies

```bash
pip install psutil
```

### 2. Basic Usage

```python
from task_scheduler import (
    initialize, schedule_task, wait_for_task, get_task_status, TaskDefinition
)

# Initialize the scheduler
scheduler = initialize(
    db_path="~/.hermes/tasks.sqlite",
    max_workers=10,
    executor_type="thread"  # or "process"
)

# Define a task
task = TaskDefinition(
    task_id="my_task",
    name="My First Task",
    task_type="function",  # or 'shell', 'http', 'batch'
    func="mymodule.my_function",  # module.function path
    kwargs={"param1": "value", "param2": 42},
    timeout=300,  # 5 minutes
    priority=2  # MEDIUM (0=CRITICAL, 1=HIGH, 2=MEDIUM, 3=LOW, 4=BACKGROUND)
)

# Schedule it
run_id = schedule_task(task)
print(f"Task scheduled: {run_id}")

# Wait for completion
final_status = wait_for_task(run_id, timeout=600)
print(f"Final status: {final_status}")

# Check status anytime
status = get_task_status(run_id)
```

### 3. Using Task Functions

```python
# Define function to execute
def process_data(source_file, output_dir):
    import subprocess
    result = subprocess.run(
        f"process {source_file} --output {output_dir}",
        shell=True, capture_output=True
    )
    return {
        'returncode': result.returncode,
        'output': result.stdout.decode()
    }

# Register the handler (optional, alternative to full module path)
from task_scheduler import register_handler
register_handler('process_data', process_data)

# Use in task
task = TaskDefinition(
    task_id="data_job",
    task_type="function",
    func="process_data"  # if registered, or "mymodule.process_data"
)
```

### 4. Dependencies

```python
# Task B depends on A completing successfully
run_a = schedule_task(task_a)
run_b = schedule_task(task_b, dependencies=[run_a])

# Multiple dependencies
run_c = schedule_task(task_c, dependencies=[run_a, run_b])

# Cyclic dependencies are rejected with CyclicDependencyError
```

### 5. Resource Limits

```python
task = TaskDefinition(
    task_id="heavy_job",
    task_type="function",
    func="mymodule.heavy_function",
    resource_limits={
        'cpu_percent': 50.0,    # Max 50% CPU
        'memory_mb': 512        # Max 512MB memory
    }
)
```

### 6. Retry with Backoff

```python
task = TaskDefinition(
    task_id="unreliable_job",
    task_type="function",
    func="mymodule.unreliable_api_call",
    max_retries=5,
    timeout=60
)
# Retry is automatic on any exception with exponential backoff
```

### 7. Batch Tasks

```python
# Tasks with same batch_key are aggregated and can be processed together
for item in items:
    task = TaskDefinition(
        task_id=f"process_{item.id}",
        task_type="function",
        func="process_item",
        kwargs={"item": item}
    )
    schedule_task(task, batch_key="batch_process_items")
```

### 8. Delayed Execution

```python
# Schedule task to run in 5 minutes
run_id = schedule_task(task, delay_seconds=300)
```

### 9. Shell & HTTP Tasks

```python
# Shell command
task = TaskDefinition(
    task_id="backup",
    task_type="shell",
    func="",  # not used
    kwargs={"command": "pg_dump mydb > backup.sql"}
)

# HTTP request
task = TaskDefinition(
    task_id="api_call",
    task_type="http",
    kwargs={
        "url": "https://api.example.com/endpoint",
        "method": "POST",
        "json": {"key": "value"}
    }
)
```

---

## Command Line Interface

### CLI Commands

```bash
# Schedule a task
task-scheduler-cli schedule function \
  --name "My Task" \
  --func "mymodule.my_function" \
  --kwargs '{"param": "value"}' \
  --priority high \
  --timeout 300

# Check status
task-scheduler-cli status <run_id>

# List tasks
task-scheduler-cli list --status running --limit 50

# Cancel a task
task-scheduler-cli cancel <run_id>

# Show queue
task-scheduler-cli queue

# Live monitoring
task-scheduler-cli monitor --continuous

# Statistics
task-scheduler-cli stats --detailed

# View logs
task-scheduler-cli logs <run_id> --limit 100

# Interactive shell
task-scheduler-cli shell

# Shutdown
task-scheduler-cli shutdown
```

---

## API Reference

### Initialization

```python
scheduler = initialize(
    db_path: Optional[str] = None,           # Default: ~/.hermes/task-scheduler/tasks.sqlite
    max_workers: int = 10,                   # Max concurrent tasks
    executor_type: ExecutorType = ExecutorType.THREAD,  # THREAD or PROCESS
    scheduling_strategy: SchedulingStrategy = SchedulingStrategy.PRIORITY_FIFO
) -> TaskScheduler
```

### TaskDefinition

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `task_id` | str | No (auto-generated) | Unique identifier |
| `name` | str | Yes | Human-readable name |
| `task_type` | str | Yes | `function`, `shell`, `http`, `batch` |
| `func` | str | Conditionally | Module path `module.function` |
| `args` | list | No | Positional arguments |
| `kwargs` | dict | No | Keyword arguments |
| `priority` | int | No (default=2) | 0-4 (CRITICAL to BACKGROUND) |
| `timeout` | int | No (default=300) | Seconds before timeout |
| `max_retries` | int | No (default=3) | Max retry attempts |
| `resource_limits` | dict | No | `{"cpu_percent": 50, "memory_mb": 512}` |
| `dependencies` | list[str] | No | List of run IDs |
| `checkpoint` | str | No | Checkpoint function name |
| `template` | str | No | Template name for parameterization |
| `template_vars` | dict | No | Template variable values |

### API Functions

| Function | Description |
|----------|-------------|
| `schedule_task(task_def, priority, dependencies, timeout, ...)` | Schedule a task, returns run_id |
| `cancel_task(run_id)` | Cancel a scheduled or running task |
| `get_task_status(run_id)` | Get detailed status dict |
| `list_tasks(status=None, limit=100, task_type=None)` | List task runs |
| `wait_for_task(run_id, timeout=None)` | Block until completion |
| `get_task_logs(run_id, limit=100)` | Get execution logs |
| `get_dashboard()` | Get real-time dashboard data |
| `get_statistics()` | Get scheduler statistics |
| `get_performance_report(hours=24)` | Generate performance report |
| `shutdown(wait=True)` | Gracefully shutdown scheduler |

### TaskStatus Enum

```python
class TaskStatus(Enum):
    PENDING = "pending"      # Created but not queued
    QUEUED = "queued"        # In queue waiting
    RUNNING = "running"      # Currently executing
    COMPLETED = "completed"  # Successfully finished
    FAILED = "failed"        # Execution failed
    CANCELLED = "cancelled"  # User cancelled
    TIMEOUT = "timeout"      # Exceeded timeout
    RETRYING = "retrying"    # Will retry
```

### TaskPriority Enum

```python
class TaskPriority(Enum):
    CRITICAL = 0   # Highest priority
    HIGH = 1       # High priority
    MEDIUM = 2     # Default
    LOW = 3        # Low priority
    BACKGROUND = 4 # Lowest priority (batch/background jobs)
```

---

## Data Model

### Database Schema

The scheduler uses SQLite with these main tables:

**task_definitions**
- `task_id` (PK) - Unique task identifier
- `name`, `task_type`, `func`, `args`, `kwargs`
- `priority`, `max_retries`, `timeout`
- `resource_limits` (JSON), `dependencies` (JSON array)
- `checkpoint`, `template`, `template_vars`
- `created_at`, `updated_at`

**task_runs**
- `run_id` (PK) - Unique run identifier
- `task_id` (FK) - Reference to definition
- `status`, `priority`, `attempt`
- `queued_at`, `started_at`, `completed_at`, `timeout_at`
- `result` (BLOB - pickled), `error`, `traceback`
- `checkpoint_data` (BLOB), `worker_id`
- `resource_usage` (JSON), `metadata` (JSON)
- `created_at`

**task_logs**
- `log_id` (AUTOINCREMENT)
- `run_id` (FK), `timestamp`, `level`, `message`
- `structured_data` (JSON)

**task_dependencies**
- `task_id`, `depends_on` - DAG edges

**resource_quotas**
- `resource_type` (PK) - e.g., "global_memory"
- `limit_value`, `current_usage`, `updated_at`

---

## Advanced Usage

### Custom Scheduling Strategy

```python
from task_scheduler import TaskScheduler, SchedulingStrategy

scheduler = TaskScheduler(
    storage=storage,
    queue=queue,
    executor=executor,
    strategy=SchedulingStrategy.SHORTEST_JOB_FIRST  # or LEAST_LOADED
)
```

### Custom Alert Handlers

```python
def send_alert(alert):
    severity = alert['severity']
    message = alert['message']
    if severity == 'critical':
        send_email("admin@example.com", f"CRITICAL: {message}")
    elif severity == 'warning':
        log_to_slack(f"⚠️ {message}")

monitor = TaskMonitor(storage, executor, alert_handlers=[send_alert])
```

### Checkpointing

```python
def long_task(checkpoint_state=None):
    state = checkpoint_state or {"step": 0, "data": []}

    # Process in chunks
    for i in range(state['step'], 1000):
        # Do work
        state['step'] = i
        state['data'].append(process_chunk(i))

        # Save checkpoint every 100 steps
        if i % 100 == 0:
            save_checkpoint(state)  # Implementation-specific

    return state

task = TaskDefinition(
    task_id="long_running",
    task_type="function",
    func="mymodule.long_task",
    checkpoint="save_checkpoint"  # checkpoint function name
)
```

### Function Registry (Alternative to module paths)

```python
from task_scheduler import register_handler

def my_handler(context):
    # context contains: {'step': ..., 'workflow_id': ..., 'variables': {...}}
    result = do_work()
    return result

# Register
register_handler('my_handler_name', my_handler)

# Use in task
task = TaskDefinition(
    task_id="using_registered",
    task_type="function",
    func="my_handler_name"  # refers to registered handler
)
```

---

## Monitoring

### Real-time Dashboard

```python
from task_scheduler import get_dashboard

dashboard = get_dashboard()
{
    'timestamp': '2024-01-15T10:30:00',
    'queue_sizes': {'ready': 5, 'delayed': 2, 'pending_dependencies': 1, 'total': 8},
    'active_tasks': [
        {'run_id': '...', 'task_name': 'Job 1', 'elapsed_seconds': 12.3}
    ],
    'recent_runs': [...],
    'statistics': {...},
    'resource_usage': {...},
    'alerts': [...]
}
```

### Performance Report

```python
from task_scheduler import get_performance_report

report = get_performance_report(hours=24)
{
    'period_hours': 24,
    'throughput_by_hour': [
        {'hour': '2024-01-14T09:00', 'total': 150, 'completed': 145, 'failed': 5, 'success_rate': 0.966}
    ],
    'task_type_distribution': [
        {'task_type': 'function', 'count': 800, 'completed': 780, 'success_rate': 0.975}
    ],
    'priority_distribution': [
        {'priority': 0, 'count': 100, 'success_rate': 0.99}
    ]
}
```

---

## Configuration

### Environment Variables

- `TASK_SCHEDULER_DB_PATH`: Override default database path
- `TASK_SCHEDULER_MAX_WORKERS`: Default max workers
- `TASK_SCHEDULER_EXECUTOR_TYPE`: `thread` or `process`

### Database Tuning

The storage automatically configures SQLite for concurrency:
- WAL mode for writer/reader concurrency
- 10-second checkpoint interval
- 10GB memory map size

Adjust in `task_storage.py` if needed.

---

## Best Practices

1. **Idempotent Tasks**: Design handlers to be safely retryable
2. **Timeouts**: Always set reasonable timeouts (avoid infinite hangs)
3. **Resource Limits**: Use memory/CPU limits to prevent resource exhaustion
4. **Checkpoints**: For long tasks, implement checkpointing for recovery
5. **Dependencies**: Minimize dependency depth for better parallelism
6. **Error Handling**: Catch exceptions in task functions, don't let them propagate
7. **Batch Similar Tasks**: Use batch_key for similar small tasks
8. **Monitor Alerts**: Set up alert handlers for production deployments

---

## Troubleshooting

### Tasks not executing
- Check queue size with `get_dashboard()['queue_sizes']`
- Verify workers are running: `get_statistics()['executor_active']`
- Check if dependencies are blocking tasks

### High memory usage
- Reduce `max_workers`
- Set memory limits per task
- Use process executor (isolated memory)

### Deadlocks in dependencies
- Cyclic dependencies raise `CyclicDependencyError`
- Use `get_dependencies()` to inspect DAG

### Slow performance
- Use priority FIFO strategy for fairness
- Reduce batch size if aggregation overhead dominates
- Consider process executor for CPU-bound tasks

---

## Testing

Run the comprehensive test suite:

```bash
cd ~/.hermes/skills/task-scheduler
python test_task_scheduler.py
```

Tests cover:
- Storage CRUD operations
- Queue ordering and delays
- Executor timeouts and resource limits
- DAG dependency resolution
- Cyclic dependency detection
- Resource quotas
- Batch aggregation
- Priority ordering
- Retry logic
- Monitoring
- Full integration

---

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   API/CLI       │────▶│  TaskScheduler  │────▶│    TaskQueue    │
│ (schedule_task, │     │  (DAG, Strategy)│     │  (Priority)     │
│  cancel_task)   │     └─────────────────┘     └─────────────────┘
└─────────────────┘              │                       │
                                  │                       │
                                  ▼                       ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   TaskStorage   │◀────┤  TaskExecutor   │◀────│   Worker Pool   │
│  (SQLite)       │     │ (Timeout, caps) │     │ (Thread/Process)│
└─────────────────┘     └─────────────────┘     └─────────────────┘
         │                                                │
         │                                                │
         └────────────────────────────────────────────────┘
                          │
                          ▼
               ┌─────────────────┐
               │  TaskMonitor    │
               │ (Metrics, Alerts)│
               └─────────────────┘
```

**Key Components**:
- **TaskStorage**: Persistent SQLite storage with ACID transactions
- **TaskQueue**: Multi-priority priority queue with delayed tasks
- **TaskExecutor**: Async executor with timeout and resource enforcement
- **TaskScheduler**: Orchestrates dependencies, batching, and dispatch
- **TaskMonitor**: Real-time metrics, alerts, performance reports

---

## Performance Characteristics

| Operation | Time Complexity |
|-----------|-----------------|
| Enqueue | O(log n) |
| Dequeue | O(log n) |
| Dependency check | O(d) where d = number of dependencies |
| Storage read/write | O(1) with SQLite index |
| Status query | O(1) (indexed by run_id) |

**Throughput**: With 10 workers, typical throughput 50-200 tasks/sec (varies by task duration)
**Overhead**: ~1-5ms per task (excluding execution time)
**Memory**: ~1KB per queued task, ~5KB per running task

---

## Production Deployment

1. **Database**: Consider PostgreSQL for higher scale (>10M tasks)
2. **Executor**: Use `PROCESS` executor for better isolation
3. **Monitoring**: Set up alert handlers for critical alerts
4. **Backups**: Regular SQLite backups or WAL archiving
5. **Log Rotation**: Configure log rotation in `task_logs`
6. **Resource Quotas**: Set conservative limits to prevent resource exhaustion

---

## License

MIT

---

## Contributing

This is a core Hermes skill. Modifications should maintain:
- Backward compatibility in database schema
- Thread-safe operations
- ACID transaction guarantees
- Comprehensive error handling

## 回滚方案
### 快速回滚
如果部署后发现问题：
1. 使用版本控制回退到上一个提交：`git revert HEAD`
2. 确认回滚后系统状态正常
3. 通知相关方变更已撤销

### 数据安全
- 所有修改前确认有备份
- 配置变更记录版本历史
