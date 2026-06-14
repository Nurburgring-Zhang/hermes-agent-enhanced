---
name: hermes-fast-intelligence-pipeline
description: 快速情报采集管线 (--fast) — 并行采集6个源+清洗评估+存储，不推送
workflow:
  trigger: 快速情报采集任务
  script: ~/.hermes/scripts/hermes_fast_pipeline.py
  sources: B站(全站+科技), 微博热搜, GitHub热门, IT之家, HackerNews
  execution: python3 ~/.hermes/scripts/hermes_fast_pipeline.py [timeout=180s]
  db_path: ~/.hermes/intelligence.db
  notes: |
    - 并行采集5个worker，去重范围2小时
    - 价值评估⭐1~5，关键词匹配+热度打分
    - SQLite datetime('now')=UTC，CST=UTC+8
  pitfalls:
    - 微博热搜可能返回0条（API不稳定，HTTP 403常见）
    - HackerNews API极慢：topstories列表首请求~30s, 每个item~20s, 20个item顺序请求超400s
    - HN采集器已修复：limit降到15条, 增加90s deadline, sleep降到0.05s, as_completed(timeout=150)
    - COUNT查询5万行大表可能超时
---

# Hermes 快速情报管线

`python3 ~/.hermes/scripts/hermes_fast_pipeline.py`

快速采集 → 清洗 → 评估 → 存储，无推送。

## 采集源 (并行6个)

## 触发条件
- 用户提及情报采集、推送、评分时
- 需要配置或调试采集管道时
- 检查情报系统运行状态时

- B站全站 + 科技 (各~100条)
- 微博热搜 (~50条, 可能为空)
- GitHub热门 (Python/TS/JS各10)
- IT之家 (~40条)
- HackerNews Top20 (~20条)

## 价值等级
| 等级 | 条件 |
|------|------|
| ⭐5 | ≥4关键词 + ≥30分 |
| ⭐4 | ≥3关键词 + ≥20分 |
| ⭐3 | ≥2关键词 + ≥15分 |
| ⭐2 | ≥1关键词 + ≥10分 |
| ⭐1 | 其他常规内容 |

## 注意事项
- DB存储PRAGMA WAL + synchronous=OFF加速
- 去重检查2小时窗口内已存数据
- 每次执行约60秒完成
- 微博热搜API可能不稳定返回0条

## 回滚方案
### 快速回滚
如果部署后发现问题：
1. 使用版本控制回退到上一个提交：`git revert HEAD`
2. 确认回滚后系统状态正常
3. 通知相关方变更已撤销

### 数据安全
- 所有修改前确认有备份
- 配置变更记录版本历史
