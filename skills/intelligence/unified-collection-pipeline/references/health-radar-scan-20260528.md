# 全系统健康雷达扫描 —— 2026-05-28 实战模板

## 场景
格林主人要求"回顾历史，全面复盘，汇报进度，深度思考，全盘规划，全部能力，组合调用，继续执行，进度把控"——需要**10个维度并行扫描**。

## 10项扫描命令

### 1. 系统脚本/文件统计
```bash
cd ~/.hermes && find scripts/ -name '*.py' | wc -l
ls -la *.db | awk '{print $5, $NF}'  # 看哪个db最大
```

### 2. 所有cron检查
```bash
# 两个系统都要查！
crontab -l
python3 -c "import json; [print(j['name'], j['schedule']) for j in json.load(open('.hermes/cron/jobs.json'))['jobs']]" 2>/dev/null
# 关键搜索: grep -iE 'push|score|evol|pipeline|guardian'
```

### 3. 采集系统状态
```bash
cd ~/.hermes && python3 scripts/unified_collector_v5.py --stats
python3 -c "
import sqlite3
conn = sqlite3.connect('intelligence.db')
cur = conn.cursor()
# 今日入库
cur.execute(\"SELECT COUNT(*) FROM raw_intelligence WHERE date(collected_at)=date('now','localtime')\")
print(f'今日raw入库: {cur.fetchone()[0]}')
# 各平台排行
cur.execute('SELECT source, COUNT(*) FROM raw_intelligence GROUP BY source ORDER BY COUNT(*) DESC LIMIT 30')
for s,c in cur.fetchall(): print(f'  {s}: {c}')
conn.close()
"
```

### 4. 推送系统扫描
```bash
# 检查cron存在
crontab -l | grep -iE 'push|v12'
# 测试推送候选
cd ~/.hermes && python3 scripts/hermes_v12_push.py --draft 2>&1 | head -20
# 检查推送历史
python3 -c "
import sqlite3
conn = sqlite3.connect('intelligence.db')
cur = conn.cursor()
cur.execute('SELECT COUNT(*) FROM push_records WHERE date(created_at)=date(\"now\",\"localtime\")')
print(f'今日推送轮次: {cur.fetchone()[0]}')
conn.close()
"
```

### 5. AI评分队列
```bash
python3 -c "
import sqlite3
conn = sqlite3.connect('intelligence.db')
cur = conn.cursor()
cur.execute('SELECT COUNT(*) FROM cleaned_intelligence')
total = cur.fetchone()[0]
cur.execute('SELECT COUNT(*) FROM cleaned_intelligence WHERE ai_score_total IS NULL OR ai_score_total = 0')
unscored = cur.fetchone()[0]
print(f'cleaned总量: {total}, 未评分: {unscored} ({unscored*100//total}%)')
cur.execute('SELECT COUNT(*) FROM ai_score_queue')
queued = cur.fetchone()[0]
print(f'AILOW评分队列: {queued}')
cur.execute('SELECT source, COUNT(*) FROM cleaned_intelligence WHERE ai_score_total IS NULL OR ai_score_total=0 GROUP BY source ORDER BY COUNT(*) DESC LIMIT 5')
print('积压来源:')
for s,c in cur.fetchall(): print(f'  {s}: {c}')
conn.close()
"
```

### 6. 齿轮系统
```bash
cat ~/.hermes/reports/wake_guide.json | python3 -m json.tool 2>&1
cat ~/.hermes/reports/gear_checkpoint.json | python3 -m json.tool 2>&1
```

### 7. 数据库综合
```bash
python3 -c "
import sqlite3
conn = sqlite3.connect('intelligence.db')
cur = conn.cursor()
cur.execute(\"SELECT name FROM sqlite_master WHERE type='table'\")
for t in cur.fetchall():
    tn = t[0]
    try:
        cur.execute(f'SELECT COUNT(*) FROM \"{tn}\"')
        print(f'  {tn}: {cur.fetchone()[0]} 行')
    except: pass
conn.close()
"
```

### 8. 生产级可靠性引擎
```bash
ls -la ~/.hermes/production_loop/ 2>/dev/null && echo '存在'
ls -la ~/.hermes/state/ 2>/dev/null
```

### 9. 自进化集群日志
```bash
ls -lt ~/.hermes/logs/*evol*.log 2>/dev/null | head -3
# 检查最近一次运行是否有异常
tail -5 ~/.hermes/logs/self_evolve_$(date +%Y%m%d).log 2>/dev/null
```

### 10. 上下文压缩系统
```bash
ls -la ~/.hermes/reports/context_*.json 2>/dev/null
ls ~/.hermes/reports/context_sections/ 2>/dev/null
```

## 关键发现检查清单

| 检查项 | 危险信号 | P级别 |
|--------|---------|:-----:|
| 推送cron缺失 | `crontab -l` 没有push相关行 | 🔴 P0 |
| AI评分积压>1000 | cleaned中未评分>1000 | 🔴 P0 |
| 采集cron缺失 | 无 `unified_collector` cron | 🔴 P0 |
| 齿轮心跳>30分钟 | wake_guide中gear_heartbeat_minutes>30 | 🟡 P1 |
| 推送质量差 | draft输出的top候选ai_score<70 | 🟡 P1 |
| 偏好方向缺失 | 某P0/P1方向无数据 | 🟡 P1 |
| cron冗余>10 | crontab -l与cronjob list数量差>10 | 🟢 P2 |
| 零数据平台>5 | --stats显示今日0数据的平台超过5个 | 🟢 P2 |

## 2026-05-28 实战成果

本次扫描发现了2个P0问题：
1. **推送cron完全缺失** — crontab -l | grep push 返回空
2. **AI评分积压21,882条** — 75%数据未评分

修复方案：
- 推送: 创建4个cron(8/14/20/0点)直接跑 `hermes_v12_push.py`
- 评分: 创建每30分钟cron跑 `hermes_intelligence_pipeline.py --mode score`

## 更新记录
- 2026-05-28: 首次创建，记录全系统雷达扫描方法论
