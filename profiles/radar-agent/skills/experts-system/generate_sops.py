#!/usr/bin/env python3
"""Generate differentiated SOP yaml for 120 Hermes experts (Architect/Innovator/Analyst/Collector)"""
import os
import re

EXPERTS_DIR = str(Path.home() / ".hermes" / "skills" / "experts-system" / "experts")

# ============================================================
# Domain -> step name adaptation mappings per expert type
# ============================================================

# Architect base steps (7 steps): needs demand analysis -> arch design -> tech selection -> review -> prototype -> perf eval -> debt analysis
ARCHITECT_STEPS = {
    "云计算与基础设施": [
        ("需求分析", "分析客户云基础设施需求与约束条件", "15min"),
        ("架构设计", "设计多云/混合云系统架构方案", "25min"),
        ("技术选型", "评估云原生技术栈与中间件选型", "20min"),
        ("方案评审", "组织架构评审并识别潜在风险", "15min"),
        ("原型验证", "搭建原型环境验证架构可行性", "25min"),
        ("性能评估", "进行性能基准测试与弹性容量评估", "20min"),
        ("技术债务", "识别基础设施技术债务并制定迁移计划", "15min"),
    ],
    "DevOps与SRE": [
        ("需求分析", "分析DevOps流水线与运维需求", "15min"),
        ("架构设计", "设计CI/CD与可观测性系统架构", "25min"),
        ("技术选型", "评估容器编排/监控/告警工具链", "20min"),
        ("方案评审", "组织SRE方案评审并检查SLA合规", "15min"),
        ("原型验证", "搭建混沌工程实验环境验证韧性", "25min"),
        ("性能评估", "评估系统吞吐瓶颈与故障恢复能力", "20min"),
        ("技术债务", "梳理自动化测试/部署/配置的技术债务", "15min"),
    ],
    "通信与网络": [
        ("需求分析", "分析通信网络架构需求与性能指标", "15min"),
        ("架构设计", "设计5G/边缘网络系统架构方案", "25min"),
        ("技术选型", "评估SDN/NFV/路由协议与硬件选型", "20min"),
        ("方案评审", "组织网络架构评审与安全合规审查", "15min"),
        ("原型验证", "搭建网络仿真环境验证拓扑设计", "25min"),
        ("性能评估", "进行网络延迟/吞吐/冗余测试", "20min"),
        ("技术债务", "识别老旧协议与网络设备的技术债务", "15min"),
    ],
}

INNOVATOR_STEPS = {
    "汽车与交通": [
        ("趋势扫描", "扫描汽车行业技术趋势与政策动向", "15min"),
        ("创意发散", "发散智能出行/车路协同创新方向", "20min"),
        ("可行性评估", "评估创意技术成熟度与落地可行性", "15min"),
        ("概念验证", "搭建自动驾驶/车联网概念验证原型", "25min"),
        ("方案优化", "优化创新方案的成本/性能/安全性", "20min"),
        ("效果评估", "评估方案在真实场景中的表现数据", "15min"),
        ("迭代规划", "规划下一阶段迭代方向与里程碑", "10min"),
    ],
    "机器人与自动化": [
        ("趋势扫描", "扫描机器人技术前沿与自动化趋势", "15min"),
        ("创意发散", "发散人机协作/智能控制创新方向", "20min"),
        ("可行性评估", "评估机器人方案的技术与成本可行性", "15min"),
        ("概念验证", "搭建机器人控制/感知系统概念原型", "25min"),
        ("方案优化", "优化运动控制/路径规划/安全性", "20min"),
        ("效果评估", "评估方案在产线/场景中的效果指标", "15min"),
        ("迭代规划", "规划下一代机器人平台的迭代路线", "10min"),
    ],
    "区块链与Web3": [
        ("趋势扫描", "扫描区块链与Web3行业技术演进趋势", "15min"),
        ("创意发散", "发散DeFi/DAO/数字身份创新方向", "20min"),
        ("可行性评估", "评估区块链方案的可扩展性与合规性", "15min"),
        ("概念验证", "搭建智能合约/跨链互操作概念原型", "25min"),
        ("方案优化", "优化Gas效率/共识机制/安全模型", "20min"),
        ("效果评估", "评估方案在测试网/沙盒中的表现", "15min"),
        ("迭代规划", "规划主网上线与生态建设的迭代路径", "10min"),
    ],
}

ANALYST_STEPS = {
    "AI与机器学习": [
        ("数据采集", "采集模型训练/评估所需数据集", "15min"),
        ("数据清洗", "清洗异常值/缺失值并标准化格式", "15min"),
        ("分析建模", "构建统计模型或机器学习基线模型", "25min"),
        ("结果解读", "解读模型输出与统计显著性结果", "15min"),
        ("洞察提炼", "提炼数据中隐藏的业务洞见与模式", "15min"),
        ("报告撰写", "撰写数据分析报告与可落地的建议", "15min"),
    ],
    "数据与存储": [
        ("数据采集", "采集数据库/存储系统的性能与容量数据", "15min"),
        ("数据清洗", "清洗存储指标中的噪声与异常点", "15min"),
        ("分析建模", "建立存储性能/容量预测分析模型", "25min"),
        ("结果解读", "解读存储瓶颈与数据分布特征", "15min"),
        ("洞察提炼", "提炼存储优化与容量规划的关键洞察", "15min"),
        ("报告撰写", "撰写存储系统分析报告与优化建议", "15min"),
    ],
    "经济与金融": [
        ("数据采集", "采集宏观经济指标与金融市场数据", "15min"),
        ("数据清洗", "清洗高频交易数据与财报中的异常", "15min"),
        ("分析建模", "构建量化模型/风险预测分析框架", "25min"),
        ("结果解读", "解读回测结果与风险敞口分析", "15min"),
        ("洞察提炼", "提炼市场趋势与投资策略核心洞察", "15min"),
        ("报告撰写", "撰写金融分析报告与策略建议", "15min"),
    ],
}

COLLECTOR_STEPS = {
    "AI与机器学习": [
        ("信源发现", "发现AI领域高质量学术/工程信源", "15min"),
        ("数据抓取", "抓取论文/模型库/竞赛数据资源", "20min"),
        ("清洗去重", "清洗学术数据中的重复/低质内容", "15min"),
        ("质量评估", "评估数据完整性/权威性/时效性", "15min"),
        ("存储入库", "结构化存储至知识图谱/向量库", "15min"),
        ("元数据标注", "标注数据集领域标签/质量评分/来源", "10min"),
    ],
    "地理与空间": [
        ("信源发现", "发现GIS/遥感领域权威数据信源", "15min"),
        ("数据抓取", "抓取地理空间/气象/遥感影像数据", "20min"),
        ("清洗去重", "清洗地理坐标系/投影/重叠数据", "15min"),
        ("质量评估", "评估空间数据精度/分辨率/时效性", "15min"),
        ("存储入库", "按地理格网/瓦片格式结构化存储", "15min"),
        ("元数据标注", "标注空间元数据/坐标系/采集时间", "10min"),
    ],
    "语言与翻译": [
        ("信源发现", "发现语料库/平行语料/词典权威信源", "15min"),
        ("数据抓取", "抓取多语种语料/翻译数据/术语库", "20min"),
        ("清洗去重", "清洗语料噪音/对齐偏移/重复片段", "15min"),
        ("质量评估", "评估语料对齐质量/语种覆盖/规模", "15min"),
        ("存储入库", "按语种/领域/难度结构化入库", "15min"),
        ("元数据标注", "标注语料来源/语种/领域/质量评分", "10min"),
    ],
}

# Expert list per type with their domains
experts = {}

# Architect: 35 experts
experts["Architect"] = [
    # 云计算与基础设施 (5)
    ("expert_091", "姚天佑", "云计算与基础设施"),
    ("expert_092", "闵伟毅", "云计算与基础设施"),
    ("expert_093", "韩振宇", "云计算与基础设施"),
    ("expert_094", "朱一鸣", "云计算与基础设施"),
    ("expert_095", "汪天成", "云计算与基础设施"),
    # DevOps与SRE (15)
    ("expert_141", "杜雨泽", "DevOps与SRE"),
    ("expert_142", "曹伟毅", "DevOps与SRE"),
    ("expert_143", "王明轩", "DevOps与SRE"),
    ("expert_144", "云昊然", "DevOps与SRE"),
    ("expert_145", "尹烨磊", "DevOps与SRE"),
    ("expert_146", "于泽宇", "DevOps与SRE"),
    ("expert_147", "萧伟毅", "DevOps与SRE"),
    ("expert_148", "马昱辰", "DevOps与SRE"),
    ("expert_149", "金景行", "DevOps与SRE"),
    ("expert_150", "温昊天", "DevOps与SRE"),
    ("expert_151", "包思源", "DevOps与SRE"),
    ("expert_152", "姜振宇", "DevOps与SRE"),
    ("expert_153", "连哲瀚", "DevOps与SRE"),
    ("expert_154", "祝振宇", "DevOps与SRE"),
    ("expert_155", "李曜辰", "DevOps与SRE"),
    # 通信与网络 (15)
    ("expert_216", "安瑾瑜", "通信与网络"),
    ("expert_217", "龚明达", "通信与网络"),
    ("expert_218", "晏瑾瑜", "通信与网络"),
    ("expert_219", "许瑾瑜", "通信与网络"),
    ("expert_220", "屈昊然", "通信与网络"),
    ("expert_221", "鲍承宇", "通信与网络"),
    ("expert_222", "舒鹏程", "通信与网络"),
    ("expert_223", "龚思远", "通信与网络"),
    ("expert_224", "任逸尘", "通信与网络"),
    ("expert_225", "段浩轩", "通信与网络"),
    ("expert_226", "尹正阳", "通信与网络"),
    ("expert_227", "卢子墨", "通信与网络"),
    ("expert_228", "卢浩然", "通信与网络"),
    ("expert_229", "赵思源", "通信与网络"),
    ("expert_230", "梅泽楷", "通信与网络"),
]

# Innovator: 30 experts
experts["Innovator"] = [
    # 汽车与交通 (10)
    ("expert_311", "管启瑞", "汽车与交通"),
    ("expert_312", "喻泽洋", "汽车与交通"),
    ("expert_313", "鲁文昊", "汽车与交通"),
    ("expert_314", "贾浩然", "汽车与交通"),
    ("expert_315", "司子墨", "汽车与交通"),
    ("expert_316", "方天佑", "汽车与交通"),
    ("expert_317", "阮明达", "汽车与交通"),
    ("expert_318", "连雨泽", "汽车与交通"),
    ("expert_319", "项弘文", "汽车与交通"),
    ("expert_320", "祝思远", "汽车与交通"),
    # 机器人与自动化 (10)
    ("expert_341", "席弘远", "机器人与自动化"),
    ("expert_342", "向修远", "机器人与自动化"),
    ("expert_343", "柏鹏程", "机器人与自动化"),
    ("expert_344", "姜思慧", "机器人与自动化"),
    ("expert_345", "左鹏程", "机器人与自动化"),
    ("expert_346", "席瑾瑜", "机器人与自动化"),
    ("expert_347", "强睿智", "机器人与自动化"),
    ("expert_348", "盛弘远", "机器人与自动化"),
    ("expert_349", "卢辰逸", "机器人与自动化"),
    ("expert_350", "季清风", "机器人与自动化"),
    # 区块链与Web3 (10)
    ("expert_351", "安昱辰", "区块链与Web3"),
    ("expert_352", "田伟泽", "区块链与Web3"),
    ("expert_353", "庄致远", "区块链与Web3"),
    ("expert_354", "窦昊天", "区块链与Web3"),
    ("expert_355", "柳睿智", "区块链与Web3"),
    ("expert_356", "张远峰", "区块链与Web3"),
    ("expert_357", "季诗嘉", "区块链与Web3"),
    ("expert_358", "韦子轩", "区块链与Web3"),
    ("expert_359", "蔡健柏", "区块链与Web3"),
    ("expert_360", "孟伟奇", "区块链与Web3"),
]

# Analyst: 30 experts
experts["Analyst"] = [
    # AI与机器学习 (5)
    ("expert_007", "陆雅婷", "AI与机器学习"),
    ("expert_008", "韦睿渊", "AI与机器学习"),
    ("expert_009", "丁梦瑶", "AI与机器学习"),
    ("expert_011", "路清风", "AI与机器学习"),
    ("expert_012", "毕思远", "AI与机器学习"),
    # 数据与存储 (15)
    ("expert_066", "强鹏飞", "数据与存储"),
    ("expert_067", "习子墨", "数据与存储"),
    ("expert_068", "鲍哲翰", "数据与存储"),
    ("expert_069", "屈修杰", "数据与存储"),
    ("expert_070", "倪鸿儒", "数据与存储"),
    ("expert_071", "倪曜辰", "数据与存储"),
    ("expert_072", "马远峰", "数据与存储"),
    ("expert_073", "容晟睿", "数据与存储"),
    ("expert_074", "纪天佑", "数据与存储"),
    ("expert_075", "江弘远", "数据与存储"),
    ("expert_076", "司浩宇", "数据与存储"),
    ("expert_077", "戴泽宇", "数据与存储"),
    ("expert_078", "樊思远", "数据与存储"),
    ("expert_079", "朱辰逸", "数据与存储"),
    ("expert_080", "周子安", "数据与存储"),
    # 经济与金融 (10)
    ("expert_301", "樊振宇", "经济与金融"),
    ("expert_302", "张泽楷", "经济与金融"),
    ("expert_303", "穆俊驰", "经济与金融"),
    ("expert_304", "蓝明杰", "经济与金融"),
    ("expert_305", "穆天骐", "经济与金融"),
    ("expert_306", "秦启明", "经济与金融"),
    ("expert_307", "狄思琪", "经济与金融"),
    ("expert_308", "韦睿智", "经济与金融"),
    ("expert_309", "雷鸿晖", "经济与金融"),
    ("expert_310", "田景行", "经济与金融"),
]

# Collector: 25 experts
experts["Collector"] = [
    # AI与机器学习 (6)
    ("expert_001", "鲁思慧", "AI与机器学习"),
    ("expert_002", "洪伟奇", "AI与机器学习"),
    ("expert_003", "谢瑾瑜", "AI与机器学习"),
    ("expert_004", "苏雨晴", "AI与机器学习"),
    ("expert_005", "韦佳音", "AI与机器学习"),
    ("expert_006", "白烨磊", "AI与机器学习"),
    # 地理与空间 (10)
    ("expert_291", "吕浩宇", "地理与空间"),
    ("expert_292", "苏浩轩", "地理与空间"),
    ("expert_293", "宋瑾瑜", "地理与空间"),
    ("expert_294", "狄俊驰", "地理与空间"),
    ("expert_295", "戚建国", "地理与空间"),
    ("expert_296", "晏黎明", "地理与空间"),
    ("expert_297", "丘振宇", "地理与空间"),
    ("expert_298", "鲍曜辰", "地理与空间"),
    ("expert_299", "樊越泽", "地理与空间"),
    ("expert_300", "庞维新", "地理与空间"),
    # 语言与翻译 (9)
    ("expert_331", "路雅馨", "语言与翻译"),
    ("expert_332", "蒲正阳", "语言与翻译"),
    ("expert_334", "郝梦蝶", "语言与翻译"),
    ("expert_335", "程承志", "语言与翻译"),
    ("expert_336", "费明杰", "语言与翻译"),
    ("expert_337", "徐婉清", "语言与翻译"),
    ("expert_338", "顾嘉诚", "语言与翻译"),
    ("expert_339", "蓝梦蝶", "语言与翻译"),
    ("expert_340", "邵立诚", "语言与翻译"),
]

# Role mappings per expert to build the workflow name
# We'll read from identity.yaml to get the role
def get_role(expert_id):
    path = os.path.join(EXPERTS_DIR, expert_id, "identity.yaml")
    with open(path, encoding="utf-8") as f:
        content = f.read()
    m = re.search(r"role:\s*(.+)", content)
    if m:
        return m.group(1).strip()
    return "专家"

def build_sop(expert_id, name, expert_type, domain):
    role = get_role(expert_id)

    if expert_type == "Architect":
        steps_data = ARCHITECT_STEPS[domain]
    elif expert_type == "Innovator":
        steps_data = INNOVATOR_STEPS[domain]
    elif expert_type == "Analyst":
        steps_data = ANALYST_STEPS[domain]
    elif expert_type == "Collector":
        steps_data = COLLECTOR_STEPS[domain]
    else:
        raise ValueError(f"Unknown type: {expert_type}")

    workflow_name = f"{role}工作流程"

    lines = []
    lines.append("workflow:")
    lines.append(f"  id: sop_{expert_id}")
    lines.append(f"  name: {workflow_name}")
    lines.append("  steps:")

    for i, (step_name, desc, dur) in enumerate(steps_data, 1):
        lines.append(f"  - id: S{i:02d}")
        lines.append(f"    name: {step_name}")
        lines.append(f"    description: {desc}")
        lines.append(f"    duration: {dur}")

    return "\n".join(lines)

# Generate all SOPs
count = 0
for expert_type, expert_list in experts.items():
    for expert_id, name, domain in expert_list:
        content = build_sop(expert_id, name, expert_type, domain)
        sop_path = os.path.join(EXPERTS_DIR, expert_id, "sop.yaml")
        with open(sop_path, "w", encoding="utf-8") as f:
            f.write(content + "\n")
        count += 1
        print(f"[{count:03d}] {expert_id} ({name}) - {expert_type}/{domain} -> sop.yaml")

print(f"\n✅ Generated {count} SOP files total")
