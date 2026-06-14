"""
Hermes 模型智能路由插件 — 注入到 Hermes 主Agent 的 pre_tool_call hook
========================================================================
当模型调用连续失败时，自动按路由链切换到下一个可用模型。

路由链（按优先级）:
  普通任务: deepseek-v4-flash
  标准任务: deepseek-v4-pro
  困难任务: deepseek-v4-pro
  超难任务: 建议 Claude 4.8/GPT 5.5/Gemini 3.5 Pro

工作原理:
  1. 统计连续失败的 tool 调用次数
  2. 连续 3 次失败 → 触发模型切换
  3. 在当前 provider 的 model 列表中轮转
  4. 记录切换历史到日志文件

不需要任何外部调用——只要 Hermes 主Agent 在运行，这个插件就在工作。
"""

import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

HERMES_HOME = Path(os.environ.get("HERMES_HOME", os.path.expanduser("~/.hermes")))

# 失败计数和切换状态
_failure_counts: dict[str, int] = {}  # session_id -> count
_switch_history: list[dict] = []
_last_model: dict[str, str] = {}  # session_id -> current_model

# 配置
MAX_FAILURES_BEFORE_SWITCH = 3
SWITCH_COOLDOWN = 60  # 秒，切换后至少等待这么长时间再切换

# 路由链
ROUTING_CHAIN = {
    "normal": ["deepseek-v4-flash"],
    "standard": ["deepseek-v4-pro"],
    "hard": ["deepseek-v4-pro"],
    "extreme": ["claude-4.8", "gpt-5.5", "gemini-3.5-pro"],
}

# 所有可用模型（按切换优先级）
FALLBACK_MODELS = [
    "deepseek-v4-pro",
    "deepseek-v4-flash",
    "deepseek-chat",
    # NVIDIA 备选
    "deepseek-ai/deepseek-v4-pro",
    "z-ai/glm-5.1",
    "moonshotai/kimi-k2.6",
    "nvidia/nemotron-3-ultra-550b-a55b",
    # OpenRouter 备选
    "moonshotai/kimi-k2.6:free",
    "sourceful/riverflow-v2.5-pro:free",
    "nvidia/nemotron-3-ultra-550b-a55b:free",
    "openrouter/owl-alpha",
    "nex-agi/nex-n2-pro:free",
    # Google
    "gemini-2.5-pro",
    "gemini-2.5-flash",
]


def register(ctx):
    """插件注册入口 — Hermes 主Agent启动时自动调用"""
    ctx.register_hook("post_tool_call", model_router_hook)

    # 写入激活日志
    log_dir = HERMES_HOME / "logs" / "model_router"
    log_dir.mkdir(parents=True, exist_ok=True)
    activation_log = log_dir / "plugin_activated.log"
    from datetime import datetime, timedelta, timezone
    with open(activation_log, "a") as f:
        f.write(f"[{datetime.now(timezone(timedelta(hours=8))).isoformat()}] 模型路由插件已激活\n")


def model_router_hook(tool_name: str, args: dict, result: Any,
                      task_id: str = "", session_id: str = "",
                      tool_call_id: str = "") -> dict | None:
    """
    post_tool_call hook — 每个 tool 调用完后触发
    
    检测连续失败，触发模型切换。
    返回 None = 无操作，返回 dict = 切换指令。
    """
    global _failure_counts, _switch_history, _last_model

    now = time.time()

    # 判断是否失败
    is_failure = _is_tool_failure(tool_name, args, result)

    if is_failure:
        # 累加失败次数
        key = session_id or "default"
        _failure_counts[key] = _failure_counts.get(key, 0) + 1

        count = _failure_counts[key]

        # 检查是否需要切换模型
        if count >= MAX_FAILURES_BEFORE_SWITCH:
            # 检查冷却期
            last_switch = _get_last_switch_time(session_id)
            if last_switch and (now - last_switch) < SWITCH_COOLDOWN:
                return None  # 还在冷却期，不切换

            # 执行切换
            switch_result = _switch_model(session_id)
            if switch_result:
                _failure_counts[key] = 0  # 重置计数
                return switch_result
    else:
        # 成功后逐渐减少失败计数
        key = session_id or "default"
        if key in _failure_counts and _failure_counts[key] > 0:
            _failure_counts[key] = max(0, _failure_counts[key] - 1)

    return None


def _is_tool_failure(tool_name: str, args: dict, result: Any) -> bool:
    """判断 tool 调用是否为失败"""
    if result is None:
        return True

    if isinstance(result, dict):
        # 检查标准错误模式
        if result.get("error"):
            return True
        if result.get("status") == "error":
            return True
        if result.get("exit_code") and result.get("exit_code") != 0:
            return True

    # 字符串结果中的错误模式
    if isinstance(result, str):
        error_patterns = [
            "error", "fail", "timeout", "500", "502", "503",
            "Internal Server Error", "Connection refused",
            "Authentication Fails", "invalid api key",
            "rate limit", "too many requests",
        ]
        result_lower = result.lower()
        for pattern in error_patterns:
            if pattern in result_lower:
                return True

    return False


def _get_last_switch_time(session_id: str) -> float | None:
    """获取上次切换模型的时间"""
    for entry in _switch_history:
        if entry.get("session_id") == session_id:
            return entry.get("timestamp")
    return None


def _get_current_model(session_id: str) -> str:
    """获取当前使用的模型"""
    return _last_model.get(session_id, "deepseek-v4-pro")


def _switch_model(session_id: str) -> dict | None:
    """执行模型切换，返回切换指令"""
    global _switch_history, _last_model

    current = _get_current_model(session_id)

    # 找当前模型在 fallback 链中的位置
    try:
        current_idx = FALLBACK_MODELS.index(current)
    except ValueError:
        current_idx = -1

    # 选下一个模型
    next_idx = current_idx + 1
    if next_idx >= len(FALLBACK_MODELS):
        # 已经到链尾了，从头开始
        next_idx = 0

    next_model = FALLBACK_MODELS[next_idx]

    # 如果下一个和当前一样，说明只有一个模型，无法切换
    if next_model == current:
        return None

    # 记录切换
    _last_model[session_id] = next_model
    entry = {
        "timestamp": time.time(),
        "session_id": session_id,
        "from": current,
        "to": next_model,
        "reason": f"连续{MAX_FAILURES_BEFORE_SWITCH}次失败后自动切换",
    }
    _switch_history.append(entry)

    # 写入日志
    log_dir = HERMES_HOME / "logs" / "model_router"
    log_dir.mkdir(parents=True, exist_ok=True)
    switch_log = log_dir / "switches.log"
    with open(switch_log, "a") as f:
        f.write(json.dumps(entry) + "\n")

    # 返回切换指令（Hermes 主Agent 会处理这个指令）
    return {
        "action": "switch_model",
        "model": next_model,
        "reason": entry["reason"],
        "fallback_chain": FALLBACK_MODELS[next_idx:next_idx + 3],
    }


def get_status() -> dict:
    """获取路由插件状态"""
    return {
        "active": True,
        "failure_counts": _failure_counts,
        "switch_history": _switch_history[-10:],  # 最近10次
        "current_models": _last_model,
        "fallback_chain": FALLBACK_MODELS,
        "config": {
            "max_failures": MAX_FAILURES_BEFORE_SWITCH,
            "cooldown_seconds": SWITCH_COOLDOWN,
        },
    }
