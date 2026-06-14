---
name: cognitive-distillation-ppt-director
description: 女娲Skill(认知蒸馏) + PPT Director 方法论 — 先蒸馏受众认知模型和评审专家模型，再基于结构化模型驱动PPT全流程生产。适合所有需要精准面向受众的输出场景。
version: 1.0.0
author: Hermes Agent
domain: autonomous-systems
tags:
  - cognitive-distillation
  - ppt-director
  - audience-modeling
  - reviewer-model
  - presentation
triggers:
  - "认知蒸馏"
  - "女娲Skill"
  - "PPT Director"
  - "受众建模"
  - "评审模型"
  - "PPT生成"
  - "演示文稿"
---

# 认知蒸馏 + PPT Director

## 核心理念

来自花叔的女娲 Skill + PPT Director 方法论的全面集成：

一句话总结：**先搞清楚他的脑子怎么转，再决定输出的每页放什么。**

### 三步法

```
Step 1: 蒸馏受众认知模型 → 搞清楚看的那个人怎么思考
Step 2: 蒸馏评审专家模型 → 搞清楚谁会挑毛病
Step 3: PPT Director调度 → 基于模型精准生产
```

## 认知蒸馏引擎

### 6Agent并行蒸馏

```
用户输入: "用女娲蒸馏'袁家军'"
    │
    女娲自动调度6个Agent并行工作:
    │
    ├── 著作Agent    — 调研该角色的著作、文章、公开讲话
    ├── 对话Agent    — 分析其对话风格、提问方式、思维习惯
    ├── 表达Agent    — 提炼其常用表达、比喻、价值判断
    ├── 批评Agent    — 找出其常见的否定模式、反感的事物
    ├── 决策Agent    — 梳理其决策框架、权重分配
    └── 时间线Agent  — 追踪其认知演变和立场变化
```

### 认知模型输出 (audience-card.md)

```yaml
# audience-card.md
name: 袁家军
role: 省级分管数字化副省长

心智模型:
  核心思维: 系统工程思维 × 数据驱动
  决策框架: 问题导向 → 数据验证 → 机制创新 → 可复制推广
  注意力分配: 前3页必须看到核心成效和亮点数据

否决触发器:
  - 只说理念不讲落地
  - 数据前后不一致
  - 避谈困难和挑战
  - 表达空泛没有具体案例

偏好呈现:
  - 先总后分，先结论后论据
  - 数据可视化优先于大段文字
  - 对比呈现: 改革前vs改革后
```

### 评审模型输出 (reviewer-card.md)

```yaml
# reviewer-card.md
name: 袁家军 (作为评审专家)
审查维度:
  - 数据闭环: 输入→产出→成效是否可追溯
  - 抓手逻辑: 有无具体可操作的工程/项目
  - 可复制性: 经验能否推广
  - 风险可控: 是否有预案和底线
```

## PPT Director 5阶段

```
A: 灵感激发      (只有一个主题/想法 → 发散思路)
B: 内容打磨      (有思路或原始材料 → 观点型大纲+标准交付文档)
C: 视觉定义      (有标准交付文档 → 页型分配+风格映射)
D: 代码生成      (视觉定义已完成 → python-pptx代码→ .pptx)
E: 迭代优化      (有PPT初稿 → 三重评审挑毛病→ 修改清单)
```

### 17种标准页型

| 编号 | 名称 | 说明 |
|------|------|------|
| T01 | 封面页 | 标题+副标题+汇报人 |
| T02 | 目录页 | 整体结构概览 |
| T03 | 章节过渡页 | 大段落切换 |
| T04 | 纯文字观点页 | 一个核心观点+3个要点 |
| T05 | 数据图表页 | 柱状图/折线图/饼图 |
| T06 | 对比页 | 改革前vs改革后 |
| T07 | 流程图页 | 步骤/时间线/路径 |
| T08 | 架构图页 | 系统架构/组织结构 |
| T09 | 案例展示页 | 具体案例+成效 |
| T10 | 数字突出页 | 1-3个大数字+说明 |
| T11-T17 | ... | 图片+文字/引言/矩阵/列表/地图/时间轴/总结 |

### 评审三检查

```yaml
audience_check:
  - 前3页是否抓住注意力？
  - 受众是否关心这些内容？
  - 信息密度是否匹配受众耐心？

reviewer_check:
  - 逻辑有抓手吗？
  - 风险闭环了吗？
  - 表达不空泛？

style_check:
  - 颜色规范？
  - 字数控制？(每页≤50字)
  - 页型使用合理？
```

## 与Hermes现有系统融合

### 1. 受众模型 → 用户画像

Hermes的 `hy_memory.persona_summary` 可以作为受众模型的初始输入。
认知蒸馏的产出可以固化到memory，反复使用。

### 2. 评审模型 → 质量检查

评审三检查与 `production-reliability-engine` 的 CriticAgent 审查互补：
- 评审三检查：面向PPT内容质量
- CriticAgent：面向任务执行质量
- DegradationPreventer：面向降级检测

### 3. PPT生成管道

```python
# 全自动化管道
# Step 1: 蒸馏受众
audience_model = distill("袁家军")
# Step 2: 评审模型
reviewer_model = distill_as_reviewer("袁家军")
# Step 3: PPT Director规划
doc = ppt_director_plan(topic, audience_model, reviewer_model)
# Step 4: 达尔文优化
doc = darwin_optimize(doc)
# Step 5: 代码生成
pptx = ppt_director_generate(doc, style="digital-zhejiang")
# Step 6: 评审验证
review = triple_review(pptx, audience_model, reviewer_model)
```

### 4. 通用化：不限于PPT

认知蒸馏+Director模式适用于**所有面向受众的输出**：
- 报告/方案/演讲
- 代码评审（面向技术Leader）
- API设计（面向使用方）
- 架构决策（面向团队）

## 验证清单

- [ ] 可以蒸馏具体人物的认知模型
- [ ] 受众卡包含心智模型+否决触发器
- [ ] 评审卡包含审查维度+否决点
- [ ] PPT Director可接管从A到E的完整流程
- [ ] 17种页型可用
- [ ] 评审三检查可执行
- [ ] 产出物与达尔文互优化可联动
- [ ] 不限于PPT的通用输出模式
