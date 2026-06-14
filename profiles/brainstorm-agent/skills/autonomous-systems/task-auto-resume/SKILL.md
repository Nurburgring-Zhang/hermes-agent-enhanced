---
name: task-auto-resume
title: "Hermes 长期任务自动恢复系统"
description: "每次Hermes醒来时自动检查未完成的长期任务并从断点恢复执行。含齿轮驱动器和上下文漂移恢复。"
version: "2.1"
author: "Hermes"
trigger: "every_session,bootstrap"
---

# 长期任务自动恢复 (Task Auto-Resume) v2.1

## 是什么
每次Hermes醒来时，自动检查是否有未完成的长期任务。如果有，自动从断点恢复执行，不需要格林主人提醒。

> **7条永久执行规则已通过9层机制在所有对话中强制生效**。
> 详见 `green-master-rules` skill §10 或 `references/enforcement-matrix.md`。

## 前置流程：7步任务执行规则（格林主人最高指令 2026-05-23 固化）
接到任何任务后，必须先走完这7步流程。参见 `~/.hermes/SOUL.md §八` 完整版。

### Step 0: 全面深度复盘（接任务后第一件事）
```
① 查全所有相关文件/配置/日志（不用单日日志就下结论，看全量）
② session_search 搜索所有相关历史会话
③ 检查所有相关记忆（memory）和技能（skill）
④ 验证系统实际状态（DB/文件/crontab等多角度）
⑤ 确认掌握完整信息后才开始执行
```
**禁令**: 禁止凭碎片信息下结论、省略排查步骤、偷懒心态。

### Step 1: 全局预判 + 总体规划
- 历史回顾（session_search → 所有相关会话）
- 全网检索（web_search → 技术/方案/标准）
- 明确任务要求、规则、标准
- 全局纵览、全局预判、全局总观、全局预览
- 制定详细总体规划
- 复杂任务拆解（分阶段/分步骤/分方向）
- 需要明确的信息 → 向格林主人提问请教

### Step 2: 超限拆解 + 自动续跑
遇到 tokens量大/模型超限/输出限制/字数超长：
1. 任务拆解，分阶段/分步骤/分方向执行
2. **任务中断 → 必须继续执行！！！** 回顾历史信息与文档，明确标准要求规则
3. **必须是高质量实现！！！** 严禁降级
4. `task_monitor.py` 每10分钟自动审查状态（cron: `*/10 * * * *`）

### Step 3: 每阶段完成后复盘
每个阶段执行完毕后：
1. 任务复盘 + 历史信息回顾
2. 确认任务方向不跑偏
3. 检查所有要求、标准、条件仍满足

### Step 4: 完整后全局复盘
任务完整执行完毕后：
1. 再次历史回顾 + 全局复盘
2. 确保所有要求、标准、条件均满足预设要求
3. 输出完整复盘报告

### Step 5: 真实实现 + 联网最佳方案 + 严苛测试
1. 所有设计/标准/功能完全真实实现
2. 高质量真实使用和运行
3. **联网检索**最新、最强、最高质量的实现方法参考
4. 确保达到**最佳质量实现**
5. 极端严苛的多工况 **商用级测试/评测**
6. 按需继续优化完善
7. 深度代码审核与功能测试
8. 确保所有功能完整、高质量、真实可运行

### Step 6: 多轮完善→审核→测试循环（至少3轮）
```
全面完善优化、迭代升级
  → 全面深度极端详细的商用级代码审核
    → 全面深度极端详细的商用级测试
      → 全面完善优化、迭代升级（回到第一步）
```

### Step 7: 严禁降级实现
- ✅ **高质量真实实现**
- ❌ 禁止简单/精简/批量/降级/模拟/虚拟实现
- ❌ 禁止只做示例、占位符、只写核心代码
- ❌ 禁止代码缩写、功能降级
- ❌ 禁止逃避缺陷——主动积极高质量解决问题
- ⚠️ 任务中断 → 必须继续执行！！！必须是高质量实现！！！回顾历史信息与文档 → 继续执行！！！

## 触发条件
- 每次新会话启动时（自动）
- 每次心跳检查时（自动）
- 格林主人说"干活"、"继续"、"续跑"时（手动）
- 任务卡死或中断（由 task_monitor.py 每10分钟检测触发）
- SOUL.md §0 强制8步协议：醒来后先读 `cat ~/.hermes/reports/wake_guide.json`

## 恢复层级

系统有三层独立恢复机制, 从底层到顶层:

### L1: 棘轮自动续跑 (GearTaskDriver)
**核心**: `~/.hermes/scripts/gear_task_driver.py`
cron: `* * * * *` (每1分钟)
原理: 读取 `reports/gear_task_queue.json`, 
检查是否有 `status=active` 但超过5分钟没有推动的任务,
自动调用 `recover()` 触发下一齿轮签署.

```bash
# 手动触发
python3 ~/.hermes/scripts/gear_task_driver.py recover
# 查看队列
python3 ~/.hermes/scripts/gear_task_driver.py status
```

### L1b: gear_enforcer Phase7 自动恢复 (★增强版)
**核心**: `~/.hermes/scripts/gear_enforcer.py` Phase 7
cron: `* * * * *` (每1分钟, 通过 gear_master)
原理: 检测到中断任务后，不再只是记录日志——**真正执行自动恢复**:
1. 调用 wake_guide.py 更新醒来指南
2. 自动修复文件一致性——如果 gear_checkpoint 和 task_current 的 task_id 不一致, 同步它们
3. 修复 recovery_pack 的状态和字段
4. 调用 meta_thinker_auto() 触发漂移检测+恢复
5. 如果 next_action 明确，写入 `.resume_instruction.txt` 供下次醒来读取
6. 无中断时自动清理残留恢复指令

```bash
# 手动触发 (测试恢复流程)
python3 ~/.hermes/scripts/gear_enforcer.py
# 查看恢复日志
tail -30 ~/.hermes/logs/self_enhance.log | grep "恢复"
```

### L1c: task_monitor 每10分钟自动监控
**核心**: `~/.hermes/scripts/task_monitor.py`
cron: `*/10 * * * *` (每10分钟, 通过 cronjob system)
原理: 三重检查中断任务（wake_guide → gear_checkpoint → recovery_pack），发现后立即自动恢复:
1. 同步三份文件状态一致
2. 调用 gear_enforcer.py 运行恢复
3. 调用 gear_task_driver.py cron 续跑
4. 重新生成 wake_guide
5. 检查 gear_enforcer 心跳，如果超过30分钟无心跳则尝试重启
6. 写入 `reports/task_monitor_report.json` 供醒来读取

```bash
# 手动检查
python3 ~/.hermes/scripts/task_monitor.py
# 查看最新报告
cat ~/.hermes/reports/task_monitor_report.json
```

### L2: 上下文漂移恢复 (MetaThinker + ContextEquilibria)
**核心**: `~/.hermes/scripts/meta_thinker.py` + `context_equilibria.py`
检测: 三路漂移检测(语义/策略/保真度)
恢复: 从LCM DAG记忆引擎检索原始目标, 重新注入上下文检查点

```bash
# 设置任务目标
python3 ~/.hermes/scripts/meta_thinker.py set-goal "<目标描述>"
# 检测漂移
python3 ~/.hermes/scripts/meta_thinker.py check --context "<当前上下文>"
# 恢复上下文
python3 ~/.hermes/scripts/context_equilibria.py restore <task_id> --goal "<目标>"
# 查看漂移日志
python3 ~/.hermes/scripts/meta_thinker.py log
```

### L3: 齿轮主调度器 (GearMaster)
**核心**: `~/.hermes/scripts/gear_master.py`
cron: `* * * * *` (每1分钟, 通过cron调用 `gear_master.py once`)
原理: 统一调度G1-G7+DRIVER, 每15秒循环检查.
★增强: 每次循环读取 wake_guide.json，如果检测到中断任务且G1未处理完毕，额外触发一次DRIVER实现双重保险.

```bash
python3 ~/.hermes/scripts/gear_master.py status
```

## 漂移检测快速参考

当任务执行偏离目标时:

```python
from meta_thinker import MetaThinker
mt = MetaThinker()
result = mt.check(initial_goal="目标", current_context="当前上下文")
if result["level"] in ("critical", "fail"):
    # 触发恢复
    from context_equilibria import ContextEquilibria
    ce = ContextEquilibria()
    ce.restore("task_id", "目标")
```

输出字段: `drift_score`(0-1), `semantic_drift`, `strategy_drift`, 
`context_fidelity`, `level`(ok/warn/critical/fail), `actions`

## 检查点

`~/.hermes/task_tracker.json` — 长期任务完成状态
`~/.hermes/reports/gear_task_queue.json` — 棘轮队列
`~/.hermes/memory/context_manager/context_state.json` — 热/温/冷上下文

## 执行流程

### Step 1: 醒来第一件事（SOUL.md §0 强制）
```bash
cat ~/.hermes/reports/wake_guide.json
```
→ 有 interrupted_task → 从 next_action 继续
→ 有 pipeline_actions → 先处理pipeline队列
→ gear_health=degraded → 先诊断齿轮系统

### Step 2: 运行检查脚本
```bash
cd ~/.hermes && python3 scripts/task_monitor.py
```

### Step 3: 读取队列状态
```bash
python3 scripts/gear_task_driver.py status
```

### Step 4: 检查上下文漂移
```bash
python3 scripts/meta_thinker.py status
```

### Step 5: 如果有中断任务
```bash
python3 scripts/gear_task_driver.py recover
python3 scripts/gear_enforcer.py  # 触发Phase7自动恢复
```

### Step 6: 验证
```bash
python3 scripts/gear_master.py status
python3 scripts/audit_logger.py verify
python3 scripts/task_monitor.py  # 确认中断已清理
```

## 中断恢复真实验证记录（2026-05-27）

### 已验证的中断恢复场景
| 场景 | 触发方式 | 恢复路径 | 验证状态 |
|------|---------|---------|:--------:|
| 对话被切断导致任务未完成 | AI醒来 → GEAR L1自动检测 | wake_guide → gear_checkpoint → next_action | ✅ 真实验证通过 |
| cron中缺少新部署的脚本 | crontab -l 检查 | 发现后直接添加到crontab | ✅ 真实验证通过 |
| 子Agent并行代码审核+压力测试 | delegate_task x 2 | 25个问题修复+314次测试全部通过 | ✅ 真实验证通过 |

### 验证的完整恢复链
```
醒来(对话重开)
  → cat wake_guide.json (有interrupted_task)
  → cat gear_checkpoint.json (task_id匹配, next_action已知)
  → cat recovery_pack.json (三重冗余备份)
  → 按next_action执行 (不等待用户指令)
  → 每完成1步写checkpoint
  → 每个工具调用后写断点
```

### 关键发现：醒来后实际做的
1. **wake_guide.json** 是唯一需要读的文件 → 包含任务ID + next_action + gear_health + 待办
2. **gear_checkpoint.json** 确认round/step细节
3. **recovery_pack.json** 兜底（三份文件一致时不需要）
4. 如果cron中缺少脚本（新部署但未添加），必须手动补充
5. **不要等用户指令** — 规则2要求中断后立即自动恢复

### pitfall: 醒来后先搞懂当前状态再做别的
不要一来就检查系统状态/DB/cron/齿轮。先按SOUL.md §0步骤做：
1. 读 wake_guide.json
2. 中断任务存在？→ 从next_action继续
3. 确认cron包含所需脚本
4. 继续执行

## 关键文件
- `~/.hermes/reports/context_pack.json` - 上下文压缩输出（2927 tokens, 86.3%压缩率）
- `~/.hermes/reports/surgical_context.json` - 手术刀切分输出（947 tokens/通用）
- `~/.hermes/reports/context_auto_assoc.json` - 自动关联输出（3195 tokens/索引+预加载）
- `~/.hermes/reports/context_auto_assoc.md` - 自动关联Markdown输出
- `~/.hermes/reports/context_sections/*.md` - 14个章节独立文件（AI按需读取）
- `~/.hermes/reports/cross_session_cache.json` - 跨轮次缓存（对话轮次+已完成/待办）
- `~/.hermes/reports/context_index.json` - 章节索引（1900 tokens, 14章节索引）
- `~/.hermes/resources/context_packer.py` - 上下文压缩脚本（备用位置）
- `references/wake_recovery_session.md` — 实战恢复记录（2026-05-27）
- `~/.hermes/task_tracker.json` - 任务跟踪器
- `~/.hermes/scripts/ability_activator.py` - 全能力激活扫描器(每1小时cron, 2026-05-24新增)
- `~/.hermes/reports/rules_verification_report.json` - 规则验证报告
- `~/.hermes/reports/ability_activation_report.json` - 全能力激活报告
- `~/.hermes/SOUL.md §八` - 7步永久任务执行规则
- `~/.hermes/AGENTS.md` - 全平台强制规则文件
- `~/.hermes/CLAUDE.md` - Claude Code规则文件
- `~/.hermes/.cursorrules` - Cursor规则文件
- `~/.hermes/scripts/long_task_guardian.py` - 守护脚本
- `~/.hermes/scripts/task_resumer.py` - 续跑脚本
- `~/.hermes/scripts/gear_task_driver.py` - 棘轮推动器(L1核心)
- `~/.hermes/scripts/gear_enforcer.py` - 强制器(含Phase7自动恢复, L1b核心)
- `~/.hermes/scripts/task_monitor.py` - 每10分钟自动监控(L1c核心, 2026-05-23新增)
- `~/.hermes/scripts/meta_thinker.py` - 漂移检测(L2核心)
- `~/.hermes/scripts/context_equilibria.py` - 上下文恢复(L2核心)
- `~/.hermes/scripts/gear_master.py` - 齿轮主调度器(L3核心)
- `~/.hermes/scripts/wake_guide.py` - 醒来指南生成器(G7齿轮, 被G1和G7 cron调用)
- `~/.hermes/scripts/gear_context_compressor.py` - 上下文压缩器(修复compress_round空字符串bug)
- `~/.hermes/reports/gear_task_queue.json` - 棘轮队列
- `~/.hermes/reports/wake_guide.json` - 醒来指南(G1+G7生成, Hermes醒来先读此文件)
- `~/.hermes/reports/task_monitor_report.json` - 任务监控报告(每10分钟更新)
- `~/.hermes/reports/recovery_pack.json` - 三重冗余恢复包
- `~/.hermes/reports/gear_checkpoint.json` - 齿轮检查点
- `~/.hermes/reports/.resume_instruction.txt` - 恢复指令(Phase7写入, 清理后自动删除)
- `~/.hermes/SOUL.md §八` - 7步永久任务执行规则

## 核心原则：任务终止是系统级失职，不是"正常边界"

**如果对话因 token 超限或输出限制被截断，这不是终止任务的借口。**
必须按以下步骤处理：

### 中断恢复铁律（格林主人最高指令 2026-05-27 固化 + 2026-05-31 强化）
1. **任何任务未完成即被中断** → 必须自动继续执行，不等用户催
2. **中断后必须拆解为多阶段** → 每阶段独立的检查点 + 齿轮驱动续跑
3. **禁止用"对话太长"做理由跳过复盘/迭代/测试循环**
4. **必须在SOUL.md §0 写checkpoint** → 每完成1个工具调用就写一次断点
5. **🔴🔴 必读：上下文过长时的输出策略** — 如果回复内容可能超过tokens限制，**必须主动拆分为多条回复**。不要一次性输出所有内容然后被截断。发现回复变长时，说"这段需要分步输出"然后分批发。格林主人因"一口气输出太长被截断"会直接骂人（"操你妈，这时候你不是应该回顾历史对话，然后将任务继续拆分"）。这是工作流问题不是memory问题。

### 避免中断的预防措施
- 超过5步的任务必须提前拆解成子任务（分阶段执行）
- 每个阶段结束时写文件断点（`task_current.json`）
- 每个工具调用后写checkpoint（`gear_context_compressor.py checkpoint`）
- 不要等到token快爆了才想拆解，一开始就拆
- 如果发现回复越来越长，主动说"这段回复太大，我拆成多个阶段"

## 陷阱

- **⚠️ 用户问进度/状态时，第一句话必须直接回答问题。** 格林主人极度厌恶先罗列诊断信息再给结论。用户说"怎么停了"时，必须按此结构回复：
  1. **第一行：核心结论** → "没有停。推送12:00成功11条，18:00成功14条。"
  2. 然后可以跟诊断细节
  这个优先级高于所有流程规范。被用户骂"操你妈"就是因为没先给结论直接开诊断。
- 不要让delegate_task无限嵌套
- 逐一手工严禁批量生成
- 正常状态输出 TASK_OK
- 漂移检测不要依赖 Jaccard 关键词匹配(准确率50%)
  使用 `local_semantic_embedding.py` 或 sentence-transformers(需缓存)
- **漂移检测时永远传入完整上下文,不要只传入步骤名** — 在execute_plan中, 将`goal + step_name`拼成一句话传入detect_drift,而不是只传step_name。步骤名+"需求分析"与目标+"实现JWT认证"看似无关(trigram/关键词无重叠), 但"实现JWT认证 当前步骤: 需求分析"明显相关。这个bug导致所有多步任务在第0步就被判定为"重度漂移"而终止。
- 上下文恢复后必须检查 LCM DAG 完整性:
  ```bash
  python3 ~/.hermes/scripts/lcm_dag_engine.py verify
  ```
- **⚠️ compress_round 传空字符串bug** — `gear_context_compressor.py` 的 compress_round CLI 路径曾传空字符串 `""` 给 gear_compress，导致 `estimate_tokens("")` 永远返回0，风险等级永远是"low"，实际压缩永远不触发。修复：改为自动读取 `current_context.txt` 或 `task_current.json` 作为上下文。
- **⚠️ gear_enforcer Phase7 仅检测不恢复** — 原来 Phase7 发现中断任务后只记录日志但不执行恢复操作。修复：现在自动同步3份文件一致性、调用 wake_guide、写入恢复指令。
- **⚠️ 文件一致性检查** — gear_checkpoint.json 和 task_current.json 的 task_id 可能不一致（一个显示running但另一个显示completed）。修复：现在 Phase7 和 task_monitor 都会自动修复这种矛盾，以 gear_checkpoint 为准。
- **⚠️ recovery_pack 数据矛盾** — recovery_pack 可能同时包含 running 和 completed 两种状态。修复：get_active_task() 增加第三重 recovery_pack 检测源，Phase7 自动修复 recovery_pack 状态。
- **⚠️ ability_activation监督** — gear_enforcer Phase8 新增全能力激活监督，每分钟检查 G1-G8+DRIVER+MASTER 文件完整性和语法正确性。如果某个齿轮文件缺失或语法错误，记录到 `self_enhance_report.json` 的 `ability_activation` 字段。
- **⚠️ G6验证告警噪声（已根治）** — 旧任务(如self_enhance_*, production_reliability_engine_v1)只有G0/G8+签名，不含完整G1-G7，G6每30分钟产生告警，gear_health保持degraded。**已根治**（2026-05-27）：归档非标准任务 + gear_task_validator.py新增跳过逻辑 + 清理告警文件。详见 `gear-interlocking-audit-v3` skill 陷阱#4。

## 回滚方案
### 快速回滚
如果部署后发现问题：
1. 使用版本控制回退到上一个提交：`git revert HEAD`
2. 确认回滚后系统状态正常
3. 通知相关方变更已撤销

### 数据安全
- 所有修改前确认有备份
- 配置变更记录版本历史
