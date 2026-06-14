---
name: zhiying-dev-engine
description: 三阶段开发铁律(R14代码强制)—S1规划执行(9步)/S2对标升级(≥3轮)/S3全功能审核(多轮修复)。替代原7步SDLC。每次开发必须按三阶段依次执行不可跳过。
---

# 智影开发引擎 — 三阶段开发铁律(R14) + 三AI互审

## 重要说明（2026-06-12重大更新 — 三阶段开发铁律替代7步SDLC）

**三阶段开发铁律已通过R14写入rule_enforcer.py代码级强制（商用级，不是关键词检测）。**
这意味着：
- **pre_tool级别拦截** — 第一阶段未完成时delegate_task被直接block（非规划类），不是事后警告
- **真实产出证据检查** — 声称阶段完成必须有文件路径/HTTP状态码/测试通过等实际证据，不是关键词匹配就放行
- **状态持久化** — 三阶段进度写入 `.phase_state.json`，跨会话保持
- 跳阶段（第一阶段未完成进入第二阶段）→ delegate_task被block（执行中断）
- 第二阶段不足3轮进入第三阶段 → delegate_task被block（执行中断）
- SOUL.md + rule_enforcer.py + .phase_state.json 三保险，不可绕过

**R14实现结构（rule_enforcer.py 1200+行新代码）：**
- `ThreePhaseDevEnforcer` 类 — 包含pre_tool_block/complete_step/advance_phase2_round/complete_phase3 等方法
- `_has_real_output_evidence()` — 真实证据检查（文件产出/运行结果/工具调用/状态码），取代旧的关键词扫描
- `complete_step()` — 只有真实产出证据才能标记某一步为完成
- 注入位: `pre_tool_intercept`（调用前阻断）+ `post_response_intercept`（每次响应后自动检测阶段进展并标记步骤）

**7步SDLC已被三阶段开发铁律替代。** 三阶段包含9+3+7共19小步，比7步更细、更严、更完整。

zhiying-dev-engine 是**每次开发任务必须遵循的执行流程**。不是"自动完成开发的引擎"。

## 何时使用

每次有新的开发任务时。包括：
- 新功能开发
- 系统改造
- Bug修复
- 功能迁移
- 用户说"继续开发"或"继续推进"或"继续审核优化完善"

**必须先 skill_view(name='zhiying-dev-engine') 加载此流程，然后按三阶段依次执行。不可并行、不可跳阶段、不可偷懒。**

## 全流程概览

```
第一阶段: 规划与执行（不可跳过，可迭代多轮）
  1.1 全网检索 — web_search + session_search + fact_store三路并行
  1.2 全局观念+技术方向设定
  1.3 开发计划+需求文档+开发文档
  1.4 拆分为多个子Agent并行任务
  1.5 每个子Agent按模型能力拆解为多阶段
  1.6 每阶段全程三AI互审互查互纠偏
  1.7 阶段性检查+与执行计划映证（防跑偏）
  1.8 所有阶段完成后的总体验证+与总规划映证
  1.9 可迭代多轮，必须完成整体开发
         ↓
第二阶段: 全面升级（至少3轮迭代，不可跳过）
  2.1 匹配全网相关软件/信息/项目/研究
  2.2 对标同方向最优最强最全面
  2.3 功能/能力/效果/交互所有方面全面升级开发
  2.4 开发完善方法参考第一阶段要求
  2.5 至少完成3轮迭代以达到最优
         ↓
第三阶段: 全功能审核测试（多轮迭代）
  3.1 全面的审核+测试+上线测试+功能测试
  3.2 每一个可执行操作的完整测试+交互测试+结果验证
  3.3 根据测试结果优化完善
  3.4 多轮迭代确保全部达到最优最强最完善
  3.5 自动校验+三AI互查互审互监督
  3.6 所有问题自动修复
  3.7 最终交付完整的项目成品
```

### 强制顺序（R14自动检测）
- 未完成第一阶段 → 禁止进入第二阶段（R14自动检测并警告）
- 未完成第二阶段3轮迭代 → 禁止进入第三阶段（R14自动检测并警告）

## 3AI互审互查模式（2026-06-12新增，2026-06-12实战更新）

对于大型改造任务（如商用级功能补齐、架构重塑、规则引擎构建），必须启动三AI互审互查。

### 关键陷阱：子Agent搜索范围漂移

**子Agent可能跑偏到错误的项目目录。** 实战中发现：当创建子Agent时给了"搜索范围"上下文，子Agent可能无视给定路径，自己去全局搜索同名的不同项目，然后输出不相关的文件分析。

**预防措施：**
- 子Agent的goal中必须包含**确切的项目根路径**（不是相对路径，不是描述）
- goal中明确写 "仅在 /mnt/d/Hermes/xxx 目录下工作"
- 多Agent的toolsets限制为 `["terminal","file"]`，避免它们自己开浏览器搜索
- 子Agent返回后，父Agent必须核对输出中的路径是否与目标一致

### 执行方式
1. 创建3个子Agent并行独立工作，各自输出报告
2. **架构视角Agent**: 功能树设计（维度节点→能力节点→功能节点三层结构），行业对标分析
3. **产品视角Agent**: 优先级分级(P0-P3)，依赖分析，每次功能标注"必须有vs锦上添花"
4. **工程视角Agent**: 技术实现方案，节点化工作流引擎架构，路由/API设计
5. 三份报告交叉验证，不一致处标记为"需人工决策"

### 商用级差距分析（84项功能对标）
在全网调研阶段，必须对标以下工业级平台的功能清单：
Scale AI / Labelbox / CVAT / Supervisely / Snorkel AI / FiftyOne(Voxel51) / Data-Juicer / Great Expectations
输出84+项功能的已有/缺失/部分对标表，按P0-P3分级。

### P0批量实施模式
对于P0项目，采用子Agent批量实施+逐个验证模式：
1. 同一个子Agent负责写入全部代码（避免多写冲突）
2. 全部写入后才启动服务做一次全链路验证
3. 验证失败则逐个排查而非重新全量写入

### 多子Agent冲突模式（2026-06-12/13 实战教训）

当多个子Agent并行修改同一个项目时，以下冲突模式反复出现：

**1. 同一文件重复定义**
- 不同子Agent可能都修改 `canvas_web.py`，产生重复的函数定义
- 解决方案：**每个文件只允许一个子Agent修改**，其他子Agent只能读

**2. 旧代码残留**
- 子Agent插入新函数后，旧版代码未被清理
- 解决方案：patch后必须 grep 检查是否有重复的函数定义

**3. HTML_TEMPLATE 串联覆盖**
- 子Agent A注入监控面板，子Agent B注入数据浏览器，子Agent C注入运营看板
- 每个注入都在同一个 r"""...""" 字符串的不同位置，但累积的花括号/注释问题导致整个script不执行
- 解决方案：**所有前端变更合并为一次写入**，或严格按顺序逐个验证后再交下一个

**4. 端口占用导致子进程用旧代码**
- fuser -k + sleep 1 + 新服务启动 — 如果旧进程没被杀干净，新进程可能绑定失败
- 解决方案：`pkill -f "python3 api/canvas_web"` 杀干净再启动，启动后检查 `/api/v1/health`

### JS语法保护措施：
- 修改HTML_TEMPLATE后必须验证花括号配对
- 禁止在 `const NT={...}` 对象内使用 `//` 注释（必须用 `/* ... */`）
- 禁止子Agent直接patch HTML_TEMPLATE — 只允许写出完整可靠的JS代码段后再一次性替换
- 验证序列：花括号配对检查 → 对象内//注释检查 → 关键函数存在检查 → node --check（有Node.js时）

### JS语法验证（Python字符串内嵌JS专用）

当HTML/CSS/JS嵌入在Python r"""...""" 字符串中时，Python编译检查不会发现JS语法错误。

**必须做：**
```python
# 用Node.js验证
import subprocess, tempfile
with tempfile.NamedTemporaryFile(suffix='.js', mode='w', delete=False) as f:
    f.write(js_code)
result = subprocess.run(['node', '--check', f.name], capture_output=True, text=True)
assert result.returncode == 0, f"JS语法错误: {result.stderr}"
```

**无Node.js时的替代方案：**
- 检查花括号/中括号/圆括号是否配对
- 检查对象字面量内是否有//注释（必须是/* */）
- 检查模板字符串(反引号)数量是否为偶数

## 前端JS嵌入在Python字符串中的语法验证（2026-06-12实战教训）

当HTML/CSS/JS嵌入在Python r"""...""" 多行字符串中时，Python编译器不检查JS语法。必须手动验证：

```python
# 1. 花括号配对检查
opens = js_code.count('{')
closes = js_code.count('}')
assert opens == closes, f"花括号不匹配: {opens}:{closes}"

# 2. 对象字面量内//注释检查
# const NT={...} 内的 // 注释会导致整个script块无法执行
# 必须用 /* ... */ 替代

# 3. 模板字符串配对检查
backticks = js_code.count('`')
assert backticks % 2 == 0, f"反引号(模板字符串)数量为奇数: {backticks}"
```

## 三AI互审使用不同模型

监督AI和执行AI必须使用不同模型接入：
- 执行AI = 当前主模型
- 监督AI = 不同的provider/模型
这样可以避免两个AI犯同样的错误，实现真正的不同视角互审。
当delegate_task可用时，监督AI使用不同的模型接入，独立于执行AI。

### 子Agent强制指定模型（2026-06-15实战）

当用户要求使用特定模型但当前上下文已被降级时：
1. **在delegate_task调用中显式指定模型**：`delegate_task(goal=..., model={"model":"deepseek-v4-pro","provider":"deepseek"})`
2. 如果自身模型已降级，**必须主动告知用户**，建议通过子Agent使用目标模型
3. 不要静默接受降级 — 用户对此愤怒

### 旧进程彻底清理（2026-06-15实战）

当端口被占用时，fuser -k可能杀不干净。必须用：
```bash
pkill -9 -f "python3 server.py"
sleep 3
fuser 8001/tcp 2>/dev/null || echo "free"
```
然后用background=true启动新进程，再通过process(action='wait', timeout=15)确认启动日志中有Application startup complete。

## 致命教训：禁止内联HTML — 必须使用独立前端文件（2026-06-13实战）

43833字符的HTML_TEMPLATE(r"""..."""字符串)被多轮子Agent注入破坏导致全部JS不执行。根因链: 子Agent注入→花括号不匹配→//注释在对象字面量内→sed删除破坏括号→execNode被重复覆盖3次。最终`typeof switchTab === undefined`。

**铁律：前端代码不得内联在Python字符串中。** 改用`frontend/index.html` + `frontend/js/pages/*.js`。

**PAGE_RENDERERS坑:** navigate()必须用`window[name]`动态查找，因为后续加载的JS覆盖的全局函数不会被缓存字典识别。

详见`references/inline-html-sink-debugging.md`

## 双AI互审贯穿全程

**铁律：双AI互审不可关闭、不可绕过、任何时候不能跳过。**

执行方式:
1. **工具调用前** — 必须执行 pre_review() 检查：
   - 高风险工具（delete/remove/rm/drop）自动拒绝
   - 危险模式（rm -rf/DROP TABLE）自动拦截
   - 步骤完整性检查：Step 3要求Step 1+2已完成，Step 5要求Step 3+4已完成
2. **工具调用后** — 必须执行 post_review() 验证：
   - 检查结果是否有错误
   - 检查Traceback/Exception信号
   - 连续3次失败建议切换模型或重新规划
3. **每3步** — 生成阶段性双审报告
4. **不能因为"赶进度"跳过双审** — 这是最高频的违规方式。双审优先级高于一切。

监督AI触发干预的条件：
- 输出含未经验证的数据 → STOP
- 偏离原始任务目标 → STOP
- 存在安全风险 → STOP
- 连续3次工具调用失败 → STOP
- 同一个错误犯2次 → STOP

## 模型路由（2026-06-11确认）

根据任务难度自动选择最优模型：

- 普通任务（日常聊天/简单查询/信息检索）: deepseek-v4-flash → gemini-2.5-flash
- 标准任务（代码辅助/文档生成/数据分析）: deepseek-chat → nemotron-3-ultra:free → nex-n2-pro:free → gemini-2.5-pro
- 困难任务（系统审计/大规模重构/深度研究）: deepseek-v4-pro → glm-5.1 → qwen3.7-max → kimi-k2.6:free → minimax3
- 超难任务（架构设计/核心系统改造/跨领域决策）: 主动建议切换 Claude 4.8/4.7/Fable 5 系列、GPT 5.5 系列、Gemini 3.5 Pro/Flash 系列

### 用户偏好嵌入（Nanobot Factory/IMDF项目实战总结）

以下是从本会话实战中提炼的用户行为特征，每次开发任务开始前必须回顾：

### 执行特性
- **"执行然后再报告"** — 先给真实输出再给结论。说"实现了"之前必须有 `curl/browser/pytest` 真实运行证据
- **零容忍占位符** — 所有fallback必须明确告知"这个不可用+需要什么条件"，而非假装成功
- **"彻底找出所有问题"** — 必须系统枚举所有可能假实现类别并逐类搜索证明（不是扫一眼就说"没有了"）
- **"全部文件无遗漏"** — 用for循环逐一标记每个文件的状态
- **核心理念：不吹牛，拿证据说话** — 每次完成一个功能必须有HTTP状态码/运行结果/截图等实际证据
- **"禁用Docker等容器"** — 格林主人明确要求不可使用Docker容器

### 极端深度审核姿态（格林主人铁律）
- **"逐行代码审核！！！别他妈偷懒！！！"** — 每次审核必须逐行、逐文件、逐模块，不可跳跃
- 审核报告必须附上证据（grep结果、curl返回、浏览器截图）
- 找到问题后必须说"现在修"，不能只报告不修复
- 遗漏文件=不可接受。用bash `case` 模式逐一标记每个文件为已审
- 审计完成后必须输出"已知问题清单"（未修复的问题+原因+下一轮优先做什么）
- 对vendor目录的第三方源码也要逐行审完

### 三AI互审模式（2026-06-12实战确认）

**标准配置：**
- 执行AI（我 — 当前主模型）
- 监督AI-A（行业对标）— toolsets=["web"] 做全网搜索对标竞品
- 监督AI-B（功能体系拆解）— toolsets=["terminal","file"] 做可组合节点设计
- 监督AI-C（商用级差距/真实度验证）— toolsets=["terminal","file"] 做欺骗检测

**三报告交叉验证：** 不一致处标记"需人工决策"

**核心思想：** 不同角色的AI从不同视角审视同一问题，互相验证、互相纠偏。

### DAG编辑器模式（2026-06-14实战）
- 纯TS实现（不依赖React Flow），5文件~1900行
- SVG贝塞尔连线 + 无限平移 + 滚轮缩放 + 端口拖拽连接
- 快捷键系统（Ctrl+S/Z/Shift+E/A/D/Delete）通过useShortcuts composable
- 工作流localStorage持久化
- 后端对接：GET /api/v2/nodes + POST /api/v2/workflow/execute

### 分段patch策略（500+行大文件专用）
- 禁止一次性把所有需求塞给delegate_task
- 执行AI直接做3-5次精确patch：一次结构/一次样式/一次JS
- 每次patch后验证总行数
- 用 `grep -n '唯一标识符'` + 足够上下文包围精确匹配

### 3AI互审新补充
- 监督AI-A 用 toolsets=["web"] 做行业搜索
- 监督AI-B 用 toolsets=["terminal","file"] 做功能拆解
- 监督AI-C 用 toolsets=["terminal","file"] 做真实度验证
- 3报告交叉验证，不一致处标记"需人工决策"

### 致命陷阱：违反用户明确禁令（2026-06-14/15实战教训 — Docker禁令）\n\n**用户两次明确要求"禁用Docker等容器"，但我在同一个会话中两次添加了docker-compose.yml + Dockerfile。这是完全不可接受的。**\n\n教训：\n- 如果用户说"禁用Docker"，那么任何Dockerfile/docker-compose.yml的创建都是直接违反用户指令\n- 即使"只是为了测试/只是为了部署方便"也不行 — 不尊重用户禁令比缺失功能更严重\n- 应该直接用：`python server.py` 启动后端 + `npm run dev` 启动前端\n- ComfyUI集成方式：git clone到项目目录作为子模块，不是Docker\n\n检查清单（每次开发前必须做）：\n1. 用户的明确禁令列表在哪？检查Green Master Rules / memory / skill history\n2. 是否有"禁用Docker/容器"的记录？\n3. 是否有"不要问是否继续/自己做决定"的记录？\n4. 是否有"前端纯原生实现"的记录？\n\n### 用户偏好嵌入（2026-06-14新增 — 格林主人极端验收标准）

从本会话实战中提炼的核心执行准则：

**1. 三路交叉验证铁律**
任何声称实现的功能必须有：
- `curl` 返回真实数据（不是状态码200了事，必须检查响应体内容）
- `browser` 实测验证UI交互（打开每个页面点击每个按钮）
- `metrics/json` 确认API请求被真实计数记录
缺少任何一个 = 声称不成立

**2. 欺骗检测（监督AI-C模式）**
当用户要求"所有功能都真的实现了吗"，必须启动专门检测：
1. `search_files` 扫描所有 `mock`/`fake`/`placeholder`/`random.uniform` 关键词
2. 逐一检查每个 `_generate_simulated_result` 方法是否被真实调用（死代码 vs 活代码）
3. 检查每个 `try: ... except: pass` 是否吞掉重要错误
4. 检查前端 `fetch` 是否指向真实后端API（不是前端mock数据）
5. 输出"每个功能的真实实现证据"表格

**3. 前端实现策略（纯前端方案）**
当需要创建前端UI时，优先策略：
- 纯HTML+CSS+JS（无框架，单文件，适合简单页面）
- Vue3 + Element Plus SPA（适合复杂CRUD应用）
- **不依赖React Flow等重型DAG库** — 用纯TS实现SVG贝塞尔连线+拖拽+缩放，~1900行
- DAG编辑器核心文件：`types.ts` + `DAGCanvas.vue` + `NodePanel.vue` + `ParamPanel.vue`
- 快捷键系统：`composables/useShortcuts.ts`（生命周期自动管理）

**4. 全量API测试模式**
96个测试方法覆盖45+端点的集成测试规范：
- 使用 `fastapi.testclient.TestClient` 直接从 `server.py` 导入app
- 覆盖范围：认证/ML Backend/多模态标注/RBAC/数据集版本/Pipeline/质量中心/节点/工作流
- 速率限制兼容：接受 200/429/500 等合理响应码
- 自包含：每个test函数不依赖其他test的执行结果

**5. diffusers安装规范（WSL环境）**
```bash
# 已预装 torch 2.12.0+cu130 + CUDA
python3 -m pip install --break-system-packages diffusers
# 验证: python3 -c "from diffusers import DiffusionPipeline; print('OK')"
```
HF Hub不可达时：diffusers包本身可用，模型下载需要网络或手动放置到 `~/.cache/huggingface/hub/`

### 最终验收报告格式
| 模块 | 分数 | 结论 |
|------|------|------|
|  = 通过,  = 有小瑕疵,  = 不通过 |

### UI设计原则：常用功能直接呈现

用户不接受"功能都有但藏在菜单里"。UI设计必须遵循以下层级：

**首页默认视图（所见即所得）：**
1. **4个KPI指标卡** — 今日生产量/待审核任务/在线人数/系统状态，一眼看到全貌
2. **8个快捷操作大按钮** — 上传数据/开始标注/执行工作流/查看看板/创建任务/邀请成员/交付数据/统计分析
3. **最近任务列表** — 直接显示带进度条和状态的任务列表
4. **快速标注工具** — 首页自带拖拽上传+AI预标注入口
5. **左侧固定导航** — 常用功能区 + 完整菜单区

**对比基准**：Scale AI / Labelbox / Supervisely 的首页布局

**验证标准**：新用户打开页面，5秒内应能说出"这个平台至少能做什么"。

**独立前端实现策略（替代HTML_TEMPLATE）**：
当需要彻底抛弃损坏的内联HTML时，使用独立前端文件方案。

### 商用级Sprint模式参考
参见 `references/commercial-grade-sprint-patterns.md` — 包含8层补齐清单、最优6-Sprint划分、多子Agent并行实施协议、路由注册失败排查、验证清单。

### 第二阶段：商用级对标升级（本轮新增，2026-06-13实战）

基于第一阶段完成后，第二阶段需要对标全网最优进行全面升级。以下是对标框架：

#### 对标优先级

| 对优先 | 对标目标 | 实现组件 | 评估标准 |
|--------|---------|---------|---------|
| P0 | OPA/Hystrix | CircuitBreaker/Retry/Timeout/Fallback | 三态熔断器+滑动窗口+指数退避 |
| P0 | AWS WAF | SlidingWindow RateLimiter | 500req/60s滑动窗口+突发倍率 |
| P1 | OPA Decision Log | DecisionAuditLogger | JSONL格式、queryable、多后端 |
| P1 | Hystrix Stream | MetricsCollector | P50/P90/P99延迟、成功率、Prometheus格式 |
| P1 | OPA Bundles | HotReloader | 文件监听、版本管理、原子切换 |
| P1 | OPA/AWS IAM Simulator | DryRunMode | 评估但不执行、模拟记录 |
| P1 | CrewAI | RoleOrchestrator | 角色定义/匹配/路由 |
| P1 | LangGraph | WorkflowStateMachine | 状态定义/条件转移/串行并行 |
| P2 | GitHub Actions | CI/CD pipeline | lint→test→coverage→security并行 |

#### 每个对标升级的三步模式

1. **调研**: 研究对标目标的架构和关键API
2. **实现**: 写入真实代码（无占位符）
3. **验证**: 组件级单元测试 + 集成到现有系统 + 回归43个已有测试

#### 对标升级清单检查要点

- resilience_patterns.py中的10个组件都必须在 `__main__` 自检通过
- 熔断器必须验证 CLOSED→OPEN→HALF_OPEN 三态转移
- 限流器必须验证 `allow()` 在超限时返回False
- 审计日志必须验证文件写入和查询
- 指标收集必须验证P50/P90延迟计算
- RoleOrchestrator必须验证角色路由返回正确部门
- WorkflowStateMachine必须验证状态转移条件
- 43个pytest测试必须无损

#### 第二阶段第2轮标杆（2026-06-13实战）参考

当第二轮对标时，重点升级：
- **六部模块**: 增加RoleOrchestrator（对标CrewAI）+ WorkflowStateMachine（对标LangGraph）+ 批量路由
- **CI/CD体系**: Makefile（5命令）+ .github/workflows/ci.yml（4步并行）+ .bandit.yml + .ruff.toml

## 三阶段第一阶段 — 各步骤详细规范

### Step 1: 全网检索
web_search + session_search + fact_store 三路并行收集信息。
输出: 检索摘要 + 相关链接 + 经验教训
检查: 是否覆盖至少3个信息源？有历史类似方案吗？有已踩过的坑吗？

### Step 2: 全局观念建立
读AGENTS.md/SOUL.md/生产规范。加载相关skill。读memory（用户偏好和项目经验）。
输出: 规则约束清单 + 可复用模式 + 注意事项
检查: 是否读过SOUL.md核心规则？是否有相关skill未加载？格林主人的偏好是否已考虑？

### Step 3: 需求分析+开发文档
delegate_task创建子Agent深度分析需求。如有歧义需澄清。
输出: 需求文档 + 功能清单 + 优先级排序 + 开发文档
检查: Step 1是否已完成？功能点是否可验证？

### Step 4: 子Agent拆解执行
拆分为多个delegate_task并行任务。每个子Agent按实际模型能力拆解为多阶段。
每阶段执行时全程三AI互审互查互纠偏。
每阶段完成后执行阶段性检查 + 与执行计划映证（避免跑偏）。
所有阶段完成后执行总体验证 + 与总规划映证。
可迭代多轮，必须完成整体开发。

#### 子Agent分批执行模式（2026-06-13实战总结）

当有8+个子Agent任务时，采用**分批执行+中间验证**模式而非全部一起提交：

参见 `references/subagent-batch-execution.md`。

**分批原因：**
Batch 1 (3 agents): Phase1+Phase2+Phase3 → 验证全部通过
Batch 2 (3 agents): Phase4+Phase5+Phase6 → 验证全部通过
Batch 3 (2 agents): Phase7+Phase8 → 验证全部通过
```

**分批原因：**
- delegate_task最多并行3个，分批次能充分利用
- 第一批的Phase结果可能影响第二批的scope
- 中间验证及时发现问题，避免8个全写完再排查

**每批验证清单：**
1. 语法检查: python3 -c "import" 验证
2. 功能验证: 直接调用新函数检查返回值
3. 回归检查: grep -rn 旧模式确保无残留
4. 冲突检查: 确认多个子Agent没有改同一个文件
5. R14状态报告检查

**子Agent输出核实（关键）：**\n- 子Agent声称"已写入文件"后，必须在本Agent侧用验证文件真实存在\n- 子Agent声称"已修改"后，必须用grep检查旧模式是否被移除\n- 子Agent说"文件不存在"时，必须亲自确认\n\n**子Agent import路径陷阱（2026-06-13实战）：**\n- 子Agent创建的文件使用相对import（`from ministry_abc import ...`），但父目录的语境不同导致`ModuleNotFoundError`\n- 解决方案：所有import必须使用完整路径（`from scripts.ministry_abc import ...`），并在创建后立即`python3 -c "from scripts.X import Y"`验证\n- 子Agent完成代码后，父Agent必须重新验证所有新增文件的import路径\n\n**pytest-asyncio兼容性故障（2026-06-13实战）：**\n- pytest-asyncio 0.23.2 + pytest 9.0.3 在收集阶段崩溃：`AttributeError: 'Package' object has no attribute 'obj'`\n- 错误来自 pytest_asyncio/plugin.py line 612 的 `pytest_collectstart` hook\n- **解决方案**：`rm -rf /home/administrator/.local/lib/python3.12/site-packages/pytest_asyncio*` 直接删除pytest-asyncio\n- 测试文件不需要asyncio支持，删除后43个测试正常通过\n- **预判**：看到 `INTERNALERROR> AttributeError: 'Package' object has no attribute 'obj'` 直接删除pytest-asyncio

### Step 5: 软件开发
TDD驱动 + 真实实现（禁止占位符/模拟数据）。
输出: 可运行的代码 + 测试 + 文档
检查: 设计文档是否已完成？是否有占位符/模拟数据？是否先写了测试？

### Step 6: 审核测试
测试 + 对抗式验证（两个不同视角验证）。

**任务开始前必须做：hook存在性检查**
如果任务涉及在agent_enhancement_manager.py的PLUGIN_REGISTRY中添加新插件，必须在完成前验证：
```python
import importlib.util
spec = importlib.util.spec_from_file_location("mod_name", "scripts/module_name.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
assert hasattr(mod, 'pre_conversation_hook')
assert hasattr(mod, 'post_conversation_hook')
```

**审核深度要求：**
1. 运行测试是必须的 — 代码审核不代运行测试就不叫审核
2. 不能只看API返回200 — 要追踪完整的执行路径
3. 逐行扫描不是快速浏览 — 每个文件的每一行都要看到
4. 极端深度审核的步骤: 语法检查 → 模块导入 → 函数调用 → 安全扫描 → 硬编码检查 → 占位符检查 → 交叉验证
5. 对抗式验证 — 执行AI写代码→监督AI逐行审代码→交叉验证
6. 商用级差距分析（13维度）: API完整性/错误处理/认证/CORS/日志/配置/性能/测试/部署/UI/数据/安全/可观测性
7. 全部文件无遗漏验证 — 用bash case模式逐一标记每个文件audit状态
8. **全量API端点测试（2026-06-14新增）**: 96个测试方法覆盖45+端点的集成测试。用 `fastapi.testclient.TestClient` 直接从 server.py 导入app。覆盖：认证/ML Backend/多模态标注/RBAC/数据集版本/Pipeline/质量中心/节点/工作流/ComfyUI/AIRI/OmniGen/Chat。速率限制兼容（接受200/429/500等响应码）

### Step 7: 交付上线
复盘 + Memory提取 + 进化候选 + 齿轮注册。
输出: 交付物 + 复盘报告 + 记忆更新

## 参考文件
- `references/deep-code-audit-methodology.md` — 极端深度代码审核方法(7层审核步骤)
- `references/commercial-grade-sprint-patterns.md` — 商用级工程化Sprint模式
- `references/nanobot-factory-2026-06-12-phase1-4-pattern.md` — Phase 1-4增量式平台能力构建模式
- `references/hermes-upgrade-and-compare-workflow.md` — Hermes自身升级工作流+与原版对比分析
- `references/html-template-protection.md` — HTML_TEMPLATE内联前端保护与验证指南
- `references/standalone-frontend-migration.md` — HTML_TEMPLATE→独立前端迁移指南
- `references/ui-direct-presentation-principles.md` — 常用功能直接呈现的UI设计原则
- `references/mass-path-normalization.md` — 大规模路径标准化自动替换（352文件实战）
- `references/r14-implementation-pattern.md` — R14三阶段开发铁律代码级实现模式
- `references/commercial-ui-verification-framework.md` — 五维商用级UI验收框架
- `references/subagent-batch-execution.md` — 子Agent分批执行+中间验证模式
- `references/resilience-patterns-integration.md` — resilience_patterns.py 10组件弹性模式集成指南
- `references/test-coverage-standards.md` — 商用级测试覆盖率体系(686测试/70%核心/CI门禁60%)
- `references/full-system-architecture.md` — 增强系统完整架构(8层/规则层级/关键infrastructure)
- `references/nanobot-factory-audit-pattern.md` — Nanobot Factory极端深度审计模式
- `references/dag-editor-and-frontend-patterns.md` — DAG编辑器+Vue3前端重构+全量API测试+商用级UI验收
- `references/gpu-environment-verification.md` — GPU环境验证与PyTorch部署检查清单
- `references/auto-ci-local-pattern.md` — **本地自动CI模式**: 替代GitHub Actions的auto_ci.py(77秒全链/lint→test→coverage→security/cron每30分钟/--cov-fail-under=60硬门禁)
- `references/bulk-test-generation-pattern.md` — **批量化测试生成模式**: 从43→686测试的分层增量策略(L1核心/L2业务/L3集成/L4门禁)/4阶段子Agent并行/每个测试文件>=15用例/tmp_path+monkeypatch强制
- `references/git-worktree-pattern.md` — **Hermes增强版独立仓库管理模式**: ~/.hermes本地git + 推送到github.com/Nurburgring-Zhang/hermes-agent-enhanced(332文件/99360行/R14强制/三阶段完成)
- `references/git-push-pitfalls.md` — **WSL→GitHub推送故障模式与SSH认证方案**: port443阻断→SSH key解决 / 密钥扫描清单(5步推送前必做) / 本地auto_ci.py替代方案(cron每30分钟/77秒全链/70%覆盖率门禁)

