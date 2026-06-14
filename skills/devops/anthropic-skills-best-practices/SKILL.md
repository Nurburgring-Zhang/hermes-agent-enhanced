---
name: anthropic-skills-best-practices
description: 基于Anthropic内部经验的Skills最佳实践。9类技能分类法、gotchas驱动写作、渐进式披露、description优化、memory/scripts/hooks模式。
---

# Anthropic Skills 最佳实践

## 何时使用
- 创建新Skill时，作为模板和质量标准
- 审核已有Skill质量时
- 想理解"好的Skill长什么样"时

## 核心原则

### 1. 9类Skill分类法
Anthropic内部将Skills分为9类，每类有明确的焦点：

| 分类 | 焦点 | 价值 |
|------|------|------|
| API Reference | 解释库/CLI/SDK的正确用法和gotchas | 减少模型幻觉 |
| Verification | 判断产出是否真的工作（测试/截图/断言） | 质量提升最明显 |
| Data Fetching | 连接数据仓库/监控，封装取数方法 | 降低重复工作 |
| Business Process | 压成一条命令的团队流程 | 减少手动操作 |
| Code Scaffolding | 固定骨架+自然语言约束的代码生成 | 替代纯模板引擎 |
| Code Quality | 代码审查/安全审计 | 保持质量标准 |
| CI/CD | 从开发到上线的全链路 | 自动化部署 |
| Runbooks | 症状→诊断→行动的标准流程 | 故障响应 |
| Infrastructure | 资源清理/治理/成本排查 | 运维自动化 |

### 2. Gotchas驱动写作
Skill中最有价值的内容不是通用步骤，而是gotchas（坑点）：
- "subscriptions表是append-only，找最高version不能只看created_at"
- "同一个字段在API gateway叫@request_id，在billing服务叫trace_id"
- "staging返回200不代表Stripe webhook真处理成功"

规则：如果Claude默认就会做的事情，不要写进Skill。只有"会把它从默认路径拽出来"的信息才值得写。

### 3. 渐进式披露（Progressive Disclosure）
SKILL.md只做目录和路标，详细资料按需分发到单独文件：
- SKILL.md — 名称/描述/触发条件/步骤/输出格式
- references/api.md — API签名和用法
- references/template.md — 输出模板
- references/gotchas.md — 坑点列表
- scripts/ — 可执行脚本
- assets/ — 模板/示例文件

启动时只加载name和description到系统提示。只有Claude判断相关时才按需读取完整内容。

### 4. Description优化
description写给模型看，决定Skill会不会被触发：
- 用户可能说什么关键词（触发词直接写进去）
- 用户会上传什么文件
- 什么场景应该激活这个Skill
- 例子：用"babysit"作为触发词，就直接出现在description里

### 5. 记忆/脚本/Hooks三件套

#### 记忆模式
- append-only日志：每次输出记录到.log文件
- 下次运行时先读历史，再判断变化
- 可用环境变量${HERMES_HOME}获取持久化目录

#### 脚本模式
- 预置helper functions，Claude不必从零写样板代码
- helper之上可临时组合更复杂的分析
- 数据分析类Skill应直接带一组helper

#### Hooks模式
- on-demand hooks：只在Skill被调用时生效
- /careful：拦住rm -rf / DROP TABLE等高危操作
- /freeze：阻止对指定目录之外的写操作

## Gotchas: SOUL.md 精简原则

2026-06-09 实践中将 SOUL.md 从 708 行重构为 41 行核心契约。原则:
- 只保留身份/核心规则/沟通风格/自主边界/问责/任务地图 6个大节
- 详细的人格描述/emoji规则/九维清单全部移到外挂文件
- Agent的task地图保持活跃更新(当前优先级清单)
- 反幻觉铁律和前置三查是最高优先级不可违反

**精简效果: token消耗降为原来的1/17, Agent不再被大量冗长规则稀释注意力。**

## Gotchas: Skill合并原则

当有406个skills时,必然存在大量重叠。合并判断标准:
1. **描述同一系统不同侧面** → 合并(如4个记忆skill)
2. **同一管线的4个步骤** → 合并(如进化周期)
3. **被新版本替代的旧版** → 删除(如推送v8被v12替代)
4. **auto-generated重复品** → 删除(自进化引擎生成的旧skill)
5. **不同技术路线同一产出** → **不要合并**(如录屏式视频 vs 原生渲染视频)

合并执行: 先建伞skill,再删旧skill(用absorbed_into参数标记去向)

## Gotchas: description的实战写法

description是skill被触发的唯一入口,必须覆盖用户可能说的关键词:
参照本仓库已有的SKILL.md结构，确保包含：
1. 名称和描述（frontmatter）
2. 何时使用（触发条件）
3. 核心流程（步骤化）
4. 输出格式（结构化）
5. 约束（边界条件）
6. Gotchas（坑点）
