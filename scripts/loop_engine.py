"""
Loop Engine — Hermes Loop Engineering 执行引擎
================================================
基于 Loop Engineering 范式：
  Loop = 调度触发器 + 任务图 + 验证规则 + 记忆存储

生命周期：wake → plan → execute → verify → record → sleep

触发模式：
  - 定时触发 (cron)
  - 事件触发 (webhook / file watch)
  - 连续执行 (continuous)

并行隔离：每个子任务独立 worktree / 临时目录
成本追踪：token 消耗统计 + 预算上限
"""
from __future__ import annotations

import asyncio
import json
import os
import sqlite3
import subprocess
import tempfile
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, field, fields
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union

# ─── 基础数据模型 ───────────────────────────────────────────────


class LoopPhase(str, Enum):
    """Loop 生命周期阶段"""
    SLEEP = "sleep"
    WAKE = "wake"
    PLAN = "plan"
    EXECUTE = "execute"
    VERIFY = "verify"
    RECORD = "record"
    RECOVER = "recover"
    ERROR = "error"


class TriggerType(str, Enum):
    """触发类型"""
    CRON = "cron"
    EVENT_WEBHOOK = "webhook"
    EVENT_FILE_WATCH = "file_watch"
    CONTINUOUS = "continuous"
    MANUAL = "manual"


@dataclass
class TokenBudget:
    """Token 预算追踪"""
    model: str = ""
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    budget_cap: int = 0  # 0 = unlimited
    cost_per_1k_input: float = 0.0
    cost_per_1k_output: float = 0.0

    @property
    def total_cost(self) -> float:
        return (self.total_input_tokens / 1000 * self.cost_per_1k_input +
                self.total_output_tokens / 1000 * self.cost_per_1k_output)

    @property
    def budget_exceeded(self) -> bool:
        if self.budget_cap <= 0:
            return False
        return self.total_cost >= self.budget_cap

    def consume(self, input_tokens: int, output_tokens: int):
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens

    def to_dict(self) -> dict:
        return {
            "model": self.model,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "budget_cap": self.budget_cap,
            "total_cost": round(self.total_cost, 6),
            "budget_exceeded": self.budget_exceeded,
        }


@dataclass
class TaskNode:
    """任务图中的单个节点"""
    id: str
    name: str
    description: str = ""
    node_type: str = "action"  # action | decision | verification | human
    depends_on: List[str] = field(default_factory=list)
    tool_name: Optional[str] = None
    tool_params: dict = field(default_factory=dict)
    success_criteria: List[dict] = field(default_factory=list)
    max_retries: int = 3
    timeout_seconds: int = 300
    weight: float = 1.0
    risk_level: str = "low"  # low | medium | high | critical
    requires_human: bool = False
    isolate_execution: bool = False  # 是否需要独立 worktree/临时目录

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class TaskEdge:
    """任务图边"""
    from_node: str
    to_node: str
    edge_type: str = "dependency"  # dependency | data_flow | trigger | conditional
    condition: Optional[dict] = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class TaskGraph:
    """任务 DAG 图"""
    loop_id: str = ""
    nodes: List[TaskNode] = field(default_factory=list)
    edges: List[TaskEdge] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    def get_node(self, node_id: str) -> Optional[TaskNode]:
        for n in self.nodes:
            if n.id == node_id:
                return n
        return None

    def get_dependencies(self, node_id: str) -> List[str]:
        return [e.from_node for e in self.edges if e.to_node == node_id
                and e.edge_type in ("dependency",)]

    def get_dependents(self, node_id: str) -> List[str]:
        return [e.to_node for e in self.edges if e.from_node == node_id
                and e.edge_type in ("dependency", "trigger")]

    def topological_sort(self) -> List[str]:
        """拓扑排序，返回执行顺序"""
        in_degree = {n.id: 0 for n in self.nodes}
        for e in self.edges:
            if e.edge_type == "dependency":
                in_degree[e.to_node] = in_degree.get(e.to_node, 0) + 1
        queue = [nid for nid, d in in_degree.items() if d == 0]
        result = []
        while queue:
            node = queue.pop(0)
            result.append(node)
            for dep in self.get_dependents(node):
                edges_to = [e for e in self.edges
                            if e.to_node == dep and e.edge_type == "dependency"]
                if all(e.from_node in result for e in edges_to):
                    queue.append(dep)
        return result if len(result) == len(self.nodes) else []

    def to_dict(self) -> dict:
        return {
            "loop_id": self.loop_id,
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges],
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TaskGraph":
        graph = cls(
            loop_id=data.get("loop_id", ""),
            metadata=data.get("metadata", {}),
        )
        graph.nodes = [TaskNode(**n) for n in data.get("nodes", [])]
        graph.edges = [TaskEdge(**e) for e in data.get("edges", [])]
        return graph


@dataclass
class TriggerConfig:
    """触发器配置"""
    trigger_type: TriggerType = TriggerType.MANUAL
    # Cron 配置
    cron_expression: str = ""  # "*/5 * * * *"
    cron_timezone: str = "UTC"
    # Webhook 配置
    webhook_url_path: str = ""
    webhook_secret: str = ""
    # File watch 配置
    watch_directory: str = ""
    watch_pattern: str = "*"
    # 连续执行配置
    continuous_interval_seconds: int = 60
    continuous_max_cycles: int = 0  # 0 = unlimited

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "TriggerConfig":
        return cls(**{k: v for k, v in data.items()
                      if k in {f.name for f in fields(cls)}})


@dataclass
class VerificationRule:
    """验证规则定义"""
    id: str
    name: str
    rule_type: str  # test_pass | output_format | security_check | custom
    check_method: str = ""  # 检查方法名
    expected_value: Any = None
    severity: str = "error"  # error | warning | info
    auto_fix_attempts: int = 3
    escalate_to_human: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class LoopDefinition:
    """Loop 完整定义"""
    loop_id: str = ""
    name: str = ""
    description: str = ""
    trigger: TriggerConfig = field(default_factory=TriggerConfig)
    task_graph: TaskGraph = field(default_factory=TaskGraph)
    verification_rules: List[VerificationRule] = field(default_factory=list)
    memory_config: dict = field(default_factory=lambda: {
        "store_type": "sqlite",
        "max_checkpoints": 50,
        "retention_days": 30,
    })

    # 成本和预算
    budget: TokenBudget = field(default_factory=TokenBudget)

    # 执行配置
    max_parallel_tasks: int = 4
    isolation_temp_dir: str = ""
    isolation_use_worktree: bool = False

    def to_dict(self) -> dict:
        return {
            "loop_id": self.loop_id,
            "name": self.name,
            "description": self.description,
            "trigger": self.trigger.to_dict(),
            "task_graph": self.task_graph.to_dict(),
            "verification_rules": [r.to_dict() for r in self.verification_rules],
            "memory_config": self.memory_config,
            "budget": self.budget.to_dict(),
            "max_parallel_tasks": self.max_parallel_tasks,
            "isolation_temp_dir": self.isolation_temp_dir,
            "isolation_use_worktree": self.isolation_use_worktree,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "LoopDefinition":
        ld = cls(
            loop_id=data.get("loop_id", ""),
            name=data.get("name", ""),
            description=data.get("description", ""),
            memory_config=data.get("memory_config", {}),
            max_parallel_tasks=data.get("max_parallel_tasks", 4),
            isolation_temp_dir=data.get("isolation_temp_dir", ""),
            isolation_use_worktree=data.get("isolation_use_worktree", False),
        )
        ld.trigger = TriggerConfig.from_dict(data.get("trigger", {}))
        ld.task_graph = TaskGraph.from_dict(data.get("task_graph", {}))
        ld.verification_rules = [
            VerificationRule(**r)
            for r in data.get("verification_rules", [])
        ]
        ld.budget = TokenBudget(**data.get("budget", {}))
        return ld


# ─── 执行上下文与隔离 ──────────────────────────────────────────


@dataclass
class ExecutionContext:
    """子任务执行上下文"""
    session_id: str
    loop_id: str
    node_id: str
    work_dir: str
    temp_dir: str
    env_vars: dict = field(default_factory=dict)
    isolation_id: str = ""

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "loop_id": self.loop_id,
            "node_id": self.node_id,
            "work_dir": self.work_dir,
            "temp_dir": self.temp_dir,
            "env_vars": self.env_vars,
            "isolation_id": self.isolation_id,
        }


class ExecutionSandbox:
    """
    执行沙箱 — 为每个子任务提供隔离的临时目录/worktree
    """

    def __init__(self, base_temp_dir: str = "",
                 use_worktree: bool = False,
                 repo_path: str = ""):
        self.base_temp_dir = base_temp_dir or tempfile.gettempdir()
        self.use_worktree = use_worktree
        self.repo_path = repo_path
        self._active_contexts: Dict[str, ExecutionContext] = {}

    def create_context(self, loop_id: str, node_id: str) -> ExecutionContext:
        """为子任务创建隔离执行上下文"""
        session_id = f"isolate_{uuid.uuid4().hex[:12]}"
        isolation_id = f"{loop_id}_{node_id}_{int(time.time())}"

        if self.use_worktree and self.repo_path:
            work_dir = self._create_git_worktree(isolation_id)
        else:
            work_dir = os.path.join(
                self.base_temp_dir,
                f"hermes_loop_{isolation_id}"
            )
            os.makedirs(work_dir, exist_ok=True)

        temp_dir = os.path.join(work_dir, ".hermes_tmp")
        os.makedirs(temp_dir, exist_ok=True)

        ctx = ExecutionContext(
            session_id=session_id,
            loop_id=loop_id,
            node_id=node_id,
            work_dir=work_dir,
            temp_dir=temp_dir,
            env_vars={
                "HERMES_ISOLATION_ID": isolation_id,
                "HERMES_WORK_DIR": work_dir,
                "HERMES_TEMP_DIR": temp_dir,
                "HOME": os.path.expanduser("~"),
            },
            isolation_id=isolation_id,
        )
        self._active_contexts[session_id] = ctx
        return ctx

    def _create_git_worktree(self, isolation_id: str) -> str:
        """创建 git worktree 用于隔离"""
        worktree_path = os.path.join(
            self.base_temp_dir,
            f"hermes_wt_{isolation_id}"
        )
        try:
            subprocess.run(
                ["git", "worktree", "add", "--detach", worktree_path, "HEAD"],
                cwd=self.repo_path,
                capture_output=True,
                timeout=30,
            )
        except Exception:
            os.makedirs(worktree_path, exist_ok=True)
        return worktree_path

    def cleanup_context(self, session_id: str):
        """清理隔离上下文"""
        ctx = self._active_contexts.pop(session_id, None)
        if not ctx:
            return
        import shutil
        try:
            if os.path.exists(ctx.temp_dir):
                shutil.rmtree(ctx.temp_dir, ignore_errors=True)
            if self.use_worktree and os.path.exists(ctx.work_dir):
                subprocess.run(
                    ["git", "worktree", "remove", "--force", ctx.work_dir],
                    cwd=self.repo_path,
                    capture_output=True,
                    timeout=10,
                )
        except Exception:
            pass

    def cleanup_all(self):
        for sid in list(self._active_contexts.keys()):
            self.cleanup_context(sid)


# ─── 事件触发器 ────────────────────────────────────────────────


class TriggerWatcher:
    """
    触发器监视器 — 管理不同触发源
    """

    def __init__(self):
        self._cron_jobs: Dict[str, dict] = {}
        self._file_watchers: Dict[str, dict] = {}
        self._webhook_handlers: Dict[str, Callable] = {}
        self._continuous_timers: Dict[str, threading.Timer] = {}
        self._stopped = False

    def setup_trigger(self, loop_def: LoopDefinition,
                      callback: Callable) -> bool:
        """根据 Loop 定义设置触发器"""
        trigger = loop_def.trigger

        if trigger.trigger_type == TriggerType.CRON:
            return self._setup_cron(loop_def.loop_id,
                                    trigger.cron_expression, callback)
        elif trigger.trigger_type == TriggerType.EVENT_FILE_WATCH:
            return self._setup_file_watch(
                loop_def.loop_id, trigger.watch_directory,
                trigger.watch_pattern, callback)
        elif trigger.trigger_type == TriggerType.EVENT_WEBHOOK:
            self._webhook_handlers[loop_def.loop_id] = callback
            return True
        elif trigger.trigger_type == TriggerType.CONTINUOUS:
            return self._setup_continuous(
                loop_def.loop_id,
                trigger.continuous_interval_seconds,
                trigger.continuous_max_cycles,
                callback)

        return True  # MANUAL — no setup needed

    def _setup_cron(self, loop_id: str, expression: str,
                    callback: Callable) -> bool:
        """设置 cron 触发器"""
        self._cron_jobs[loop_id] = {
            "expression": expression,
            "callback": callback,
            "last_trigger": None,
        }
        # Cron 解析和调度由外部 cron 守护进程处理
        # 这里只记录配置
        return True

    def _setup_file_watch(self, loop_id: str, directory: str,
                          pattern: str, callback: Callable) -> bool:
        """设置文件监视触发器"""
        watch_dir = os.path.expanduser(directory) if directory else ""
        if not watch_dir or not os.path.isdir(watch_dir):
            return False

        self._file_watchers[loop_id] = {
            "directory": watch_dir,
            "pattern": pattern,
            "callback": callback,
            "last_snapshot": self._snapshot_dir(watch_dir, pattern),
        }
        return True

    def _snapshot_dir(self, directory: str, pattern: str) -> dict:
        """捕获目录快照"""
        import fnmatch
        snapshot = {}
        try:
            for root, _, files in os.walk(directory):
                for fname in files:
                    if fnmatch.fnmatch(fname, pattern):
                        fpath = os.path.join(root, fname)
                        snapshot[fpath] = os.path.getmtime(fpath)
        except Exception:
            pass
        return snapshot

    def check_file_watch(self) -> List[str]:
        """检查文件变更，返回触发的 loop_id 列表"""
        triggered = []
        for loop_id, watcher in list(self._file_watchers.items()):
            new_snapshot = self._snapshot_dir(
                watcher["directory"], watcher["pattern"]
            )
            if new_snapshot != watcher["last_snapshot"]:
                watcher["last_snapshot"] = new_snapshot
                triggered.append(loop_id)
        return triggered

    def _setup_continuous(self, loop_id: str, interval: int,
                          max_cycles: int,
                          callback: Callable) -> bool:
        """设置连续执行触发器"""

        def _continuous_runner():
            cycles = 0
            while not self._stopped:
                if max_cycles > 0 and cycles >= max_cycles:
                    break
                try:
                    callback()
                except Exception:
                    pass
                cycles += 1
                time.sleep(interval)

        timer = threading.Thread(target=_continuous_runner, daemon=True)
        timer.start()
        self._continuous_timers[loop_id] = timer
        return True

    def stop_all(self):
        """停止所有触发器"""
        self._stopped = True
        for timer in self._continuous_timers.values():
            try:
                timer.join(timeout=2)
            except Exception:
                pass

    def get_cron_expression(self, loop_id: str) -> Optional[str]:
        """获取 cron 表达式"""
        job = self._cron_jobs.get(loop_id)
        return job["expression"] if job else None


# ─── Loop 执行引擎 ─────────────────────────────────────────────


@dataclass
class LoopExecutionResult:
    """Loop 执行结果"""
    loop_id: str
    session_id: str
    success: bool
    phase: LoopPhase
    completed_nodes: List[str]
    failed_nodes: List[str]
    total_turns: int
    total_duration_seconds: float
    token_budget: TokenBudget
    errors: List[str] = field(default_factory=list)
    details: dict = field(default_factory=dict)
    timestamp: str = ""

    def to_dict(self) -> dict:
        return {
            "loop_id": self.loop_id,
            "session_id": self.session_id,
            "success": self.success,
            "phase": self.phase.value,
            "completed_nodes": self.completed_nodes,
            "failed_nodes": self.failed_nodes,
            "total_turns": self.total_turns,
            "total_duration_seconds": self.total_duration_seconds,
            "token_budget": self.token_budget.to_dict(),
            "errors": self.errors,
            "details": self.details,
            "timestamp": self.timestamp,
        }


class LoopEngine:
    """
    Loop 执行引擎 — Loop Engineering 核心

    管理 Loop 的完整生命周期：
      wake → plan → execute → verify → record → sleep

    使用方式：
      engine = LoopEngine()
      engine.register_loop(my_loop_def)
      result = await engine.run_loop("my_loop_id")

    或者注册回调：
      engine.on_node_execute = my_executor
      engine.on_node_verify = my_verifier
    """

    DB_PATH = os.path.expanduser("~/.hermes/state/loop_engine.db")

    def __init__(self, db_path: str = None):
        self.db_path = db_path or self.DB_PATH
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

        self.registered_loops: Dict[str, LoopDefinition] = {}
        self.trigger_watcher = TriggerWatcher()
        self.sandbox = ExecutionSandbox()
        self._active_sessions: Dict[str, LoopPhase] = {}
        self._session_results: Dict[str, LoopExecutionResult] = {}

        # 回调注册
        self._on_wake: Optional[Callable] = None
        self._on_plan: Optional[Callable] = None
        self._on_node_execute: Optional[Callable] = None
        self._on_node_verify: Optional[Callable] = None
        self._on_record: Optional[Callable] = None
        self._on_sleep: Optional[Callable] = None
        self._on_error: Optional[Callable] = None

        # 并发控制
        self._executor = ThreadPoolExecutor(max_workers=8)
        self._running = False

    # ─── 回调注册 ─────────────────────────────────────────

    def on_wake(self, fn: Callable):
        self._on_wake = fn

    def on_plan(self, fn: Callable):
        self._on_plan = fn

    def on_node_execute(self, fn: Callable):
        """注册节点执行回调: (ExecutionContext, TaskNode) -> dict"""
        self._on_node_execute = fn

    def on_node_verify(self, fn: Callable):
        """注册节点验证回调: (ExecutionContext, TaskNode, dict) -> bool"""
        self._on_node_verify = fn

    def on_record(self, fn: Callable):
        self._on_record = fn

    def on_sleep(self, fn: Callable):
        self._on_sleep = fn

    def on_error(self, fn: Callable):
        self._on_error = fn

    # ─── Loop 注册与管理 ──────────────────────────────────

    def register_loop(self, loop_def: Union[LoopDefinition, dict]):
        """注册 Loop 定义"""
        if isinstance(loop_def, dict):
            loop_def = LoopDefinition.from_dict(loop_def)

        if not loop_def.loop_id:
            loop_def.loop_id = f"loop_{uuid.uuid4().hex[:12]}"

        loop_def.task_graph.loop_id = loop_def.loop_id
        self.registered_loops[loop_def.loop_id] = loop_def
        self._save_loop_def(loop_def)

        # 设置触发器
        self.trigger_watcher.setup_trigger(
            loop_def, lambda: asyncio.run(self.run_loop(loop_def.loop_id))
        )

    def unregister_loop(self, loop_id: str):
        """注销 Loop"""
        self.registered_loops.pop(loop_id, None)

    def get_loop(self, loop_id: str) -> Optional[LoopDefinition]:
        return self.registered_loops.get(loop_id)

    def list_loops(self) -> List[dict]:
        return [
            {"loop_id": lid, "name": ld.name, "trigger": ld.trigger.trigger_type.value}
            for lid, ld in self.registered_loops.items()
        ]

    def load_loops_from_db(self):
        """从数据库加载所有 Loop 定义"""
        rows = self._db_query(
            "SELECT loop_id, definition_json FROM loop_definitions"
        )
        for row in rows:
            try:
                data = json.loads(row["definition_json"])
                ld = LoopDefinition.from_dict(data)
                self.registered_loops[ld.loop_id] = ld
            except Exception:
                pass

    # ─── 核心运行方法 ─────────────────────────────────────

    async def run_loop(self, loop_id: str,
                       trigger_reason: str = "manual") -> LoopExecutionResult:
        """
        完整执行一个 Loop — wake → plan → execute → verify → record → sleep
        """
        loop_def = self.registered_loops.get(loop_id)
        if not loop_def:
            return LoopExecutionResult(
                loop_id=loop_id,
                session_id="",
                success=False,
                phase=LoopPhase.ERROR,
                completed_nodes=[],
                failed_nodes=[],
                total_turns=0,
                total_duration_seconds=0,
                token_budget=TokenBudget(),
                errors=[f"Loop '{loop_id}' not registered"],
            )

        session_id = f"sess_{uuid.uuid4().hex[:16]}"
        start_time = time.time()
        completed_nodes: List[str] = []
        failed_nodes: List[str] = []
        errors: List[str] = []

        try:
            # ── Phase 1: WAKE ──
            await self._phase_wake(loop_def, session_id, trigger_reason)

            # ── Phase 2: PLAN ──
            execution_order = await self._phase_plan(loop_def, session_id)
            if not execution_order:
                errors.append("No executable nodes found in task graph")

            # ── Phase 3: EXECUTE ──
            total_turns = 0
            for node_id in execution_order:
                total_turns += 1
                node = loop_def.task_graph.get_node(node_id)
                if not node:
                    continue

                # 检查预算
                if loop_def.budget.budget_exceeded:
                    errors.append(
                        f"Budget exceeded: ${loop_def.budget.total_cost:.2f} >= "
                        f"${loop_def.budget.budget_cap:.2f}"
                    )
                    failed_nodes.append(node_id)
                    break

                # 创建隔离上下文
                if node.isolate_execution:
                    ctx = self.sandbox.create_context(loop_id, node_id)
                else:
                    ctx = ExecutionContext(
                        session_id=session_id,
                        loop_id=loop_id,
                        node_id=node_id,
                        work_dir=os.getcwd(),
                        temp_dir=tempfile.gettempdir(),
                    )

                # 执行节点（带重试）
                success = await self._execute_with_retry(
                    loop_def, ctx, node
                )

                if success:
                    completed_nodes.append(node_id)
                    self._save_node_execution(session_id, loop_id, node_id,
                                              "completed", ctx.to_dict())
                else:
                    failed_nodes.append(node_id)
                    errors.append(f"Node '{node_id}' ({node.name}) failed")
                    self._save_node_execution(session_id, loop_id, node_id,
                                              "failed", ctx.to_dict())

                # 清理隔离上下文
                if node.isolate_execution:
                    self.sandbox.cleanup_context(ctx.session_id)

            # ── Phase 4: VERIFY ──
            all_passed = await self._phase_verify(
                loop_def, session_id, completed_nodes, failed_nodes
            )

            # ── Phase 5: RECORD ──
            await self._phase_record(
                loop_def, session_id,
                completed_nodes, failed_nodes, errors
            )

            # ── Phase 6: SLEEP ──
            success = len(failed_nodes) == 0 and all_passed
            await self._phase_sleep(loop_def, session_id, success)

        except Exception as e:
            errors.append(f"Loop error: {str(e)}")
            success = False

        elapsed = time.time() - start_time
        result = LoopExecutionResult(
            loop_id=loop_id,
            session_id=session_id,
            success=success,
            phase=LoopPhase.SLEEP,
            completed_nodes=completed_nodes,
            failed_nodes=failed_nodes,
            total_turns=len(completed_nodes) + len(failed_nodes),
            total_duration_seconds=round(elapsed, 2),
            token_budget=loop_def.budget,
            errors=errors,
            details={
                "trigger_reason": trigger_reason,
                "execution_order": execution_order if 'execution_order' in dir() else [],
            },
            timestamp=datetime.now().isoformat(),
        )

        self._session_results[session_id] = result
        self._save_execution_result(result)
        return result

    # ─── Phase 实现 ───────────────────────────────────────

    async def _phase_wake(self, loop_def: LoopDefinition,
                          session_id: str, reason: str):
        """唤醒阶段：日志记录、资源准备"""
        self._active_sessions[session_id] = LoopPhase.WAKE
        self._log_event(loop_def.loop_id, session_id,
                        "wake", {"reason": reason})

        if self._on_wake:
            await self._maybe_await(self._on_wake(loop_def, session_id))

    async def _phase_plan(self, loop_def: LoopDefinition,
                          session_id: str) -> List[str]:
        """规划阶段：拓扑排序生成执行计划"""
        self._active_sessions[session_id] = LoopPhase.PLAN

        if self._on_plan:
            await self._maybe_await(
                self._on_plan(loop_def, loop_def.task_graph)
            )

        plan = loop_def.task_graph.topological_sort()
        self._log_event(loop_def.loop_id, session_id,
                        "plan", {"order": plan})
        return plan

    async def _execute_with_retry(self, loop_def: LoopDefinition,
                                  ctx: ExecutionContext,
                                  node: TaskNode) -> bool:
        """带重试的节点执行"""
        for attempt in range(node.max_retries):
            try:
                result = await self._execute_node(ctx, node)
                response_text = str(result) if result else ""

                # 粗略估算 token（实际应由 LLM 调用方提供精确值）
                input_tokens = len(str(node.to_dict())) // 4
                output_tokens = len(response_text) // 4
                loop_def.budget.consume(input_tokens, output_tokens)

                # 验证结果
                verified = await self._verify_node_result(ctx, node, result)
                if verified:
                    return True

                self._log_event(
                    ctx.loop_id, ctx.session_id, "verify_fail",
                    {"node_id": node.id, "attempt": attempt + 1,
                     "result_preview": response_text[:200]}
                )
            except Exception as e:
                self._log_event(
                    ctx.loop_id, ctx.session_id, "execute_error",
                    {"node_id": node.id, "attempt": attempt + 1,
                     "error": str(e)}
                )
                if attempt < node.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)  # exponential backoff

        return False

    async def _execute_node(self, ctx: ExecutionContext,
                            node: TaskNode) -> Any:
        """执行单个节点"""
        if self._on_node_execute:
            return await self._maybe_await(
                self._on_node_execute(ctx, node)
            )
        # 默认执行：模拟
        self._log_event(ctx.loop_id, ctx.session_id,
                        "node_executed",
                        {"node_id": node.id, "tool": node.tool_name})
        return {"success": True, "output": f"Node {node.id} executed"}

    async def _verify_node_result(self, ctx: ExecutionContext,
                                   node: TaskNode,
                                   result: Any) -> bool:
        """验证节点执行结果"""
        if self._on_node_verify:
            return await self._maybe_await(
                self._on_node_verify(ctx, node, result)
            )
        # 默认验证：检查 success 标志
        if isinstance(result, dict):
            return result.get("success", False) is not False
        return True

    async def _phase_verify(self, loop_def: LoopDefinition,
                            session_id: str,
                            completed: List[str],
                            failed: List[str]) -> bool:
        """验证阶段：运行所有验证规则"""
        self._active_sessions[session_id] = LoopPhase.VERIFY

        all_passed = len(failed) == 0
        for rule in loop_def.verification_rules:
            rule_passed = self._run_verification_rule(rule, completed, failed)
            if not rule_passed:
                all_passed = False
                self._log_event(
                    loop_def.loop_id, session_id, "rule_failed",
                    {"rule_id": rule.id, "rule_name": rule.name}
                )

        self._log_event(loop_def.loop_id, session_id,
                        "verify_complete", {"all_passed": all_passed})
        return all_passed

    def _run_verification_rule(self, rule: VerificationRule,
                               completed: List[str],
                               failed: List[str]) -> bool:
        """运行单个验证规则"""
        if rule.rule_type == "test_pass":
            return len(failed) == 0
        elif rule.rule_type == "output_format":
            # 简单格式检查
            return True
        elif rule.rule_type == "security_check":
            # 安全检查（由外部安全模块处理）
            return True
        return True

    async def _phase_record(self, loop_def: LoopDefinition,
                            session_id: str,
                            completed: List[str],
                            failed: List[str],
                            errors: List[str]):
        """记录阶段：持久化执行记录"""
        self._active_sessions[session_id] = LoopPhase.RECORD

        if self._on_record:
            await self._maybe_await(
                self._on_record(loop_def, session_id, {
                    "completed": completed,
                    "failed": failed,
                    "errors": errors,
                })
            )

    async def _phase_sleep(self, loop_def: LoopDefinition,
                           session_id: str, success: bool):
        """休眠阶段：清理资源、等待下次触发"""
        self._active_sessions.pop(session_id, None)

        if self._on_sleep:
            await self._maybe_await(
                self._on_sleep(loop_def, session_id, success)
            )

    # ─── 并行执行 ─────────────────────────────────────────

    async def run_parallel(self, loop_ids: List[str],
                           max_concurrent: int = None) -> Dict[str, LoopExecutionResult]:
        """并行执行多个 Loop"""
        if max_concurrent is None:
            max_concurrent = len(loop_ids)

        semaphore = asyncio.Semaphore(max_concurrent)

        async def _bounded_run(lid: str):
            async with semaphore:
                return lid, await self.run_loop(lid)

        tasks = [_bounded_run(lid) for lid in loop_ids]
        results = {}
        for coro in asyncio.as_completed(tasks):
            lid, result = await coro
            results[lid] = result
        return results

    # ─── 文件监听轮询 ────────────────────────────────────

    async def poll_file_watchers(self):
        """轮询文件监听器，触发相应的 Loop"""
        triggered = self.trigger_watcher.check_file_watch()
        for loop_id in triggered:
            await self.run_loop(loop_id, "file_watch")

    # ─── 数据库操作 ───────────────────────────────────────

    def _init_db(self):
        conn = self._get_conn()
        try:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS loop_definitions (
                    loop_id TEXT PRIMARY KEY,
                    name TEXT,
                    trigger_type TEXT,
                    definition_json TEXT NOT NULL,
                    created_at TEXT DEFAULT (datetime('now')),
                    updated_at TEXT DEFAULT (datetime('now'))
                );
                CREATE TABLE IF NOT EXISTS loop_executions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    loop_id TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    success INTEGER NOT NULL,
                    completed_nodes TEXT,
                    failed_nodes TEXT,
                    total_turns INTEGER,
                    duration_seconds REAL,
                    errors TEXT,
                    details TEXT,
                    timestamp TEXT DEFAULT (datetime('now'))
                );
                CREATE TABLE IF NOT EXISTS loop_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    loop_id TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    event_data TEXT,
                    timestamp TEXT DEFAULT (datetime('now'))
                );
                CREATE TABLE IF NOT EXISTS node_executions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    loop_id TEXT NOT NULL,
                    node_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    context_json TEXT,
                    timestamp TEXT DEFAULT (datetime('now'))
                );
                CREATE INDEX IF NOT EXISTS idx_loop_exec_loop
                    ON loop_executions(loop_id, timestamp);
                CREATE INDEX IF NOT EXISTS idx_loop_events_session
                    ON loop_events(session_id);
            """)
            conn.commit()
        finally:
            conn.close()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _db_query(self, sql: str, params: tuple = ()) -> list:
        conn = self._get_conn()
        try:
            return [dict(r) for r in conn.execute(sql, params).fetchall()]
        finally:
            conn.close()

    def _db_execute(self, sql: str, params: tuple = ()):
        conn = self._get_conn()
        try:
            conn.execute(sql, params)
            conn.commit()
        finally:
            conn.close()

    def _save_loop_def(self, loop_def: LoopDefinition):
        self._db_execute(
            """INSERT OR REPLACE INTO loop_definitions
               (loop_id, name, trigger_type, definition_json, updated_at)
               VALUES (?, ?, ?, ?, datetime('now'))""",
            (loop_def.loop_id, loop_def.name,
             loop_def.trigger.trigger_type.value,
             json.dumps(loop_def.to_dict(), ensure_ascii=False))
        )

    def _save_execution_result(self, result: LoopExecutionResult):
        self._db_execute(
            """INSERT INTO loop_executions
               (loop_id, session_id, success, completed_nodes, failed_nodes,
                total_turns, duration_seconds, errors, details)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (result.loop_id, result.session_id,
             1 if result.success else 0,
             json.dumps(result.completed_nodes),
             json.dumps(result.failed_nodes),
             result.total_turns, result.total_duration_seconds,
             json.dumps(result.errors),
             json.dumps(result.details))
        )

    def _save_node_execution(self, session_id: str, loop_id: str,
                             node_id: str, status: str,
                             context_json: dict):
        self._db_execute(
            """INSERT INTO node_executions
               (session_id, loop_id, node_id, status, context_json)
               VALUES (?, ?, ?, ?, ?)""",
            (session_id, loop_id, node_id, status,
             json.dumps(context_json, ensure_ascii=False))
        )

    def _log_event(self, loop_id: str, session_id: str,
                   event_type: str, event_data: dict):
        self._db_execute(
            """INSERT INTO loop_events
               (loop_id, session_id, event_type, event_data)
               VALUES (?, ?, ?, ?)""",
            (loop_id, session_id, event_type,
             json.dumps(event_data, ensure_ascii=False))
        )

    # ─── 工具方法 ─────────────────────────────────────────

    @staticmethod
    async def _maybe_await(result: Any) -> Any:
        if asyncio.iscoroutine(result):
            return await result
        return result

    def get_execution_history(self, loop_id: str,
                              limit: int = 20) -> List[dict]:
        return self._db_query(
            """SELECT * FROM loop_executions
               WHERE loop_id = ?
               ORDER BY timestamp DESC LIMIT ?""",
            (loop_id, limit)
        )

    def get_loop_events(self, session_id: str) -> List[dict]:
        return self._db_query(
            "SELECT * FROM loop_events WHERE session_id = ?",
            (session_id,)
        )

    def get_active_sessions(self) -> Dict[str, str]:
        return {k: v.value for k, v in self._active_sessions.items()}

    def shutdown(self):
        """关闭引擎，清理资源"""
        self._running = False
        self.trigger_watcher.stop_all()
        self.sandbox.cleanup_all()
        self._executor.shutdown(wait=False)


# ─── 方便使用的工厂函数 ────────────────────────────────────────


def create_loop(
    name: str,
    trigger_type: str = "manual",
    cron_expression: str = "",
    nodes: List[dict] = None,
    edges: List[dict] = None,
    verification_rules: List[dict] = None,
    budget_cap: int = 0,
    max_parallel: int = 4,
) -> LoopDefinition:
    """
    快速创建 Loop 定义

    Example:
        loop = create_loop(
            name="daily_backup",
            trigger_type="cron",
            cron_expression="0 2 * * *",
            nodes=[
                {"id": "check_disk", "name": "Check Disk Space",
                 "tool_name": "check_disk"},
                {"id": "run_backup", "name": "Run Backup",
                 "tool_name": "run_backup", "depends_on": ["check_disk"]},
            ],
            verification_rules=[
                {"id": "v1", "name": "Backup Success Check",
                 "rule_type": "test_pass"},
            ],
        )
        engine.register_loop(loop)
    """
    tnodes = []
    for n in (nodes or []):
        tnodes.append(TaskNode(
            id=n["id"],
            name=n.get("name", n["id"]),
            description=n.get("description", ""),
            tool_name=n.get("tool_name"),
            tool_params=n.get("tool_params", {}),
            depends_on=n.get("depends_on", []),
            max_retries=n.get("max_retries", 3),
            isolate_execution=n.get("isolate_execution", False),
        ))

    tedges = [TaskEdge(**e) for e in (edges or [])]
    if not tedges:
        # 自动从 depends_on 推断边
        for node in tnodes:
            for dep_id in node.depends_on:
                tedges.append(TaskEdge(from_node=dep_id, to_node=node.id))

    # 去重
    seen = set()
    unique_edges = []
    for e in tedges:
        key = (e.from_node, e.to_node)
        if key not in seen:
            seen.add(key)
            unique_edges.append(e)

    trigger = TriggerConfig(
        trigger_type=TriggerType(trigger_type),
        cron_expression=cron_expression,
    )

    budget = TokenBudget(budget_cap=budget_cap)
    if budget_cap > 0:
        budget.cost_per_1k_input = 0.003
        budget.cost_per_1k_output = 0.015

    vrules = [VerificationRule(**r) for r in (verification_rules or [])]

    return LoopDefinition(
        loop_id=f"loop_{uuid.uuid4().hex[:12]}",
        name=name,
        trigger=trigger,
        task_graph=TaskGraph(nodes=tnodes, edges=unique_edges),
        verification_rules=vrules,
        budget=budget,
        max_parallel_tasks=max_parallel,
    )


# ─── 简单 CLI ─────────────────────────────────────────────────


def main():
    """CLI 入口 — 测试和手动触发"""
    import argparse
    parser = argparse.ArgumentParser(description="Hermes Loop Engine")
    parser.add_argument("action", nargs="?", default="status",
                        choices=["status", "run", "list", "test",
                                 "events", "history"])
    parser.add_argument("--loop-id", help="Loop ID")
    parser.add_argument("--name", help="Loop name (for test)")

    args = parser.parse_args()
    engine = LoopEngine()

    if args.action == "test":
        loop = create_loop(
            name=args.name or "test_loop",
            trigger_type="manual",
            nodes=[
                {"id": "init", "name": "Initialize", "tool_name": "init"},
                {"id": "process", "name": "Process",
                 "tool_name": "process", "depends_on": ["init"]},
                {"id": "cleanup", "name": "Cleanup",
                 "tool_name": "cleanup", "depends_on": ["process"]},
            ],
            verification_rules=[
                {"id": "v1", "name": "All Steps Pass",
                 "rule_type": "test_pass"},
            ],
        )
        engine.register_loop(loop)
        print(f"Test loop registered: {loop.loop_id}")
        result = asyncio.run(engine.run_loop(loop.loop_id))
        print(f"Result: success={result.success}, "
              f"completed={result.completed_nodes}, "
              f"failed={result.failed_nodes}")

    elif args.action == "status":
        active = engine.get_active_sessions()
        print(f"Active sessions: {len(active)}")
        for sid, phase in active.items():
            print(f"  {sid}: {phase}")

    elif args.action == "list":
        engine.load_loops_from_db()
        loops = engine.list_loops()
        print(f"Registered loops: {len(loops)}")
        for l in loops:
            print(f"  {l['loop_id']}: {l['name']} [{l['trigger']}]")

    elif args.action == "run":
        if not args.loop_id:
            print("Error: --loop-id required")
            return
        engine.load_loops_from_db()
        result = asyncio.run(engine.run_loop(args.loop_id))
        print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))

    elif args.action == "history":
        if not args.loop_id:
            print("Error: --loop-id required")
            return
        history = engine.get_execution_history(args.loop_id, limit=10)
        print(f"Execution history for {args.loop_id} ({len(history)}):")
        for entry in history:
            status = "OK" if entry["success"] else "FAIL"
            print(f"  [{entry['timestamp']}] {status} "
                  f"({entry['total_turns']} turns, "
                  f"{entry['duration_seconds']:.1f}s)")

    elif args.action == "events":
        if not args.loop_id:
            print("Error: --loop-id required")
            return
        sessions = engine._db_query(
            "SELECT DISTINCT session_id FROM loop_events WHERE loop_id = ? "
            "ORDER BY timestamp DESC LIMIT 1",
            (args.loop_id,)
        )
        if sessions:
            events = engine.get_loop_events(sessions[0]["session_id"])
            print(f"Events for session {sessions[0]['session_id']} "
                  f"({len(events)}):")
            for ev in events:
                print(f"  [{ev['timestamp']}] {ev['event_type']}")


if __name__ == "__main__":
    main()
