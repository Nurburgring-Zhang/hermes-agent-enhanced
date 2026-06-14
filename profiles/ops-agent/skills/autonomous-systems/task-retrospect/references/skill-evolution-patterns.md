# Skill Evolution Patterns (2026-05-30)

来自4个Hermes生态项目的源码深度分析和AI Agent论文检索，提炼的证据驱动Skill进化的核心模式。

## 核心模式：证据驱动Skill进化闭环

```
证据收集 → 语义分类 → 变体生成 → 评分选优 → 受保护写入 → 验证反馈
```

## 模式1：Plugin Hook无侵入收集

**来源**: hermes-curator-evolver

Hermes Plugin系统提供三个关键Hook点：
- `on_post_tool_call` — 工具执行完毕后捕获结果和错误
- `on_post_llm_call` — LLM调用完成后捕获响应
- `on_session_end` — 会话结束时做总结

所有Hook必须用try/except包裹，永不中断主Session。

```
异常处理原则：吞掉所有异常。若Hook引发异常，记录错误日志但不影响主流程。
```

## 模式2：规则引擎语义分类

**来源**: hermes-curator-evolver

证据不需要LLM来分析，规则引擎足够高效：

| 分类 | 判定条件 | 动作 |
|------|---------|------|
| memory | 用户纠正历史技能 | 记忆更新候选 |
| skill_update | 工作流步骤重复/改进 | skill修改候选 |
| skill_new | 发现新工作流模式 | 新skill创建候选 |
| replay_benchmark | Session可用作验证 | 验证集候选 |
| ignore | 普通对话、无模式价值 | 跳过 |

中英文Workflow识别：正表达式匹配"流程/步骤/SOP/workflow/step/procedure"。

## 模式3：确定性变体生成

**来源**: hermes-curator-evolver

每次改进生成4种确定性变体，不是随机：

1. **verify-first**: 先验证当前方案完整性，再决定是否改写。适合稳定但细节不足的skill
2. **evidence-first**: 基于新证据完整重写。适合过时的skill
3. **errors-first**: 只修复已知错误点。适合大多数patch场景
4. **spillover-minimal-inline**: 最小改动+内联补丁。适合小修小补

通过评分函数自动选择最优变体（规则评分，非LLM）。

## 模式4：受保护自动写入（9层门禁）

**来源**: hermes-curator-evolver

```
1. SHA256签名校验（确保文件未被篡改）
2. 备份原文件
3. 内置结构检查（YAML frontmatter完整性）
4. 分阶段校验（廉价→昂贵链）
5. 自动回滚（验证失败恢复备份）
6. 来源溯源门禁（只允许修改local-agent-created skill）
7. Pin检测（被保护的skill不可改）
8. 容量软硬限制（单文件大小/单skill引用数上限）
9. 恢复演练（回滚manifest回放验证）
```

## 模式5：Session评判（4维度）

**来源**: SkillClaw

评价一个Session的Skill进化价值：

| 维度 | 权重 | 评分标准 |
|------|------|---------|
| completeness | 25% | Session是否完整覆盖了一个任务场景 |
| difficulty | 25% | 任务复杂度（步骤数/工具使用多样性） |
| efficiency | 25% | 重复实验/纠错次数（越低越好） |
| reusability | 25% | 工作流模式是否可迁移到其他任务 |

总分<60 → 不适合Skill进化
总分60-79 → 候选，需要人工审核
总分80+ → 高价值，自动加入进化管线

## 模式6：集体进化

**来源**: SkillClaw

多用户共享Skill进化：
- Client Proxy拦截Agent ↔ LLM通信
- 共享存储（OSS/S3/Nacos）作为Skill注册中心
- Evolve Server从多用户的Session数据中提炼进化
- 验证发布机制：validated模式需要客户端背景验证

## 模式7：负迁移检测

**来源**: SkillOpt论文 (arXiv:2605.23899)

25%的model-generated skill造成负迁移。检测方法：
- 比较Skill修改前后的验证分数
- 分数下降>10%视为负迁移风险
- 触发review_and_fix动作
- 拒绝缓冲区记录被拒编辑

## 与Hermes现有能力的整合点

| 模式 | Hermes已有 | 差距 | 优先级 |
|------|-----------|------|--------|
| 证据收集 | on_post_tool_call Hook可用 | 未用于Skill进化 | P1 |
| 语义分类 | 无 | 需要candidates.py移植 | P1 |
| 变体生成 | 无 | 需要auto_evolve.py移植 | P2 |
| 受保护写入 | SkillOpt验证门(仅结构检查) | 缺SHA备份+回滚+溯源 | P1 |
| Session评判 | 复盘引擎(5维度) | 已实现，可对齐SkillClaw4维度 | ✅完成 |
| 集体进化 | Single-user | 无多用户需求 | P3 |
| 负迁移检测 | skillopt_trainer.py | 已实现每日扫描 | ✅完成 |
