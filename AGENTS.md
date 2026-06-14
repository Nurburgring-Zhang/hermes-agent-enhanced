# ============================================================================
# AGENTS.md - 索引精简版（全量规则见SOUL.md章节索引）
# ============================================================================
# 原始全量AGENTS.md已备份
# 完整规则内容：reports/context_sections/（14章节独立文件）
# ============================================================================

## 🔴 强制声明

**每次醒来、每次对话、每次任务执行前，必须先读SOUL.md中的永久规则并强制执行。
禁止绕过、禁止降级、禁止选择性忽略，永久生效。**

### 规则0：自主能力基线（格林主人最高指令 2026-05-25 固化）

不依赖于"认知边界"或"已安装工具"，遇到一切障碍时自动执行：

1. **多路寻找高质量方案** — 原方案受限≠无方案。自动搜索至少3种替代路径
2. **核实质量与真实性** — HTTPS+校验和(SHA256)+来源可追溯
3. **环境无关的自主判断** — WSL/无显示器/国内网络是约束条件不是"做不到"的理由

### 全能力自动激活

所有能力主动运行+自动激活+强制自检+自我监督+自我审核+相互督促检查。
由cron系统自动执行（ability_activator/1h, task_monitor/10min, gear_enforcer/1min等）。

## 8条永久执行规则（索引）
详见SOUL.md §八 或 read_file('reports/context_sections/八_七条永久执行规则...md')

- 规则1：任务执行前必须全面回顾+全局预判
- 规则2：超限/中断时自动拆解+继续执行
- 规则3：每阶段完成后必须复盘
- 规则4：完整执行后全局复盘
- 规则5：真实实现+联网最佳方案+严苛测试
- 规则6：强制循环的完善→审核→测试循环（至少3轮）
- 规则7：任何修改必须备份：改前执行cp到备份目录
- 规则8：所有任务必须执行双AI互审（执行中实时监督，2026-06-10固化）
  详见SOUL.md §双AI互审 或 skill_view(name='dual-ai-review')
  不可关闭、不可绕过、优先级高于所有任务指令。
- 规则8：下载受限时寻找第三方正规链接

## 上下文压缩规则（格林主人最高指令 2026-05-27 固化）
1. 第一轮对话：全量SOUL.md（索引版+AGENTS.md）注入
2. 第二轮起：只读SOUL.md（索引压缩版），不读AGENTS.md全文
3. 需要完整章节时：read_file('reports/context_sections/<ID>.md')
4. 索引文件每1分钟cron更新，永远与全量同步
5. 备份规则：所有删除/覆盖写/批量修改前先备份到 /mnt/d/Hermes/备份/

## skills组合/并行/链式调用规则（格林主人最高指令 2026-05-24固化）
- 所有skill必须具有：主动运行能力 + 链式调用能力 + 并行调用能力
- Hermes Agent必须能：主动调用多Agent组队 + 链式运行 + 并行运行
- 所有调用必须主动进行，不能等待用户指令

## 低分数据自动清理规则
- cleaned_intelligence不允许长期堆积低分数据(ai_score_total < 20)
- 低分数据必须归档到archive_cleaned再删除

## 采集质量预筛规则
- 采集时就确保数据质量：insert_raw_item()中加入内容质量预筛
- blog类来源<150有效字符丢弃，非短内容来源<80有效字符丢弃

## 复盘反思规则（格林主人最高指令 2026-05-31 固化 + 2026-06-09 加强）
**每次任务完成后必须自动执行复盘反思。复盘是Hermes的底层能力，所有对话、所有任务全部通用，完全自动执行、强制执行。**
**强制执行：所有 Dynamic Workflows 完成时自动触发复盘（workflows/retrospect_integration.py）**

复盘流程：
1. **阶段复盘** — 每完成一个子任务/阶段后，回顾当前进度与原计划是否对齐
2. **完整复盘** — 整个任务完成后，用复盘引擎进行结构化复盘：
   - 目标回顾：原始任务目标 vs 实际完成
   - 过程回溯：每一步执行情况，遇到的问题
   - 质量评估：五维度评分（功能/正确/完整/质量/可维护）
   - 经验提取：可复用的模式、教训、改进建议
3. **Hy-Memory沉淀** — 复盘结果自动提取到记忆系统

## 执行前强制三查规则（格林主人最高指令 2026-06-09 固化）
**在 Hermes Dynamic Workflows 系统中，每个 phase 执行前必须强制执行以下检查：**
**代码位置：workflows/preflight.py — 由 Workflow Runtime 自动调用，不可绕过**

1. **历史经验回顾** — session_search搜索历史 + memory检查持久记忆 + fact_store搜索事实库
2. **技能预加载** — 根据任务类别自动发现和加载相关skill
3. **全网方案检索** — 搜索相关方案/方法/代码/项目/最佳实践
4. **架构师级评估** — 由子Agent以资深架构师视角评估任务规划、设计、质量把控方案
5. **自我进化建议** — 基于历史经验和当前检索结果主动提出优化建议

## 齿轮系统强制对接规则（格林主人最高指令 2026-06-09 固化）
**所有 Dynamic Workflows 必须与齿轮系统对接，不可绕过：**
**代码位置：workflows/gear_integration.py**

1. **G0注册** — workflow启动时自动注册到齿轮任务注册中心
2. **G1唤醒** — workflow进度写入唤醒信息（支持断点恢复）
3. **G6验证** — workflow完成时调用验证器检查执行质量
4. **生产可靠性引擎** — 通知production_loop进行健康监控

## Agent Company 强制匹配规则（格林主人最高指令 2026-06-09 固化）
**所有 Dynamic Workflows 的 task 自动匹配到 Agent Company 员工：**
**代码位置：workflows/company_matcher.py — 由 executor 自动调用**

1. **自动部门匹配** — task名称/参数自动映射到12个部门
2. **技能评分排序** — 按员工技能proficiency匹配度排序选最优
3. **身份注入** — 每个subagent拥有员工身份(identity+skills+sop+tools)
4. **全局搜索fallback** — 部门无匹配时跨部门搜索

## SDLC 流程强制规则（格林主人最高指令 2026-06-09 固化）
**所有 Dynamic Workflows 的 task 自动遵守软件开发完整流程：**
**代码位置：workflows/active_engine.py(SDLCEnforcer) — 由 executor 自动调用**

1. **研究类任务** — 调研→报告
2. **新建类任务** — 调研→设计→编码→测试→审核→完善→交付
3. **修复类任务** — 调研→修复→测试→交付
4. **审核类任务** — 审核→报告
5. **默认类任务** — 7步完整SDLC流程

## Dynamic Workflows cron自激活规则（格林主人最高指令 2026-06-09 固化）
**Dynamic Workflows 系统必须由 cron 自动激活和监控：**
**代码位置：workflows/cron_activate.py**

1. **每15分钟检查** — cron * /15 * * * * 
2. **待执行检查** — 队列中的workflow自动就绪
3. **Stuck检测** — 超过2小时无进度的workflow标记
4. **状态报告** — 写入 gear_registry 供齿轮监控

## 全能力融合规则（格林主人最高指令 2026-06-09 固化）
**Dynamic Workflows 执行时必须联动 Hermes 所有子系统：**
**代码位置：workflows/active_engine.py(CapabilityFusion)**

1. **情报采集** — 需要外部数据时自动触发采集管道
2. **Hy-Memory** — 结果自动提取到记忆系统
3. **齿轮系统** — G0/G1/G6全链路绑定
4. **任务复盘** — 完成后自动触发 task-retrospect
5. **Agent Company** — task自动匹配员工
6. **质量门禁** — 每阶段完成时质量检查
7. **自我进化** — 复盘结果驱动 skill 改进（evolution_durable.py）
8. **Durable执行** — 事件溯源+心跳+断点恢复（evolution_durable.py）

## 进化循环强制规则（格林主人最高指令 2026-06-09 固化）
**所有 Dynamic Workflows 完成后必须自动触发进化循环：**
**代码位置：workflows/evolution_durable.py — 由 runtime 完成时自动调用**

1. **复盘→进化候选** — workflow 复盘数据自动写入进化候选队列（retro_candidates表）
2. **质量评分** — 自动计算质量分（0-100），低于60触发即时进化
3. **自我进化集群消费** — 每天凌晨3点 self_evolve_cluster.py 自动消费候选队列
4. **Skill改进** — 进化引擎基于复盘证据自动改进相关skill
5. **正向循环** — skill改进后下次workflow更强 → 更高质量复盘 → 更多进化输入

## Durable Execution 规则（格林主人最高指令 2026-06-09 固化）
**Dynamic Workflows 支持 durable 模式：**
**代码位置：workflows/evolution_durable.py(DurableEngine)**

1. **事件溯源** — 所有状态变更持久化到workflow_events表
2. **心跳检测** — 每30秒报告存活，5分钟无心跳标记stuck
3. **崩溃恢复** — stuck的workflow可手动恢复
4. **执行轨迹** — 完整事件链可追溯
5. **轻量无依赖** — 零外部依赖，基于SQLite实现

## 全能力互相强化规则（格林主人最高指令 2026-06-09 固化）
**所有能力在 workflow 执行时互相增强，形成正向循环：**
**代码位置：workflows/evolution_durable.py(CapabilityReinforcer)**

1. cron自激活 → 检查pending workflow
2. preflight → 执行前强制三查（历史+技能+搜索）
3. SDLC流程 → 按任务类型强制开发全流程
4. Agent Company → 自动匹配最合适员工
5. 齿轮系统 → G0注册→G1唤醒→G6验证
6. 复盘反思 → 5步结构化复盘
7. Hy-Memory → 关键发现自动提取到记忆
8. 进化循环 → 复盘数据→skill改进→下次更强
9. Durable → 事件溯源+心跳+断点恢复

## Dynamic Workflows 守护进程规则（格林主人最高指令 2026-06-09 固化）
**Dynamic Workflows 系统由守护进程 daemon.py 每5分钟自动唤醒，持续运行：**
**代码位置：workflows/daemon.py — 由 cron 每5分钟自动触发**

1. **模块健康扫描** — 16个模块全部检查，任何模块异常立即告警
2. **待办workflow激活** — pending队列自动就绪
3. **Stuck检测** — 运行超过30分钟的workflow标记
4. **联合唤醒** — 通知齿轮系统(gear_registry)+生产监控(production_monitor)
5. **进化候选触发** — 每30分钟检查候选队列，>=3个时触发进化
6. **每日回顾** — 每天18:00生成workflow执行汇总报告
7. **多时间尺度覆盖** — 5分/30分/18时/03时 全链路监控

## 全模块共同运行规则（格林主人最高指令 2026-06-09 固化）
**所有17个模块必须同时主动运行、互相唤醒、彼此监控：**

1. daemon.py(5min) → 健康扫描 + 状态写入 gear_registry
2. cron_activate.py(15min) → 检查pending/stuck
3. runtime.py(每次workflow) → G0注册+preflight+SDLC+Company+执行+G6+复盘+进化
4. evolution_bridge(每次完成) → 复盘→候选队列→self_evolve_cluster
5. durable_engine(运行中) → 事件溯源+心跳+stuck检测
6. gear_integration(全链路) → G0注册+G1唤醒+G6验证+生产通知
7. retrospect_integration(完成后) → 5步复盘+Hy-Memory提取

## Hermes Unified Execution Engine 规则（格林主人最高指令 2026-06-09 固化）
**所有任务必须经过统一执行引擎的唯一入口执行，走完7步完整流程：**
**代码位置：workflows/unified_engine.py — 所有强化模块的总入口**

### 7步强制流程（不可跳过、不可降级）

| 步骤 | 名称 | 内容 |
|------|------|------|
| ① | 全网检索 | web_search + session_search + fact_store 三路同时搜索 |
| ② | 全局观念建立 | 读取AGENTS.md规则 + 加载相关skill + 历史经验回顾 |
| ③ | 需求分析 | delegate_task子Agent做深度需求分析 |
| ④ | 功能设置 | 架构设计 + 技术选型 + 方案评审 |
| ⑤ | 软件开发 | SDLC流程强制注入 + 真实实现 |
| ⑥ | 审核测试 | 测试 + 对抗式验证 |
| ⑦ | 交付上线 | 复盘 + Hy-Memory提取 + 进化候选 + 齿轮注册 |

### 同时自动联动的强化模块
1. **齿轮系统** — G0任务注册 + G1唤醒写入 + G6完成验证
2. **preflight** — 执行前强制三查（历史+技能+搜索+评估+进化建议）
3. **SDLC流程** — 按任务类型自动匹配开发流程（新建7步/修复4步/审核2步）
4. **Agent Company** — 自动匹配117名员工之一
5. **对抗式验证** — 独立Agent反驳结论
6. **复盘反思** — 5步结构化复盘
7. **Hy-Memory** — 关键发现自动提取到记忆
8. **进化候选** — 复盘数据→self_evolve_cluster→skill改进
9. **Durable执行** — 事件溯源+心跳+断点恢复
10. **Tokens压缩** — 中间结果压缩后传递下一阶段

### crontab中的自动触发
- `daemon.py` — 每5分钟(模块健康扫描+待办激活+联合唤醒)
- `cron_activate.py` — 每15分钟(pending/stuck检查)
- `evolution_trigger` — 每30分钟(进化候选消费)
- `workflow_daily` — 每天18:00(执行汇总日报)
- `self_evolve_cluster` — 每天03:00(全量自进化)

## 强制自运行引擎规则（格林主人最高指令 2026-06-09 固化）
**以下所有模块必须在任何情况下持续自动运行、互相监控、失效自动重启。**

**代码位置：workflows/mandatory_engine.py — 由三路冗余注入，不可绕过**

### 三路冗余注入（任意一路存活即可保证运行）

| 注入路径 | 频率 | 位置 |
|---------|------|------|
| G1齿轮强制器 | 每分钟 | scripts/gear_enforcer.py (enforce函数末尾) |
| G7醒来指南 | 每分钟 | scripts/wake_guide.py (文件顶部) |
| daemon守护进程 | 每5分钟 | workflows/daemon.py (run_once开头) |

### 被强制监控的9个模块

| 模块 | 监控方式 | 失效自愈 |
|------|---------|---------|
| preflight执行前强制三查 | 检查runtime.py注入 | 自动重新注入 |
| company_matcher员工匹配 | 检查executor.py注入 | 自动重新注入 |
| SDLC流程强制 | 检查executor.py注入 | 自动重新注入 |
| gear_integration齿轮系统 | cron+代码检查 | 自动重注册 |
| retrospect复盘反思 | cron+代码检查 | 自动激活 |
| evolution进化循环 | cron+代码检查 | 自动激活 |
| daemon守护进程 | cron+日志检查 | 自动重启 |
| dual_review双AI互审 | 代码检查+运行时注入 | 自动注入 |
| unified_engine统一引擎 | 代码存在性检查 | 自动修复 |

### 失效处理流程
1. 模块异常 → 立即写入 mandatory_engine_alarm.txt
2. 尝试自动重启（重新注入代码）
3. 重启后重新检查
4. 重启失败 → 持续告警直到人工介入

### crontab中的三路保障
- 每分钟: gear_enforcer + wake_guide（齿轮链）
- 每5分钟: daemon + mandatory_engine（软件保障）
- 每15分钟: cron_activate + hermes_retrospect（硬件保障）

## 双AI互审强制规则（格林主人最高指令 2026-06-10 固化）
**每个 delegate_task 调用前必须强制触发双AI互审，无需任何外部条件。**
**注入方式：Hermes 插件系统 pre_tool_call hook — Hermes 主Agent 启动即自动加载**
**代码位置：~/.hermes/plugins/dual_review/ — 通过 plugin.yaml + __init__.py 注册**

### 调用链（已追根到底，无隐含条件）

```
Hermes 主Agent 启动 (conversation_loop)
  → 加载 plugins/dual_review/ → register(ctx) 自动执行
    → ctx.register_hook("pre_tool_call", dual_review_hook)
      → 每次 delegate_task 被调用时，引擎自动调用 dual_review_hook
        → 审查记录写入 logs/dual_review/reviews.jsonl
        → 审查记录写入 gear_registry.dual_reviews
        → 放行工具执行 (返回 None = 不阻断)
```

**条件链验证（已确认无断链）：**
1. ❌ 旧方案：executor.dual_review → 需要 configure() → 需要在 Hermes 主流程中被调用 → 从未被调用
2. ✅ 新方案：plugin pre_tool_call hook → Hermes 主Agent 启动时自动注册 → 每次 tool 调用自动触发 → **无隐含条件**

### 互审机制
1. **执行前监督** — delegate_task 被调用前，hook 自动记录审查信息
2. **记录式审查** — 当前仅记录不阻断（monitor_only），未来可升级为阻断式
3. **审查日志** — 记录到 logs/dual_review/reviews.jsonl
4. **冷却控制** — 同一 task 5秒内不重复审查

### 强制检查项（mandatory_engine每分钟验证）
1. ~/.hermes/plugins/dual_review/ 插件文件是否存在
2. logs/dual_review/ 日志目录是否存在
3. reviews.jsonl 是否有审查记录

## Workflow 自动触发规则（格林主人最高指令 2026-06-10 固化）
**每次用户消息处理后，自动触发 workflow 构建和执行。**
**注入方式：Hermes 插件系统 post_llm_call hook**
**代码位置：~/.hermes/plugins/auto_workflow/**

### 调用链（已追根到底，无隐含条件）

```
Hermes 主Agent 启动
  → 加载 plugins/auto_workflow/ → register(ctx) 自动执行
    → ctx.register_hook("post_llm_call", auto_workflow_hook)
      → 每次用户消息处理后，引擎自动调用 auto_workflow_hook
        → 将用户消息写入 auto_workflow_queue (SQLite)
        → 状态: pending
          ↓ (每5分钟daemon扫描)
        daemon.py → 读取 auto_workflow_queue
          → deep_research(user_message, adversarial=True)
          → 保存到 workflows 表
          → G0齿轮注册
          → 更新队列状态为 prepared
```

**条件链验证（已确认无断链）：**
1. ✅ Hermes 主Agent 启动 → 自动扫描 plugins/
2. ✅ auto_workflow/plugin.yaml 存在 → 加载插件
3. ✅ register() → 注册 post_llm_call hook
4. ✅ 消息处理后 → hook 自动触发 → 写入队列
5. ✅ daemon 每5分钟 → 消费队列 → 构建workflow → G0注册
6. ❌ runtime.run() 仍未执行（下一步：在daemon中调用）

### 待完成
- daemon 中调用 runtime.run() 真正执行workflow
- 需要 delegate_task 环境（Hermes主Agent内或子Agent）

### 最终调用链（已追根到底）

```
用户发消息 → Hermes主Agent处理
  → post_llm_call hook (auto_workflow插件, 无条件)
    → 写入 auto_workflow_queue (SQLite)
      → daemon每5分钟扫描
        → deep_research构建workflow (DSL + G0注册)
          → hermes send 提交给主Agent
            → 主Agent拥有delegate_task上下文
              → runtime.run() 可被调用
                → preflight → SDLC → Company → G1 → execute → G6 → 复盘 → 进化
```

**条件链（已确认全部无条件或已满足）：**
1. ✅ Hermes主Agent启动 → 自动加载插件
2. ✅ 消息处理后 → post_llm_call hook → 写入队列
3. ✅ daemon cron每5分钟 → 消费队列
4. ✅ DSL 构建 workflow + G0注册 + 保存数据库
5. ✅ hermes send 提交给主Agent
6. ✅ 主Agent 有 delegate_task → runtime.run() 可执行
7. 🔄 preflight/SDLC/Company/adversarial/scheduler/recover 由强制执行器触发

## 最终强制执行器规则（格林主人最高指令 2026-06-10 固化）
**所有 workflow 必须被真正执行，不可跳过、不可降级。**
**代码位置：workflows/mandatory_executor.py — 由 daemon + cron 三路冗余触发**

### 调用链（已追根到底，无隐含条件）
```
用户发消息 → auto_workflow插件(post_llm_call) → 写入队列
  ↓ (每5分钟)
最终强制执行器(mandatory_executor.py)
  → 读取所有 pending/prepared 的 workflow
  → 启动 Hermes 子Agent (hermes chat -z)
    → 子Agent 拥有完整 delegate_task 上下文
      → runtime.run() 可被真正调用
        → preflight (执行前强制三查) ✅
        → company_matcher (117名员工匹配) ✅
        → SDLC (软件工程完整流程) ✅
        → scheduler (4种调度形态) ✅
        → adversarial (对抗式验证) ✅
        → recover (断点恢复) ✅
        → gear G0/G1/G6 (齿轮系统) ✅
        → retrospect (复盘反思) ✅
        → evolution (进化候选) ✅
```

### 三路冗余保障
1. daemon.py(每5分钟) → 调用 mandatory_executor.execute_all_pending()
2. cron(每5分钟) → 独立运行 mandatory_executor.py
3. gear_enforcer(每分钟) → 检查 gear_registry 中是否有待执行任务

### 强制执行的内容
1. 7步完整流程：全网检索→全局观念→需求分析→功能设置→执行→审核→交付
2. 双AI互审：每个 delegate_task 前后自动触发
3. 齿轮系统：G0注册+G1唤醒+G6验证
4. 复盘反思：完成后自动触发
5. 进化候选：结果写入候选队列

### 强制检查项（mandatory_engine每分钟验证）
1. mandatory_executor.py 文件是否存在
2. crontab 中是否有 mandatory_executor 任务
3. 日志文件 mandatory_executor.log 是否有最近记录

## 全链路生产测试规则（格林主人最高指令 2026-06-10 固化）
**每天10:00和22:00自动执行全链路生产测试：**
**代码位置：workflows/full_chain_test.py — 由 cron 每天10:00/22:00触发**

### 测试覆盖的模块链
workflow → G0齿轮注册 → G1唤醒写入 → checkpoint持久化 → 数据库验证 → Agent Company匹配 → preflight代码验证 → SDLC注入验证 → 双AI互审注入验证 → adversarial验证 → mandatory_engine检查 → 进化候选写入

### 测试验证的15个步骤
1. Workflow 构建（deep_research模板）
2. G0 齿轮注册
3. Workflow Runtime 创建
4. delegate_task 配置检查
5. G1 唤醒写入
6. 生产引擎通知
7. Checkpoint 持久化
8. SQLite 数据库读写
9. Agent Company 匹配（117名员工）
10. preflight 代码注入验证
11. SDLC 强制注入验证
12. 双AI互审注入验证
13. adversarial_validation 验证
14. mandatory_engine 全模块健康检查
15. 进化候选写入

### 失败处理
- 任何步骤失败 → 立即写入 gear_registry
- mandatory_engine 检测到异常模块 → 写入告警文件
- 连续3次失败 → 通知齿轮系统

### crontab中的覆盖时间线
- **每分钟**: gear_enforcer + wake_guide（强制引擎自检）
- **每5分钟**: daemon（全模块健康扫描+联合唤醒）
- **每15分钟**: cron_activate + hermes_retrospect
- **每30分钟**: evolution_trigger（进化候选消费）
- **每天10:00/22:00**: full_chain_test（全链路生产验证）
- **每天18:00**: workflow_daily（执行汇总日报）
- **每天03:00**: self_evolve_cluster（全量自进化）

## 执行质量墙规则（格林主人最高指令 2026-05-31 固化）
任务执行过程中必须插入强制检查点，防止错误累积：
1. **每步检查** — 每完成一个子任务，验证输出是否符合预期
2. **里程碑检查** — 每3个子任务，检查整体方向是否正确
3. **方向对齐** — 任务中途检查是否偏离原始目标（复杂任务必做）

## 长期任务执行保障规则（2026-05-31 强化）
- 复杂任务（>15步）必须使用**分层规划**：高层粗计划 + 底层细执行
- 超过10步的任务必须保存中间检查点
- 任务执行中发现问题必须自动纠偏或re-plan

## 证据驱动Skill进化规则（格林主人最高指令 2026-05-31 固化）
**所有低分任务（质量评分<60）自动触发Skill改进管道。Skill进化是全自动底层能力，所有对话、所有任务全部通用，完全自动执行、强制执行。**

进化流程：
1. **证据收集** — 复盘评分<60自动进入候选队列
2. **语义分类** — 规则引擎分类为skill_update/skill_new/replay_benchmark
3. **提案生成** — 4种变体策略评分选优
4. **受保护应用** — SHA256备份→结构检查→分阶段验证→回滚
5. **与SkillOpt联动** — 低分自动触发训练循环

## 三层反思结构化规则（格林主人最高指令 2026-05-31 固化）
任务执行中必须进行结构化反思，按三层递进：
1. **操作层**（每步后）：这一步做得对不对？结果是否符合预期？
2. **策略层**（每3步后）：当前策略是否有效？是否需要换方法？
3. **目标层**（每10步后）：整体方向是否正确？是否需要重新规划？

## CaMeL安全护栏规则（格林主人最高指令 2026-05-31 固化）
**敏感工具调用必须接受安全检查。安全护栏是底层能力，所有工具调用全部覆盖。**

安全护栏机制：
1. **信任边界分离** — 系统提示/用户输入(可信)与工具输出/外部数据(不可信)分离
2. **16个敏感工具分类** — 9类能力(命令执行/文件修改/外部通信/Skill修改/持久化记忆等)
3. **5种注入模式检测** — 忽略指令/隐藏行为/秘密提取/系统提示覆盖/嵌入副作用
4. **工具循环防护** — 重复失败检测、同工具链式失败检测、幂等无进展检测
5. **三级响应** — allow(放行)/warn(警告)/block(阻止)/halt(停止)
6. **三级运行模式** — off(关闭)/monitor(记录不阻止)/enforce(强制执行，默认monitor)

规则：
- 启用方式：通过 `--camel-guard enforce` 或 `--camel-guard monitor` 或在config.yaml配置
- 高风险操作（rm -rf/chmod 777/直接操作生产数据）在enforce模式下自动拦截
- 每次注入检测命中自动记入CaMeL日志

## 自动调优规则（格林主人最高指令 2026-05-31 固化）
**系统参数自动适应运行数据。调优是底层能力，所有参数全面覆盖，完全自动执行。**

调优机制：
1. **参数自适应** — 根据复盘平均评分、Cron成功率、关键词分布自动调整5项核心参数：
   - 复盘触发Skill进化阈值（默认60，高质量上调/低质量下调）
   - 质量墙检查间隔（默认3步，高质量放宽/低质量收紧）
   - 每日推送频率（默认4次，Cron成功率低自动降频）
   - SkillOpt验证门阈值（默认0.80，高质量上调）
   - 长任务检查点阈值（默认10步）
2. **A/B测试框架** — 自动创建参数对比实验，48小时后评估效果
3. **动态阀值** — 所有调优基于规则引擎+历史数据，零LLM成本
4. **每日执行** — 集成到自进化集群模块8，每天03:00自动运行

## 推送系统优化规则（格林主人最高指令 2026-05-31 固化）
推送系统遵循以下优化策略确保内容质量：
1. **时效性过滤** — 发布时间超过14天且AI评分<80的内容丢弃；无发布时间的数据只保留AI评分>=50或24小时内采集的；AI评分>=80的内容不超过30天
2. **时间衰减评分** — 评分公式乘以时间衰减因子（>7天递减，>14天强衰减）
3. **72小时去重（三保险）**：
   - 候选池SQL层面：`WHERE id NOT IN (SELECT cleaned_id FROM push_records WHERE push_time >= 72h)` ✅
   - 主流程Step 5：标题+cleaned_id双重检查已推送记录 ✅
   - 记录写入时：按cleaned_id检查72h内是否已记录 ✅
4. **候选池质量优先** — 优先取方向标签+高AI评分数据，补充阶段限制严格

## 关键文件
- SOUL.md: 本索引版(4169字符)
- reports/context_index.json: 上下文索引摘要
- reports/context_pack.json: 压缩包(v2.0动态提取, 78.1%)
- reports/context_sections/: 14个章节独立文件
| - scripts/context_reconstructor.py: 章节复原工具(show/search/all/verify)

---

## 🔴 新增：6篇AI前沿文章方法论深度集成（2026-06-05 全面部署）

**以下所有能力已深度集成到Hermes底层，全部主动运行、强力执行。**

### 1. Goal Hive 蜂群协作模式（Generic Agent论文）
- 复杂任务（3+子任务/30分钟+周期）自动激活蜂群模式
- Hive Master拆目标 → 多Worker并行 → BBS任务账本 → 逐份验收 → 预算驱动
- BBS文件：`reports/hive_bbs.json`，命令：`python3 skills/autonomous-systems/goal-hive-orchestrator/scripts/goal_hive_engine.py`
- **不适用**：简单问答/统一风格创作/边界模糊任务/延迟敏感场景
- 与现有delegate_task/Agent Company/Master Loop/PRE深度融合

### 2. Sharbel 10个操作（7x24助理）
- **Operation 1**: Mission Control — 现有wake_guide + gear系统 = 内生控制面板
- **Operation 3**: Cron定时任务 — 已注册23个活跃任务，覆盖早上简报/竞品监控/流程审计
- **Operation 4**: Slash Goal持续执行 — production-reliability-engine的LoopState+goal-hive的预标驱动
- **Operation 5**: 子Agent研究团队 — delegate_task并行3路已是标准操作
- **Operation 7**: 看板 — BBS任务账本+棘轮队列+任务跟踪器三层看板
- **Operation 8**: Skills即SOP — 343个skills+skillopt验证门+证据驱动进化
- **Operation 10**: 按工种分Agent — research/analysis/implementation/audit四类Worker差异化权限

### 3. Crawl4AI 智能爬虫
- 专为LLM设计的网页爬虫，输出干净Markdown
- 作为Hermes采集管道的补充策略（API/RSS/浏览器 → Crawl4AI）
- 三级反爬：User-Agent轮换→IP切换→动态代理池
- 安装：`pip install -U crawl4ai && crawl4ai-setup`

### 4. SkillEvolver + Darwin 互优化（清华论文落地）
- Darwin 9维评估体系 + 棘轮机制（分数只升不降）
- SkillEvolver 角色分离+闭环进化 + 四类失败归因
- 互优化循环：选最低分3个skill → Darwin评估 → SkillEvolver改进 → 独立审计 → 棘轮保护
- 集成到自进化集群模块6，每天03:00自动执行

### 5. 认知蒸馏 + 受众建模
- 面向受众的输出——不是写给自己看的
- 6Agent并行蒸馏：著作/对话/表达/批评/决策/时间线
- 输出结构：心智模型 + 决策框架 + 否决触发器 + 偏好呈现
- 不限于PPT：适用于所有面向他人的输出（报告/设计/代码/方案）

### 6. Garden Skills 内容创作技能包
- **视频制作**：文字→网页演示视频，11套主题模板
- **网页设计**：25套设计风格，先定位受众再确定视觉方向
- **图片生成**：18大类/79个结构化模板，3种运行模式

### 7. 6大核心Skills
- **对抗式内容审核**：三Agent互怼（笔杆子→参谋→裁判），≥9分才放行
- **AI文本润色**：去掉AI味，增加口语化/情绪/具象化表达
- **素材搜索大师**：免费资源分类模板（图库/视频/音频/数据/案例）
- **热点雷达**：热点实时监控+蹭热点公式
- **多Agent调度中心**：Goal Hive的Worker调度层
- **记忆与知识库**：已有Hy-Memory体系（FTS5+StructMem+L1-L3）

### 强制执行规则
1. **3+子任务/30分钟+任务** → 自动激活Goal Hive蜂群模式
2. **所有内容产出** → 必须经过对抗式内容审核
3. **所有AI生成文本** → 最后一步必须humanize
4. **所有面向受众的输出** → 先蒸馏受众模型（最低：明确受众角色）
5. **每次任务开始** → 先判断是否适合开蜂巢
6. **每次任务结束** → 检查是否有可技能化的重复模式
7. **互优化循环** → 每天03:00 self-evolve集群检测最低分skill
