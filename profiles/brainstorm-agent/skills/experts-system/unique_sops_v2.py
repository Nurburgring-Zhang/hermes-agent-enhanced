#!/usr/bin/env python3
"""为剩余11种类型专家生成差异化SOP"""
import random
from pathlib import Path

import yaml

EXPERTS_DIR = Path.home() / ".hermes" / "skills" / "experts-system" / "experts"

# 之前unique_sops.py只覆盖了4种(155人)，补充剩余11种(235人)
SOP_SETS = {
    "Architect": {
        "default": [
            ["系统需求分析","架构方案设计","技术选型评估","架构评审与优化","原型验证","性能评估报告","技术债务梳理","演进路线规划"],
        ],
        "云计算与基础设施": [
            ["云资源需求分析","多云架构设计","基础设施选型","容量规划评估","灾备方案设计","成本优化分析","运维自动化规划","架构演进路线"],
        ],
        "DevOps与SRE": [
            ["SLO/SLI定义","系统可靠性设计","容量与性能评估","事故响应流程","可观测性方案","混沌工程规划","运维自动化设计","架构韧性评估"],
        ],
        "通信与网络": [
            ["网络需求分析","网络架构设计","协议选型评估","安全架构设计","流量规划","QoS策略制定","网络演进规划","性能基准测试"],
        ],
    },
    "Innovator": {
        "default": [
            ["趋势扫描与分析","创意发散与生成","可行性评估","概念原型验证","方案优化迭代","效果评估","落地路线规划"],
        ],
        "汽车与交通": [
            ["出行趋势扫描","场景痛点挖掘","智能方案设计","概念车验证","用户反馈收集","方案迭代","产业链资源评估","落地路线图"],
        ],
        "机器人与自动化": [
            ["自动化需求扫描","技术瓶颈分析","创新方案构思","原型机/POC验证","效率评估","方案调优","产业链调研","规模化路线"],
        ],
        "区块链与Web3": [
            ["链上生态监控","去中心化趋势分析","DApp创新设计","智能合约验证","社区反馈收集","TVL/用户评估","生态建设规划"],
        ],
    },
    "Analyst": {
        "default": [
            ["数据需求梳理","数据采集与清洗","探索性分析","统计建模","可视化呈现","洞察提炼","报告撰写","建议方案制定"],
        ],
        "AI与机器学习": [
            ["模型评估需求","训练数据质量分析","模型性能基准测试","偏差分析","结果可解释性评估","对比实验","分析报告","优化建议"],
        ],
        "数据与存储": [
            ["存储需求分析","数据流梳理","存储性能分析","成本评估","容量预测","分层策略","分析报告","优化建议"],
        ],
        "经济与金融": [
            ["宏观经济数据采集","政策影响分析","市场趋势建模","风险因子识别","投资组合分析","预测模型","研究报告","策略建议"],
        ],
    },
    "Collector": {
        "default": [
            ["采集需求分析","信源发现与评估","数据抓取执行","清洗与去重","质量评估","存储与索引","元数据标注","采集报告"],
        ],
        "AI与机器学习": [
            ["AI数据需求分析","语料源发现","爬虫策略设计","数据抓取执行","清洗与标注","质量抽检","存储入库","元数据管理"],
        ],
        "地理与空间": [
            ["空间需求分析","遥感源评估","GIS数据采集","坐标校准","数据融合","质量验证","瓦片存储","元数据维护"],
        ],
        "语言与翻译": [
            ["多语种源评估","语料采集执行","对齐与清洗","质量评分","平行语料入库","元数据标注","入库报告"],
        ],
    },
    "Security": {
        "default": [
            ["资产发现与盘点","威胁建模分析","漏洞扫描执行","渗透测试","安全审计","事件响应处置","合规检查","安全加固建议"],
        ],
    },
    "Companion": {
        "default": [
            ["需求倾听与理解","情感状态分析","知识检索匹配","推理与建议","情感支持陪伴","反馈记录整理","知识更新维护"],
        ],
    },
    "Acceptance": {
        "default": [
            ["验收需求审查","测试计划制定","测试用例设计","执行与缺陷跟踪","回归验证","质量评估报告","验收签字","交付物归档"],
        ],
    },
    "Office": {
        "default": [
            ["工单受理与分派","资源协调与调度","流程节点处理","文档编制与归档","审批跟踪","归档管理","效果反馈"],
        ],
        "管理与沟通": [
            ["行政事务受理","文件流转处理","会议组织协调","办公资源调配","流程审批跟踪","档案归集管理","满意度反馈收集"],
        ],
        "教育与培训": [
            ["培训需求受理","教学资源协调","教务流程处理","教案文档编制","教学审批流转","学员档案管理","教学效果反馈"],
        ],
    },
    "Artist": {
        "default": [
            ["设计需求沟通","创意构思与发散","概念草图设计","视觉方案精修","评审反馈处理","修改完善","交付归档"],
        ],
        "艺术与设计": [
            ["设计需求理解","概念创意发散","视觉方案设计","配色与字体定稿","评审与修改","定稿输出","归档整理"],
        ],
    },
    "AIGC": {
        "default": [
            ["内容选题策划","素材准备整理","模型选择与调参","内容生成与优化","质量审核","迭代优化","成品交付"],
        ],
        "内容与创意": [
            ["内容策略策划","素材库整理","AI模型选型","生成执行","质量审核","效果分析","存档备案"],
        ],
    },
    "Media": {
        "default": [
            ["热点追踪与选题","内容策划定位","素材制作编排","渠道分发排期","互动管理与响应","数据采集分析","策略优化迭代"],
        ],
        "内容与创意": [
            ["热点监控与选题","内容策略规划","多媒体素材制作","多平台分发","用户互动管理","多源数据分析","内容策略优化"],
        ],
    },
}

def main():
    # 先读取所有专家类型分布
    type_count = {}
    for d in sorted(EXPERTS_DIR.iterdir()):
        if not d.is_dir(): continue
        iy = d / "identity.yaml"
        if not iy.exists(): continue
        with open(iy) as f: data = yaml.safe_load(f) or {}
        etype = data.get("agent", {}).get("expert_type", "")
        type_count[etype] = type_count.get(etype, 0) + 1

    total = 0
    for d in sorted(EXPERTS_DIR.iterdir()):
        if not d.is_dir(): continue
        iy = d / "identity.yaml"
        sop = d / "sop.yaml"
        if not iy.exists() or not sop.exists(): continue

        with open(iy) as f:
            data = yaml.safe_load(f) or {}
        agent = data.get("agent", {})
        etype = agent.get("expert_type", "")
        domain = agent.get("domain", "")
        name = agent.get("name", "")

        if etype not in SOP_SETS:
            continue

        # 获取模板
        type_sets = SOP_SETS[etype]
        if domain in type_sets:
            templates = type_sets[domain]
        else:
            templates = type_sets.get("default", [["任务分析","方案设计","执行","验证","交付"]])

        idx = hash(name + d.name) % len(templates)
        steps = list(templates[idx])

        # 每人微调
        rng = random.Random(hash(d.name) * 7919)
        if len(steps) >= 6:
            i1 = rng.randint(0, len(steps)-1)
            i2 = rng.randint(0, len(steps)-1)
            steps[i1], steps[i2] = steps[i2], steps[i1]

        workflow_steps = []
        for i, step_name in enumerate(steps):
            workflow_steps.append({
                "id": f"S{i+1:02d}",
                "name": step_name,
                "description": f"{name}执行{etype}工作中的{step_name}步骤",
                "duration": f"{10 + i * 5}min",
                "output": f"{step_name}交付物"
            })

        sop_data = {
            "workflow": {
                "id": f"sop_{d.name}",
                "name": f"{name}的{etype}工作流程",
                "steps": workflow_steps
            }
        }

        with open(sop, "w") as f:
            yaml.dump(sop_data, f, allow_unicode=True, default_flow_style=False)

        total += 1

    print(f"✅ 完成: {total} 个专家SOP差异化修复（全部15类型）")

if __name__ == "__main__":
    main()
