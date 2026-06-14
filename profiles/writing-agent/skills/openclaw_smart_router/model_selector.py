"""
OpenClaw AI Smart Router - Model Selector
模型选择器 - 基于分析结果和用户偏好选择最合适的模型
"""

from dataclasses import dataclass

from .logger import get_logger
from .models import COMPLEXITY_TIER_MAP, FREE_MODELS, get_available_models
from .smart_router_types import (
    InstructionAnalysis,
    ModelInfo,
    ModelTier,
    RoutingContext,
    RoutingDecision,
    UserPreferences,
)


@dataclass
class ModelSelectorConfig:
    """模型选择器配置"""
    prefer_free_models: bool = True
    fallback_to_paid: bool = True
    max_cost_per_request: float = 1.0
    enable_tier_escalation: bool = True
    min_confidence_for_tier_escalation: float = 0.6


class ModelSelector:
    """模型选择器"""

    def __init__(self, config: ModelSelectorConfig | None = None):
        self.config = config or ModelSelectorConfig()
        self.logger = get_logger("SmartRouter.ModelSelector")
        self._current_model: ModelInfo | None = None
        self._consecutive_failures: dict[str, int] = {}

        # 初始化当前模型为第一个免费模型
        if FREE_MODELS:
            self._current_model = FREE_MODELS[0]

    def select(
        self,
        analysis: InstructionAnalysis,
        context: RoutingContext | None = None
    ) -> RoutingDecision:
        """
        选择最佳模型
        """
        preferences = context.preferences if context else None

        self.logger.debug(
            f"Selecting model: intent={analysis.intent.value}, "
            f"complexity={analysis.complexity.value}, confidence={analysis.confidence}"
        )

        # 1. 确定目标层级
        target_tier = self._determine_target_tier(analysis, preferences)

        # 2. 根据目标层级获取候选模型
        candidate_models = self._get_candidates_for_tier(target_tier)

        # 3. 过滤满足能力的模型
        candidate_models = self._filter_by_capabilities(
            candidate_models,
            analysis.required_capabilities
        )

        # 4. 应用用户偏好
        candidate_models = self._apply_preferences(candidate_models, preferences)

        # 5. 排序并选择最佳模型
        sorted_models = self._rank_models(candidate_models, analysis)
        recommended_model = sorted_models[0] if sorted_models else self._get_fallback_model()
        alternative_models = sorted_models[1:4] if len(sorted_models) > 1 else []

        # 6. 判断是否需要升级
        should_upgrade = self._should_escalate(analysis, recommended_model)
        upgrade_reason = None

        if should_upgrade:
            upgrade_reason = f"任务复杂度({analysis.complexity.value})需要更高层级的模型"
            self.logger.info(f"Upgrade suggested: {upgrade_reason}")

        # 更新当前模型
        self._current_model = recommended_model

        # 构建理由
        reasoning = self._build_reasoning(analysis, recommended_model)

        decision = RoutingDecision(
            recommended_model=recommended_model,
            alternative_models=alternative_models,
            fallback_model=self._get_fallback_model(),
            reasoning=reasoning,
            confidence=analysis.confidence,
            should_upgrade=should_upgrade,
            upgrade_reason=upgrade_reason
        )

        self.logger.info(f"Selected model: {recommended_model.name} ({recommended_model.provider})")
        return decision

    def _determine_target_tier(
        self,
        analysis: InstructionAnalysis,
        preferences: UserPreferences | None
    ) -> ModelTier:
        """确定目标模型层级"""
        # 用户强制指定层级
        if preferences and preferences.always_premium:
            return ModelTier.PREMIUM

        if preferences and preferences.preferred_tier:
            return preferences.preferred_tier

        # 基于复杂度的默认层级
        complexity_tier = COMPLEXITY_TIER_MAP.get(
            analysis.complexity.value,
            ModelTier.FREE
        )

        # 如果置信度低，提升一级
        if analysis.confidence < self.config.min_confidence_for_tier_escalation:
            return self._escalate_tier(complexity_tier)

        return complexity_tier

    def _escalate_tier(self, current_tier: ModelTier) -> ModelTier:
        """升级模型层级"""
        tier_order = [ModelTier.FREE, ModelTier.STANDARD, ModelTier.PREMIUM, ModelTier.ENTERPRISE]
        current_index = tier_order.index(current_tier)
        if current_index + 1 < len(tier_order):
            return tier_order[current_index + 1]
        return current_tier

    def _get_candidates_for_tier(self, tier: ModelTier) -> list[ModelInfo]:
        """获取特定层级的候选模型"""
        available_models = get_available_models()

        # 如果配置优先使用免费模型，并且有免费的，直接返回免费
        if self.config.prefer_free_models:
            free_models = [m for m in available_models if m.tier == ModelTier.FREE]
            if free_models:
                return free_models

        # 返回指定层级及以上的模型
        tier_order = [ModelTier.FREE, ModelTier.STANDARD, ModelTier.PREMIUM, ModelTier.ENTERPRISE]
        tier_index = tier_order.index(tier)

        candidates = []
        for i in range(tier_index, len(tier_order)):
            current_tier = tier_order[i]
            candidates.extend([m for m in available_models if m.tier == current_tier])

        return candidates

    def _filter_by_capabilities(
        self,
        models: list[ModelInfo],
        required_capabilities: list[str]
    ) -> list[ModelInfo]:
        """根据能力需求过滤模型"""
        if not required_capabilities:
            return models

        filtered = []
        for model in models:
            has_all = all(
                getattr(model.capabilities, cap, False)
                for cap in required_capabilities
            )
            if has_all:
                filtered.append(model)

        return filtered

    def _apply_preferences(
        self,
        models: list[ModelInfo],
        preferences: UserPreferences | None
    ) -> list[ModelInfo]:
        """应用用户偏好"""
        if not preferences:
            return models

        filtered = models.copy()

        # 排除指定模型
        if preferences.exclude_models:
            filtered = [m for m in filtered if m.id not in preferences.exclude_models]

        # 按成本过滤
        if preferences.max_cost is not None:
            filtered = [
                m for m in filtered
                if m.cost.is_free or (m.cost.input_cost + m.cost.output_cost) <= preferences.max_cost
            ]

        # 优先免费
        if preferences.preferred_tier == ModelTier.FREE or self.config.prefer_free_models:
            free_models = [m for m in filtered if m.cost.is_free]
            if free_models:
                return free_models

        return filtered

    def _rank_models(
        self,
        models: list[ModelInfo],
        analysis: InstructionAnalysis
    ) -> list[ModelInfo]:
        """对模型进行排序"""
        return sorted(models, key=lambda m: self._calculate_model_score(m, analysis), reverse=True)

    def _calculate_model_score(self, model: ModelInfo, analysis: InstructionAnalysis) -> float:
        """计算模型评分"""
        score = 100.0

        # 能力匹配度 (0-40分)
        capability_match = sum(
            1 for cap in analysis.required_capabilities
            if getattr(model.capabilities, cap, False)
        )
        required_count = max(1, len(analysis.required_capabilities))
        score += (capability_match / required_count) * 40

        # 成本因素 (0-30分，免费30分)
        if model.cost.is_free:
            score += 30
        else:
            total_cost = model.cost.input_cost + model.cost.output_cost
            cost_score = max(0, 30 - total_cost / 2)  # 成本越低分越高
            score += cost_score

        # 层级匹配度 (0-20分)
        target_tier = COMPLEXITY_TIER_MAP.get(analysis.complexity.value, ModelTier.FREE)
        tier_order = [ModelTier.FREE, ModelTier.STANDARD, ModelTier.PREMIUM, ModelTier.ENTERPRISE]
        tier_diff = abs(tier_order.index(model.tier) - tier_order.index(target_tier))
        score += max(0, 20 - tier_diff * 5)

        # 错误惩罚 (最多减10分)
        failure_count = self._consecutive_failures.get(model.id, 0)
        score -= min(10, failure_count * 2)

        # 长上下文加分
        if "long_context" in analysis.required_capabilities:
            if model.capabilities.long_context:
                score += 10
            else:
                score -= 20

        return score

    def _should_escalate(self, analysis: InstructionAnalysis, model: ModelInfo) -> bool:
        """检查是否需要升级"""
        if not self.config.enable_tier_escalation:
            return False

        # 专家级任务需要高级模型
        if analysis.complexity == TaskComplexity.EXPERT:
            return model.tier not in (ModelTier.PREMIUM, ModelTier.ENTERPRISE)

        # 检查能力缺失
        missing_capabilities = [
            cap for cap in analysis.required_capabilities
            if not getattr(model.capabilities, cap, False)
        ]

        return len(missing_capabilities) > 0

    def _get_fallback_model(self) -> ModelInfo:
        """获取后备模型"""
        available_models = get_available_models()

        # 优先免费
        free_models = [m for m in available_models if m.tier == ModelTier.FREE]
        if free_models:
            return free_models[0]

        # 次选标准
        standard_models = [m for m in available_models if m.tier == ModelTier.STANDARD]
        if standard_models:
            return standard_models[0]

        # 最后返回任意可用模型
        return available_models[0] if available_models else self._current_model or FREE_MODELS[0]

    def _build_reasoning(self, analysis: InstructionAnalysis, model: ModelInfo) -> str:
        """构建决策理由"""
        parts = [
            f"选择 {model.name} ({model.provider})",
            f"原因: 意图={analysis.intent.value}, 复杂度={analysis.complexity.value}",
            f"所需能力: {', '.join(analysis.required_capabilities) or '无特殊要求'}",
            f"模型层级: {model.tier.value}",
            f"成本: {'免费' if model.cost.is_free else f'${model.cost.input_cost + model.cost.output_cost}/1M tokens'}"
        ]
        return " | ".join(parts)

    def report_execution_result(self, model_id: str, success: bool):
        """报告执行结果"""
        if success:
            self._consecutive_failures.pop(model_id, None)
        else:
            count = self._consecutive_failures.get(model_id, 0) + 1
            self._consecutive_failures[model_id] = count

            if count >= 3 and self.config.fallback_to_paid:
                self.logger.warning(
                    f"模型 {model_id} 连续失败 {count} 次，建议切换到备用模型"
                )

    def get_current_model(self) -> ModelInfo | None:
        """获取当前模型"""
        return self._current_model

    def get_failure_stats(self) -> dict[str, int]:
        """获取失败统计"""
        return self._consecutive_failures.copy()

    def reset_failure_count(self, model_id: str | None = None):
        """重置失败计数"""
        if model_id:
            self._consecutive_failures.pop(model_id, None)
        else:
            self._consecutive_failures.clear()

    def update_config(self, config: ModelSelectorConfig):
        """更新配置"""
        self.config = config

    def clear_stats(self):
        """清除统计信息"""
        self._consecutive_failures.clear()
        self._current_model = FREE_MODELS[0] if FREE_MODELS else None
