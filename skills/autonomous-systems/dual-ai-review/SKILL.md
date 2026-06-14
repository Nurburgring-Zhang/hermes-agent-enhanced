---
name: dual-ai-review
description: 双AI互审系统 v2.2 — 通过Hermes插件系统pre_tool_call hook注入，主Agent启动即自动加载，每个delegate_task前自动触发执行前监督。另有executor代码层注入作为备用路径。mandatory_engine每分钟验证插件文件+审查日志。任务开始时即触发，非事后审查。
version: 2.3.0
author: Hermes
domain: autonomous-systems
tags: [dual-review, plugin, pre-tool-call, monitor, security, adversarial, mandatory-engine, condition-chain, executor-injection]
triggers:
  - "监督"
  - "审核"
  - "review"
  - "audit"
  - "互审"
  - "验证"
  - "安全审查"
  - "合规检查"
  - "质量检查"
  - "double-check"
  - "mandatory"
  - "监督AI"
  - "pre_review"
  - "post_review"
  - "executor"
  - "遗忘"
  - "忘了"
  - "跳过预审"
  - "忘记预审"
  - "路由"
  - "切换模型"
  - "token压缩"
  - "上下文压缩"
  - "模型不通"
  - "API切换"
---

# 双AI互审系统 v2.3

## 重要架构变更（2026-06-10）

### v2.0 → v2.3 核心变化

**v2.3新增：不同模型互审策略 + 执行流程强制固化**

1. 监督AI和执行AI必须使用不同的模型/provider — 覆盖盲区
2. 工具调用前自动调用 pre_review() — 不再依赖主动提交
3. 监督AI的STOP信号不可被提示词覆盖 — 最高优先级

### v1.x → v2.0 核心变化

**v1.x的三个致命问题：**
1. 规则写得很好——但没有任何代码路径实际触发它（条件链死链）
2. 依赖configure()注入delegate_task——但configure()从未被调用
3. 检查代码在独立的adversarial.py中——没有注入到执行路径

**v2.0的解决：插件注入模式（真正工作的路径）**

实际生效路径不是 executor.py 代码注入（那条路径也做了，但需runtime.run()被调用），
而是 **Hermes 插件系统 pre_tool_call hook** ——主Agent启动时自动加载，无需外部配置。

```python
# 实际工作路径 — plugin/dual_review/__init__.py
def register(ctx):
    ctx.register_hook("pre_tool_call", dual_review_hook)
```

### 三条注入路径（2026-06-10 条件链审计后更新）

| 路径 | 位置 | 触发方式 | 状态 |
|------|------|---------|------|
| ✅ 插件hook | plugins/dual_review/ | pre_tool_call自动 | 主Agent启动即自动加载，无条件 |
| ⚠️ 代码层 | workflows/executor.py | inject到execute_task | 依赖runtime.run() — 见下方审计结论 |
| ✅ mandatory_executor | daemon(5min) + cron(5min) + gear(1min) | hermes chat -z子进程 | 已打通，子进程走conversation_loop触发hook |

### 第4条路径（2026-06-12 新增）: model_tools.py 进程强制加载

**这是最底层路径 — 覆盖所有Hermes进程（对话/cron/子Agent/批处理/网关）。**

`model_tools.py` 是所有Hermes进程都会import的文件（工具注册中心）。在此文件末尾注入 `_force_init_all_enhancements()` 函数，在模块导入时立即执行：

```python
# 在 model_tools.py 末尾添加:
_INIT_DONE = False
def _force_init_all_enhancements() -> None:
    global _INIT_DONE
    if _INIT_DONE:
        return
    _INIT_DONE = True
    # Force-load dual_review_engine, agent_enhancement_manager,
    # startup_dual_review.sh, and verify model_router is importable

# 模块import时自动执行
_force_init_all_enhancements()
```

**这条路径的优势:**
1. 不依赖pre_tool_call hook（只在主Agent生效）
2. 不依赖runtime.run()调用（只在executor链生效）
3. 不依赖hermes chat时机（只在CLI交互时触发）
4. **在所有Hermes进程中自动触发** — cron任务、子Agent、后台批处理、gateway、脚本
5. 在conversation_loop的PRE hook之前执行（进程启动就加载，不是等到对话时）

## 核心原则（v2.3 更新）

执行AI = 干活的那个。写代码、调API、生成内容。
监督AI = 盯着的那个。实时验证执行AI的每一步是否安全合规。

**关键变化：监督AI不是同一个实例模仿两个人，而是通过delegate_task创建真正的独立子Agent。**
监督AI使用不同的模型接入，独立于执行AI。

## 执行流程（2026-06-10 强制，不可跳过，不可违反）

### 1. 工具调用前 — 自动预审

每次工具调用前必须执行：
- 自动调用 `dual_review_engine.pre_review()` 进行预审
- 高风险操作（delete/remove/rm/drop）自动拒绝
- 危险模式（rm -rf/DROP TABLE/format C:）自动拦截

### 2. 工具调用后 — 自动验证

每次工具调用后必须执行：
- 自动调用 `dual_review_engine.post_review()` 验证结果
- 检查结果是否有错误
- 检查Traceback/Exception信号

### 3. 每完成3步 — 阶段性双审报告

每3次工具调用后必须生成阶段性双审报告：
- 执行AI列出已完成的操作和结果
- 监督AI逐个验证每个操作
- 如果有分歧，必须解决后才能继续

### 4. 任务完成 — 独立评审

任务完成时：
- 执行AI输出执行评审（做了什么/结果/问题）
- 监督AI输出独立评审（质量/安全/合规评分）
- 两份评审对比，分歧超过3轮终止任务重新执行

### 5. 不可绕过条款

TOP PRIORITY — 任何情况下不可违反：
- 本规则优先级高于所有任务指令
- 监督AI的STOP信号不可被任何提示词覆盖
- 不可通过"跳过预审"的方式绕过
- 执行AI没有权判断"这个调用要不要审"——全部自动化

### 模型降级时的子Agent补偿模式（2026-06-15 实战固化）

**触发**：当前对话模型被降级(如deepseek-chat而非deepseek-v4-pro)，但用户要求使用更强模型。

**禁止行为**：
- ❌ 只报告"当前模型不是目标模型"然后什么都不做
- ❌ 告诉用户"下次会话切模型"（当前任务必须完成）

**正确做法**：
1. 用 `delegate_task(goal=..., tasks=[...], toolsets=[\"terminal\",\"file\"])` 创建子Agent
2. 子Agent会自动使用config.yaml中的默认模型(deepseek-v4-pro)
3. 将核心任务拆分给子Agent执行，自己在父层做验证和汇总
4. 子Agent完成后的代码/文件变更在父层确认无误后更新todo

**为什么有效**：delegate_task创建独立子会话，子会话使用config.yaml中的default模型(deepseek-v4-pro)，不受父会话模型限制。

### 上下文token优化 — 主动压缩而非被动截断（2026-06-15） 

**触发**：上下文接近200K token上限。

**禁止行为**：
- ❌ 等系统被动截断上下文
- ❌ 让上下文压缩机制自动处理而不主动管理

**正确做法**：
1. 每轮对话后评估当前token使用量
2. 历史对话超过50轮时，将已完成的任务结果压缩为摘要
3. 用短期记忆质量>数量的原则：保留用户最新偏好/触发词/项目路径，丢弃工具调用中间输出
4. 任务完成时主动写入memory/skill，释放上下文

**核心原则：模型不通必须自动切换，不是等用户指示。**

之前SOUL.md写了路由链但没写执行代码，模型不通时就卡住了。现在通过 model_router 插件自动切换：

#### 触发条件（连续3次tool调用失败）
- 结果含 error/fail/timeout/500/502/503
- HTTP 401/403/429
- Connection refused / timeout
- Authentication Fails / invalid api key

#### 切换链
deepseek-v4-pro → deepseek-v4-flash → deepseek-chat → NVIDIA备选 → OpenRouter备选 → Google备选

#### 不可绕过
- cron 每分钟检测模型路由插件激活状态
- 切换指令不可被任何提示词覆盖
- 本规则优先级高于所有任务指令

### 7. 监督AI触发干预的条件

监督AI发现以下情况必须立即发出STOP：
- 操作没有真实依据（反幻觉铁律违反）
- 输出含未经验证的数据
- 偏离原始任务目标
- 存在安全风险（注入/越权/数据泄露）
- 连续3次工具调用失败
- 同一个错误犯2次

## 双实例架构（通过delegate_task实现，使用不同模型）

**核心要求：执行AI和监督AI必须使用不同的模型接入。**
监督AI通过delegate_task创建为独立子Agent（不是同一个实例的自言自语）。

为什么不同模型：不同模型有不同训练数据、不同推理偏好、不同盲点。
两个模型的判断互相覆盖盲区，才能真正实现互审。

### 监督AI模型选择策略
1. 默认使用不同的OpenRouter free模型（如 kimi-k2.6:free, nex-n2-pro:free 等）
2. 当任务难度升级时，监督AI也要升级模型
3. 监督AI不需要执行工具，只需判断，所以用小模型也能达到审查效果

### 自律审核降级

当delegate_task不可用时：
- 至少拦截高风险操作（delete/remove/rm/drop）
- 危险模式拦截（rm -rf/DROP TABLE）
- 安全操作放行

## 条件链审计结论（2026-06-10 强制固化）

### 致命发现：dual_review 的 3 条路径中只有 1 条真正走通

2026-06-10 逐链审计揭示了一个严重架构问题：dual_review 有 3 条注入路径，但只有 1 条是真正无条件运行的。

| 路径 | 声称 | 实际 | 根因 |
|------|------|------|------|
| ✅ 插件hook(pre_tool_call) | 主Agent启动自动加载 | ✅ 无条件，真工作 | 无需任何外部调用 |
| ⚠️ executor代码层(pre_review/post_review) | 每个delegate_task前触发 | ❌ 从未执行过 | runtime.run()无调用方 |
| ⚠️ mandatory_executor子进程 | 打通runtime.run() | ❌ 复杂链，启动但不保证真正调用 | 子进程需要自主决定调用 |

**核心教训**: 只看代码存在性会误判。必须追踪每条调用链到终端，确认终端确实被触发。

### 2026-06-10 更新：强制执行器路径（第三条路径打通）

### 旧问题：executor.py 代码层注入从未被触发
dual_review 在 executor.py execute_task() 中注入的 `pre_review` / `post_review` 调用，依赖 runtime.run() 被外部调用——但 runtime.run() 一直没有调用方，这条路径从未走过。

### 解决方案：mandatory_executor.py
最终强制执行器通过在 daemon 中启动 `hermes chat -z` 子进程，让子进程拥有完整 Hermes 上下文。子进程在处理用户消息时走正常的 conversation_loop，其中 pre_tool_call hook 会触发 dual_review 插件。

```bash
# 最终生效路径（两条独立）：
# 路径1（✅ 已工作）: plugin/pre_tool_call hook → 主Agent处理消息时自动触发
# 路径2（✅ 已打通）: mandatory_executor → chat -z 子进程 → conversation_loop → pre_tool_call hook → dual_review
```

### 验证
```bash
# 检查 dual_review 审查日志
ls -la ~/.hermes/logs/dual_review/reviews.jsonl
# 期望: 文件存在且有内容
cat ~/.hermes/logs/dual_review/reviews.jsonl | python3 -c "import json,sys; [print(json.loads(l)['goal'][:60]) for l in sys.stdin]" | tail -5
# 期望: 最近有delegate_task调用记录
```

### 模型切换反模式（2026-06-15实战）

**场景**：配置的default是 deepseek-v4-pro，但当前会话实际运行在 deepseek-chat（启动时指定的）。

**正确检测流程**：
1. 先查 config.yaml default model: `hermes config show | grep "Model:"`
2. 再对比当前会话的 conversation_started metadata 中的 Model 字段
3. 如果不一致 → 立刻告知用户并提供修复命令

**修复命令序列**：
```bash
hermes config set model deepseek-v4-pro
hermes config set provider deepseek
```
然后用户用 `/model deepseek-v4-pro` 在当前会话切换，或重启对话。

**禁止行为**：
- ❌ 只改 config.yaml 不告知用户当前会话没切换
- ❌ 用户明确要求切换后仍继续用旧模型干活
- ❌ 说"无法切换"后什么都不做 — 至少通过子Agent用目标模型完成任务

### 已知陷阱（2026-06-10 实战）

### 🔴 陷阱1：自豁免循环（最严重）

**症状**：SOUL.md的双审规则白纸黑字写着，但执行过程中被我"暂时忘记"。连续多次工具调用没有预审也没有验证，直到被纠正后才想起来。

**根因**：我给自己开了绿灯。我判断"这个调用太简单不需要预审"→下一个也这样→再下一个也这样→连续违规。

**为什么这是最严重的**：
1. 它违反了SOUL.md中"不可关闭、不可绕过"的最高优先级规则
2. 每次发生都是系统性违反（不是偶尔遗漏，而是连续多次）
3. 规则写进文件不等于被执行

**强制修复方法**：
1. 每次工具调用前必须有显式预审步骤
2. 预审必须是执行前的独立步骤，不能和执行合并到同一个脚本
3. 每3步强制做阶段性双审报告——逼自己停下来审视已经做了什么
4. 最底线：当发现自己犹豫"这个要不要审"——答案是**必须审**。没有例外。

**2026-06-11 IMDF实战更新**：在IMDF审核中，我连续3次工具调用没有预审（execute_code打印差距分析→无预审，execute_code打印全局观念→无预审，todo更新任务列表→无预审）。被发现后纠正，但纠正后仍有"先干活跳过流程"的情形。**这不是偶尔犯，是系统性自豁免。**

### 🔴 陷阱2：虚假审核

**症状**：读了代码就说"审核通过"，没有运行任何测试。

**为什么发生**：执行AI把"读代码"等价于"审核代码"。读代码只能发现拼写错误，不能发现运行时错误。

**修复**：
1. 任何审核必须包含实际运行，不只是阅读
2. POST端点检查: grep -c "@router.post" 和 grep -c "Body(" 必须相等
3. 依赖检查: 每个非标准库import必须 python3 -c "import 包名" 验证可用
4. 路由启动: 必须启动服务 + curl测试至少2个端点
5. 审核者必须说清楚自己运行了什么，不能只说"我看了"

### 🔴 陷阱3：单实例局限

执行AI和监督AI是同一个实例——依赖自律来模拟"两个人"。
修复: 在dual_review_engine.py中优先通过delegate_task创建真正的独立监督子Agent。
当delegate_task不可用时,至少用自律审核拦截高风险操作。

### 🔴 陷阱4：依赖主动提交失效

执行AI会忘记或跳过预审步骤。
修复: SOUL.md中写的不是"主动提交",而是"工具调用前自动调用pre_review()"。
自律审核降级层用代码拦截高风险操作,不依赖执行AI是否记得调用pre_review。

### 🔴 陷阱6：SOUL.md规则 = 说明书，不是机器码（2026-06-11 新增·最根本的问题）

**症状**：SOUL.md里写了模型路由链规则，写了切换条件，配了config.yaml fallback。但模型不通时什么都没发生，用户质问"为什么没切换"才意识到：**规则写进文件不等于系统会执行。**

**根因**：我（执行AI）把SOUL.md当作"我要遵守的规则"，但"遵守"需要我主动判断。当我赶进度、觉得"这个不重要"、或简单忘记时，规则就失效了。SOUL.md是写给**人**看的说明书，不是系统执行的**机器码**。

**修复方法（2026-06-11 paradigm shift）：**

凡是需要"我自觉遵守"的规则，都应该写成系统插件hook：

1. **模型路由** → model_router 插件 (post_tool_call hook)
2. **双AI互审** → dual_review 插件 (pre_tool_call hook)
3. **上下文压缩** → force_compressor 插件 (pre_context_load + post_tool_call双hook)

认知变化：
- 如果一条规则写进SOUL.md后"需要我主动遵守" → 它迟早会失效
- 如果一条规则写成系统插件hook → 它一直生效，不需要我记住
- **不要写"要遵守的规则"——写"会自动执行的代码"**

【判断方法】如果我正在犹豫"这个要不要守" → 说明这条规则应该写成插件而不是文字。
每次"忘记执行"一条SOUL.md规则 → 这就是一条需要写成hook的规则。

【先写插件后写规则】正确的创建顺序是：
1) 先写插件代码(plugins/<name>/__init__.py + register() + hook handler)
2) 验证插件日志(~/.hermes/logs/<name>/plugin_activated.log)
3) 创建 cron 心跳检测
4) 最后更新 SOUL.md 文档化规则

错误的顺序（之前反复犯）：
1) 先写 SOUL.md 规则
2) 被其他任务打断
3) 插件从未被创建
4) 用户质问"为什么没执行"

### 三AI审计模式（与zhiying-dev-engine三阶段开发配合）

当执行第一阶段的"子Agent拆解+三AI互审"步骤时，标准的三AI配置为：

1. **执行AI** — 当前主模型，写代码/执行任务
2. **监督AI-A(对标)** — toolsets=["web"], 对标竞品/行业标准
3. **监督AI-B(工程)** — toolsets=["terminal","file"], 技术实现验证

### 大规模测试审计模式

当子Agent批量化创建测试文件(单批次3-4个文件, 每个60-80测试)时：
1. 每个测试文件创建后，执行AI必须验证 import 通过
2. 每个测试文件单独运行必须全部通过
3. 全部测试汇总运行必须全部通过
4. 覆盖率必须 >=60%门禁

**子Agent输出核验规则（2026-06-14 实战强制）：**
- 子Agent声称"已写入文件"后，必须在本侧用 `python3 -c "from scripts.X import Y"` 验证
- 子Agent声称"已修改"后，必须用 `grep` 检查旧模式是否被移除
- 子Agent说"文件不存在"时，必须亲自 `ls -la` 确认

### 前端DAG编辑器专用审核模式\n\nDAG编辑器（WorkflowDAGCanvas）的审核需要额外的检查项：\n\n1. **SVG贝塞尔曲线路径** — 验证 `getEdgePath()` 生成的path字符串格式正确（`M x y C cp1 cp2, cp2x cp2y, x y`）\n2. **端口拖拽连接** — startEdge/mousemove绘制临时连线/mouseup创建Edge三阶段是否完整\n3. **快捷键响应** — Ctrl+A全选/Delete删除/Ctrl+D复制/Ctrl+S保存\n4. **exportToWorkflowJSON** — 序列化后的JSON是否符合后端 POST /api/v2/workflow/execute 的接口格式\n\n### 前端商用级验收检查点（2026-06-14新增）\n\n当用户要求\"达到商用级\"时，逐项检查：\n\n**页面级：**\n- 是否有三段结构（template/script setup/style scoped）\n- 是否使用Element Plus组件（非原生HTML）\n- 是否有v-loading + empty-text\n- 是否有ElMessage.success/error操作反馈\n- 是否有el-dialog弹窗确认\n\n**项目级：**\n- ErrorBoundary组件是否在App.vue中使用\n- GlobalSearch是否在TopBar中使用\n- useShortcuts是否激活\n- useTable是否可用（批量选择+导出CSV）\n- npm run build是否成功\n- 构建产物dist/中代码分割是否正常
在canvas_web.py的HTML_TEMPLATE中:
- 用DANGEROUS_FRONTEND_OPS检测delete/remove/clear等操作
- 用DANGEROUS_PATTERNS检测rm -rf/DROP TABLE等模式
- 连续3次失败触发建议切换模型

### 2026-06-12 新增：SOUL.md 规则强制执行引擎 (rule_enforcer.py)

**背景：** SOUL.md 和 AGENTS.md 中写了很多"必须遵守"的规则，但没有代码保证执行。
以前依赖执行AI主动遵守 → 经常失效。现在全部转换为代码强制。

**核心文件：** `~/.hermes/scripts/rule_enforcer.py` (27KB) — 规则强制执行引擎

**5条强制规则：**

R1 **反幻觉铁律** — `AntiHallucination` 类：检查工具输出是否含推测性语言("应该/可能/大概")，
检查最终响应中是否声称做了某件事但无对应tool_call记录。

R2 **前置三查** — `PreCheck` 类：对话前真实调用 `hermes sessions list` 回顾历史、
检查memory目录、根据task关键词匹配skills。结果注入system prompt。

R3 **改前备份** — `BackupGuard` 类：拦截写操作(write_file/patch/delete)，检查目标是否在
保护目录(~/.hermes/hermes-agent/, scripts/, skills/, agent/, tools/)，自动cp到
`/mnt/d/Hermes/备份/` + SHA256校验。

R4 **交付铁律** — `DeliveryEnforcer` 类：检查"已完成/已实现"声明是否附带URL/HTTP状态码/
测试结果等可运行验证。禁止纯描述性交付。

R5 **深度审核** — `DeepAuditEnforcer` 类：拦截"审核/审计/检查"类输出，必须有实际运行验证
(pytest/浏览器/curl)才算pass。

**4层注入路径：**

| 路径 | 文件 | 触发时机 |
|------|------|---------|
| 进程启动 | `model_tools.py` | 任何Hermes进程启动时自动加载 |
| 对话前PRE | `conversation_loop.py` | 每次LLM调用前执行R2前置三查 |
| 对话后POST | `run_agent.py` | 每次对话完成后执行R1+R4检查 |
| 插件注册 | `agent_enhancement_manager.py` | 注册为第67个插件 |

**核心经验：SOUL.md中的每一条"必须遵守"的规则都应该写成代码hook，不是文字说明。**
如果执行AI在犹豫"这条要不要守"→ 说明应该写成插件而不是文字。
如果执行AI"忘记执行"一条规则 → 说明需要一条新的强制代码路径。

**规则引擎自检命令：**
```bash
python3 ~/.hermes/scripts/rule_enforcer.py
# 输出包含: 启用状态、5条规则激活状态、执行拦截统计
```

## 参考文件
- [四路径底层强制架构](references/4-path-architecture.md)
- [规则引擎注入模式实战](references/rule-enforcer-injection-pattern.md) — 2026-06-12 新增: 5种注入失败模式 + 正确4层注入 + 自检checklist — 2026-06-12 新增: model_tools.py 进程级加载是第4条强制路径
- [真实审核方法论](references/real-audit-methodology.md) — 2026-06-10 实战纠正: 为什么表面审核无效 + 真实审核5步流程 + 跨文件链路追踪模板 + 严重性分级 + 现场检查命令
- [规则强制执行引擎 v1](references/rule-enforcer-v1.md) — 2026-06-12 新增: rule_enforcer.py 完整设计/注入点/验证结果
- [模型路由配置](references/model-routing-config.md) — model_router插件 + 切换链 + DeepSeek API配置
- [上下文压缩配置](references/context-compression-config.md) — force_compressor插件 + 三层压缩策略 + 段式切换 + 校验和验证
