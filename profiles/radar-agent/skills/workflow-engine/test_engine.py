#!/usr/bin/env python3
"""
Test script for the Workflow Engine.
Runs basic tests to verify functionality.
"""
import asyncio
import sys
import tempfile
from pathlib import Path

# If running as script in the package directory, set up package imports
if __name__ == "__main__" and __package__ is None:
    package_dir = str(Path(__file__).parent)
    if package_dir not in sys.path:
        sys.path.insert(0, package_dir)
    __package__ = Path(__file__).parent.name

from .workflow_builder import WorkflowBuilder
from .workflow_definitions import StepStatus, StepType, Workflow, WorkflowStatus, WorkflowStep
from .workflow_engine import WorkflowEngine
from .workflow_storage import WorkflowStorage


async def test_engine_async():
    """Test workflow execution with async"""
    print("\n=== Test 3: Workflow Execution (Async) ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_engine.sqlite"
        storage = WorkflowStorage(str(db_path))

        wf_data = {
            "id": "simple_pipeline",
            "name": "Simple Pipeline",
            "start_step_id": "task1",
            "steps": {
                "task1": {
                    "id": "task1",
                    "type": "task",
                    "name": "Task 1",
                    "action": "test_action_1",
                    "next_steps": ["task2"]
                },
                "task2": {
                    "id": "task2",
                    "type": "task",
                    "name": "Task 2",
                    "action": "test_action_2"
                }
            }
        }

        workflow = WorkflowBuilder.from_dict(wf_data)
        storage.save_workflow(workflow)

        async def handler1(context):
            return {"result": "from handler1"}

        async def handler2(context):
            prev = context["variables"].get("_test_action_1_result", {})
            return {"result": "from handler2", "prev": prev}

        engine = WorkflowEngine(storage)
        engine.register_handler("test_action_1", handler1)
        engine.register_handler("test_action_2", handler2)

        print("Running workflow asynchronously...")
        run_id = engine.execute_workflow("simple_pipeline", wait=True)

        # Check status
        status = engine.get_run_status(run_id)
        print(f"Workflow completed. Status: {status['status']}")

        if status["status"] == "completed":
            print("✓ Workflow executed successfully")
            return True
        print(f"✗ Workflow failed with status: {status['status']}")
        return False


def test_basic_workflow():
    """Test a basic sequential workflow"""
    print("\n=== Test 1: Basic Sequential Workflow ===")

    wf_def = {
        "id": "test_basic",
        "name": "Test Basic Workflow",
        "start_step_id": "step1",
        "steps": {
            "step1": {"id": "step1", "type": "task", "name": "Step 1", "action": "test_action_1"},
            "step2": {"id": "step2", "type": "task", "name": "Step 2", "action": "test_action_2", "next_steps": ["step3"]},
            "step3": {"id": "step3", "type": "task", "name": "Step 3", "action": "test_action_3"}
        }
    }

    workflow = WorkflowBuilder.from_dict(wf_def)
    print(f"Created workflow: {workflow.name} with {len(workflow.steps)} steps")

    errors = workflow.validate()
    if errors:
        print(f"Validation errors: {errors}")
        return False
    print("Validation: OK")
    return True


def test_storage():
    """Test storage operations"""
    print("\n=== Test 2: Storage Operations ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.sqlite"
        storage = WorkflowStorage(str(db_path))

        wf = Workflow(
            id="test_wf",
            name="Test Workflow",
            start_step_id="start",
            steps={
                "start": WorkflowStep(id="start", type=StepType.TASK, name="Start", action="test")
            }
        )

        if not storage.save_workflow(wf):
            print("Failed to save workflow")
            return False
        print("Saved workflow")

        loaded = storage.load_workflow("test_wf")
        if not loaded:
            print("Failed to load workflow")
            return False
        print(f"Loaded workflow: {loaded.name}")

        run_id = storage.create_run(workflow_id="test_wf", run_id="test_run_1", goal="Test run", trigger_by="test")
        if not run_id:
            print("Failed to create run")
            return False
        print(f"Created run: {run_id}")

        if not storage.update_run_status(run_id, WorkflowStatus.COMPLETED):
            print("Failed to update run status")
            return False
        print("Updated run status")

        step_exec_id = storage.create_step_execution(
            run_id=run_id,
            workflow_id="test_wf",
            step_id="start",
            step_type="task",
            step_name="Start"
        )
        if not step_exec_id:
            print("Failed to create step execution")
            return False
        print(f"Created step execution: {step_exec_id}")

        if not storage.complete_step(step_exec_id, StepStatus.COMPLETED, result={"status": "ok"}):
            print("Failed to complete step")
            return False
        print("Completed step")

    print("Storage operations: OK")
    return True


def test_conditional():
    """Test conditional workflow"""
    print("\n=== Test 4: Conditional Workflow ===")

    wf_data = {
        "id": "conditional_test",
        "name": "Conditional Test",
        "start_step_id": "check",
        "variables": [{"name": "value", "default_value": 10}],
        "steps": {
            "check": {
                "id": "check",
                "type": "condition",
                "name": "Check Value",
                "condition": "value > 5",
                "branches": {"true": "high_path", "false": "low_path"}
            },
            "high_path": {"id": "high_path", "type": "task", "name": "High Value", "action": "mark_high"},
            "low_path": {"id": "low_path", "type": "task", "name": "Low Value", "action": "mark_low"}
        }
    }

    workflow = WorkflowBuilder.from_dict(wf_data)
    errors = workflow.validate()
    if errors:
        print(f"Validation errors: {errors}")
        return False
    print("Conditional workflow validated successfully")
    return True


async def main_async():
    """Run all tests (some async)"""
    results = []

    # Sync tests
    sync_tests = [test_basic_workflow, test_storage, test_conditional]
    for test in sync_tests:
        try:
            result = test()
            results.append((test.__name__, result))
        except Exception as e:
            print(f"Test {test.__name__} failed: {e}")
            import traceback
            traceback.print_exc()
            results.append((test.__name__, False))

    # Async test
    try:
        result = await test_engine_async()
        results.append(("test_engine_async", result))
    except Exception as e:
        print(f"Test test_engine_async failed: {e}")
        import traceback
        traceback.print_exc()
        results.append(("test_engine_async", False))

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    for name, passed in results:
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {name}")

    all_passed = all(passed for _, passed in results)
    if all_passed:
        print("\nAll tests passed!")
        return 0
    print("\nSome tests failed.")
    return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main_async()))
