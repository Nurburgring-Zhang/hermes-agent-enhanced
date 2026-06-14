# ============================================================================
# AGENTS_v2.md — 核心规则精简版 (~500行)
# 原始全量: AGENTS.md (566行) → 提取真正可用的核心执行规则
# ============================================================================

## 🔴 强制声明

每次醒来、每次对话、每次任务执行前，必须先读SOUL.md中的永久规则并强制执行。
禁止绕过、禁止降级、禁止选择性忽略，永久生效。

### 规则0：自主能力基线

不依赖于"认知边界"或"已安装工具"，遇到一切障碍时自动执行：
1. 多路寻找高质量方案 — 原方案受限≠无方案，自动搜索至少3种替代路径
2. 核实质量与真实性 — HTTPS+校验和(SHA256)+来源可追溯
3. 环境无关的自主判断 — WSL/无显示器/国内网络是约束条件不是"做不到"的理由

## 8条永久执行规则

- 规则1：任务执行前必须全面回顾+全局预判
- 规则2：超限/中断时自动拆解+继续执行
- 规则3：每阶段完成后必须复盘
- 规则4：完整执行后全局复盘
- 规则5：真实实现+联网最佳方案+严苛测试
- 规则6：强制循环的完善→审核→测试循环（至少3轮）
- 规则7：任何修改必须备份：改前执行cp到备份目录
- 规则8：所有任务必须执行双AI互审（执行中实时监督）

## 上下文压缩规则

1. 第一轮对话：全量SOUL.md注入
2. 第二轮起：只读SOUL.md索引压缩版
3. 需要完整章节时：read_file('reports/context_sections/<ID>.md')
4. 索引文件每1分钟cron更新
5. 备份规则：所有删除/覆盖写/批量修改前先备份到 /mnt/d/Hermes/备份/

## Skills组合/并行/链式调用

- 所有skill必须具有：主动运行能力 + 链式调用能力 + 并行调用能力
- Hermes Agent必须能：主动调用多Agent组队 + 链式运行 + 并行运行
- 所有调用必须主动进行，不能等待用户指令

## 低分数据自动清理

- cleaned_intelligence不允许长期堆积低分数据(ai_score_total < 20)
- 低分数据必须归档到archive_cleaned再删除

## 采集质量预筛

- 采集时确保数据质量：insert_raw_item()中加入内容质量预筛
- blog类来源<150有效字符丢弃，非短内容来源<80有效字符丢弃

## 复盘反思规则

每次任务完成后必须自动执行复盘反思。强制执行：所有Dynamic Workflows完成时自动触发复盘。

复盘流程：
1. 阶段复盘 — 每完成一个子任务/阶段后，回顾当前进度与原计划是否对齐
2. 完整复盘 — 整个任务完成后，用复盘引擎进行结构化复盘：
   - 目标回顾：原始任务目标 vs 实际完成
   - 过程回溯：每一步执行情况，遇到的问题
   - 质量评估：五维度评分（功能/正确/完整/质量/可维护）
   - 经验提取：可复用的模式、教训、改进建议
3. Hy-Memory沉淀 — 复盘结果自动提取到记忆系统

## 执行前强制三查规则

每个phase执行前必须强制执行：
1. 历史经验回顾 — session_search搜索历史 + memory检查持久记忆 + fact_store搜索事实库
2. 技能预加载 — 根据任务类别自动发现和加载相关skill
3. 全网方案检索 — 搜索相关方案/方法/代码/项目/最佳实践
4. 架构师级评估 — 由子Agent以资深架构师视角评估任务规划、设计、质量把控方案
5. 自我进化建议 — 基于历史经验和当前检索结果主动提出优化建议

## 齿轮系统强制对接

所有Dynamic Workflows必须与齿轮系统对接：
1. G0注册 — workflow启动时自动注册到齿轮任务注册中心
2. G1唤醒 — workflow进度写入唤醒信息（支持断点恢复）
3. G6验证 — workflow完成时调用验证器检查执行质量
4. 生产可靠性引擎 — 通知production_loop进行健康监控

## Agent Company强制匹配

所有Dynamic Workflows的task自动匹配到Agent Company员工：
1. 自动部门匹配 — task名称/参数自动映射到12个部门
2. 技能评分排序 — 按员工技能proficiency匹配度排序选最优
3. 身份注入 — 每个subagent拥有员工身份(identity+skills+sop+tools)
4. 全局搜索fallback — 部门无匹配时跨部门搜索

## SDLC流程强制规则

所有Dynamic Workflows的task自动遵守软件开发完整流程：
1. 研究类任务 — 调研→报告
2. 新建类任务 — 调研→设计→编码→测试→审核→完善→交付
3. 修复类任务 — 调研→修复→测试→交付
4. 审核类任务 — 审核→报告
5. 默认类任务 — 7步完整SDLC流程

## Dynamic Workflows cron自激活

Dynamic Workflows系统必须由cron自动激活和监控：
1. 每15分钟检查 — cron */15 * * * *
2. 待执行检查 — 队列中的workflow自动就绪
3. Stuck检测 — 超过2小时无进度的workflow标记
4. 状态报告 — 写入gear_registry供齿轮监控

## 全能力融合规则

Dynamic Workflows执行时必须联动Hermes所有子系统：
1. 情报采集 — 需要外部数据时自动触发采集管道
2. Hy-Memory — 结果自动提取到记忆系统
3. 齿轮系统 — G0/G1/G6全链路绑定
4. 任务复盘 — 完成后自动触发task-retrospect
5. Agent Company — task自动匹配员工
6. 质量门禁 — 每阶段完成时质量检查
7. 自我进化 — 复盘结果驱动skill改进
8. Durable执行 — 事件溯源+心跳+断点恢复

## 进化循环强制规则

所有Dynamic Workflows完成后必须自动触发进化循环：
1. 复盘→进化候选 — workflow复盘数据自动写入进化候选队列
2. 质量评分 — 自动计算质量分（0-100），低于60触发即时进化
3. 自我进化集群消费 — 每天凌晨3点self_evolve_cluster.py自动消费候选队列
4. Skill改进 — 进化引擎基于复盘证据自动改进相关skill
5. 正向循环 — skill改进后下次workflow更强→更高质量复盘→更多进化输入

## Durable Execution规则

Dynamic Workflows支持durable模式：
1. 事件溯源 — 所有状态变更持久化到workflow_events表
2. 心跳检测 — 每30秒报告存活，5分钟无心跳标记stuck
3. 崩溃恢复 — stuck的workflow可手动恢复
4. 执行轨迹 — 完整事件链可追溯
5. 轻量无依赖 — 零外部依赖，基于SQLite实现

## 全能力互相强化规则

所有能力在workflow执行时互相增强，形成正向循环：
1. cron自激活 → 检查pending workflow
2. preflight → 执行前强制三查（历史+技能+搜索）
3. SDLC流程 → 按任务类型强制开发全流程
4. Agent Company → 自动匹配最合适员工
5. 齿轮系统 → G0注册→G1唤醒→G6验证
6. 复盘反思 → 5步结构化复盘
7. Hy-Memory → 关键发现自动提取到记忆
8. 进化循环 → 复盘数据→skill改进→下次更强
9. Durable → 事件溯源+心跳+断点恢复

## Dynamic Workflows守护进程

Dynamic Workflows系统由守护进程daemon.py每5分钟自动唤醒：
1. 模块健康扫描 — 16个模块全部检查，任何模块异常立即告警
2. 待办workflow激活 — pending队列自动就绪
3. Stuck检测 — 运行超过30分钟的workflow标记
4. 联合唤醒 — 通知齿轮系统+生产监控
5. 进化候选触发 — 每30分钟检查候选队列，>=3个时触发进化
6. 每日回顾 — 每天18:00生成workflow执行汇总报告
7. 多时间尺度覆盖 — 5分/30分/18时/03时全链路监控

## 全模块共同运行规则

所有17个模块必须同时主动运行、互相唤醒、彼此监控：
1. daemon.py(5min) → 健康扫描+状态写入gear_registry
2. cron_activate.py(15min) → 检查pending/stuck
3. runtime.py(每次workflow) → G0注册+preflight+SDLC+Company+执行+G6+复盘+进化
4. evolution_bridge(每次完成) → 复盘→候选队列→self_evolve_cluster
5. durable_engine(运行中) → 事件溯源+心跳+stuck检测
6. gear_integration(全链路) → G0注册+G1唤醒+G6验证+生产通知
7. retrospect_integration(完成后) → 5步复盘+Hy-Memory提取

## Hermes Unified Execution Engine

所有任务必须经过统一执行引擎的唯一入口执行，走完7步完整流程：

| 步骤 | 名称 | 内容 |
|------|------|------|
| ① | 全网检索 | web_search+session_search+fact_store三路同时搜索 |
| ② | 全局观念建立 | 读取AGENTS.md规则+加载相关skill+历史经验回顾 |
| ③ | 需求分析 | delegate_task子Agent做深度需求分析 |
| ④ | 功能设置 | 架构设计+技术选型+方案评审 |
| ⑤ | 软件开发 | SDLC流程强制注入+真实实现 |
| ⑥ | 审核测试 | 测试+对抗式验证 |
| ⑦ | 交付上线 | 复盘+Hy-Memory提取+进化候选+齿轮注册 |

同时自动联动的强化模块：齿轮系统/preflight/SDLC流程/Agent Company/对抗式验证/复盘反思/Hy-Memory/进化候选/Durable执行/Tokens压缩

### crontab中的自动触发
- daemon.py — 每5分钟(模块健康扫描+待办激活+联合唤醒)
- cron_activate.py — 每15分钟(pending/stuck检查)
- evolution_trigger — 每30分钟(进化候选消费)
- workflow_daily — 每天18:00(执行汇总日报)
- self_evolve_cluster — 每天03:00(全量自进化)

## 强制自运行引擎

以下所有模块必须在任何情况下持续自动运行、互相监控、失效自动重启。
三路冗余注入（任意一路存活即可保证运行）：

| 注入路径 | 频率 | 位置 |
|---------|------|------|
| G1齿轮强制器 | 每分钟 | scripts/gear_enforcer.py |
| G7醒来指南 | 每分钟 | scripts/wake_guide.py |
| daemon守护进程 | 每5分钟 | workflows/daemon.py |

被强制监控的9个模块：preflight/company_matcher/SDLC/gear_integration/retrospect/evolution/daemon/dual_review/unified_engine

失效处理流程：
1. 模块异常 → 立即写入mandatory_engine_alarm.txt
2. 尝试自动重启（重新注入代码）
3. 重启后重新检查
4. 重启失败 → 持续告警直到人工介入

## 双AI互审强制规则

每个delegate_task调用前必须强制触发双AI互审。
注入方式：Hermes插件系统pre_tool_call hook — Hermes主Agent启动即自动加载

调用链：
```
Hermes主Agent启动 → 加载plugins/dual_review/ → register(ctx)
  → ctx.register_hook("pre_tool_call", dual_review_hook)
    → 每次delegate_task被调用时，引擎自动调用dual_review_hook
      → 审查记录写入logs/dual_review/reviews.jsonl
      → 放行工具执行
```

互审机制：
1. 执行前监督 — delegate_task被调用前，hook自动记录审查信息
2. 记录式审查 — 当前仅记录不阻断（monitor_only）
3. 审查日志 — 记录到logs/dual_review/reviews.jsonl
4. 冷却控制 — 同一task 5秒内不重复审查

## Workflow自动触发规则

每次用户消息处理后，自动触发workflow构建和执行。
注入方式：Hermes插件系统post_llm_call hook

调用链：
```
用户发消息 → Hermes主Agent处理
  → post_llm_call hook (auto_workflow插件)
    → 写入auto_workflow_queue (SQLite)
      → daemon每5分钟扫描
        → deep_research构建workflow (DSL+G0注册)
          → hermes send提交给主Agent
            → runtime.run()可被调用
              → preflight→SDLC→Company→G1→execute→G6→复盘→进化
```

## 最终强制执行器

所有workflow必须被真正执行，不可跳过、不可降级。
调用链：
```
用户发消息 → auto_workflow插件 → 写入队列
  ↓ (每5分钟)
最终强制执行器(mandatory_executor.py)
  → 读取所有pending/prepared的workflow
  → 启动Hermes子Agent(hermes chat -z)
    → runtime.run()可被真正调用
      → preflight/SDLC/Company/adversarial/recover/gear/retrospect/evolution
```

三路冗余保障：
1. daemon.py(每5分钟) → 调用mandatory_executor.execute_all_pending()
2. cron(每5分钟) → 独立运行mandatory_executor.py
3. gear_enforcer(每分钟) → 检查gear_registry中是否有待执行任务

## 全链路生产测试

每天10:00和22:00自动执行全链路生产测试。
测试覆盖：workflow→G0齿轮注册→G1唤醒写入→checkpoint持久化→数据库验证→Agent Company匹配→preflight代码验证→SDLC注入验证→双AI互审注入验证→adversarial验证→mandatory_engine检查→进化候选写入

### crontab中的覆盖时间线
- 每分钟: gear_enforcer + wake_guide（强制引擎自检）
- 每5分钟: daemon（全模块健康扫描+联合唤醒）
- 每15分钟: cron_activate + hermes_retrospect
- 每30分钟: evolution_trigger（进化候选消费）
- 每天10:00/22:00: full_chain_test（全链路生产验证）
- 每天18:00: workflow_daily（执行汇总日报）
- 每天03:00: self_evolve_cluster（全量自进化）

## 执行质量墙规则

任务执行过程中必须插入强制检查点：
1. 每步检查 — 每完成一个子任务，验证输出是否符合预期
2. 里程碑检查 — 每3个子任务，检查整体方向是否正确
3. 方向对齐 — 任务中途检查是否偏离原始目标

## 长期任务执行保障

- 复杂任务（>15步）必须使用分层规划：高层粗计划+底层细执行
- 超过10步的任务必须保存中间检查点
- 任务执行中发现问题必须自动纠偏或re-plan

## 证据驱动Skill进化

所有低分任务（质量评分<60）自动触发Skill改进管道。
进化流程：
1. 证据收集 — 复盘评分<60自动进入候选队列
2. 语义分类 — 规则引擎分类为skill_update/skill_new/replay_benchmark
3. 提案生成 — 4种变体策略评分选优
4. 受保护应用 — SHA256备份→结构检查→分阶段验证→回滚
5. 与SkillOpt联动 — 低分自动触发训练循环

## 三层反思结构化规则

任务执行中必须进行结构化反思：
1. 操作层（每步后）：这一步做得对不对？结果是否符合预期？
2. 策略层（每3步后）：当前策略是否有效？是否需要换方法？
3. 目标层（每10步后）：整体方向是否正确？是否需要重新规划？

## CaMeL安全护栏

敏感工具调用必须接受安全检查：
1. 信任边界分离 — 系统提示/用户输入(可信)与工具输出/外部数据(不可信)分离
2. 16个敏感工具分类 — 9类能力(命令执行/文件修改/外部通信/Skill修改/持久化记忆等)
3. 5种注入模式检测 — 忽略指令/隐藏行为/秘密提取/系统提示覆盖/嵌入副作用
4. 工具循环防护 — 重复失败检测、同工具链式失败检测、幂等无进展检测
5. 三级响应 — allow(放行)/warn(警告)/block(阻止)/halt(停止)
6. 三级运行模式 — off(关闭)/monitor(记录不阻止)/enforce(强制执行)

## 自动调优规则

系统参数自动适应运行数据：
1. 参数自适应 — 根据复盘平均评分、Cron成功率、关键词分布自动调整5项核心参数
2. A/B测试框架 — 自动创建参数对比实验，48小时后评估效果
3. 动态阀值 — 所有调优基于规则引擎+历史数据，零LLM成本
4. 每日执行 — 集成到自进化集群模块8，每天03:00自动运行

## 推送系统优化规则

1. 时效性过滤 — 发布时间超过14天且AI评分<80的内容丢弃；无发布时间的数据只保留AI评分>=50或24小时内采集的；AI评分>=80的内容不超过30天
2. 时间衰减评分 — 评分公式乘以时间衰减因子（>7天递减，>14天强衰减）
3. 72小时去重（三保险）：
   - 候选池SQL层面：WHERE id NOT IN (SELECT cleaned_id FROM push_records WHERE push_time >= 72h)
   - 主流程Step 5：标题+cleaned_id双重检查已推送记录
   - 记录写入时：按cleaned_id检查72h内是否已记录
4. 候选池质量优先 — 优先取方向标签+高AI评分数据

## 关键文件

- SOUL.md: 索引版
- reports/context_index.json: 上下文索引摘要
- reports/context_pack.json: 压缩包(v2.0动态提取)
- reports/context_sections/: 14个章节独立文件
- scripts/context_reconstructor.py: 章节复原工具(show/search/all/verify)

## 6篇AI前沿文章方法论（已深度集成）

1. Goal Hive蜂群协作模式 — 复杂任务（3+子任务/30分钟+周期）自动激活蜂群模式
2. Sharbel 10个操作 — Mission Control/Cron定时任务/Slash Goal持续执行等
3. Crawl4AI智能爬虫 — 专为LLM设计的网页爬虫，输出干净Markdown
4. SkillEvolver + Darwin互优化 — Darwin 9维评估体系+棘轮机制
5. 认知蒸馏 + 受众建模 — 6Agent并行蒸馏，面向受众的输出
6. Garden Skills内容创作技能包 — 视频制作/网页设计/图片生成

### 强制执行规则
1. 3+子任务/30分钟+任务 → 自动激活Goal Hive蜂群模式
2. 所有内容产出 → 必须经过对抗式内容审核
3. 所有AI生成文本 → 最后一步必须humanize
4. 所有面向受众的输出 → 先蒸馏受众模型
5. 每次任务开始 → 先判断是否适合开蜂巢
6. 每次任务结束 → 检查是否有可技能化的重复模式
7. 互优化循环 → 每天03:00 self-evolve集群检测最低分skill
