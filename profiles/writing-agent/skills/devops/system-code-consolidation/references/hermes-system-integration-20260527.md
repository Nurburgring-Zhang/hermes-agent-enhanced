# 2026-05-27 全系统整合实战记录

## 范围

同时清理了4个问题域：重复cron + 上下文系统 + 记忆系统 + 旧脚本清理。

## 清理统计

| 指标 | 前 | 后 | 差 |
|------|:--:|:--:|:--:|
| cron总数 | 76 | 62 | -14 |
| task-monitor | 3个 | 1个 | 对话框不再弹两次 |
| guardian | 6个(新旧各3) | 3个(新版) | 清理旧系统 |
| context-index | 3个 | 1个 | 清理副本 |
| memory cron | 5个 | 3个(统一引擎) | -2 |
| ability-activator | 2个 | 1个 | 清理副本 |
| ai-scoring | 2个 | 1个 | 清理副本 |

## 代码整合

| 旧 | 新 | 行数变化 |
|----|-----|--------|
| surgical_context_slicer.py (339) + context_auto_assoc.py (279) | context_pipeline.py (349) | -269行 |
| lossless_claw_v2.py (543) + structmem_memory.py (362) | unified_memory_core.py (696) | -209行 |
| 3份classify_task + 3份映射表 | 1份 task_type_config.json | 统一数据源 |

## 关键发现

### 1. 复制→粘贴→微调是最常见的重复来源
三个独立脚本各自维护了几乎相同的 `classify_task()` 函数。AI复制粘贴时没有提取共享逻辑。**提取共享配置为独立 JSON 是最高优先级的整合手段。**

### 2. cron job_id 格式是识别新旧系统的最快线索
- 旧版: `3c0084b57096`（12位hex）
- 新版: `567f1c990fc5` 或 `2b8b44314a4c`（12位hex）
- 最新: `268de29bfc94`（UUID无横线）
如果看到同一功能有短hex和UUID两份，删短hex保留UUID。

### 3. deliver=origin vs deliver=local
- `origin` — 输出会推送到 Hermes 会话 → 产生消息通知
- `local` — 输出只在终端 → 安静运行
同功能cron一个deliver=origin一个deliver=local时，删origin保留local。

### 4. 脚本路径差异不一定是不同文件
cron可能写 `script=task_monitor.py` 或 `script=scripts/task_monitor.py`，都指向 `scripts/` 下的同一文件。**不要依据路径字符串判断是否为重复cron。**

### 5. 记忆系统碎片化的典型模式
多套代码写同一个DB（active_memory.db）但表名前缀不同（structmem_*/mp_*/memory_*），无统一schema管理。原因是多轮迭代中不同人/不同时间加了不同方案，但没有清理旧方案。**整合时选择功能最完整的版本作为基础（lossless_claw_v2的记忆宫殿），把其他版本的独特功能（structmem的双视角提取）作为模块植入。**
