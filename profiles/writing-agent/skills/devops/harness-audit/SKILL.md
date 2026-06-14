---
name: harness-audit
description: 生产级Agent Harness性能审计。基于ECC(178K Stars)架构 + Agent Harness十二大模块方法论，全面审计当前Hermes系统的Harness完整性和性能。输出评分和优化建议。
---

# Harness Audit — 生产级Agent Harness性能审计

## 何时使用
- 进行系统性能审查时
- 感觉Agent越来越慢/不稳时
- 想确认当前Harness配置是否生产级时
- 定期（每月）系统健康检查时

## 审计维度（基于Agent Harness十二大模块）

### 模块1: 编排循环（Orchestration Loop）
检查项：
- 循环是否有限制（max_turns）
- 是否有超时保护（gateway_timeout）
- 是否有自动继续机制（gateway_auto_continue_freshness）

### 模块2: 工具（Tools）
检查项：
- 工具数量是否过多（>30个建议精简）
- 高危工具是否有审批保护
- 是否有按Profile隔离工具

### 模块3: 记忆（Memory）
检查项：
- 记忆系统是否启用（memory_enabled）
- 是否有跨会话持久化
- USER.md和MEMORY.md是否更新

### 模块4: 上下文管理（Context Management）
检查项：
- 压缩是否启用（compression.enabled）
- 压缩触发阈值是否合理
- 是否有tool结果自动卸载

### 模块5: 提示词组装（Prompt Assembly）
检查项：
- SOUL.md是否有效
- AGENTS.md/CLAUDE.md是否按目录配置
- Skill数量是否过多（>10个常驻建议精简）

### 模块6: 工具调用与结构化输出
检查项：
- 是否使用原生tool_calls
- Schema约束是否到位

### 模块7: 状态与检查点（State & Checkpointing）
检查项：
- checkpoints是否启用
- session管理策略

### 模块8: 错误处理（Error Handling）
检查项：
- 重试次数配置（api_max_retries）
- fallback链是否配置
- 是否有降级策略

### 模块9: 护栏（Guardrails）
检查项：
- CaMeL安全护栏是否启用
- 敏感工具是否有审批
- tool_loop_guardrails配置

### 模块10: 验证与反馈（Verification & Feedback）
检查项：
- 是否有结果验证机制
- 是否有复盘/反思机制

### 模块11: 子Agent编排（Subagent Orchestration）
检查项：
- delegate_task是否配置
- 子Agent模型是否独立配置

### 模块12: 初始化与环境搭建
检查项：
- 启动配置是否合理
- 环境变量是否完整

## 评分标准
| 分数 | 评级 | 说明 |
|------|------|------|
| 90-100 | S级 | 生产级就绪，可7x24运行 |
| 70-89 | A级 | 良好，有少量优化空间 |
| 50-69 | B级 | 可用但不稳定，需针对性改进 |
| 30-49 | C级 | 玩具级，不可用于生产 |
| 0-29 | D级 | 严重缺失，需要全面重构 |

## 输出格式
```markdown
## Harness Audit 报告

**审计时间**: [日期]
**总体评分**: [分数]/100 ([评级])

### 各维度评分
| 模块 | 评分 | 状态 | 关键问题 |
|------|------|------|---------|
| 1. 编排循环 | /10 | ✅/⚠️/❌ | ... |
| ... | ... | ... | ... |

### Top 3 优化建议
1. [最高优先级]
2. [次优先级]
3. [第三优先级]

### 关键风险
- [风险1]
- [风险2]

### 下一步行动
- [具体行动1]
- [具体行动2]
```
