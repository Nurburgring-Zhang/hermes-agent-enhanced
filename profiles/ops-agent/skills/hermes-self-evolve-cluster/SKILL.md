---
name: hermes-self-evolve-cluster
description: Hermes 自进化集群 — 每天凌晨3点全自动执行技能进化/记忆压缩/对话压缩/能力进化/三省六部进化
tags: [self-evolve, memory-compress, skill-evolution, auto-optimization]
---

# Hermes 自进化集群

## 触发条件
- Cron: 每天 03:00 自动触发
- 手动: `python3 ~/.hermes/scripts/hermes_self_evolve_cluster.py`

## 2026-05-07 进化实战修复
- **根因**: 采集量爆发(~13K/天)但清洗管道backlog_limit=5000太小，且97.9%未清洗项是重复标题
- **修复**: ① backlog_limit 5000→50000 ② 预去重过滤跳过重复标题 ③ 创建purge_dup_raw.py清洗后清理raw_intelligence ④ guardian.py集成purge脚本
  
## 8个模块 (增强版 v3.0 — 集成6篇AI前沿文章方法论)

| 模块 | 功能 | 来源 | 关键操作 |
|------|------|------|---------|
| skill_evolution | 技能自动进化 | 原有 | 扫描所有skill,检测重复/废弃/空模板,挖掘新模式 |
| memory_compress | 记忆压缩提取 | 原有 | 清理>60天记忆,合并重复keyword,移除低权重关键词(<0.3),清理>90天feedback |
| token_compress | 对话Tokens压缩 | 原有 | 删除空会话,FTS5索引重建,清理>30天旧事件日志 |
| capability_evolve | 能力自主进化 | 原有 | Cron失败任务自动暂停,采集趋势告警,关键词权重微调(+2%) |
| sango_evolve | 三省六部自进化 | 原有 | 更新6部门拓扑,记录进化事件到state.db |
| **mutual_optimize** | **Darwin+SkillEvolver互优化** | **清华SkillEvolver论文+Garden-Skills** | 选最低分3个skill → Darwin9维评估 → SkillEvolver生成改进 → 棘轮保护 → 独立审计 |
| **goal_hive_audit** | **Goal Hive蜂群模式审计** | **Generic Agent Goal Hive论文** | 检查是否有可拆解的任务未拆分 → 检查Budget驱动是否生效 → 检查BBS完整性 |
| **cognitive_distill** | **认知蒸馏+受众建模** | **女娲Skill+PPT Director方法论** | 评估当前任务是否需要受众/评审模型蒸馏 → 触发蒸馏管道 → 结果固化到memory |

## Cron 注册
已注册为每日03:00执行，任务ID: `hermes-self-evolve-cluster`
执行后自动读取报告并推送摘要到微信。

## 报告路径
`~/.hermes/reports/self_evolve_{YYYYMMDD}.json`
`~/.hermes/logs/self_evolve_{YYYYMMDD}.log`

## 引用文件
- `references/cron-failure-pattern-analysis.md` — 假阳性cron失败诊断（脚本名截断bug）
- `references/duplicate-skill-tracker.md` — 重复skill检测历史跟踪（建议合并列表）
- `references/report-signal-interpretation-v2.md` — 自进化报告信号分类详解v2（2026-06-02新增：state.db残留cron/稳态参数/零数据源诊断/L2L3假阳性）
- `references/cron-failure-pattern-analysis-realtime.md` — 实时Cron失败模式跟踪(2026-06-02新增:四轮执行数据/AI评分处理语法错误/采集回升验证/state.db残留确认)

## 调优提示
- 采集量下降50%以上会触发告警
- 失败Cron任务会被自动暂停
- 关键词权重每月微调一次
- 发现重复skill只标记不自动删除

## 报告解读 checklist

运行完成后阅读 `reports/self_evolve_{YYYYMMDD}.json`，关注以下信号：

### 🚩 疑似假阳性：采集量凌晨暴跌
- 凌晨3:00执行时报告 `采集量下降 X→Y` → 大概率是**跨天边界采样偏差**
- 今日采集刚开始时 count 低是正常的（采集15分钟一轮，3am才跑了几轮）
- 真正判断标准：**查看最近4小时采集量 + 逐来源检查今日数据**
- 中午12点后仍<500才是真异常

### 🚩 疑似假阳性：脚本路径被截断
- capability_evolve 扫描 cron 时可能报告 `Script not found: scripts/script` 或 `Script not found: scripts/python`
- 这是脚本自身取的 cron job `script` 字段被截断（`scripts/hermes_xxx.py` 被截成 `scripts/script` 或 `scripts/python`）
- **不是真的脚本丢失** — 是扫描逻辑中的名称截断bug
- 应该用 `cronjob action=list` 或查 `state.db` 中的实际 script 路径二次确认

### 🚩 疑似假阳性：state.db残留cron任务
- capability_evolve 可能报告某些cron任务失败并暂停（如G1齿轮执行器、context-pipeline）
- 但 `crontab -l` 中可能已经**不存在这些任务**（手动清理过crontab）
- state.db中的记录是旧注册残留
- **不是真的失败** — 是state.db ↔ 实际crontab不一致
- 诊断: 用 `crontab -l | grep "python3"` 确认实际crontab内容

### ✅ 正常信号
- `skilled_evolution.actions` 有重复检测条目（证明扫描跑了）
- `memory_compress.removed=0, merged=0` 说明条目正常且没有堆积
- `token_compress.deleted_empty` 小数字（0-5个）— 正常清理
- `capability_evolve.cron_fail` 有值 → 需要人工判断后决定降级或恢复

### ⚠️ 需处理的信号
- 同一个 cron 连续 3 天被 `capability_evolve` 标记 `fail` 且暂停 ← 应该检查脚本的真实路径
- `采集量下降` 告警在 12:00+ 仍出现 ← 采集器大概率卡死
- `zero_source` 连续 3 天相同源 ← 采集器注册坏了

## 进化报告解读 (v2.0 更新 2026-06-01)

阅读 `reports/self_evolve_{YYYYMMDD}.json` 时，还需关注以下信号：

### 🤖 技能进化引擎 — 目标Skill匹配失败
- 当 skill_evolution_engine 报告 `applied=false` 且说明为"未识别目标Skill"时：
  - 证据评分 ≥ 60 但无法找到可修改的skill → 这是证据粒度太细的证据（改进点散见于多个技能，无法归一到一个skill）
  - **应对**: 不需要新建skill。这表示改进证据已经潜在于多个技能中，由后续的skill-specific进化循环提取
  - 如果同一提案连续3天未识别到目标skill → 考虑在 `self-evolution-executor` 中新增一个综合改进条目

### 📈 重复检测趋势
- 重复对数量每次运行时略有波动（上次9对，本次13对）
- 这是因为每次扫描的tag匹配计算复用embedding缓存，新入技能或tag调整会改变匹配结果
- **真正的合并信号**: 同一对重复连续出现 ≥3 次 → 建议人工合并
- **暂时忽略**: 只出现1次的匹配 → 可能是tag重叠但内容不同的情况(e.g. `expert-team`类)
- 当前(2026-06-01)已见3次以上的稳定重复: `legal-ethics-experts ↔ expert-legal`, `security-experts ↔ expert-network-security`

### 🕳️ 空来源名异常
- 2026-06-01 首次观察到 `capability_evolve.recommendations` 中包含 `[检查]  无数据`（来源名为空字符串）
- **原因**: `get_source_stats()` SQL查询产生 LEFT JOIN 时，某个采集来源的 name 字段为 NULL
- **影响**: 轻微（告警消息中有空白行）。不影响实际采集
- **应对**: 不需要紧急修复。下一次进化循环中如果有新来源注册，NULL name 会被覆盖

### ⏸️ Cron自动暂停的激进性观察
- 2026-06-01 一次性暂停了 8 个 cron 任务
- 其中至少有 5-6 个是"脚本名截断"假阳性（见 `references/cron-failure-pattern-analysis.md`）
- **问题**: capability_evolve 对每次检测到的失败都执行暂停，但未区分"真失败 vs 截断假阳性 vs state.db残留"
- **建议**: 在暂停前加二次确认。用 verified_failures = [f for f in detected_failures if not is_truncated_false_positive(f) and not is_state_db_stale(f)] 过滤

### ✅ 自动调优参数稳定信号
- 当复盘平均分趋势="stable"且cron成功率为9/17≈53%（已暂停8个忽略不计时为9/9=100%）时
- auto_tune模块维持参数默认值不变（retrospect_threshold=60, wall_interval=3, push_freq=4, skillopt=0.8, checkpoint=10）
- **这不是bug**，这是系统处于稳态的信号
- 只有当 `avg_score` 趋势为 "rising" 或 "falling" 时调优才会自动调整阈值

### ✅ PushPlus推送验证
- 2026-06-01 推送成功: 自进化报告已推送到微信
- 确认内置的 PushPlus 推送链路正常运作（.env 中 PUSHPLUS_TOKEN 可用）
- 推送格式: title="🧬 Hermes 自进化 {月-日} | {total_actions}操作"

## 回滚方案
### 快速回滚
如果部署后发现问题：
1. 使用版本控制回退到上一个提交：`git revert HEAD`
2. 确认回滚后系统状态正常
3. 通知相关方变更已撤销

### 数据安全
- 所有修改前确认有备份
- 配置变更记录版本历史
