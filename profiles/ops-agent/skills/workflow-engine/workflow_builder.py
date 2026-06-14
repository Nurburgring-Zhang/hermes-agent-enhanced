"""
Workflow Builder Module
Parses YAML/JSON workflow definitions and converts them to Workflow objects.
Supports both declarative definitions and programmatic building.
"""
import json
from pathlib import Path
from typing import Any

import yaml
from workflow_definitions import (
    RetryPolicy,
    StepIO,
    StepType,
    TimeoutPolicy,
    VariableScope,
    Workflow,
    WorkflowStep,
)


class WorkflowBuilder:
    """
    Builds Workflow objects from various sources:
    - YAML files
    - JSON files/dicts
    - Programmatic API
    """

    def __init__(self):
        self._workflow: Workflow | None = None
        self._steps: dict[str, WorkflowStep] = {}

    # ==================== YAML/JSON Loading ====================

    @classmethod
    def from_yaml(cls, filepath: str | Path) -> Workflow:
        """Load workflow from YAML file"""
        filepath = Path(filepath)
        with open(filepath, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return cls.from_dict(data, source_file=str(filepath))

    @classmethod
    def from_json(cls, filepath: str | Path) -> Workflow:
        """Load workflow from JSON file"""
        filepath = Path(filepath)
        with open(filepath, encoding="utf-8") as f:
            data = json.load(f)
        return cls.from_dict(data, source_file=str(filepath))

    @classmethod
    def from_dict(cls, data: dict, source_file: str = None) -> Workflow:
        """Create workflow from dictionary"""
        builder = cls()

        # Parse workflow metadata
        workflow_id = data.get("id") or data.get("workflow_id")
        name = data.get("name")
        version = data.get("version", "1.0.0")
        description = data.get("description", "")
        start_step_id = data.get("start_step_id") or data.get("startStep")
        end_step_id = data.get("end_step_id") or data.get("endStep")
        tags = data.get("tags", [])
        created_by = data.get("created_by", "")
        created_at = data.get("created_at")
        updated_at = data.get("updated_at")

        if not workflow_id:
            raise ValueError("Workflow definition must include 'id'")
        if not name:
            raise ValueError("Workflow definition must include 'name'")
        if not start_step_id:
            raise ValueError("Workflow definition must include 'start_step_id'")

        # Parse variables
        variables = []
        for v_data in data.get("variables", []):
            if isinstance(v_data, dict):
                variables.append(VariableScope(**v_data))
            elif isinstance(v_data, str):
                variables.append(VariableScope(name=v_data))
        # Also check 'params' for backward compatibility
        for p_data in data.get("params", []):
            if isinstance(p_data, dict):
                variables.append(VariableScope(
                    name=p_data.get("name"),
                    description=p_data.get("description", ""),
                    required=p_data.get("required", False),
                    default_value=p_data.get("default")
                ))

        # Parse steps
        steps: dict[str, WorkflowStep] = {}
        steps_data = data.get("steps", {})

        # Handle both dict (by id) and list formats
        if isinstance(steps_data, list):
            # Convert list to dict using id field
            for step_data in steps_data:
                step_id = step_data.get("id") or step_data.get("step_id")
                if not step_id:
                    raise ValueError(f"Step missing 'id': {step_data}")
                steps[step_id] = builder._parse_step(step_id, step_data)
        elif isinstance(steps_data, dict):
            for step_id, step_data in steps_data.items():
                steps[step_id] = builder._parse_step(step_id, step_data)
        else:
            raise ValueError("'steps' must be a list or dict")

        # Handle legacy format (linear pipeline)
        if "pipeline" in data:
            pipeline_steps = data.get("pipeline", [])
            for i, step_action in enumerate(pipeline_steps):
                step_id = f"step_{i}"
                steps[step_id] = WorkflowStep(
                    id=step_id,
                    type=StepType.TASK,
                    name=f"Pipeline Step {i+1}",
                    action=step_action,
                    next_steps=[f"step_{i+1}"] if i+1 < len(pipeline_steps) else []
                )
            if not start_step_id and steps:
                start_step_id = "step_0"
            if not end_step_id and steps:
                end_step_id = f"step_{len(pipeline_steps)-1}"

        # Create workflow
        workflow = Workflow(
            id=workflow_id,
            name=name,
            version=version,
            description=description,
            steps=steps,
            start_step_id=start_step_id,
            end_step_id=end_step_id,
            variables=variables,
            configuration=data.get("configuration", {}),
            tags=tags,
            created_by=created_by,
            created_at=created_at,
            updated_at=updated_at
        )

        return workflow

    def _parse_step(self, step_id: str, data: dict) -> WorkflowStep:
        """Parse a single step definition"""
        # Step type
        step_type = data.get("type", "task")
        if isinstance(step_type, str):
            step_type = StepType(step_type)
        elif step_type is None:
            step_type = StepType.TASK

        # Basic required fields
        name = data.get("name", step_id)
        description = data.get("description", "")

        # Determine action based on type
        action = data.get("action", "")
        if not action and step_type == StepType.TASK:
            action = data.get("task", name)

        # Handler
        handler = data.get("handler")

        # Parameters
        parameters = data.get("parameters", {})
        # Also support 'args', 'config', 'options'
        parameters.update(data.get("args", {}))
        parameters.update(data.get("config", {}))
        parameters.update(data.get("options", {}))

        # IO configuration
        io_data = data.get("io", {})
        io = StepIO(
            inputs=io_data.get("inputs", {}),
            outputs=io_data.get("outputs", {}),
            result_path=io_data.get("result_path")
        )

        # Flow control
        next_steps = data.get("next_steps", []) or data.get("next", [])
        condition = data.get("condition")
        branches = data.get("branches", {})
        # Also support 'if' / 'else' structure
        if "if" in data:
            if not condition:
                condition = data["if"]
            if "then" in data:
                branches["true"] = data["then"]
            if "else" in data:
                branches["false"] = data["else"]

        # Parallel
        parallel = data.get("parallel", False)
        join_policy = data.get("join_policy", "all")
        join_n = data.get("join_n", 1)

        # Loop
        loop_condition = data.get("loop_condition") or data.get("while")
        loop_variable = data.get("loop_variable") or data.get("iterate")
        max_iterations = data.get("max_iterations") or data.get("max_loops")

        # Subworkflow
        subworkflow_id = data.get("subworkflow_id") or data.get("workflow")
        subworkflow_inputs = data.get("subworkflow_inputs", {}) or data.get("workflow_inputs", {})

        # Wait
        wait_for = data.get("wait_for") or data.get("wait")
        wait_timeout_ms = data.get("wait_timeout_ms") or data.get("wait_timeout")

        # Script
        script = data.get("script")
        script_language = data.get("script_language", "python")

        # Error handling
        on_error = data.get("on_error", "fail")
        error_handler = data.get("error_handler") or data.get("error_step")
        retry_policy_data = data.get("retry_policy", {})
        retry_policy = RetryPolicy(**retry_policy_data) if retry_policy_data else RetryPolicy()

        # Timeout
        timeout_policy_data = data.get("timeout_policy", {})
        timeout_policy = TimeoutPolicy(**timeout_policy_data) if timeout_policy_data else TimeoutPolicy()

        # Compensation
        compensate_steps = data.get("compensate_steps", []) or data.get("rollback_steps", [])

        # Tags and metadata
        tags = data.get("tags", [])
        metadata = {k: v for k, v in data.items() if k not in {
            "id", "type", "name", "description", "action", "task", "handler",
            "parameters", "args", "config", "options",
            "io", "next_steps", "next", "condition", "if", "then", "else", "branches",
            "parallel", "join_policy", "join_n",
            "loop_condition", "while", "loop_variable", "iterate", "max_iterations", "max_loops",
            "subworkflow_id", "workflow", "subworkflow_inputs", "workflow_inputs",
            "wait_for", "wait", "wait_timeout_ms", "wait_timeout",
            "script", "script_language",
            "on_error", "error_handler", "error_step", "retry_policy",
            "timeout_policy", "compensate_steps", "rollback_steps",
            "tags", "metadata"
        }}
        metadata.update(data.get("metadata", {}))

        return WorkflowStep(
            id=step_id,
            type=step_type,
            name=name,
            description=description,
            action=action,
            handler=handler,
            parameters=parameters,
            io=io,
            next_steps=next_steps,
            condition=condition,
            branches=branches,
            parallel=parallel,
            join_policy=join_policy,
            join_n=join_n,
            loop_condition=loop_condition,
            loop_variable=loop_variable,
            max_iterations=max_iterations,
            subworkflow_id=subworkflow_id,
            subworkflow_inputs=subworkflow_inputs,
            wait_for=wait_for,
            wait_timeout_ms=wait_timeout_ms,
            script=script,
            script_language=script_language,
            on_error=on_error,
            error_handler=error_handler,
            retry_policy=retry_policy,
            timeout_policy=timeout_policy,
            compensate_steps=compensate_steps,
            tags=tags,
            metadata=metadata
        )

    # ==================== Programmatic Building ====================

    @classmethod
    def create(cls, workflow_id: str, name: str) -> "WorkflowBuilder":
        """Start building a new workflow programmatically"""
        builder = cls()
        builder._workflow = Workflow(
            id=workflow_id,
            name=name,
            steps={},
            start_step_id="",
            variables=[]
        )
        return builder

    def description(self, desc: str) -> "WorkflowBuilder":
        """Set workflow description"""
        if self._workflow:
            self._workflow.description = desc
        return self

    def version(self, version: str) -> "WorkflowBuilder":
        """Set workflow version"""
        if self._workflow:
            self._workflow.version = version
        return self

    def variable(self, name: str, default: Any = None, required: bool = False,
                 description: str = "") -> "WorkflowBuilder":
        """Add a workflow variable"""
        if self._workflow:
            self._workflow.variables.append(VariableScope(
                name=name,
                default_value=default,
                description=description,
                required=required
            ))
        return self

    def add_step(self, step_id: str, step_type: str | StepType, name: str,
                 **kwargs) -> "WorkflowBuilder":
        """Add a step to the workflow"""
        if not self._workflow:
            raise ValueError("Workflow not initialized. Call WorkflowBuilder.create() first.")

        if isinstance(step_type, str):
            step_type = StepType(step_type)

        step = WorkflowStep(
            id=step_id,
            type=step_type,
            name=name,
            **kwargs
        )
        self._workflow.steps[step_id] = step

        # If this is the first step and start_step_id not set, use this
        if not self._workflow.start_step_id:
            self._workflow.start_step_id = step_id

        return self

    def task(self, step_id: str, name: str, action: str, **kwargs) -> "WorkflowBuilder":
        """Add a task step"""
        return self.add_step(step_id, StepType.TASK, name, action=action, **kwargs)

    def condition(self, step_id: str, name: str, condition: str,
                  branches: dict[str, str], **kwargs) -> "WorkflowBuilder":
        """Add a conditional step"""
        return self.add_step(
            step_id, StepType.CONDITION, name,
            condition=condition,
            branches=branches,
            **kwargs
        )

    def parallel(self, step_id: str, name: str, steps: list[str],
                 join_policy: str = "all", **kwargs) -> "WorkflowBuilder":
        """Add a parallel step that executes multiple branches"""
        branches = {f"branch{i}": step_id for i, step_id in enumerate(steps)}
        return self.add_step(
            step_id, StepType.PARALLEL, name,
            branches=branches,
            parallel=True,
            join_policy=join_policy,
            **kwargs
        )

    def loop(self, step_id: str, name: str, loop_condition: str = None,
             loop_variable: str = None, max_iterations: int = None,
             **kwargs) -> "WorkflowBuilder":
        """Add a loop step"""
        return self.add_step(
            step_id, StepType.LOOP, name,
            loop_condition=loop_condition,
            loop_variable=loop_variable,
            max_iterations=max_iterations,
            **kwargs
        )

    def subworkflow(self, step_id: str, name: str, subworkflow_id: str,
                    inputs: dict[str, Any] = None, **kwargs) -> "WorkflowBuilder":
        """Add a subworkflow invocation"""
        return self.add_step(
            step_id, StepType.SUBWORKFLOW, name,
            subworkflow_id=subworkflow_id,
            subworkflow_inputs=inputs or {},
            **kwargs
        )

    def script_step(self, step_id: str, name: str, script: str,
                    language: str = "python", **kwargs) -> "WorkflowBuilder":
        """Add a script execution step"""
        return self.add_step(
            step_id, StepType.SCRIPT, name,
            script=script,
            script_language=language,
            **kwargs
        )

    def connect(self, from_step_id: str, to_step_id: str) -> "WorkflowBuilder":
        """Connect two steps sequentially"""
        if not self._workflow:
            raise ValueError("Workflow not initialized")
        if from_step_id not in self._workflow.steps:
            raise ValueError(f"Step '{from_step_id}' not found")
        if to_step_id not in self._workflow.steps:
            raise ValueError(f"Step '{to_step_id}' not found")

        self._workflow.steps[from_step_id].next_steps.append(to_step_id)
        return self

    def build(self) -> Workflow:
        """Build and validate the workflow"""
        if not self._workflow:
            raise ValueError("No workflow to build")

        # Validate
        errors = self._workflow.validate()
        if errors:
            raise ValueError(f"Workflow validation failed: {'; '.join(errors)}")

        return self._workflow

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return self.build().to_dict()

    # ==================== DSL Parsing ====================

    @classmethod
    def parse_dsl(cls, dsl_text: str) -> Workflow:
        """
        Parse a simple DSL for defining workflows.
        Example:
        ```
        workflow DataPipeline
          description: "Collect and process data"
          var input_file default="data.csv"
          var output_file default="result.json"

          step collect
            type: task
            action: collect_data
            next: validate

          step validate
            type: condition
            condition: "data_valid == true"
            branches:
              true: transform
              false: retry

          step transform
            type: task
            action: transform_data
            next: done
        ```
        """
        import re

        lines = dsl_text.strip().split("\n")
        data = {}
        current_step = None
        steps = {}

        for line in lines:
            line = line.rstrip()
            indent = len(line) - len(line.lstrip())

            # Workflow header
            if re.match(r"^workflow\s+\w+", line, re.IGNORECASE):
                match = re.search(r"workflow\s+(\w+)", line, re.IGNORECASE)
                if match:
                    data["id"] = match.group(1)
                    data["name"] = match.group(1)
                continue

            # Description
            if indent == 2 and line.strip().startswith("description:"):
                data["description"] = line.strip().split(":", 1)[1].strip().strip('"\'')
                continue

            # Variable definition
            if indent == 2 and re.match(r"^var\s+\w+", line):
                parts = line.strip().split()
                var_name = parts[1]
                var_def = {"name": var_name}
                if "default=" in line:
                    default_val = line.split("default=")[1].split()[0].strip(",")
                    var_def["default_value"] = default_val
                if "required" in line:
                    var_def["required"] = True
                if "vars" not in data:
                    data["vars"] = []
                data["vars"].append(var_def)
                continue

            # Step declaration
            step_match = re.match(r"^step\s+(\w+)", line, re.IGNORECASE)
            if step_match:
                step_id = step_match.group(1)
                current_step = {"id": step_id, "name": step_id}
                steps[step_id] = current_step
                continue

            # Step properties
            if current_step and indent >= 4:
                prop_line = line.strip()
                if ":" in prop_line:
                    key, value = prop_line.split(":", 1)
                    key = key.strip()
                    value = value.strip()

                    # Handle special cases
                    if key == "type":
                        current_step["type"] = value
                    elif key == "action" or key == "task":
                        current_step["action"] = value
                    elif key == "next":
                        if isinstance(current_step.get("next_steps"), list):
                            current_step["next_steps"].append(value)
                        else:
                            current_step["next_steps"] = [value]
                    elif key == "condition":
                        current_step["condition"] = value
                    elif key == "branches":
                        # Parse YAML-like branches
                        branches = {}
                        for branch_line in value.split("\n"):
                            branch_line = branch_line.strip()
                            if ":" in branch_line:
                                k, v = branch_line.split(":", 1)
                                branches[k.strip()] = v.strip()
                        current_step["branches"] = branches
                    else:
                        current_step[key] = value

        # Assemble workflow
        data["steps"] = steps
        return cls.from_dict(data)


# ==================== Convenience Functions ====================

def load_workflow(filepath: str | Path) -> Workflow:
    """Load workflow from file (auto-detect format)"""
    filepath = Path(filepath)
    suffix = filepath.suffix.lower()
    if suffix == ".yaml" or suffix == ".yml":
        return WorkflowBuilder.from_yaml(filepath)
    if suffix == ".json":
        return WorkflowBuilder.from_json(filepath)
    raise ValueError(f"Unsupported file format: {suffix}")


def workflow_from_template(template_id: str, storage: "WorkflowStorage",
                          overrides: dict = None) -> Workflow:
    """Create a workflow from a stored template"""
    template_def = storage.load_template(template_id)
    if not template_def:
        raise ValueError(f"Template not found: {template_id}")

    # Apply overrides
    if overrides:
        # Deep merge overrides
        def merge_dict(base, update):
            for k, v in update.items():
                if isinstance(v, dict) and isinstance(base.get(k), dict):
                    merge_dict(base[k], v)
                else:
                    base[k] = v
        merge_dict(template_def, overrides)

    return WorkflowBuilder.from_dict(template_def)


if __name__ == "__main__":
    # Test builder
    yaml_example = """
id: example_workflow
name: Example Workflow
description: A simple example workflow
version: "1.0.0"
start_step_id: step1
variables:
  - name: input_data
    default: "default_input"
    required: true
steps:
  step1:
    type: task
    name: First Step
    action: collect_data
    next_steps: [step2]
  step2:
    type: condition
    name: Check Data
    condition: "data_valid == true"
    branches:
      true: step3
      false: step4
  step3:
    type: task
    name: Process
    action: process_data
  step4:
    type: task
    name: Handle Error
    action: handle_error
"""

    print("Testing YAML builder...")
    wf = WorkflowBuilder.from_yaml.__func__(yaml_example)  # type: ignore
    print("Workflow loaded!")
    print(f"ID: {wf.id}, Name: {wf.name}, Steps: {len(wf.steps)}")

    errors = wf.validate()
    if errors:
        print("Errors:", errors)
    else:
        print("Valid workflow!")
        print(json.dumps(wf.to_dict(), indent=2))
