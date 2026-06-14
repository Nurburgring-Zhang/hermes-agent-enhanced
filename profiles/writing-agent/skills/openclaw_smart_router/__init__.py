"""
OpenClaw AI Smart Router - Main Entry Point
智能路由系统主入口

提供统一的接口来使用智能路由功能，包括:
- 快速路由
- 智能模型选择
- 满意度反馈
- 性能统计
- 配置管理
"""

import time
from collections.abc import Callable
from typing import Any, Dict, List, Optional

from .cache import SmartRouterCache
from .config_loader import ConfigLoader, get_default_config
from .logger import get_logger, setup_logging_from_config
from .openclaw_adapter import OpenClawAdapterConfig, OpenClawSmartRouterAdapter
from .routing_engine import RoutingEngine
from .smart_router_types import (
    ExecutionResult,
    ModelInfo,
    ModelTier,
    RouterConfig,
    RoutingContext,
    RoutingDecision,
    SatisfactionFeedback,
    TaskComplexity,
    TaskIntent,
    UserPreferences,
)

# 导出所有类型和类
__all__ = [
    # 类型
    "ModelTier", "TaskIntent", "TaskComplexity",
    "ModelCapabilities", "ModelCost", "ModelInfo",
    "InstructionAnalysis", "RoutingDecision", "SatisfactionFeedback",
    "RoutingHistory", "ExecutionResult", "UserPreferences",
    "RoutingContext", "RouterConfig", "ModelStatus", "RouterStats",

    # 核心类
    "RoutingEngine",
    "OpenClawSmartRouterAdapter",
    "ConfigLoader",
    "SmartRouterCache",
    "AIAnalyzer",
    "ModelSelector",
    "SatisfactionEvaluator",

    # 模型注册表
    "get_all_models",
    "get_model_by_id",
    "get_models_by_tier",
    "get_available_models",
    "FREE_MODELS",
    "STANDARD_MODELS",
    "PREMIUM_MODELS",
    "ENTERPRISE_MODELS",

    # 便捷函数
    "create_router",
    "quick_route",
    "create_adapter",
    "load_config",
    "get_logger"
]

# 导入模型注册表函数
# 导入其他模块
from .ai_analyzer import AIAnalyzer
from .model_selector import ModelSelector
from .models import (
    ENTERPRISE_MODELS,
    FREE_MODELS,
    PREMIUM_MODELS,
    STANDARD_MODELS,
    get_all_models,
    get_available_models,
    get_model_by_id,
    get_models_by_tier,
)
from .satisfaction_evaluator import SatisfactionEvaluator


def create_router(
    config_path: str | None = None,
    enable_auto_reload: bool = True,
    ai_provider: Callable[[str], Any] | None = None,
    log_level: str = "info"
) -> RoutingEngine:
    """
    创建并初始化路由引擎

    Args:
        config_path: 配置文件路径，如果为 None 则使用默认配置
        enable_auto_reload: 是否启用配置热重载
        ai_provider: AI提供者函数，用于指令分析
        log_level: 日志级别

    Returns:
        初始化好的路由引擎
    """
    logger = get_logger(log_level=log_level)
    logger.info(f"Creating router with config_path={config_path}")

    # 加载配置
    if config_path:
        try:
            from .config_loader import ConfigLoader
            loader = ConfigLoader(config_path, auto_reload=enable_auto_reload)
            config = loader.get_config()
        except Exception as e:
            logger.error(f"Failed to load config from {config_path}: {e}")
            config = get_default_config()
    else:
        config = get_default_config()

    # 创建路由引擎
    engine = RoutingEngine(config)

    # 设置AI提供者
    if ai_provider:
        engine.set_ai_provider(ai_provider)

    logger.info("Router created successfully")
    return engine


def load_config(
    config_path: str | None = None,
    auto_reload: bool = True
) -> ConfigLoader:
    """
    加载配置

    Args:
        config_path: 配置文件路径
        auto_reload: 是否启用热重载

    Returns:
        配置加载器实例
    """
    return ConfigLoader(config_path, auto_reload=auto_reload)


def create_adapter(
    config_path: str | None = None,
    ai_provider: Callable[[str], Any] | None = None,
    auto_initialize: bool = True
) -> OpenClawSmartRouterAdapter:
    """
    创建OpenClaw适配器

    Args:
        config_path: 配置文件路径
        ai_provider: AI提供者函数
        auto_initialize: 是否自动初始化

    Returns:
        OpenClaw适配器实例
    """
    from .config_loader import ConfigLoader

    config = OpenClawAdapterConfig(auto_initialize=auto_initialize)

    if config_path:
        try:
            loader = ConfigLoader(config_path)
            config.router_config = loader.get_config()
        except Exception as e:
            get_logger().error(f"Failed to load config: {e}")

    adapter = OpenClawSmartRouterAdapter(config)

    if auto_initialize:
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(adapter.initialize())
            else:
                loop.run_until_complete(adapter.initialize())
        except Exception as e:
            get_logger().error(f"Failed to auto-initialize adapter: {e}")

    return adapter


def quick_route(
    instruction: str,
    context: RoutingContext | None = None,
    config_path: str | None = None,
    ai_provider: Callable[[str], Any] | None = None
) -> RoutingDecision:
    """
    快速路由 - 简化API

    Args:
        instruction: 用户指令
        context: 路由上下文
        config_path: 配置文件路径
        ai_provider: AI提供者函数

    Returns:
        路由决策
    """
    import asyncio

    async def _route():
        router = create_router(config_path, ai_provider=ai_provider)
        return await router.route(instruction, context)

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            task = asyncio.create_task(_route())
            # 注意：在运行中的循环中，需要等待任务完成
            return asyncio.run_coroutine_threadsafe(_route(), loop).result(timeout=60)
        return loop.run_until_complete(_route())
    except Exception as e:
        get_logger().error(f"Quick route failed: {e}")
        raise


def get_router_version() -> str:
    """获取路由系统版本"""
    return "1.0.0"


class SmartRouter:
    """
    智能路由器主类
    提供完整的智能路由功能
    """

    def __init__(
        self,
        config_path: str | None = None,
        ai_provider: Callable[[str], Any] | None = None,
        auto_init: bool = True
    ):
        self.logger = get_logger()
        self._adapter: OpenClawSmartRouterAdapter | None = None
        self._engine: RoutingEngine | None = None
        self._config_path = config_path
        self._ai_provider = ai_provider

        if auto_init:
            self._initialize()

    def _initialize(self):
        """初始化路由器"""
        try:
            self._adapter = create_adapter(
                config_path=self._config_path,
                ai_provider=self._ai_provider,
                auto_initialize=True
            )
            self._engine = self._adapter.get_router()
            self.logger.info("SmartRouter initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize SmartRouter: {e}")
            raise

    def route(
        self,
        instruction: str,
        context: RoutingContext | None = None,
        **kwargs
    ) -> RoutingDecision:
        """
        路由指令

        Args:
            instruction: 用户指令
            context: 路由上下文
            **kwargs: 额外参数

        Returns:
            路由决策
        """
        if not self._adapter:
            raise RuntimeError("Router not initialized")

        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                result = asyncio.run_coroutine_threadsafe(
                    self._adapter.handle_instruction(instruction, context),
                    loop
                ).result(timeout=60)
            else:
                result = loop.run_until_complete(
                    self._adapter.handle_instruction(instruction, context)
                )
            return result
        except Exception as e:
            self.logger.error(f"Route failed: {e}")
            raise

    def report_execution(self, result: ExecutionResult):
        """报告执行结果"""
        if not self._adapter:
            raise RuntimeError("Router not initialized")

        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.run_coroutine_threadsafe(
                    self._adapter.report_execution(result),
                    loop
                )
            else:
                loop.run_until_complete(
                    self._adapter.report_execution(result)
                )
        except Exception as e:
            self.logger.error(f"Report execution failed: {e}")

    def submit_feedback(self, rating: int, comments: str | None = None):
        """提交反馈"""
        if not self._adapter:
            raise RuntimeError("Router not initialized")

        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.run_coroutine_threadsafe(
                    self._adapter.submit_user_feedback(rating, comments),
                    loop
                )
            else:
                loop.run_until_complete(
                    self._adapter.submit_user_feedback(rating, comments)
                )
        except Exception as e:
            self.logger.error(f"Submit feedback failed: {e}")

    def get_statistics(self) -> dict[str, Any]:
        """获取统计信息"""
        if not self._adapter:
            raise RuntimeError("Router not initialized")

        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                result = asyncio.run_coroutine_threadsafe(
                    self._adapter.get_statistics(),
                    loop
                ).result(timeout=30)
            else:
                result = loop.run_until_complete(
                    self._adapter.get_statistics()
                )
            return result
        except Exception as e:
            self.logger.error(f"Get statistics failed: {e}")
            return {}

    def get_health_status(self) -> dict[str, Any]:
        """获取健康状态"""
        if not self._adapter:
            raise RuntimeError("Router not initialized")

        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                result = asyncio.run_coroutine_threadsafe(
                    self._adapter.health_check(),
                    loop
                ).result(timeout=30)
            else:
                result = loop.run_until_complete(
                    self._adapter.health_check()
                )
            return result
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return {"healthy": False, "issues": [str(e)]}

    def switch_model(self, model_id: str) -> bool:
        """切换模型"""
        if not self._adapter:
            raise RuntimeError("Router not initialized")

        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                result = asyncio.run_coroutine_threadsafe(
                    self._adapter.switch_model(model_id),
                    loop
                ).result(timeout=30)
            else:
                result = loop.run_until_complete(
                    self._adapter.switch_model(model_id)
                )
            return result
        except Exception as e:
            self.logger.error(f"Switch model failed: {e}")
            return False

    def reset(self):
        """重置路由器"""
        if self._adapter:
            self._adapter.reset()
            self.logger.info("Router reset")

    def set_callbacks(self, callbacks: dict[str, Callable]):
        """设置回调函数"""
        if self._adapter:
            self._adapter.set_callbacks(callbacks)

    def get_current_model(self) -> ModelInfo | None:
        """获取当前模型"""
        if self._adapter:
            status = self._adapter.get_status()
            model_id = status.get("current_model")
            if model_id:
                try:
                    return get_model_by_id(model_id)
                except ValueError:
                    pass
        return None

    def set_ai_provider(self, provider: Callable[[str], Any]):
        """设置AI提供者"""
        if self._engine:
            self._engine.set_ai_provider(provider)

    def update_config(self, updates: dict[str, Any]):
        """更新配置"""
        if self._engine:
            self._engine.update_config(updates)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.reset()


def create_smart_router(
    config_path: str | None = None,
    ai_provider: Callable[[str], Any] | None = None
) -> SmartRouter:
    """
    创建智能路由器

    Args:
        config_path: 配置文件路径
        ai_provider: AI提供者函数

    Returns:
        SmartRouter实例
    """
    return SmartRouter(config_path=config_path, ai_provider=ai_provider, auto_init=True)
