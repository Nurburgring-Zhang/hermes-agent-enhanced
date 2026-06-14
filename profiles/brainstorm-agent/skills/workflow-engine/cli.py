#!/usr/bin/env python3
"""
Workflow Engine CLI

Command-line interface for managing and running workflows.
Usage:
    workflow-cli run <workflow_id> [--var KEY=VAL] [--wait]
    workflow-cli list [--active] [--tag TAG]
    workflow-cli status [--run RUN_ID] [--workflow WORKFLOW_ID]
    workflow-cli stop <run_id>
    workflow-cli monitor
    workflow-cli create <definition_file>
"""
import argparse
import json
import sys
from pathlib import Path

import yaml

# Add parent directory to path for imports (for direct script execution)
if str(Path(__file__).parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent))

from workflow_builder import WorkflowBuilder
from workflow_engine import WorkflowEngine
from workflow_monitor import WorkflowMonitor
from workflow_storage import WorkflowStorage


def cmd_run(args):
    """Run a workflow"""
    storage = WorkflowStorage()
    engine = WorkflowEngine(storage)

    # Parse variables
    variables = {}
    for var in args.var:
        if "=" in var:
            key, val = var.split("=", 1)
            # Try to parse as JSON, fallback to string
            try:
                val = json.loads(val)
            except:
                pass
            variables[key] = val

    try:
        if args.wait:
            print(f"Running workflow '{args.workflow_id}'...")
            run_id = engine.start_workflow(
                args.workflow_id,
                variables=variables,
                goal=args.goal,
                trigger_by="cli"
            )
            print(f"Run ID: {run_id}")
            print("Waiting for completion...")

            # Wait by checking status
            import time
            while True:
                status = engine.get_run_status(run_id)
                if status:
                    print(f"\rStatus: {status['status']}", end="", flush=True)
                    if status["status"] not in ["running", "pending"]:
                        print(f"\nWorkflow finished with status: {status['status']}")
                        if status.get("error_message"):
                            print(f"Error: {status['error_message']}")
                        break
                time.sleep(1)
        else:
            run_id = engine.start_workflow_async(
                args.workflow_id,
                variables=variables,
                goal=args.goal,
                trigger_by="cli"
            )
            print(f"Started workflow '{args.workflow_id}' asynchronously")
            print(f"Run ID: {run_id}")
            print("Use: workflow-cli status --run", run_id)

        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_list(args):
    """List workflows"""
    storage = WorkflowStorage()

    workflows = storage.list_workflows(active_only=not args.all, tags=args.tag)

    if not workflows:
        print("No workflows found")
        return 0

    # Print as table
    print(f"{'ID':<30} {'Name':<30} {'Version':<10} {'Steps':<8} {'Updated':<12}")
    print("-" * 100)
    for wf in workflows:
        # Get step count by loading full definition
        full_wf = storage.load_workflow(wf["id"])
        step_count = len(full_wf.steps) if full_wf else 0
        updated = time.strftime("%Y-%m-%d", time.localtime(wf["updated_at"]/1000)) if wf["updated_at"] else "N/A"
        active_marker = "" if wf["is_active"] else " [INACTIVE]"
        print(f"{wf['id']:<30} {wf['name']:<30} {wf['version']:<10} {step_count:<8} {updated:<12}{active_marker}")

    print(f"\nTotal: {len(workflows)} workflows")
    return 0


def cmd_status(args):
    """Show status of runs"""
    storage = WorkflowStorage()

    if args.run:
        # Detailed status for a specific run
        run = storage.get_run(args.run)
        if not run:
            print(f"Run not found: {args.run}")
            return 1

        steps = storage.get_step_executions(args.run)

        print(f"Run ID:       {run['run_id']}")
        print(f"Workflow ID:  {run['workflow_id']}")
        print(f"Status:       {run['status']}")
        print(f"Started:      {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(run['started_at']/1000))}")
        if run.get("completed_at"):
            print(f"Completed:    {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(run['completed_at']/1000))}")
            duration = (run["completed_at"] - run["started_at"]) / 1000
            print(f"Duration:     {duration:.1f}s")
        print(f"Goal:         {run.get('goal', 'N/A')}")
        if run.get("error_message"):
            print(f"Error:        {run['error_message']}")

        print(f"\nSteps ({len(steps)}):")
        print(f"  {'Step ID':<20} {'Name':<25} {'Status':<12} {'Duration':<10}")
        print("  " + "-" * 80)
        for step in steps:
            duration = step.get("duration_ms", 0) / 1000 if step.get("duration_ms") else 0
            print(f"  {step['step_id']:<20} {step.get('step_name', 'N/A'):<25} {step['status']:<12} {duration:>8.3f}s")
            if step.get("error_message"):
                print(f"    ERROR: {step['error_message']}")

    elif args.workflow:
        # List runs for a workflow
        runs = storage.list_runs(workflow_id=args.workflow, limit=args.limit)
        if not runs:
            print(f"No runs found for workflow: {args.workflow}")
            return 0

        print(f"Runs for workflow '{args.workflow}':")
        print(f"  {'Run ID':<30} {'Status':<12} {'Started':<20} {'Duration':<10}")
        print("  " + "-" * 80)
        for run in runs:
            started = time.strftime("%m-%d %H:%M", time.localtime(run["started_at"]/1000))
            duration = "N/A"
            if run.get("completed_at"):
                dur = (run["completed_at"] - run["started_at"]) / 1000
                duration = f"{dur:.1f}s"
            print(f"  {run['run_id']:<30} {run['status']:<12} {started:<20} {duration:<10}")
    else:
        # List recent runs across all workflows
        runs = storage.list_runs(limit=args.limit)
        if not runs:
            print("No workflow runs found")
            return 0

        print("Recent runs (most recent first):")
        print(f"  {'Run ID':<30} {'Workflow':<25} {'Status':<12} {'Started':<20}")
        print("  " + "-" * 80)
        for run in runs:
            started = time.strftime("%m-%d %H:%M", time.localtime(run["started_at"]/1000))
            print(f"  {run['run_id']:<30} {run['workflow_id'][:25]:<25} {run['status']:<12} {started:<20}")

    return 0


def cmd_stop(args):
    """Stop a running workflow"""
    storage = WorkflowStorage()
    engine = WorkflowEngine(storage)

    if engine.stop_run(args.run_id, args.reason):
        print(f"Stop requested for run: {args.run_id}")
        return 0
    print(f"Could not stop run: {args.run_id} (not running or not found)")
    return 1


def cmd_monitor(args):
    """Show monitoring dashboard"""
    storage = WorkflowStorage()
    engine = WorkflowEngine(storage)
    monitor = WorkflowMonitor(storage, engine)

    # Refresh metrics if requested
    if args.refresh:
        monitor._refresh_metrics()

    dashboard = monitor.get_dashboard_data()

    # Display dashboard
    print("=" * 80)
    print(" WORKFLOW MONITOR DASHBOARD")
    print("=" * 80)

    metrics = dashboard["metrics"]
    print("\n📊 Metrics:")
    print(f"  Total Runs:           {metrics['runs']['total']}")
    print(f"  Active Now:           {metrics['runs']['active']}")
    print(f"  Completed:            {metrics['runs']['completed']}")
    print(f"  Failed:               {metrics['runs']['failed']}")
    print(f"  Avg Duration:         {metrics['performance']['avg_duration_sec']:.1f}s")
    print(f"  Throughput (1h avg):  {metrics['performance']['throughput_per_minute']:.1f}/min")

    print("\n🏃 Active Runs:")
    active = dashboard["active_runs"]
    if active:
        for run in active:
            elapsed = time.time() - run["elapsed_sec"]
            print(f"  • {run['run_id'][:20]}...  {run['workflow_name']}  (current: {run['current_step']}, elapsed: {elapsed:.1f}s)")
    else:
        print("  None")

    print("\n📈 Top Workflows (last 24h):")
    top = dashboard["top_workflows"]
    if top:
        for wf in top[:5]:
            print(f"  • {wf['workflow_id']:<30} runs: {wf['runs']:>4}  success: {wf['success_rate']*100:>5.1f}%")
    else:
        print("  None")

    if args.detailed:
        print("\n📋 Recent Runs:")
        recent = dashboard["recent_runs"][:10]
        for run in recent:
            status_icon = {"completed": "✅", "failed": "❌", "running": "🔄", "cancelled": "⏹️"}.get(run["status"], "?")
            print(f"  {status_icon} {run['run_id'][:20]}...  {run['workflow_id'][:20]:<20} {run['status']}")

    print("\n" + "=" * 80)
    return 0


def cmd_create(args):
    """Create a workflow from a definition file"""
    try:
        with open(args.definition_file) as f:
            content = f.read()

        # Parse based on file extension
        if args.definition_file.endswith(".json"):
            definition = json.loads(content)
        elif args.definition_file.endswith((".yaml", ".yml")):
            definition = yaml.safe_load(content)
        else:
            raise ValueError("File must be .json, .yaml, or .yml")

        workflow = WorkflowBuilder.from_dict(definition)
        storage = WorkflowStorage()
        storage.save_workflow(workflow)

        print(f"Created workflow: {workflow.id}")
        print(f"Name: {workflow.name}")
        print(f"Steps: {len(workflow.steps)}")

        # Validate
        errors = workflow.validate()
        if errors:
            print("\nValidation warnings:")
            for err in errors:
                print(f"  • {err}")
        else:
            print("Validation: OK")

        return 0
    except Exception as e:
        print(f"Error creating workflow: {e}", file=sys.stderr)
        return 1


def main():
    parser = argparse.ArgumentParser(
        description="Workflow Engine CLI",
        prog="workflow-cli",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s run my_workflow --var input=data.csv --wait
  %(prog)s list --active
  %(prog)s status --run abc123
  %(prog)s stop abc123 --reason "Timeout"
  %(prog)s monitor
  %(prog)s create my_workflow.yaml
        """
    )
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # run
    run_parser = subparsers.add_parser("run", help="Run a workflow")
    run_parser.add_argument("workflow_id", help="ID of the workflow to run")
    run_parser.add_argument("--var", action="append", default=[], help="Variables: KEY=VALUE (JSON parse if possible)")
    run_parser.add_argument("--goal", help="Goal/description for this run")
    run_parser.add_argument("--wait", action="store_true", help="Wait for completion")
    run_parser.set_defaults(func=cmd_run)

    # list
    list_parser = subparsers.add_parser("list", help="List workflows")
    list_parser.add_argument("--all", action="store_true", help="Show all workflows including inactive")
    list_parser.add_argument("--tag", help="Filter by tag")
    list_parser.set_defaults(func=cmd_list)

    # status
    status_parser = subparsers.add_parser("status", help="Show status")
    status_group = status_parser.add_mutually_exclusive_group()
    status_group.add_argument("--run", help="Show details for a specific run")
    status_group.add_argument("--workflow", help="Show runs for a specific workflow")
    status_parser.add_argument("--limit", type=int, default=20, help="Max number of runs to show")
    status_parser.set_defaults(func=cmd_status)

    # stop
    stop_parser = subparsers.add_parser("stop", help="Stop a running workflow")
    stop_parser.add_argument("run_id", help="Run ID to stop")
    stop_parser.add_argument("--reason", default="Manual stop", help="Reason for stopping")
    stop_parser.set_defaults(func=cmd_stop)

    # monitor
    monitor_parser = subparsers.add_parser("monitor", help="Show monitoring dashboard")
    monitor_parser.add_argument("--refresh", action="store_true", help="Force refresh metrics")
    monitor_parser.add_argument("--detailed", action="store_true", help="Show more details")
    monitor_parser.set_defaults(func=cmd_monitor)

    # create
    create_parser = subparsers.add_parser("create", help="Create workflow from file")
    create_parser.add_argument("definition_file", help="Path to workflow definition (YAML/JSON)")
    create_parser.set_defaults(func=cmd_create)

    # Parse arguments
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Run the command
    try:
        return args.func(args)
    except KeyboardInterrupt:
        print("\nInterrupted")
        return 130
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
