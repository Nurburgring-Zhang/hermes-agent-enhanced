"""
Goal Hive Engine v1.0 — Hermes 蜂群协作模式引擎
=============================================
基于 Generic Agent 团队 Goal Hive 模式实现：
  Master拆目标 → 多Worker并行执行 → BBS任务账本 → Master逐份验收 → 预算驱动

集成点:
  - delegate_task → Worker执行
  - production_loop → 降级检测
  - Agent Company → 员工角色作为Worker
"""

import json
import os
import sys
from datetime import datetime

# Paths
HERMES_HOME = os.environ.get("HERMES_HOME", os.path.expanduser("~/.hermes"))
BBS_PATH = os.path.join(HERMES_HOME, "reports", "hive_bbs.json")
BBS_ARCHIVE_DIR = os.path.join(HERMES_HOME, "reports", "hive_archive")
CONFIG_PATH = os.path.join(HERMES_HOME, "config", "goal_hive_config.json")

# Default config
DEFAULT_CONFIG = {
    "max_workers": 12,
    "max_rounds": 5,
    "budget_tokens": 50000,
    "min_improvement": 0.02,
    "convergence_window": 3,
    "bbs_max_size_kb": 100,
}


class GoalHive:
    def __init__(self, goal: str, context: str = "", config: dict | None = None):
        self.goal = goal
        self.context = context
        self.config = {**DEFAULT_CONFIG, **(config or {})}
        self.hive_id = f"hive_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.bbs = self._init_bbs()
        self.budget = {
            "max_rounds": self.config["max_rounds"],
            "remaining": self.config["max_rounds"],
        }
        self.deficits = []
        self.round_count = 0

    def run(self, tasks: list[dict] | None = None) -> dict:
        print(f"[GoalHive] 启动 Hive: {self.hive_id}")
        print(f"[GoalHive] 目标: {self.goal[:100]}...")
        if tasks:
            hive_tasks = tasks
        else:
            print("[GoalHive] Phase 1: 自动拆解目标...")
            hive_tasks = self.decompose()
        print(f"[GoalHive] Phase 2: 派 {len(hive_tasks)} 个任务到BBS...")
        self.post_to_bbs(hive_tasks)
        while self.budget["remaining"] > 0:
            self.round_count += 1
            print(f"\n[GoalHive] Round {self.round_count}/{self.budget['max_rounds']} (剩余预算: {self.budget['remaining']})")
            pending = self._get_pending_tasks()
            if not pending:
                if self._check_and_fill_deficits():
                    continue
                print("[GoalHive] 所有任务完成，无缺口 → 提前交付")
                break
            for task in pending:
                self._execute_task(task)
            completed = [t for t in self.bbs["tasks"] if t["status"] == "completed"]
            for task in completed:
                self._review_task(task)
            self.budget["remaining"] -= 1
            if self._check_convergence():
                print("[GoalHive] 收敛检测触发 → 提前停止")
                break
        print("\n[GoalHive] Phase 4: 整合交付")
        return self._integrate()

    def decompose(self) -> list[dict]:
        tasks = []
        if any(w in self.goal.lower() for w in ["分析", "调研", "研究", "收集", "采集", "搜索"]):
            tasks.append({
                "task_id": "T001", "title": "信息收集与调研",
                "description": "围绕核心主题收集相关信息",
                "acceptance_criteria": "收集不少于5条相关信息或数据点",
                "status": "pending", "worker_type": "research",
                "dependencies": [], "deliverable": "research_findings.md"
            })
        if any(w in self.goal.lower() for w in ["分析", "对比", "评估", "判断"]):
            tasks.append({
                "task_id": "T002", "title": "深度分析",
                "description": "对收集的信息进行多维度分析",
                "acceptance_criteria": "输出包含至少3个维度的分析结论",
                "status": "pending", "worker_type": "analysis",
                "dependencies": ["T001"] if tasks else [],
                "deliverable": "analysis_report.md"
            })
        if any(w in self.goal.lower() for w in ["设计", "方案", "架构", "规划"]):
            tasks.append({
                "task_id": "T003", "title": "方案设计与规划",
                "description": "基于分析结果设计实施方案",
                "acceptance_criteria": "包含具体可行的实施方案",
                "status": "pending", "worker_type": "design",
                "dependencies": [t["task_id"] for t in tasks if "分析" in t["title"]],
                "deliverable": "design_proposal.md"
            })
        if any(w in self.goal.lower() for w in ["实现", "开发", "构建", "部署", "配置"]):
            tasks.append({
                "task_id": "T004", "title": "实现与部署",
                "description": "按方案实施具体工作",
                "acceptance_criteria": "实现可运行/可验证的成果",
                "status": "pending", "worker_type": "implementation",
                "dependencies": [t["task_id"] for t in tasks if "设计" in t["title"]],
                "deliverable": "implementation_output"
            })
        if not tasks:
            tasks = [
                {"task_id": "T001", "title": "问题理解与范围定义",
                 "description": "明确任务边界和核心要求",
                 "acceptance_criteria": "输出清晰的任务边界文档",
                 "status": "pending", "worker_type": "analysis",
                 "dependencies": [], "deliverable": "scope_definition.md"},
                {"task_id": "T002", "title": "方案研究与设计",
                 "description": "研究最佳方案并设计方案",
                 "acceptance_criteria": "输出至少2个可选方案",
                 "status": "pending", "worker_type": "research",
                 "dependencies": ["T001"], "deliverable": "solution_design.md"},
                {"task_id": "T003", "title": "执行与验证",
                 "description": "按选定方案执行并验证结果",
                 "acceptance_criteria": "成果可验证/可交付",
                 "status": "pending", "worker_type": "implementation",
                 "dependencies": ["T002"], "deliverable": "final_deliverable.md"}
            ]
        return tasks

    def post_to_bbs(self, tasks: list[dict]):
        for task in tasks:
            self.bbs["tasks"].append({
                "task_id": task["task_id"], "title": task["title"],
                "description": task.get("description", ""), "status": "pending",
                "acceptance_criteria": task.get("acceptance_criteria", ""),
                "worker_type": task.get("worker_type", "general"),
                "dependencies": task.get("dependencies", []),
                "deliverable": task.get("deliverable", ""), "worker": None,
                "post": {"submitted_at": None, "deliverable": None, "summary": None, "tokens_used": 0},
                "review": {"reviewed_at": None, "passed": None, "l1_completeness": None,
                          "l2_correctness": None, "l3_usability": None, "comments": [], "rework_count": 0}
            })
        self._save_bbs()

    def _get_pending_tasks(self) -> list[dict]:
        result = []
        for task in self.bbs["tasks"]:
            if task["status"] in ("pending", "needs_rework"):
                deps_met = all(
                    next((t for t in self.bbs["tasks"] if t["task_id"] == d), None) is None or
                    next((t for t in self.bbs["tasks"] if t["task_id"] == d), {}).get("status") in ("completed",)
                    for d in task.get("dependencies", [])
                )
                if deps_met:
                    result.append(task)
        return result

    def _execute_task(self, task: dict):
        print(f"[GoalHive]   执行: {task['task_id']} - {task['title']}")
        task["status"] = "in_progress"
        task["worker"] = f"Hermes_Worker_{task.get('worker_type', 'general')}"
        self._save_bbs()

    def mark_completed(self, task_id: str, summary: str, deliverable_path: str = ""):
        for task in self.bbs["tasks"]:
            if task["task_id"] == task_id:
                task["status"] = "completed"
                task["post"]["submitted_at"] = datetime.now().isoformat()
                task["post"]["summary"] = summary[:500]
                task["post"]["deliverable"] = deliverable_path
                self._save_bbs()
                return True
        return False

    def mark_failed(self, task_id: str, error: str):
        for task in self.bbs["tasks"]:
            if task["task_id"] == task_id:
                task["status"] = "failed"
                self.bbs.setdefault("errors", []).append({
                    "task_id": task_id, "error": error[:500],
                    "at": datetime.now().isoformat()
                })
                self._save_bbs()
                return True
        return False

    def _review_task(self, task: dict):
        task["review"]["reviewed_at"] = datetime.now().isoformat()
        has_summary = bool(task["post"].get("summary"))
        has_deliverable = bool(task["post"].get("deliverable"))
        degraded_keywords = ["占位符", "TODO", "待实现", "待补充", "placeholder",
                           "简化版", "示例", "样例", "演示", "demo"]
        summary = (task["post"].get("summary") or "").lower()
        has_degradation = any(kw in summary for kw in degraded_keywords)
        usable = has_summary and has_deliverable and not has_degradation
        task["review"]["l1_completeness"] = has_summary and has_deliverable
        task["review"]["l2_correctness"] = not has_degradation
        task["review"]["l3_usability"] = usable
        task["review"]["passed"] = usable
        if not usable:
            task["status"] = "needs_rework"
            task["review"]["rework_count"] += 1
            comments = []
            if not has_summary: comments.append("缺少提交摘要")
            if not has_deliverable: comments.append("缺少交付物路径")
            if has_degradation: comments.append("检测到降级关键词")
            task["review"]["comments"] = comments
            print(f"[GoalHive]   验收 X {task['task_id']}: {'; '.join(comments)}")
        else:
            print(f"[GoalHive]   验收 V {task['task_id']}: 通过")
        self._save_bbs()

    def _check_and_fill_deficits(self) -> bool:
        failed_tasks = [t for t in self.bbs["tasks"]
                       if t["status"] == "needs_rework" and t["review"]["rework_count"] < 3]
        if failed_tasks:
            print(f"[GoalHive]   缺口发现: {len(failed_tasks)} 个任务需返工")
            return True
        completed_tasks = [t for t in self.bbs["tasks"] if t["status"] == "completed"]
        coverage = self._check_coverage(completed_tasks)
        if coverage["missing"]:
            for gap in coverage["missing"]:
                new_id = f"T{len(self.bbs['tasks']) + 1:03d}"
                self.deficits.append({
                    "deficit_id": f"D{len(self.deficits) + 1:03d}",
                    "description": gap, "new_task_id": new_id
                })
                self.bbs["tasks"].append({
                    "task_id": new_id, "title": gap[:60],
                    "description": gap, "status": "pending",
                    "acceptance_criteria": "填补缺口",
                    "worker_type": "general", "dependencies": [],
                    "deliverable": "deficit_fill.md"
                })
            print(f"[GoalHive]   缺口发现: {len(coverage['missing'])} 个新任务已创建")
            return True
        return False

    def _check_coverage(self, completed_tasks: list[dict]) -> dict:
        goal_lower = self.goal.lower()
        keyword_map = {
            "分析": ["分析", "调研", "研究"],
            "实现": ["实现", "开发", "构建", "部署"],
            "方案": ["方案", "设计", "规划", "架构"],
            "验证": ["验证", "测试", "检查", "验收"],
            "文档": ["文档", "报告", "输出"],
        }
        covered = set()
        for task in completed_tasks:
            tl = task["title"].lower()
            for cat, kws in keyword_map.items():
                if any(kw in tl for kw in kws):
                    covered.add(cat)
        missing = []
        for cat, kws in keyword_map.items():
            if any(kw in goal_lower for kw in kws) and cat not in covered:
                missing.append(f"缺少{cat}类任务")
        return {"covered": list(covered), "missing": missing}

    def _check_convergence(self) -> bool:
        if self.round_count < self.config["convergence_window"]:
            return False
        all_passed = all(t["status"] == "completed" for t in self.bbs["tasks"])
        return all_passed

    def _integrate(self) -> dict:
        tasks_status = {}
        for task in self.bbs["tasks"]:
            tasks_status[task["task_id"]] = {
                "title": task["title"], "status": task["status"],
                "summary": task["post"].get("summary", "未交付"),
                "passed_review": task["review"].get("passed", False),
                "rework_count": task["review"].get("rework_count", 0)
            }
        result = {
            "hive_id": self.hive_id, "goal": self.goal,
            "status": "completed" if self.budget["remaining"] > 0 else "budget_exhausted",
            "rounds_used": self.round_count,
            "budget_remaining": self.budget["remaining"],
            "total_tasks": len(self.bbs["tasks"]),
            "completed_tasks": sum(1 for t in self.bbs["tasks"] if t["status"] == "completed"),
            "rework_tasks": sum(1 for t in self.bbs["tasks"] if t["status"] == "needs_rework"),
            "failed_tasks": sum(1 for t in self.bbs["tasks"] if t["status"] == "failed"),
            "deficits_found": len(self.deficits),
            "deficits_filled": sum(1 for d in self.deficits
                                   if any(t["task_id"] == d["new_task_id"]
                                          and t["status"] == "completed"
                                          for t in self.bbs["tasks"])),
            "tasks": tasks_status,
            "bbs_path": BBS_PATH,
            "completed_at": datetime.now().isoformat()
        }
        report_path = os.path.join(HERMES_HOME, "reports", f"hive_result_{self.hive_id}.json")
        os.makedirs(os.path.dirname(report_path), exist_ok=True)
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        return result

    def get_status(self) -> dict:
        status_counts = {"pending": 0, "in_progress": 0, "completed": 0, "needs_rework": 0, "failed": 0}
        for t in self.bbs.get("tasks", []):
            s = t.get("status", "")
            if s in status_counts:
                status_counts[s] += 1
        return {
            "hive_id": self.hive_id, "goal": self.goal[:100],
            "round": self.round_count,
            "budget_remaining": self.budget["remaining"],
            "total_tasks": len(self.bbs.get("tasks", [])),
            **status_counts,
            "deficits": len(self.deficits),
            "errors": len(self.bbs.get("errors", []))
        }

    def _init_bbs(self) -> dict:
        os.makedirs(os.path.dirname(BBS_PATH), exist_ok=True)
        os.makedirs(BBS_ARCHIVE_DIR, exist_ok=True)
        os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
        return {
            "hive_id": self.hive_id, "goal": self.goal,
            "context": self.context[:2000],
            "master": "Hermes", "created_at": datetime.now().isoformat(),
            "budget": {"max_rounds": self.budget["max_rounds"], "remaining": self.budget["remaining"]},
            "tasks": [], "deficits": [], "errors": []
        }

    def _save_bbs(self):
        os.makedirs(os.path.dirname(BBS_PATH), exist_ok=True)
        with open(BBS_PATH, "w", encoding="utf-8") as f:
            json.dump(self.bbs, f, ensure_ascii=False, indent=2)

    def load_bbs(self, path: str = None) -> bool:
        load_path = path or BBS_PATH
        if os.path.exists(load_path):
            with open(load_path, encoding="utf-8") as f:
                self.bbs = json.load(f)
            self.hive_id = self.bbs.get("hive_id", self.hive_id)
            self.goal = self.bbs.get("goal", self.goal)
            self.budget["remaining"] = self.bbs.get("budget", {}).get("remaining", 0)
            return True
        return False


def cli():
    if len(sys.argv) < 2:
        print("用法: python3 goal_hive_engine.py <command> [args]")
        print("命令:")
        print("  run <goal>            - 启动一个Goal Hive蜂群任务")
        print("  run-tasks <json>      - 从JSON文件加载自定义任务")
        print("  status                - 查看当前Hive状态")
        print("  tasks                 - 列出所有任务")
        print("  complete <id> <summ> [deliv] - 标记任务完成")
        print("  fail <id> <error>     - 标记任务失败")
        print("  mark <id> <status>    - 设置任务状态")
        print("  bbs                   - 查看完整BBS")
        return

    cmd = sys.argv[1]

    if cmd == "run" and len(sys.argv) >= 3:
        hive = GoalHive(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "")
        result = hive.run()
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif cmd == "run-tasks" and len(sys.argv) >= 3:
        with open(sys.argv[2], encoding="utf-8") as f:
            task_data = json.load(f)
        hive = GoalHive(task_data.get("goal", "蜂群任务"), task_data.get("context", ""))
        hive.run(task_data.get("tasks", []))
        print(json.dumps(hive.get_status(), ensure_ascii=False, indent=2))

    elif cmd == "status":
        hive = GoalHive("")
        hive.load_bbs()
        print(json.dumps(hive.get_status(), ensure_ascii=False, indent=2))

    elif cmd == "tasks":
        hive = GoalHive("")
        hive.load_bbs()
        marks = {"pending": "PENDING", "in_progress": "INPROG", "completed": "DONE",
                "needs_rework": "REWORK", "failed": "FAIL"}
        for t in hive.bbs.get("tasks", []):
            m = marks.get(t["status"], "?")
            print(f"  {m} {t['task_id']}: {t['title']}")

    elif cmd == "complete" and len(sys.argv) >= 4:
        hive = GoalHive("")
        if hive.load_bbs():
            if hive.mark_completed(sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else ""):
                print(f"[GoalHive] V {sys.argv[2]} 标记完成")
            else:
                print(f"[GoalHive] X 未找到任务 {sys.argv[2]}")

    elif cmd == "fail" and len(sys.argv) >= 4:
        hive = GoalHive("")
        if hive.load_bbs():
            hive.mark_failed(sys.argv[2], sys.argv[3])
            print(f"[GoalHive] X {sys.argv[2]} 标记失败")

    elif cmd == "mark" and len(sys.argv) >= 4:
        hive = GoalHive("")
        if hive.load_bbs():
            for t in hive.bbs.get("tasks", []):
                if t["task_id"] == sys.argv[2]:
                    t["status"] = sys.argv[3]
                    hive._save_bbs()
                    print(f"[GoalHive] V {sys.argv[2]} -> {sys.argv[3]}")
                    break

    elif cmd == "bbs":
        hive = GoalHive("")
        hive.load_bbs()
        print(json.dumps(hive.bbs, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    cli()
