# Cron 清理方法论 —— 67→10 实战记录 (2026-05-28)

## 背景
Hermes 系统经过数月迭代，accumulated 67个 cron jobs（系统crontab + Hermes内部cron）。其中大量cron是过期/冗余/被替代的。格林主人明确要求精简。

## 清理决策框架

### 保留标准
以下类型的cron必须保留：
1. **采集** — unified_collector_v5.py（每3h/6h）
2. **推送** — v12推送（8/14/20/0点）
3. **AI评分** — intelligence_pipeline评分（每30分）
4. **齿轮系统** — gear_enforcer.py（每1分钟）
5. **自进化** — self_evolve_cluster.py（每天3点）
6. **上下文系统** — context_packer + context_index_system（每1分钟）
7. **数据归档** — archive_old_data（每天4点）

### 删除标准
以下类型的cron应该删除：

| 模式 | 判断规则 | 例子 |
|------|---------|------|
| **prompt生产** | 单次大规模任务，完成就删 | pg2-pg10（每5分钟追加prompt到文件） |
| **旧版轮子** | 被新版替代的采集/守护进程 | ultimate-collector(被v5替代), V3-daemon(被齿轮替代) |
| **Agent驱动循环** | 使用delegate_task的agent循环，实际效果不如直接脚本 | 全能主控Agent、4层记忆Agent、自进化Agent |
| **冗余守护神** | 功能与齿轮G系列重复 | super_guardian(被G5替代), guardian-heal(被G1替代) |
| **孤立任务** | 脚本已移除/不存在 | surgical_context_slicer, context_auto_assoc |
| **特定平台采集** | 已被unified_collector_v5.py覆盖 | 抖音独立采集、小红书独立采集、微信MCP采集 |
| **调试/一次性** | 验证用cron，任务完成后未删 | ai-score-backfill, batch-import-pipeline |

### 危险：清理cron时不要误删
- **自进化集群**很隐蔽（名称可能叫"self-evolution-executor"或"自进化集群"），检查是否被替代后再删
- **齿轮系统**有多层（G0-G8），删除其中一层会导致心跳链断裂
- **上下文索引**每1分钟运行，删了会导致后续会话读不到context_index.json

## 执行步骤（可靠方法）

### 1. 全景观测
```bash
# 列出所有Hermes内部cron
cronjob list
# 列出系统crontab
crontab -l
# 对比两者数量和功能
echo "系统: $(crontab -l | grep -v '^#' | grep -v '^$' | wc -l)个"
echo "内部: $(cronjob list | python3 -c 'import sys,json; print(len(json.load(sys.stdin)[\"jobs\"]))' 2>/dev/null || echo '查不了')"
```

### 2. 按组批量删除
用 `cronjob remove` 按job_id删除。建议按组一次删8-10个。

```python
# 删除模式参考
targets = [
    # prompt生产组
    'pg2', 'pg3', 'pg4', 'pg5', 'pg6', 'pg7', 'pg8', 'pg9', 'pg10',
    # 旧版守护神
    'omni-health-monitor', 'super_guardian', 'production-loop-check',
    # Agent驱动循环（被齿轮替代）
    '全能主控Agent驱动', '4层记忆Agent驱动', '自进化Agent驱动', 'Token压缩Agent驱动',
    # 冗余采集  
    'ultimate-collector', '抖音热点采集', '小红书增强采集',
    # 孤立的V3任务
    'V3全自动守护进程', 'V3-SAR深度分析',
]
for t in targets:
    cronjob(action='remove', name=t)
```

### 3. 验证结果
```bash
cronjob list  # 确认剩余数量合理
crontab -l    # 确认系统crontab没被误改
```

### 4. 检查被移除功能是否受影响
```bash
# 齿轮系统
cat ~/.hermes/reports/wake_guide.json | python3 -c "import sys,json; d=json.load(sys.stdin); print('gear_health:', d.get('gear_health'))"
# 推送
cd ~/.hermes && python3 scripts/hermes_v12_push.py --draft 2>&1 | grep '候选'
# 采集
cd ~/.hermes && python3 scripts/unified_collector_v5.py --stats 2>&1 | tail -5
# AI评分
python3 -c "import sqlite3; conn=sqlite3.connect('intelligence.db'); c=conn.cursor(); c.execute('SELECT COUNT(*) FROM cleaned_intelligence WHERE ai_score_total IS NULL OR ai_score_total=0'); print(f'未评分: {c.fetchone()[0]}'); conn.close()"
```

## 2026-05-28 清理结果

| 指标 | 清理前 | 清理后 |
|------|:-----:|:-----:|
| 总cron数 | 67 | 11 |
| 系统crontab | 2 | 2（未动） |
| 内部cron | 65 | 9 |
| 删除脚本prompt生产pg组 | 9 | 0 |
| 删除旧版守护神 | 8 | 0 |
| 删除Agent驱动循环 | 5 | 0 |
| 删除冗余采集 | 5 | 0 |
| 删除孤立V3任务 | 2 | 0 |
| 删除其他 | ~30 | 0 |

## 坑：需要重新注册的cron
清理后发现以下cron需要重新创建（删错了或需要恢复）：
- G1齿轮: `* * * * *` → 齿轮系统的核心心跳
- 自进化集群: `0 3 * * *` → 24天未运行
- v12推送晚20点: `0 20 * * *` → 误删后重新加回
