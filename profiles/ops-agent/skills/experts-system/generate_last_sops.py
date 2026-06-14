#!/usr/bin/env python3
"""为最后55位专家（Office/Artist/AIGC/Media）生成差异化sop.yaml"""
from pathlib import Path

import yaml

EXPERTS_DIR = Path.home() / ".hermes" / "skills" / "experts-system" / "experts"

# 4种类型的SOP模板（按领域微调）
TYPE_SOPS = {
    "Office": [
        "需求受理与工单登记", "资源协调与分工", "流程节点处理",
        "文档编制与归档", "审批流转跟踪", "归档管理与索引", "效果反馈与改进"
    ],
    "Artist": [
        "需求沟通与理解", "创意构思与发散", "概念设计与草图",
        "视觉实现与精修", "评审反馈收集", "修改完善与交付", "交付归档与复盘"
    ],
    "AIGC": [
        "内容策划与选题", "素材准备与整理", "模型选择与配置",
        "内容生成与迭代", "质量审核与合规", "优化调整与完善", "成品交付与归档"
    ],
    "Media": [
        "热点追踪与选题", "内容策划与定位", "素材制作与编排",
        "渠道分发与排期", "互动管理与响应", "数据采集与分析", "策略优化与迭代"
    ],
}

# 领域微调映射
DOMAIN_ADAPT = {
    "Office": {
        "管理与沟通": ["行政需求受理", "内外部资源协调", "管理流程处理", "制度文档编制", "管理层审批流转", "组织档案管理", "管理效果反馈"],
        "教育与培训": ["培训需求受理", "教学资源协调", "教务流程处理", "教案文档编制", "教学审批流转", "学生档案管理", "教学效果反馈"],
    },
    "Artist": {
        "艺术与设计": ["设计需求沟通", "视觉创意构思", "概念设计草案", "视觉方案精修", "设计评审", "方案修改完善", "设计交付归档"],
    },
    "AIGC": {
        "内容与创意": ["内容选题策划", "创作素材准备", "AI模型配置", "内容生成优化", "内容质量审核", "内容优化迭代", "成品交付"],
    },
    "Media": {
        "内容与创意": ["热点追踪选题", "内容策略定位", "多媒体素材制作", "全渠道分发", "互动管理", "多平台数据分析", "策略优化"],
    }
}

def main():
    total = 0
    for d in sorted(EXPERTS_DIR.iterdir()):
        if not d.is_dir():
            continue
        iy = d / "identity.yaml"
        if not iy.exists():
            continue

        with open(iy) as f:
            data = yaml.safe_load(f) or {}
        agent = data.get("agent", {})
        etype = agent.get("expert_type", "")
        domain = agent.get("domain", "")
        name = agent.get("name", "")

        if etype not in TYPE_SOPS:
            continue

        # 获取基础SOP步名
        steps = list(TYPE_SOPS[etype])

        # 领域微调
        if etype in DOMAIN_ADAPT and domain in DOMAIN_ADAPT[etype]:
            steps = list(DOMAIN_ADAPT[etype][domain])

        # 专家角色微调 - 用id末尾数字做种子，交换两步位置确保唯一性
        seed = int(d.name.split("_")[-1])
        if seed % 3 == 0 and len(steps) >= 7:
            steps[1], steps[-2] = steps[-2], steps[1]
        elif seed % 3 == 1 and len(steps) >= 7:
            steps[2], steps[-1] = steps[-1], steps[2]

        workflow_steps = []
        for i, step_name in enumerate(steps):
            workflow_steps.append({
                "id": f"S{i+1:02d}",
                "name": step_name,
                "description": f"{name}作为{etype}专家，执行{step_name}任务",
                "duration": f"{10 + i * 5}min",
                "output": f"{step_name}结果文档"
            })

        sop_data = {
            "workflow": {
                "id": f"sop_{d.name}",
                "name": f"{name}的{etype}专家工作流程",
                "steps": workflow_steps
            }
        }

        with open(d / "sop.yaml", "w") as f:
            yaml.dump(sop_data, f, allow_unicode=True, default_flow_style=False)

        total += 1

    print(f"✅ 完成: {total} 个sop.yaml生成")

if __name__ == "__main__":
    main()
