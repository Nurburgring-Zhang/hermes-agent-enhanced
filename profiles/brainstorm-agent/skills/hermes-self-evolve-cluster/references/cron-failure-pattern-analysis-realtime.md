# 实时Cron失败模式跟踪 (2026-06-02 新增)

## 今日四轮执行数据

| 执行轮次 | 时间 | Cron总任务 | 正常 | 失败(暂停) | 新增失败 | 采集量(今日) |
|---------|------|-----------|------|-----------|---------|------------|
| Round 1 | 03:05 | 17 | 9 | 8 | - | 306 |
| Round 2 | 06:01 | 17 | 9 | 8 | - | 233 |
| Round 3 | 12:01 | 17 | 9 | 8 | - | 1159 |
| Round 4 | 18:07 | 17 | 8 | 9 | AI评分处理 | 1726 |

## 分析

### 模式1: 脚本名截断假阳性 (已存在, 稳定8个)
这批8个自2026-05-28以来一直在被暂停，实际是扫描逻辑bug。详见`cron-failure-pattern-analysis.md`。

### 模式2: AI评分处理 - 真实语法错误 (NEW in Round 4)
**症状**: `AI评分处理 - 每30分钟: expected an indented block after function definition on line`
**这是真假阳性**: 
- 错误信息是`expected an indented block` — 这是一个**Python语法错误**, 不是脚本路径问题
- `state.db` 中的 `script` 字段指向实际的 `real_ai_scorer.py` 路径, 但又通过 `python3 -c` 包装了额外的代码
- 实际执行的命令是 `python3 -c <inline_code>` 而非 `python3 path/to/script.py`
- 语法错误来自 **cron命令中的内联代码** (不是脚本文件本身)

**根因推测**:
- `cron_jobs` 表中的 `script` 或 `command` 字段存的是 `python3 -c "..."` 内联代码
- 内联代码的缩进被破坏了（多行命令拼接时丢失缩进层级）
- 或者集成发布时的替换操作(如`context_pipeline`)修改了包装代码破坏了缩进

**诊断命令**:
```bash
cd ~/.hermes && python3 -c "
import sqlite3
conn = sqlite3.connect('state.db')
rows = conn.execute(\"SELECT id, name, command, script FROM cron_jobs WHERE name LIKE '%AI评分%'\").fetchall()
for r in rows:
    print(f'ID: {r[0]}')
    print(f'Name: {r[1]}')
    print(f'Command: {r[2][:200]}')
    print(f'Script: {r[3][:200]}')
    print()
conn.close()
"

# 尝试复现错误
python3 -c "$(python3 -c "
import sqlite3
conn = sqlite3.connect('state.db')
cmd = conn.execute(\"SELECT command FROM cron_jobs WHERE name LIKE '%AI评分%'\").fetchone()[0]
conn.close()
print(cmd)
")" 2>&1 | head -20
```

### 模式3: state.db残留 vs 实际crontab不一致
**2026-06-02 验证**:
- G1齿轮执行器在state.db中标记为暂停, 但 `crontab -l` 中已不存在
- context-packer/context-index-system/context-pipeline 同样状态
- 验证了v2报告中预测的"50%假阳性率"

**确认结论**: 以下任务在state.db中暂停但crontab不存在:
1. context-packer-唤醒时打包
2. context-index-system
3. context-pipeline
4. G1齿轮执行器-每1分钟
5. hy-memory-refs-cleanup
6. hy-memory-l1-extract-daily
7. hy-memory-episodic-from-bounda
8. hy-memory-orchestrator-hourly

这8个应在下次进化循环中从state.db清除, 而非继续暂停。

### 模式4: 采集量跨天边界偏差 — 案例验证
自进化集群的采集量判断存在"凌晨采样偏差"：
- 03:05(306) 和 06:01(233) 的数据是因为采集器刚开始跑
- 12:01(1159) 已恢复到正常区间
- 18:07(1726) 超过昨日(1405)
- **结论**: 凌晨告警是假阳性, 12:00+才是真实判断时间窗

## 总结: 真实需处理 vs 假阳性

| 优先级 | 任务 | 状态 | 处理方式 |
|--------|-----|------|---------|
| P0 | AI评分处理-每30分钟 | ❌ 真实语法错误 | 修复内联代码缩进 |
| P1 | state.db残留(8个) | ⏸️ 残留记录 | 删除state.db中记录(非crontab修正) |
| P2 | toutiao_finance/tech/sports | ⚠️ 可能真零数据 | 检查采集器状态 |
| P2 | B站-全站 | ⚠️ 可能真零数据 | 检查采集器状态 |
| 忽略 | 采集量下降告警(凌晨) | ✅ 假阳性 | 查看12:00+数据再判断 |
