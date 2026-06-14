"""
Workflow Engine Skill for Hermes
Provides complete workflow orchestration capabilities.
"""

from workflow_builder import WorkflowBuilder, load_workflow, workflow_from_template
from workflow_definitions import (
    ExecutionContext,
    RetryPolicy,
    StepIO,
    StepStatus,
    StepType,
    TimeoutPolicy,
    VariableScope,
    Workflow,
    WorkflowStatus,
    WorkflowStep,
    evaluate_condition,
)
from workflow_engine import WorkflowEngine, WorkflowExecution
from workflow_monitor import LogAggregator, WorkflowMonitor
from workflow_storage import WorkflowStorage

__all__ = [
    "ExecutionContext",
    "LogAggregator",
    "RetryPolicy",
    "StepIO",
    "StepStatus",
    "StepType",
    "TimeoutPolicy",
    "VariableScope",
    "Workflow",
    "WorkflowBuilder",
    "WorkflowEngine",
    "WorkflowExecution",
    "WorkflowMonitor",
    "WorkflowStatus",
    "WorkflowStep",
    "WorkflowStorage",
    "evaluate_condition",
    "load_workflow",
    "workflow_from_template"
]

# CLI command functions (to be used with Hermes slash commands or standalone)
def workflow_run(workflow_id: str, variables: dict = None, goal: str = None,
                wait: bool = True, **kwargs) -> str:
    """
    Run a workflow.

    Args:
        workflow_id: ID of the workflow to run
        variables: Optional input variables
        goal: Optional goal/description for this run
        wait: If True, block until completion (default: True)

    Returns:
        run_id of the executed workflow
    """
    from workflow_engine import WorkflowEngine
    from workflow_storage import WorkflowStorage

    storage = WorkflowStorage()
    engine = WorkflowEngine(storage)

    if wait:
        return engine.start_workflow(workflow_id, variables=variables, goal=goal, **kwargs)
    return engine.start_workflow_async(workflow_id, variables=variables, goal=goal, **kwargs)


def workflow_list(active_only: bool = True, tags: list = None, workflow_id: str = None) -> list:
    """
    List workflows.

    Args:
        active_only: Only show active workflows (default: True)
        tags: Filter by tags
        workflow_id: Specific workflow ID to list

    Returns:
        List of workflow metadata
    """
    from workflow_storage import WorkflowStorage

    storage = WorkflowStorage()
    if workflow_id:
        wf = storage.load_workflow(workflow_id)
        if wf:
            return [wf.to_dict()]
        return []
    return storage.list_workflows(active_only=active_only, tags=tags)


def workflow_status(run_id: str = None, workflow_id: str = None, limit: int = 20) -> dict:
    """
    Get status of workflow runs.

    Args:
        run_id: Specific run ID to check
        workflow_id: List runs for a workflow
        limit: Max number of runs to return

    Returns:
        Status information
    """
    from workflow_definitions import WorkflowStatus
    from workflow_storage import WorkflowStorage

    storage = WorkflowStorage()

    if run_id:
        run = storage.get_run(run_id)
        if run:
            steps = storage.get_step_executions(run_id)
            run["steps"] = steps
            return run
        return {}
    if workflow_id:
        runs = storage.list_runs(workflow_id=workflow_id, limit=limit)
        return {"workflow_id": workflow_id, "runs": runs}
    runs = storage.list_runs(limit=limit)
    return {"runs": runs}


def workflow_stop(run_id: str, reason: str = "Manual stop") -> bool:
    """
    Stop a running workflow.

    Args:
        run_id: Run ID to stop
        reason: Reason for stopping

    Returns:
        True if stop was requested
    """
    from workflow_definitions import WorkflowStatus
    from workflow_engine import WorkflowEngine
    from workflow_storage import WorkflowStorage

    storage = WorkflowStorage()
    engine = WorkflowEngine(storage)

    return engine.stop_run(run_id, reason)


def workflow_monitor(refresh: bool = True, limit: int = 50) -> dict:
    """
    Get monitoring dashboard data.

    Args:
        refresh: Force refresh metrics
        limit: Limit for recent runs

    Returns:
        Dashboard data including metrics, active runs, etc.
    """
    from workflow_engine import WorkflowEngine
    from workflow_monitor import WorkflowMonitor
    from workflow_storage import WorkflowStorage

    storage = WorkflowStorage()
    engine = WorkflowEngine(storage)
    monitor = WorkflowMonitor(storage, engine)

    if refresh:
        monitor._refresh_metrics()

    return monitor.get_dashboard_data()


def workflow_register_handler(action: str, handler_path: str = None, handler_code: str = None):
    """
    Register a custom handler for workflow steps.

    Args:
        action: Action name to handle (e.g., 'send_email', 'api_call')
        handler_path: Python module path (e.g., 'mymodule.myhandler')
        handler_code: Inline Python code defining the handler function
    """
    from workflow_engine import WorkflowEngine
    from workflow_storage import WorkflowStorage

    storage = WorkflowStorage()
    engine = WorkflowEngine(storage)

    if handler_path:
        import importlib
        mod_name, func_name = handler_path.rsplit(".", 1)
        mod = importlib.import_module(mod_name)
        handler = getattr(mod, func_name)
    elif handler_code:
        # Execute code to define handler
        namespace = {}
        exec(handler_code, namespace)
        handler = namespace.get("handler")
        if not handler:
            raise ValueError("Handler code must define 'handler' function")
    else:
        raise ValueError("Must provide handler_path or handler_code")

    engine.register_handler(action, handler)
    return f"Registered handler for '{action}'"


# Quick utility to create and save a workflow
def workflow_create(definition: dict or str, workflow_id: str = None) -> str:
    """
    Create and save a workflow from definition.

    Args:
        definition: Dict or YAML/JSON string
        workflow_id: Optional ID override

    Returns:
        Workflow ID of created workflow
    """
    from workflow_builder import WorkflowBuilder
    from workflow_storage import WorkflowStorage

    storage = WorkflowStorage()

    if isinstance(definition, str):
        # Try to parse as YAML or JSON
        import json

        import yaml
        try:
            definition = yaml.safe_load(definition)
        except:
            try:
                definition = json.loads(definition)
            except:
                raise ValueError("Failed to parse definition as YAML or JSON")

    if "id" not in definition and workflow_id:
        definition["id"] = workflow_id

    workflow = WorkflowBuilder.from_dict(definition)
    storage.save_workflow(workflow)

    return workflow.id
