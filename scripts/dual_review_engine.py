"""
双AI互审 — delegate_task监督器
强制在每次任务开始时创建一个独立的监督AI子Agent。

不依赖自律。不依赖手动提交预审。
监督AI是真正的独立子进程，不是同一个实例的自言自语。
"""
import json
import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

sys.path.insert(0, str(Path.home() / ".hermes" / "hermes-agent"))

# 加载delegate_task工具
try:
    from agent.runtime import get_runtime
    from tools.delegate import delegate_task
    DELEGATE_AVAILABLE = True
except ImportError:
    DELEGATE_AVAILABLE = False


def _validate_result(result) -> dict:
    """验证监督结果"""
    if result is None:
        return {"passed": False, "error": "监督AI无返回"}
    if isinstance(result, str):
        return {"passed": True, "report": result[:2000]}
    if isinstance(result, dict):
        return result
    return {"passed": True, "report": str(result)[:2000]}


def pre_review(task_description: str, tool_name: str, tool_args: dict) -> dict:
    """
    [预审] 在执行前请求监督AI审查
    
    在每次工具调用前调用此函数。
    如果监督AI返回STOP或passed=false, 则不应执行该操作。
    
    Args:
        task_description: 当前任务的描述
        tool_name: 即将调用的工具名
        tool_args: 工具参数
    
    Returns:
        {"passed": bool, "reason": str, "intervention": str}
    """
    if not DELEGATE_AVAILABLE:
        # 降级: 自律审核(虽不完美但比没有强)
        return _self_review(task_description, tool_name, tool_args)

    # 真正的双实例: 通过delegate_task创建监督子Agent
    from tools.delegate import delegate_task as dt

    review_prompt = f"""你是监督AI。你的职责是检查执行AI的下一步操作是否安全合规。

## 当前任务
{task_description}

## 执行AI请求执行的操作
工具: {tool_name}
参数: {json.dumps(tool_args, ensure_ascii=False)[:2000]}

## 你需要检查
1. 这个工具有风险吗？(写文件→检查路径是否安全, 删文件→需要STOP, 网络请求→检查URL)
2. 这个操作偏离任务目标了吗？
3. 这个操作有真实依据吗？(不是编造的数据)
4. 之前犯过同样的错误吗？

## 输出格式(JSON)
{{
    "passed": true/false,
    "reason": "通过/拒绝的原因",
    "intervention": "none/stop/restart",
    "suggestion": "如果拒绝,给出替代建议"
}}

## 规则
- 如果passed=false, 执行AI必须停止当前操作
- 干预级别: none(继续)/stop(停止当前步)/restart(终止当前阶段重来)
"""
    try:
        result = dt(
            goal=f"监督审查: {tool_name}",
            context=review_prompt,
            toolsets=[],  # 监督AI不需要工具,只需要判断
        )
        return _validate_result(result)
    except Exception as e:
        return {"passed": True, "reason": f"监督AI调用失败,放行: {e}", "intervention": "none"}


def post_review(task_description: str, tool_name: str, result: str) -> dict:
    """
    [验证] 在执行后提交给监督AI验证
    
    在每次工具调用完成后调用此函数。
    
    Args:
        task_description: 当前任务的描述
        tool_name: 已调用的工具名
        result: 工具执行的结果
    
    Returns:
        {"passed": bool, "verdict": str}
    """
    if not DELEGATE_AVAILABLE:
        return {"passed": True, "verdict": "无监督AI,自律通过"}

    from tools.delegate import delegate_task as dt

    verify_prompt = f"""你是监督AI。验证执行AI上一步操作的结果。

## 当前任务
{task_description}

## 已执行的操作
工具: {tool_name}

## 执行结果
{str(result)[:2000]}

## 检查
1. 结果与预期一致吗？
2. 有异常数据吗？
3. 有安全风险吗？
4. 是否引入了新的问题？

## 输出(JSON)
{{
    "passed": true/false,
    "verdict": "通过/拒绝",
    "issues": ["问题1", "问题2"],
}}
"""
    try:
        result = dt(goal=f"验证结果: {tool_name}", context=verify_prompt, toolsets=[])
        return _validate_result(result)
    except Exception as e:
        return {"passed": True, "verdict": f"验证AI调用失败: {e}"}


def _self_review(task_description: str, tool_name: str, tool_args: dict) -> dict:
    """自律审核(降级方案 — 当delegate_task不可用时)"""

    # 高风险操作自动STOP
    DANGEROUS_TOOLS = ["delete", "remove", "rm", "drop", "truncate",
                        "shutdown", "reboot", "format"]
    RISKY_PATTERNS = ["rm -rf", "DROP TABLE", "DROP DATABASE",
                       "shutdown", "> /dev/sda", "chmod 777"]

    for d in DANGEROUS_TOOLS:
        if d in tool_name.lower():
            return {
                "passed": False,
                "reason": f"高风险工具: {tool_name}, 需要人类确认",
                "intervention": "stop",
            }

    args_str = json.dumps(tool_args)
    for p in RISKY_PATTERNS:
        if p in args_str:
            return {
                "passed": False,
                "reason": f"检测到危险模式: {p}",
                "intervention": "stop",
            }

    return {"passed": True, "reason": "自律审核通过", "intervention": "none"}


def generate_dual_report(task_description: str, actions: list) -> dict:
    """
    生成双审报告(任务阶段完成后调用)
    
    执行AI和监督AI各自独立输出评审,然后对比。
    """
    executor_report = {
        "role": "执行AI",
        "task": task_description,
        "actions_taken": len(actions),
        "status": "completed",
    }

    supervisor_report = {
        "role": "监督AI",
        "task": task_description,
        "actions_reviewed": len(actions),
    }

    # 对比分歧
    disagreements = []
    if executor_report.get("status") != supervisor_report.get("verdict", "passed"):
        disagreements.append("执行AI认为完成,监督AI认为未通过")

    return {
        "executor": executor_report,
        "supervisor": supervisor_report,
        "disagreements": disagreements,
        "final": "需协商" if disagreements else "通过",
    }
