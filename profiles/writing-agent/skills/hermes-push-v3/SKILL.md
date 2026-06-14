---
name: hermes-push-v3
title: "Hermes 推送系统 v12（当前活跃版）"
description: "Hermes 微信推送系统 — 从候选获取、AI评分排序、HTML构建到PushPlus推送的全链路"
version: "12.0"
author: "Hermes"
trigger: "cron: 0 8,12,18,0 * * *"
related_skills: [intelligence, hermes-intelligence-collection-v3]
---

# Hermes v12 推送系统

## 架构

## 触发条件
- 用户提及此功能相关关键词时
- 遇到此领域的标准问题时
- 需要执行该领域的标准操作时

```
采集（unified_collector_v5.py → raw_intelligence）
  → 清洗（hermes_deep_clean_v2.py → cleaned_intelligence）
    → AI评分（ai_score_backfill.py → ai_score_total字段）
      → 候选获取（hermes_v12_push.py get_candidates_balanced）
        → 偏好评分排序（score_quality）
          → 垃圾过滤（is_trash）
            → 已推送排除 + 去重
              → 中文优先（80/20）
                → 平台多样性强制
                  → HTML消息构建（build_html_message）
                    → PushPlus推送（push_wechat）
```

## 核心文件

### 推送主脚本
| 文件 | 用途 |
|------|------|
| `scripts/hermes_v12_push.py` | v12推送主脚本（当前活跃，~898行） |
| `scripts/guardian.py` | cron入口，`guardian.py push` 调用v12推送 |

### 候选获取（get_candidates_balanced）
3阶段递进策略 + **已推送排除**（2026-05-31 新增）：
1. **Step 1**: P0/P1方向标签 + 高价值(ai_score>=15 OR importance>=15) + **id NOT IN push_records(72h)**
2. **Step 2**: 放宽到有标签+低分(ai_score>=10) + **id NOT IN push_records(72h)**
3. **Step 3**: 补充General高质数据(ai_score>=15) + **id NOT IN push_records(72h)**
- 时间窗口: 72小时
- 上限: 300条
- **三保险去重**: SQL排除 + 写入72h窗口 + Step 5标题/id双重检查

### 排序（score_quality）
- AI评分 ×0.4 + tags方向分 ×0.25 + 关键词匹配 ×0.25 + 偏好分 ×0.1
- P0标签: +20分 ×2.5倍率
- P1标签: +12分 ×1.5倍率
- 无AI评分数据的方向分只给30%权重

### 推送条件
- 目标: 25条/次（PushPlus限制2万字，从50条降级）
- 最少5条才推送
- 中文优先: 80%中文 + 20%英文
- 每平台上限: target_count × 0.3

## 等级评定（推送后记录）
| 等级 | 条件 |
|:----:|------|
| 9 | ai_score >= 80 |
| 8 | ai_score >= 65 或 effective_score >= 75 |
| 7 | ai_score >= 50 或 effective_score >= 50 |
| 6 | effective_score >= 30 |
| 5 | effective_score >= 15 |
| 3 | 以上都不满足 |

## AI评分

### 主评分脚本
| 文件 | 用途 |
|------|------|
| `scripts/ai_score_backfill.py` | cron回填（每4小时 `--high-value` mode，评6条） |
| 评分API | DeepSeek Chat（`model: "deepseek-chat"`） |
| 六维 | scarcity(0-30) + impact(0-30) + tech_depth(0-20) + timeliness(0-10) + preference(0-10) + credibility(0-10) |

### 评分状态（2026-05-28）
- cleaned_intelligence总条数: **28,896**
- 已评分: **24,190**（83.7%）
- **待评分积压: 4,706条+21,882条队列中** ❗（微博/百度/知乎为主要积压来源）
- 独立评分cron: `*/30 * * * * cd ~/.hermes && python3 scripts/hermes_intelligence_pipeline.py --mode score`（2026-05-28新增，每30分钟处理一批）
- 旧backfill cron: `0 */4 * * * cd ~/.hermes/scripts && python3 ai_score_backfill.py --high-value`（可能已失效或太低效）

## 推送cron

### 当前配置（2026-05-28修复 — 🔴之前完全缺失！）

```cron
# v12推送 - 每8/14/20/0点 (2026-05-28新增)
0 8 * * * cd ~/.hermes && python3 scripts/hermes_v12_push.py
0 14 * * * cd ~/.hermes && python3 scripts/hermes_v12_push.py
0 20 * * * cd ~/.hermes && python3 scripts/hermes_v12_push.py
0 0 * * * cd ~/.hermes && python3 scripts/hermes_v12_push.py
```

### ⚠️ 历史陷阱: 推送cron曾完全缺失（2026-05-28修复） 
- **发现经过**: 在2026-05-28的全系统审计中，`crontab -l`只显示2个采集cron，0个推送cron。推送依赖 `guardian.py push` 但你不会推推推。`hermes_v12_push.py` 本身没有cron注册 —— 它所生成的17轮"推送记录"实际上是自进化报告推送和手动测试，不是真正的情报推送。
- **根因**: 共4个cron系统（crontab直写/cronjob工具/guardian.py/内部调度器）混用，推送cron在迁移v11→v12时丢失，始终没有补回来。
- **教训**: 每次迁移系统后，手动验证 `crontab -l | grep -i push` 和 `cronjob list | grep -i push` 同时检查。不能相信"迁移完成" → 必须用命令验证cron存在。这是P0级别的漏洞。

### 旧配置（已废弃）
```cron
# guardian.py 模式 — 已废弃（v12直接跑）
0 8,12,18,0 * * * cd ~/.hermes && python3 scripts/guardian.py push >> logs/cron_push.log 2>&1
```

## PushPlus

### 配置
- Token来源: `~/.hermes/.env` 或 `~/.hermes/config.yaml`
- 端点: `https://www.pushplus.plus/send`
- 模板: `html`
- Token长度: 32字符 (a8f152...ab7f)
- 内容限制: **不超过2万字**

## 陷阱/Pitfalls

### 🔴 推送SQL标签筛选不完整（2026-05-28发现并修复）

- **症状**: 即使 cleaned_intelligence.tags 正确包含了 `Photo`、`Camera`、`Fight`、`MMA`、`Chip`、`Semi`、`Travel` 等标签，推送SQL的WHERE条件只匹配 `Sports_Fight` 和 `Beauty_Photo`（extract_tags()风格的标签名），不匹配 `Photo`/`Camera`/`Fight`/`Chip`（category_tags风格的标签名）。这些数据被排除在候选池之外。
- **原因链**: 标签系统存在两套命名格式。采集器写category_tags（`Photo|Camera|Match`），extract_tags()写cleaned.tags（`Beauty_Photo|Sports_Fight`）。虽然2026-05-28修复了cleaning管道合并二者，但推送SQL只写了 `Sports_Fight`/`Beauty_Photo` 类的名，没覆盖 `Photo`/`Camera`/`Fight`/`Chip` 等值。
- **修复**: `get_candidates_balanced()` 的WHERE条件中新增 `tags LIKE '%Photo%'`、`tags LIKE '%Camera%'`、`tags LIKE '%Fight%'`、`tags LIKE '%MMA%'`、`tags LIKE '%Chip%'`、`tags LIKE '%Semi%'`、`tags LIKE '%Fengniao%'`、`tags LIKE '%Travel%'`（后者已存在，但单独列出避免歧义）
- **教训**: 任何依赖标签的模块都要考虑两套命名格式的兼容性。推送SQL写 `LIKE '%Fight%'` 比 `LIKE '%Sports_Fight%'` 更稳妥。
- **症状**: 推送记录显示"今日已推17轮"但实际只有2轮是真的，其余15轮是空记录
- **原因链**: v11→v12迁移后，推送cron从未重新配置。`crontab -l`只看得到采集cron。`hermes_v12_push.py`每天在跑的唯一推送是自进化报告（`self_evolve_cluster.py`自带推送能力）
- **检测方法**: `crontab -l | grep -iE 'push|v12'` — 如果返回空，推送cron不存在
- **修复**: 用 `cronjob create` 添加4个定时cron（8/14/20/0点），或在crontab直接写入
- **教训**: 永远不要假设cron迁移成功了。每次系统迁移后，**必须显式验证** `crontab -l` 的输出。

### 🔴 AI评分中断（2026-05-26 ~ 2026-05-27）
- **症状**: 推送候选池为空，推送日志报"服务端验证错误"
- **原因链**: `ai_score_backfill.py` 用 `model: "deepseek/deepseek-chat"`（OpenRouter斜杠格式）调DeepSeek API → 400 → 所有新数据ai_score_total=0 → 推送SQL `ai_score_total>=15` 过滤所有数据 → 候选池空
- **修复**: model名改为 `"deepseek-chat"` + 推送SQL加 `importance_score>=50 OR personal_match_score>=10` 降级条件
- **教训**: 推送条件不要完全依赖AI评分，做三层降级（有评分→重要性分→直接放行新数据）

### 🔴 PushPlus内容超限
- **症状**: `'code': 999, 'msg': '服务端验证错误', 'data': '发送内容过大，不能超过2万字'`
- **原因**: TARGET_COUNT=50时HTML超过2万字
- **修复**: TARGET_COUNT降到25 + `push_wechat()` 加降级截断逻辑
- **教训**: 任何第三方API都要做长度/大小检查 + 降级策略

### 🔴 URL中&符号未转义
- **症状**: 推送偶尔失败，PushPlus报验证错误
- **原因**: 文章URL包含 `&` 参数（如 `utm_medium=xxx&biz_id=yyy`），嵌入HTML的`href`属性时未转义
- **修复**: `safe_url = url.replace('&', '&amp;')`

### 🔴 推送记录重复（三保险修复，2026-05-31）
- **症状**: push_records表同一条cleaned_id被推送3次（间隔约24h）
- **根因（3层）**: 
  1. 候选池SQL不排除已推送cleaned_id → 同条数据每次进候选
  2. record_pushed()用标题+24h窗口 → 第2天放行
  3. Step 5只有标题去重 → 很多匹配不上
- **修复**: 
  - 候选池SQL加 `AND id NOT IN (SELECT cleaned_id FROM push_records WHERE 72h)`
  - record_pushed()改按cleaned_id检查72h
  - Step 5加cleaned_id双重检查
- **教训**: 标题去重不可靠，永远用cleaned_id做主键。窗口必须 > 2×间隔

### 🟡 推送等级无区分度
- **问题**: 旧版等级评定只有3/5/7/9四个档，所有数据都拿9
- **原因**: `effective_score = max(score, ai_score)` 中score(偏好分)偏高
- **修复**: 以ai_score为主，分6级（3/5/6/7/8/9），阈值更细化

### 🟡 guardian.py push 日志不完整
- **问题**: `do_push()` 通过子进程调用v12脚本，只显示最后15行stdout，看不到是否成功
- **改进建议**: 检查stdout中的"推送成功"、"推送失败"关键词并单独记录

## 数据库
- `intelligence.db` — 主库（~285MB）
  - `cleaned_intelligence` 表: 23,188条
  - `raw_intelligence` 表: ~28,000条
  - `push_records` 表: 3,709+条
  - `archive_cleaned` 表: 381,250条
- `data/cleaned_intelligence.db` — 分离的旧库（1.7MB, 1,393条，不活跃）

## 回滚方案
### 快速回滚
如果部署后发现问题：
1. 使用版本控制回退到上一个提交：`git revert HEAD`
2. 确认回滚后系统状态正常
3. 通知相关方变更已撤销

### 数据安全
- 所有修改前确认有备份
- 配置变更记录版本历史
