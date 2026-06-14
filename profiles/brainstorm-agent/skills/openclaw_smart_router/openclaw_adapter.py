"""
OpenClaw AI Smart Router - OpenClaw Adapter
OpenClaw集成适配器 - 将智能路由系统集成到OpenClaw中
"""

import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from .logger import get_logger
from .routing_engine import RoutingEngine
from .smart_router_types import (
    ExecutionResult,
    InstructionAnalysis,
    ModelInfo,
    ModelTier,
    RouterConfig,
    RoutingContext,
    RoutingDecision,
    SatisfactionFeedback,
)


@dataclass
class OpenClawAdapterConfig:
    """OpenClaw适配器配置"""
    router_config: RouterConfig | None = None
    auto_initialize: bool = True
    intercept_all_requests: bool = False
    enable_feedback_collection: bool = True
    feedback_collection_delay: float = 2.0  # 秒


class OpenClawSmartRouterAdapter:
    """OpenClaw智能路由适配器"""

    def __init__(self, config: OpenClawAdapterConfig | None = None):
        self.config = config or OpenClawAdapterConfig()
        self.logger = get_logger("SmartRouter.Adapter")
        self.router = RoutingEngine(self.config.router_config)
        self._current_task_id: str | None = None
        self._is_initialized: bool = False

        # 回调函数
        self._on_model_selected: Callable[[ModelInfo], None] | None = None
        self._on_upgrade_triggered: Callable[[str], None] | None = None
        self._on_feedback_received: Callable[[SatisfactionFeedback], None] | None = None
        self._on_analysis_complete: Callable[[InstructionAnalysis], None] | None = None

    async def initialize(self) -> None:
        """初始化适配器"""
        if self._is_initialized:
            self.logger.info("Adapter already initialized")
            return

        self.logger.info("Initializing OpenClaw Smart Router Adapter...")

        # 检查配置
        config = self.router.get_config()
        if not config.models:
            raise ValueError("No models configured")

        model_names = [m.name for m in config.models if m.is_available]
        self.logger.info(f"Initialized with {len(model_names)} available models")
        self.logger.debug(f"Available models: {', '.join(model_names)}")

        self._is_initialized = True

    def is_initialized(self) -> bool:
        """检查是否已初始化"""
        return self._is_initialized

    async def handle_instruction(
        self,
        instruction: str,
        context: RoutingContext | None = None
    ) -> RoutingDecision:
        """
        处理用户指令 - 主要入口
        """
        if not self._is_initialized:
            await self.initialize()

        self.logger.info(f"Handling instruction: {instruction[:80]}...")

        # 执行路由
        decision = await self.router.route(instruction, context)

        # 存储当前任务ID
        self._current_task_id = decision.recommended_model.id

        # 触发回调
        self._on_model_selected(decision.recommended_model) if self._on_model_selected else None

        if decision.should_upgrade:
            reason = decision.upgrade_reason or "自动升级"
            self._on_upgrade_triggered(reason) if self._on_upgrade_triggered else None

        # 触发分析完成回调（通过提取分析）
        # 注意：需要从路由引擎获取分析结果，这里简化处理
        if self._on_analysis_complete:
            try:
                # 注意：当前决策可能已包含分析信息
                # 这里需要从路由器获取完整分析
                pass
            except Exception as e:
                self.logger.warning(f"Failed to trigger analysis callback: {e}")

        return decision

    async def report_execution(self, result: ExecutionResult) -> None:
        """
        报告执行结果
        """
        if not self._current_task_id:
            self.logger.warning("No active task ID to report execution for")
            return

        await self.router.report_result(self._current_task_id, result)

        # 如果失败，检查是否需要升级
        if not result.success and self.config.enable_feedback_collection:
            self._check_for_upgrade_needed()

    def _check_for_upgrade_needed(self):
        """检查是否需要升级"""
        try:
            # 这里可以异步调用，但为简化保持同步
            import asyncio
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(self._async_check_upgrade())
            else:
                loop.run_until_complete(self._async_check_upgrade())
        except Exception as e:
            self.logger.warning(f"Failed to check upgrade: {e}")

    async def _async_check_upgrade(self):
        """异步检查升级"""
        try:
            stats = await self.router.get_stats()
            if stats.total_tasks > 5:
                success_rate = stats.successful_tasks / stats.total_tasks
                if success_rate < 0.7:
                    self._on_upgrade_triggered(
                        f"成功率过低 ({success_rate * 100:.0f}%)"
                    ) if self._on_upgrade_triggered else None
        except Exception as e:
            self.logger.warning(f"Failed to get stats for upgrade check: {e}")

    async def submit_user_feedback(
        self,
        rating: int,
        comments: str | None = None
    ) -> None:
        """
        提交用户反馈
        """
        if not self._current_task_id:
            self.logger.warning("No active task ID to submit feedback for")
            return

        feedback = SatisfactionFeedback(
            task_id=self._current_task_id,
            model_used=self.router.get_current_model_status().current_model,
            rating=rating,
            is_satisfied=rating >= 3,
            issues=[comments] if comments else None,
            would_retry=rating >= 4,
            timestamp=time.time()
        )

        await self.router.submit_feedback(feedback)
        self._on_feedback_received(feedback) if self._on_feedback_received else None

        # 如果评分低于阈值，触发升级提醒
        threshold = self.router.get_config().upgrade_threshold
        if rating < threshold and self.config.enable_feedback_collection:
            self._on_upgrade_triggered(
                f"用户评分过低 ({rating}分)"
            ) if self._on_upgrade_triggered else None

    async def quick_feedback(self, is_satisfied: bool) -> None:
        """快速反馈 - 简单的好坏评价"""
        rating = 4 if is_satisfied else 2
        await self.submit_user_feedback(rating)

    def get_status(self) -> dict[str, Any]:
        """获取当前状态"""
        model_status = self.router.get_current_model_status()

        return {
            "is_initialized": self._is_initialized,
            "current_model": model_status.current_model,
            "current_tier": model_status.current_tier.value if model_status.current_tier else "unknown",
            "total_tasks": model_status.total_requests,
            "average_satisfaction": model_status.average_satisfaction,
            "model_switch_count": 0  # 需要从路由器统计获取
        }

    async def get_statistics(self) -> dict[str, Any]:
        """获取统计信息"""
        stats = await self.router.get_stats()

        return {
            "total_tasks": stats.total_tasks,
            "successful_tasks": stats.successful_tasks,
            "failed_tasks": stats.failed_tasks,
            "success_rate": (
                round((stats.successful_tasks / stats.total_tasks * 100), 1)
                if stats.total_tasks > 0 else 0.0
            ),
            "average_satisfaction": round(stats.average_satisfaction, 2),
            "model_distribution": {
                tier.value: count for tier, count in stats.tier_distribution.items()
            },
            "intent_distribution": {
                intent.value: count for intent, count in stats.intent_distribution.items()
            }
        }

    async def switch_model(self, model_id: str) -> bool:
        """
        强制切换模型
        """
        config = self.router.get_config()
        model = next((m for m in config.models if m.id == model_id), None)

        if not model:
            self.logger.error(f"Model {model_id} does not exist")
            return False

        # 更新配置中的默认模型
        if model.tier == ModelTier.FREE:
            self.router.update_config({"default_free_model": model_id})
        elif model.tier == ModelTier.STANDARD:
            self.router.update_config({"default_standard_model": model_id})
        elif model.tier == ModelTier.PREMIUM:
            self.router.update_config({"default_premium_model": model_id})

        self.logger.info(f"Switched to model: {model.name}")
        return True

    def reset(self):
        """重置路由系统"""
        self.router.reset()
        self._current_task_id = None
        self.logger.info("Router system reset")

    def set_callbacks(
        self,
        callbacks: dict[str, Callable]
    ):
        """设置回调函数"""
        self._on_model_selected = callbacks.get("on_model_selected")
        self._on_upgrade_triggered = callbacks.get("on_upgrade_triggered")
        self._on_feedback_received = callbacks.get("on_feedback_received")
        self._on_analysis_complete = callbacks.get("on_analysis_complete")

    def get_router(self) -> RoutingEngine:
        """获取底层路由引擎"""
        return self.router

    def get_config(self) -> OpenClawAdapterConfig:
        """获取适配器配置"""
        return self.config

    async def get_detailed_stats(self) -> dict[str, Any]:
        """获取详细统计"""
        router_stats = await self.router.get_stats()
        evaluator_stats = self.router.get_evaluator().get_satisfaction_stats()
        model_status = self.router.get_current_model_status()

        return {
            "routing": router_stats.to_dict(),
            "satisfaction": evaluator_stats,
            "current_model": model_status.to_dict(),
            "cache_stats": self.router.get_analyzer().get_cache_stats(),
            "failure_stats": self.router.get_selector().get_failure_stats()
        }

    async def health_check(self) -> dict[str, Any]:
        """健康检查"""
        try:
            stats = await self.get_detailed_stats()
            config = self.router.get_config()

            issues = []

            if not config.models:
                issues.append("No models configured")

            available_count = sum(1 for m in config.models if m.is_available)
            if available_count == 0:
                issues.append("No models available")

            if stats["routing"]["total_tasks"] > 0:
                success_rate = (
                    stats["routing"]["successful_tasks"] /
                    stats["routing"]["total_tasks"]
                )
                if success_rate < 0.5:
                    issues.append(f"Low success rate: {success_rate:.1%}")

            return {
                "healthy": len(issues) == 0,
                "issues": issues,
                "stats": stats,
                "timestamp": time.time()
            }
        except Exception as e:
            return {
                "healthy": False,
                "issues": [f"Health check failed: {e!s}"],
                "timestamp": time.time()
            }
