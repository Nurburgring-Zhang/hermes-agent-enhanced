---
name: production-reliability-engine
description: 生产级可靠性引擎 — 解决长链任务"越往后越做不对、一步错步步错、做完不检查、执行不稳定"四大致命缺陷
trigger: 复杂任务（5+步骤）、长链任务、多阶段任务、需要高可靠性的任务、降级检测、Critic审查、中断恢复
---

# Hermes 生产级可靠性强化引擎

基于《让Agent真正完成真实任务：生产级可靠性Agent技术升级方案》实现。
轻量级设计，不干扰现有齿轮系统（G0-G7）。G8-PROD作为可选增强层。

## 解决的问题

## 触发条件
- 用户提及Agent编排、系统集成、管道时
- 需要配置或调试多Agent系统时
- 执行系统自我进化或健康检查时


| 失败模式 | 表现 | 根因 | 解决方案 |
|:---------|:-----|:-----|:---------|
| 概率复合崩塌 | 12步95%检查点→仅54%通过 | 缺少全局进度追踪 | DAG任务图+LoopState全局进度 |
| 错误级联传播 | 一步错导致下游全偏 | 缺少操作后即时验证 | 每一步后强制验证+退路机制 |
| 意图-状态断层 | Agent以为做完了实际没生效 | 缺少独立验证 | StepVerifier+CriticAgent独立审计 |
| 路径依赖随机分叉 | 同任务3次分数0.00~0.68 | 缺少确定性锚点 | FSM+全局约束+ReFlect规则引擎 |

## 模块架构

```
production_loop/
├── __init__.py           # 包标识
├── loop_state.py         # LoopState全局状态 + SQLite持久化 + 5文件状态
├── dag_manager.py        # DAG任务图 + 全局约束锚定 + 拓扑排序
├── main_loop.py          # 确定性主循环 + 10种终止条件
├── agent_committee.py    # 专家委员会 + CriticAgent + 三层反思
├── verification.py       # 步骤验证器 + ReFlect规则引擎 + 降级拦截器
├── security.py           # 7层权限 + 子代理隔离 + 可观测性
└── engine.py             # 统一引擎 + CLI入口 + 中断恢复

scripts/
└── production_loop_cron.py  # cron调度器
```

## 关键组件详解

### 1. LoopState全局状态（唯一真相源）

`loop_state.py` 实现文档§2.2完整LoopState架构：

- **状态机FSM**: IDLE→PLANNING→EXECUTING→VERIFYING→REFLECTING→WAITING_FOR_USER→RECOVERING
- **全局进度追踪**: completedNodes + failedNodes + overallProgress(0-1)
- **全局约束锚定**: originalGoal + hardConstraints + softConstraints + constraintCheckHistory
- **SQLite持久化**: 5张表（agent_state_transitions/agent_checkpoints/agent_tasks/agent_verification_log）
- **5文件状态架构**: run_state.json + last_success.json + dedupe_index.json + execution_log.jsonl + handoff.md

### 2. DAG任务图

`dag_manager.py` 实现文档§3.2：

- `build_auto_dag(steps)` — 从步骤列表自动生成DAG
- `validate_dag()` — 验证完整性（节点存在性、边存在性、环检测）
- `topological_sort()` — Kahn算法拓扑排序
- `get_ready_nodes()` — 获取当前可执行节点（依赖检查）
- 失败策略：maxRetries + retryStrategy(immediate/backoff/replan) + fallbackNodeId

### 3. 确定性主循环

`main_loop.py` 实现文档§2.1：

- **10种终止条件**: completed/max_turns/user_interrupted/critic_judged/failures_3/max_retries/deadlock/context_overflow/max_tokens/error
- **每5步自动保存检查点**
- **高风险操作前强制环境快照**
- **工具调用统计**：totalCalls + successRate + toolSpecific

### 4. 专家委员会 + CriticAgent

`agent_committee.py` 实现文档§2.3 + §4：

- **6种预定义子代理**: planning/execution/verification/critique/recovery/research
- **每个子代理**: 独立system prompt + 工具白名单 + 隔离级别
- **CriticAgent独立审计者**（文档§4.2）："宁可多质疑，不可遗漏问题"
- **三层反思**（文档§4.1）: 
  - 操作层反思：每个工具调用后即时验证
  - 策略层反思：每个子任务完成后评估效率和质量
  - 目标层反思：每10步检查是否偏离原始目标
- **结构化反思工作流**（文档§5.1）: 5-Why根因分析→修正方案→执行→验证→技能沉淀
- **降级检测**（文档§8.1）: 5种降级模式自动检测

### 5. 步骤验证器 + ReFlect + 降级拦截

`verification.py` 实现文档§3.4 + §4.3 + §8.1：

- **StepVerifier**: 4种验证策略（快照对比/页面重读/数据库断言/值匹配）
- **ReFlect确定性规则引擎**: 7条独立于LLM的规则
  - 规则1: post_action_page_check — 操作后错误页面检测
  - 规则2: loop_detection — 同一工具同一参数连续3次
  - 规则3: context_overflow — 上下文使用量>80%
  - 规则4: consecutive_failure — 最近3次验证全失败
  - 规则5: noop_detection — 读操作连续返回空
  - 规则6: outlier_duration — 耗时>平均值5倍
  - 规则7: truncation_detection — 输出被截断
- **DegradationPreventer降级拦截器**: 检测6种模式（40个关键词）
  - 范围缩减（只实现/简化为/仅支持/先做/例子/样例/演示/MVP/最小可行/简化版/demo）
  - 批量生成（批量生成/循环生成/批量创建/批量实现/模板生成/自动生成所有）— 格林主人禁令
  - 方案替换（替换为/改用/替代方案/变通）
  - 验证跳过（跳过验证/不验证/略过/不做测试/先不测）
  - 占位符（占位符/TODO/待实现/待补充/placeholder/FIXME/HACK）— 大小写不敏感
  - 负向声明防护：检测到"无任何/没有/不存在/杜绝了"等否定词时跳过匹配
  - 兜底策略：1个以上问题→block_and_escalate

### 6. 7层权限系统

`security.py` 实现文档§6：

- L1: Trust Dialog — 会话级信任
- L2: Permission Mode — default/plan/acceptEdits
- L3: Pattern Match — allow/deny/ask规则
- L4: ML Classifier — 工具风险+路径风险+高危模式
- L5: Command Validation — 静态检查（sudo/管道bash/重定向设备/rm根目录）
- L6: Sandbox Isolation — 高风险操作沙箱检查
- L7: User Confirmation — 最终兜底 + 15分钟临时凭证

## 使用方式

### 在对话中调用

```python
# 检查当前是否有中断任务
python3 ~/.hermes/production_loop/engine.py resume

# 查看运行状态
python3 ~/.hermes/production_loop/engine.py status

# 检查点健康
python3 ~/.hermes/production_loop/engine.py check
```

### 降级检测（最常用功能）

```python
from production_loop.verification import DegradationPreventer

preventer = DegradationPreventer()
result = await preventer.check_for_degradation(
    {"output": "输出文本"},
    "原始目标",
    success_criteria_list  # 可选
)
if result["degraded"]:
    # 检测到降级实现
    print(result["issues"])
```

### Critic审查

```python
from production_loop.agent_committee import CriticAgent

critic = CriticAgent()
review = await critic.review_execution(task_dict, execution_trace)
for issue in review["issues"]:
    print(f"问题: {issue}")
```

## 集成点

- **SOUL.md**: 已注册G8-PROD齿轮（§零外挂保障表）
- **AGENTS.md**: 已写入8条强化规则
- **齿轮系统**: 不干扰G0-G7，作为可选增强层（G8）
- **cron**: production-loop-check 每10分钟
- **记忆**: 已持久化到memory
- **Dynamic Workflows G6集成**: `workflows/gear_integration.py`中的`run_validator()`通过delegate_task调用验证器检查workflow执行质量（完整性/正确性/一致性/质量四维度）。验证结果写入gear_vault凭证链。对接位置：runtime.py正在执行finally块（已完成状态检查）。

## 坑

- 降级检测不要对目标关键词做覆盖度检查——短文本场景下误报率高。改用关键词匹配（只检查降级关键词是否出现）
- production_loop与齿轮系统各自独立运行，互不依赖
- LoopState的异步主循环需要llm_caller回调才能完整工作；同步场景下使用SimpleLoopExecutor
- check_for_degradation是async函数，调用时用await
- 权限系统L7的用户确认需要交互式支持，纯cron场景下自动跳过

### 🔴 死声明陷阱（2026-06-12 实战）

SOUL.md 中声明了 `force_compressor` 插件（"pre_context_load + post_tool_call 双hook"），
但实际不存在对应文件。这种现象（**声明了但没构建**）比降级实现更隐蔽：

降级实现至少写了代码（虽然假装实现），死声明连代码都没有。

**检测方法**：
1. 对SOUL.md/AGENTS.md中的每个声明能力，找对应的 `.py` 文件
2. 对每个文件路径，`test -f` 确认存在
3. 对每个文件，确认它被至少一条 import/调用路径引用（不是死文件）
4. 对每个被引用的模块，确认它被 `agent_enhancement_manager._try_load()` 的 safe_hook 调用

**2026-06-12 修复**：新建 `scripts/force_compressor.py` (10.9KB)，
实现 L1 差分/L2 统计/L3 归档 + SHA256 校验和验证。

详细方法论：`references/dead-declaration-detection.md`

### 4级穿透检查法

| 级别 | 检查 | 方法 | 判定 |
|------|------|------|------|
| L1 | 文件存在 | `test -f <path>` | 通过=文件在磁盘上 |
| L2 | 被导入/引用 | `grep -rn 'import\|from.*import'` | 通过=至少1个其他文件引用它 |
| L3 | 被拦截链调用 | 追踪agent_enhancement_manager._try_load() / tool_executor / conversation_loop / run_agent 的执行路径 | 通过=有至少1条执行路径 |
| L4 | 真实产生可观测输出 | 验证日志文件/状态文件/实际修改 | 通过=能在日志中找到执行记录 |

### 深度审计：工具调用链的假实现检测（2026-06-12 实战）

本会话中发现的6个死声明/假实现及修复：

| 问题 | 位置 | 修复方式 |
|------|------|----------|
| `query_llm()` 用硬编码 `Bearer ***` | forced_executor.py:149 | 改为从config.yaml读取真实api_key |
| `query_llm` 函数双重定义 | forced_executor.py | 去除重复定义 |
| `post_conversation_hook` 双重定义 | rule_enforcer.py | 保留第一个功能完整的，删除重复的 |
| R9 DualModelEnforcer 从未被拦截入口调用 | rule_enforcer.py | 集成到post_response_intercept |
| R11 IterationEnforcer 从未被拦截入口调用 | rule_enforcer.py | 集成到post_response_intercept |
| R8 AccountabilityEnforcer 无外部调用者 | rule_enforcer.py | 集成到post_response_intercept自动触发 |
| battle_commander中的18个武器全部指向真实文件，Weapon.fire()真实subprocess.run | battle_commander.py | ✅ 已验证，不需要修复 |
| forced_executor中的execute_plan()真实subprocess.run武器脚本 | forced_executor.py | ✅ 已验证包含完整阶段调度+并行执行+超时处理 |

## 🔴 反幻觉铁律：禁止假装实现（2026-06-10 格林主人最高指令）

本会话中发现的致命反模式：

### 反模式1: "功能声明 ≠ 功能实现"
**症状**: 写了`<button onclick="createRequirement()">`但函数是空的或只剩alert/prompt。
**根因**: 先搭框架承诺"后面补逻辑"——后面永远不会补。
**修复**: 任何UI交互必须从真实API调用开始写。API不存在就先建API再建UI。

### 反模式2: "返回静态JSON = 假装有API"
**症状**: routes_extended.py中16个POST端点有15个`return {"success": True, "data": {**data}}`——只返回用户输入，不调引擎。
**根因**: 先静态占位确认接口格式，然后"忘了回来改"。
**修复**: 每个API端点创建时必须调真实引擎。不能先占位再"后面补"。

### 反模式3: "前端画布 = 纯静态展示"
**症状**: 前端看起来有节点/连线/执行按钮，但拖不动/加不了/点不动。HTML是纯CSS展示。
**根因**: 认为"后端是真的就行，前端展示一下"——双重标准。
**修复**: 前端交互首次提交就必须真实实现。不允许先展示版再加强。

### 反模式4: "算子注册了 = 算子实现了"
**症状**: operators_lib.py注册了44个算子，全部`run()`默认返回`data`——什么都不做。
**根因**: 注册元信息被误认为等于功能实现。
**修复**: 关键算子(null_filter/dedup/html_cleaner)必须在注册时就有真实逻辑。

### 反模式5: "引擎写好了 = 引擎被调用了"
**症状**: 26个引擎全部可import，但HTTP层16个端点中15个不调用它们。
**根因**: 审核只看import能否成功，不看调用链路。
**修复**: 审核必须追踪完整调用链：HTTP端点→引擎构造→方法调用→返回数据。

## 🔴 审核实操规则（格林主人 2026-06-10 固化）
1. **读+跑=真正审核** — 只读不跑=无效。grep比阅读更有效。
2. **跨文件链路追踪** — 前端button→JS函数→API端点→引擎方法，每环必须存在且匹配。
3. **真实运行验证** — curl测试端点，python3 -c测试引擎import，记录每个问题。
4. **严重性分级** — ⛔阻塞 🔴高(静态mock) 🟡中(参数名) 🟢低(拼写)
5. **不通过必须修复** — 高严重性问题修复后重新审，不能"标记一下后面改"。

## 🔴 格林主人强制工作流（融入引擎）

每次执行任务时必须按此序列——这是降级检测之外的第二层保障：

1. **全面历史回顾 + 全局预判**: 读相关文件/日志/记忆/技能，不做"先回一个试试看"
2. **分阶段拆解**: 大任务→阶段/步骤/方向，逐步执行
3. **每阶段阶段性复盘**: 确认方向不跑偏
4. **完整后全局复盘**: 确认所有要求满足 — **必须调用`hermes_retrospect.py`复盘引擎进行结构化复盘**
5. **深度自检**: 所有功能必须真实实现，严禁降级/模拟/占位符
6. **循环完善**: "完善优化→商用级代码审核→商用级测试→再完善"循环
7. **中断自动恢复**: 中断→自动拆解继续→高质量实现→回顾历史文档→继续执行

## 🔴 执行质量墙（2026-05-31 格林主人最高指令）

任务执行过程中必须插入强制检查点，规则已固化到AGENTS.md：

**1. 每步检查** — 每完成一个子任务，验证输出是否符合预期
- 检查方法：运行验证脚本、检查输出文件、对比预期结果
- 失败处理：记录错误→分析根因→修正→重试

**2. 里程碑检查** — 每3个子任务，检查整体方向是否正确
- 检查内容：当前进度 vs 原始规划、是否偏离目标
- 失败处理：re-plan（调整后续步骤计划）
- 推荐使用 `writing-plans` skill的复杂性评估选择合适策略

**3. 方向对齐** — 任务中途检查是否偏离原始目标（复杂任务必做）
- 检查时机：任务30%/50%/70%进度节点
- 检查方法：重新阅读原始需求，对比已完成工作和剩余工作
- 失败处理：调整策略或重新规划

这些检查与 production_loop 中的 StepVerifier 和 CriticAgent 互补：
- StepVerifier 覆盖"每步检查"的技术验证层
- CriticAgent 覆盖"里程碑检查"的策略验证层
- 质量墙的"方向对齐"是 CriticAgent 的三层反思中"目标层反思"的强化版

## 🔴 三层反思结构化规则（2026-05-31 格林主人最高指令）

任务执行中必须进行结构化反思，按三层递进（规则已固化到AGENTS.md）：

1. **操作层**（每步后）：这一步做得对不对？结果是否符合预期？
   - 由 StepVerifier 覆盖：post_action_page_check + consecutive_failure
   
2. **策略层**（每3步后）：当前策略是否有效？是否需要换方法？
   - 由 CriticAgent 覆盖：策略层反思 + 5-Why根因分析
   
3. **目标层**（每10步后）：整体方向是否正确？是否需要重新规划？
   - 由 CriticAgent 覆盖：目标层反思 + DAG任务图重排序

这三层反思与执行质量墙互补：质量墙的"每步/每3步/中途"是检查时机，三层反思是检查方法。

## 🔴 上下文截断自动拆解规则（格林主人最高指令 2026-05-31 固化）

**⚠️ 2026-06-02 实战追加：无感分段，别说理由**

格林主人在本会话中连续质问"为什么不会拆解任务继续执行？？？有强化这个能力啊！！！"
这意味着:
1. **不能等他说才分段** — 当输出明显超长时，自动化拆解，不要解释为什么拆
2. **不要写"由于输出限制，我先分N段输出"** — 直接分段，别说"由于限制"
3. **不要问"要继续吗"** — 自然断点停，下一轮自动从断点继续
4. **每段保持高质量** — 分段≠降级，每段依然是完整代码/完整逻辑

**实战案例（本会话被骂的）:**
- ❌ 输出写到一半卡住，说"内容太长，我分步输出" → 被骂
- ✅ 直接写第1段（完整的类定义+方法声明），停 → 下一段从下一个类继续
- ❌ 写了"我将分批次修改，第一批先..." → 被骂"废话太多"
- ✅ 直接开始写第一批代码，写到自然断点停

当输出即将/已被截断（token超限/字数超长/上下文溢出）时：

当输出即将/已被截断（token超限/字数超长/上下文溢出）时：
- **立即将输出拆分成N个独立小段**，不要试图一次性输出完
- 第一段输出结论+已完成部分；后续段逐步输出细节
- 拆分策略：按逻辑边界（文件写完→验证→下一文件→验证）
- **禁止让整段输出被截断**——截断=用户看不到完整个任务结果

对话过长时：
- 主动说"内容过多，我分3步输出：第一步先确认方向，第二步给具体代码，第三步验证"
- 每输出一段后等用户响应，再继续下一段

与执行质量墙配合：每步检查后输出该步结果，不攒到全部完成再输出。

## 姊妹系统

- `goal-hive-orchestrator` — Goal Hive蜂群协作模式（Master+多Worker+BBS+预算驱动验收）  
  PRE的DegradationPreventer作为Goal Hive的验收防线，CriticAgent作为Master的第三方验证。
  
- `hermes-capability-inventory-weapons-arsenal` — 武器强制调用协议

本引擎专注于**检测**和**恢复** (DegradationPreventer/CriticAgent/三层反思).

姊妹系统 `hermes-capability-inventory-weapons-arsenal` 的 v3.1 通过 `agent_enhancement_manager.py` 插件矩阵 + `run_agent.py` 系统底层注入实现**预防**:
- 在LLM回答之前自动执行武器, 不让LLM有机会降级
- 强制≥3个武器同时执行, 强制≥3个阶段深度分解
- 执行结果直接注入system prompt, LLM只能基于真实结果做总结
- **关键架构差异**: 不是通过print日志或prompt规则, 而是通过修改run_agent.py对话循环注入2个安全钩子

两者协作:
```
预防层(agent_enhancement_manager.py → forced_executor): 在LLM回答前自动执行武器 → 不让降级发生
检测层(production_loop): 执行后扫描结果关键词 → 发现降级
性能看板(production_loop cron): 定期审计 → 发现趋势性问题
```

**2026-06-01重大变更**: 插件矩阵架构将16个增强模块统一管理。force_executor只是其中之一。
架构详情见 `hermes-capability-inventory-weapons-arsenal` skill 的"插件矩阵架构"章节。

任务执行完成后，必须调用复盘引擎进行结构复盘，而不是仅凭自主反思：

```python
# 任务完成后的强制复盘
from scripts.hermes_retrospect import inline_after_task

inline_after_task({
    "task_id": task_id,
    "title": task_title,
    "steps": execution_trace,
    "model": model_name,
    "started_at": start_time,
    "tokens_used": token_count,
})
```

复盘结果自动:
- 五维度质量评分（功能性/正确性/完整性/质量/可维护性）
- 存入state.db retrospectives表
- 低于60分自动写入进化候选队列 → 次日自进化集群消费

## 🔗 安全护栏集成（CaMeL）

CaMeL Guard 已集成到 production_loop_cron.py，每10分钟自动执行安全检查：

### 每10分钟（run_check → run_camel_check）
```python
def run_camel_check():
    \"\"\"读取 camel_guard.log 最近50条，统计注入事件和敏感工具调用\"\"\"
    # 输出: {injection_events, sensitive_tools_called, status}
    # 写入 production_loop_audit.json 的 camel_guard 字段
```

审计快照中的CaMeL部分：
```json
{
  "timestamp": "...",
  "unfinished_tasks": 3,
  "camel_guard": {
    "injection_events": 0,
    "sensitive_tools_called": [],
    "status": "safe"
  }
}
```

### 每30分钟（run_critic）
Critic审查报告包含CaMeL安全检查结果，可发现安全事件增长趋势。

### 每2小时（run_deep_check）
深度验证检查 `camel_guard.py` 脚本和 `camel_guard.log` 文件的完整性。

### 三级模式
- `off` — production_loop不检查CaMeL日志
- `monitor` — 读取日志，报告但不告警（默认）
- `enforce` — 检测到注入事件时触发Critic告警

## 🔴 SkillOpt验证门集成

使用 `scripts/skillopt_trainer.py` 在每次系统组件修改时应用验证门：

```python
from scripts.skillopt_trainer import SkillOptTrainer
trainer = SkillOptTrainer()

# 文本学习率：每次最多改3条规则
result = trainer.validate_skill("组件名", test_count=3)
if result["passed"]:
    print(f"验证通过: {result['score']:.2f}")
else:
    trainer.add_to_reject_buffer("组件名", 旧内容, 新内容, 
        f"验证门: {result['score']:.2f}<{result['threshold']:.2f}")
```

### 负迁移检测（每30天执行）
```bash
python3 scripts/skillopt_trainer.py risks   # 扫描负迁移风险
python3 scripts/skillopt_trainer.py stats   # 验证统计
```

## 关联技能

- `dual-ai-review` — 双AI互审系统，所有生产执行必须受互审监督
- `gear-context-compression` — G3齿轮上下文压缩强化的前提
- `task-auto-resume` — 任务自动恢复（与production_loop_resume配合）
- `hermes-self-enhancement` — 自我强化增强（CriticAgent输出的反思可触发进化）

## 参考文件

- `references/degradation-keywords.md` — 40个降级关键词完整清单（5分类）
- `references/full-backup-procedure.md` — 全系统备份流程（27545文件/525MB/含SHA256校验）

## 回滚方案
### 快速回滚
如果部署后发现问题：
1. 使用版本控制回退到上一个提交：`git revert HEAD`
2. 确认回滚后系统状态正常
3. 通知相关方变更已撤销

### 数据安全
- 所有修改前确认有备份
- 配置变更记录版本历史
