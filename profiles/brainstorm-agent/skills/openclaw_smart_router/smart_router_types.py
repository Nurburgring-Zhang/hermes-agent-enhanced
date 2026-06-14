"""
OpenClaw AI Smart Router - Type Definitions
智能路由系统类型定义
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional


class ModelTier(str, Enum):
    """模型能力等级"""
    FREE = "free"
    STANDARD = "standard"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"


class TaskIntent(str, Enum):
    """任务意图"""
    GENERAL_CHAT = "general_chat"
    CODE_GENERATION = "code_generation"
    CODE_REVIEW = "code_review"
    CREATIVE_WRITING = "creative_writing"
    DATA_ANALYSIS = "data_analysis"
    RESEARCH = "research"
    IMAGE_UNDERSTANDING = "image_understanding"
    SUMMARIZATION = "summarization"
    TRANSLATION = "translation"
    PROBLEM_SOLVING = "problem_solving"
    COMPLEX_REASONING = "complex_reasoning"
    MATH_CALCULATION = "math_calculation"
    MULTIMODAL = "multimodal"


class TaskComplexity(str, Enum):
    """任务复杂度"""
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"
    EXPERT = "expert"


@dataclass
class ModelCapabilities:
    """模型能力"""
    reasoning: bool = False  # 推理能力
    code_generation: bool = False  # 代码生成
    creative: bool = False  # 创意写作
    analysis: bool = False  # 分析能力
    vision: bool = False  # 视觉理解
    function_calling: bool = False  # 函数调用
    long_context: bool = False  # 长上下文

    def to_dict(self) -> dict[str, Any]:
        return {
            "reasoning": self.reasoning,
            "code_generation": self.code_generation,
            "creative": self.creative,
            "analysis": self.analysis,
            "vision": self.vision,
            "function_calling": self.function_calling,
            "long_context": self.long_context
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ModelCapabilities":
        return cls(**data)


@dataclass
class ModelCost:
    """模型成本"""
    input_cost: float = 0.0  # 输入成本 (per 1M tokens)
    output_cost: float = 0.0  # 输出成本 (per 1M tokens)
    is_free: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "input_cost": self.input_cost,
            "output_cost": self.output_cost,
            "is_free": self.is_free
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ModelCost":
        return cls(**data)


@dataclass
class ModelInfo:
    """模型信息"""
    id: str
    name: str
    provider: str
    tier: ModelTier
    capabilities: ModelCapabilities
    cost: ModelCost
    max_tokens: int
    is_available: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "provider": self.provider,
            "tier": self.tier.value,
            "capabilities": self.capabilities.to_dict(),
            "cost": self.cost.to_dict(),
            "max_tokens": self.max_tokens,
            "is_available": self.is_available
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ModelInfo":
        data["capabilities"] = ModelCapabilities.from_dict(data["capabilities"])
        data["cost"] = ModelCost.from_dict(data["cost"])
        data["tier"] = ModelTier(data["tier"])
        return cls(**data)


@dataclass
class InstructionAnalysis:
    """指令分析结果"""
    intent: TaskIntent
    complexity: TaskComplexity
    required_capabilities: list[str]
    estimated_tokens: int
    language: str
    confidence: float
    reasoning: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "intent": self.intent.value,
            "complexity": self.complexity.value,
            "required_capabilities": self.required_capabilities,
            "estimated_tokens": self.estimated_tokens,
            "language": self.language,
            "confidence": self.confidence,
            "reasoning": self.reasoning
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "InstructionAnalysis":
        data["intent"] = TaskIntent(data["intent"])
        data["complexity"] = TaskComplexity(data["complexity"])
        return cls(**data)


@dataclass
class RoutingDecision:
    """路由决策"""
    recommended_model: ModelInfo
    alternative_models: list[ModelInfo] = field(default_factory=list)
    fallback_model: ModelInfo | None = None
    reasoning: str = ""
    confidence: float = 0.0
    should_upgrade: bool = False
    upgrade_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "recommended_model": self.recommended_model.to_dict(),
            "alternative_models": [m.to_dict() for m in self.alternative_models],
            "fallback_model": self.fallback_model.to_dict() if self.fallback_model else None,
            "reasoning": self.reasoning,
            "confidence": self.confidence,
            "should_upgrade": self.should_upgrade,
            "upgrade_reason": self.upgrade_reason
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RoutingDecision":
        if "recommended_model" in data:
            data["recommended_model"] = ModelInfo.from_dict(data["recommended_model"])
        if "alternative_models" in data:
            data["alternative_models"] = [ModelInfo.from_dict(m) for m in data["alternative_models"]]
        if data.get("fallback_model"):
            data["fallback_model"] = ModelInfo.from_dict(data["fallback_model"])
        return cls(**data)


@dataclass
class SatisfactionFeedback:
    """用户满意度反馈"""
    task_id: str
    model_used: str
    rating: int  # 1-5 星评分
    is_satisfied: bool
    issues: list[str] | None = None
    improvement_areas: list[str] | None = None
    would_retry: bool = False
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "model_used": self.model_used,
            "rating": self.rating,
            "is_satisfied": self.is_satisfied,
            "issues": self.issues,
            "improvement_areas": self.improvement_areas,
            "would_retry": self.would_retry,
            "timestamp": self.timestamp
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SatisfactionFeedback":
        return cls(**data)


@dataclass
class RoutingHistory:
    """路由历史记录"""
    task_id: str
    user_instruction: str
    analysis: InstructionAnalysis
    routing_decision: RoutingDecision
    execution_result: Optional["ExecutionResult"] = None
    feedback: SatisfactionFeedback | None = None
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "user_instruction": self.user_instruction,
            "analysis": self.analysis.to_dict(),
            "routing_decision": self.routing_decision.to_dict(),
            "execution_result": self.execution_result.to_dict() if self.execution_result else None,
            "feedback": self.feedback.to_dict() if self.feedback else None,
            "timestamp": self.timestamp
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RoutingHistory":
        if "analysis" in data:
            data["analysis"] = InstructionAnalysis.from_dict(data["analysis"])
        if "routing_decision" in data:
            data["routing_decision"] = RoutingDecision.from_dict(data["routing_decision"])
        if data.get("execution_result"):
            data["execution_result"] = ExecutionResult.from_dict(data["execution_result"])
        if data.get("feedback"):
            data["feedback"] = SatisfactionFeedback.from_dict(data["feedback"])
        return cls(**data)


@dataclass
class ExecutionResult:
    """执行结果"""
    success: bool
    response: str | None = None
    error: str | None = None
    tokens_used: int | None = None
    execution_time: float = 0.0
    model_switched: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "response": self.response,
            "error": self.error,
            "tokens_used": self.tokens_used,
            "execution_time": self.execution_time,
            "model_switched": self.model_switched
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ExecutionResult":
        return cls(**data)


@dataclass
class UserPreferences:
    """用户偏好"""
    preferred_tier: ModelTier | None = None
    max_cost: float | None = None  # 最大成本 ($ per 1M tokens)
    preferred_language: str | None = None
    exclude_models: list[str] = field(default_factory=list)
    always_premium: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "preferred_tier": self.preferred_tier.value if self.preferred_tier else None,
            "max_cost": self.max_cost,
            "preferred_language": self.preferred_language,
            "exclude_models": self.exclude_models,
            "always_premium": self.always_premium
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "UserPreferences":
        if data.get("preferred_tier"):
            data["preferred_tier"] = ModelTier(data["preferred_tier"])
        return cls(**data)


@dataclass
class RoutingContext:
    """路由上下文"""
    user_id: str | None = None
    session_id: str = "default"
    conversation_history: list[dict[str, str]] | None = None  # [{'role': 'user'|'assistant', 'content': '...'}]
    preferences: UserPreferences | None = None
    metadata: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "session_id": self.session_id,
            "conversation_history": self.conversation_history,
            "preferences": self.preferences.to_dict() if self.preferences else None,
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RoutingContext":
        if data.get("preferences"):
            data["preferences"] = UserPreferences.from_dict(data["preferences"])
        return cls(**data)


@dataclass
class RouterConfig:
    """路由配置"""
    default_free_model: str = "claude-3-haiku"
    default_standard_model: str = "gpt-4o"
    default_premium_model: str = "claude-3.5-sonnet-20241022"
    auto_upgrade_enabled: bool = True
    upgrade_threshold: int = 3  # 满意度阈值，低于此值自动升级
    max_consecutive_failures: int = 3  # 连续失败次数阈值
    models: list[ModelInfo] = field(default_factory=list)
    analysis_model: str = "claude-3-haiku"  # 用于分析指令的模型
    analysis_prompt: str | None = None  # 自定义分析提示词
    enable_cache: bool = True
    cache_expiration: int = 3600000  # 缓存过期时间(ms)
    log_level: str = "info"  # 'debug' | 'info' | 'warn' | 'error'
    log_file: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "default_free_model": self.default_free_model,
            "default_standard_model": self.default_standard_model,
            "default_premium_model": self.default_premium_model,
            "auto_upgrade_enabled": self.auto_upgrade_enabled,
            "upgrade_threshold": self.upgrade_threshold,
            "max_consecutive_failures": self.max_consecutive_failures,
            "models": [m.to_dict() for m in self.models],
            "analysis_model": self.analysis_model,
            "analysis_prompt": self.analysis_prompt,
            "enable_cache": self.enable_cache,
            "cache_expiration": self.cache_expiration,
            "log_level": self.log_level,
            "log_file": self.log_file
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RouterConfig":
        if "models" in data:
            data["models"] = [ModelInfo.from_dict(m) for m in data["models"]]
        return cls(**data)


@dataclass
class ModelStatus:
    """模型状态"""
    current_model: str
    current_tier: ModelTier
    total_requests: int
    average_satisfaction: float
    model_usage_stats: dict[str, int]

    def to_dict(self) -> dict[str, Any]:
        return {
            "current_model": self.current_model,
            "current_tier": self.current_tier.value,
            "total_requests": self.total_requests,
            "average_satisfaction": self.average_satisfaction,
            "model_usage_stats": self.model_usage_stats
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ModelStatus":
        data["current_tier"] = ModelTier(data["current_tier"])
        return cls(**data)


@dataclass
class RouterStats:
    """路由统计"""
    total_tasks: int = 0
    successful_tasks: int = 0
    failed_tasks: int = 0
    average_satisfaction: float = 0.0
    model_switch_count: int = 0
    tier_distribution: dict[ModelTier, int] = field(default_factory=dict)
    intent_distribution: dict[TaskIntent, int] = field(default_factory=dict)
    average_tokens_saved: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_tasks": self.total_tasks,
            "successful_tasks": self.successful_tasks,
            "failed_tasks": self.failed_tasks,
            "average_satisfaction": self.average_satisfaction,
            "model_switch_count": self.model_switch_count,
            "tier_distribution": {k.value: v for k, v in self.tier_distribution.items()},
            "intent_distribution": {k.value: v for k, v in self.intent_distribution.items()},
            "average_tokens_saved": self.average_tokens_saved
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RouterStats":
        if "tier_distribution" in data:
            data["tier_distribution"] = {ModelTier(k): v for k, v in data["tier_distribution"].items()}
        if "intent_distribution" in data:
            data["intent_distribution"] = {TaskIntent(k): v for k, v in data["intent_distribution"].items()}
        return cls(**data)
