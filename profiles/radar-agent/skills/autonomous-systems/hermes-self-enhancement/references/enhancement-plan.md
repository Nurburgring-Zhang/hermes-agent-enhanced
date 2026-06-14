# Hermes 综合任务执行与自我进化增强提升计划

> 基于方向A（Agent长程任务：LangGraph/MetaGPT/Reflexion）、方向B（软件工程方法论：Amazon 6页纸/华为IPD/DoD/Testing Trophy）、方向C（自我进化：Reflexion/Voyager/GEPA/AutoClean）全网调研，结合Hermes现有齿轮系统、复盘引擎、Hy-Memory、自进化引擎、检查点管理、技能系统等能力，制定的可执行增强计划。
>
> **核心原则：补充而非推翻。Hermes已有架构不重构——只在关键节点插入增强模块。**

---

## P0：基础层增强（本轮对话执行）

### P0-1：三层认知架构 → 文件级分离

**背景：** 当前Hermes无明确的执行/监控/反思分层。LangGraph的StateGraph启发：执行层做工具调用→监控层做状态检查→反思层做元认知评估。三层分离带来可观测性和可打断性。

**实现路径：**

| 文件 | 改动 |
|------|------|
| `run_agent.py` (`AIAgent.run_conversation`) | 在主循环中插入3个显式阶段标记。在每个工具调用回合后增加 `_monitor_turn()` 调用 |
| `agent/monitor.py` **【新建】** | 监控层引擎：`MonitorEngine(mode='auto')` → 检查迭代预算/进度/异常 → 输出 `MonitorSignal(CONTINUE\|CHECKPOINT\|REFLECT\|ABORT)` |
| `agent/reflector.py` **【新建】** | 反思层引擎：`ReflectorEngine` → 在监控层发出`REFLECT`信号时自动调用。复用Hermes已有复盘模式 |
| `hermes_cli/commands.py` | 加 `/status` 命令显示当前层级状态：`[EXEC] Gear 3/8 → [MON] 65% → [REF] 待触发` |

**验证方法：**
- 运行 `python -c "from agent.monitor import MonitorEngine; m=MonitorEngine(); print(m.evaluate({'turns':5,'max_iterations':90}))"` 得到 CONTINUE
- 运行 `python -c "from agent.reflector import ReflectorEngine; r=ReflectorEngine(); print(r.reflect(['error: file not found','retry: create parent dir']))"` 得到反思文本
- AIAgent集成测试：`tests/test_three_layer_architecture.py` 验证每层调用链

**优先级：** P0 | **估算：** 3h

### P0-2：模型智能路由策略

**背景：** 目前Hermes使用单模型调用。MetaGPT按角色分配模型的方式启发：低成本模型处理路由判断，高成本模型处理核心推理。

**实现路径：**

| 文件 | 改动 |
|------|------|
| `agent/model_router.py` **【新建】** | `ModelRouter` 类：根据任务特征向量(复杂度/步长/工具数)自动选择模型梯队。E0=deepseek-chat(普通), E1=v4-pro(高难代码), E2=v4-flash(简单检索) |
| `run_agent.py` (`AIAgent.__init__`) | 新增 `model_router` 参数，如果启用则在每次LLM调用前 `self.model = self.model_router.select(messages)` |
| `hermes_constants.py` | 加 `HERMES_MODEL_ROUTER_ENABLED` 环境变量开关 |
| `~/.hermes/config.yaml` | 扩展 `model_router:` 配置段，支持自定义梯队模型名 |

**验证方法：**
- `tests/test_model_router.py`：输入"hello"应返回E2(v4-flash)，输入"写一个分布式raft协议实现"应返回E1(v4-pro)
- `hermes --model-router` 以路由模式启动，观察不同任务触发的不同模型
- `hermes stats` 显示各梯队调用统计

**优先级：** P0 | **估算：** 2h

### P0-3：对话层实时进度反馈

**背景：** 长任务中用户看到空白输出，不知道Agent在做什么。参考Google Search的逐段渲染机制。

**实现路径：**

| 文件 | 改动 |
|------|------|
| `run_agent.py` (`AIAgent.run_conversation`) | 每轮结束后生成 `_progress_summary()`，格式：`[步骤 5/42] ✓ 已创建配置文件 → 等待数据库迁移... (预计3步)` |
| `cli.py` (`HermesCLI._display_progress`) | 新增回调，每次 `_progress_summary()` 更新状态栏（非阻塞，不打断输出流） |
| `tools/progress_tool.py` **【新建】** | `progress_report(action, message)` 工具——Agent可主动上报进度里程碑 |
| `agent/display.py` | 给KawaiiSpinner增加进度感知，显示 `┊ [5/42] 🔧 配置数据库` |

**验证方法：**
- `hermes --progress` 指定进度模式
- 手动触发一次40步任务，观察每轮结束是否出现 `[步骤 X/Y]` 格式输出
- `tools/progress_tool.py` 测试：`progress_report('milestone','数据库连接成功')` → 输出已确认

**优先级：** P0 | **估算：** 2h

---

## P1：全局规划与长程任务（本周执行）

### P1-1：6页纸式任务前分析

**背景：** Amazon 6页纸的核心是「写作迫使思考」——在行动之前强制写文档。当前Hermes直接进入工具调用，没有任务前规划环节。

**实现路径：**

| 文件 | 改动 |
|------|------|
| `writing-plans` skill | 扩展SKILL.md，增加 `## 任务前分析（6页纸模板）` 章节 |
| `templates/task-analysis-6pager.md` **【新建】** | 标准模板含：背景/方案/实施计划/成功标准/风险回滚/附录 |
| `templates/tenets-template.md` **【新建】** | 2-5条决策原则模板 |
| `run_agent.py` | 如果`confidence<0.7`或`is_complex`标记为True，自动调用6页纸分析 |

**模板示例：**
```markdown
# 任务分析：{{TASK_NAME}}

## 1. 背景与问题定义
- 用户需求一句话：
- 核心问题：
- 当前状态：

## 2. 解决方案
- 方案A：{{DESC}} (优点/缺点/风险)
- 方案B：{{DESC}} (优点/缺点/风险)
- 选定方案：

## 3. 实施计划
- Phase 1: {{PHASE}} (预计X步)
- Phase 2: {{PHASE}} (预计X步)
...

## 4. 成功标准
- [ ] 标准1
- [ ] 标准2

## 5. 风险与回滚
- 风险A：{{RISK}} → 应对{{COUNTERMEASURE}}
- 回滚计划：{{ROLLBACK}}

## 6. Tenets（决策原则）
1. {{TENET1}}
2. {{TENET2}}
```

**验证方法：**
- 手动触发复杂任务，检查是否自动生成了任务分析文档
- 文档覆盖6页纸全部6个章节
- 复盘时引用成功标准做对照

**优先级：** P1 | **估算：** 4h

### P1-2：结构化检查点机制强化

**背景：** 现有检查点(5步/阶段)过于基础。LangGraph的StateGraph启发：每个检查点应保存环境快照+进度+中间结果+决策理由。

**实现路径：**

| 文件 | 改动 |
|------|------|
| `schema/checkpoint_v2.py` **【新建】** | 新检查点数据类：`CheckpointV2` 含timestamp, session_id, executed_steps[], pending_steps[], env_snapshot, partial_results[], decisions[], metrics{} |
| `scripts/checkpoint_manager.py` | 新增 `save_v2(checkpoint)` 和 `load_v2(session_id)` 接口，兼容旧版本 |
| `run_agent.py` | 每5步或阶段结束时调用 `checkpoint_manager.save_v2(CheckpointV2(...))` |
| `tests/test_checkpoint_v2.py` | 验证保存+恢复+兼容旧格式 |

**验证方法：**
- 模拟中断：保存检查点→重启→验证进度恢复
- 环境快照检查：中断前的中间结果在恢复后可用
- 旧格式检查点仍可读取

**优先级：** P1 | **估算：** 5h

### P1-3：L1-L2-L3 分层规划

**背景：** 当前任务规划不做三层分解。MetaGPT的分层输出启发：每层使用不同粒度。

**实现路径：**

| 层 | 触发 | 内容 | 输出 |
|----|------|------|------|
| L1目标层 | 任务开始 | 用户真正要什么?成功标准?约束? | `【任务目标】` + `【成功标准清单】` |
| L2策略层 | 任务开始 | 用什么工具/技能?分几个阶段? | `【执行策略】` + `【阶段划分】` |
| L3执行层 | 逐步 | 当前做什么? | ReAct: Thought→Action→Observation |

**验证方法：**
- 任务开始后检查是否有3层分离输出
- L1不变时多个L2策略的方案对比
- 每步L3执行绑定到L2的某个子阶段

**优先级：** P1 | **估算：** 3h

---

## P2：质量把控与审核（下周执行）

### P2-1：IPD TR门禁改造

**背景：** 华为IPD TR1-TR6门禁体系确保每个阶段有明确退出标准。Hermes每类任务的阶段对应TR门禁。

**实现路径：**

| 阶段 | Hermes对应 | 门禁条件 |
|------|-----------|---------|
| TR1(需求) | 任务接收 | 任务目标定义完整+成功标准明确 |
| TR2(方案) | 策略选择 | 方案评估≥2种+选定方案有理由 |
| TR3(模块) | 子任务实现 | 每个子任务有输出+验证 |
| TR4(原型) | 关键功能 | 核心功能端到端可工作 |
| TR5(集成) | 全链路 | 所有子任务集成+测试通过 |
| TR6(交付) | 最终验收 | DoD全部满足+复盘完成 |

**验证方法：**
- 每个阶段完成后自动检查门禁条件
- 未通过则触发REFLECT信号
- 记录每个TR的通过/失败历史

**优先级：** P2 | **估算：** 6h

### P2-2：DoD清单改造

**背景：** Definition of Done是敏捷开发的核心质量门。每类任务应有标准DoD。

**实现路径：**

| 任务类型 | DoD清单 |
|---------|---------|
| 代码任务 | [ ] 代码完整可运行 [ ] 语法无错误 [ ] 备份已完成 [ ] 测试通过 [ ] 自审查完成 [ ] 交付报告 |
| 修复任务 | [ ] 根因已确认 [ ] 修复已实施 [ ] 恢复已验证 [ ] 未引入新问题 [ ] 复盘已完成 |
| 调研任务 | [ ] 来源≥3 [ ] 信息可追溯 [ ] 非幻觉验证 [ ] 逻辑链完整 [ ] 结论有依据 |
| 推送任务 | [ ] 候选池有数据 [ ] 评分正常 [ ] 推送成功 [ ] 用户收到 |

**验证方法：**
- 每类任务结束后自动检查DoD
- 未通过标记为"待完善"
- 通过后记录到复盘报告

**优先级：** P2 | **估算：** 3h

### P2-3：三轮复盘强化

**背景：** 当前复盘单轮完成。OpenClaw三轮反思(执行→策略→元认知)可显著提升复盘的深度。

**实现路径：**

| 轮次 | 焦点 | 触发 | 输出 |
|------|------|------|------|
| Round 1: 执行复盘 | 结果vs预期 | 任务结束 | 差距分析+修正项 |
| Round 2: 策略复盘 | 方法vs标准 | Round 1完成 | 策略评估+方法改进 |
| Round 3: 元认知复盘 | 为什么选这策略 | Round 2完成 | 通用教训+模式提取 |

**验证方法：**
- 复盘报告包含3轮独立分析
- Round 3输出可重复使用的"通用教训"
- 通用教训自动写入memory

**优先级：** P2 | **估算：** 4h

---

## P3：自我进化与能力增强（第3-4周执行）

### P3-1：Reflexion结构化反思

**基于现有复盘引擎强化：**

失败任务自动调用Reflexion三段式：
1. **轨迹分析**：检查执行失败的完整轨迹
2. **根因推断**：LLM分析失败根因(理解错误/执行错误/计划错误/环境约束)
3. **改进策略生成**：输出格式为`{修正指令}`或`{行为准则}`

改进策略存入memory_semantic，下次相似任务通过相似度检索自动注入。

**验证方法：**
- 人工触发一个失败任务→检查是否产出结构化反思
- 反思输出格式正确(修正指令/行为准则)
- 下个任务是否自动检索到相关反思

**优先级：** P3 | **估算：** 6h

### P3-2：Voyager技能发现机制

**自动检测能力边界+推荐进化方向：**

1. 扫描所有Skill的调用频率+成功率
2. 生成当前能力画像(能做什么/不能做什么)
3. 让LLM推荐"下一步应该掌握的Skill"
4. 推荐的Skill进入"待学习队列"

**验证方法：**
- 启动技能发现→输出能力画像
- 画像包含：已掌握技能覆盖+能力边界
- 推荐的新Skill有明确学习路径

**优先级：** P3 | **估算：** 5h

### P3-3：GEPA遗传变异

**在每日03:00进化引擎中加入遗传操作：**

1. 选出连续3天评分<60的低分Skill
2. 生成5种变异(加点/删点/替换/参数/交叉重组)
3. 每种变异跑A/B测试(原版vs新版)
4. 优胜者替换原Skill

**变异策略：**
- 加点变异：在流程中插入新步骤
- 删点变异：移除冗余步骤
- 替换变异：用已知更优方案替换
- 参数变异：调整阈值/超时等参数
- 交叉重组：合并两个Skill

**验证方法：**
- 每日进化日志显示遗传操作记录
- 变异后Skill的A/B测试结果
- 保留最优变体的记录

**优先级：** P3 | **估算：** 6h

### P3-4：经验引擎 (Experience Engine)

**每次任务后自动从执行轨迹提取可复用经验：**

1. 收集完整轨迹(需要agent/reflector.py配合)
2. LLM从轨迹提取"条件→行动→结果"模式
3. 过滤掉任务特定的细节
4. 经验验证(在类似任务上测试)
5. 经验固化(转化为Skill或Smart Flow)

**经验存储格式：**
```json
{
  "id": "exp_001",
  "pattern": "当出现X错误时，执行Y操作，得到Z结果",
  "context": "数据库迁移场景",
  "confidence": 0.85,
  "verified": true,
  "created_at": "2026-06-01"
}
```

**验证方法：**
- 每次任务后检查是否产出了经验片段
- 经验片段的数量和质量
- 在类似任务上能检索到相关经验

**优先级：** P3 | **估算：** 6h

### P3-5：AutoClean 机器遗忘

**定期清理记忆和Skill库中的错误/过时/冗余内容：**

1. **错误检测**：Skill调用连续失败n次→标记可疑
2. **过时检测**：记忆超90天未访问→冷归档
3. **冗余检测**：功能相似的Skill→合并建议
4. **清理策略**：软删除(标记)+归档(冷存储)+合并(通用版)

**验证方法：**
- 运行AutoClean输出清理建议
- 清理后记忆库大小变化
- 检索准确度在清理后保持不变或提升

**优先级：** P3 | **估算：** 4h

---

## 执行路线图

```
Week 1 (6/1-6/7): P0 已完成 + P1 开始
  ├─ 三层认知架构(monitor/reflector) ✅
  ├─ 模型路由(model_router) ✅
  ├─ 进度反馈工具(progress_tool) ✅
  ├─ 6页纸模板 → 本周
  ├─ 检查点V2 → 本周
  └─ L1-L2-L3分层 → 本周

Week 2 (6/8-6/14): P1完成 + P2开始
  ├─ TR1-TR6门禁
  ├─ DoD清单
  └─ 三轮复盘

Week 3-4 (6/15-6/28): P3
  ├─ Reflexion结构化反思
  ├─ Voyager技能发现
  ├─ GEPA遗传变异
  ├─ 经验引擎
  └─ AutoClean机器遗忘
```

## 关联文件

| 文件 | 说明 |
|------|------|
| `agent/monitor.py` | 监控层引擎（P0已编码） |
| `agent/reflector.py` | 反思层引擎（P0已编码） |
| `agent/model_router.py` | 模型路由引擎（P0已编码） |
| `tools/progress_tool.py` | 进度反馈工具（P0已编码） |
| `tests/test_three_layer_architecture.py` | 三层架构测试（P0已编码） |
| `tests/test_model_router.py` | 模型路由测试（P0已编码） |
| `tests/test_progress_tool.py` | 进度工具测试（P0已编码） |
| `scripts/run_p0_tests.py` | P0测试运行器（P0已编码） |
| `references/research-driven-enhancement-methodology.md` | 调研成果知识库 |
