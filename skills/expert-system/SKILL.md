---
name: expert-system
description: Hermes Expert System - 390 AI experts across 30 domains. Routes requests to the appropriate specialized expert team or individual expert for consultation, design, review, or task execution. Fully migrated from OpenClaw expert_system_config.json (2026-04-21).
version: 2.0.0
author: Hermes Agent
license: MIT
dependencies: []
metadata:
  hermes:
    tags: ["expert-system", "multi-agent", "routing", "consultation", "experts"]
    migration_date: "2026-04-21"
    source: "/mnt/d/openclaw/experts/"
---

# Hermes Expert System

Central routing hub for **390 specialized AI experts** organized across **30 professional domains**. This system provides access to world-class expertise spanning AI/ML, software engineering, design, product, data science, security, cloud infrastructure, and many more verticals.

> **迁移状态**: ✅ 完全迁移 (2026-04-21)
> - Expert definitions: `/mnt/d/openclaw/experts/expert_system_config.json` (390 experts)
> - Individual AGENTS.md: `/mnt/d/openclaw/experts/expert_XXX/AGENTS.md` (390 files)
> - Hermes完整定义: `~/.hermes/skills/expert-system/AGENTS.md` (601 lines)

## When to Use

## 触发条件
- 用户提及此功能相关关键词时
- 遇到此领域的标准问题时
- 需要执行该领域的标准操作时


When you need:
- Expert consultation on a specialized technical or business domain
- Architecture design or code review from a senior specialist
- Cross-domain analysis requiring multiple expert perspectives
- A complete solution from design to implementation to testing
- Specialized knowledge not covered by general-purpose skills

## 390 Experts Across 30 Domains

| Domain | Expert Count | Sample Expert |
|--------|-------------|---------------|
| AI与机器学习 | 30 | expert_001: 深度学习架构师 (鲁思慧, 22年) |
| 软件工程 | 20 | expert_031: 微服务架构专家 (谢天成, 26年) |
| 通信与网络 | 15 | expert_051: 网络安全专家 (邓天骐, 32年) |
| 质量与测试 | 15 | - |
| 行业垂直 | 15 | - |
| 管理与沟通 | 15 | - |
| 移动与IoT | 15 | - |
| 数据与存储 | 15 | - |
| 数学与理论 | 15 | - |
| 安全与隐私 | 15 | - |
| 前端与用户体验 | 15 | - |
| 产品与商业 | 15 | expert_111: 产品战略专家 (徐志泽, 34年) |
| 云计算与基础设施 | 15 | - |
| DevOps与SRE | 15 | - |
| 艺术与设计 | 10 | - |
| 内容与创意 | 10 | - |
| 语言与翻译 | 10 | - |
| 能源与环保 | 10 | - |
| 经济与金融 | 10 | - |
| 生物与医学 | 10 | - |
| 物理与材料 | 10 | - |
| 法律与伦理 | 10 | - |
| 汽车与交通 | 10 | - |
| 机器人与自动化 | 10 | - |
| 教育与培训 | 10 | - |
| 心理学与认知 | 10 | - |
| 地理与空间 | 10 | - |
| 哲学与人文 | 10 | - |
| 区块链与Web3 | 10 | - |
| 供应链与物流 | 10 | - |

## Personality Gene Distribution (15 Types)

| 性格 | 人数 | 代表口头禅 |
|------|------|-----------|
| 连接者，擅长发现别人看不到的关联 | 37 | "等等，这个逻辑有问题。" |
| 质疑者，每个假设都要被挑战 | 34 | "我来搞定。" |
| 执行力爆表，从不拖延，说完就做 | 32 | "先跑起来再说。" |
| 极致审美，像素级要求，对'够用了'过敏 | 30 | "竞品怎么做的？" |
| 共情高手，永远站在用户角度思考 | 28 | "有没有更简单的方案？" |
| 沟通大师，能在5分钟内对齐所有人 | 27 | "文档写了吗？" |
| 细节强迫症，魔鬼藏在细节里 | 26 | "这个ROI够吗？" |
| 深度思考者，每个决策背后有三层推理 | 24 | "监控埋了吗？" |
| 实战派，理论再好不如跑通一次 | 24 | - |
| 战略视野强，冷静判断，一切用数据说话 | 24 | - |
| 稳重可靠，是团队的定海神针 | 24 | - |
| 创新狂人，从不走寻常路 | 23 | - |
| 系统思考者，看问题从不只看一点 | 22 | - |
| 速度型选手，快狠准是信条 | 21 | "删掉，少即是多。" |
| 完美主义者，交付物必须是行业标杆 | 14 | - |

## Top 10 Individual Experts (Direct Invocation)

| Expert | 姓名 | 角色 | 性格 | 口头禅 | Skill |
|--------|------|------|------|--------|-------|
| expert_001 | 鲁思慧 | 深度学习架构师 | 深度思考者 | 监控埋了吗？ | `expert-ai-dl-arch` |
| expert_002 | (expert_002) | NLP专家 | - | - | `expert-ai-nlp` |
| expert_003 | (expert_003) | CV专家 | - | - | `expert-ai-cv` |
| expert_004 | (expert_004) | 强化学习专家 | - | - | `expert-ai-rl` |
| expert_005 | (expert_005) | 联邦学习专家 | - | - | `expert-ai-federated` |
| expert_006 | (expert_006) | 模型压缩专家 | - | - | `expert-ai-model-compress` |
| expert_007 | (expert_007) | AI伦理专家 | - | - | `expert-ai-ethics` |
| expert_008 | (expert_008) | AutoML专家 | - | - | `expert-ai-automl` |
| expert_009 | (expert_009) | 知识图谱专家 | - | - | `expert-ai-knowledge-graph` |
| expert_010 | (expert_010) | 多模态AI专家 | - | - | `expert-ai-multimodal` |

## How to Invoke

### Domain Team (recommended for most cases)
```
skill://ai-ml-experts        # AI & Machine Learning
skill://engineering-experts  # Software Engineering
skill://product-experts      # Product & Business
skill://qa-experts           # Quality & Testing
skill://devops-experts       # DevOps & SRE
skill://security-experts      # Security & Privacy
skill://cloud-infra-experts  # Cloud & Infrastructure
skill://data-storage-experts  # Data & Storage
skill://frontend-ux-experts  # Frontend & UX
skill://mobile-iot-experts    # Mobile & IoT
```

### Individual Expert (for specific top-tier experts)
```
skill://expert-ai-dl-arch        # Deep Learning Architect (鲁思慧)
skill://expert-ai-nlp             # NLP Expert
skill://expert-ai-cv              # Computer Vision Expert
skill://expert-ai-rl              # Reinforcement Learning Expert
skill://expert-ai-federated       # Federated Learning Expert
skill://expert-ai-model-compress  # Model Compression Expert
skill://expert-ai-ethics          # AI Ethics Expert
skill://expert-ai-automl          # AutoML Expert
skill://expert-ai-knowledge-graph # Knowledge Graph Expert
skill://expert-ai-multimodal      # Multimodal AI Expert
```

## Expert Capabilities

Each expert provides:
- **World-class domain knowledge**: 22-34 years of professional experience equivalent
- **Full-stack solution capability**: From design to implementation to review
- **Cross-domain collaboration**: Can consult with other domain experts
- **Tool access**: web_search, web_fetch, read/write, exec, memory_search, memory_get, sessions_spawn, cron, image_generate
- **Knowledge沉淀**: Every consultation is archived for future reference
- **9-step workflow**: 需求接收 → 方案设计 → 执行 → 质量自检 → 交付 → 复盘

## Expert Workflow (9 Steps)

```
1. 需求接收：理解任务需求与约束条件
2. 背景调研：沉浸式收集相关上下文
3. 方案设计：制定执行方案（方法+步骤+标准）
4. 多源验证：三轮验证式信息搜集
5. 原子执行：按方案精密执行每一步
6. 质量自检：对照标准进行完整性/准确性检查
7. 交付输出：产出有数据/逻辑支撑的交付物
8. 复盘总结：提炼经验，更新知识库
9. 协作汇报：通知相关方，记录状态
```

## Workflow

```
User Request
    |
    v
Expert System (routing by domain keyword)
    |
    +---> Domain Team Skill (e.g., ai-ml-experts)
    |         |
    |         v
    |     Expert Consultation (390 experts available)
    |         |
    |         +---> Cross-domain if needed
    |         |
    |         v
    |     Solution / Recommendation
    |
    +---> Individual Expert (e.g., expert_001)
              |
              v
          Direct Expert Consultation
```

## Source Data (Accurate as of 2026-04-21)

| Data | Location | Count |
|------|----------|-------|
| Expert Config | `/mnt/d/openclaw/experts/expert_system_config.json` | 390 experts |
| Expert AGENTS.md | `/mnt/d/openclaw/experts/expert_XXX/AGENTS.md` | 390 files |
| Hermes AGENTS.md | `~/.hermes/skills/expert-system/AGENTS.md` | 601 lines |
| Domains | 30 domains | See table above |
| Personality Types | 15 types | See table above |

## Notes

- For complex multi-domain problems, start with the primary domain team
- Expert teams can collaborate and spawn sub-sessions for cross-domain work
- All 390 experts follow the same quality standards and 9-step workflow
- Solutions must have data/logic/case support
- Risk assessments must include probability + impact + mitigation measures
- **CORRECTED (2026-04-21)**: Was incorrectly listed as "432 experts" — actual count is **390 experts** across 30 domains

## 回滚方案
### 快速回滚
如果部署后发现问题：
1. 使用版本控制回退到上一个提交：`git revert HEAD`
2. 确认回滚后系统状态正常
3. 通知相关方变更已撤销

### 数据安全
- 所有修改前确认有备份
- 配置变更记录版本历史
