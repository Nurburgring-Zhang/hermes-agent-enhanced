# Anthropic Skills 实践引用

来自 https://claude.com/blog/lessons-from-building-claude-code-how-we-use-skills 和 https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills

## 核心引文

### Skill 不是提示词，是文件夹
"Skill 不只是几段提示词，它更接近一个围绕任务组织起来的文件夹。这个文件夹里可以放 SKILL.md，也可以放参考文档、脚本、模板、示例、hooks，甚至放会被后续任务继续读取的数据。"

### 最好的Skill往往都很聚焦
"最好的Skill往往都很聚焦。能清楚落进某一类里的Skill，通常更稳；试图同时覆盖太多目标的Skill，反而更容易把模型带乱。"

### 所有类型里最看重验证类（Verification）
"在所有类型里，Verification 值得让工程师单独花一周打磨。因为模型最容易给人一种"已经做完了"的错觉，而真正容易掉链子的地方，恰恰是最后那一步验证。"

### Gotchas最有信号量
"最有信号量的部分，通常不是通用步骤，而是gotchas。因为Claude本来就会写代码，也会读代码库。那些'默认它也会做'的东西，写进Skill里只会增加上下文，不一定增加价值。"

### 真正值得写的gotchas例子
- subscriptions表是append-only，要找最高version，不能只看最新created_at
- 同一个字段，在API gateway里叫@request_id，到了billing服务里叫trace_id
- staging返回200，也不代表Stripe webhook真处理成功了，还得去看payment_events里的真实状态

### Progressive Disclosure设计原则
"启动时只加载技能的元数据（YAML frontmatter中的name和description）到系统提示。实际内容只有Claude判断相关时才会按需读取。"

### Description写给模型看
"description不是摘要，而是触发条件说明。用户可能会说什么关键词，会上传什么文件，什么场景下应该激活这个Skill，都应该直接写进去。"

## 9类Skill官方分类

| 类号 | 名称 | 描述 |
|------|------|------|
| 1 | library/API reference | 库/CLI/SDK的正确用法和gotchas |
| 2 | product verification | 判断产出是否真的工作 |
| 3 | data fetching & analysis | 连接数据仓库和监控系统 |
| 4 | business process & team automation | 团队重复流程压成一条命令 |
| 5 | code scaffolding & templates | 固定骨架+自然语言约束的代码生成 |
| 6 | code quality & review | 代码质量和审查 |
| 7 | CI/CD & deployment | 从开发到上线全链路 |
| 8 | runbooks | 症状→诊断→行动标准流程 |
| 9 | infrastructure operations | 资源清理/治理/成本排查 |

## Skill中常见的记忆模式

Claude Code内部SKILL.md中对记忆模式定义了三种工作方式：

### append-only日志
每次输出记录到standups.log等文件，下次运行时先读历史再判断变化。

### SQLite持久化
用环境变量${CLAUDE_PLUGIN_DATA}获取持久化目录，存SQLite或JSON。

### 预置脚本
给Claude最强的工具之一就是代码本身。预置helper functions让Claude不必从零写样板代码。

## 分发经验

Anthropic在治理上不搞中央审批：
1. 谁有Skill想给大家试，先传到sandbox文件夹
2. 发到Slack让同事试用
3. Skill有了traction，再由owner提PR正式移入marketplace
