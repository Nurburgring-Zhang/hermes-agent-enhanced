---
name: hermes-upgrade-auto-run
description: WSL2中Hermes升级 + 全能力自动运行系统搭建 - 包含实际schema验证、情报→专家→记忆管道、cron配置
triggers:
  - 升级Hermes
  - WSL2 Hermes
  - 自动运行机制
  - 情报管道
  - Expert路由
  - hermes-auto
version: 1.0
created: 2026-04-22
updated: 2026-04-22
---

# Hermes 升级 + 全能力自动运行系统搭建

## 已知现状（2026-04-22）

## 触发条件
- 用户提及Hermes系统状态、配置、诊断时
- 需要检查或修复Hermes自身功能时
- 执行系统升级、能力激活、模块检查时


### 版本（2026-04-22 更新）
- Hermes v0.10.0 (2026.4.16)，main分支=origin/main at `ff975241`
- 已完成974 commits升级（2026.4.13 → 2026.4.16）
- 升级内容：插件系统重构、新TUI (ink)、图像粘贴、Gateway大幅重构、新增 BedrockTransport 等

### 核心数据库 (intelligence.db)
**路径**: `~/.hermes/intelligence.db`

**cleaned_intelligence 表实际字段**（⚠️ 与skill文档不同）:
| 实际字段名 | 对应含义 |
|-----------|---------|
| `value_level` | 星级(1-5)，**不是** `star_level` |
| `importance_score` | 重要性分数，**不是** `score` |
| `content` | 正文内容 |
| `published_at` | 发布时间 |
| `collected_at` | 采集时间 |

**raw_intelligence 表实际字段**:
- `id`, `title`, `content`, `url`, `source`, `platform`, `author`
- `tags`, `hot_score`, `view_count`, `like_count`, `collect_count`
- `published_at`, `collected_at`, `raw_data`

**其他表**: `trend_tracking`, `source_configs`, `user_preferences`, `push_records`

### 现有Cron Jobs (共9个)
| Schedule | Name | Status |
|----------|------|--------|
| `0 8,12,18,22 * * *` | Hermes全自动情报采集推送 | 新增 |
| `0 9,15,21 * * *` | Hermes情报→专家→记忆管道 | 新增 |
| `0 */4 * * *` | Hermes系统心跳健康检查 | 新增 |
| `every 240m` | 旧版全平台情报采集推送 | 兼容 |
| `*/15 * * * *` | 旧版心跳自检 | 兼容 |
| `0 8,12,18,0 * * *` | 旧版每日定时推送 | 兼容 |

## 新增脚本

### 1. hermes_auto_main.py (33KB)
路径: `~/.hermes/scripts/hermes_auto_main.py`
功能: 全能力自动运行引擎
- 9种人格模式自动检测+切换
- 5大P1行为准则
- 10种自动恢复策略
- 390专家/20领域关键词路由
- 情报分级(⭐1-5)
- 5种运行模式: manual/semi_auto/full_auto/autonomous/overclock
- 调用关系: 采集→清洗→专家路由→记忆索引→推送

### 2. hermes_intelligence_pipeline.py (33KB)
路径: `~/.hermes/scripts/hermes_intelligence_pipeline.py`
功能: 情报→专家→记忆完整数据管道
- Expert路由: `~/.hermes/auto_run/intelligence_pipeline/expert_domains/{domain}/{date}.md`
- RAG索引: `~/.hermes/auto_run/intelligence_pipeline/rag_index.db`
- 咨询队列: `~/.hermes/auto_run/intelligence_pipeline/expert_consult_queue.db`
- 任务生成: `~/.hermes/auto_run/intelligence_pipeline/generated_tasks/{id}.json`
- 20个Expert领域定义（含keywords + priority）

## 踩坑记录

### ❌ schema字段名不匹配
**问题**: skill文档写的是 `star_level` 和 `score`，实际数据库是 `value_level` 和 `importance_score`
**解决**: 必须先 `PRAGMA table_info(cleaned_intelligence)` 验证实际字段，**不要假设文档正确**

**验证方法**:
```python
conn = sqlite3.connect(str(INTELLIGENCE_DB), timeout=30)
conn.row_factory = sqlite3.Row
c = conn.cursor()
c.execute("PRAGMA table_info(cleaned_intelligence)")
for col in c.fetchall(): print(f"  {col[1]} ({col[2]})")
```

## 验证命令

```bash
# 查看情报统计
python3 ~/.hermes/scripts/hermes_intelligence_pipeline.py --mode stats

# 测试管道
python3 ~/.hermes/scripts/hermes_auto_main.py --mode status

# 查看cron jobs
cronjob --action list
```

## 完整数据流
```
终端/Browser采集 → raw_intelligence (17,183条)
    ↓ 清洗
cleaned_intelligence (1,050条, value_level=1-5)
    ↓ 分流
├→ Expert路由 → auto_run/intelligence_pipeline/expert_domains/{domain}/{date}.md
│                → expert_consult_queue.db
├→ RAG记忆索引 → rag_index.db + memory/{date}.md
├→ 任务生成(5星) → generated_tasks/{id}.json
└→ 推送 → PushPlus → 微信

定时:
  08:00/12:00/18:00/22:00 → 全自动采集+推送
  09:00/15:00/21:00        → 专家+记忆管道
  每4小时                  → 系统健康检查
```

## 回滚方案
### 快速回滚
如果部署后发现问题：
1. 使用版本控制回退到上一个提交：`git revert HEAD`
2. 确认回滚后系统状态正常
3. 通知相关方变更已撤销

### 数据安全
- 所有修改前确认有备份
- 配置变更记录版本历史
