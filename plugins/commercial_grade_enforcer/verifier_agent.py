"""
R13: 评估器独立模型验证 — pre_tool_call hook
=================================================
方法论依据: 二.5 评估与反馈闭环
"每个Agent输出由评估器（Evaluator/Verifier Agent）校验，不合格则回退重做
指标：任务完成率、首次通过率、人工干预率、端到端耗时"

+ SOUL.md要求: "监督AI和执行AI必须使用不同模型接入"
"""

import logging
from enum import Enum

logger = logging.getLogger(__name__)


class ModelFamily(Enum):
    """模型家族分类"""
    DEEPSEEK = "deepseek"
    CLAUDE = "claude"
    OPENAI = "openai"
    GEMINI = "gemini"
    NVIDIA = "nvidia"
    OPENROUTER = "openrouter"
    UNKNOWN = "unknown"


# ── 模型名 → 家族映射 ──
MODEL_FAMILY_MAP = {
    "deepseek": ModelFamily.DEEPSEEK,
    "claude": ModelFamily.CLAUDE,
    "gpt": ModelFamily.OPENAI,
    "gemini": ModelFamily.GEMINI,
    "nvidia": ModelFamily.NVIDIA,
    "openrouter": ModelFamily.OPENROUTER,
}


def _get_model_family(model_name: str) -> ModelFamily:
    """根据模型名推断家族"""
    model_lower = model_name.lower()
    for prefix, family in MODEL_FAMILY_MAP.items():
        if prefix in model_lower:
            return family
    return ModelFamily.UNKNOWN


# ── HITL置信度阈值 ──
HITL_CONFIDENCE_THRESHOLD = 0.7
HITL_MAX_CONSECUTIVE_FAILURES = 3


def verify_model_diversity(ctx, tool_name: str, kwargs: dict):
    """
    pre_tool_call hook: 当使用 delegate_task 创建子Agent时，
    验证监督AI与执行AI使用不同模型家族。
    """
    # 只在delegate_task时检查
    if tool_name != "delegate_task":
        return None

    # 获取当前主模型
    main_model = getattr(ctx, "current_model", "unknown")
    main_family = _get_model_family(main_model)

    # 获取子Agent的模型配置
    sub_model = kwargs.get("model", "")
    if not sub_model:
        # 未指定子Agent模型 — 建议使用不同模型
        suggested_models = _suggest_alternative_model(main_family)
        logger.info(
            f"[R13-评估器] 子Agent未指定模型，建议使用: {suggested_models[0] if suggested_models else 'any'}"
        )
        # 注入建议（不强制）
        kwargs["_verifier_suggested_models"] = suggested_models
        return None

    sub_family = _get_model_family(sub_model)

    if main_family == sub_family and main_family != ModelFamily.UNKNOWN:
        logger.warning(
            f"[R13-评估器] 模型同质化风险: 主={main_model}({main_family.value}) "
            f"子={sub_model}({sub_family.value})"
        )
        # 警告但不阻止
        kwargs["_verifier_model_diversity_warning"] = (
            f"执行AI和监督AI使用同一模型家族({main_family.value})，"
            f"建议切换到不同provider以确保独立视角互审。"
        )
    else:
        logger.info(
            f"[R13-评估器] 模型独立性OK: 主={main_family.value} 子={sub_family.value}"
        )
        kwargs["_verifier_model_diversity_ok"] = True

    # HITL检查: 是否触发人工确认
    _check_hitl_trigger(ctx, kwargs)

    return None  # 不阻止


def _suggest_alternative_model(current_family: ModelFamily) -> list[str]:
    """根据当前模型家族建议替代模型"""
    alternatives = {
        ModelFamily.DEEPSEEK: ["claude-4.8", "gpt-5.5", "gemini-3.5-pro"],
        ModelFamily.CLAUDE: ["deepseek-v4-pro", "gpt-5.5", "gemini-3.5-pro"],
        ModelFamily.OPENAI: ["claude-4.8", "deepseek-v4-pro", "gemini-3.5-pro"],
        ModelFamily.GEMINI: ["claude-4.8", "deepseek-v4-pro", "gpt-5.5"],
        ModelFamily.NVIDIA: ["claude-4.8", "deepseek-v4-pro", "gpt-5.5"],
        ModelFamily.OPENROUTER: ["claude-4.8", "deepseek-v4-pro", "gpt-5.5"],
        ModelFamily.UNKNOWN: ["claude-4.8", "deepseek-v4-pro", "gpt-5.5"],
    }
    return alternatives.get(current_family, alternatives[ModelFamily.UNKNOWN])


def _check_hitl_trigger(ctx, kwargs: dict):
    """
    检查是否触发HITL(Human-in-the-Loop)人工确认。
    触发条件:
    - 置信度 < 0.7
    - 连续失败 ≥ 3次
    - 涉及安全关键操作
    """
    confidence = getattr(ctx, "_last_confidence", 1.0)
    consecutive_failures = getattr(ctx, "_consecutive_failures", 0)
    is_security_critical = kwargs.get("_security_critical", False)

    triggers = []

    if confidence < HITL_CONFIDENCE_THRESHOLD:
        triggers.append(f"低置信度({confidence:.2f} < {HITL_CONFIDENCE_THRESHOLD})")

    if consecutive_failures >= HITL_MAX_CONSECUTIVE_FAILURES:
        triggers.append(f"连续失败({consecutive_failures} ≥ {HITL_MAX_CONSECUTIVE_FAILURES})")

    if is_security_critical:
        triggers.append("安全关键操作")

    if triggers:
        logger.warning(f"[R13-HITL] 触发人工确认: {', '.join(triggers)}")
        kwargs["_hitl_required"] = True
        kwargs["_hitl_reasons"] = triggers
