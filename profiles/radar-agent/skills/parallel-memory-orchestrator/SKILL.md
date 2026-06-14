---
name: parallel-memory-orchestrator
description: Hermes 并行记忆编配器 — 同时启动5+记忆模块(增强/RAG索引/压缩/技能挖掘/进化分析)的真并行编排器
category: autonomous-systems
tags: [memory, parallel, orchestrator, subprocess]
---

# parallel-memory-orchestrator

由Hermes自进化引擎于 2026-04-30 05:01 自动生成。
最后更新: 2026-05-08 01:30 (手动填充完整文档)

## 源文件

## 触发条件
- 用户提及此功能相关关键词时
- 遇到此领域的标准问题时
- 需要执行该领域的标准操作时

- 主脚本: `/home/administrator/.hermes/scripts/parallel_memory_orchestrator.py` (106行, ~4.5KB)
- 被调用的编排器: `/home/administrator/.hermes/scripts/unified_memory_orchestrator.py`

## 功能概述

使用 `subprocess.Popen` 并行启动5个独立进程，替代串行执行模式。
与 `memory-evolution-v2` 是兄弟关系，调用同一个 `unified_memory_orchestrator.py`。

## 并行能力矩阵

| # | 能力 | CLI参数 | 数据流 |
|---|------|---------|--------|
| 1 | 记忆增强 (enhance) | `--enhance --min-importance 3.5` | intelligence.db → rag_index |
| 2 | RAG索引 (rag_index) | `--index` | workspace → memory/main.sqlite |
| 3 | 记忆压缩 (compress) | `--compress --no-dry-run` | 所有DB |
| 4 | 技能挖掘 (skill_mine) | `--skill-mine` | 模式 → skills/ |
| 5 | 进化分析 (evolve) | `--evolve` | 纯分析 |

## CLI 使用方法

```bash
# 运行并行记忆编配器（启动所有5个模块）
python3 ~/.hermes/scripts/parallel_memory_orchestrator.py

# 退出码: 0=全部成功, 1=有失败模块
```

## 输出示例

```
[PAR] 00:00:00 ⚡ Hermes 并行记忆编配器 ⚡
[PAR] 00:00:00 6个能力模块同时运行 — 不是串行，是真并行
[INFO] 00:00:00   🚀 启动: 记忆增强 (--enhance --min-importance 3.5)
[INFO] 00:00:00   🚀 启动: RAG索引 (--index)
...
[PAR] 00:05:00 ✓ 记忆增强: 完成 (5.0s)
[PAR] 00:05:00 ✓ RAG索引: 完成 (5.0s)
...
[PAR] 00:05:30 📊 并行执行报告
[PAR] 00:05:30 ✓ 记忆增强
[PAR] 00:05:30 ✓ RAG索引
[PAR] 00:05:30 总耗时: 30.0s (所有模块同时运行)
```

## 与 memory-evolution-v2 的关系

| 特性 | parallel-memory-orchestrator | memory-evolution-v2 |
|------|------------------------------|---------------------|
| 底层调用 | unified_memory_orchestrator.py | 自包含6个模块 |
| 输出统计 | 摘要行匹配（最后3行×5模块） | 完整的JSON序列化结果 |
| 并行方式 | Popen直接启动orchestrator | 创建临时stub脚本再Popen |
| 脚本大小 | 106行(轻量) | 744行(全功能) |
| 推荐使用 | 快速检查 | 深度记忆维护 |

## 注意事项
- 各子进程timeout: 180s
- 全部使用 `cwd=~/.hermes`
- 非critical路径 — 如果某个模块失败，其他模块继续

## 依赖
- `/home/administrator/.hermes/scripts/unified_memory_orchestrator.py`
- 所有核心SQLite数据库必须存在

## 回滚方案
### 快速回滚
如果部署后发现问题：
1. 使用版本控制回退到上一个提交：`git revert HEAD`
2. 确认回滚后系统状态正常
3. 通知相关方变更已撤销

### 数据安全
- 所有修改前确认有备份
- 配置变更记录版本历史
