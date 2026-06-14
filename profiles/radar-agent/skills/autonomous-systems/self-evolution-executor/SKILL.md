---
name: self-evolution-executor
title: Self-Evolution Executor
description: Execute concrete fixes for a degraded Hermes system in priority order (P0-P3). Runs repair commands, reclaims DB space, cleans outputs, and verifies system health.
domain: autonomous-systems
priority: high
triggers:
  - "execute evolution actions"
  - "fix system issues"
  - "self-heal"
  - "run degradation repair"
  - "进化修复"
  - "自愈"
---

# Self-Evolution Executor

Execute concrete fixes for a degraded Hermes system in priority order.

## P0: Run V3 Self-Check Engine (优先)

## 触发条件
- 用户提及Agent编排、系统集成、管道时
- 需要配置或调试多Agent系统时
- 执行系统自我进化或健康检查时


30秒内完成全系统15项检查。比手工排查快10倍。

```bash
# 全系统自校验(15项, 含自动修复)
cd ~/.hermes/evolution_v3 && python3 self_check_engine.py

# 查看报告
cat ~/.hermes/reports/self_check_latest.json

# 如果任何项failed, 查看详情:
python3 -c "import json; d=json.load(open('reports/self_check_latest.json')); [print(f'{r[\"subsystem\"]}: {\"FAIL\" if not r[\"ok\"] else \"OK\"} - {r.get(\"detail\",\"\")[:80]}') for r in d['details'] if not r['ok']]"
```

## P0: Verify V3 Daemon Health

如果齿轮系统和V3守护报告degraded:

```bash
# 检查V3守护最近状态
tail -3 ~/.hermes/logs/v3_daemon.log
tail -3 ~/.hermes/logs/gear_enforcer.log
tail -3 ~/.hermes/logs/self_check.log

# 检查V3守护历史
python3 -c "import json; d=json.load(open('reports/v3_daemon_report.json')); print(f'最近: {d[-1][\"ts\"][:19]} status={d[-1][\"status\"]} phases={len(d[-1][\"phases\"])}')"

# 强制重新运行
cd ~/.hermes/evolution_v3 && python3 v3_daemon.py
```

## P0: Restart Stalled Pipelines

1. Check cron: `cat ~/.hermes/cron/jobs.json | python3 -m json.tool`
2. Run omni loop: `cd ~/.hermes && timeout 120 python3 scripts/omni_loop.py`
3. Run guardian cycle: `cd ~/.hermes && timeout 60 python3 scripts/guardian.py cycle`
4. Run company pipeline: `cd ~/.hermes && timeout 120 python3 scripts/agent_company_runner.py`

## P0: Fix Dead Collection Sources

1. Test kuaishou: `cd ~/.hermes && timeout 30 python3 scripts/collector_kuaishou_enhanced.py`
2. Test via curl: `curl -sI --max-time 10 "https://www.kuaishou.com/"`
3. Check today's volume: query raw_intelligence per-source past 24h

## P1: Consume Retrospect Candidate Queue

The retrospect engine (`hermes_retrospect.py`) writes low-scoring task evaluations to `data/retro_candidates.jsonl`. Consume this daily:

```bash
cd ~/.hermes && python3 scripts/hermes_self_evolve_cluster.py
```
(The `consume_retro_candidates()` function in Module 6 reads the queue, aggregates improvement patterns, and clears consumed entries.)

To check the queue manually:
```bash
cd ~/.hermes && python3 scripts/hermes_retrospect.py --check-evolution
```

**Pitfall — skill_evolution_engine.applied=false**: If after this run, `skill_evolution_engine.applied=false`, it means the engine collected evidence but could not identify a target SKILL.md to patch. Common causes:
  1. **Evidence too granular**: The improvement touches multiple skills at once, not one clearly identifiable one. Solution: nothing needs fixing — this is the engine correctly rejecting low-confidence proposals.
  2. **Evidence score below threshold**: Highest proposal score < 60. The engine only applies changes when score ≥ 60. Check `reports/skill_evolution/evolution_{datestamp}.json` for the `top_candidate.score`.
  3. **Trigger skill not found**: The engine outputs `未识别目标Skill`. This is expected when the evidence is about a workflow pattern (errors-first) rather than a single skill.
  **Rule**: Do NOT create a new skill just because the engine couldn't find one. If the same proposal repeats for 3+ consecutive days, consider adding a section to an existing umbrella skill.
```

## P1: Reclaim DB Space

Use Python's sqlite3 (not CLI):
```python
import sqlite3, os
db = '/home/administrator/.hermes/state.db'
conn = sqlite3.connect(db, timeout=60)
cur = conn.cursor()
cur.execute('PRAGMA wal_checkpoint(TRUNCATE);')
cur.execute('PRAGMA freelist_count;')
free = cur.fetchone()[0]
if free > 100:
    cur.execute(f'PRAGMA incremental_vacuum({free});')
conn.commit()
conn.close()
```

## P1: Analyze Collection Volume

```sql
SELECT source, platform, COUNT(*), MAX(collected_at)
FROM raw_intelligence 
WHERE collected_at >= datetime('now', '-1 day')
GROUP BY source, platform
ORDER BY COUNT(*) DESC
```

## P2: Clean Output Files

```bash
find ~/.hermes/outputs/ -type f -name "state_backup_pre_*.db" -delete
find ~/.hermes/outputs/ -maxdepth 1 -type f \( -name "debug_*" -o -name "*.html" \) -delete
```

## P3: Save Proven Workflow as Skill

- When a non-trivial technique or workflow emerged, save it as a skill
- Include validation gate: run the skill on 3-5 test scenarios before accepting
- Max 3 rules modified per patch cycle (SkillOpt learning rate)
- See references/skillopt-validation-gate.md for full methodology

## P3: Verify Self-Evolution Engine Output

After the daily 3am evolution cycle, the `evolve_skills()` output now includes:

```json
{
  "skills_analyzed": 359,
  "skills_passed_validation": 180,
  "skills_failed_validation": 179,
  "negative_transfer_risks": [],
  "overall_quality_score": 0.501,
  "deprecations": []
}
```

Key checks:
- **skills_passed_validation**: Should be ≥50% after mass repair; reference-type skills (mlops docs, category indexes) will naturally fail — that's by design.
- **negative_transfer_risks**: Should remain 0 unless skill quality is degrading. If any appear, run `skillopt_trainer.py risks` to list them and investigate manually.
- **overall_quality_score**: The ratio of passed/total. Expect ~0.5 for the full library. For a filtered set of workflow skills only, expect ≥0.85.
- **deprecations**: Skills >180 days old. Review periodically but don't auto-delete — some static reference skills are intentionally untouched.

## P3: Run Negative Transfer Detection on Skills

Per Microsoft Skill Lifecycle paper (arXiv:2605.23899), **25% of model-generated skills cause negative transfer**:

```bash
# Quick scan: flag skills that haven't been modified in 30+ days
find ~/.hermes/skills -name "SKILL.md" -mtime +30 | while read f; do
  skill=$(basename $(dirname $(dirname "$f")))
  echo "Stale: $skill (last modified >30 days ago)"
done

# Use SkillOpt trainer for formal validation
python3 ~/.hermes/scripts/skillopt_trainer.py risks    # 负迁移检测
python3 ~/.hermes/scripts/skillopt_trainer.py stats    # 验证统计
python3 ~/.hermes/scripts/skillopt_trainer.py validate <skill-name>  # 单skill验证
```

## ⚡ Type-Aware Validation Gate (v2.0变化)

验证门现在是**类型感知的**，skillopt_trainer自动检测Skill类型：

| 类型 | 判定方式 | 阈值 | 示例 |
|------|---------|------|------|
| workflow | 类别白名单 | 80% | fde/hermes/engineering/creative... |
| reference | 类别白名单 | 60% | expert-system/domain/inference-sh... |
| mlops_ref | 子路径模糊匹配 | 跳过(0%) | mlops/models/*, mlops/inference/*... |

mlops参考型Skill不需要改成工作流结构。论文证明format不预测效用(p>0.34)。它们的信息密度本身就是价值。

## P3: SkillOpt Validation Gate for All Changes (LLM增强双轨)

When this executor proposes any modification (skill/script/config), apply the validation gate BEFORE accepting.

The `analyze_performance()` method now uses **LLM dual-track architecture**:
- **LLM路径（优先）**: `_llm_analyze_performance()` — 用LLM分析性能数据，生成有数据支撑的洞察
- **规则路径（降级）**: 固定模板建议（LLM不可用时）

The `evolve_skills()` method now includes **SkillOpt full validation**:
- `skills_passed_validation` — 通过5维度验证门的skill数
- `skills_failed_validation` — 未通过的skill数（大部分是参考型）
- `overall_quality_score` — passed/total比率
- `negative_transfer_risks` — 负迁移风险列表

```python
from scripts.skillopt_trainer import SkillOptTrainer
trainer = SkillOptTrainer()

# LLM+规则双轨验证
result = trainer.validate_skill("affected_component", test_count=3, use_llm=True)
# result.score = rule_score * 0.5 + llm_score * 0.5

if not result["passed"]:
    trainer.add_to_reject_buffer("affected_component", old_content, new_content, 
        f"Self-evolution validation: {result['score']:.2f} (llm={result.get('llm_score',0):.2f})")
    # Do not apply the change — record what was rejected
```

The validation gate is now integrated into `self_evolution_engine.py`'s `evolve_skills()` method. When the daily 3am cron runs `full_evolution_cycle()`, it automatically:
- Scans all 359 skills through the 5-dimension validation gate + LLM semantic assessment
- Records pass/fail counts and individual deprecations
- Runs negative transfer detection against historical records
- Computes `overall_quality_score = passed / total`
- The results are logged and persisted in the evolution history DB

## ⏰ Cron Collision Avoidance

当添加新cron时，必须检查现有cron的时间分布，避免重叠：
```
当前时间槽占用:
  0分 → 采集3h + 审计2h + 编排每小时 + 清理3点
  15分 → L2场景(错开采集)  
  30分 → 采集6h加重
  45分 → L1提取(错开采集30分)
  */30 → 情景注入
  * * → 唤醒注入(每分钟,无冲突风险)
```

**规则**: L1/L2/cron维护任务必须与采集(0分)错开至少15分钟。

当执行进化修复任务时，遵循以下8步序列：
1. 全面历史回顾 + 系统状态审计 → 先读日志/记忆/技能，确认根因
2. 分阶段拆解 → P0→P1→P2→P3，逐步执行
3. 每阶段阶段性复盘 → 确认方向不跑偏
4. 完整后全局复盘 → 确认所有要求满足
5. 深度自检 → 所有修复必须真实实现
6. 循环完善 → "完善→审核→测试→再完善"
7. 中断自动恢复 → 中断→继续执行→回顾历史→高质量实现
8. **禁止批量生成配置** → 每个员工/专家逐个手工定制

## Pitfalls (V3.3补充)

- **patch工具丢弃函数体**: `skill_manage(action='patch')` 在文件被部分读取后（如用 `offset/limit` 分页查看），patch 操作可能将函数体连带新旧字符串匹配失败。**修改前必须先用 `read_file()` 完整读取文件**，确保patch工具拥有完整的old_string上下文。如果报错 "Could not find a match"，不应直接假设字符串不存在——先检查是否是分页读取导致的不完整上下文。
- **execute_plan returns 0 steps — check experience_engine**: If task execution returns `completed_steps=0`, the experience_engine import likely threw an exception. Check for `experiences = []` missing or DriftLevel enum comparison failures.
- **V3 subsystem import fails in sandbox**: `task_engine.py` uses `Path(__file__).parent.parent / "evolution_v3"`. In sandbox/testing this resolves wrong. Always `sys.path.insert(0, str(HERMES / "evolution_v3"))` before V3 imports.
- **Python __method name mangling**: Avoid `__method` in single-instance patterns. `self.__init_core()` becomes `_ClassName__init_core` and silently fails.
- **Merkle tree hash format**: Use `.digest()` (raw bytes) for tree nodes, `.hex()` only for external display. Mixing hex and bytes causes root hash mismatch.

## Pitfalls

- **No sqlite3 CLI**: Always use `python3 -c "import sqlite3"`
- **state.db locked**: Gateway holds write-lock. Checkpoint works, VACUUM may not.
- **Pipeline "stalled" may be misleading**: Pipeline_v3 outputs only update on agent-driven runs
- **Kuaishou test first**: It may still work despite being flagged as dead
- **No sudo on WSL2**: Use non-sudo alternatives for everything

## 回滚方案
### 快速回滚
如果部署后发现问题：
1. 使用版本控制回退到上一个提交：`git revert HEAD`
2. 确认回滚后系统状态正常
3. 通知相关方变更已撤销

### 数据安全
- 所有修改前确认有备份
- 配置变更记录版本历史
