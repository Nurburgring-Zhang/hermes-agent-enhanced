"""三省六部异常类定义"""

from __future__ import annotations

from typing import Any


class MinistryError(Exception):
    """所有六部异常的基类"""

    def __init__(
        self,
        message: str,
        ministry: str = "",
        task_id: str = "",
        details: dict[str, Any] | None = None,
    ) -> None:
        self.ministry = ministry
        self.task_id = task_id
        self.details = details or {}
        super().__init__(message)


class CircuitBreakerOpenError(MinistryError):
    """熔断器已打开，请求被拒绝"""

    def __init__(
        self,
        ministry: str,
        task_id: str = "",
        message: str = "",
    ) -> None:
        msg = message or f"[{ministry}] 熔断器已打开，拒绝执行任务"
        super().__init__(msg, ministry=ministry, task_id=task_id)


class TaskTimeoutError(MinistryError):
    """任务执行超时"""

    def __init__(
        self,
        ministry: str,
        task_id: str = "",
        timeout_seconds: float = 0.0,
        message: str = "",
    ) -> None:
        msg = message or f"[{ministry}] 任务超时 ({timeout_seconds}s): {task_id}"
        self.timeout_seconds = timeout_seconds
        super().__init__(msg, ministry=ministry, task_id=task_id)


class TaskExecutionError(MinistryError):
    """任务执行过程中出现的非超时错误"""

    def __init__(
        self,
        ministry: str,
        task_id: str = "",
        message: str = "",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, ministry=ministry, task_id=task_id, details=details)


class InvalidTaskError(MinistryError):
    """任务载荷校验不通过"""

    def __init__(
        self,
        ministry: str,
        task_id: str = "",
        reason: str = "",
    ) -> None:
        msg = f"[{ministry}] 无效任务: {reason}" if reason else f"[{ministry}] 无效任务"
        super().__init__(msg, ministry=ministry, task_id=task_id)


class PipelineExecutionError(MinistryError):
    """执行管道处理异常"""

    def __init__(
        self,
        ministry: str,
        task_id: str = "",
        stage: str = "",
        message: str = "",
    ) -> None:
        msg = f"[{ministry}] 管道阶段 '{stage}' 执行失败: {message}"
        self.stage = stage
        super().__init__(msg, ministry=ministry, task_id=task_id)


class WorkflowExecutionError(MinistryError):
    """工作流执行异常"""

    def __init__(
        self,
        workflow_name: str,
        state: str = "",
        task_id: str = "",
        message: str = "",
    ) -> None:
        msg = f"[工作流:{workflow_name}] 状态'{state}'执行失败: {message}"
        self.workflow_name = workflow_name
        self.state = state
        super().__init__(msg, ministry="workflow", task_id=task_id)


class WorkflowTransitionError(MinistryError):
    """工作流状态转移异常"""

    def __init__(
        self,
        workflow_name: str,
        from_state: str,
        to_state: str,
        task_id: str = "",
        reason: str = "",
    ) -> None:
        msg = f"[工作流:{workflow_name}] 从'{from_state}'到'{to_state}'转移失败: {reason}"
        self.workflow_name = workflow_name
        self.from_state = from_state
        self.to_state = to_state
        super().__init__(msg, ministry="workflow", task_id=task_id)


class RoleAssignmentError(MinistryError):
    """角色分配异常"""

    def __init__(
        self,
        role_name: str,
        ministry: str = "",
        task_id: str = "",
        reason: str = "",
    ) -> None:
        msg = f"[角色:{role_name}] 分配失败: {reason}"
        super().__init__(msg, ministry=ministry, task_id=task_id)
