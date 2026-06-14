# 自进化报告信号解读 (v2 2026-06-02)

## 新增于 v2 (2026-06-02)

### 🚩 假阳性: cron任务在state.db中存在但无实际crontab条目 — 已验证

2026-06-02 观察到 **G1齿轮执行器** 和 **context-pipeline** 被capability_evolve标记为失败并暂停，
但实际 `crontab -l` 中已经没有这些条目了。

**根因**: 
- `hermes_self_evolve_cluster.py` 中的 `capability_evolve` 模块读取 `state.db` 的 `cron_jobs` 表
- state.db中的记录是旧cron注册残留（之前有crontab条目时写入的）
- 但实际crontab已经移除这些条目（手动清理或systemd更新）
- 扫描逻辑没有校验"state.db记录 vs 实际crontab是否匹配"

**诊断方法**:
```bash
# Step 1: 检查state.db中有哪些cron任务被标记为paused
cd ~/.hermes && python3 -c "
import sqlite3, os
db = os.path.expanduser('~/.hermes/state.db')
conn = sqlite3.connect(db, timeout=10)
for r in conn.execute('SELECT id, name, status, last_status FROM cron_jobs ORDER BY status'):
    print(f'{r[0][:8]} | {r[1]:50s} | {r[3]:12s} | {r[2]}')
conn.close()
"

# Step 2: 比较实际crontab
crontab -l | grep -i \"python3\" | head -20
```

**应对**:
- 如果state.db中标记为失败/暂停，但crontab中不存在该条目 → **这是残留记录，不需要修复**
- 真正的修复动作：删除state.db中的残留记录，或在扫描时跳过无实际crontab匹配的条目
- 假阳性率估算：当前约 **50%**（8个标记暂停中约4-5个是残留）

### ✅ 新信号: AI评分处理语法错误 (Round 4 新增)
**18:07 发现第9个Cron失败**: `AI评分处理 - 每30分钟: expected an indented block after function definition on line`

**这是真实错误**, 与脚本名截断假阳性不同:
- `expected an indented block` 是Python语法错误 → cron命令中的内联代码缩进被破坏
- 很可能来自 `python3 -c "..."` 包装代码在集成时丢失缩进
- 参考 `references/cron-failure-pattern-analysis-realtime.md` 获取诊断方法

### ✅ 采集回升已验证 — 凌晨偏差确认
2026-06-02四轮数据完美验证了"凌晨跨天边界偏差"理论:
- 03:05(306) → 06:01(233) → 12:01(1159) → 18:07(1726)
- 12:00+采集恢复到昨日水平以上(1726 > 1405)
- **结论**: 凌晨 <500 告警是假阳性。12:00后 <500 才是真异常

### ✅ 正常信号: 新重复对比旧有重复对

2026-06-02 观察到13组重复（上次9组→13组）。
skill总数也从180增加到182。

- 新增的4组重复来自新注册的skill（expert-system系列的交叉匹配）
- 已连续≥3次出现的稳定重复对不变 → 合并建议依然聚焦于legal-ethics-experts/expert-legal和security-experts/expert-network-security

### ✅ 正常信号: 自动调优参数保持不变

当复盘平均分稳定且cron成功率在合理范围时，auto_tune模块会维持参数默认值不变。
这不是bug，这是**稳态信号**。
当前参数:
- retrospect_threshold = 60.0
- quality_wall_check_interval = 3
- cron_push_frequency = 4
- skillopt_threshold = 0.8
- max_task_steps_before_checkpoint = 10

### 🚩 假阳性: L2/L3 scheduler脚本缺失

2026-06-02 capability_evolve报告:
```
hy-memory-l2-scene-scheduler: Script not found: python3
hy-memory-l3-persona-scheduler: Script not found: python3
```

**根因**: 和脚本名截断bug相同。这些cron的script字段值为 `python3 scripts/l2_scene_scheduler.py`，
截断逻辑错误地取 `python3` 作为脚本名 → 报告文件丢失。

**实际情况**: `scripts/l2_scene_scheduler.py` 和 `scripts/l3_persona_scheduler.py` 都存在。

**应对**: 与cron-failure-pattern-analysis.md中的截断bug是同一类假阳性。忽略。

### 🚩 零数据源诊断: toutiao_* 系列

2026-06-02 报告toutiao_finance、toutiao_tech、toutiao_sports为零数据。

**可能的真实原因** (区别于假阳性):
1. 今日头条反爬升级（2026-05以来屡见不鲜）
2. 采集器注册但未绑定有效关键词
3. 采集器本身被临时禁用/超时

**诊断方法**:
```bash
cd ~/.hermes && python3 -c "
import sqlite3
conn = sqlite3.connect('intelligence.db')
# 检查这些源最近是否有数据
rows = conn.execute('''
    SELECT source, COUNT(*) as cnt 
    FROM raw_intelligence 
    WHERE source LIKE \"toutiao%\"
    AND collected_at > datetime('now', '-24 hours')
    GROUP BY source
    ORDER BY cnt DESC
''').fetchall()
for r in rows:
    print(f'{r[0]:30s} → {r[1]}条')
conn.close()
"
```

**应对**: 真零数据 ≠ 假阳性。如果连续3天以上toutiao系列零数据 → 需要检查采集器或切换采集策略。

## 原始信号分类 (从v1继承)

### 采集量跨天边界偏差
- 凌晨3:00执行时报告 `采集量下降` → 今日采集刚开始，count低是正常的
- 真正判断标准：中午12点后仍<500才是真异常

### 脚本路径截断假阳性
- `Script not found: scripts/script` → 截断bug，脚本存不存在取决于`scripts/xxx.py`路径
- `Script not found: scripts/python` → `python3 scripts/xxx.py`被解析为script=`python3`

### 空来源名异常
- 报告 `[检查]  无数据`（来源名为空字符串）→ SQL LEFT JOIN中某个采集来源的name字段为NULL
- 影响轻微，不需要紧急修复
