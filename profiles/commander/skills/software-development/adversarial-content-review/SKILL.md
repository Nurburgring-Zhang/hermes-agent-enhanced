---
name: adversarial-content-review
description: 对抗式内容审核 — 三Agent互怼机制。笔杆子Agent写初稿 → 参谋Agent五维批判(标题/结构/数据/价值/篇幅) → 裁判Agent打分(≥9分才放行)。集成到Hermes所有内容生产任务中强制执行。
version: 1.0.0
author: Hermes Agent
domain: software-development
tags:
  - adversarial-review
  - content-quality
  - three-agent
  - auto-review
  - quality-gate
triggers:
  - "对抗式审核"
  - "内容审查"
  - "三Agent互怼"
  - "质量把关"
  - "adversarial review"
  - "内容生产质量检查"
---

# 对抗式内容审核 (Adversarial Content Review)

## 核心理念

三Agent互怼机制来解决内容质量的终极问题：**一个AI看不出自己的问题**。

```
笔杆子Agent (Writer): 写初稿
    ↓
参谋Agent (Critic): 专门挑毛病
    ├── 标题批判
    ├── 结构批判
    ├── 数据批判
    ├── 价值批判
    └── 篇幅批判
    ↓
裁判Agent (Judge): 打分过滤
    └── ≥9分才放行
```

## 五维批判标准

| 维度 | 内容 | 典型问题 |
|------|------|---------|
| 标题 | 是否吸引人、是否准确、是否太长 | "标题太平"、"标题党" |
| 结构 | 逻辑是否清晰、段落衔接是否自然 | "结构松散"、"过渡生硬" |
| 数据 | 是否有数据支撑、数据可信度、是否需要更新 | "数据过时"、"缺乏数据支撑" |
| 价值 | 读完后读者是否有所得、信息密度是否合理 | "价值不足"、"信息密度太低" |
| 篇幅 | 是否过长/过短、每个部分是否均衡 | "头重脚轻"、"虎头蛇尾" |

## 强制集成

所有内容生产任务（文章/报告/PRD/设计文档/架构文档/推送文案）**必须**通过此审核。

```python
# Hermes集成步骤
# 1. 写完内容后自动触发
# 2. 让参谋Agent五维批判
# 3. 裁判Agent打分
# 4. 分数<9分 → 修改 → 重新审核 → 直到≥9分
# 5. 记录审核历史
```

## 与Hermes现有系统融合

- **CriticAgent** (production-reliability-engine) — 作为参谋Agent的后备
- **DegradationPreventer** — 检测内容中的降级模式
- **hermes-retrospect** — 审核结果的复盘积累
- **skillopt** — 审核标准的Skill验证

## 使用方式

```python
"用对抗式内容审核检查我刚写的[内容]，
 输出五维打分和改进建议"
```

## 验证清单

- [ ] 笔杆子Agent可写初稿
- [ ] 参谋Agent五维批判
- [ ] 裁判Agent打分
- [ ] ≥9分才放行
- [ ] 审核结果可追溯
