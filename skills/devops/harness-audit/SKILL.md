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

## 已知故障模式（从实战审计中提取）
见 `references/common-failure-patterns.md`。包括：
- `.venv` vs `venv` 路径typo导致systemd无限重启
- PYTHONPATH缺失导致`ImportError: __version__`
- 脚本存在但crontab没有更新
- 多个systemd服务冲突
- 管线产生fake delivery（DB标记delivered但产出骨架）
- @dataclass接口漂移导致TypeError
- 穿透式3层验证方法 + **Layer 4: Data-Truth验证**（直接读DB查真实产出）
- **跨项目迁移完整性检查**: 逻辑重写完成但物理文件未迁移 → 项目无法独立运行
- **跨平台路径硬编码**: unix绝对路径被硬编码到Python代码 → 项目无法移植到其他PC
- **启动依赖缺失**: 无requirements.txt/启动脚本 → 新环境无法一键启动
- **前端静态展示冒充交付**: 后端API全部真实但前端HTML_TEMPLATE是纯静态无交互
  见 `references/static-frontend-audit-failure.md`

### 前端审计检查（每次交付前必做）
```bash
grep -c 'addEventListener' api/canvas_web.py && echo "❌ 无事件绑定"  # 必须有
grep -c 'ondrag\|draggable\|mousedown.*mousemove' api/canvas_web.py  # 可拖拽
grep -c 'connections.*svg\|connections.*push' api/canvas_web.py  # 有连线系统
grep -c 'fetch(' api/canvas_web.py  # 调后端API
grep -c 'execNode\|execute' api/canvas_web.py  # 可执行生产
grep -c 'saveWF\|loadWF\|JSON.stringify' api/canvas_web.py  # 工作流持久化
grep -c 'FileReader\|input type=\"file\"' api/canvas_web.py  # 文件上传
```
任意一项缺失 = 阻断交付 = 不可标记"完成"。

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
