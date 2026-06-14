---
name: workflow-engine
description: Complete workflow orchestration system - define, run, monitor, and manage complex multi-step workflows with persistence, error handling, and recovery.
version: 1.0.0
author: Hermes Research
license: MIT
metadata:
  hermes:
    tags: [workflow, automation, orchestration, etl, pipeline, retry, compensation]
    related_skills: []
---

# Workflow Engine Skill

A robust workflow orchestration system for Hermes that enables complex multi-step task execution with full state persistence, error handling, retries, timeouts, parallel execution, and compensation/rollback mechanisms.

## Features

## 触发条件
- 用户提及此功能相关关键词时
- 遇到此领域的标准问题时
- 需要执行该领域的标准操作时


- **Workflow Definition**: YAML/JSON definitions with rich step types
- **State Persistence**: SQLite-backed storage for workflow definitions and execution history
- **Execution Engine**: Full runtime with state management and error recovery
- **Step Types**: Sequential, conditional, parallel, loop, sub-workflow, script, transform, wait
- **Error Handling**: Retry with exponential backoff, timeouts, compensation/rollback
- **Variable Scoping**: Input/output passing between steps
- **Monitoring**: Real-time dashboard, metrics, event streaming
- **CLI Interface**: Command-line tool for management

## Installation

The workflow engine is part of Hermes skills. No installation needed beyond having the skill files in `~/.hermes/skills/workflow-engine/`.

Dependencies:
- Python 3.8+
- pyyaml (for YAML parsing)

Install dependencies:
```bash
pip install pyyaml
```

## Quick Start

### 1. Create a Workflow Definition

Create a YAML file (e.g., `my_workflow.yaml`):

```yaml
id: my_workflow
name: "My First Workflow"
description: "A simple example"
start_step_id: step1

variables:
  - name: input_data
    default: "test"

steps:
  step1:
    type: task
    name: "First Step"
    action: "process_data"
    next_steps: [step2]

  step2:
    type: task
    name: "Second Step"
    action: "send_result"
```

### 2. Create the Workflow

```bash
workflow-cli create my_workflow.yaml
```

Or use Python:
```python
from workflow_engine import workflow_create

workflow_id = workflow_create(definition_file='my_workflow.yaml')
```

### 3. Register Handlers

Define handler functions for your actions:

```python
from workflow_engine import workflow_register_handler

async def process_data_handler(context):
    data = context['variables'].get('input_data')
    # Do processing...
    result = {'processed': data.upper()}
    return result

workflow_register_handler('process_data', handler=process_data_handler)
```

Or use the shell to test:
```python
# Define inline
handler_code = """
async def handler(context):
    return {'status': 'success', 'message': 'Hello from workflow!'}
"""
workflow_register_handler('greet', handler_code=handler_code)
```

### 4. Run the Workflow

```bash
# Synchronous (wait for completion)
workflow-cli run my_workflow --var input_data="Hello World" --wait

# Asynchronous
workflow-cli run my_workflow --wait=false
```

Or in Python:
```python
from workflow_engine import workflow_run

run_id = workflow_run('my_workflow', variables={'input_data': 'Hello World'}, wait=True)
print(f"Run ID: {run_id}")
```

## CLI Commands

The workflow engine provides CLI commands via `workflow-cli`:

| Command | Description |
|---------|-------------|
| `workflow-cli run <id> [--var KEY=VAL] [--wait]` | Run a workflow |
| `workflow-cli list [--active] [--tag TAG]` | List workflows |
| `workflow-cli status [--run RUN_ID] [--workflow WF_ID]` | Show run status |
| `workflow-cli stop RUN_ID [--reason REASON]` | Stop a running workflow |
| `workflow-cli monitor [--refresh] [--detailed]` | Show monitoring dashboard |
| `workflow-cli create DEFINITION_FILE` | Create workflow from file |

## Workflow Definition Reference

### Root Fields

| Field | Required | Description |
|-------|----------|-------------|
| `id` | Yes | Unique workflow identifier |
| `name` | Yes | Human-readable name |
| `description` | No | Description |
| `version` | No | Version string (default: "1.0.0") |
| `start_step_id` | Yes | ID of the first step |
| `end_step_id` | No | Optional end marker (not used currently) |
| `tags` | No | List of tags |
| `variables` | No | Variable definitions |

### Variables

```yaml
variables:
  - name: var_name           # Variable name
    default: "value"         # Default value
    required: false          # Required flag
    description: "..."       # Description
```

### Steps

Each step has a unique ID and the following common fields:

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique step identifier |
| `type` | string | Step type: `task`, `condition`, `parallel`, `loop`, `subworkflow`, `wait`, `script`, `transform` |
| `name` | string | Human-readable name |
| `description` | string | Description |
| `action` | string | Action/handler name to execute (for task types) |
| `handler` | string | Custom handler module path |
| `parameters` | dict | Parameters passed to the action |
| `io` | dict | Input/output configuration |
| `next_steps` | list[str] | Sequential next steps |
| `condition` | string | Expression for condition steps (Python-like) |
| `branches` | dict[str, str] | Branches for condition/parallel (key -> step_id) |
| `parallel` | bool | Execute in parallel (for parallel steps) |
| `join_policy` | string | Parallel join: `all`, `any`, `n` |
| `loop_condition` | string | Condition to continue looping |
| `loop_variable` | string | Variable to track iteration |
| `max_iterations` | int | Maximum loop iterations |
| `subworkflow_id` | string | Workflow to invoke |
| `subworkflow_inputs` | dict | Inputs for subworkflow |
| `wait_for` | string | Event name to wait for |
| `script` | string | Inline script code |
| `script_language` | string | Script language (default: python) |
| `on_error` | string | Error policy: `fail`, `continue`, `retry`, `compensate` |
| `error_handler` | string | Step ID to jump to on error |
| `retry_policy` | dict | Retry configuration |
| `timeout_policy` | dict | Timeout configuration |
| `compensate_steps` | list[str] | Steps to execute for compensation |

### Input/Output Configuration

Steps can define I/O mappings to pass data:

```yaml
io:
  inputs:
    source_data: "$upstream_variable"   # Map variable to input param
  outputs:
    result_var: "$step_output_field"    # Map output field to variable
  result_path: "$.data.items"           # JSONPath to extract result (future)
```

### Retry Policy

```yaml
retry_policy:
  max_attempts: 3
  initial_delay_ms: 1000
  max_delay_ms: 30000
  backoff_factor: 2.0
  retry_on_exceptions: ["NetworkError", "TimeoutError"]
```

### Timeout Policy

```yaml
timeout_policy:
  timeout_ms: 300000    # 5 minutes
  timeout_strategy: "fail"   # or "retry"
```

### Conditions

Condition expressions use Python-like syntax and are evaluated against the context variables:

```yaml
condition: "data_received == True and len(items) > 0"
```

Supported: comparison operators (`==`, `!=`, `<`, `<=`, `>`, `>=`), boolean (`and`, `or`, `not`), variable references.

## Step Types in Detail

### Task Step

The basic execution unit. Requires an `action` (handler name) or `handler` (module function).

```yaml
step_name:
  type: task
  action: "my_action"
  parameters:
    key: "value"
```

**Handler Functions**: Must be async or sync callables accepting a context dict:

```python
async def my_handler(context):
    # context contains:
    #   - 'step': step definition dict
    #   - 'workflow_id', 'run_id'
    #   - 'variables': dict of current variables
    #   - 'parameters': step parameters
    result = do_work()
    return result  # Will be stored in '_my_handler_result' variable
```

Register:
```python
engine.register_handler('my_action', my_handler)
```

### Condition Step

Evaluates a boolean expression and branches accordingly.

```yaml
check_items:
  type: condition
  condition: "item_count > 0"
  branches:
    true: process_items
    false: handle_empty
```

### Parallel Step

Executes multiple branches concurrently.

```yaml
parallel_process:
  type: parallel
  parallel: true
  join_policy: all      # Continue when all branches complete
  branches:
    branch_a: process_a
    branch_b: process_b
    branch_c: process_c
  next_steps: [aggregate]
```

### Loop Step

Repeats execution while a condition holds.

```yaml
retry_loop:
  type: loop
  loop_condition: "attempt < 5"
  loop_variable: "attempt"
  max_iterations: 10
  next_steps: [final_step]
```

### Subworkflow Step

Invokes another workflow.

```yaml
process_sub:
  type: subworkflow
  subworkflow_id: "child_workflow"
  subworkflow_inputs:
    input_data: "$parent_data"
  io:
    outputs:
      child_result: "$result"
  next_steps: [continue_parent]
```

### Script Step

Executes inline Python code.

```yaml
custom_transform:
  type: script
  script: |
    data = variables['input']
    result = [x * 2 for x in data]
    variables['output'] = result
    result = output  # Final result
  script_language: python
```

### Transform Step

Applies a transformation function to input data.

```yaml
transform:
  type: transform
  action: "lambda x: x * 2"   # Expression or callable
```

### Wait Step

Pauses execution, optionally waiting for an event.

```yaml
wait_for_event:
  type: wait
  wait_for: "external_signal"
  wait_timeout_ms: 300000
```

## Error Handling

Steps can define how errors are handled via `on_error`:

- `fail`: Stop the workflow (default)
- `continue`: Continue to next step (if any)
- `retry`: Retry according to retry_policy
- `compensate`: Execute compensation steps, then fail

**Compensation**: Define steps to undo partial work:

```yaml
critical_step:
  type: task
  action: "create_order"
  on_error: "compensate"
  compensate_steps:
    - cancel_order
    - refund_payment
    - notify_admin
```

## Monitoring

Use the `workflow_monitor` to track executions:

```python
from workflow_engine import WorkflowMonitor, WorkflowStorage, WorkflowEngine

storage = WorkflowStorage()
engine = WorkflowEngine(storage)
monitor = WorkflowMonitor(storage, engine)

dashboard = monitor.get_dashboard_data()
print(f"Active runs: {len(dashboard['active_runs'])}")

# Get run summary
summary = monitor.get_run_summary(run_id)
print(json.dumps(summary, indent=2))

# Generate HTML report
report_path = monitor.generate_html_report(run_id)
```

## Examples

See the `examples/` directory for complete workflow definitions:

- `data_pipeline.yaml`: ETL pipeline with validation and error handling
- `task_scheduler.yaml`: Parallel batch processing with retries
- `error_handling_demo.yaml`: Transactional workflow with compensation

Load and run them:

```bash
workflow-cli create examples/data_pipeline.yaml
workflow-cli run data_pipeline_v1 --var input_source="data.csv" --wait
```

## API Reference (Python)

### Core Classes

- `Workflow`: Workflow definition container
- `WorkflowStep`: Individual step definition
- `ExecutionContext`: Runtime state container
- `WorkflowEngine`: Main execution engine
- `WorkflowStorage`: Database persistence layer
- `WorkflowBuilder`: DSL/JSON/YAML parser
- `WorkflowMonitor`: Monitoring and metrics

### Key Functions

```python
# Workflow management
workflow_create(definition, workflow_id=None) -> str
workflow_list(active_only=True, tags=None) -> List[Dict]
workflow_status(run_id=None, workflow_id=None, limit=20) -> Dict
workflow_stop(run_id, reason="Manual stop") -> bool
workflow_run(workflow_id, variables=None, wait=True) -> str
workflow_monitor(refresh=True, limit=50) -> Dict
workflow_register_handler(action, handler=None, handler_path=None, handler_code=None)
```

## Data Persistence

All workflow definitions, runs, and step executions are stored in SQLite:

```
~/.hermes/workflows/registry.sqlite
```

Tables:
- `workflows`: Workflow definitions
- `flow_runs`: Workflow run instances
- `flow_steps`: Individual step executions
- `workflow_templates`: Reusable templates
- `workflow_events`: Audit and event log

## Best Practices

1. **Idempotent Handlers**: Design handlers to be safely retryable
2. **Checkpointing**: Use step outputs to persist intermediate results
3. **Error Handling**: Always define `on_error` for critical steps
4. **Timeouts**: Set reasonable timeouts to avoid hanging
5. **Compensation**: For transactional workflows, define proper rollback steps
6. **Variables**: Use descriptive variable names and document them
7. **Testing**: Test workflows with simulated failures

## Troubleshooting

### Workflow fails immediately
Check that handlers are registered before running. Use `engine.register_handler()`.

### Steps not executing sequentially
Ensure `next_steps` are correctly defined. The default is no next step.

### Variables not accessible
Variable scope is flat (workflow-level). Use `context.set_variable()` in handlers to set outputs.

### Retries not working
Verify `retry_policy` is defined and `on_error: retry` is set.

### Performance issues
- Use `max_concurrent` for parallel steps
- Set timeouts to prevent hangs
- Consider splitting large workflows

## Advanced Usage

### Custom Handlers

Create a Python module with handler functions:

```python
# my_handlers.py
import asyncio

async def email_sender(context):
    recipient = context['parameters']['to']
    subject = context['parameters']['subject']
    # Send email...
    return {'sent': True, 'recipient': recipient}

async def api_caller(context):
    url = context['parameters']['url']
    # Make API call...
    return {'status': 200, 'data': ...}
```

Register:
```python
from workflow_engine import workflow_register_handler
workflow_register_handler('email_sender', handler_path='my_handlers.email_sender')
```

### Subworkflows

Create modular workflows that can be composed:

```yaml
parent:
  steps:
    - type: subworkflow
      subworkflow_id: "child_wf"
      subworkflow_inputs:
        input: "$parent_data"
      io:
        outputs:
          child_output: "processed_by_child"
```

### Templates

Store reusable workflow templates in the database:

```python
from workflow_engine import WorkflowStorage
storage = WorkflowStorage()
storage.save_template(
    template_id="etl_template",
    name="ETL Pipeline Template",
    definition={...},
    category="data"
)
# Instances can be created from templates with overrides
```

## Logs and Debugging

Workflow logs are stored in:
```
~/.hermes/logs/workflows/
```

View recent logs:
```bash
tail -f ~/.hermes/logs/workflows/recent.jsonl
```

Search logs:
```python
from workflow_monitor import LogAggregator
logs = LogAggregator().search_logs("error", run_id="abc123")
```

## Performance Tuning

- **Database**: SQLite works for moderate loads. For high volume, consider PostgreSQL.
- **Parallelism**: Tune `max_workers` in WorkflowEngine constructor.
- **Storage**: Periodically archive old runs to keep DB small.

## License

MIT

## 回滚方案
### 快速回滚
如果部署后发现问题：
1. 使用版本控制回退到上一个提交：`git revert HEAD`
2. 确认回滚后系统状态正常
3. 通知相关方变更已撤销

### 数据安全
- 所有修改前确认有备份
- 配置变更记录版本历史
