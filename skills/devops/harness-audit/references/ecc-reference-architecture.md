# ECC (everything-claude-code) 参考架构

仓库: https://github.com/affaan-m/ECC
Stars: 209K+, Forks: 32K+
许可: MIT

## 规模
- 64 agents (agents/目录)
- 261 skills (skills/目录)
- 84 legacy command shims
- 997+ 内部测试
- 7+ harness兼容: Claude Code, Codex, OpenCode, Cursor, Gemini, Zed, GitHub Copilot

## Harness Audit命令
`/harness-audit` — 对当前环境进行全面harness兼容性评分。检查项目包括：
- Harness版本兼容性
- 已安装的agents/skills完整性
- Token使用效率和配置
- 安全策略覆盖
- 验证循环完整性

## RTK Token Saver机制
ECC通过以下方式优化token消耗：
1. 模型选择优化 — 大任务用强模型，小任务用轻模型
2. 系统提示精简 — 只保留当前任务相关的指令
3. 后台进程管理 — 自动清理无用后台进程
4. 工具结果压缩 — 只保留对推理有用的部分（80%输出是噪音）

## 验证循环设计
ECC采用GAN风格的Generator-Evaluator架构:
- Generator: 主agent执行任务
- Evaluator: 独立agent验证结果（Playwright MCP与真实页面交互）
- checkpoint + continuous evals
- pass@k指标追踪

## 7大架构决策

| # | 抉择 | ECC选择 |
|---|------|---------|
| 1 | 跨Harness兼容 | 优先于任何单个Harness，不绑定任一Harness的UX |
| 2 | 渐进式披露 | Skill内容按需加载，启动只加载元数据 |
| 3 | 验证循环分离 | 生成器和评估器分离，避免self-evaluation bias |
| 4 | Agent通信 | 基于文件传递，避免上下文污染 |
| 5 | Checkpoint会话管理 | context reset优于compaction |
| 6 | 安全层一等公民 | AgentShield, SARIF, CVE追踪 |
| 7 | 算子状态快照 | `ecc status --markdown --write status.md` |

## LangChain TerminalBench实验
(来自article中引用的数据)
- 未改动任何模型权重
- 只优化了Agent Harness架构
- 结果：从30名开外提升到第5名
- 验证了Harness工程的价值远大于模型本身

## 3-Agent GAN架构(Anthropic实验)
- Planner: 从1-4句话扩展为完整产品规格
- Generator: 逐个sprint实现
- Evaluator: Playwright MCP做端到端测试
- 结果：20x成本但质量远超baseline
