"""
Workflow Definition Classes
Defines the core data structures for representing workflows, steps, and their relationships.
"""
import json
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class StepType(Enum):
    """Types of workflow steps"""
    TASK = "task"           # Simple task execution
    CONDITION = "condition" # Conditional branching
    PARALLEL = "parallel"   # Parallel execution of branches
    LOOP = "loop"           # Loop/iteration
    SUBWORKFLOW = "subworkflow"  # Invoke another workflow
    WAIT = "wait"           # Wait for external event
    SCRIPT = "script"       # Execute inline script/code
    TRANSFORM = "transform" # Data transformation


class StepStatus(Enum):
    """Execution status of a step"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


class WorkflowStatus(Enum):
    """Overall workflow status"""
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class VariableScope:
    """Variable scoping rules"""
    name: str
    default_value: Any = None
    description: str = ""
    required: bool = False
    persist: bool = True  # Persist across workflow runs?


@dataclass
class StepIO:
    """Input/Output specification for a step"""
    inputs: dict[str, Any] = field(default_factory=dict)   # Input mappings
    outputs: dict[str, str] = field(default_factory=dict) # Output variable names
    result_path: str | None = None  # JSONPath to extract result


@dataclass
class RetryPolicy:
    """Retry configuration for a step"""
    max_attempts: int = 1
    initial_delay_ms: int = 1000
    max_delay_ms: int = 30000
    backoff_factor: float = 2.0
    retry_on_exceptions: list[str] = field(default_factory=list)  # Exception types to retry


@dataclass
class TimeoutPolicy:
    """Timeout configuration"""
    timeout_ms: int = 300000  # 5 minutes default
    timeout_strategy: str = "fail"  # "fail" or "continue"


@dataclass
class WorkflowStep:
    """
    Represents a single step in a workflow.
    Steps can be chained, branched, parallelized, or nested.
    """
    id: str
    type: StepType
    name: str
    description: str = ""

    # Execution configuration
    action: str = ""  # What to execute (task name, command, script, etc.)
    handler: str | None = None  # Handler function/module name
    parameters: dict[str, Any] = field(default_factory=dict)

    # Input/Output
    io: StepIO = field(default_factory=StepIO)

    # Flow control
    next_steps: list[str] = field(default_factory=list)  # Sequential continuation
    condition: str | None = None  # Expression for conditional branching
    branches: dict[str, str] = field(default_factory=dict)  # condition_value -> step_id

    # Parallel execution
    parallel: bool = False
    join_policy: str = "all"  # "all", "any", "n"
    join_n: int = 1

    # Loop configuration
    loop_condition: str | None = None
    loop_variable: str | None = None
    max_iterations: int | None = None

    # Sub-workflow
    subworkflow_id: str | None = None
    subworkflow_inputs: dict[str, Any] = field(default_factory=dict)

    # Wait configuration
    wait_for: str | None = None  # Event name
    wait_timeout_ms: int | None = None

    # Script/code
    script: str | None = None
    script_language: str = "python"

    # Error handling
    on_error: str = "fail"  # "fail", "continue", "retry", "compensate"
    error_handler: str | None = None  # Step ID to jump to on error
    retry_policy: RetryPolicy = field(default_factory=RetryPolicy)

    # Timeout
    timeout_policy: TimeoutPolicy = field(default_factory=TimeoutPolicy)

    # Compensation/rollback
    compensate_steps: list[str] = field(default_factory=list)

    # Metadata
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary representation"""
        result = asdict(self)
        result["type"] = self.type.value
        result["io"] = asdict(self.io) if self.io else {}
        result["retry_policy"] = asdict(self.retry_policy)
        result["timeout_policy"] = asdict(self.timeout_policy)
        return result

    @classmethod
    def from_dict(cls, data: dict) -> "WorkflowStep":
        """Create from dictionary representation"""
        # Handle enums
        if "type" in data:
            data["type"] = StepType(data["type"])
        if "io" in data and isinstance(data["io"], dict):
            data["io"] = StepIO(**data["io"])
        if "retry_policy" in data and isinstance(data["retry_policy"], dict):
            data["retry_policy"] = RetryPolicy(**data["retry_policy"])
        if "timeout_policy" in data and isinstance(data["timeout_policy"], dict):
            data["timeout_policy"] = TimeoutPolicy(**data["timeout_policy"])
        return cls(**data)


@dataclass
class Workflow:
    """
    Complete workflow definition.
    Contains steps, metadata, and configuration.
    """
    id: str
    name: str
    version: str = "1.0.0"
    description: str = ""

    # Steps indexed by ID
    steps: dict[str, WorkflowStep] = field(default_factory=dict)

    # Entry points
    start_step_id: str = ""
    end_step_id: str | None = None

    # Variables
    variables: list[VariableScope] = field(default_factory=list)

    # Configuration
    configuration: dict[str, Any] = field(default_factory=dict)

    # Metadata
    tags: list[str] = field(default_factory=list)
    created_by: str = ""
    created_at: str | None = None
    updated_at: str | None = None

    def validate(self) -> list[str]:
        """Validate workflow structure. Returns list of errors."""
        errors = []

        if not self.id:
            errors.append("Workflow ID is required")
        if not self.name:
            errors.append("Workflow name is required")
        if not self.start_step_id:
            errors.append("Start step ID is required")
        if self.start_step_id not in self.steps:
            errors.append(f"Start step '{self.start_step_id}' not found in steps")

        # Check all step references exist
        for step in self.steps.values():
            for next_id in step.next_steps:
                if next_id not in self.steps:
                    errors.append(f"Step '{step.id}' references non-existent next step '{next_id}'")
            if step.error_handler and step.error_handler not in self.steps:
                errors.append(f"Step '{step.id}' has error_handler '{step.error_handler}' not found")
            for comp_id in step.compensate_steps:
                if comp_id not in self.steps:
                    errors.append(f"Step '{step.id}' has compensate step '{comp_id}' not found")

            # Check branch targets exist
            for branch_target in step.branches.values():
                if branch_target not in self.steps:
                    errors.append(f"Step '{step.id}' branches to non-existent step '{branch_target}'")

        # Check for circular dependencies
        visited = set()
        path = []

        def check_circular(step_id: str) -> bool:
            if step_id in path:
                return True
            if step_id in visited:
                return False
            path.append(step_id)
            visited.add(step_id)
            step = self.steps.get(step_id)
            if step:
                for next_id in step.next_steps:
                    if check_circular(next_id):
                        return True
                # Also check branches
                for branch_target in step.branches.values():
                    if check_circular(branch_target):
                        return True
            path.pop()
            return False

        if self.start_step_id:
            if check_circular(self.start_step_id):
                errors.append("Workflow contains circular dependency")

        return errors

    def get_step_order(self) -> list[str]:
        """Get topological order of steps (simple linearization)"""
        order = []
        visited = set()

        def visit(step_id: str):
            if step_id in visited or step_id not in self.steps:
                return
            visited.add(step_id)
            step = self.steps[step_id]
            for next_id in step.next_steps:
                visit(next_id)
            order.append(step_id)

        visit(self.start_step_id)

        # Add any orphan steps
        for step_id in self.steps:
            if step_id not in visited:
                order.append(step_id)

        return order

    def to_dict(self) -> dict:
        """Convert to dictionary representation"""
        return {
            "id": self.id,
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "start_step_id": self.start_step_id,
            "end_step_id": self.end_step_id,
            "steps": {sid: step.to_dict() for sid, step in self.steps.items()},
            "variables": [asdict(v) for v in self.variables],
            "configuration": self.configuration,
            "tags": self.tags,
            "created_by": self.created_by,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Workflow":
        """Create from dictionary representation"""
        # Parse steps
        steps_data = data.get("steps", {})
        steps = {}
        for sid, step_data in steps_data.items():
            steps[sid] = WorkflowStep.from_dict(step_data)

        # Parse variables
        variables = []
        for v_data in data.get("variables", []):
            variables.append(VariableScope(**v_data))

        return cls(
            id=data["id"],
            name=data["name"],
            version=data.get("version", "1.0.0"),
            description=data.get("description", ""),
            steps=steps,
            start_step_id=data.get("start_step_id", ""),
            end_step_id=data.get("end_step_id"),
            variables=variables,
            configuration=data.get("configuration", {}),
            tags=data.get("tags", []),
            created_by=data.get("created_by", ""),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at")
        )


@dataclass
class ExecutionContext:
    """
    Runtime execution context for a workflow instance.
    Holds state, variables, and history during execution.
    """
    workflow_id: str
    run_id: str
    status: WorkflowStatus = WorkflowStatus.RUNNING

    # Variable store (workflow variables + step outputs)
    variables: dict[str, Any] = field(default_factory=dict)

    # Step execution history
    step_history: list[dict[str, Any]] = field(default_factory=list)

    # Current execution state
    current_step_id: str | None = None
    call_stack: list[str] = field(default_factory=list)  # For subworkflows

    # Error tracking
    errors: list[dict[str, Any]] = field(default_factory=list)

    # Timing
    started_at: float = 0
    updated_at: float = 0
    completed_at: float | None = None

    # Metadata
    metadata: dict[str, Any] = field(default_factory=dict)

    def set_variable(self, name: str, value: Any):
        """Set a workflow variable"""
        self.variables[name] = value
        self.updated_at = time.time()

    def get_variable(self, name: str, default: Any = None) -> Any:
        """Get a workflow variable"""
        return self.variables.get(name, default)

    def add_error(self, step_id: str, error: Exception, fatal: bool = False):
        """Record an error"""
        self.errors.append({
            "step_id": step_id,
            "error": str(error),
            "error_type": type(error).__name__,
            "fatal": fatal,
            "timestamp": time.time()
        })

    def record_step_execution(self, step_id: str, status: StepStatus,
                            output: Any = None, error: Exception = None,
                            duration_ms: float = 0):
        """Record step execution in history"""
        record = {
            "step_id": step_id,
            "status": status.value,
            "output": output,
            "error": str(error) if error else None,
            "duration_ms": duration_ms,
            "timestamp": time.time()
        }
        self.step_history.append(record)
        self.current_step_id = step_id if status == StepStatus.RUNNING else None

    def to_dict(self) -> dict:
        """Convert to dictionary for storage"""
        return {
            "workflow_id": self.workflow_id,
            "run_id": self.run_id,
            "status": self.status.value,
            "variables": self.variables,
            "step_history": self.step_history,
            "current_step_id": self.current_step_id,
            "call_stack": self.call_stack,
            "errors": self.errors,
            "started_at": self.started_at,
            "updated_at": self.updated_at,
            "completed_at": self.completed_at,
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ExecutionContext":
        """Recreate from dictionary"""
        # Convert status enum
        status = WorkflowStatus(data.get("status", "running"))

        ctx = cls(
            workflow_id=data["workflow_id"],
            run_id=data["run_id"],
            status=status,
            variables=data.get("variables", {}),
            step_history=data.get("step_history", []),
            current_step_id=data.get("current_step_id"),
            call_stack=data.get("call_stack", []),
            errors=data.get("errors", []),
            started_at=data.get("started_at", 0),
            updated_at=data.get("updated_at", 0),
            completed_at=data.get("completed_at"),
            metadata=data.get("metadata", {})
        )
        return ctx


# Condition evaluation helper
def evaluate_condition(condition: str, context: dict) -> bool:
    """
    Safely evaluate a condition expression.
    Uses a restricted environment for security.
    """
    import ast
    import operator

    # Supported operators
    operators = {
        ast.Eq: operator.eq,
        ast.NotEq: operator.ne,
        ast.Lt: operator.lt,
        ast.LtE: operator.le,
        ast.Gt: operator.gt,
        ast.GtE: operator.ge,
        ast.And: operator.and_,
        ast.Or: operator.or_,
        ast.Not: operator.not_,
    }

    def _eval(node):
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.Name):
            return context.get(node.id)
        if isinstance(node, ast.Dict):
            return {_eval(k): _eval(v) for k, v in zip(node.keys, node.values)}
        if isinstance(node, ast.List):
            return [_eval(elt) for elt in node.elts]
        if isinstance(node, ast.Compare):
            left = _eval(node.left)
            for op, comparator in zip(node.ops, node.comparators):
                right = _eval(comparator)
                op_func = operators.get(type(op))
                if not op_func:
                    raise ValueError(f"Unsupported operator: {type(op)}")
                if not op_func(left, right):
                    return False
                left = right
            return True
        if isinstance(node, ast.BoolOp):
            if isinstance(node.op, ast.And):
                return all(_eval(v) for v in node.values)
            if isinstance(node.op, ast.Or):
                return any(_eval(v) for v in node.values)
            raise ValueError(f"Unsupported boolop: {type(node.op)}")
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            return not _eval(node.operand)
        raise ValueError(f"Unsupported AST node: {type(node)}")

    try:
        tree = ast.parse(condition, mode="eval")
        return _eval(tree.body)
    except Exception as e:
        raise ValueError(f"Condition evaluation failed: {condition} - {e}")


if __name__ == "__main__":
    # Test example
    workflow = Workflow(
        id="test_workflow",
        name="Test Workflow",
        start_step_id="step1",
        steps={
            "step1": WorkflowStep(
                id="step1",
                type=StepType.TASK,
                name="First Step",
                action="collect_data",
                next_steps=["step2"]
            ),
            "step2": WorkflowStep(
                id="step2",
                type=StepType.CONDITION,
                name="Check Data",
                condition="data_collected == True",
                branches={"true": "step3", "false": "step4"}
            ),
            "step3": WorkflowStep(
                id="step3",
                type=StepType.TASK,
                name="Process Data",
                action="process_data",
                next_steps=["step5"]
            ),
            "step4": WorkflowStep(
                id="step4",
                type=StepType.TASK,
                name="Handle Missing",
                action="handle_missing"
            ),
            "step5": WorkflowStep(
                id="step5",
                type=StepType.PARALLEL,
                name="Parallel Tasks",
                parallel=True,
                branches={"branch1": "step6a", "branch2": "step6b"},
                next_steps=["step7"]
            )
        }
    )

    errors = workflow.validate()
    if errors:
        print("Validation errors:", errors)
    else:
        print("Workflow is valid!")
        print(json.dumps(workflow.to_dict(), indent=2))
