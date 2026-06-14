---
name: lossless-claw-compression
description: "Lossless-Claw 无损上下文压缩引擎 — 三级压缩策略，上下文使用量降低60-70%"
version: 1.0.0
tags: ["compression", "context-optimization", "token-saving", "memory-compression"]
trigger: Level1每5轮对话自动触发；Level2每30分钟；Level3每日03:00；AUTO-LOAD on every session start to ensure compression is active; IMMEDIATE TRIGGER when user mentions token saving or context compression
---

# Lossless-Claw 统一记忆核心 v3.0

**2026-05-27 架构合并：** lossless_claw.py(v1) + lossless_claw_v2.py(v2) + structmem_memory.py → **`scripts/unified_memory_core.py`**

统一引擎包含三个子系统：
1. **CompressionEngine** (原v1) — zlib/gzip三级压缩+检查点+delta+VACUUM归档
2. **MemPalace** (原v2) — 四层记忆堆栈(翼楼/房间/衣柜/抽屉)+时序知识图谱+FTS5搜索
3. **DualExtractor** (原structmem) — 双视角提取(事实+关系)+跨事件整合

## 三级压缩策略

## 触发条件
- 用户提及Agent编排、系统集成、管道时
- 需要配置或调试多Agent系统时
- 执行系统自我进化或健康检查时


### Level 1 (即时/高频压缩)
- 触发：每5次对话轮次
- 目标：压缩当前会话90%上下文
- 方法：差分压缩（仅存储变化部分）
- 延迟要求：<50ms

### Level 2 (周期/统计压缩)
- 触发：每30分钟 / 每6小时
- 方法：基于频率和重要性的选择性压缩
- 保留高频引用段完整，压缩低频段
- 延迟要求：<200ms

### Level 3 (深度/归档压缩)
- 触发：每日03:00
- 方法：完整归档+老化清理
- 超过7天的低价值段自动归档
- 保留关键段（用户偏好、项目配置等）

## 无损保证机制

1. 每个压缩操作创建校验和（SHA256 of original）
2. 保留原始数据的FTS5索引
3. 关键数据永不压缩（白名单机制）
4. 差分压缩保留基线和diff

## AUTO-LOAD Mandate (Updated 2026-05-27)

**格林主人 command:** These skills were installed but never auto-loaded, wasting tokens every call.

**FIX:** Whenever `delegate_task` is called or a new session starts, this skill MUST be loaded via:
```python
skill_view(name='lossless-claw-compression')
```
to activate the compression pipeline.

### 整合后cron jobs（2026-05-27 合并为 unified_memory_core.py）：
| cron名 | 脚本 | 频率 |
|--------|------|------|
| `unified-memory-wakeup` | `scripts/unified_memory_core.py wakeup` | 每2小时 |
| `unified-memory-compress` | `scripts/unified_memory_core.py compress 1` | 每4小时 |
| `unified-memory-archive` | `scripts/unified_memory_core.py archive 7` | 每日03:00 |

旧脚本已整合备份到 /mnt/d/Hermes/备份/memory_old_scripts_20260527/

**核心文件：** `/home/administrator/.hermes/scripts/unified_memory_core.py`
- 三级压缩引擎（zlib/gzip检查点+delta）— 整合自 lossless_claw.py
- 记忆宫殿架构（四层堆栈+知识图谱+FTS5搜索）— 整合自 lossless_claw_v2.py
- 双视角提取+跨事件整合 — 整合自 structmem_memory.py

## 集成方式
- 自动集成到agent-driven-master-loop的步骤8-9
- 与structmem记忆框架共享压缩元数据
- cron调度已在系统中注册

## 回滚方案
### 快速回滚
如果部署后发现问题：
1. 使用版本控制回退到上一个提交：`git revert HEAD`
2. 确认回滚后系统状态正常
3. 通知相关方变更已撤销

### 数据安全
- 所有修改前确认有备份
- 配置变更记录版本历史
