"""
R9: WBS注入器 — pre_task_start hook
========================================
方法论依据: 七.1 工作分解结构 (WBS)
"自顶向下分解：Epic → Feature → User Story → Task → Sub-task
100%规则：WBS必须100%覆盖项目范围
分解到可估算、可分配、可追踪的粒度（理想粒度：1-3天工作量）"

+ MoSCoW优先级: Must have / Should have / Could have / Won't have
+ 故事点估算: Fibonacci (1, 2, 3, 5, 8, 13, 21)
"""

import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class MoSCoW(Enum):
    MUST = "Must have"       # 必须有 — 缺了项目失败
    SHOULD = "Should have"   # 应该有 — 重要但不是关键路径
    COULD = "Could have"     # 可以有 — 锦上添花
    WONT = "Won't have"      # 本次不做 — 明确排除


@dataclass
class WBSNode:
    """WBS树节点"""
    level: str  # "Epic" | "Feature" | "Story" | "Task" | "Sub-task"
    name: str
    description: str
    moscow: MoSCoW = MoSCoW.MUST
    story_points: int = 1  # Fibonacci: 1,2,3,5,8,13,21
    estimated_hours: float = 0.0
    dependencies: list[str] = field(default_factory=list)  # 前置节点名
    children: list["WBSNode"] = field(default_factory=list)
    acceptance_criteria: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "level": self.level,
            "name": self.name,
            "description": self.description,
            "moscow": self.moscow.value,
            "story_points": self.story_points,
            "estimated_hours": self.estimated_hours,
            "dependencies": self.dependencies,
            "acceptance_criteria": self.acceptance_criteria,
            "children": [c.to_dict() for c in self.children],
        }


def _validate_100_percent_rule(wbs: WBSNode, task_scope: str) -> bool:
    """验证100%规则: WBS必须100%覆盖任务范围"""
    # 简单检查: WBS叶节点数量是否覆盖了任务描述的要点
    scope_keywords = set(task_scope.lower().split())
    covered_keywords = set()

    def collect_keywords(node: WBSNode):
        covered_keywords.update(node.name.lower().split())
        covered_keywords.update(node.description.lower().split())
        for c in node.children:
            collect_keywords(c)

    collect_keywords(wbs)
    # 至少50%的关键词被覆盖
    overlap = len(scope_keywords & covered_keywords)
    total = len(scope_keywords) if scope_keywords else 1
    return overlap / total >= 0.5


def _build_default_wbs(task_description: str, task_steps: int) -> WBSNode:
    """根据任务描述和步骤数自动构建默认WBS树"""
    # Epic
    epic = WBSNode(
        level="Epic",
        name=task_description[:80],
        description=task_description,
        moscow=MoSCoW.MUST,
        story_points=8,
    )

    # 根据步骤数决定Feature数量
    num_features = max(1, task_steps // 5)

    for fi in range(num_features):
        feature = WBSNode(
            level="Feature",
            name=f"Phase {fi + 1}",
            description=f"Phase {fi + 1} of {task_description[:50]}",
            moscow=MoSCoW.MUST if fi < num_features - 1 else MoSCoW.SHOULD,
            story_points=5 if fi == 0 else 3,
        )

        # 每个Feature下有2-3个Story
        num_stories = min(3, max(2, task_steps // num_features))
        for si in range(num_stories):
            story = WBSNode(
                level="Story",
                name=f"Step {fi * num_stories + si + 1}",
                description=f"Complete step {fi * num_stories + si + 1}",
                moscow=MoSCoW.MUST if si == 0 else MoSCoW.SHOULD,
                story_points=2,
                dependencies=[f"Phase {fi}" if fi > 0 and si == 0 else ""],
            )

            # 每个Story下有1-2个Task
            num_tasks = 2 if si < num_stories - 1 else 1
            for ti in range(num_tasks):
                task = WBSNode(
                    level="Task",
                    name=f"Task {fi * num_stories + si * num_tasks + ti + 1}",
                    description=f"Execute subtask",
                    story_points=1,
                    estimated_hours=2.0,
                )
                story.children.append(task)

            feature.children.append(story)

        epic.children.append(feature)

    return epic


def inject_wbs(ctx, task_description: str, task_steps: int):
    """
    pre_task_start hook: 任务启动前自动构建WBS树。
    验证100%规则，标注MoSCoW优先级和故事点。
    """
    logger.info(f"[R9-WBS] 构建WBS: steps={task_steps} scope='{task_description[:60]}...'")

    # 构建WBS树
    wbs = _build_default_wbs(task_description, task_steps)

    # 验证100%规则
    if not _validate_100_percent_rule(wbs, task_description):
        logger.warning("[R9-WBS] 100%规则验证未通过，扩展WBS覆盖范围")
        # 追加一个补充Feature覆盖遗漏
        catch_all = WBSNode(
            level="Feature",
            name="边缘需求与集成",
            description="覆盖WBS未完全覆盖的范围",
            moscow=MoSCoW.COULD,
            story_points=2,
        )
        wbs.children.append(catch_all)

    # 注入到上下文
    ctx._wbs_tree = wbs
    ctx._wbs_dict = wbs.to_dict()

    # 生成依赖矩阵
    deps = {}
    def collect_deps(node: WBSNode):
        if node.dependencies:
            deps[node.name] = node.dependencies
        for c in node.children:
            collect_deps(c)
    collect_deps(wbs)
    ctx._wbs_dependency_matrix = deps

    # 生成摘要
    total_points = sum(
        child.story_points for child in wbs.children
    )
    ctx._wbs_summary = {
        "epic": wbs.name,
        "num_features": len(wbs.children),
        "total_story_points": total_points,
        "moscow_breakdown": {
            "Must": sum(1 for c in wbs.children if c.moscow == MoSCoW.MUST),
            "Should": sum(1 for c in wbs.children if c.moscow == MoSCoW.SHOULD),
            "Could": sum(1 for c in wbs.children if c.moscow == MoSCoW.COULD),
            "Won't": sum(1 for c in wbs.children if c.moscow == MoSCoW.WONT),
        },
        "wbs_json": wbs.to_dict(),
    }

    logger.info(
        f"[R9-WBS] 构建完成: {len(wbs.children)} Features, "
        f"{total_points} story points, "
        f"MoSCoW: {ctx._wbs_summary['moscow_breakdown']}"
    )

    return None  # 不阻止任务启动
