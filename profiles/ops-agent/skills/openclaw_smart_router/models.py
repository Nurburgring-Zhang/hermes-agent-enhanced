"""
OpenClaw AI Smart Router - Model Registry
模型注册表 - 免费和付费模型配置
"""

from .smart_router_types import ModelCapabilities, ModelCost, ModelInfo, ModelTier

# 免费模型列表（优先使用）
FREE_MODELS: list[ModelInfo] = [
    ModelInfo(
        id="claude-3-haiku",
        name="Claude 3 Haiku",
        provider="Anthropic",
        tier=ModelTier.FREE,
        capabilities=ModelCapabilities(
            reasoning=True,
            code_generation=True,
            creative=True,
            analysis=True,
            vision=False,
            function_calling=True,
            long_context=False
        ),
        cost=ModelCost(input_cost=0, output_cost=0, is_free=True),
        max_tokens=200000,
        is_available=True
    ),
    ModelInfo(
        id="gpt-4o-mini",
        name="GPT-4o Mini",
        provider="OpenAI",
        tier=ModelTier.FREE,
        capabilities=ModelCapabilities(
            reasoning=True,
            code_generation=True,
            creative=True,
            analysis=True,
            vision=True,
            function_calling=True,
            long_context=False
        ),
        cost=ModelCost(input_cost=0, output_cost=0, is_free=True),
        max_tokens=128000,
        is_available=True
    ),
    ModelInfo(
        id="gemini-1.5-flash",
        name="Gemini 1.5 Flash",
        provider="Google",
        tier=ModelTier.FREE,
        capabilities=ModelCapabilities(
            reasoning=True,
            code_generation=True,
            creative=True,
            analysis=True,
            vision=True,
            function_calling=True,
            long_context=True
        ),
        cost=ModelCost(input_cost=0, output_cost=0, is_free=True),
        max_tokens=1000000,
        is_available=True
    ),
    ModelInfo(
        id="claude-3.5-sonnet",
        name="Claude 3.5 Sonnet",
        provider="Anthropic",
        tier=ModelTier.FREE,
        capabilities=ModelCapabilities(
            reasoning=True,
            code_generation=True,
            creative=True,
            analysis=True,
            vision=True,
            function_calling=True,
            long_context=True
        ),
        cost=ModelCost(input_cost=0, output_cost=0, is_free=True),
        max_tokens=200000,
        is_available=True
    )
]


# 标准模型列表
STANDARD_MODELS: list[ModelInfo] = [
    ModelInfo(
        id="gpt-4o",
        name="GPT-4o",
        provider="OpenAI",
        tier=ModelTier.STANDARD,
        capabilities=ModelCapabilities(
            reasoning=True,
            code_generation=True,
            creative=True,
            analysis=True,
            vision=True,
            function_calling=True,
            long_context=True
        ),
        cost=ModelCost(input_cost=5, output_cost=15, is_free=False),
        max_tokens=128000,
        is_available=True
    ),
    ModelInfo(
        id="claude-3-opus",
        name="Claude 3 Opus",
        provider="Anthropic",
        tier=ModelTier.STANDARD,
        capabilities=ModelCapabilities(
            reasoning=True,
            code_generation=True,
            creative=True,
            analysis=True,
            vision=True,
            function_calling=True,
            long_context=True
        ),
        cost=ModelCost(input_cost=15, output_cost=75, is_free=False),
        max_tokens=200000,
        is_available=True
    ),
    ModelInfo(
        id="gemini-1.5-pro",
        name="Gemini 1.5 Pro",
        provider="Google",
        tier=ModelTier.STANDARD,
        capabilities=ModelCapabilities(
            reasoning=True,
            code_generation=True,
            creative=True,
            analysis=True,
            vision=True,
            function_calling=True,
            long_context=True
        ),
        cost=ModelCost(input_cost=1.25, output_cost=5, is_free=False),
        max_tokens=2000000,
        is_available=True
    )
]


# 高级/专业模型列表
PREMIUM_MODELS: list[ModelInfo] = [
    ModelInfo(
        id="claude-3.5-sonnet-20241022",
        name="Claude 3.5 Sonnet (Latest)",
        provider="Anthropic",
        tier=ModelTier.PREMIUM,
        capabilities=ModelCapabilities(
            reasoning=True,
            code_generation=True,
            creative=True,
            analysis=True,
            vision=True,
            function_calling=True,
            long_context=True
        ),
        cost=ModelCost(input_cost=3, output_cost=15, is_free=False),
        max_tokens=200000,
        is_available=True
    ),
    ModelInfo(
        id="o1-preview",
        name="OpenAI o1 Preview",
        provider="OpenAI",
        tier=ModelTier.PREMIUM,
        capabilities=ModelCapabilities(
            reasoning=True,
            code_generation=True,
            creative=True,
            analysis=True,
            vision=False,
            function_calling=False,
            long_context=True
        ),
        cost=ModelCost(input_cost=15, output_cost=60, is_free=False),
        max_tokens=128000,
        is_available=True
    ),
    ModelInfo(
        id="o1-mini",
        name="OpenAI o1 Mini",
        provider="OpenAI",
        tier=ModelTier.PREMIUM,
        capabilities=ModelCapabilities(
            reasoning=True,
            code_generation=True,
            creative=False,
            analysis=True,
            vision=False,
            function_calling=False,
            long_context=True
        ),
        cost=ModelCost(input_cost=3, output_cost=12, is_free=False),
        max_tokens=128000,
        is_available=True
    ),
    ModelInfo(
        id="gemini-2.0-flash-exp",
        name="Gemini 2.0 Flash Experimental",
        provider="Google",
        tier=ModelTier.PREMIUM,
        capabilities=ModelCapabilities(
            reasoning=True,
            code_generation=True,
            creative=True,
            analysis=True,
            vision=True,
            function_calling=True,
            long_context=True
        ),
        cost=ModelCost(input_cost=0, output_cost=0, is_free=True),
        max_tokens=1000000,
        is_available=True
    )
]


# 企业级模型列表
ENTERPRISE_MODELS: list[ModelInfo] = [
    ModelInfo(
        id="claude-3-5-sonnet-v2",
        name="Claude 3.5 Sonnet V2",
        provider="Anthropic",
        tier=ModelTier.ENTERPRISE,
        capabilities=ModelCapabilities(
            reasoning=True,
            code_generation=True,
            creative=True,
            analysis=True,
            vision=True,
            function_calling=True,
            long_context=True
        ),
        cost=ModelCost(input_cost=3, output_cost=15, is_free=False),
        max_tokens=200000,
        is_available=True
    ),
    ModelInfo(
        id="gpt-4-turbo",
        name="GPT-4 Turbo",
        provider="OpenAI",
        tier=ModelTier.ENTERPRISE,
        capabilities=ModelCapabilities(
            reasoning=True,
            code_generation=True,
            creative=True,
            analysis=True,
            vision=True,
            function_calling=True,
            long_context=True
        ),
        cost=ModelCost(input_cost=10, output_cost=30, is_free=False),
        max_tokens=128000,
        is_available=True
    )
]


def get_all_models() -> list[ModelInfo]:
    """获取所有模型"""
    return FREE_MODELS + STANDARD_MODELS + PREMIUM_MODELS + ENTERPRISE_MODELS


def get_model_by_id(model_id: str) -> ModelInfo:
    """根据ID获取模型"""
    all_models = get_all_models()
    for model in all_models:
        if model.id == model_id:
            return model
    raise ValueError(f"Model with id '{model_id}' not found")


def get_models_by_tier(tier: ModelTier) -> list[ModelInfo]:
    """根据层级获取模型"""
    tier_map = {
        ModelTier.FREE: FREE_MODELS,
        ModelTier.STANDARD: STANDARD_MODELS,
        ModelTier.PREMIUM: PREMIUM_MODELS,
        ModelTier.ENTERPRISE: ENTERPRISE_MODELS
    }
    return tier_map.get(tier, []).copy()


def get_available_models(tier: ModelTier = None) -> list[ModelInfo]:
    """获取可用模型"""
    if tier:
        models = get_models_by_tier(tier)
    else:
        models = get_all_models()
    return [m for m in models if m.is_available]


# 意图到能力需求映射
INTENT_CAPABILITY_MAP: dict[str, list[str]] = {
    "general_chat": [],
    "code_generation": ["code_generation", "reasoning"],
    "code_review": ["code_generation", "analysis", "reasoning"],
    "creative_writing": ["creative", "reasoning"],
    "data_analysis": ["analysis", "reasoning"],
    "research": ["analysis", "reasoning", "long_context"],
    "image_understanding": ["vision"],
    "summarization": ["analysis"],
    "translation": ["reasoning"],
    "problem_solving": ["reasoning", "analysis"],
    "complex_reasoning": ["reasoning", "analysis"],
    "math_calculation": ["reasoning"],
    "multimodal": ["vision", "reasoning", "analysis", "creative"]
}


# 复杂度到模型层级映射
COMPLEXITY_TIER_MAP: dict[str, ModelTier] = {
    "simple": ModelTier.FREE,
    "moderate": ModelTier.FREE,
    "complex": ModelTier.STANDARD,
    "expert": ModelTier.PREMIUM
}


def get_best_free_model_for_capabilities(required_capabilities: list[str]) -> ModelInfo:
    """获取适合特定能力的最佳免费模型"""
    if not required_capabilities:
        return FREE_MODELS[0] if FREE_MODELS else None

    # 找到满足所有能力的免费模型
    for model in FREE_MODELS:
        has_all = all(
            getattr(model.capabilities, cap, False)
            for cap in required_capabilities
        )
        if has_all:
            return model

    # 如果没有完全满足的，返回第一个免费模型作为后备
    return FREE_MODELS[0] if FREE_MODELS else None


def get_best_paid_model_for_capabilities(required_capabilities: list[str]) -> ModelInfo:
    """获取适合特定能力的最佳付费模型"""
    paid_models = STANDARD_MODELS + PREMIUM_MODELS

    for model in paid_models:
        has_all = all(
            getattr(model.capabilities, cap, False)
            for cap in required_capabilities
        )
        if has_all:
            return model

    return paid_models[0] if paid_models else None
