---
name: self-evolution-agent-cycle
description: "完整的Hermes AI自进化周期：健康检查→退化检测→修复→报告生成。使用delegate_task调度子Agent做真实进化分析。"
category: operations
---

# Hermes AI 自进化周期 (Agent-Driven)

完整的自进化流程，使用 `delegate_task` 调度子Agent进行系统健康检查、退化检测、修复和报告生成。

## 触发条件
- Cron调度：`0 */2 * * *`（每2小时）
- 或手动触发：系统启动/运维巡检/异常告警

## 步骤1: 系统健康检查

使用 `delegate_task` 调度审计Agent，检查以下4个子系统：

1. **Cron任务状态**: 读取 `/home/administrator/.hermes/cron/jobs.json`，列出所有任务及最近运行状态。标记失败/异常任务。
2. **情报采集量检查**: 查询 `intelligence.db` 今日采集记录数。使用 SQLite:
   ```sql
   SELECT COUNT(*) FROM raw_intelligence WHERE DATE(collected_at) = DATE('now','localtime')
   ```
   同时按platform分组看各源贡献：
   ```sql
   SELECT platform, COUNT(*) FROM raw_intelligence WHERE DATE(collected_at) = DATE('now','localtime') GROUP BY platform ORDER BY COUNT(*) DESC
   ```
3. **新组件健康检查 (2026-05-08新增)**:
   - **StructMem记忆**: `cd ~/.hermes && python3 scripts/structmem_memory.py | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'StructMem: {d[\"total_events\"]} events, {d[\"total_knowledge\"]} knowledge, integration_rate={d[\"integration_rate\"]}')"`
   - **Lossless-Claw压缩**: `cd ~/.hermes && python3 scripts/lossless_claw.py status | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'Claw: {d[\"total_compressions\"]} compressions, {d[\"overall_ratio\"]} ratio, saved {d[\"savings_pct\"]}')"`
   - **Cross-Review审核**: 检查 `outputs/cross-review/` 目录是否存在最近审核记录
   - **MasterController**: 检查 `outputs/master_controller/` 目录是否有24小时内的运行记录
4. **QC报告检查**: 查找 `outputs/audits/` 目录下最近的QC报告（最近3个），读取并总结质量趋势。
5. **Pipeline产出检查**: 查找 `outputs/pipeline_v3/` 目录，检查最近的Pipeline产出文件。

6. **AR-029心跳Bug检查 (2026-05-08新增)**: 
   - 检查 `~/.hermes/cron/omni_heartbeat.txt` 是否存在 (应在AR-029修复后被删除)
   - 检查 `~/.hermes/cron/omni_last_run.txt` 是否存在 (同上)
   - 检查 `omni_recover.log` 的行数 (正常应≤6行/天来自真实重启，当前~287行说明AR-029未修复)
   - 检查 `guardian.py` 第278行 `if age_minutes > max_age` 是否仍为错误逻辑
   - 如果以上任意一项为阳性，在健康报告中标记为 **CRITICAL AR-029**

目标：输出系统健康度评分（0-100），明确列出所有问题。

**关键检查点** — 5个常见静默失效源：
- `kuaishou`, `sina_tech`, `zhihu_daily`, `zhihu_topstory`, `ifanr`
- 用SQL检查3天内是否有数据，如果为0则需要告警
- 这些源的采集函数在 `scripts/unified_collector_v5.py` 中定义

## 步骤2: 退化检测

使用 `delegate_task` 调度分析Agent，基于健康检查结果判断：

1. **退化趋势判断**: 检查评分趋势、采集量历史变化
2. **是否需要回滚**: 审查近期变更
3. **异常模式**: 采集量断崖式下跌、DB异常缩容、源静默失效
4. **风险评级**: 低/中/高

**历史基线数据**（用于对比）：
- 健康报告在: `~/.hermes/reports/health_*.json`
- 深度审计: `reports/deep_audit_*.json`
- 自进化报告: `reports/self_evolve_*.json`
- QC评分: `outputs/audits/audit_*.json`

## 步骤3: 进化动作

如果发现退化或异常，执行修复：

1. **修复暂停任务的paused_reason**: 使用 `patch` 工具为 `jobs.json` 中被暂停的任务补充 `paused_reason` 字段
2. **保存自进化工作流为技能**: 使用 `skill_manage`
3. **重启关键Cron**: 如必要，可使用 `process` 命令
4. **优化关键词权重**（如果有关键词配置文件）
5. **诊断采集源失效**: 检查 `unified_collector_v5.py` 中对应源的采集函数，尝试手动调用测试

## 步骤4: 报告生成

汇总本自进化结果，生成JSON报告保存在 `/home/administrator/.hermes/outputs/evolve_agent_driven/`

报告字段：
```json
{
  "timestamp": "YYYY-MM-DDTHH:MM:SS+08:00",
  "health_score": 85,
  "subsystems": { "...": { "status": "healthy|degraded|critical", "score": 0-100, "issues": [] } },
  "degradation": { "overall": "none|mild|severe", "risk_rating": "low|medium|high", "anomalies": [] },
  "actions_taken": [ "..." ],
  "summary": "..."
}
```

## 陷阱与注意事项

1. ⚠️ **采集量基线漂移**: 真实健康基线是 ~700-1000条/天（去重后）。历史峰值 ~7794条/天（4/29）是重复数据导致的虚高。不要用峰值做退化判断。**凌晨低峰期(00:00-06:00)采集量可能在100-200条，不可误判为采集故障**。
2. ⚠️ **Cross-Review组件状态**: 该组件自引入以来从未实际部署 — `/scripts/cross_review*` 不存在，`/outputs/cross-review/` 目录不存在（已在2026-05-08自进化循环中创建占位目录）。健康检查时应标记为critical但不要重复告警。
3. ⚠️ **StructMem集成率0%**: 集成率在早期启动阶段可能为0%（仅1个事件，0个knowledge项），这属于bootstrap正常状态，不是退化。
2. ⚠️ **4个源永久失效**: kuaishou (站点重构), zhihu_topstory (HTTP 401需auth), zhihu_daily (API废弃), ifanr (RSS空数据) — 在v5采集器中永久失效，需要浏览器方案重写。不要重复告警，记录为已知问题即可。
3. ⚠️ **sina_tech可能自愈**: 这个源有时会间歇性工作，不要误告为永久失效。
4. ⚠️ **DB缩容**: intelligence.db 出现 >50% 缩容（如119MB→30MB）通常是有意的purge/archive操作。检查 archive_* 表确认数据有备份。
5. ⚠️ **state.db增长**: gate进程(PID 984781)持有active连接，导致WAL checkpoint无法完全执行。215MB DB + ~200MB WAL是正常状态。仅在 >500MB+500MB 时报警。
6. ⚠️ **delegate_task超时**: 子Agent有300s超时限制。复杂任务（修复+报告并行）容易超时。拆分为更小的任务或直接执行关键修复。
7. ⚠️ **cron/jobs.json位置**: jobs可能在 `jobs` 键下面（`data['jobs']`），也有旧版是直接数组。读取时兼容两者。
8. ⚠️ **intelligence.db路径**: DB可能在项目根目录 `/home/administrator/.hermes/intelligence.db` 而非 `data/intelligence.db`。
9. ⚠️ **进度跟踪**: 使用 `todo` 工具跟踪4个步骤的进度。

## 验证检查清单

- [ ] Cron任务无失败记录
- [ ] 所有采集源在48h内有数据
- [ ] QC评分趋势稳定或上升
- [ ] Pipeline最近一次完整运行
- [ ] 数据库尺寸正常增长
- [ ] 暂停任务有 paused_reason
- [ ] 报告已保存到 outputs/evolve_agent_driven/
- [ ] 本工作流已固化到 skills/

## 回滚方案
### 快速回滚
如果部署后发现问题：
1. 使用版本控制回退到上一个提交：`git revert HEAD`
2. 确认回滚后系统状态正常
3. 通知相关方变更已撤销

### 数据安全
- 所有修改前确认有备份
- 配置变更记录版本历史
