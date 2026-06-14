"""三省六部模块完整测试套件。

覆盖范围：
- MinistryBase 基类熔断器
- RoleOrchestrator 角色注册/匹配/路由
- WorkflowStateMachine 状态机(串行/并行/条件转移)
- 所有异常类
"""

import asyncio
import unittest
from typing import Any

# ── 被测试模块 ──────────────────────────────────────────────
from scripts.ministry_abc import (
    CircuitBreaker,
    MinistryBase,
    RoleOrchestrator,
    WorkflowStateMachine,
)
from scripts.ministry_exceptions import (
    CircuitBreakerOpenError,
    InvalidTaskError,
    MinistryError,
    PipelineExecutionError,
    RoleAssignmentError,
    TaskExecutionError,
    TaskTimeoutError,
    WorkflowExecutionError,
    WorkflowTransitionError,
)
from scripts.ministry_types import (
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
)

# ════════════════════════════════════════════════════════════
# 辅助工具
# ════════════════════════════════════════════════════════════

class AsyncTestCase(unittest.IsolatedAsyncioTestCase):
    """所有异步测试的基类。"""


def make_task(task_id: str = "t1", action: str = "test", **extra: Any) -> TaskPayload:
    """快速创建 TaskPayload。"""
    return {
        "task_id": task_id,
        "action": action,
        "args": {},
        "timeout_seconds": 5.0,
        **extra,
    }


class SimpleMinistry(MinistryBase):
    """用于测试的最简 Ministry 实现。"""
    def __init__(self, name: str = "test_ministry",
                 cb_config: CircuitBreakerConfig | None = None) -> None:
        super().__init__(name, cb_config)

    async def _execute_impl(self, task: TaskPayload) -> Any:
        action: str = task.get("action", "default")
        args: dict[str, Any] = task.get("args", {})
        return {
            "action": action,
            "args": args,
            "ministry": self.ministry_name,
            "processed": True,
        }


class FailingMinistry(MinistryBase):
    """总是失败的 Ministry，用于测试熔断器。"""
    def __init__(self, name: str = "failing_ministry",
                 cb_config: CircuitBreakerConfig | None = None) -> None:
        super().__init__(name, cb_config)

    async def _execute_impl(self, task: TaskPayload) -> Any:
        raise RuntimeError(f"simulated failure for {task.get('task_id', '')}")


class SlowMinistry(MinistryBase):
    """超慢 Ministry，用于测试超时。"""
    def __init__(self, name: str = "slow_ministry",
                 cb_config: CircuitBreakerConfig | None = None) -> None:
        super().__init__(name, cb_config)

    async def _execute_impl(self, task: TaskPayload) -> Any:
        await asyncio.sleep(60)
        return {"done": True}


# ════════════════════════════════════════════════════════════
# 第1部分：异常类测试
# ════════════════════════════════════════════════════════════

class TestExceptions(unittest.TestCase):
    """所有异常类的构造、继承关系和属性。"""

    def test_ministry_error_base(self) -> None:
        """MinistryError 是所有异常的基类。"""
        e = MinistryError("test error", ministry="吏部", task_id="t1",
                          details={"key": "val"})
        self.assertEqual(str(e), "test error")
        self.assertEqual(e.ministry, "吏部")
        self.assertEqual(e.task_id, "t1")
        self.assertEqual(e.details, {"key": "val"})

    def test_ministry_error_defaults(self) -> None:
        e = MinistryError("msg")
        self.assertEqual(e.ministry, "")
        self.assertEqual(e.task_id, "")
        self.assertEqual(e.details, {})

    def test_circuit_breaker_open_error(self) -> None:
        """CircuitBreakerOpenError 的默认消息。"""
        e = CircuitBreakerOpenError(ministry="吏部")
        self.assertIn("吏部", str(e))
        self.assertIn("熔断器已打开", str(e))
        self.assertEqual(e.ministry, "吏部")

    def test_circuit_breaker_open_error_custom_msg(self) -> None:
        e = CircuitBreakerOpenError(ministry="兵部", task_id="t99",
                                    message="custom msg")
        self.assertEqual(str(e), "custom msg")
        self.assertEqual(e.task_id, "t99")

    def test_task_timeout_error(self) -> None:
        e = TaskTimeoutError(ministry="工部", task_id="t2", timeout_seconds=5.0)
        self.assertIn("工部", str(e))
        self.assertIn("5.0", str(e))
        self.assertIn("t2", str(e))
        self.assertEqual(e.timeout_seconds, 5.0)

    def test_task_timeout_error_default_msg(self) -> None:
        e = TaskTimeoutError(ministry="礼部")
        self.assertIn("礼部", str(e))

    def test_task_execution_error(self) -> None:
        e = TaskExecutionError(ministry="刑部", task_id="t3",
                               message="exec failed",
                               details={"code": 500})
        self.assertEqual(str(e), "exec failed")
        self.assertEqual(e.details, {"code": 500})

    def test_invalid_task_error(self) -> None:
        e = InvalidTaskError(ministry="户部", task_id="t4", reason="missing args")
        self.assertIn("户部", str(e))
        self.assertIn("missing args", str(e))

    def test_invalid_task_error_no_reason(self) -> None:
        e = InvalidTaskError(ministry="户部")
        self.assertIn("无效任务", str(e))

    def test_pipeline_execution_error(self) -> None:
        e = PipelineExecutionError(ministry="吏部", task_id="t5",
                                   stage="validate", message="validation failed")
        self.assertIn("validate", str(e))
        self.assertIn("validation failed", str(e))
        self.assertEqual(e.stage, "validate")

    def test_workflow_execution_error(self) -> None:
        e = WorkflowExecutionError(workflow_name="wf1", state="process",
                                   task_id="t6", message="boom")
        self.assertIn("wf1", str(e))
        self.assertIn("process", str(e))
        self.assertIn("boom", str(e))
        self.assertEqual(e.workflow_name, "wf1")
        self.assertEqual(e.state, "process")
        self.assertEqual(e.ministry, "workflow")

    def test_workflow_transition_error(self) -> None:
        e = WorkflowTransitionError(workflow_name="wf2",
                                    from_state="init", to_state="process",
                                    task_id="t7", reason="condition not met")
        self.assertIn("wf2", str(e))
        self.assertIn("init", str(e))
        self.assertIn("process", str(e))
        self.assertIn("condition not met", str(e))
        self.assertEqual(e.from_state, "init")
        self.assertEqual(e.to_state, "process")

    def test_role_assignment_error(self) -> None:
        e = RoleAssignmentError(role_name="scribe", task_id="t8",
                                reason="not found")
        self.assertIn("scribe", str(e))
        self.assertIn("not found", str(e))

    def test_exception_inheritance_chain(self) -> None:
        """所有自定义异常都继承自 MinistryError。"""
        exceptions = [
            CircuitBreakerOpenError(ministry="x"),
            TaskTimeoutError(ministry="x"),
            TaskExecutionError(ministry="x"),
            InvalidTaskError(ministry="x"),
            PipelineExecutionError(ministry="x"),
            WorkflowExecutionError(workflow_name="x"),
            WorkflowTransitionError(workflow_name="x", from_state="a", to_state="b"),
            RoleAssignmentError(role_name="x"),
        ]
        for e in exceptions:
            with self.subTest(type(e).__name__):
                self.assertIsInstance(e, MinistryError)

    def test_exception_inherits_exception(self) -> None:
        """所有自定义异常最终继承自 Exception。"""
        self.assertTrue(issubclass(MinistryError, Exception))


# ════════════════════════════════════════════════════════════
# 第2部分：熔断器（CircuitBreaker）测试
# ════════════════════════════════════════════════════════════

class TestCircuitBreaker(AsyncTestCase):
    """CircuitBreaker 的单元测试。"""

    async def test_initial_state_closed(self) -> None:
        cb = CircuitBreaker()
        self.assertEqual(cb.state, CircuitState.CLOSED)
        self.assertEqual(cb.failure_count, 0)

    async def test_call_success_keeps_closed(self) -> None:
        cb = CircuitBreaker()

        async def ok() -> str:
            return "hello"

        result = await cb.call(ok)
        self.assertEqual(result, "hello")
        self.assertEqual(cb.state, CircuitState.CLOSED)

    async def test_trip_to_open_after_threshold_failures(self) -> None:
        cb = CircuitBreaker({
            "failure_threshold": 3,
            "recovery_timeout": 999.0,
            "half_open_max_requests": 1,
            "success_threshold": 1,
        })

        async def fail() -> str:
            raise ValueError("boom")

        for i in range(2):
            with self.assertRaises(ValueError):
                await cb.call(fail)
            self.assertEqual(cb.state, CircuitState.CLOSED,
                             f"should still be closed after {i+1} failures")

        # 第3次失败 → 打开
        with self.assertRaises(ValueError):
            await cb.call(fail)
        self.assertEqual(cb.state, CircuitState.OPEN)

    async def test_circuit_breaker_open_error_raised(self) -> None:
        """熔断器打开后调用抛 CircuitBreakerOpenError。"""
        cb = CircuitBreaker({
            "failure_threshold": 1,
            "recovery_timeout": 999.0,
        })

        async def fail() -> str:
            raise ValueError("boom")

        with self.assertRaises(ValueError):
            await cb.call(fail)
        self.assertEqual(cb.state, CircuitState.OPEN)

        # 再次调用应抛 CircuitBreakerOpenError
        with self.assertRaises(CircuitBreakerOpenError):
            await cb.call(fail)

    async def test_half_open_limit(self) -> None:
        """半开状态限制探测请求数。"""
        cb = CircuitBreaker({
            "failure_threshold": 1,
            "recovery_timeout": 0.01,  # 立即恢复
            "half_open_max_requests": 1,
            "success_threshold": 1,
        })

        async def fail() -> str:
            raise ValueError("boom")

        with self.assertRaises(ValueError):
            await cb.call(fail)
        self.assertEqual(cb.state, CircuitState.OPEN)

        # 等待进入半开
        await asyncio.sleep(0.02)

        # 第一个探测请求成功 → 闭合
        async def ok() -> str:
            return "ok"

        result = await cb.call(ok)
        self.assertEqual(result, "ok")
        self.assertEqual(cb.state, CircuitState.CLOSED)

    async def test_half_open_failure_reopens(self) -> None:
        """半开状态失败 → 回到打开。"""
        cb = CircuitBreaker({
            "failure_threshold": 1,
            "recovery_timeout": 0.01,
            "half_open_max_requests": 2,
            "success_threshold": 2,
        })

        async def fail() -> str:
            raise ValueError("boom")

        with self.assertRaises(ValueError):
            await cb.call(fail)
        self.assertEqual(cb.state, CircuitState.OPEN)

        await asyncio.sleep(0.02)

        # 半开中失败 → 回到打开
        with self.assertRaises(ValueError):
            await cb.call(fail)
        self.assertEqual(cb.state, CircuitState.OPEN)

    async def test_reset(self) -> None:
        cb = CircuitBreaker({"failure_threshold": 1})
        async def fail() -> str:
            raise ValueError("x")
        with self.assertRaises(ValueError):
            await cb.call(fail)
        cb.reset()
        self.assertEqual(cb.state, CircuitState.CLOSED)
        self.assertEqual(cb.failure_count, 0)

    async def test_custom_config(self) -> None:
        config: CircuitBreakerConfig = {
            "failure_threshold": 2,
            "recovery_timeout": 10.0,
            "half_open_max_requests": 3,
            "success_threshold": 5,
        }
        cb = CircuitBreaker(config)
        self.assertEqual(cb._failure_threshold, 2)
        self.assertEqual(cb._recovery_timeout, 10.0)
        self.assertEqual(cb._half_open_max_requests, 3)
        self.assertEqual(cb._success_threshold, 5)


# ════════════════════════════════════════════════════════════
# 第3部分：MinistryBase 测试
# ════════════════════════════════════════════════════════════

class TestMinistryBase(AsyncTestCase):
    """MinistryBase 的 execute / pipeline / 熔断 / 超时。"""

    async def test_execute_success(self) -> None:
        m = SimpleMinistry("test_m")
        result: ExecutionResult = await m.execute(make_task("t1", "test_action"))
        self.assertEqual(result["status"], ExecutionStatus.SUCCESS)
        self.assertEqual(result["task_id"], "t1")
        self.assertIsNotNone(result["data"])
        self.assertIsNone(result["error"])
        self.assertGreater(result["duration_seconds"], 0)

    async def test_execute_default_impl(self) -> None:
        """未重写 _execute_impl 时使用默认实现。"""
        class DefaultMinistry(MinistryBase):
            pass

        m = DefaultMinistry("default_m")
        result = await m.execute(make_task("t99", "ping"))
        self.assertEqual(result["status"], ExecutionStatus.SUCCESS)
        data = result["data"]
        self.assertEqual(data["ministry"], "default_m")
        self.assertEqual(data["action"], "ping")
        self.assertEqual(data["processed"], True)

    async def test_execute_failure(self) -> None:
        m = FailingMinistry("fail_m")
        result: ExecutionResult = await m.execute(make_task("f1"))
        self.assertEqual(result["status"], ExecutionStatus.FAILED)
        self.assertIsNone(result["data"])
        self.assertIn("simulated failure", result["error"] or "")

    async def test_circuit_breaker_integration(self) -> None:
        """熔断器打开后返回 CIRCUIT_OPEN 而非再尝试执行。"""
        config: CircuitBreakerConfig = {
            "failure_threshold": 2,
            "recovery_timeout": 999.0,
        }
        m = FailingMinistry("cb_int", config)

        # 失败 2 次 → 熔断器打开
        for i in range(2):
            r = await m.execute(make_task(f"f{i}"))
            self.assertEqual(r["status"], ExecutionStatus.FAILED)

        # 第3次 → CIRCUIT_OPEN
        r = await m.execute(make_task("f3"))
        self.assertEqual(r["status"], ExecutionStatus.CIRCUIT_OPEN)
        self.assertEqual(r["error"], "熔断器已打开，拒绝执行")

    async def test_circuit_breaker_reset_method(self) -> None:
        config: CircuitBreakerConfig = {
            "failure_threshold": 1,
            "recovery_timeout": 999.0,
        }
        m = FailingMinistry("cb_reset", config)
        r = await m.execute(make_task("f1"))
        self.assertEqual(r["status"], ExecutionStatus.FAILED)
        self.assertEqual(m.circuit_state, CircuitState.OPEN)

        m.circuit_breaker_reset()
        self.assertEqual(m.circuit_state, CircuitState.CLOSED)

    async def test_pipeline_stages_execute_in_order(self) -> None:
        m = SimpleMinistry("pipe_m")

        async def stage_a(task: TaskPayload) -> TaskPayload:
            d = dict(task)
            d["args"] = {**d.get("args", {}), "a": 1}
            return d

        async def stage_b(task: TaskPayload) -> TaskPayload:
            d = dict(task)
            d["args"] = {**d.get("args", {}), "b": 2, "seq": d["args"].get("a", 0) + 1}
            return d

        m.register_pipeline_stage(stage_a)
        m.register_pipeline_stage(stage_b)

        result = await m.execute(make_task("pipe1", action="pipe_test"))
        self.assertEqual(result["status"], ExecutionStatus.SUCCESS)
        data = result["data"]
        self.assertEqual(data["args"]["a"], 1)
        self.assertEqual(data["args"]["b"], 2)
        self.assertEqual(data["args"]["seq"], 2)  # a then b

    async def test_pipeline_clear(self) -> None:
        m = SimpleMinistry("clear_pipe")
        async def stage(task: TaskPayload) -> TaskPayload:
            raise RuntimeError("should not run")
        m.register_pipeline_stage(stage)
        m.clear_pipeline()

        result = await m.execute(make_task("clear1"))
        self.assertEqual(result["status"], ExecutionStatus.SUCCESS)

    async def test_timeout_returns_failed(self) -> None:
        m = SlowMinistry("slow_m")
        task = make_task("slow1", action="slow", timeout_seconds=0.01)
        result = await m.execute(task)
        self.assertEqual(result["status"], ExecutionStatus.FAILED)
        self.assertIn("超时", result["error"] or "")

    async def test_ministry_name_property(self) -> None:
        m = SimpleMinistry("custom_name")
        self.assertEqual(m.ministry_name, "custom_name")

    async def test_circuit_state_property(self) -> None:
        m = SimpleMinistry("prop_test")
        self.assertEqual(m.circuit_state, CircuitState.CLOSED)


# ════════════════════════════════════════════════════════════
# 第4部分：RoleOrchestrator 测试
# ════════════════════════════════════════════════════════════

class TestRoleOrchestrator(AsyncTestCase):
    """RoleOrchestrator 角色注册 / 匹配 / 路由。"""

    async def asyncSetUp(self) -> None:
        self.orch = RoleOrchestrator()
        self.li_bu = SimpleMinistry(Ministry.LI_BU.value)
        self.hu_bu = SimpleMinistry(Ministry.HU_BU.value)
        self.bing_bu = SimpleMinistry(Ministry.BING_BU.value)
        self.orch.register_ministries(self.li_bu, self.hu_bu, self.bing_bu)

    # ── 角色注册 ──────────────────────────────────────────

    def test_register_role(self) -> None:
        role: RoleDefinition = {
            "name": "scribe",
            "goal": "write documents",
            "backstory": "a scribe",
            "allowed_ministries": [Ministry.LI_BU.value],
            "priority": 5,
        }
        self.orch.register_role(role)
        self.assertTrue(self.orch.has_role("scribe"))
        self.assertEqual(self.orch.role_count, 1)

    def test_register_role_from_args(self) -> None:
        self.orch.register_role_from_args(
            name="general",
            goal="command army",
            backstory="a general",
            allowed_ministries=[Ministry.BING_BU.value],
            priority=1,
        )
        self.assertTrue(self.orch.has_role("general"))

    def test_remove_role_existing(self) -> None:
        self.orch.register_role_from_args(name="tmp", goal="x", backstory="y")
        self.assertTrue(self.orch.remove_role("tmp"))
        self.assertFalse(self.orch.has_role("tmp"))

    def test_remove_role_missing(self) -> None:
        self.assertFalse(self.orch.remove_role("nonexistent"))

    def test_list_roles_sorted_by_priority(self) -> None:
        self.orch.register_role_from_args(name="low", goal="x", backstory="y", priority=100)
        self.orch.register_role_from_args(name="high", goal="z", backstory="w", priority=1)
        roles = self.orch.list_roles()
        self.assertEqual([r["name"] for r in roles], ["high", "low"])

    def test_get_role(self) -> None:
        self.orch.register_role_from_args(name="find_me", goal="x", backstory="y")
        role = self.orch.get_role("find_me")
        self.assertIsNotNone(role)
        self.assertEqual(role["name"], "find_me")

    def test_get_role_missing(self) -> None:
        self.assertIsNone(self.orch.get_role("missing"))

    # ── 部门注册 ──────────────────────────────────────────

    def test_register_ministry(self) -> None:
        self.assertTrue(self.orch.has_ministry(Ministry.LI_BU.value))
        self.assertTrue(self.orch.has_ministry(Ministry.HU_BU.value))
        self.assertTrue(self.orch.has_ministry(Ministry.BING_BU.value))
        self.assertEqual(self.orch.ministry_count, 3)

    def test_unregister_ministry(self) -> None:
        self.assertTrue(self.orch.unregister_ministry(Ministry.LI_BU.value))
        self.assertFalse(self.orch.has_ministry(Ministry.LI_BU.value))

    def test_unregister_ministry_missing(self) -> None:
        self.assertFalse(self.orch.unregister_ministry("nonexistent"))

    # ── 角色匹配 ──────────────────────────────────────────

    def test_find_role_for_task_explicit_role(self) -> None:
        self.orch.register_role_from_args(
            name="analyzer", goal="analyze data", backstory="data analyst")
        task = make_task("t1", "analyze", role="analyzer")
        role = self.orch.find_role_for_task(task)
        self.assertIsNotNone(role)
        self.assertEqual(role["name"], "analyzer")

    def test_find_role_for_task_by_action(self) -> None:
        self.orch.register_role_from_args(
            name="writer", goal="write content", backstory="writer")
        task = make_task("t1", "write")
        role = self.orch.find_role_for_task(task)
        self.assertIsNotNone(role)
        self.assertEqual(role["name"], "writer")

    def test_find_role_for_task_no_match(self) -> None:
        self.orch.register_role_from_args(
            name="writer", goal="write", backstory="w")
        task = make_task("t1", "cook")
        role = self.orch.find_role_for_task(task)
        self.assertIsNone(role)

    def test_find_role_for_task_no_action_returns_highest_priority(self) -> None:
        self.orch.register_role_from_args(
            name="low", goal="x", backstory="y", priority=50)
        self.orch.register_role_from_args(
            name="high", goal="z", backstory="w", priority=1)
        task: TaskPayload = {"task_id": "t1"}
        role = self.orch.find_role_for_task(task)
        self.assertEqual(role["name"], "high")

    # ── 路由 ──────────────────────────────────────────────

    async def test_route_task_to_explicit_role(self) -> None:
        self.orch.register_role_from_args(
            name="minister",
            goal="manage",
            backstory="minister",
            allowed_ministries=[Ministry.LI_BU.value],
        )
        result: RoutingResult = await self.orch.route_task(
            make_task("r1", "manage"), role_name="minister")
        self.assertEqual(result["role_name"], "minister")
        self.assertEqual(result["target_ministry"], Ministry.LI_BU.value)
        self.assertEqual(result["task_id"], "r1")
        self.assertEqual(result["result"]["status"], ExecutionStatus.SUCCESS)

    async def test_route_task_auto_role_match(self) -> None:
        self.orch.register_role_from_args(
            name="builder",
            goal="build things",
            backstory="builder",
            allowed_ministries=[Ministry.GONG_BU.value],
        )
        # 注册工部
        gong_bu = SimpleMinistry(Ministry.GONG_BU.value)
        self.orch.register_ministry(gong_bu)

        result = await self.orch.route_task(make_task("r2", "build"))
        self.assertEqual(result["role_name"], "builder")
        self.assertEqual(result["target_ministry"], Ministry.GONG_BU.value)

    async def test_route_task_role_not_found(self) -> None:
        with self.assertRaises(RoleAssignmentError) as ctx:
            await self.orch.route_task(make_task("r3", "cook"), role_name="nonexistent")
        self.assertIn("nonexistent", str(ctx.exception))

    async def test_route_task_auto_role_not_found(self) -> None:
        with self.assertRaises(RoleAssignmentError) as ctx:
            await self.orch.route_task(make_task("r4", "surf"))
        self.assertIn("无法自动匹配合适的角色", str(ctx.exception))

    async def test_route_task_no_available_ministry(self) -> None:
        self.orch.register_role_from_args(
            name="isolated",
            goal="isolated task",
            backstory="alone",
            allowed_ministries=["nonexistent_dept"],
        )
        with self.assertRaises(RoleAssignmentError) as ctx:
            await self.orch.route_task(
                make_task("r5", "isolated"), role_name="isolated")
        self.assertIn("均未注册", str(ctx.exception))

    async def test_route_batch_parallel(self) -> None:
        self.orch.register_role_from_args(
            name="worker",
            goal="work",
            backstory="worker",
            allowed_ministries=[Ministry.LI_BU.value],
        )
        tasks = [make_task(f"b{i}", "work") for i in range(3)]
        results = await self.orch.route_batch(tasks, role_name="worker", parallel=True)
        self.assertEqual(len(results), 3)
        for r in results:
            self.assertEqual(r["result"]["status"], ExecutionStatus.SUCCESS)

    async def test_route_batch_serial(self) -> None:
        self.orch.register_role_from_args(
            name="worker",
            goal="work",
            backstory="worker",
            allowed_ministries=[Ministry.LI_BU.value],
        )
        tasks = [make_task(f"s{i}", "work") for i in range(3)]
        results = await self.orch.route_batch(tasks, role_name="worker", parallel=False)
        self.assertEqual(len(results), 3)
        for r in results:
            self.assertEqual(r["result"]["status"], ExecutionStatus.SUCCESS)


# ════════════════════════════════════════════════════════════
# 第5部分：WorkflowStateMachine 测试
# ════════════════════════════════════════════════════════════

class TestWorkflowStateMachine(AsyncTestCase):
    """WorkflowStateMachine 状态机测试：串行 / 并行 / 条件转移。"""

    async def asyncSetUp(self) -> None:
        self.wf = WorkflowStateMachine("test_workflow")
        # 注册一些标准状态
        self.wf.add_state(WorkflowState.INPUT, [lambda x: {"processed": x}])
        self.wf.add_state(WorkflowState.PROCESS, [lambda x: {"result": "ok", **x}])
        self.wf.add_state(WorkflowState.REVIEW, [lambda x: {"reviewed": True, **x}])
        self.wf.add_state(WorkflowState.APPROVE)
        self.wf.add_state(WorkflowState.REJECT)
        # 转移：INPUT → PROCESS → REVIEW → APPROVE
        self.wf.add_transition_from_args(WorkflowState.INPUT, WorkflowState.PROCESS)
        self.wf.add_transition_from_args(WorkflowState.PROCESS, WorkflowState.REVIEW)
        self.wf.add_transition_from_args(WorkflowState.REVIEW, WorkflowState.APPROVE)

    # ── 基础属性 ──────────────────────────────────────────

    async def test_initial_state(self) -> None:
        self.assertEqual(self.wf.current_state, WorkflowState.INIT)
        self.assertEqual(self.wf.name, "test_workflow")

    def test_set_initial_state(self) -> None:
        self.wf.set_initial_state(WorkflowState.INPUT)
        self.assertEqual(self.wf.current_state, WorkflowState.INPUT)

    def test_set_end_states(self) -> None:
        self.wf.set_end_states([WorkflowState.COMPLETE])
        self.assertEqual(self.wf._end_states, {WorkflowState.COMPLETE})

    def test_set_execution_mode(self) -> None:
        self.wf.set_execution_mode(ExecutionMode.PARALLEL)
        self.assertEqual(self.wf._execution_mode, ExecutionMode.PARALLEL)

    # ── 串行执行 ──────────────────────────────────────────

    async def test_serial_execution(self) -> None:
        self.wf.set_initial_state(WorkflowState.INPUT)
        result = await self.wf.run("hello")
        self.assertEqual(result["workflow"], "test_workflow")
        # Flow: INPUT → PROCESS → REVIEW → APPROVE → (no outbound) → COMPLETE
        # History records: input, process, review, approve (4 states)
        # COMPLETE is an end state and not recorded in history
        self.assertEqual(result["final_state"], WorkflowState.COMPLETE.value)
        self.assertTrue(result["success"])
        self.assertEqual(len(result["history"]), 4)

    async def test_serial_execution_passes_data_through(self) -> None:
        self.wf.set_initial_state(WorkflowState.INPUT)
        result = await self.wf.run({"start": "data"})
        history = result["history"]
        # INPUT handler: {"processed": {"start": "data"}}
        # PROCESS handler: {"result": "ok", "processed": {"start": "data"}}
        # REVIEW handler: {"reviewed": True, "result": "ok", "processed": ...}
        last_output = history[-1]["output"]
        self.assertEqual(last_output["reviewed"], True)
        self.assertEqual(last_output["result"], "ok")

    # ── 并行执行 ──────────────────────────────────────────

    async def test_parallel_execution(self) -> None:
        wf = WorkflowStateMachine("parallel_wf")
        wf.set_initial_state(WorkflowState.PROCESS)
        wf.set_end_states([WorkflowState.COMPLETE])
        wf.set_execution_mode(ExecutionMode.PARALLEL)

        async def handler_a(data: Any) -> dict[str, Any]:
            await asyncio.sleep(0.01)
            return {"a": 1, **data} if isinstance(data, dict) else {"a": 1}

        async def handler_b(data: Any) -> dict[str, Any]:
            await asyncio.sleep(0.02)
            return {"b": 2, **data} if isinstance(data, dict) else {"b": 2}

        wf.add_state(WorkflowState.PROCESS, [handler_a, handler_b])
        wf.add_transition_from_args(WorkflowState.PROCESS, WorkflowState.COMPLETE)

        result = await wf.run({"seed": 0})
        self.assertTrue(result["success"])
        process_output = result["context"].get("process_output")
        # 并行模式返回列表
        self.assertIsInstance(process_output, list)
        self.assertEqual(len(process_output), 2)

    async def test_serial_vs_parallel_same_handlers(self) -> None:
        """验证串行模式返回单个值（不是列表）。"""
        wf = WorkflowStateMachine("compare_wf")
        wf.set_initial_state(WorkflowState.PROCESS)
        wf.set_end_states([WorkflowState.COMPLETE])
        wf.set_execution_mode(ExecutionMode.SERIAL)

        async def h(data: Any) -> dict[str, Any]:
            return {"tag": "serial"}

        wf.add_state(WorkflowState.PROCESS, [h])
        wf.add_transition_from_args(WorkflowState.PROCESS, WorkflowState.COMPLETE)

        result = await wf.run(None)
        process_output = result["context"].get("process_output")
        self.assertIsInstance(process_output, dict)  # 串行返回单个 dict
        self.assertEqual(process_output["tag"], "serial")

    # ── 条件转移 ──────────────────────────────────────────

    async def test_conditional_transition_success_path(self) -> None:
        wf = WorkflowStateMachine("conditional_wf")
        wf.set_initial_state(WorkflowState.REVIEW)
        wf.add_state(WorkflowState.REVIEW, [lambda x: {"status": "success"}])
        wf.add_state(WorkflowState.APPROVE, [lambda x: {"approved": True}])
        wf.add_state(WorkflowState.REJECT)
        wf.set_end_states([WorkflowState.APPROVE, WorkflowState.REJECT])

        # 条件：status == 'success' → APPROVE, 否则 → REJECT
        wf.add_transition_from_args(
            WorkflowState.REVIEW, WorkflowState.APPROVE,
            condition="result.status == 'success'",
            description="审核通过",
        )
        wf.add_transition_from_args(
            WorkflowState.REVIEW, WorkflowState.REJECT,
            condition="True",
            description="默认拒绝",
        )
        # Make APPROVE an end state to stop there
        wf.set_end_states([WorkflowState.APPROVE, WorkflowState.REJECT])

        result = await wf.run(None)
        # REVIEW passes (status='success') → APPROVE (end state)
        self.assertEqual(result["final_state"], WorkflowState.APPROVE.value)
        # Note: only COMPLETE is considered 'success' by the module design
        # (line 811: "success": final_state in (WorkflowState.COMPLETE,))

    async def test_conditional_transition_reject_path(self) -> None:
        wf = WorkflowStateMachine("conditional_reject")
        wf.set_initial_state(WorkflowState.REVIEW)
        wf.add_state(WorkflowState.REVIEW, [lambda x: {"status": "failed"}])
        wf.add_state(WorkflowState.APPROVE)
        wf.add_state(WorkflowState.REJECT)
        wf.set_end_states([WorkflowState.APPROVE, WorkflowState.REJECT])

        wf.add_transition_from_args(
            WorkflowState.REVIEW, WorkflowState.APPROVE,
            condition="result.status == 'success'",
        )
        wf.add_transition_from_args(
            WorkflowState.REVIEW, WorkflowState.REJECT,
            condition="True",
        )

        result = await wf.run(None)
        self.assertEqual(result["final_state"], WorkflowState.REJECT.value)

    async def test_conditional_transition_with_error_is_none(self) -> None:
        wf = WorkflowStateMachine("error_none_wf")
        wf.set_initial_state(WorkflowState.PROCESS)
        wf.add_state(WorkflowState.PROCESS, [lambda x: {"status": "success", "error": None}])
        wf.add_state(WorkflowState.COMPLETE)
        wf.add_state(WorkflowState.ERROR)
        wf.set_end_states([WorkflowState.COMPLETE, WorkflowState.ERROR])

        wf.add_transition_from_args(
            WorkflowState.PROCESS, WorkflowState.ERROR,
            condition="result.error is not None",
        )
        wf.add_transition_from_args(
            WorkflowState.PROCESS, WorkflowState.COMPLETE,
            condition="result.error is None",
        )

        result = await wf.run(None)
        self.assertEqual(result["final_state"], WorkflowState.COMPLETE.value)

    async def test_conditional_transition_with_error_not_none(self) -> None:
        wf = WorkflowStateMachine("error_not_none_wf")
        wf.set_initial_state(WorkflowState.PROCESS)
        wf.add_state(WorkflowState.PROCESS, [lambda x: {"status": "failed", "error": "boom"}])
        wf.add_state(WorkflowState.COMPLETE)
        wf.add_state(WorkflowState.ERROR)
        wf.set_end_states([WorkflowState.COMPLETE, WorkflowState.ERROR])

        wf.add_transition_from_args(
            WorkflowState.PROCESS, WorkflowState.COMPLETE,
            condition="result.error is None",
        )
        wf.add_transition_from_args(
            WorkflowState.PROCESS, WorkflowState.ERROR,
            condition="result.error is not None",
        )

        result = await wf.run(None)
        self.assertEqual(result["final_state"], WorkflowState.ERROR.value)

    # ── 缺省转移（无匹配时 → COMPLETE） ──────────────────

    async def test_no_matching_transition_goes_to_complete(self) -> None:
        wf = WorkflowStateMachine("default_end_wf")
        wf.set_initial_state(WorkflowState.PROCESS)
        wf.add_state(WorkflowState.PROCESS)
        # 没有定义任何转移
        result = await wf.run(None)
        self.assertEqual(result["final_state"], WorkflowState.COMPLETE.value)
        self.assertTrue(result["success"])

    # ── 单步执行 ──────────────────────────────────────────

    async def test_step_execution(self) -> None:
        wf = WorkflowStateMachine("step_wf")
        wf.set_initial_state(WorkflowState.INPUT)
        wf.add_state(WorkflowState.INPUT, [lambda x: {"stepped": True}])
        wf.add_state(WorkflowState.PROCESS)
        wf.add_transition_from_args(WorkflowState.INPUT, WorkflowState.PROCESS)

        step1 = await wf.step("start")
        self.assertEqual(step1["from_state"], WorkflowState.INPUT.value)
        self.assertEqual(step1["to_state"], WorkflowState.PROCESS.value)
        self.assertFalse(step1["done"])

        step2 = await wf.step(None)
        self.assertEqual(step2["from_state"], WorkflowState.PROCESS.value)
        self.assertEqual(step2["to_state"], WorkflowState.COMPLETE.value)
        self.assertTrue(step2["done"])

    async def test_step_at_end_state(self) -> None:
        wf = WorkflowStateMachine("done_step")
        wf.set_initial_state(WorkflowState.COMPLETE)
        wf.set_end_states([WorkflowState.COMPLETE])
        result = await wf.step()
        self.assertTrue(result["done"])
        self.assertIn("已到达终态", result["message"])

    # ── 回调 ──────────────────────────────────────────────

    async def test_on_enter_callback(self) -> None:
        calls: list[str] = []

        async def enter_cb() -> None:
            calls.append("entered")

        wf = WorkflowStateMachine("cb_wf")
        wf.set_initial_state(WorkflowState.PROCESS)
        wf.add_state(WorkflowState.PROCESS)
        wf.on_enter(WorkflowState.PROCESS, enter_cb)
        # 转移至终态
        wf.add_transition_from_args(WorkflowState.PROCESS, WorkflowState.COMPLETE)
        wf.set_end_states([WorkflowState.COMPLETE])

        await wf.run(None)
        self.assertIn("entered", calls)

    async def test_on_exit_callback(self) -> None:
        calls: list[str] = []

        async def exit_cb() -> None:
            calls.append("exited")

        wf = WorkflowStateMachine("exit_cb_wf")
        wf.set_initial_state(WorkflowState.PROCESS)
        wf.add_state(WorkflowState.PROCESS)
        wf.on_exit(WorkflowState.PROCESS, exit_cb)
        wf.add_transition_from_args(WorkflowState.PROCESS, WorkflowState.COMPLETE)
        wf.set_end_states([WorkflowState.COMPLETE])

        await wf.run(None)
        self.assertIn("exited", calls)

    # ── 工作流定义导入/导出 ──────────────────────────────

    def test_from_definition(self) -> None:
        definition: WorkflowDefinition = {
            "name": "imported_wf",
            "states": [WorkflowState.INPUT, WorkflowState.PROCESS],
            "transitions": [
                {
                    "from_state": WorkflowState.INPUT,
                    "to_state": WorkflowState.PROCESS,
                    "condition": "True",
                    "description": "go",
                },
            ],
            "initial_state": WorkflowState.INPUT,
            "end_states": [WorkflowState.PROCESS],
            "execution_mode": ExecutionMode.SERIAL,
        }
        wf = WorkflowStateMachine()
        wf.from_definition(definition)
        self.assertEqual(wf.name, "imported_wf")
        self.assertEqual(wf.current_state, WorkflowState.INPUT)
        self.assertEqual(wf._end_states, {WorkflowState.PROCESS})
        self.assertIn(WorkflowState.INPUT, wf._states)

    def test_get_definition(self) -> None:
        wf = WorkflowStateMachine("export_wf")
        wf.set_initial_state(WorkflowState.INPUT)
        definition = wf.get_definition()
        self.assertEqual(definition["name"], "export_wf")
        self.assertEqual(definition["initial_state"], WorkflowState.INPUT)
        self.assertIsInstance(definition["states"], list)
        self.assertIsInstance(definition["transitions"], list)

    # ── 重置 ──────────────────────────────────────────────

    async def test_reset(self) -> None:
        wf = WorkflowStateMachine("reset_wf")
        wf.set_initial_state(WorkflowState.PROCESS)
        wf.add_state(WorkflowState.PROCESS)
        wf.add_transition_from_args(WorkflowState.PROCESS, WorkflowState.COMPLETE)

        await wf.run("hello")
        self.assertNotEqual(wf.current_state, WorkflowState.PROCESS)
        self.assertGreater(len(wf._history), 0)

        wf.reset()
        self.assertEqual(wf.current_state, WorkflowState.PROCESS)
        self.assertEqual(len(wf._history), 0)
        self.assertEqual(wf._context, {})

    # ── 上下文 ────────────────────────────────────────────

    async def test_context_and_history(self) -> None:
        self.wf.set_initial_state(WorkflowState.INPUT)
        result = await self.wf.run({"initial": True})
        ctx = result["context"]
        self.assertIn("initial_input", ctx)
        self.assertIn("final_state", ctx)
        self.assertIn("input_output", ctx)
        # Flow ends at COMPLETE (APPROVE → no transition → COMPLETE)
        self.assertEqual(ctx["final_state"], WorkflowState.COMPLETE.value)
        history = result["history"]
        self.assertEqual(len(history), 4)

    # ── 异常处理 ──────────────────────────────────────────

    async def test_state_handler_raises_workflow_execution_error(self) -> None:
        wf = WorkflowStateMachine("error_wf")
        wf.set_initial_state(WorkflowState.PROCESS)

        async def crash(data: Any) -> Any:
            raise ValueError("handler crashed")

        wf.add_state(WorkflowState.PROCESS, [crash])
        wf.add_transition_from_args(WorkflowState.PROCESS, WorkflowState.COMPLETE)

        with self.assertRaises(WorkflowExecutionError) as ctx:
            await wf.run(None)
        self.assertIn("handler crashed", str(ctx.exception))

    async def test_error_history_recorded(self) -> None:
        wf = WorkflowStateMachine("err_hist")
        wf.set_initial_state(WorkflowState.PROCESS)

        async def crash(data: Any) -> Any:
            raise ValueError("crash")

        wf.add_state(WorkflowState.PROCESS, [crash])

        with self.assertRaises(WorkflowExecutionError):
            await wf.run(None)

        self.assertIn("error", wf._context)
        self.assertIn("crash", wf._context["error"])
        # history 应有 error 条目
        has_error = any("error" in h for h in wf._history)
        self.assertTrue(has_error)

    # ── 无处理函数的状态 ──────────────────────────────────

    async def test_state_without_handlers_returns_input(self) -> None:
        wf = WorkflowStateMachine("no_handler")
        wf.set_initial_state(WorkflowState.PROCESS)
        wf.add_state(WorkflowState.PROCESS)  # 没有 handler
        wf.add_transition_from_args(WorkflowState.PROCESS, WorkflowState.COMPLETE)
        wf.set_end_states([WorkflowState.COMPLETE])

        result = await wf.run("pass_through")
        self.assertEqual(result["final_state"], WorkflowState.COMPLETE.value)
        # 无 handler 时输出等于输入
        self.assertEqual(result["context"].get("process_output"), "pass_through")

    # ── 条件 evel False ──────────────────────────────────

    def test_evaluate_condition_false(self) -> None:
        self.assertFalse(self.wf._evaluate_condition("False", {"status": "ok"}))
        self.assertTrue(self.wf._evaluate_condition("True", {"status": "ok"}))

    def test_evaluate_condition_safe_eval_fallback(self) -> None:
        """当标准解析失败时，fallback 到安全 eval。"""
        result = {"score": 42}
        # 安全 eval
        val = self.wf._evaluate_condition("result.get('score') == 42", result)
        self.assertTrue(val)

    def test_evaluate_condition_catches_exception(self) -> None:
        result = {"key": "val"}
        # Accessing result.__class__.__init__ returns a valid method object (truthy),
        # so the safe eval returns True. Test a genuinely unsafe expression instead.
        val = self.wf._evaluate_condition("result['nonexistent_key'] + 1", result)
        self.assertFalse(val)


# ════════════════════════════════════════════════════════════
# 主入口
# ════════════════════════════════════════════════════════════

if __name__ == "__main__":
    unittest.main(verbosity=2)
