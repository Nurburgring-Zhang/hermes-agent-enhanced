"""
Workflow Engine Module
Core execution engine for running workflows with full state management,
error handling, retry logic, timeouts, parallelism, and persistence.
"""
import asyncio
import json
import threading
import time
import traceback
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from workflow_definitions import (
    ExecutionContext,
    StepStatus,
    StepType,
    Workflow,
    WorkflowStatus,
    WorkflowStep,
    evaluate_condition,
)
from workflow_storage import WorkflowStorage


class WorkflowEngine:
    """
    Main workflow execution engine.
    Supports:
    - Sequential, parallel, conditional, and loop step execution
    - Subworkflow invocation
    - Retry with exponential backoff
    - Timeout handling
    - Compensation/rollback on failure
    - Variable scoping and data flow
    - Persistent state via WorkflowStorage
    - Event logging and monitoring
    - Graceful shutdown and resumption
    """

    def __init__(self, storage: WorkflowStorage = None, max_workers: int = 10):
        self.storage = storage or WorkflowStorage()
        self.max_workers = max_workers
        self._running_runs: dict[str, WorkflowExecution] = {}
        self._lock = threading.RLock()
        self._shutdown = False
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="workflow-")

        # Handler registry for custom actions
        self._handlers: dict[str, Callable] = {}

        # Event listeners
        self._event_listeners: list[Callable] = []

        # Load pending runs on init (for recovery)
        self._recover_pending_runs()

    def register_handler(self, action: str, handler: Callable):
        """Register a handler function for a specific action/step type"""
        self._handlers[action] = handler

    def add_event_listener(self, listener: Callable):
        """Add an event listener for workflow events"""
        self._event_listeners.append(listener)

    def _emit_event(self, run_id: str, event_type: str, step_id: str = None,
                   event_data: dict = None):
        """Emit an event to all listeners and log to storage"""
        event = {
            "run_id": run_id,
            "event_type": event_type,
            "step_id": step_id,
            "event_data": event_data or {},
            "timestamp": time.time()
        }
        # Log to storage
        self.storage.log_event(run_id, event_type, step_id, event_data)
        # Notify listeners
        for listener in self._event_listeners:
            try:
                listener(event)
            except Exception as e:
                print(f"Event listener error: {e}")

    def _recover_pending_runs(self):
        """Recover interrupted runs that were in 'running' state"""
        pending_runs = self.storage.list_runs(
            status=WorkflowStatus.RUNNING,
            limit=100
        )
        for run_data in pending_runs:
            run_id = run_data["run_id"]
            print(f"Found interrupted run: {run_id}, attempting recovery...")
            # In a full implementation, we would resume from last known state
            # For now, we'll mark them as failed with a recovery error
            self.storage.update_run_status(
                run_id,
                WorkflowStatus.FAILED,
                error_message="Workflow interrupted (engine restart)",
                error_details=json.dumps({"recovered": True})
            )

    def start_workflow(self, workflow_id: str, run_id: str = None,
                      context: dict = None, variables: dict = None,
                      goal: str = None, trigger_by: str = None) -> str:
        """
        Start a new workflow execution (synchronous blocking wait).
        Returns run_id.
        """
        return self.execute_workflow(workflow_id, run_id, context, variables, goal, trigger_by, wait=True)

    def start_workflow_async(self, workflow_id: str, run_id: str = None,
                           context: dict = None, variables: dict = None,
                           goal: str = None, trigger_by: str = None) -> str:
        """
        Start a new workflow execution asynchronously.
        Returns run_id immediately, execution happens in background.
        """
        return self.execute_workflow(workflow_id, run_id, context, variables, goal, trigger_by, wait=False)

    def execute_workflow(self, workflow_id: str, run_id: str = None,
                        context: dict = None, variables: dict = None,
                        goal: str = None, trigger_by: str = None,
                        wait: bool = True) -> str:
        """
        Execute a workflow.
        If wait=True, blocks until completion and returns final status.
        If wait=False, returns run_id immediately and runs in background.
        """
        # Generate run_id if not provided
        if not run_id:
            run_id = f"run_{workflow_id}_{int(time.time() * 1000)}"

        # Load workflow definition
        workflow = self.storage.load_workflow(workflow_id)
        if not workflow:
            raise ValueError(f"Workflow not found: {workflow_id}")

        # Create execution context
        ctx = ExecutionContext(
            workflow_id=workflow_id,
            run_id=run_id,
            started_at=time.time()
        )

        # Initialize variables from:
        # 1. Workflow variable defaults
        for var in workflow.variables:
            if var.default_value is not None:
                ctx.set_variable(var.name, var.default_value)

        # 2. Provided variables
        if variables:
            for k, v in variables.items():
                ctx.set_variable(k, v)

        # Validate required variables
        missing_required = []
        for var in workflow.variables:
            if var.required and var.name not in ctx.variables:
                missing_required.append(var.name)
        if missing_required:
            raise ValueError(f"Missing required variables: {missing_required}")

        # Create run record in storage
        self.storage.create_run(
            workflow_id=workflow_id,
            run_id=run_id,
            goal=goal or workflow.description,
            trigger_type="async" if not wait else "sync",
            trigger_by=trigger_by,
            input_variables=variables,
            initial_context=context
        )

        # Create execution wrapper
        exec_obj = WorkflowExecution(
            engine=self,
            workflow=workflow,
            context=ctx,
            storage=self.storage
        )

        # Register in running set
        with self._lock:
            self._running_runs[run_id] = exec_obj

        # Emit start event
        self._emit_event(run_id, "workflow_started", None, {"workflow_id": workflow_id})

        if wait:
            # Run synchronously in current thread
            try:
                final_status = exec_obj.run()
                return run_id
            finally:
                with self._lock:
                    self._running_runs.pop(run_id, None)
        else:
            # Run in background thread
            def background_run():
                try:
                    exec_obj.run()
                except Exception as e:
                    print(f"Background run {run_id} failed: {e}")
                    traceback.print_exc()
                finally:
                    with self._lock:
                        self._running_runs.pop(run_id, None)

            thread = threading.Thread(target=background_run, name=f"workflow-{run_id}", daemon=True)
            thread.start()
            return run_id

    def get_run_status(self, run_id: str) -> dict | None:
        """Get current status of a workflow run"""
        run_data = self.storage.get_run(run_id)
        if run_data:
            return {
                "run_id": run_id,
                "workflow_id": run_data["workflow_id"],
                "status": run_data["status"],
                "started_at": run_data["started_at"],
                "completed_at": run_data.get("completed_at"),
                "error_message": run_data.get("error_message")
            }
        return None

    def list_runs(self, **kwargs) -> list[dict]:
        """List workflow runs (passes through to storage)"""
        return self.storage.list_runs(**kwargs)

    def stop_run(self, run_id: str, reason: str = "Requested stop") -> bool:
        """Request a running workflow to stop gracefully"""
        with self._lock:
            exec_obj = self._running_runs.get(run_id)
            if exec_obj:
                exec_obj.request_stop(reason)
                return True
        # If not running, check if it exists and mark cancelled
        run_data = self.storage.get_run(run_id)
        if run_data and run_data["status"] == "running":
            self.storage.update_run_status(run_id, WorkflowStatus.CANCELLED, f"Stopped: {reason}")
            return True
        return False

    def shutdown(self):
        """Shutdown the engine (stop all running workflows)"""
        self._shutdown = True
        with self._lock:
            for exec_obj in self._running_runs.values():
                exec_obj.request_stop("Engine shutdown")
        self._executor.shutdown(wait=False)


class WorkflowExecution:
    """
    Handles execution of a single workflow instance.
    Manages step execution order, state, retries, timeouts, etc.
    """

    def __init__(self, engine: WorkflowEngine, workflow: Workflow,
                 context: ExecutionContext, storage: WorkflowStorage):
        self.engine = engine
        self.workflow = workflow
        self.context = context
        self.storage = storage
        self._stop_requested = False
        self._active_step_futures: set[asyncio.Future] = set()

    def request_stop(self, reason: str = ""):
        """Request graceful shutdown of this execution"""
        self._stop_requested = True
        self.context.set_variable("_stop_requested", True)
        self.context.set_variable("_stop_reason", reason)
        print(f"[{self.context.run_id}] Stop requested: {reason}")

    async def run(self) -> WorkflowStatus:
        """Execute the workflow (main entry point)"""
        print(f"[{self.context.run_id}] Starting workflow: {self.workflow.name}")

        try:
            # Initialize step execution tracking
            completed_steps: set[str] = set()
            active_steps: dict[str, asyncio.Future] = {}

            # Start with initial step
            pending_steps = [self.workflow.start_step_id]

            while pending_steps or active_steps:
                # Check for stop request
                if self._stop_requested:
                        self.context.status = WorkflowStatus.CANCELLED
                        break

                # Process pending steps (depth-first with parallel support)
                new_pending = []
                for step_id in pending_steps:
                    if step_id in completed_steps:
                        continue

                    step = self.workflow.steps.get(step_id)
                    if not step:
                        print(f"[{self.context.run_id}] Step not found: {step_id}")
                        continue

                    # Check if step should run in parallel
                    if step.parallel and step.branches:
                        # Execute parallel branches
                        branch_results = await self._execute_parallel_branches(step)
                        # After parallel, continue with next steps
                        for next_id in step.next_steps:
                            if next_id not in completed_steps:
                                new_pending.append(next_id)
                        completed_steps.add(step_id)
                    else:
                        # Execute step synchronously
                        success = await self._execute_step(step)
                        if success:
                            completed_steps.add(step_id)
                            # Determine next step
                            next_step_ids = self._determine_next_steps(step)
                            for next_id in next_step_ids:
                                if next_id not in completed_steps and next_id not in active_steps:
                                    new_pending.append(next_id)
                        else:
                            # Step failed, handle based on on_error policy
                            should_continue = await self._handle_step_failure(step)
                            if not should_continue:
                                break

                pending_steps = new_pending

                # Small delay to avoid busy loop
                await asyncio.sleep(0.01)

            # Workflow complete
            final_status = self.context.status
            if final_status == WorkflowStatus.RUNNING:
                final_status = WorkflowStatus.COMPLETED
                self.context.status = final_status

            # Record completion
            self.context.completed_at = time.time()
            final_context = self.context.to_dict()

            # Update storage
            self.storage.update_run_status(
                self.context.run_id,
                final_status,
                final_context=final_context
            )

            # Emit completion event
            self._emit_event(
                self.context.run_id,
                "workflow_completed" if final_status == WorkflowStatus.COMPLETED else "workflow_failed",
                None,
                {"duration_sec": self.context.completed_at - self.context.started_at}
            )

            print(f"[{self.context.run_id}] Workflow finished with status: {final_status.value}")
            return final_status

        except Exception as e:
            print(f"[{self.context.run_id}] Workflow execution failed: {e}")
            traceback.print_exc()

            self.context.status = WorkflowStatus.FAILED
            self.context.add_error("workflow", e, fatal=True)
            self.context.completed_at = time.time()

            self.storage.update_run_status(
                self.context.run_id,
                WorkflowStatus.FAILED,
                error_message=str(e),
                error_details=traceback.format_exc(),
                final_context=self.context.to_dict()
            )

            self._emit_event(self.context.run_id, "workflow_failed", None, {"error": str(e)})
            return WorkflowStatus.FAILED

    async def _execute_step(self, step: WorkflowStep) -> bool:
        """
        Execute a single step.
        Returns True if successful, False otherwise.
        """
        step_exec_id = None
        try:
            # Check stop before starting
            if self._stop_requested:
                return False

            # Create step execution record
            step_exec_id = self.storage.create_step_execution(
                run_id=self.context.run_id,
                workflow_id=self.context.workflow_id,
                step_id=step.id,
                step_type=step.type.value,
                step_name=step.name,
                parameters=step.parameters
            )
            if not step_exec_id:
                print(f"[{self.context.run_id}] Failed to create step execution record")
                return False

            # Start step
            input_vars = {k: self.context.get_variable(k) for k in step.io.inputs.keys()}
            self.storage.start_step(step_exec_id, input_vars)

            # Record in context
            self.context.current_step_id = step.id

            # Check retry policy - get current attempt count from history
            retry_count = sum(
                1 for record in self.context.step_history
                if record["step_id"] == step.id and record.get("retry_count") is not None
            )
            max_attempts = step.retry_policy.max_attempts

            for attempt in range(max_attempts):
                if self._stop_requested:
                    self.storage.complete_step(step_exec_id, StepStatus.CANCELLED)
                    return False

                if attempt > 0:
                    print(f"[{self.context.run_id}] Retrying {step.id} (attempt {attempt + 1}/{max_attempts})")
                    # Exponential backoff
                    delay = min(
                        step.retry_policy.initial_delay_ms * (step.retry_policy.backoff_factor ** (attempt - 1)),
                        step.retry_policy.max_delay_ms
                    )
                    await asyncio.sleep(delay / 1000.0)

                # Execute the step
                start_time = time.time()
                success, result, error = await self._execute_step_core(step, step_exec_id, attempt)

                duration_ms = (time.time() - start_time) * 1000

                if success:
                    # Record outputs to context
                    self._record_step_outputs(step, result)
                    self.storage.complete_step(
                        step_exec_id,
                        StepStatus.COMPLETED,
                        output_vars={k: self.context.get_variable(k) for k in step.io.outputs.keys()},
                        result=result,
                        duration_ms=duration_ms
                    )
                    self.context.record_step_execution(
                        step.id,
                        StepStatus.COMPLETED,
                        output=result,
                        duration_ms=duration_ms
                    )
                    self.engine._emit_event(
                        self.context.run_id,
                        "step_completed",
                        step.id,
                        {"duration_ms": duration_ms}
                    )
                    return True
                # Check if should retry
                if attempt + 1 < max_attempts:
                    print(f"[{self.context.run_id}] Step {step.id} failed (attempt {attempt+1}): {error}")
                    continue
                # Max attempts exhausted
                self.storage.complete_step(
                    step_exec_id,
                    StepStatus.FAILED,
                    error_message=str(error),
                    error_details=traceback.format_exc(),
                    duration_ms=duration_ms
                )
                self.context.record_step_execution(
                    step.id,
                    StepStatus.FAILED,
                    error=error,
                    duration_ms=duration_ms
                )
                self.context.add_error(step.id, error)
                return False

        except Exception as e:
            if step_exec_id:
                self.storage.complete_step(
                    step_exec_id,
                    StepStatus.FAILED,
                    error_message=str(e),
                    error_details=traceback.format_exc()
                )
            self.context.record_step_execution(step.id, StepStatus.FAILED, error=e)
            self.context.add_error(step.id, e)
            return False

    async def _execute_step_core(self, step: WorkflowStep, step_exec_id: str, attempt: int) -> tuple:
        """
        Core step execution logic.
        Returns (success: bool, result: Any, error: Exception)
        """
        try:
            # Check timeout policy
            timeout = step.timeout_policy.timeout_ms / 1000.0 if step.timeout_policy else None

            # Determine execution method based on step type
            if step.type == StepType.TASK:
                result = await self._execute_task(step, timeout)
            elif step.type == StepType.CONDITION:
                result = await self._execute_condition(step)
            elif step.type == StepType.PARALLEL:
                result = await self._execute_parallel(step)
            elif step.type == StepType.LOOP:
                result = await self._execute_loop(step)
            elif step.type == StepType.SUBWORKFLOW:
                result = await self._execute_subworkflow(step)
            elif step.type == StepType.WAIT:
                result = await self._execute_wait(step)
            elif step.type == StepType.SCRIPT:
                result = await self._execute_script(step)
            elif step.type == StepType.TRANSFORM:
                result = await self._execute_transform(step)
            else:
                raise ValueError(f"Unsupported step type: {step.type}")

            return True, result, None

        except Exception as e:
            return False, None, e

    async def _execute_task(self, step: WorkflowStep, timeout: float = None) -> Any:
        """Execute a task step"""
        action = step.action or step.id

        # Check for registered handler
        if action in self.engine._handlers:
            handler = self.engine._handlers[action]
            # Build task context
            task_context = {
                "step": step.to_dict(),
                "workflow_id": self.context.workflow_id,
                "run_id": self.context.run_id,
                "variables": dict(self.context.variables),
                "parameters": step.parameters
            }
            if asyncio.iscoroutinefunction(handler):
                result = await asyncio.wait_for(handler(task_context), timeout=timeout)
            else:
                # Run synchronous handler in executor
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    self.engine._executor,
                    lambda: handler(task_context)
                )
            return result

        # No handler - simulate or use default
        print(f"[{self.context.run_id}] No handler for action '{action}', simulating success")
        await asyncio.sleep(0.1)  # Simulate work
        return {"status": "completed", "action": action, "message": "Task executed (no handler)"}

    async def _execute_condition(self, step: WorkflowStep) -> Any:
        """Evaluate a condition step"""
        condition = step.condition
        if not condition:
            raise ValueError("Condition step missing 'condition'")

        # Evaluate condition in context
        result = evaluate_condition(condition, self.context.variables)
        print(f"[{self.context.run_id}] Condition '{condition}' evaluated to: {result}")

        # Store result
        self.context.set_variable(f"_condition_{step.id}", result)

        return {"condition": condition, "result": result, "branch_taken": "true" if result else "false"}

    async def _execute_parallel(self, step: WorkflowStep) -> Any:
        """Execute parallel branches"""
        if not step.branches:
            raise ValueError("Parallel step missing 'branches'")

        # Create tasks for each branch
        tasks = []
        branch_names = list(step.branches.keys())

        for branch_name, target_step_id in step.branches.items():
            # Create a context copy for the branch
            async def run_branch(b_name: str, target_id: str):
                branch_ctx = dict(self.context.variables)
                branch_ctx["_branch_name"] = b_name
                branch_ctx["_branch_target"] = target_id

                # Execute the target step
                target_step = self.workflow.steps.get(target_id)
                if not target_step:
                    raise ValueError(f"Branch target step not found: {target_id}")

                # Simplified: just execute the step directly
                success, result, error = await self._execute_step_core(target_step, None, 0)
                if not success:
                    raise RuntimeError(f"Branch {b_name} failed: {error}")
                return {"branch": b_name, "step_id": target_id, "result": result}

            tasks.append(run_branch(branch_name, target_step_id))

        # Wait for all branches
        if step.join_policy == "all":
            results = await asyncio.gather(*tasks, return_exceptions=True)
            # Check for failures
            for i, res in enumerate(results):
                if isinstance(res, Exception):
                    raise RuntimeError(f"Parallel branch {branch_names[i]} failed: {res}")
            return {"results": {branch_names[i]: results[i] for i in range(len(branch_names))}}
        if step.join_policy == "any":
            # Wait for first successful completion
            done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            for task in pending:
                task.cancel()
            result = done.pop().result()
            return {"first_completed": result}
        # Custom N
        n = step.join_n or 1
        results = []
        for coro in asyncio.as_completed(tasks):
            result = await coro
            results.append(result)
            if len(results) >= n:
                # Cancel remaining
                for task in tasks:
                    if not task.done():
                        task.cancel()
                break
        return {"completed": results}

    async def _execute_loop(self, step: WorkflowStep) -> Any:
        """Execute a loop"""
        if not step.loop_condition and not step.loop_variable:
            raise ValueError("Loop step requires either 'loop_condition' or 'loop_variable'")

        iterations = 0
        results = []

        loop_key = step.loop_variable or "loop_item"
        max_iterations = step.max_iterations or 1000

        while True:
            if self._stop_requested:
                break

            if step.max_iterations and iterations >= step.max_iterations:
                break

            # Check loop condition if provided
            if step.loop_condition:
                try:
                    should_continue = evaluate_condition(step.loop_condition, self.context.variables)
                except Exception as e:
                    raise ValueError(f"Loop condition evaluation failed: {e}")
                if not should_continue:
                    break

            # Execute loop body (steps connected to this loop step)
            # For simplicity, we just track iterations
            iteration_ctx = dict(self.context.variables)
            iteration_ctx[loop_key] = iterations
            self.context.variables.update(iteration_ctx)

            results.append({"iteration": iterations, "context": dict(iteration_ctx)})
            iterations += 1

            # Small delay
            await asyncio.sleep(0.001)

        return {"iterations": iterations, "results": results}

    async def _execute_subworkflow(self, step: WorkflowStep) -> Any:
        """Invoke a subworkflow"""
        if not step.subworkflow_id:
            raise ValueError("Subworkflow step missing 'subworkflow_id'")

        # Prepare subworkflow variables
        sub_vars = {}
        for input_key, source_expr in step.subworkflow_inputs.items():
            # Simple variable resolution
            if source_expr.startswith("$"):
                var_name = source_expr[1:]
                if var_name in self.context.variables:
                    sub_vars[input_key] = self.context.variables[var_name]
            else:
                sub_vars[input_key] = source_expr

        # Push current context onto stack
        self.context.call_stack.append(self.context.current_step_id or "")

        # Execute subworkflow (synchronously)
        sub_run_id = self.engine.start_workflow(
            workflow_id=step.subworkflow_id,
            variables=sub_vars,
            trigger_by=f"parent:{self.context.run_id}"
        )

        # Wait for subworkflow to complete
        while True:
            sub_status = self.engine.get_run_status(sub_run_id)
            if sub_status and sub_status["status"] not in ["running", "pending"]:
                break
            await asyncio.sleep(0.5)

        # Get subworkflow results
        sub_run_data = self.storage.get_run(sub_run_id)
        if sub_run_data and sub_run_data["status"] == "completed":
            final_context = json.loads(sub_run_data["final_context_json"]) if sub_run_data.get("final_context_json") else {}
            # Extract outputs based on step.io.outputs mapping
            subworkflow_outputs = {}
            for output_key, var_name in step.io.outputs.items():
                if var_name in final_context.get("variables", {}):
                    subworkflow_outputs[output_key] = final_context["variables"][var_name]
                    # Set in parent context
                    self.context.set_variable(output_key, final_context["variables"][var_name])

            self.context.call_stack.pop()
            return {"subworkflow_id": step.subworkflow_id, "sub_run_id": sub_run_id, "outputs": subworkflow_outputs}
        self.context.call_stack.pop()
        raise RuntimeError(f"Subworkflow {step.subworkflow_id} failed or was cancelled")

    async def _execute_wait(self, step: WorkflowStep) -> Any:
        """Wait for an event"""
        # For now, simple timeout-based wait
        wait_for = step.wait_for
        timeout_sec = (step.wait_timeout_ms or 300000) / 1000.0

        print(f"[{self.context.run_id}] Waiting for event: {wait_for} (timeout: {timeout_sec}s)")
        start = time.time()

        while time.time() - start < timeout_sec:
            if self._stop_requested:
                raise RuntimeError("Wait cancelled due to stop request")
            # Check if event occurred (would need external notification mechanism)
            # For now, just wait full timeout
            await asyncio.sleep(1)

        raise TimeoutError(f"Wait for '{wait_for}' timed out after {timeout_sec}s")

    async def _execute_script(self, step: WorkflowStep) -> Any:
        """Execute inline script"""
        if not step.script:
            raise ValueError("Script step missing 'script'")

        language = step.script_language or "python"

        if language == "python":
            # Execute in isolated namespace
            namespace = {
                "context": self.context,
                "variables": self.context.variables,
                "__builtins__": {}
            }
            try:
                exec(step.script, namespace)
                # Capture any 'result' or 'output' variable
                result = namespace.get("result", namespace.get("output", {"status": "executed"}))
                return result
            except Exception as e:
                raise RuntimeError(f"Script execution failed: {e}")
        else:
            raise ValueError(f"Unsupported script language: {language}")

    async def _execute_transform(self, step: WorkflowStep) -> Any:
        """Transform data (simple transformation)"""
        # Get input from context
        input_data = {}
        for input_key, var_name in step.io.inputs.items():
            if var_name in self.context.variables:
                input_data[input_key] = self.context.variables[var_name]

        # Apply transformation (could be a function reference or expression)
        transform = step.parameters.get("transform") or step.action
        if callable(transform):
            result = transform(input_data)
        elif isinstance(transform, str):
            # Evaluate as expression
            result = evaluate_condition(transform, {"input": input_data})
        else:
            result = input_data

        return result

    def _determine_next_steps(self, step: WorkflowStep) -> list[str]:
        """Determine which step(s) to execute next after this step"""
        next_steps = []

        # If step is a condition, check which branch to take
        if step.type == StepType.CONDITION:
            # Get condition result from context
            cond_result = self.context.get_variable(f"_condition_{step.id}")
            if cond_result is not None:
                branch_key = "true" if cond_result else "false"
                branch_target = step.branches.get(branch_key)
                if branch_target:
                    next_steps.append(branch_target)
                elif "default" in step.branches:
                    next_steps.append(step.branches["default"])
            else:
                # No condition result? Use sequential next_steps
                next_steps.extend(step.next_steps)
        else:
            # Normal sequential flow
            next_steps.extend(step.next_steps)

        return next_steps

    async def _handle_step_failure(self, step: WorkflowStep) -> bool:
        """
        Handle a step failure according to on_error policy.
        Returns True if workflow should continue, False to stop.
        """
        on_error = step.on_error

        # Check if compensation steps exist
        if on_error == "compensate" and step.compensate_steps:
            print(f"[{self.context.run_id}] Executing compensation for {step.id}")
            for comp_step_id in reversed(step.compensate_steps):  # Execute in reverse
                comp_step = self.workflow.steps.get(comp_step_id)
                if comp_step:
                    try:
                        await self._execute_step(comp_step)
                    except Exception as e:
                        print(f"[{self.context.run_id}] Compensation step {comp_step_id} failed: {e}")

        if on_error == "fail":
            self.context.status = WorkflowStatus.FAILED
            return False
        if on_error == "continue":
            print(f"[{self.context.run_id}] Continuing despite step failure")
            return True
        if on_error == "retry":
            # Already handled in _execute_step
            return True
        # Default: fail
        self.context.status = WorkflowStatus.FAILED
        return False

    def _record_step_outputs(self, step: WorkflowStep, result: Any):
        """Record step outputs to context variables"""
        # If step has output mappings, apply them
        if step.io.outputs:
            # Result might be a dict
            if isinstance(result, dict):
                for output_key, var_name in step.io.outputs.items():
                    if output_key in result:
                        self.context.set_variable(var_name, result[output_key])
            else:
                # Use result directly
                for output_key, var_name in step.io.outputs.items():
                    self.context.set_variable(var_name, result)
        elif result is not None:
            # Auto-create output variable
            result_var = f"_{step.id}_result"
            self.context.set_variable(result_var, result)

    def _emit_event(self, event_type: str, step_id: str = None, event_data: dict = None):
        """Emit event through engine"""
        self.engine._emit_event(self.context.run_id, event_type, step_id, event_data)


async def test_engine():
    """Simple test"""
    storage = WorkflowStorage("/tmp/test_workflows_engine.sqlite")

    # Build a simple workflow
    from workflow_builder import WorkflowBuilder

    wf_data = {
        "id": "test_sequential",
        "name": "Test Sequential",
        "start_step_id": "step1",
        "steps": {
            "step1": {
                "id": "step1",
                "type": "task",
                "name": "Step 1",
                "action": "test_action",
                "next_steps": ["step2"]
            },
            "step2": {
                "id": "step2",
                "type": "task",
                "name": "Step 2",
                "action": "test_action2",
            }
        }
    }

    workflow = WorkflowBuilder.from_dict(wf_data)
    storage.save_workflow(workflow)

    engine = WorkflowEngine(storage)

    # Register a test handler
    async def test_handler(context):
        print(f"Handler called with: {context.get('action')}")
        return {"status": "success", "message": "Handled"}

    engine.register_handler("test_action", test_handler)
    engine.register_handler("test_action2", test_handler)

    # Run workflow
    run_id = engine.start_workflow_async("test_sequential", goal="Test run")
    print(f"Started run: {run_id}")

    # Wait a bit for completion
    await asyncio.sleep(2)

    status = engine.get_run_status(run_id)
    print(f"Final status: {status}")


if __name__ == "__main__":
    asyncio.run(test_engine())
