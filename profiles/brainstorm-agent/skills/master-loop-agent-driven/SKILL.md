---
name: master-loop-agent-driven
description: "Hermes 全自主主控循环工作流 — 9步Agent驱动流水线：采集→评分→市场分析→产品设计→技术架构→项目计划→推送候选→记忆更新→审计"
category: autonomous-systems
tags: [master-loop, agent-driven, pipeline, intelligence, automation]
---

# 全自主主控循环工作流 (Agent-Driven)

完整9步Agent驱动流水线，使用 `delegate_task` 调度子Agent进行全自主情报采集→产品生产→推送发布。

## 触发条件
- Cron调度：`*/30 * * * *`（每30分钟，通过"全能主控-Agent驱动流水线" cron任务）
- 或手动触发：`delegate_task` + 本技能

## 流水线步骤总览

```
采集(20+条) → AI六维评分 → 市场分析+需求挖掘 → 产品设计 → 技术架构 → 项目计划 → 推送候选(30条) → 4层记忆更新 → 质量审计
```

## 步骤1: 全平台信息采集
使用 `delegate_task` 调度采集Agent，从所有配置采集源获取最新情报。

**目标**: ≥20条高价值情报。
**工具**: `web_search` 在agent内部使用，而非直接跑脚本。
**输出**: 保存到 `~/.hermes/outputs/agent_driven/` 下作为 `raw_intelligence.json`

### 采集源优先级
| 优先级 | 源 | 说明 |
|--------|-----|------|
| P0 | Hacker News, TechCrunch, AI专业媒体 | 高价值AI/科技情报 |
| P1 | GitHub, 微信公众号, 知乎 | 开源/中文生态 |
| P2 | 抖音, B站, 36氪, 虎嗅 | 泛科技热点 |

## 步骤2: AI清洗与评分
使用 `delegate_task` 调度评分Agent，对采集情报做AI六维评分。

**评分维度**:
1. **稀缺性 (rarity)** — 信息是否独家/罕见 (0-20分)
2. **影响力 (impact)** — 对行业/用户的潜在影响 (0-20分)
3. **技术深度 (tech_depth)** — 技术含量和创新度 (0-20分)
4. **时效性 (timeliness)** — 信息的新鲜程度 (0-15分)
5. **偏好匹配 (preference_match)** — 与格林主人偏好的匹配度 (0-15分)
6. **可信度 (credibility)** — 来源可靠性 (0-10分)

**目标**: 筛选≥5条高分情报 (>60分)，输出 `scored_intelligence.json` + `high_score_intelligence.json`

### 偏好匹配关键词 (P0-P2)
- **P0**: AI, LLM, 开源, 芯片, 新能源, 军事, 国防, 编程, 安全
- **P1**: UFC, 摄影, 电影, 小米, 华为, 特斯拉
- **P2**: 机器人, 自动驾驶, 量子计算, 生物科技

## 步骤3: 市场分析与需求挖掘 (运营部)
使用 `delegate_task` 调度市场分析Agent（模拟傅浩轩角色），基于高分情报做：
1. 识别市场趋势
2. 提炼产品需求（至少2个）
3. 输出市场分析报告

**输出**: `market_analysis_report.md`

## 步骤4: 产品功能设计 (设计部)
使用 `delegate_task` 调度设计Agent（模拟林若溪角色），输出产品交互与视觉设计方案。

**输出**: `product_design_spec.md`

## 步骤5: 技术架构规划 (技术部)
使用 `delegate_task` 调度技术架构Agent，输出技术架构规范。

**输出**: `tech_architecture_spec.md`

### 降级处理
当技术架构Agent连续失败时，由父进程直接 `write_file` 生成合理内容，保证流程不中断。

## 步骤6: 项目计划 (PMO)
使用 `delegate_task` 调度PMO Agent，输出项目开发计划。

**输出**: `project_plan.md`

## 步骤7: 推送候选生成
使用 `delegate_task` 调度推送Agent，基于评分和市场需求生成30条推送候选。

**目标**: 30条候选
**输出**: `push_candidates.json` (保存到 `~/.hermes/outputs/agent_driven/` 和 `~/.hermes/cron/push_candidates_latest.json`)

## 步骤8: 4层记忆更新
更新Hermes 4层记忆系统：
- **Layer1** — 本次循环摘要（时间、步数、核心发现）
- **Layer2** — 关键事实提取（5-10条高置信度事实）
- **Layer3** — 工作流固化（本工作流的步骤记录）
- **Layer4** — 模式学习（新发现的时序/技术/生态模式）

**输出文件**: `~/.hermes/memory_layer{1,2,3,4}.json`
**聚合文件**: `~/.hermes/memory_layers.json`

## 步骤9: 质量审计
使用 `delegate_task` 调度审计Agent，检查所有产出物的质量和完整性。

**检查清单**:
- [ ] 采集条数 ≥ 20
- [ ] 评分覆盖度 100%
- [ ] 市场报告包含 ≥2 个产品需求
- [ ] 技术架构文档完整
- [ ] 项目计划包含排期
- [ ] 推送候选 ≥ 30 条
- [ ] 4层记忆均已更新

**输出**: 审计报告到 `outputs/agent_driven/`

## 数据流模式
子Agent之间通过JSON文件传递数据 (`delegate_task write_file` 输出 → `read_file` 输入)，避免大文件读取减少超时。

## 错误处理
- 每步失败重试1次
- 重试仍失败则跳过该步骤，继续后续流程
- 关键步骤（技术架构）失败时，父进程直接生成降级内容
- 所有产出物保存在 `~/.hermes/outputs/agent_driven/`

## 验证检查清单
- [ ] Cron作业 `全能主控-Agent驱动流水线` 每30分钟自动触发
- [ ] 所有产出物JSON/MD文件可读
- [ ] 推送候选文件格式正确
- [ ] 记忆层文件格式正确
- [ ] 系统连续运行无中断

## 历史运行记录
- 36次omni完美循环 (截至2026-05-08)
- 125+ master controller完成记录
- 最近完整周期: 2026-05-08T03:30 (全9步完成)

## 回滚方案
### 快速回滚
如果部署后发现问题：
1. 使用版本控制回退到上一个提交：`git revert HEAD`
2. 确认回滚后系统状态正常
3. 通知相关方变更已撤销

### 数据安全
- 所有修改前确认有备份
- 配置变更记录版本历史
