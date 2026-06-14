---
name: darwin-skill-evolver-bridge
description: Darwin-skill + SkillEvolver 双向互优化系统 — 基于清华SkillEvolver论文(角色分离+闭环进化) + Darwin 9维评估+棘轮机制。两个skill互相调教、互相进化，形成完整的自增强循环。
version: 1.0.0
author: Hermes Agent
domain: autonomous-systems
tags:
  - darwin
  - skill-evolver
  - mutual-optimization
  - self-evolution
  - 9-dimension-scoring
  - ratchet-mechanism
triggers:
  - "Darwin"
  - "SkillEvolver"
  - "互优化"
  - "skill进化"
  - "9维评估"
  - "棘轮机制"
  - "四类失败归因"
---

# Darwin-SkillEvolver 互优化系统

## 核心理念

基于三篇前沿论文的落地融合：
- **清华 SkillEvolver**（角色分离+闭环进化）
- **微软 Darwin-skill**（9维评估+棘轮机制）
- **EmbodiSkill**（南大/微软/清华AIR，四类失败归因）

核心结论：**两个skills互相调教4轮，Skill可以从61分进化到86分——不需要更强的模型，只需要更好的方法论。**

## 双角色架构

```
Darwin (评估专家)              SkillEvolver (进化专家)
    │                                │
    │ 9维评估体系                    │ 角色分离+闭环进化
    │ 棘轮机制                       │ 策略多样化探索
    │ 探索性重写                     │ 对比式更新
    │ 版本追踪                       │ 独立审计
    │                                │
    └──────────互优化互审────────────┘
         │                    │
         ↓                    ↓
   darwin注入到             skill-evolver注入到
   skill-evolver:           darwin:
   - 9维rubric              - 四类失败归因
   - 棘轮机制               - 补丁式修订
   - 探索性重写              - CHECKPOINT检查点
   - results.tsv版本追踪
```

## 9维评估体系

Darwin 的 9 维评估（满分100）：

| 维度 | 权重 | 评估内容 |
|------|------|---------|
| dim1 frontmatter | 10% | YAML frontmatter完整性 |
| dim2 workflow_flow | 15% | 工作流清晰度和步骤完整性 |
| dim3 failure_coding | 15% | 失败模式是否已编码 |
| dim4 checkpoint | 10% | 检查点设计是否合理 |
| dim5 executability | 15% | 可执行具体性 |
| dim6 pitfalls | 10% | 陷阱和黑名单 |
| dim7 verification | 10% | 验证checklist |
| dim8 practical_test | 10% | 实测表现 |
| dim9 readability | 5% | 可读性 |

**棘轮机制**：分数只能涨不能跌。每次优化后重新评估，分数降了就自动回滚。

## 四类失败归因

EmbodiSkill 论文核心（补丁式修订的基础）：

| 类型 | 判断 | 动作 |
|------|------|------|
| 技能缺陷 | skill写得不对 → 修改skill | 补丁式修订 |
| 执行失误 | skill是对的但执行者做错了 → 不改skill | 记附录，不改skill |
| 新发现 | 执行中发现的skill未覆盖场景 → 扩充skill | 新增条目 |
| 优化机会 | 核心逻辑对但可以更好 → 微调skill | 参数微调 |

**关键**：区分"技能缺陷"和"执行失误"至关重要。说明书是对的但人做错了，改了说明书下次更糟。

## 互优化循环

```
Round 1: skill-evolver被darwin9维审计 → 61分
         失败模式编码缺失 → 补8个if-then → 81分

Round 2: Pitfalls+反例合并去重 → 85.8分

Round 3: delegate_task参数模板+evolution-log实例文件 → 86.0分

Round 4: darwin被注入四类归因 → 二分法→四类分支决策
         skill-evolver权重修正 → 79.1(更准确)
```

## 注入互优化轮次

### 将darwin注入skill-evolver
```yaml
injections_from_darwin:
  - 9维rubric评分标准
  - 棘轮机制（revert on score下降）
  - Phase 2.5 探索性重写
  - results.tsv 9列版本追踪
```

### 将skill-evolver注入darwin
```yaml
injections_from_skill_evolver:
  - 四类失败归因（Step 1.5）
  - 补丁式修订（Step 5 四类分支决策）
  - results.tsv新增failure_type列
  - 反例黑名单新增归因列
  - 约束规则#9 归因驱动修订
```

## 扩展模式: 外部知识注入（2026-06-06新增）

Darwin-SkillEvolver互优化的逻辑可扩展到**外部知识注入**场景——从文章/论文/开源项目中提取方法论并注入Hermes底层能力。

### 注入流程
```
Step 1: 全文获取 — 读取或采集完整外部内容（文章/论文/文档）
Step 2: 能力审计 — 扫描Hermes已有skills/scripts/规则，标记已存在vs缺失
Step 3: 方法论提取 — 抽取可固化的设定/规则/流程/能力
Step 4: 分层部署 — 
   方法论层 → 创建/更新Skill
   执行层 → 创建执行脚本（scripts/）
   规则层 → 注入SOUL.md永久规则
Step 5: 验证 — 确认所有提取的方法论已激活
```

### 本会话实例（2026-06-05/06）
7篇文章 + 桌面副本SOUL.md的完整注入过程:
- 已存在5篇的方法论已确认（Goal Hive/Sharbel 10ops/Crawl4AI/PPT Director/Darwin）
- 新增5个Skill（garden-web-video-production/garden-web-design-engineer/garden-gpt-image-engineer/hermes-6-essential-skills/ai-short-drama-pipeline）
- 创建3个执行引擎脚本（hermes_video_engine/hermes_short_drama_engine/hermes_video_pipeline_executor）
- SOUL.md: 完整九面人格架构+强制执行宪章+专家工作全流程+软件专家完整规范+文学大师完整规范
- 注入6条永久规则到SOUL.md

### 适用信号（何时激活外部知识注入）
- 用户发送多篇长文章要求"全部迁移部署到底层"
- 发现外部方法论与Hermes已有能力互补
- 用户提供标准/规范/最佳实践类文档要求系统集成

## 与Hermes自进化系统融合

### 1. 集成到自进化集群

每天的 self_evolve 流水线增加互优化步骤：

```yaml
# 在hermes_self_evolve_cluster.py 添加模块8
module_8_mutual_optimization:
  - 扫描当前所有skill
  - 选出评分最低的3个
  - Darwin评估 → SkillEvolver生成改进 → Darwin再次评估
  - 棘轮保护（分数不降）
  - 记录evolution-log
```

### 2. 离策略多样化探索

```python
def diverse_exploration(skill_content: str, n_variants: int = 3) -> list:
    """同一任务生成N条不同策略"""
    variants = []
    strategies = [
        "verify-first",      # 先验证再改写
        "evidence-first",    # 精简证据直接改进
        "errors-first",      # 只修复错误
        "minimal-inline",    # 最小改动内联补丁
    ]
    for i in range(min(n_variants, len(strategies))):
        variant = generate_variant(skill_content, strategies[i])
        variants.append(variant)
    return variants
```

### 3. 独立审计

```python
def independent_audit(skill_content: str, audits: list) -> dict:
    """
    审计官看不到作者的修改理由，只看skill本身
    """
    # 9条审计规则
    rules = [
        "frontmatter完整性",
        "工作流可执行性",
        "失败模式是否编码",
        "有无模棱两可的表述",
        "反例与黑名单",
        "验证checklist",
        ...
    ]
    return {"passed": all(check(r) for r in rules)}
```

## 验证清单

- [ ] Darwin 9维评估能对任意skill打分
- [ ] SkillEvolver能从失败证据生成改进提案
- [ ] 棘轮机制在分数下降时自动回滚
- [ ] 四类失败归因正确区分技能缺陷 vs 执行失误
- [ ] 互优化至少可迭代4轮
- [ ] 每次迭代分数不降
- [ ] 审计官看不到修改理由

## 陷阱

- **评分膨胀**：Darwin倾向于给高分。强制每个维度都有扣分项。
- **补丁式修订 vs 整体重写**：补丁更安全。只改分叉点，不整段重写。
- **收敛检测**：连续N轮Δ<0.02 → 停止。避免边际效益耗尽。
- **负迁移**：改进一个skill的同时可能在另一个skill上变差。用SkillOpt负迁移检测定期扫描。
- **独立审计的真实独立性**：审计官必须用新的AI会话，不能共享上下文。

## 关联skill

- `hermes-skill-evolver` — Hermes现有证据驱动Skill进化
- `hermes-self-evolve-cluster` — 每天03:00自进化
- `production-reliability-engine` — 含降级检测
- `skills-orchestration-engine` — Skills编排
