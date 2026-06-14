"""
OpenClaw AI Smart Router - Routing Engine
路由引擎 - 核心智能路由逻辑，整合分析器、选择器和满意度评估
"""

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from .ai_analyzer import AIAnalyzer
from .logger import get_logger
from .model_selector import ModelSelector
from .models import get_all_models
from .satisfaction_evaluator import SatisfactionEvaluator
from .smart_router_types import (
    ExecutionResult,
    InstructionAnalysis,
    ModelStatus,
    ModelTier,
    RouterConfig,
    RouterStats,
    RoutingContext,
    RoutingDecision,
    RoutingHistory,
    SatisfactionFeedback,
    TaskIntent,
)


@dataclass
class HistoryRecord:
    """内部历史记录"""
    task_id: str
    user_instruction: str
    analysis: InstructionAnalysis
    routing_decision: RoutingDecision
    execution_result: ExecutionResult | None = None
    feedback: SatisfactionFeedback | None = None
    timestamp: float = field(default_factory=time.time)


class RoutingEngine:
    """智能路由引擎"""

    def __init__(self, config: RouterConfig | None = None):
        self.config = config or RouterConfig()
        self.logger = get_logger("SmartRouter.RoutingEngine")

        # 初始化组件
        self.analyzer = AIAnalyzer()
        self.selector = ModelSelector()
        self.evaluator = SatisfactionEvaluator()

        # 历史存储
        self._sessions: dict[str, list[HistoryRecord]] = {}
        self._tasks: dict[str, HistoryRecord] = {}

        # 统计信息
        self._total_tasks = 0
        self._successful_tasks = 0
        self._failed_tasks = 0
        self._model_switch_count = 0
        self._tier_distribution: dict[ModelTier, int] = {}
        self._intent_distribution: dict[TaskIntent, int] = {}

        # 初始化统计
        self._initialize_stats()

    def _initialize_stats(self):
        """初始化统计字典"""
        for tier in ModelTier:
            self._tier_distribution[tier] = 0
        for intent in TaskIntent:
            self._intent_distribution[intent] = 0

    def set_ai_provider(self, provider):
        """设置AI提供者"""
        self.analyzer.set_ai_provider(provider)
        self.logger.info("AI provider set on analyzer")

    async def route(
        self,
        instruction: str,
        context: RoutingContext | None = None
    ) -> RoutingDecision:
        """
        路由用户指令
        """
        task_id = str(uuid.uuid4())
        session_id = context.session_id if context else "default"

        self.logger.info(f"Routing task {task_id}: {instruction[:80]}...")

        try:
            # 1. AI分析指令
            self.logger.debug(f"Task {task_id}: Analyzing instruction")
            analysis = await self.analyzer.analyze(instruction, context)
            self.logger.debug(
                f"Task {task_id}: Analysis result - "
                f"intent={analysis.intent.value}, complexity={analysis.complexity.value}"
            )

            # 2. 模型选择
            self.logger.debug(f"Task {task_id}: Selecting model")
            decision = self.selector.select(analysis, context)

            # 3. 检查是否需要升级（基于历史反馈）
            session_history = self._sessions.get(session_id, [])
            upgrade_suggestion = self.evaluator.evaluate_upgrade(
                task_id,
                analysis,
                decision.recommended_model,
                session_history
            )

            if upgrade_suggestion.should_upgrade and self.config.auto_upgrade_enabled:
                self.logger.info(
                    f"Task {task_id}: Upgrade suggested: {upgrade_suggestion.reason}"
                )
                decision = self._apply_upgrade(decision, upgrade_suggestion)

            # 4. 记录历史
            history_record = HistoryRecord(
                task_id=task_id,
                user_instruction=instruction,
                analysis=analysis,
                routing_decision=decision,
                timestamp=time.time()
            )
            self._record_history(session_id, history_record)

            # 5. 更新统计
            self._update_stats(analysis, decision)

            self.logger.info(
                f"Task {task_id}: Routing complete - "
                f"selected {decision.recommended_model.name} (confidence={decision.confidence:.2f})"
            )

            return decision

        except Exception as e:
            self.logger.error(f"Task {task_id}: Routing failed - {e}", exc_info=True)
            self._failed_tasks += 1
            raise

    def _apply_upgrade(
        self,
        current_decision: RoutingDecision,
        upgrade: Any  # UpgradeSuggestion type
    ) -> RoutingDecision:
        """应用升级建议"""
        all_models = get_all_models()
        tier_order = [ModelTier.FREE, ModelTier.STANDARD, ModelTier.PREMIUM, ModelTier.ENTERPRISE]

        current_tier_index = tier_order.index(current_decision.recommended_model.tier)
        target_tier_index = tier_order.index(upgrade.suggested_tier)

        if target_tier_index > current_tier_index:
            target_models = [
                m for m in all_models
                if tier_order.index(m.tier) >= target_tier_index and m.is_available
            ]

            if target_models:
                new_model = target_models[0]
                self._model_switch_count += 1

                self.logger.info(
                    f"Applying upgrade: {current_decision.recommended_model.name} "
                    f"-> {new_model.name}"
                )

                return RoutingDecision(
                    recommended_model=new_model,
                    alternative_models=current_decision.alternative_models,
                    fallback_model=current_decision.fallback_model,
                    reasoning=f"{current_decision.reasoning} | [升级: {upgrade.reason}]",
                    confidence=current_decision.confidence,
                    should_upgrade=True,
                    upgrade_reason=upgrade.reason
                )

        return current_decision

    async def report_result(self, task_id: str, result: ExecutionResult):
        """报告执行结果"""
        record = self._tasks.get(task_id)
        if not record:
            self.logger.warning(f"Task {task_id}: No history record found")
            return

        record.execution_result = result

        # 报告给选择器
        self.selector.report_execution_result(
            record.routing_decision.recommended_model.id,
            result.success
        )

        if result.success:
            self._successful_tasks += 1
        else:
            self._failed_tasks += 1

        if result.model_switched:
            self._model_switch_count += 1

        self.logger.info(
            f"Task {task_id}: Execution reported - "
            f"{'success' if result.success else 'failed'}"
        )

    async def submit_feedback(self, feedback: SatisfactionFeedback):
        """提交满意度反馈"""
        self.evaluator.submit_feedback(feedback)

        record = self._tasks.get(feedback.task_id)
        if record:
            record.feedback = feedback

        self.logger.info(
            f"Feedback received for task {feedback.task_id}: "
            f"rating={feedback.rating}"
        )

    async def get_history(self, session_id: str) -> list[RoutingHistory]:
        """获取会话历史"""
        session_records = self._sessions.get(session_id, [])

        history = []
        for record in session_records:
            history.append(RoutingHistory(
                task_id=record.task_id,
                user_instruction=record.user_instruction,
                analysis=record.analysis,
                routing_decision=record.routing_decision,
                execution_result=record.execution_result,
                feedback=record.feedback,
                timestamp=record.timestamp
            ))

        return history

    async def get_stats(self) -> RouterStats:
        """获取统计信息"""
        evaluator_stats = self.evaluator.get_satisfaction_stats()

        stats = RouterStats(
            total_tasks=self._total_tasks,
            successful_tasks=self._successful_tasks,
            failed_tasks=self._failed_tasks,
            average_satisfaction=evaluator_stats["average_rating"],
            model_switch_count=self._model_switch_count,
            tier_distribution=self._tier_distribution.copy(),
            intent_distribution=self._intent_distribution.copy(),
            average_tokens_saved=self._calculate_tokens_saved()
        )

        return stats

    def get_current_model_status(self) -> ModelStatus:
        """获取当前模型状态"""
        current_model = self.selector.get_current_model()
        evaluator_stats = self.evaluator.get_satisfaction_stats()

        return ModelStatus(
            current_model=current_model.id if current_model else "unknown",
            current_tier=current_model.tier if current_model else ModelTier.FREE,
            total_requests=self._total_tasks,
            average_satisfaction=evaluator_stats["average_rating"],
            model_usage_stats={
                tier.value: count for tier, count in self._tier_distribution.items()
            }
        )

    def update_config(self, config_updates: dict[str, Any]):
        """更新配置"""
        current_dict = self.config.to_dict()
        current_dict.update(config_updates)
        self.config = RouterConfig.from_dict(current_dict)

        # 同步更新子组件配置
        if "auto_upgrade_enabled" in config_updates:
            self.evaluator.update_config(
                SatisfactionEvaluator(auto_upgrade_enabled=config_updates["auto_upgrade_enabled"])
            )

        self.logger.info(f"Configuration updated with {len(config_updates)} changes")

    def get_config(self) -> RouterConfig:
        """获取当前配置"""
        return self.config

    def _record_history(self, session_id: str, record: HistoryRecord):
        """记录历史"""
        # 任务记录
        self._tasks[record.task_id] = record

        # 会话记录
        if session_id not in self._sessions:
            self._sessions[session_id] = []
        self._sessions[session_id].append(record)

        # 限制会话历史长度
        if len(self._sessions[session_id]) > 100:
            self._sessions[session_id] = self._sessions[session_id][-100:]

    def _update_stats(self, analysis: InstructionAnalysis, decision: RoutingDecision):
        """更新统计"""
        self._total_tasks += 1
        self._intent_distribution[analysis.intent] += 1
        self._tier_distribution[decision.recommended_model.tier] += 1

    def _calculate_tokens_saved(self) -> int:
        """计算节省的tokens"""
        free_usage = self._tier_distribution.get(ModelTier.FREE, 0)
        paid_usage = self._total_tasks - free_usage
        return paid_usage * 5000  # 假设估算

    def reset(self):
        """重置所有状态"""
        self._total_tasks = 0
        self._successful_tasks = 0
        self._failed_tasks = 0
        self._model_switch_count = 0
        self._tasks.clear()
        self._sessions.clear()
        self._initialize_stats()
        self.selector.reset_failure_count()
        self.evaluator.reset()
        self.logger.info("Routing engine reset")

    def export_state(self) -> dict[str, Any]:
        """导出状态"""
        return {
            "config": self.config.to_dict(),
            "stats": {
                "total_tasks": self._total_tasks,
                "successful_tasks": self._successful_tasks,
                "failed_tasks": self._failed_tasks,
                "model_switch_count": self._model_switch_count,
                "tier_distribution": {t.value: c for t, c in self._tier_distribution.items()},
                "intent_distribution": {i.value: c for i, c in self._intent_distribution.items()}
            },
            "current_model": self.selector.get_current_model().to_dict() if self.selector.get_current_model() else None
        }

    def import_state(self, state: dict[str, Any]):
        """导入状态"""
        if "stats" in state:
            stats = state["stats"]
            if "total_tasks" in stats:
                self._total_tasks = stats["total_tasks"]
            if "successful_tasks" in stats:
                self._successful_tasks = stats["successful_tasks"]
            if "failed_tasks" in stats:
                self._failed_tasks = stats["failed_tasks"]
            if "model_switch_count" in stats:
                self._model_switch_count = stats["model_switch_count"]
            if "tier_distribution" in stats:
                for tier_str, count in stats["tier_distribution"].items():
                    try:
                        tier = ModelTier(tier_str)
                        self._tier_distribution[tier] = count
                    except ValueError:
                        pass
        self.logger.info("State imported")

    def get_analyzer(self) -> AIAnalyzer:
        """获取分析器"""
        return self.analyzer

    def get_selector(self) -> ModelSelector:
        """获取模型选择器"""
        return self.selector

    def get_evaluator(self) -> SatisfactionEvaluator:
        """获取满意度评估器"""
        return self.evaluator
