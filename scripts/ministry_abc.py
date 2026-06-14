"""三省六部ABC抽象基类：含熔断器 + 执行管道 + 角色编排 + 状态机"""

from __future__ import annotations

import asyncio
import time
from abc import ABC
from collections.abc import Awaitable, Callable
from typing import Any

from scripts.ministry_exceptions import (
    CircuitBreakerOpenError,
    RoleAssignmentError,
    WorkflowExecutionError,
)
from scripts.ministry_types import (
    DEFAULT_CIRCUIT_BREAKER_CONFIG,
    CircuitBreakerConfig,
    CircuitState,
    ExecutionMode,
    ExecutionResult,
    ExecutionStatus,
    Ministry,
    RoleDefinition,
    RoutingResult,
    TaskPayload,
    WorkflowDefinition,
    WorkflowState,
    WorkflowTransition,
)

# ── 熔断器 ────────────────────────────────────────────────

class CircuitBreaker:
    """熔断器，防止雪崩效应"""

    def __init__(self, config: CircuitBreakerConfig | None = None) -> None:
        cfg = config or DEFAULT_CIRCUIT_BREAKER_CONFIG
        self._failure_threshold: int = cfg.get("failure_threshold", 5)
        self._recovery_timeout: float = cfg.get("recovery_timeout", 30.0)
        self._half_open_max_requests: int = cfg.get("half_open_max_requests", 1)
        self._success_threshold: int = cfg.get("success_threshold", 2)

        self._state: CircuitState = CircuitState.CLOSED
        self._failure_count: int = 0
        self._success_count: int = 0
        self._last_failure_time: float = 0.0
        self._half_open_requests: int = 0
        self._lock: asyncio.Lock = asyncio.Lock()

    @property
    def state(self) -> CircuitState:
        return self._state

    @property
    def failure_count(self) -> int:
        return self._failure_count

    async def call(self, coro_factory: Callable[[], Awaitable[Any]]) -> Any:
        """受熔断器保护的调用。

        Args:
            coro_factory: 返回一个可等待对象的工厂函数。

        Returns:
            协程的执行结果。

        Raises:
            CircuitBreakerOpenError: 熔断器打开时拒绝执行。
        """
        async with self._lock:
            self._check_state_transition()
            if self._state == CircuitState.OPEN:
                raise CircuitBreakerOpenError(ministry="unknown")

            if self._state == CircuitState.HALF_OPEN:
                if self._half_open_requests >= self._half_open_max_requests:
                    raise CircuitBreakerOpenError(
                        ministry="unknown",
                        message="半开状态请求数已达上限",
                    )
                self._half_open_requests += 1

        try:
            result = await coro_factory()
        except Exception as exc:
            async with self._lock:
                self._on_failure()
            raise exc

        async with self._lock:
            self._on_success()
        return result

    def _check_state_transition(self) -> None:
        """检查是否需要从 OPEN → HALF_OPEN 转换。"""
        if self._state == CircuitState.OPEN:
            elapsed = time.monotonic() - self._last_failure_time
            if elapsed >= self._recovery_timeout:
                self._state = CircuitState.HALF_OPEN
                self._half_open_requests = 0
                self._success_count = 0

    def _on_failure(self) -> None:
        """记录一次失败。"""
        self._failure_count += 1
        self._last_failure_time = time.monotonic()

        if self._state == CircuitState.HALF_OPEN or (self._state == CircuitState.CLOSED and self._failure_count >= self._failure_threshold):
            self._state = CircuitState.OPEN

    def _on_success(self) -> None:
        """记录一次成功。"""
        if self._state == CircuitState.HALF_OPEN:
            self._success_count += 1
            if self._success_count >= self._success_threshold:
                self._state = CircuitState.CLOSED
                self._failure_count = 0
                self._half_open_requests = 0
        elif self._state == CircuitState.CLOSED:
            self._failure_count = 0

    def reset(self) -> None:
        """手动重置为闭合状态。"""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._half_open_requests = 0
        self._last_failure_time = 0.0


# ── 管道阶段类型 ─────────────────────────────────────────

PipelineStage = Callable[[TaskPayload], Awaitable[TaskPayload]]


# ── 抽象六部基类 ──────────────────────────────────────────

class MinistryBase(ABC):
    """所有六部的抽象基类。

    子类只需实现 _execute_impl() 方法，其余流程（熔断、管道、超时）由基类自动处理。
    如果子类不重写 _execute_impl()，则使用默认实现（直接返回 task 的 args 字段）。
    """

    def __init__(
        self,
        ministry_name: str,
        circuit_breaker_config: CircuitBreakerConfig | None = None,
    ) -> None:
        self.ministry_name = ministry_name
        self._circuit_breaker = CircuitBreaker(circuit_breaker_config)
        self._pipeline: list[PipelineStage] = []

    # ── 管道管理 ──────────────────────────────────────────

    def register_pipeline_stage(self, stage: PipelineStage) -> None:
        """注册一个管道阶段。阶段按注册顺序依次执行。"""
        self._pipeline.append(stage)

    def clear_pipeline(self) -> None:
        """清空所有管道阶段。"""
        self._pipeline.clear()

    # ── 模板方法 ──────────────────────────────────────────

    async def execute(self, task: TaskPayload) -> ExecutionResult:
        """模板方法：管道 → 熔断 → 执行 → 返回结果。"""
        task_id = task.get("task_id", "")
        start_time = time.monotonic()

        try:
            processed_task = await self._run_pipeline(task)
            result_data = await self._circuit_breaker.call(
                lambda: self._execute_with_timeout(processed_task)
            )
            duration = time.monotonic() - start_time
            return ExecutionResult(
                status=ExecutionStatus.SUCCESS,
                data=result_data,
                error=None,
                duration_seconds=duration,
                task_id=task_id,
            )
        except CircuitBreakerOpenError:
            duration = time.monotonic() - start_time
            return ExecutionResult(
                status=ExecutionStatus.CIRCUIT_OPEN,
                data=None,
                error="熔断器已打开，拒绝执行",
                duration_seconds=duration,
                task_id=task_id,
            )
        except Exception as exc:
            duration = time.monotonic() - start_time
            return ExecutionResult(
                status=ExecutionStatus.FAILED,
                data=None,
                error=str(exc),
                duration_seconds=duration,
                task_id=task_id,
            )

    async def _run_pipeline(self, task: TaskPayload) -> TaskPayload:
        """依次执行所有已注册的管道阶段。"""
        current: TaskPayload = dict(task)
        for stage in self._pipeline:
            current = await stage(current)
        return current

    async def _execute_with_timeout(self, task: TaskPayload) -> Any:
        """带超时的实际执行包装。"""
        timeout = task.get("timeout_seconds", 30.0)
        try:
            return await asyncio.wait_for(self._execute_impl(task), timeout=timeout)
        except TimeoutError:
            raise TimeoutError(
                f"[{self.ministry_name}] 任务执行超时 ({timeout}s)"
            )

    async def _execute_impl(self, task: TaskPayload) -> Any:
        """默认实现：直接返回 task 中的 args 字段。

        子类可以重写此方法实现具体的业务逻辑。
        默认行为是将 args 原样返回，保证六部至少有一个可工作的实现。
        """
        action: str = task.get("action", "default")
        args: dict[str, Any] = task.get("args", {})
        # 模拟处理延迟（防止空转），实际子类应提供真实逻辑
        await asyncio.sleep(0.01)
        return {
            "action": action,
            "args": args,
            "ministry": self.ministry_name,
            "processed": True,
        }

    def circuit_breaker_reset(self) -> None:
        """手动重置熔断器。"""
        self._circuit_breaker.reset()

    @property
    def circuit_state(self) -> CircuitState:
        return self._circuit_breaker.state


# ── 角色编排器 ── 对标 CrewAI ────────────────────────────

class RoleOrchestrator:
    """角色编排器——对标 CrewAI 的角色编排能力。

    支持角色定义（name, goal, backstory），
    支持部门间任务流转路由，
    支持根据角色智能分配任务到最合适的部门。
    """

    def __init__(self) -> None:
        self._roles: dict[str, RoleDefinition] = {}
        self._ministry_registry: dict[str, MinistryBase] = {}
        self._lock: asyncio.Lock = asyncio.Lock()

    # ── 角色注册 ──────────────────────────────────────────

    def register_role(self, role: RoleDefinition) -> None:
        """注册一个角色。

        Args:
            role: 角色定义，包含 name, goal, backstory, allowed_ministries, priority。
        """
        self._roles[role["name"]] = role

    def register_role_from_args(
        self,
        name: str,
        goal: str,
        backstory: str,
        allowed_ministries: list[str] | None = None,
        priority: int = 10,
    ) -> None:
        """便捷方法：直接传参注册角色。"""
        role: RoleDefinition = {
            "name": name,
            "goal": goal,
            "backstory": backstory,
            "allowed_ministries": allowed_ministries or [m.value for m in Ministry],
            "priority": priority,
        }
        self._roles[name] = role

    def remove_role(self, name: str) -> bool:
        """移除已注册的角色。

        Returns:
            如果角色存在并被移除返回 True，否则返回 False。
        """
        return self._roles.pop(name, None) is not None

    # ── 部门注册 ──────────────────────────────────────────

    def register_ministry(self, ministry: MinistryBase) -> None:
        """注册一个六部实例，供角色编排时调度。"""
        self._ministry_registry[ministry.ministry_name] = ministry

    def register_ministries(self, *ministries: MinistryBase) -> None:
        """批量注册多个六部实例。"""
        for m in ministries:
            self.register_ministry(m)

    def unregister_ministry(self, name: str) -> bool:
        """注销一个六部实例。

        Returns:
            如果实例存在并被注销返回 True，否则返回 False。
        """
        return self._ministry_registry.pop(name, None) is not None

    # ── 角色查询 ──────────────────────────────────────────

    def get_role(self, name: str) -> RoleDefinition | None:
        """根据名称查询角色定义。"""
        return self._roles.get(name)

    def list_roles(self) -> list[RoleDefinition]:
        """列出所有已注册的角色（按优先级排序）。"""
        return sorted(self._roles.values(), key=lambda r: r["priority"])

    def find_role_for_task(self, task: TaskPayload) -> RoleDefinition | None:
        """根据任务内容自动匹配合适的角色。

        匹配策略：
        1. 如果 task 中有 'role' 字段，直接查找该角色
        2. 如果 task 中有 'action' 字段，遍历角色找 goal 包含 action 的
        3. 返回优先级最高的角色

        Args:
            task: 任务载荷。

        Returns:
            匹配到的角色，未匹配则返回 None。
        """
        # 显式指定的角色
        explicit_role: str | None = task.get("role")
        if explicit_role and explicit_role in self._roles:
            return self._roles[explicit_role]

        # 按 action 匹配 goal
        action: str = task.get("action", "")
        candidates: list[RoleDefinition] = []
        for role in self._roles.values():
            if action and action in role["goal"]:
                candidates.append(role)
            elif not action:
                # 无 action 时返回最高优先级角色
                candidates.append(role)

        if not candidates:
            return None
        return min(candidates, key=lambda r: r["priority"])

    # ── 任务路由 ──────────────────────────────────────────

    async def route_task(
        self,
        task: TaskPayload,
        role_name: str | None = None,
    ) -> RoutingResult:
        """将任务路由到最合适的部门。

        流程：
        1. 确定执行角色（显式指定或自动匹配）
        2. 根据角色的 allowed_ministries 筛选可用部门
        3. 从可用部门中选择最合适的一个（按优先级 + 任务类型）
        4. 提交任务执行

        Args:
            task: 任务载荷。
            role_name: 可选，显式指定角色名称。

        Returns:
            路由结果，包含源/目标部门、角色、结果等信息。

        Raises:
            RoleAssignmentError: 角色不存在或没有可用部门。
        """
        # 确定角色
        role: RoleDefinition | None = None
        if role_name:
            role = self._roles.get(role_name)
            if role is None:
                raise RoleAssignmentError(
                    role_name=role_name,
                    task_id=task.get("task_id", ""),
                    reason=f"角色 '{role_name}' 未注册",
                )
        else:
            role = self.find_role_for_task(task)
            if role is None:
                raise RoleAssignmentError(
                    role_name="auto",
                    task_id=task.get("task_id", ""),
                    reason="无法自动匹配合适的角色",
                )
            role_name = role["name"]

        # 筛选可用部门
        allowed: list[str] = role["allowed_ministries"]
        available: dict[str, MinistryBase] = {}
        for name, ministry in self._ministry_registry.items():
            if name in allowed:
                available[name] = ministry

        if not available:
            raise RoleAssignmentError(
                role_name=role_name,
                task_id=task.get("task_id", ""),
                reason=f"角色 '{role_name}' 允许的部门 {allowed} 均未注册",
            )

        # 选择目标部门：优先选择名称与 action 相关的部门
        action: str = task.get("action", "")
        target_ministry: MinistryBase | None = None

        for name, ministry in available.items():
            if action and any(keyword in name for keyword in action.split("_")):
                target_ministry = ministry
                break

        if target_ministry is None:
            # 无精确匹配时选第一个
            target_ministry = next(iter(available.values()))

        # 执行任务
        source: str = task.get("source_ministry", "orchestrator")
        result: ExecutionResult = await target_ministry.execute(task)

        route_result: RoutingResult = {
            "source_ministry": source,
            "target_ministry": target_ministry.ministry_name,
            "task_id": task.get("task_id", ""),
            "role_name": role_name,
            "reason": f"角色 '{role_name}' 路由到 '{target_ministry.ministry_name}'",
            "result": result,
        }
        return route_result

    async def route_batch(
        self,
        tasks: list[TaskPayload],
        role_name: str | None = None,
        parallel: bool = True,
    ) -> list[RoutingResult]:
        """批量路由任务。

        Args:
            tasks: 任务列表。
            role_name: 可选，显式指定角色名称。
            parallel: 是否并行执行（默认 True）。

        Returns:
            路由结果列表，顺序与输入 tasks 一致。
        """
        if parallel:
            coros = [self.route_task(t, role_name=role_name) for t in tasks]
            return await asyncio.gather(*coros)
        results: list[RoutingResult] = []
        for t in tasks:
            r = await self.route_task(t, role_name=role_name)
            results.append(r)
        return results

    def has_role(self, name: str) -> bool:
        """检查角色是否已注册。"""
        return name in self._roles

    def has_ministry(self, name: str) -> bool:
        """检查部门是否已注册。"""
        return name in self._ministry_registry

    @property
    def role_count(self) -> int:
        return len(self._roles)

    @property
    def ministry_count(self) -> int:
        return len(self._ministry_registry)


# ── 工作流状态机 ── 对标 LangGraph ──────────────────────

class WorkflowStateMachine:
    """工作流状态机——对标 LangGraph 的状态机编排。

    支持：
    - 状态定义和条件转移
    - 并行/串行执行模式
    - 执行上下文跟踪
    - 状态转移回调
    """

    def __init__(self, name: str = "default_workflow") -> None:
        self._name: str = name
        self._states: dict[WorkflowState, list[Callable[..., Awaitable[Any]]]] = {}
        self._transitions: dict[WorkflowState, list[WorkflowTransition]] = {}
        self._initial_state: WorkflowState = WorkflowState.INIT
        self._end_states: set[WorkflowState] = {WorkflowState.COMPLETE, WorkflowState.ERROR, WorkflowState.CANCELLED}
        self._current_state: WorkflowState = WorkflowState.INIT
        self._execution_mode: ExecutionMode = ExecutionMode.SERIAL
        self._context: dict[str, Any] = {}
        self._history: list[dict[str, Any]] = []
        self._lock: asyncio.Lock = asyncio.Lock()
        self._on_enter_callbacks: dict[WorkflowState, list[Callable[..., Awaitable[None]]]] = {}
        self._on_exit_callbacks: dict[WorkflowState, list[Callable[..., Awaitable[None]]]] = {}

    # ── 状态定义 ──────────────────────────────────────────

    @property
    def name(self) -> str:
        return self._name

    @property
    def current_state(self) -> WorkflowState:
        return self._current_state

    @property
    def context(self) -> dict[str, Any]:
        return dict(self._context)

    @property
    def history(self) -> list[dict[str, Any]]:
        return list(self._history)

    def add_state(
        self,
        state: WorkflowState,
        handlers: list[Callable[..., Awaitable[Any]]] | None = None,
    ) -> None:
        """注册一个工作流状态及其处理函数。

        Args:
            state: 状态枚举值。
            handlers: 该状态绑定的处理函数列表（可选）。
        """
        if state not in self._states:
            self._states[state] = []
        if handlers:
            self._states[state].extend(handlers)

    def add_transition(self, transition: WorkflowTransition) -> None:
        """注册一个状态转移规则。

        Args:
            transition: 状态转移定义，包含 from_state, to_state, condition, description。
        """
        from_state = transition["from_state"]
        if from_state not in self._transitions:
            self._transitions[from_state] = []
        self._transitions[from_state].append(transition)

    def add_transition_from_args(
        self,
        from_state: WorkflowState,
        to_state: WorkflowState,
        condition: str = "True",
        description: str = "",
    ) -> None:
        """便捷方法：直接传参注册状态转移。"""
        trans: WorkflowTransition = {
            "from_state": from_state,
            "to_state": to_state,
            "condition": condition,
            "description": description,
        }
        self.add_transition(trans)

    def set_initial_state(self, state: WorkflowState) -> None:
        """设置工作流的初始状态。"""
        self._initial_state = state
        self._current_state = state

    def set_end_states(self, states: list[WorkflowState]) -> None:
        """设置工作流的终态集合。"""
        self._end_states = set(states)

    def set_execution_mode(self, mode: ExecutionMode) -> None:
        """设置执行模式：串行或并行。"""
        self._execution_mode = mode

    # ── 回调机制 ──────────────────────────────────────────

    def on_enter(self, state: WorkflowState, callback: Callable[..., Awaitable[None]]) -> None:
        """注册进入状态时的回调函数。"""
        if state not in self._on_enter_callbacks:
            self._on_enter_callbacks[state] = []
        self._on_enter_callbacks[state].append(callback)

    def on_exit(self, state: WorkflowState, callback: Callable[..., Awaitable[None]]) -> None:
        """注册退出状态时的回调函数。"""
        if state not in self._on_exit_callbacks:
            self._on_exit_callbacks[state] = []
        self._on_exit_callbacks[state].append(callback)

    # ── 条件评估 ──────────────────────────────────────────

    def _evaluate_condition(self, condition: str, result: Any) -> bool:
        """评估转移条件表达式。

        支持的表达式格式：
        - "True"           → 总是通过
        - "False"          → 总是不通过
        - "result.status == 'success'"  → 比较 result 属性
        - "result.error is None"        → 检查 None

        Args:
            condition: 条件表达式字符串。
            result: 上一状态的执行结果。

        Returns:
            条件是否满足。
        """
        cond_clean: str = condition.strip()
        if cond_clean == "True":
            return True
        if cond_clean == "False":
            return False

        # 处理标准结果比较
        if isinstance(result, dict):
            # result.status == 'success' 形式
            if "result.status" in cond_clean:
                expected_status: str = cond_clean.split("'")[1] if "'" in cond_clean else ""
                actual_status: str = result.get("status", "")
                if isinstance(actual_status, ExecutionStatus):
                    return actual_status.value == expected_status or actual_status == expected_status
                return actual_status == expected_status

            # result.error is None 形式
            if "result.error is None" in cond_clean:
                return result.get("error") is None

            # result.error is not None 形式
            if "result.error is not None" in cond_clean:
                return result.get("error") is not None

        # 通用 eval（安全：只允许访问 result 和 context）
        safe_globals: dict[str, Any] = {"result": result, "context": self._context}
        try:
            return bool(eval(condition, {"__builtins__": {}}, safe_globals))
        except Exception:
            return False

    def _find_next_state(self, result: Any) -> WorkflowState | None:
        """根据当前状态和结果，查找下一个匹配的状态。"""
        transitions = self._transitions.get(self._current_state, [])
        for trans in transitions:
            if self._evaluate_condition(trans["condition"], result):
                return trans["to_state"]
        return None

    # ── 状态执行 ──────────────────────────────────────────

    async def _execute_state_handlers(self, state: WorkflowState, input_data: Any) -> Any:
        """执行指定状态的所有处理函数。

        串行模式：按顺序依次执行，将上一个结果传入下一个。
        并行模式：所有处理函数同时执行，返回结果列表。

        支持同步和异步处理函数。
        """
        handlers = self._states.get(state, [])

        if not handlers:
            # 无处理函数时，直接返回输入数据
            return input_data

        async def _maybe_await(h: Callable, data: Any) -> Any:
            """兼容同步和异步处理函数。"""
            r = h(data)
            if asyncio.iscoroutine(r):
                return await r
            return r

        if self._execution_mode == ExecutionMode.PARALLEL:
            # 并行执行
            coros = [_maybe_await(h, input_data) for h in handlers]
            results = await asyncio.gather(*coros, return_exceptions=True)
            # 过滤异常
            valid_results = [r for r in results if not isinstance(r, Exception)]
            return valid_results or (results[-1] if results else input_data)
        # 串行执行
        current_data = input_data
        for handler in handlers:
            result = await _maybe_await(handler, current_data)
            current_data = result
        return current_data

    async def _run_enter_callbacks(self, state: WorkflowState) -> None:
        """执行进入状态的回调。"""
        callbacks = self._on_enter_callbacks.get(state, [])
        for cb in callbacks:
            try:
                await cb()
            except Exception:
                pass

    async def _run_exit_callbacks(self, state: WorkflowState) -> None:
        """执行退出状态的回调。"""
        callbacks = self._on_exit_callbacks.get(state, [])
        for cb in callbacks:
            try:
                await cb()
            except Exception:
                pass

    # ── 主执行入口 ────────────────────────────────────────

    async def run(self, initial_input: Any | None = None) -> dict[str, Any]:
        """运行工作流状态机。

        从初始状态开始，依次执行各状态的处理函数，
        根据转移条件自动流转到下一个状态，
        直到到达终态。

        Args:
            initial_input: 工作流的初始输入数据。

        Returns:
            包含最终状态、上下文、历史的执行结果字典。

        Raises:
            WorkflowExecutionError: 执行过程中出现无法恢复的错误。
        """
        async with self._lock:
            self._current_state = self._initial_state
            self._context = {}
            self._history = []
            if initial_input is not None:
                self._context["initial_input"] = initial_input

        current_input: Any = initial_input

        while self._current_state not in self._end_states:
            state: WorkflowState = self._current_state
            state_name: str = state.value

            try:
                # 进入回调
                await self._run_enter_callbacks(state)

                # 执行处理函数
                output: Any = await self._execute_state_handlers(state, current_input)

                # 更新上下文
                self._context[f"{state_name}_output"] = output
                self._context["last_state"] = state_name

                # 记录历史
                history_entry: dict[str, Any] = {
                    "state": state_name,
                    "input": current_input,
                    "output": output,
                    "timestamp": time.monotonic(),
                }
                self._history.append(history_entry)

                # 退出回调
                await self._run_exit_callbacks(state)

                # 查找下一个状态
                next_state: WorkflowState | None = self._find_next_state(output)
                if next_state is None:
                    # 无匹配转移 → 默认进入 COMPLETE
                    next_state = WorkflowState.COMPLETE

                # 状态转移
                async with self._lock:
                    self._current_state = next_state

                current_input = output

            except Exception as exc:
                error_entry: dict[str, Any] = {
                    "state": state_name,
                    "error": str(exc),
                    "timestamp": time.monotonic(),
                }
                self._history.append(error_entry)
                self._context["error"] = str(exc)
                async with self._lock:
                    self._current_state = WorkflowState.ERROR
                raise WorkflowExecutionError(
                    workflow_name=self._name,
                    state=state_name,
                    message=str(exc),
                )

        # 终态处理
        final_state: WorkflowState = self._current_state
        await self._run_enter_callbacks(final_state)
        self._context["final_state"] = final_state.value

        return {
            "workflow": self._name,
            "final_state": final_state.value,
            "context": dict(self._context),
            "history": list(self._history),
            "success": final_state in (WorkflowState.COMPLETE,),
        }

    async def step(self, input_data: Any = None) -> dict[str, Any]:
        """单步执行：只执行当前状态，然后转移到下一个状态。

        适用于交互式调试或需要外部确认的场景。

        Args:
            input_data: 当前状态的输入数据。

        Returns:
            当前步骤的执行结果。
        """
        if self._current_state in self._end_states:
            return {
                "workflow": self._name,
                "state": self._current_state.value,
                "message": "工作流已到达终态",
                "done": True,
            }

        state: WorkflowState = self._current_state
        state_name: str = state.value

        try:
            await self._run_enter_callbacks(state)
            output: Any = await self._execute_state_handlers(state, input_data)
            self._context[f"{state_name}_output"] = output
            self._context["last_state"] = state_name

            self._history.append({
                "state": state_name,
                "input": input_data,
                "output": output,
                "timestamp": time.monotonic(),
            })

            await self._run_exit_callbacks(state)

            next_state: WorkflowState | None = self._find_next_state(output)
            if next_state is None:
                next_state = WorkflowState.COMPLETE

            async with self._lock:
                self._current_state = next_state

            return {
                "workflow": self._name,
                "from_state": state_name,
                "to_state": next_state.value,
                "output": output,
                "done": next_state in self._end_states,
            }

        except Exception as exc:
            self._history.append({
                "state": state_name,
                "error": str(exc),
                "timestamp": time.monotonic(),
            })
            self._context["error"] = str(exc)
            async with self._lock:
                self._current_state = WorkflowState.ERROR
            raise WorkflowExecutionError(
                workflow_name=self._name,
                state=state_name,
                message=str(exc),
            )

    def reset(self) -> None:
        """重置状态机到初始状态，清空上下文和历史。"""
        self._current_state = self._initial_state
        self._context.clear()
        self._history.clear()

    def from_definition(self, definition: WorkflowDefinition) -> None:
        """从 WorkflowDefinition 加载完整的工作流定义。

        Args:
            definition: 工作流定义字典。
        """
        if "name" in definition:
            self._name = definition["name"]
        if "states" in definition:
            for s in definition["states"]:
                self.add_state(s)
        if "transitions" in definition:
            for t in definition["transitions"]:
                self.add_transition(t)
        if "initial_state" in definition:
            self.set_initial_state(definition["initial_state"])
        if "end_states" in definition:
            self.set_end_states(definition["end_states"])
        if "execution_mode" in definition:
            self.set_execution_mode(definition["execution_mode"])

    def get_definition(self) -> WorkflowDefinition:
        """导出当前工作流定义为 WorkflowDefinition。"""
        return {
            "name": self._name,
            "states": list(self._states.keys()),
            "transitions": [
                t for trans_list in self._transitions.values() for t in trans_list
            ],
            "initial_state": self._initial_state,
            "end_states": list(self._end_states),
            "execution_mode": self._execution_mode,
        }
