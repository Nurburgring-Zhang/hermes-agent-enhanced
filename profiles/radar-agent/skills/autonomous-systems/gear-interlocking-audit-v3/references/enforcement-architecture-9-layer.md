# 全对话永久生效方法论 — 9层固化架构
# 格林主人最高指令：所有设定必须"在所有对话、所有会话、所有上下文中永久生效"
# 来源会话：2026-05-24 大规模7条规则+OI方案全量固化
# 适用: 任何需要"永久生效"的系统设定

## 核心原则

用户要求的是**底层设定**而非临时配置。这意味着不能只写在一个地方。
必须建立**多层冗余固化体系**，让每次对话、每次终端启动、每次wake_init
都自动加载这些设定，任何一层失效时其他层兜底。

## 9层固化架构

| 层 | 文件/机制 | 范围 | 特点 |
|:-:|----------|:----:|------|
| 1 | **SOUL.md** | 本对话系统 | Agent每次对话自动读取，最核心的灵魂文件 |
| 2 | **AGENTS.md** | Claude Code/Copilot/Cline/Windsurf | 跨Agent兼容格式 |
| 3 | **CLAUDE.md** | Claude Code专用 | 专用规则文件，Claude CLI自动加载 |
| 4 | **.cursorrules** | Cursor IDE | IDE强制加载 |
| 5 | **memory** | 每个对话 | 每次对话自动注入上下文(<=2200字) |
| 6 | **wake_init.sh** | 每次终端启动 | 通过~/.bashrc注入 | 
| 7 | **gear_enforcer.py** | 每1分钟cron | 全能力监督+齿轮完整性 |
| 8 | **task_monitor.py** | 每10分钟cron | 7条规则自检+全能力扫描 |
| 9 | **ability_activator.py** | 每1小时cron | 激活遗漏能力+模块语法验证 |

## 权威验证器

```bash
python3 ~/.hermes/scripts/verify_rules.py
# 检查: SOUL.md + AGENTS.md + CLAUDE.md + .cursorrules +
#        task_monitor + gear_enforcer + wake_init + ability_activator + cron
# 输出: 9/9 ✅
```

## 模式：如何新增一个"永久生效"的设定

```markdown
步骤1: 写入 SOUL.md（核心文件，使用patch追加章节）
步骤2: 写入 AGENTS.md（跨代理兼容）  
步骤3: 写入 CLAUDE.md（Claude Code专用）
步骤4: 写入 .cursorrules（Cursor IDE专用）
步骤5: 写入 memory（使用memory add/replace）
步骤6: 检查verify_rules.py是否需要更新关键词
步骤7: 运行 verify_rules.py 确认9/9通过
```

## OI全量方案固化模式（50项+15项指标）

当需要从多份文档中提取大量方案并固化为底层设定时：

1. **全量阅读** — 使用delegate_task多路并行读取所有文档
2. **提取归类** — 按7类归类：记忆/任务/进化/安全/架构/性能/多Agent
3. **编写主清单** — 用extract_oi_plans.py统计7大类55个子方案
4. **写入SOUL.md§九** — 每个方案标注固化方式（哪段代码/哪个机制）
5. **写入15项量化指标** — 所有实现必须达到LongMemEval≥90%等
6. **写入AGENTS.md/CLAUDE.md/.cursorrules索引** — 简明索引指向SOUL.md
7. **verify_rules.py更新** — 确认包含"OI项目全量优化增强方案固化"关键词

## 已固化的全量方案索引

SOUL.md§九现在包含从6份OI文档提取的完整方案（372行SOUL.md）：

- **记忆系统(8项)**: OPME七通道/五层L0-L4/三冗余引擎/三路径压缩/认知退化/Sleeptime/永久转换/LCM DAG
- **任务执行(11项)**: DPW双规划器+见证者/KDN审计/三级纠偏/COMPASS三层/热温冷上下文/四级漂移/Kitaru+LangGraph/DAG解耦/PIVOT/CaveAgent/TodoWrite
- **自我强化(10项)**: 三级循环/GEPA优化/CASE编辑/五环节/SelfEvolution六步/Memento-Skills/反思微调/Council仲裁/三条固化/四回路
- **安全(4项)**: DDSPE五层/零信任七支柱/L0-L3等级/P0-P3事件
- **架构(6项)**: 四大原则/三三制冗余/IFC核心/原生部署/Hooks八事件/子Agent管理
- **性能(7项)**: TokenJuice/Mermaid卸载/Mem0层/TriAttention/INT8量化/2KB预览/动态上下文
- **多Agent(4项)**: A2A协议/ACP协议/六模块调度/Crew五操作
- **量化指标(15项)**: LongMemEval≥90%/恢复<5秒/偏移≤5%/信息保留率≥99.999%/检索<200ms/泄露0
