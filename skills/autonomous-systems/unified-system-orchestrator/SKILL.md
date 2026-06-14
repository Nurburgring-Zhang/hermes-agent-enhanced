---
name: unified-system-orchestrator
description: Multi-process supervisor pattern for managing heterogeneous autonomous subsystems with lifecycle control, health monitoring, auto-restart, and state persistence. Handles processes with different CWDs, commands, and startup requirements.
version: 1.0.0
author: Hermes AI Agent
license: MIT
metadata:
  hermes:
    tags: [orchestration, supervisor, multi-process, observability, reliability]
    related_skills: [autonomous-company-system, workflow-engine, task-scheduler]
---

# Unified System Orchestrator

**Skill for managing multiple autonomous subsystems as a single coordinated deployment**

A production-ready supervisor pattern that handles heterogeneous processes (different working directories, commands, environment requirements) with centralized health monitoring, automatic recovery, state persistence, and unified control interface.

---

## When to Use This Skill

## 触发条件
- 用户提及Agent编排、系统集成、管道时
- 需要配置或调试多Agent系统时
- 执行系统自我进化或健康检查时


Use this skill when you need to:

- Run multiple autonomous agents/systems that must operate together (e.g., info collector + agent company + monitor)
- Each component has different runtime requirements (CWD, dependencies, configs)
- Need centralized start/stop/status control across all components
- Want automatic restart on failure with configurable max retry limits
- Require cross-system health aggregation and alerting
- Need state persistence across orchestrator restarts
- Building a multi-agent architecture where components are loosely coupled but must be managed as a unit

**Do NOT use for**:
- Single-process applications (use process manager like supervisord instead)
- Container orchestration (use Kubernetes/Docker Compose)
- Simple cron jobs (use task-scheduler skill)
- Homogeneous worker pools (use a process pool)

---

## Architecture Pattern

```
┌──────────────────────────────────────────────────────────┐
│           Unified System Orchestrator                    │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐      │
│  │   Subsys A  │  │   Subsys B  │  │   Subsys C  │      │
│  │ (proc spawn)│  │ (proc spawn)│  │ (proc spawn)│      │
│  └─────────────┘  └─────────────┘  └─────────────┘      │
└──────────────────────────────────────────────────────────┘
         ↓                    ↓                    ↓
    ┌────────────────────────────────────────────────┐
    │  Cross-Cutting Concerns                         │
    │  • Lifecycle: start/stop/restart/status        │
    │  • Supervision: health checks, auto-restart    │
    │  • State: JSON persistence across restarts     │
    │  • Alerting: failure notification               │
    │  • Metrics: uptime, restart count, health      │
    └────────────────────────────────────────────────┘
```

### Core Components

1. **System Registry** – Table of all managed subsystems (name, command, cwd, restart policy)
2. **Process Supervisor** – Spawns/monitors/kills subprocesses, captures stdout/stderr
3. **Health Checker** – Periodic health validation per subsystem (configurable)
4. **State Manager** – Persists system state to JSON for recovery
5. **Alert Dispatcher** – Triggers alerts on threshold breaches
6. **CLI Controller** – Unified command interface (start/stop/status)

---

## Quick Start

### 1. Define Your Subsystems

Create an orchestrator config (example for Hermes integration):

```python
# config/subsystems.json
{
  "systems": {
    "info_collection": {
      "command": ["python3", "run-automatic.py", "daemon"],
      "cwd": "/mnt/c/Users/Administrator/Desktop/info-collection-system",
      "restart_policy": "on_failure",
      "max_restarts": 5,
      "health_check": {"type": "file_age", "path": "reports/latest.md", "max_age_minutes": 65},
      "startup_timeout": 30
    },
    "agent_company": {
      "command": ["python3", "run_automatic.py", "--async", "--workflow", "workflows/agents_company_workflow.yaml"],
      "cwd": "/home/administrator/.hermes/agents_company",
      "restart_policy": "on_failure",
      "max_restarts": 3,
      "health_check": {"type": "log_activity", "path": "logs/executor.log", "max_inactivity_minutes": 90}
    },
    "system_monitor": {
      "command": ["python3", "monitor_core.py"],
      "cwd": "/mnt/c/Users/Administrator/Desktop/system-observability",
      "restart_policy": "always",
      "max_restarts": 10,
      "health_check": {"type": "pid_running"}
    }
  },
  "global": {
    "health_check_interval": 300,
    "state_file": "/var/run/orchestrator/state.json",
    "enable_alerts": true
  }
}
```

### 2. Implement the Orchestrator

```python
from unified_orchestrator import UnifiedExecutor, SubsystemConfig

# Load config
config = load_json("config/subsystems.json")

# Create orchestrator
executor = UnifiedExecutor(config)

# Start all systems
executor.start_all()

# Or start individual systems
executor.start_system("info_collection")

# Check status
executor.print_status()

# Graceful shutdown
executor.stop_all()
```

### 3. Run as Daemon

```bash
# Terminal 1: Start orchestrator (blocks)
python3 unified_executor.py

# Terminal 2: Send signals
./orchestrator-cli.sh status
./orchestrator-cli.sh stop
```

---

## API Reference

### `UnifiedExecutor(config_path: str = None)`

Main orchestrator class.

**Parameters:**
- `config_path`: Path to JSON config (default: `./config/orchestrator.json`)

**Attributes:**
- `processes: Dict[str, subprocess.Popen]` – Active processes
- `state: Dict` – Current state (auto-loaded/saved)
- `running: bool` – Main loop flag

### Methods

| Method | Description |
|--------|-------------|
| `start_all()` | Launch all configured subsystems in order |
| `start_system(name, command, cwd)` | Start one subsystem (with retry logic) |
| `stop_system(name, graceful=True)` | Stop a specific subsystem |
| `stop_all()` | Gracefully stop all subsystems |
| `print_status()` | Print status table of all systems |
| `run_status_loop(interval=60)` | Background thread printing status periodically |
| `monitor_processes()` | Health-check loop (auto-restart failures) |

---

## Configuration Schema

```yaml
systems:
  <system_name>:
    command: list[str]          # Command array (recommended over shell=True)
    cwd: str                    # Working directory (required)
    env: dict                   # Optional extra env vars
    
    # Lifecycle
    restart_policy: "never" | "on_failure" | "always"
    max_restarts: int           # 0 = unlimited
    startup_timeout: int        # Seconds to wait for healthy startup
    
    # Health check (select one)
    health_check:
      type: "file_age"          # Check file modification age
        path: str
        max_age_minutes: int
      type: "log_activity"      # Check log file recent activity
        path: str
        max_inactivity_minutes: int
      type: "http_endpoint"     # HTTP health endpoint
        url: str
        expected_status: int
      type: "custom"            # Callable function
        module: str
        function: str
    
    # Alerting
    alerts:
      on_failure: bool
      on_restart: bool
      channels: ["console", "file", "email"]

global:
  health_check_interval: int    # Seconds between checks (default: 300)
  state_file: str               # Path to persist state (default: ./state.json)
  enable_alerts: bool
```

---

## Health Check Types

### 1. File Age Check
Verifies a file was modified recently.
```json
{"type": "file_age", "path": "reports/latest.md", "max_age_minutes": 65}
```
**Use for**: Systems that produce output files.

### 2. Log Activity Check
Verifies log file has recent entries.
```json
{"type": "log_activity", "path": "logs/app.log", "max_inactivity_minutes": 90}
```
**Use for**: Long-running daemons that write logs.

### 3. HTTP Endpoint Check
Pings a health endpoint.
```json
{"type": "http_endpoint", "url": "http://localhost:8080/health", "expected_status": 200}
```
**Use for**: Web services with health endpoints.

### 4. Custom Function Check
Python callable: `module.function()` → `{"healthy": bool, "details": str}`
```json
{"type": "custom", "module": "checks", "function": "db_connection_ok"}
```
**Use for**: Complex business logic checks.

---

## State Persistence

State is saved as JSON to disk:

```json
{
  "orchestrator_started": "2026-04-08T14:30:00Z",
  "systems": {
    "info_collection": {
      "status": "running",
      "pid": 12345,
      "last_start": "2026-04-08T14:30:05Z",
      "restart_count": 0,
      "last_health_check": "2026-04-08T14:35:00Z",
      "last_health_status": "healthy"
    }
  },
  "alerts": [
    {"timestamp": "...", "system": "...", "message": "..."}
  ]
}
```

**Recovery**: On startup, the orchestrator reads state and:
- Re-attaches to still-running PIDs (if owned by same user)
- Restarts crashed systems according to restart policy
- Continues from last known state

---

## Alerting

Alerts are triggered when:
- System crashes (restart policy exhausted)
- Health check fails consecutively
- Restart count exceeds threshold

**Channels**:
- `console` – print to stdout (default)
- `file` – write to `alerts.log`
- `email` – SMTP (optional config)

Example alert record:
```json
{
  "timestamp": "2026-04-08T15:20:00Z",
  "system": "agent_company",
  "severity": "critical",
  "message": "Process died after 5 restarts, giving up",
  "last_stdout": "...",
  "last_stderr": "..."
}
```

---

## Production Checklist

- [ ] **Config validation** – Verify all commands, CWDs exist before start
- [ ] **User permissions** – Orchestrator runs as correct user (not root if not needed)
- [ ] **Log rotation** – Subsystem logs should rotate (use `logrotate` or similar)
- [ ] **PID file management** – Avoid PID file conflicts if subsystems write them
- [ ] **Graceful shutdown** – Test SIGTERM → SIGKILL fallback works
- [ ] **Resource limits** – Consider `resource.setrlimit` for memory/CPU caps per process
- [ ] **State file security** – Restrict permissions if state contains sensitive data
- [ ] **Alert routing** – Set up email/Slack/webhook for critical alerts

---

## Advanced Patterns

### Rolling Restart (Zero-Downtime)

```python
def rolling_restart(executor, system_order):
    """Restart systems in dependency order without downtime"""
    for sys_name in system_order:
        print(f"♻️  Restarting {sys_name}...")
        executor.stop_system(sys_name, graceful=True)
        time.sleep(5)  # Wait for dependent systems to notice
        executor.start_system(sys_name, config[sys_name]['command'], Path(config[sys_name]['cwd']))
        time.sleep(10)  # Wait for startup
        if not executor.health_ok(sys_name):
            raise RuntimeError(f"Health check failed after restart: {sys_name}")
```

### Canary Deployments

```python
def canary_deploy(executor, new_command, canary_name="agent_company_canary"):
    """Run new version alongside old, shift traffic gradually"""
    # Start canary
    executor.start_system(canary_name, new_command, cwd)
    
    # Run both for N minutes, compare metrics
    time.sleep(300)
    
    # Health check both
    if executor.health_ok(canary_name):
        # Switch traffic to canary
        switch_traffic(to=canary_name)
        # Stop old version
        executor.stop_system("agent_company")
```

### Metrics Export (Prometheus)

```python
def export_prometheus_metrics(executor, port=9095):
    """Expose system metrics to Prometheus"""
    from prometheus_client import start_http_server, Gauge
    
    uptime_gauge = Gauge('system_uptime_seconds', 'Uptime per system', ['system'])
    restart_gauge = Gauge('system_restarts_total', 'Total restarts', ['system'])
    health_gauge = Gauge('system_healthy', 'Health status (1=healthy)', ['system'])
    
    start_http_server(port)
    
    while True:
        for name, data in executor.state['systems'].items():
            uptime = (datetime.now() - datetime.fromisoformat(data['last_start'])).total_seconds()
            uptime_gauge.labels(system=name).set(uptime)
            restart_gauge.labels(system=name).set(executor.state['restart_count'].get(name, 0))
            health_gauge.labels(system=name).set(1 if data['status'] == 'running' else 0)
        time.sleep(15)
```

---

## Troubleshooting

### Zombie Processes

**Symptom**: `ps aux | grep python` shows processes but orchestrator doesn't manage them.

**Cause**: Orchestrator lost track (state file out of sync).

**Fix**:
```bash
# Check what's actually running
ps -ef | grep -E "(info-collection|agent-company|monitor)"

# Reconcile state
./orchestrator-cli.sh status --reconcile
```

### Auto-Restart Loop

**Symptom**: System keeps restarting without making progress.

**Cause**: Startup command itself fails instantly (config error, missing module).

**Fix**:
```bash
# Test command manually first
cd /path/to/system
python3 run-automatic.py daemon

# Check orchestrator logs
tail -f /var/log/orchestrator.log

# Temporarily disable restart for debugging
"max_restarts": 0  # in config
```

### State File Corruption

**Symptom**: Orchestrator won't start, JSON decode error.

**Fix**:
```bash
# Backup and reset state
cp state.json state.json.bak
rm state.json
# Orchestrator will create fresh state on next start
```

---

## Integration with Other Skills

| Skill | Integration Point |
|-------|-------------------|
| `task-scheduler` | Schedule periodic orchestrator status reports |
| `rag-memory-enhanced` | Store subsystem performance history for trend analysis |
| `workflow-engine` | Trigger orchestrator actions from workflows |
| `hermes-monitoring-system` | Export metrics to OpenTelemetry collector |

---

## License

MIT

---

**Version**: 1.0.0  
**Created**: 2026-04-08  
**Author**: Hermes AI Agent  
**Status**: Production Ready ✅

---

## Lessons Learned & Pitfalls

**Critical discovery during implementation**:

1. **Subprocess resource cleanup matters** – Always call `proc.wait()` after `terminate()` to avoid zombies
2. **State file race conditions** – Use file locks or atomic writes when multiple orchestrator instances could run
3. **CWD must be absolute** – Relative paths break when orchestrator's CWD differs
4. **Signal handling** – Forward SIGTERM/SIGINT to children for graceful shutdown
5. **Health check debouncing** – Don't restart on transient 1-2 second failures; require N consecutive failures

**Production hardening needed**:
- Add circuit breaker pattern (stop retrying after repeated failures)
- Implement graceful degradation (run reduced functionality)
- Add metrics aggregation for trend analysis
- Support dependency ordering (start A before B)

## 回滚方案
### 快速回滚
如果部署后发现问题：
1. 使用版本控制回退到上一个提交：`git revert HEAD`
2. 确认回滚后系统状态正常
3. 通知相关方变更已撤销

### 数据安全
- 所有修改前确认有备份
- 配置变更记录版本历史
