"""
R14: 交付验收清单 — post_task_complete hook
================================================
方法论依据: 五.1 验收测试 (Acceptance Testing)
"ATDD（验收测试驱动开发）：在编码前编写验收标准，
使用 Gherkin（Given-When-Then）格式"

+ 五.3 交付清单 (Delivery Checklist):
代码冻结→回归测试→安全审计→性能压测→部署手册→监控告警→值班确认→发布
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

CHECKLIST_LOG = Path("~/.hermes/logs/acceptance_checklists.jsonl").expanduser()


# ── 标准验收清单模板 ──
STANDARD_CHECKLIST = [
    {
        "id": "AC-01",
        "category": "功能正确性",
        "item": "所有功能按预期工作",
        "gherkin": "Given 用户执行核心操作 When 操作完成 Then 输出符合预期",
        "verification": "手动/自动测试",
        "blocking": True,
    },
    {
        "id": "AC-02",
        "category": "安全性审计",
        "item": "无高危安全漏洞",
        "gherkin": "Given 系统运行中 When 执行安全扫描 Then 无HIGH/MEDIUM级别漏洞",
        "verification": "SAST扫描(ruff/bandit)",
        "blocking": True,
    },
    {
        "id": "AC-03",
        "category": "性能验证",
        "item": "关键API延迟在基线内",
        "gherkin": "Given 系统高负载时 When 调用关键API Then P99延迟 ≤ 基线110%",
        "verification": "性能测试",
        "blocking": False,
    },
    {
        "id": "AC-04",
        "category": "测试覆盖",
        "item": "单元测试覆盖率 ≥ 80%",
        "gherkin": "Given 代码提交后 When 运行测试套件 Then 覆盖率 ≥ 80% 且全部通过",
        "verification": "pytest --cov",
        "blocking": True,
    },
    {
        "id": "AC-05",
        "category": "文档完整性",
        "item": "README/CHANGELOG/API文档齐全",
        "gherkin": "Given 项目交付时 When 检查文档 Then 所有必需文档存在且内容准确",
        "verification": "手动审查",
        "blocking": False,
    },
    {
        "id": "AC-06",
        "category": "部署验证",
        "item": "部署后冒烟测试通过",
        "gherkin": "Given 新版本部署后 When 执行冒烟测试 Then 核心路径全部通过",
        "verification": "smoke_test",
        "blocking": True,
    },
    {
        "id": "AC-07",
        "category": "回滚方案",
        "item": "回滚方案就绪",
        "gherkin": "Given 发布出现严重问题 When 决定回滚 Then 可在5分钟内回滚到上一版本",
        "verification": "回滚演练",
        "blocking": True,
    },
    {
        "id": "AC-08",
        "category": "双AI互审",
        "item": "执行AI和监督AI各自输出独立评审通过",
        "gherkin": "Given 任务完成 When 双AI互审 Then 两份独立评审均无重大问题",
        "verification": "dual_review日志",
        "blocking": True,
    },
    {
        "id": "AC-09",
        "category": "反幻觉验证",
        "item": "所有输出有真实依据，零编造",
        "gherkin": "Given 任务完成 When 检查所有输出 Then 每条声明都有来源",
        "verification": "anti_hallucination扫描",
        "blocking": True,
    },
    {
        "id": "AC-10",
        "category": "复盘反思",
        "item": "完成结构化复盘",
        "gherkin": "Given 任务交付 When 执行复盘 Then 5维度评分+经验提取完成",
        "verification": "复盘报告",
        "blocking": False,
    },
]


def _generate_atdd_acceptance(task_description: str) -> list[dict]:
    """根据任务描述生成ATDD格式验收标准(Given-When-Then)"""
    # 基于标准清单+任务特定项
    checklist = list(STANDARD_CHECKLIST)

    # 添加上下文相关的验收项
    task_extra = {
        "id": "AC-11",
        "category": "任务特定",
        "item": f"满足任务核心需求: {task_description[:80]}",
        "gherkin": (
            f"Given {task_description[:50]}的上下文 "
            f"When 交付物完成 "
            f"Then 交付物满足原始需求"
        ),
        "verification": "需求对账",
        "blocking": True,
    }
    checklist.append(task_extra)

    return checklist


def generate_checklist(ctx, task_description: str, task_result: dict):
    """
    post_task_complete hook: 任务完成后自动生成验收清单并逐项打钩。
    """
    logger.info(f"[R14-验收] 生成验收清单: '{task_description[:60]}...'")

    checklist = _generate_atdd_acceptance(task_description)

    # 记录到上下文
    ctx._acceptance_checklist = checklist

    # 持久化到日志
    CHECKLIST_LOG.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "task": task_description[:200],
        "total_items": len(checklist),
        "blocking_items": sum(1 for c in checklist if c.get("blocking")),
        "items": checklist,
    }
    with open(CHECKLIST_LOG, "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    # 检查阻断项
    blocking_items = [c for c in checklist if c.get("blocking")]
    logger.info(
        f"[R14-验收] 清单: {len(checklist)}项 "
        f"(其中{len(blocking_items)}项为阻断项)"
    )

    # 存储结果
    ctx._acceptance_summary = {
        "total": len(checklist),
        "blocking": len(blocking_items),
        "checklist": checklist,
    }

    return None  # 不阻止任务完成（评估在外部进行）


def get_delivery_checklist() -> list[dict]:
    """
    获取交付清单（七步流程）:
    代码冻结→回归测试→安全审计→性能压测→部署手册→监控告警→值班确认→发布
    """
    return [
        {"step": 1, "name": "代码冻结", "action": "确认所有代码已提交且通过审查"},
        {"step": 2, "name": "回归测试", "action": "完整回归测试套件全部通过"},
        {"step": 3, "name": "安全审计", "action": "SAST+依赖漏洞扫描无高危问题"},
        {"step": 4, "name": "性能压测", "action": "关键API性能指标无退化"},
        {"step": 5, "name": "部署手册", "action": "部署步骤/配置/回滚方案文档就绪"},
        {"step": 6, "name": "监控告警", "action": "SLI/SLO告警规则配置完毕"},
        {"step": 7, "name": "值班确认", "action": "值班人员确认发布窗口"},
        {"step": 8, "name": "发布", "action": "按金丝雀/蓝绿策略执行发布"},
    ]
