---
name: memory-evolution-v2
description: Hermes 深度记忆进化引擎 v2 — 6模块并行执行，真实记忆压缩，自动技能沉淀，终身学习
category: autonomous-systems
tags: [memory, evolution, parallel, compression, skill-mining, lifelong-learning]
---

# memory-evolution-v2

由Hermes自进化引擎于 2026-04-30 05:01 自动生成。
最后更新: 2026-05-08 01:30 (手动填充完整文档)

## 源文件

## 触发条件
- 用户提及此功能相关关键词时
- 遇到此领域的标准问题时
- 需要执行该领域的标准操作时

- 主脚本: `/home/administrator/.hermes/scripts/memory_evolution_v2.py` (744行, ~30KB)
- 依赖: `/home/administrator/.hermes/scripts/unified_memory_orchestrator.py`

## 功能概述

6个独立模块并行执行，覆盖从情报到记忆的全链路：

| # | 模块 | 函数 | 功能 |
|---|------|------|------|
| 1 | 记忆增强 | `module_enhance()` | 从intelligence.db提取value_level≥3的高价值情报→rag_index.db |
| 2 | RAG索引 | `module_rag_index()` | 将workspace文件向量化→memory/main.sqlite |
| 3 | 记忆压缩 | `module_compress()` | 真实删除: 30天+低价值rag_index / 60天+chunks / 7天+低热度raw |
| 4 | 技能沉淀 | `module_skill_mining()` | 从高频领域(≥30条)自动生成memory-domain-xxx skill文件 |
| 5 | 终身学习 | `module_lifelong_learning()` | 从MEMORY.md/USER.md沉淀持久记忆→memory_entries |
| 6 | 进化分析 | `module_evolution_analysis()` | 全局DB快照+容量瓶颈建议 |

## CLI 使用方法

```bash
# 默认: 并行运行所有6个模块（推荐）
python3 ~/.hermes/scripts/memory_evolution_v2.py

# 串行模式（调试用）
python3 ~/.hermes/scripts/memory_evolution_v2.py --serial

# 参数说明:
# --parallel : 并行运行 (默认，无需显式指定)
# --serial   : 逐个运行（方便查日志）
```

## 输出文件

- 日志: `~/.hermes/logs/memory_v2_YYYYMMDD.log`
- RAG索引DB: `~/.hermes/auto_run/intelligence_pipeline/rag_memory_index.db`
  - `rag_index`表: 情报索引 (value_level≥3)
  - `memory_entries`表: 持久记忆条目
- 自动生成的skills: `~/.hermes/skills/memory-domain-xxx/SKILL.md`
- 并行临时stub: `~/.hermes/scripts/_mem_sub_*.py` (运行时创建，运行后自动删除)

## 与StructMem分层记忆集成

### 融合架构

```
RAG Memory(向量+关键词) ←→ StructMem Events(事件级绑定)
         ↕                          ↕
  memory-evolution-v2(压缩老化) ←→ structmem_knowledge(跨事件整合)
         ↕                          ↕
    memory_layer{1,2,3,4}.json (统一输出格式)
```

### 查询优先级

当用户提问时，按顺序检索:
1. StructMem knowledge(结构化知识) — 高置信度
2. RAG Memory(语义相似) — 中等置信度
3. FTS5 keyword(关键词匹配) — 低置信度但广覆盖
4. memory_layer{1,2,3,4}.json(4层记忆) — 最新情况

## 并行执行机制

使用 `subprocess.Popen` 为每个模块创建独立子进程，通过临时stub脚本序列化函数调用。
每个模块的 `print()` 输出被重定向到stderr，stdout仅输出JSON结果。

```python
# 6个模块同时启动，共用global timeout 180s
结果：结果格式为JSON，包含status/增强数/删除数/创建skills数等
```

## 记忆压缩策略

| 数据源 | 清理条件 | 时间线 |
|--------|----------|--------|
| rag_index_db.rag_index | indexed_at < 30天前 AND value_level < 3 | 30天 |
| main.sqlite.chunks | updated_at < 60天前 AND (无access_count 或 access_count < 1) | 60天 |
| intelligence.db.raw_intelligence | collected_at < 7天前 AND (hot_score IS NULL OR hot_score < 5) | 7天 |

## 能力进化分析阈值

- 高价值情报>RAG索引数+50 → 建议增大`--limit`
- 今日采集=0 → 建议检查情报管线
- chunks<100 → 建议扩大workspace索引
- memory_entries<10 → 建议更多终身学习

## 常见问题排查

1. **rag_core导入失败**: 确认 `~/.hermes/skills/rag-memory-enhanced/rag_core.py` 存在
2. **intelligence.db不存**: 检查 `/home/administrator/.hermes/intelligence.db`
3. **子进程超时(180s+)**: 单独运行模块看哪个卡住: `python3 -c "from memory_evolution_v2 import module_enhance; module_enhance()"`
4. **并行stub未清理**: 手动删除 `~/.hermes/scripts/_mem_sub_*.py`

## 系统关系

- 兄弟技能: `parallel-memory-orchestrator` (调用unified_memory_orchestrator.py的并行编排器)
- 兄弟技能: `long-task-guardian` (管道健康检查，监控memory_evolution是否正常运行)
- 父流程: `omni-loop-workflow` Step 8 (记忆更新)
- cron: 无独立cron，由omni_loop每30分钟触发的step8和cron记忆引擎每4小时save/每12小时compress覆盖

## 回滚方案
### 快速回滚
如果部署后发现问题：
1. 使用版本控制回退到上一个提交：`git revert HEAD`
2. 确认回滚后系统状态正常
3. 通知相关方变更已撤销

### 数据安全
- 所有修改前确认有备份
- 配置变更记录版本历史
