"""三省六部类型定义：TypedDict + Enum"""

from __future__ import annotations

import enum
from typing import Any, TypedDict

# ── 六部枚举 ──────────────────────────────────────────────

class Ministry(str, enum.Enum):
    """六部名称枚举"""
    LI_BU = "吏部"       # 人事任免
    HU_BU = "户部"       # 户籍财政
    LI_BU_RITES = "礼部"  # 礼仪祭祀
    BING_BU = "兵部"     # 军事
    XING_BU = "刑部"     # 司法刑狱
    GONG_BU = "工部"     # 工程建设


# ── 三省枚举 ──────────────────────────────────────────────

class Department(str, enum.Enum):
    """三省名称枚举"""
    ZHONG_SHU = "中书省"   # 决策
    MEN_XIA = "门下省"     # 审核
    SHANG_SHU = "尚书省"   # 执行


# ── 执行状态枚举 ──────────────────────────────────────────

class ExecutionStatus(str, enum.Enum):
    """执行状态"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CIRCUIT_OPEN = "circuit_open"
    SKIPPED = "skipped"


# ── 熔断器状态枚举 ────────────────────────────────────────

class CircuitState(str, enum.Enum):
    """熔断器状态"""
    CLOSED = "closed"       # 正常运行，请求通过
    OPEN = "open"           # 熔断打开，请求快速失败
    HALF_OPEN = "half_open"  # 半开状态，允许探测请求


# ── TypedDict ─────────────────────────────────────────────

class TaskPayload(TypedDict, total=False):
    """任务载荷——下发到六部的标准任务描述"""
    task_id: str
    action: str                         # 具体操作名，如 "browser_navigate"
    args: dict[str, Any]                # 操作参数
    metadata: dict[str, Any]            # 额外元数据
    timeout_seconds: float              # 超时时间
    retry_count: int                    # 已重试次数
    priority: int                       # 优先级（值越小越优先）


class ExecutionResult(TypedDict):
    """执行结果——六部统一返回结构"""
    status: ExecutionStatus
    data: Any | None                 # 成功时返回的数据
    error: str | None                # 失败时的错误消息
    duration_seconds: float             # 执行耗时
    task_id: str


class CircuitBreakerConfig(TypedDict, total=False):
    """熔断器配置"""
    failure_threshold: int              # 连续失败次数阈值，达到后断路
    recovery_timeout: float             # 恢复超时（秒），之后进入半开
    half_open_max_requests: int         # 半开状态下允许的最大探测请求数
    success_threshold: int              # 半开状态下连续成功次数，达到后闭合


# ── 默认值 ────────────────────────────────────────────────

DEFAULT_CIRCUIT_BREAKER_CONFIG: CircuitBreakerConfig = {
    "failure_threshold": 5,
    "recovery_timeout": 30.0,
    "half_open_max_requests": 1,
    "success_threshold": 2,
}


# ── 工作流状态枚举 ────────────────────────────────────────

class WorkflowState(str, enum.Enum):
    """工作流状态节点"""
    INIT = "init"
    INPUT = "input"
    PROCESS = "process"
    REVIEW = "review"
    APPROVE = "approve"
    REJECT = "reject"
    COMPLETE = "complete"
    ERROR = "error"
    CANCELLED = "cancelled"


# ── 执行模式枚举 ──────────────────────────────────────────

class ExecutionMode(str, enum.Enum):
    """执行模式：串行或并行"""
    SERIAL = "serial"
    PARALLEL = "parallel"


# ── 角色定义 ──────────────────────────────────────────────

class RoleDefinition(TypedDict, total=True):
    """角色定义——对标 CrewAI 的 Agent 角色"""
    name: str                          # 角色名称
    goal: str                          # 角色目标
    backstory: str                     # 角色背景故事
    allowed_ministries: list[str]      # 允许调度的部门列表
    priority: int                      # 优先级（值越小优先级越高）


# ── 工作流转移 ────────────────────────────────────────────

class WorkflowTransition(TypedDict, total=True):
    """状态转移定义"""
    from_state: WorkflowState          # 起始状态
    to_state: WorkflowState            # 目标状态
    condition: str                     # 转移条件表达式（如 "result.status == 'success'"）
    description: str                   # 转移描述


class WorkflowDefinition(TypedDict, total=False):
    """完整的工作流定义"""
    name: str
    states: list[WorkflowState]
    transitions: list[WorkflowTransition]
    initial_state: WorkflowState
    end_states: list[WorkflowState]
    execution_mode: ExecutionMode       # 串行/并行
    timeout_seconds: float
    roles: list[RoleDefinition]


# ── 路由结果 ──────────────────────────────────────────────

class RoutingResult(TypedDict, total=True):
    """部门间路由结果"""
    source_ministry: str               # 源部门
    target_ministry: str               # 目标部门
    task_id: str
    role_name: str                     # 执行此路由的角色
    reason: str                        # 路由原因
    result: ExecutionResult | None
