# ~/.hermes/plugins/commercial_grade_enforcer/__init__.py
"""
commercial_grade_enforcer — 商用级强制执行器入口
注册6个hook,将《商用级软件开发与任务执行方法论》代码化注入Hermes运行时。
"""
import logging
from pathlib import Path

logger = logging.getLogger(__name__)
PLUGIN_DIR = Path(__file__).parent
PLUGIN_ACTIVATED_FILE = Path.home() / ".hermes" / "logs" / "model_router" / "plugin_activated.log"

def register(ctx):
    """Hermes插件系统入口"""
    logger.info("[commercial_grade_enforcer] 注册商用级强制规则...")
    
    try:
        # R9: WBS分解 — 任务开始前注入
        from .wbs_injector import inject_wbs
        if hasattr(ctx, 'register_hook'):
            ctx.register_hook("pre_task_start", inject_wbs)
        logger.info("  ✓ R9 WBS分解规则已注册")
    except Exception as e:
        logger.warning(f"  ⚠ R9注册失败: {e}")

    try:
        # R10: 幂等性保护 — 工具调用前
        from .idempotency_guard import inject_idempotency_key
        if hasattr(ctx, 'register_hook'):
            ctx.register_hook("pre_tool_call", inject_idempotency_key)
        logger.info("  ✓ R10 幂等性保护已注册")
    except Exception as e:
        logger.warning(f"  ⚠ R10注册失败: {e}")

    try:
        # R11: Checkpoint保护 — 工具调用后
        from .checkpoint_guard import safepoint_check
        if hasattr(ctx, 'register_hook'):
            ctx.register_hook("post_tool_call", safepoint_check)
        logger.info("  ✓ R11 Checkpoint保护已注册")
    except Exception as e:
        logger.warning(f"  ⚠ R11注册失败: {e}")

    try:
        # R12: 质量门禁 — 工具调用后
        from .quality_gate import check_gates
        if hasattr(ctx, 'register_hook'):
            ctx.register_hook("post_tool_call", check_gates)
        logger.info("  ✓ R12 质量门禁已注册")
    except Exception as e:
        logger.warning(f"  ⚠ R12注册失败: {e}")

    try:
        # R13: 三Agent评估器 — 工具调用前(验证模型多样性)
        from .verifier_agent import verify_model_diversity
        if hasattr(ctx, 'register_hook'):
            ctx.register_hook("pre_tool_call", verify_model_diversity)
        logger.info("  ✓ R13 三Agent评估器已注册")
    except Exception as e:
        logger.warning(f"  ⚠ R13注册失败: {e}")

    try:
        # R14: 交付验收清单 — 任务完成时
        from .acceptance_checklist import generate_checklist
        if hasattr(ctx, 'register_hook'):
            ctx.register_hook("post_task_complete", generate_checklist)
        logger.info("  ✓ R14 交付验收清单已注册")
    except Exception as e:
        logger.warning(f"  ⚠ R14注册失败: {e}")

    try:
        # R15: 五级降级策略 — 工具调用失败时
        from .degradation_handler import handle_failure
        if hasattr(ctx, 'register_hook'):
            ctx.register_hook("post_tool_call", handle_failure)
        logger.info("  ✓ R15 降级策略已注册")
    except Exception as e:
        logger.warning(f"  ⚠ R15注册失败: {e}")

    try:
        # Metrics: 指标收集器 — 后台线程
        from .metrics_collector import start_collector
        if hasattr(ctx, 'register_hook'):
            ctx.register_hook("post_task_complete", start_collector)
        logger.info("  ✓ 指标收集器已注册")
    except Exception as e:
        logger.warning(f"  ⚠ 指标收集器注册失败: {e}")

    # 写入激活标记
    try:
        PLUGIN_ACTIVATED_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(PLUGIN_ACTIVATED_FILE, "w") as f:
            from datetime import datetime
            f.write(datetime.now().isoformat())
    except:
        pass

    logger.info("[commercial_grade_enforcer] 全部8个模块注册完成")
