#!/usr/bin/env python3
"""修复专家SOP同质化：为同类型同领域的专家生成差异化SOP步名"""
import random
from pathlib import Path

import yaml

EXPERTS_DIR = Path.home() / ".hermes" / "skills" / "experts-system" / "experts"

# 每种类型有至少5套不同步名组合，按领域和角色拆分
SOP_SETS = {
    "Pm": {
        "产品与商业": [
            ["市场调研与竞品分析","用户需求深度挖掘","产品定位与价值主张","路线图与版本规划","商业模型验证","跨部门资源协调","上线与运营监控","产品迭代复盘"],
            ["行业趋势扫描","痛点与机会识别","MVP定义与优先级","功能拆解与用户故事","原型验证与反馈","数据指标定义","A/B测试方案","发布与灰度策略"],
        ],
        "管理与沟通": [
            ["组织诊断与团队评估","沟通机制设计","干系人期望管理","冲突调解与共识","绩效体系搭建","激励方案制定","变革推动与落地","复盘与持续改进"],
            ["流程审计与效率优化","会议体系精简","信息同步机制","决策效率评估","风险预案设计","资源分配公平性","团队健康度评估","组织能力建设"],
        ],
        "法律与伦理": [
            ["法规合规审查","数据隐私评估","知识产权盘查","合同条款审核","风险合规报告","伦理委员会协调","监管对接与沟通","合规培训推动"],
        ],
        "供应链与物流": [
            ["供应商评估与准入","采购需求分析","物流网络优化","库存策略制定","供应商绩效管理","风险管理预案","成本控制分析","供应链数字化规划"],
        ],
        "default": [
            ["需求收集与分析","范围与目标定义","资源与预算评估","里程碑计划制定","进度追踪与控制","风险识别与应对","质量评审与验收","交付与复盘总结"],
        ],
    },
    "Intel": {
        "AI与机器学习": [
            ["AI技术情报搜集","论文与专利追踪","模型性能基准对比","开源生态监控","技术成熟度评估","产业应用趋势","竞争格局分析","情报报告生成"],
        ],
        "行业垂直": [
            ["行业动态监控","政策法规跟踪","市场数据分析","竞争情报搜集","专家网络访谈","预测分析建模","情报简报编写","情报分发与反馈"],
        ],
        "心理学与认知": [
            ["学术前沿追踪","研究方法论评估","实验数据分析","跨学科交叉研究","认知趋势研判","行为模式分析","研究报告撰写","同行评审参与"],
        ],
        "default": [
            ["多渠道情报搜集","信息可信度评估","关联分析建模","异常信号识别","趋势预测研判","情报产品编制","分发渠道管理","情报效果评估"],
        ],
    },
    "Coder": {
        "软件工程": [
            ["需求分析与拆解","系统设计文档","核心模块编码","接口定义与实现","单元测试编写","代码审查与重构","CI/CD集成","部署与监控"],
            ["技术方案调研","原型快速开发","性能基准测试","依赖管理与升级","安全漏洞排查","日志与异常处理","文档编写与维护","技术债清理"],
        ],
        "前端与用户体验": [
            ["UI需求分析","组件架构设计","状态管理方案","API对接实现","响应式适配","交互动效实现","性能优化与LCP","无障碍合规检查"],
        ],
        "移动与IoT": [
            ["设备端需求分析","嵌入式架构设计","固件编码实现","通信协议对接","低功耗优化","OTA升级方案","硬件集成测试","产线支持"],
        ],
        "default": [
            ["需求理解与技术拆解","架构分层设计","核心功能实现","接口契约定义","单元与集成测试","代码审查与重构","文档与注释","部署与发布验证"],
        ],
    },
    "Researcher": {
        "数学与理论": [
            ["理论假设提出","数学建模与推导","仿真验证设计","实验数据采集","统计分析验证","论文框架撰写","同行评审回应","学术报告宣讲"],
        ],
        "能源与环保": [
            ["环境数据分析","碳排放模型构建","能源效率评估","政策影响研究","实地调研采样","数据可视化","研究报告撰写","政策建议编制"],
        ],
        "生物与医学": [
            ["医学文献调研","生物学假设提出","临床试验设计","样本数据采集","生物统计分析","医学论文撰写","科研同行评审","药物评估报告"],
        ],
        "物理与材料": [
            ["物理理论推导","实验方案设计","材料制备工艺","性能表征测试","计算模拟验证","数据分析与拟合","论文撰写与修改","实验室安全管理"],
        ],
        "default": [
            ["文献系统调研","研究假设提出","实验方案设计","数据采集与分析","结果验证","论文写作","同行评审","知识传播"],
        ],
    },
}

def main():
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

        # 按类型获取SOP模板
        type_sets = SOP_SETS[etype]

        # 按领域获取可用模板，没有就用default
        if domain in type_sets:
            templates = type_sets[domain]
        else:
            templates = type_sets.get("default", [["任务分析","方案设计","执行","验证","交付"]])

        # 用姓名hash选模板
        idx = hash(name + d.name) % len(templates)
        steps = templates[idx]

        # 每人微调：基于hash交换两步
        seed = hash(d.name) * 7919
        rng = random.Random(seed)
        if len(steps) >= 6:
            steps = list(steps)
            # 每人微调2处
            i1 = rng.randint(0, len(steps)-1)
            i2 = rng.randint(0, len(steps)-1)
            steps[i1], steps[i2] = steps[i2], steps[i1]

        # 构建SOP
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

    print(f"✅ 完成: {total} 个专家SOP差异化修复")

if __name__ == "__main__":
    main()
