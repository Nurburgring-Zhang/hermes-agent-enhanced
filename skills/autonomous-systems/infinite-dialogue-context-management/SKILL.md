---
name: infinite-dialogue-context-management
description: 无限对话上下文管理 — 段式切换(segment_manager每50轮自动归档重建)+信息无损三明治交接协议+一致性守卫(consistency_guard每5轮自检文件/cron/齿轮/上下文系统)
category: autonomous-systems
---

# 无限对话上下文管理

### Absorbed Skills (consolidated)

| Former Skill | Absorbed As | Reference File |
|---|---|---|
| `context-index-resolve` | Subsection — SOUL.md index-and-resolve subsystem (context_index.json, 36-chapter on-demand restoration) | `references/context-index-resolve-skill.md` |

The absorbed skill `context-index-resolve` documents the SOUL.md index system: first-round full SOUL.md → subsequent rounds only context_index.json (~1410t). 36 chapters restored via read_file on demand. This is the index+resolve layer of the overall context management architecture. See the reference for full detail including the 5-cron-per-minute auto-indexing setup.

## 核心问题

对话轮次超过50轮后上下文累积超限。常规压缩只能减少固定开销（SOUL.md/AGENTS.md/记忆），无法阻止历史消息累积。

## 段式切换架构

不追求"每轮都小"，而是"每N轮重建上下文"。把对话生命周期拆成段(segment)，每段~50轮。

```
段1(第1-50轮):
  段内: 注入核心(2.5Kt) + 正常累积(~25Kt) → 总共~27.5Kt
  第50轮: 生成交接笔记 → 归档到文件

段2(第51-100轮):
  第51轮: 读交接笔记(~500t) + 注入核心(2.5Kt) → 重建上下文(~3Kt)
  段内: 正常累积(~25Kt)
  第100轮: 生成交接笔记 → 归档

1000轮 = 20段
每段仅消耗 ~28Kt tokens
等效处理能力: 20 × 50 × 25Kt = 25M tokens
```

## 三明治交接协议（保证信息无损传递）

段切换时不是只传一段摘要，而是三层信息同时传：

### 层1: 任务断点（wake_guide.json + task_current.json）
- 已有系统，每步更新
- 包含: task_id, next_action, completed_steps, errors
- 保证: 任务级别的"做到哪了"

### 层2: 关键决策链（segment_manager交接笔记）
- 段内: 每轮的action_summary + decision记录
- 段切换: 最近10条任务+最近5条决策+未完成任务
- 保证: "为什么做到这里、为什么选这个方案"

### 层3: 完整轨迹归档（到文件）
- tool_unloader自动卸载大工具结果到refs/*.md
- 段切换时不传所有轨迹，只传索引
- 需要时: read_file读具体某步的完整结果
- 保证: "所有历史数据可追溯，不丢任何细节"

## 信息误差的3种类型与防治（2026-06-01 固化）

格林主人极端关注"1000轮对话后信息不跑偏"——这不是段切换能单独解决的，因为每轮都有误差累积。

| 误差类型 | 原因 | 频率 | 解决方案 | 实现状态 |
|---------|------|:----:|---------|:--------:|
| A: 记忆误差 | AI记错"做了没做" | 每轮 | 文件系统锁定: 所有判断依赖`ls/stat/crontab -l`而非AI记忆 | ✅ consistency_guard |
| B: 理解误差 | AI理解歪了需求 | 每个需求 | 规划文件对照: LayeredPlanner L1目标层+DoD清单 | ✅ 已部署 |
| C: 简化误差 | 汇报简化丢细节 | 每步 | tool_unloader外置完整结果，需要时read_file | ✅ 但需强制启用 |

**关键原则：AI记忆是可选项。所有关键信息都有文件系统级别的证据，AI记错了不重要，读文件就对了。**

## 自动修复退化（auto_healer 模式）

consistency_guard检测到异常后，auto_healer自动尝试修复：

### 可修复模式
| 异常 | 自动修复动作 | 修复脚本 |
|------|------------|---------|
| context_index sections为空 | 执行 `context_index_system.py auto` 重建 | auto_healer.py |
| 关键脚本文件丢失/异常小 | 从 `/mnt/d/Hermes/备份/` 或备份目录恢复 | auto_healer.py |
| cron条目丢失 | 从cron_backup.txt或齿轮注册表重挂 | auto_healer.py |
| 齿轮不健康 | 重新启动gear_enforcer | auto_healer.py |

### 修复失败策略
- 连续3次修复失败 → 推送到微信status_reporter（齿轮degraded模式）
- 停止自动修复尝试（防止修越修坏）

### 自恢复引擎
`scripts/self_recovery.py` 提供完整恢复能力：
- 自动扫描M:/D:/C:盘的 `*enhancement*` 或 `YYYYMMDD` 备份目录
- 对比本地文件与备份，恢复缺失/损坏的文件
- 自动恢复cron条目
- 运行测试验证

```bash
python3 scripts/self_recovery.py            # 自动恢复
python3 scripts/self_recovery.py --check    # 只检查不恢复
```

### GitHub发布适配
备份到GitHub时只需确保：
1. **路径**：全部使用 `Path.home() / ".hermes"` 跨平台（已实现）
2. **脱敏**：无API KEY / 无绝对路径 / 无WSL内网IP（已实现）
3. **一键部署**：`deploy.py` 自动复制文件+挂cron+测试

## 2026-06-02 升级: 6个长程任务缺陷修复

格林主人在2026-06-02对话中进行了全面的长程任务能力审计，发现6个真实缺陷并全部修复。

### 缺陷1: 记忆分层空转 (L1/L2/L3)

**问题**: L1提取靠cron每2h运行，但一直检测0条新数据。L2/L3因无新数据从未触发。记忆系统在空转。

**修复**: `post_conversation` 中直接调用 `_run_l1_extractor(mod, user_message)`，对话刚结束时数据是热的。

```python
# agent_enhancement_manager.py safe_hook_post_conversation():
_run_l1_extractor(mod, user_message)  # 传入用户消息, 立即提取事实
```

**验证**: `grep "l1_extractor" logs/plugin_manager.log` 应看到 `[post] l1_extractor: 从对话提取X条事实`。

### 缺陷2: 检查点丢失

**问题**: 104轮对话, checkpoint_recorder为空。segment_manager切换段但没有保存过任何检查点。

**修复**: `segment_manager._rotate_segment()` 中自动调用 `checkpoint_recorder.py save`。

```python
# segment_manager.py _rotate_segment():
subprocess.run([sys.executable, str(cp_path), "save", f"segment_{old_segment}", f"段{old_segment}完成"])
```

**验证**: `python3 scripts/checkpoint_recorder.py status` 不应为空。

### 缺陷3: token浪费 (surgical_slicer输出全文)

**问题**: `surgical_context_slicer.main()` 每次输出SOUL.md前600字到stdout，每轮6825chars(~4095 tokens)注入system prompt。大量内容每轮重复。

**修复**: 输出从全文600字改为150字摘要。

```python
# 之前:
print(content[:600])
# 之后:
print(content[:150])  # 只输出摘要
```

**效果**: 每轮节省约450 chars/270 tokens。每段50轮=~13.5K tokens节省。

### 缺陷4: 段摘要不传递

**问题**: 段2只输出"段2, 4/50轮"，没有段1的任何总结或关键决策。段切换后LLM失忆。

**修复**: `_rotate_segment()` 中把 `_generate_handoff()` 生成的交接笔记同步到 `cross_session_cache.json`。

```python
csc["last_segment_handoff"] = handoff
csc["last_segment_id"] = old_segment
csc["new_segment_id"] = new_segment
```

交接笔记包含: 最近10条任务、最近5条决策、未完成任务、段进度。

**验证**: `cat reports/cross_session_cache.json | grep last_segment_handoff` 应不为空。

### 缺陷5: 无长程纠偏 (漂移检测)

**问题**: 没有检测语义漂移的机制。`meta_thinker.py` 存在但cron中未在正常对话中调用。

**修复**: `gear_enforcer Phase 0` 中每5段调用一次 `meta_thinker_auto()` 做漂移检测。

```python
# gear_enforcer.py Phase 0:
if current_seg > 0 and current_seg % 5 == 0 and seg_turns == 0:
    mt_result = meta_thinker_auto()
    drift_score = mt_result.get("drift_score", 0)
    if drift_score > 0.5:
        log("⚠️ 漂移分数={drift_score:.2f} > 0.5, 建议检查任务方向")
    else:
        log("✅ 漂移分数={drift_score:.2f}, 方向正常")
```

**验证**: `grep "纠偏\|drift" logs/gear_enforcer.log` 应看到漂移检测日志。

### 缺陷6: 无多进程任务管理

**问题**: `delegate_task` 只能并行3个，没有任务队列、状态监控、失败重试。

**修复**: 新建 `scripts/task_queue_manager.py`。

关键特性:
- SQLite持久化 (`reports/task_queue.db`)
- 并发控制: 最多5个任务同时运行
- 失败重试: 最多3次自动重试
- 依赖管理: 支持 `depends_on` 字段
- 后台线程执行, 不阻塞主线程

```bash
python3 scripts/task_queue_manager.py submit "任务名" "命令"  # 提交
python3 scripts/task_queue_manager.py process                  # 处理队列
python3 scripts/task_queue_manager.py status                   # 查看状态
python3 scripts/task_queue_manager.py retry <id>               # 重试
python3 scripts/task_queue_manager.py cancel <id>              # 取消
```

gear_enforcer每轮自动调用 `task_queue_manager process` 处理待处理任务。

**验证**: `python3 scripts/task_queue_manager.py status` 应有任务列表。

### 6个修复的验证命令

```bash
# 段状态
python3 scripts/segment_manager.py stats

# 检查点
python3 scripts/checkpoint_recorder.py status

# 任务队列
python3 scripts/task_queue_manager.py status

# 漂移检测日志
grep "纠偏\|drift" ~/.hermes/logs/gear_enforcer.log | tail -5

# 段摘要传递
grep "last_segment_handoff" ~/.hermes/reports/cross_session_cache.json

# L1记忆提取日志
grep "l1_extractor" ~/.hermes/logs/plugin_manager.log | tail -3

# 插件矩阵自检
python3 ~/.hermes/scripts/agent_enhancement_manager.py
```

## 自检不要等用户查（偏好嵌入）

格林主人要求：**所有自检/一致性检查必须主动执行，不能等用户问。** 齿轮系统每5轮自动触发consistency_guard检查文件/cron/齿轮/上下文系统。发现问题自动推送告警，修不好再等用户介入。**永远不要等用户问\"怎么样了\"才去检查系统健康。**

## 7层防线保证



| 误差类型 | 原因 | 频率 | 解决方案 |
|---------|------|:----:|---------|
| A: 记忆误差 | AI记错"做了没做" | 每轮 | 文件系统锁定: 所有判断依赖`ls/stat/crontab -l` |
| B: 理解误差 | AI理解歪了需求 | 每需求 | 规划文件对照: LayeredPlanner L1目标层+DoD清单 |
| C: 简化误差 | 汇报简化丢细节 | 每步 | tool_unloader外置完整结果，需要时read_file |

### 一致性守卫的5项检查（齿轮G1循环中自动执行）

1. **关键脚本文件完整性** — context_packer等6个脚本是否存在且>100B
2. **cron完整性** — 5个上下文相关cron是否都在crontab中
3. **齿轮健康** — wake_guide.json的gear_health==healthy
4. **上下文输出新鲜度** — context_index.json等输出文件最近更新
5. **异常记录** — 检测到异常写入consistency_anomalies.log并推送

检查频率: 每5轮一次（通过gear_enforcer的每1分钟循环检测当前轮次）

## 文件系统

| 文件 | 功能 | cron |
|------|------|:----:|
| `scripts/segment_manager.py` | 段管理器: 创建/切换/交接 | 注入gear_enforcer每1分钟 |
| `scripts/consistency_guard.py` | 一致性守卫: 5项自检 | 注入gear_enforcer每5轮 |
| `reports/segment_state.json` | 段状态持久化 | 每轮更新 |
| `reports/consistency_checkpoint.json` | 自检检查点 | 每5轮更新 |
| `reports/consistency_anomalies.log` | 异常日志 | 每次检测到异常追加 |
| `reports/handoff_notes/handoff_s{N}_to_s{N+1}_*.md` | 段交接笔记 | 每次段切换生成 |
| `reports/handoff_notes/trajectory_s{N}.jsonl` | 完整执行轨迹 | 每步写入 |

## 7层防线保证

| 防线 | 机制 | 丢了怎么办 |
|------|------|-----------|
| 1 | wake_guide.json 每分更新 | 齿轮自动恢复 |
| 2 | task_current.json 每步更新 | 读齿轮检查点 |
| 3 | 交接笔记 段结束时写入文件 | 文件永久保存 |
| 4 | 轨迹归档完整JSONL | 可从任一步追溯 |
| 5 | tool_unloader结果外置 | 每步结果独立存 |
| 6 | memory记忆注入 | 关键经验记在记忆 |
| 7 | gear_checkpoint 全系统恢复包 | G2齿轮合并断点 |

任意1层活着就能恢复，3层活着就能无损。

## 自动压缩强制执行层（force_compressor插件）

**问题：** 段式切换、context_packer、三明治协议——这些压缩机制都存在（skill定义+cron脚本），但产出没人用。SOUL.md说"应该压缩"但Hermes不主动做。

**修复：** 创建 system-level 强制压缩插件，通过 hook 注入，不可绕过。

### 架构
```
pre_context_load hook（每轮开始前）
  → 强制读 ~/.hermes/reports/context_pack.json 的压缩指令
  → 注入 context_packer 已压缩的指令集，不读原始SOUL.md全文

post_tool_call hook（每5轮触发）
  → 调用 context_packer.py 重新生成压缩包
  → 记录 SHA256 校验和
  → 30分钟触发 Level2，每日03:00触发 Level3
```

### 文件位置
- 插件代码：`~/.hermes/plugins/force_compressor/__init__.py`
- 日志目录：`~/.hermes/logs/compressor/`

### 不可绕过保障
1. pre_context_load hook 在系统底层加载，优先级高于所有 task/skill 指令
2. cron 每1分钟检测插件激活状态
3. 校验和验证：每次压缩生成 SHA256，下次加载时验证无损

### 与现有组件的关系

| 组件 | 角色 | 之前状态 | 现在状态 |
|------|------|----------|----------|
| context_packer.py | 压缩执行器 | cron每1分钟运行但产出没人读 | force_compressor pre_context_load 读出注入 |
| segment_manager.py | 段切换 | 自动运行 | 继续自动运行，互不冲突 |
| consistency_guard.py | 一致性检查 | 每5轮检查 | 继续运行 |
| force_compressor 插件 | 强制执行层 | 不存在 | 新创建 |

### 齿轮集成（已自动）
```python
# gear_enforcer.py每1分钟循环中自动执行:
from scripts.segment_manager import SegmentManager
sm = SegmentManager()
stats = sm.get_stats()
if stats["turns_in_segment"] >= stats["max_turns_per_segment"]:
    handoff = sm.advance_turn(...)
```

### 手动操作
```bash
# 查看当前段状态
python3 scripts/segment_manager.py stats

# 手动段切换
python3 scripts/segment_manager.py test

# 手动一致性检查
python3 scripts/consistency_guard.py
```

### 上下文重建提示（新段第1轮上下文中的固定内容）
```
[段N/20 · 第X轮/共计1000轮]
当前任务: {任务描述}
已完成: {任务摘要} (第{上段范围}轮)
下一步: {下一步动作}
上一段关键决策: {决策总结}
未完成任务: {未完成任务}
```

## 自动压缩强制执行层（force_compressor插件）

force_compressor 插件是压缩系统的强制执行层。
之前 context_packer.py 每1分钟产出一个压缩包但 Hermes 不会主动读它。
force_compressor 通过 pre_context_load hook 自动注入压缩产出。

### 文件位置
- 插件代码：`~/.hermes/plugins/force_compressor/__init__.py`
- 被消费的产出：`~/.hermes/reports/context_pack.json`

### 强制机制
- pre_context_load — 每轮开始前自动读压缩包
- post_tool_call — 每5轮触发压缩+校验和
- cron 每1分钟检测激活

### 关键教训
**规则写进 SOUL.md 不等于被执行。** 必须有可执行的代码路径
（插件 hook / cron 定时检测）才能真正生效。

## 触发条件
- 提及"1000轮"、"无限对话"、"上下文超限"、"对话中断"
- 提及"信息无损传递"、"模型知道要做什么"、"段切换"
- 提及"累积误差"、"跑偏"、"一致性自检"
