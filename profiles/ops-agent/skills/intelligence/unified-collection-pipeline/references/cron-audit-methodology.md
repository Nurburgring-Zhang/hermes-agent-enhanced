# Cron健康雷达扫描 + 清理方法论（实战版）

> 实战来源: 2026-05-28 全系统审计（发现67→10个cron）

## 核心原则

Hermes系统有**两套cron运行机制**，审计时必须同时检查两者：

1. **系统crontab** (`crontab -l`) — 真正的执行者
2. **Hermes内部cron** (`cronjob list`) — cron调度器的管理界面

**关键发现**: 两套cron互相独立！`cronjob create`创建的job会进入Hermes内部调度，但不会出现在`crontab -l`中。反之亦然。审计时两者都要看。

## Cron审计五步法

### Step 1: 列举
```bash
echo "=== 系统crontab ==="
crontab -l

echo "=== Hermes内部cron ==="
cronjob list

echo "=== 两者交叉 ==="
# 检查Hermes cron中是否有关键但不在系统crontab的job
```

### Step 2: 分类

每个cron按以下维度分类：

| 维度 | 判定标准 |
|------|----------|
| **必要性** | 核心（采集/推送/评分/齿轮/上下文）→ 保留；边缘（pg2-pg10/prompt-生产/production-loop-check）→ 可删 |
| **是否在跑** | `cronjob list` 中 `last_run_at` 非空 + `last_status` 非error为"在跑" |
| **功能重复** | 同一脚本出现在不同cron中（如guardian.py有3个cron对应cycle/heal/push） |
| **时效性** | 超过30天未修改/从未运行的 → 可归档 |

### Step 3: 判断保留/删除

**必然保留**（13个核心）:
```
采集（2个）:  每3h常规 + 每6h加重
推送（4个）:  8/14/20/0点
AI评分（1个）: 每30分钟——从每次只处理200条，所以每30分可以持续消化积压
齿轮G1（1个）: 每1分钟——**必须保留，否则系统健康监控丢失**
自进化（1个）: 每天03:00——**断开会严重影响系统进化能力**
上下文（3个）: 每1分钟 ×3（packer/index/pipeline）——支持索引压缩
归档（1个）: 每天04:00——低分数据自动清理
```

**必然可删**:
- `pg2`到`pg10` — prompt批量生产的过期任务（每5分钟写5条到文件，生产完就无用了）
- `guardian-heal/cycle/push` — 如果v12推送和采集cron已独立管理
- `V3-*` — V3进化系统的过期任务（已被自进化集群替代）
- `agent-drive-*` — Agent驱动的旧版循环（已废弃）
- `ultimate-collector` — 被unified_collector_v5替代
- `task-monitor` — 被gear_enforcer替代
- `production-loop-check` — 生产级引擎的独立检查（已被包含在齿轮系统）
- `WebTop` — 浏览器保活（非核心）
- `edge-ai-daily-*` — 特定采集任务（已合并到统一采集器）
- `ai-score-backfill` — 如果AI评分cron已配置
- `ecc-optimize-daemon` — 非核心
- `omni-health-monitor` — 被齿轮系统覆盖
- `lossless-claw-l3-daily` — 非核心
- `experts-anyrun/self-evolution-executor` — 被自进化集群替代
- `db-maintenance-daily` — 如果已包含在自进化集群
- `ClawHub排行榜监控` — 非核心

### Step 4: 清理

```bash
# 对于50+个僵尸cron，逐个删除
cronjob remove --job-id <id>

# 删除后验证
cronjob list
```

### Step 5: 验证

```bash
# 检查关键cron是否正在运行
crontab -l | grep -iE 'collect|push|score|gear|context'

# 验证齿轮系统心跳恢复
cat reports/wake_guide.json | grep gear_heartbeat
```

## 实战中发现的坑点

### 坑1: G1齿轮cron被误删后系统健康监控丢失

wake_guide.json中的 `gear_heartbeat_minutes` 会迅速增长（48分钟→数小时），同时 `G1_HEARTBEAT_ALERT.json` 会产生。但**系统功能不受影响**——gear_enforcer.py本身每1分钟运行一次独立地维持齿轮啮合，不是通过系统cron启动才能工作的。但cron丢失会导致系统对中断任务、AI评分积压等问题的**检测能力下降**。

**修复**: `cronjob create --name "G1齿轮执行器" --schedule "* * * * *" --script scripts/gear_enforcer.py`

### 坑2: 上下文索引cron实际上不依赖Hermes cron——系统crontab的cron_wrapper会另外跑一份

`cron_wrapper.log` 中可以看到 `context_packer: rc=0` 等输出，说明即便 `cronjob list` 中显示 `last_status=error`，实际context_packer仍然在通过系统crontab运行。Hermes内部cron显示的错误可能是历史残留。

**建议**: 对于每分钟跑一次的context job，如果系统crontab已有，可以不通过Hermes cron重复注册。

### 坑3: 删除cron前必须做整体审计，不能边删边想

先完整列出所有cron，按类别分组（采集/推送/评分/齿轮/旧系统/实验性），用分类法一次性判断。不要逐个看title凭感觉删——你会漏掉重复注册或漏删。

### 坑4: cron不持久化

`cron_jobs.db`和`cron/cron.db`的SQLite表是空的（no tables）。Hermes的内部cron可能存储在JSON文件或其他机制中。不能依赖SQLite做cron审计。

## 关键检查清单（每次系统审计用）

```markdown
- [ ] crontab -l 输出是否只有2-3行（采集×2）？
- [ ] cronjob list 中推送cron是否存在且last_status不为error？
- [ ] AI评分cron是否存在？是否每30分钟跑一次且last_status=ok？
- [ ] G1齿轮cron是否存在且每1分钟跑一次？
- [ ] 自进化cron是否存在且每天03:00？
- [ ] 上下文packer/index/pipeline 3个cron是否存在？
- [ ] 数据归档cron是否存在且每天04:00？
- [ ] 是否有pg2-pg10等过期cron残留？
- [ ] cran_old_data是否从未运行过？（last_run_at=null）
```
