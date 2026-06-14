"""
dual_review_gate.py — 强制双审门禁
==================================
在每个任务开始时调用 gate.init()。
之后每次工具调用前必须经过 gate.check()。
不经过 gate.check() 的调用标记为违规。

用法:
  from scripts.dual_review_gate import ReviewGate
  gate = ReviewGate("当前任务描述")
  gate.init()  # 任务开始

  # 每次工具调用前:
  if not gate.check("工具名", "步骤描述", {"参数": "值"}):
      print("[双审] STOP: 预审未通过")
      return  # 不能执行
  # 执行工具...
  gate.verify("工具名", 结果)  # 调用后验证
"""

import json
import time
from typing import Any

# ========== 高风险检测 ==========

DANGEROUS_TOOLS = [
    "delete", "remove", "rm", "drop", "truncate",
    "shutdown", "reboot", "format", "purge",
    "mkfs", "dd", "fdisk",
]
DANGEROUS_PATTERNS = [
    "rm -rf /", "rm -rf /*", "rm -rf ~",
    "DROP TABLE", "DROP DATABASE",
    "> /dev/sda", "chmod 777 /",
    "dd if=", "mkfs.", "fdisk /dev/",
    "shutdown", "reboot",
]


class ReviewGate:
    """强制门禁 — 不可跳过"""

    def __init__(self, task_description: str = ""):
        self.task = task_description
        self.actions: list = []
        self.call_count = 0
        self.violations: list = []
        self._initialized = False

    def init(self) -> dict:
        """任务开始时调用"""
        self._initialized = True
        return {"ok": True, "task": self.task, "timestamp": time.time()}

    def _pre_check(self, tool: str, step: str, args: dict) -> dict:
        """预审逻辑 — 不依赖外部"""
        args_str = json.dumps(args)

        # 高风险工具
        for d in DANGEROUS_TOOLS:
            if d in tool.lower():
                return {"passed": False, "reason": f"高风险工具: {tool}", "action": "STOP"}

        # 危险模式
        for p in DANGEROUS_PATTERNS:
            if p in args_str:
                return {"passed": False, "reason": f"危险模式: {p}", "action": "STOP"}

        return {"passed": True, "reason": "通过", "action": "continue"}

    def _post_check(self, tool: str, result: Any) -> dict:
        """验证逻辑"""
        result_str = str(result)
        if "Traceback" in result_str:
            return {"passed": False, "verdict": "执行异常"}
        if "error" in result_str.lower() and "success" not in result_str.lower():
            return {"passed": False, "verdict": "返回包含错误"}
        return {"passed": True, "verdict": "OK"}

    def check(self, tool: str, step: str = "", args: dict = None) -> bool:
        """工具调用前 — 返回True=通过, False=拦截"""
        if not self._initialized:
            self.violations.append({"tool": tool, "issue": "未调用init()直接check"})

        self.call_count += 1
        result = self._pre_check(tool, step, args or {})
        self.actions.append({
            "step": step, "tool": tool,
            "pre": result, "time": time.time(),
        })

        if not result["passed"]:
            self.violations.append({"tool": tool, "reason": result["reason"]})

        return result["passed"]

    def verify(self, tool: str, result: Any) -> dict:
        """工具调用后验证"""
        for a in reversed(self.actions):
            if a["tool"] == tool and "post" not in a:
                a["post"] = self._post_check(tool, result)
                return a["post"]
        return {"passed": True, "verdict": "未匹配到预审记录"}

    def get_status(self) -> dict:
        """获取当前门禁状态"""
        recent_errors = [a for a in self.actions[-5:]
                        if a.get("post", {}).get("passed") is False]
        consecutive_fails = len([a for a in self.actions[-3:]
                                 if a.get("post", {}).get("passed") is False])

        return {
            "task": self.task,
            "calls": self.call_count,
            "violations": len(self.violations),
            "consecutive_fails": consecutive_fails,
            "suggest_switch": consecutive_fails >= 3,
        }

    def get_report(self) -> str:
        """获取完整报告"""
        status = self.get_status()
        lines = [
            "=" * 50,
            f"双审报告: {self.task}",
            "=" * 50,
            f"总调用: {status['calls']}",
            f"违规: {status['violations']}",
            f"连续失败: {status['consecutive_fails']}",
            f"建议切换模型: {'是' if status['suggest_switch'] else '否'}",
        ]
        if self.violations:
            lines.append("")
            lines.append("违规记录:")
            for v in self.violations:
                lines.append(f"  - [{v.get('tool','?')}] {v.get('reason','无原因')}")
        return "\n".join(lines)
