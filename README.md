# Hermes Agent Enhanced — 商用级AI Agent平台

## 一句话定位

基于 NousResearch Hermes Agent v0.16.0 增强的商用级AI Agent开发框架。14条代码级规则引擎 + 三省六部多Agent编排 + 10组件弹性模式。

## 核心增强模块

| 模块 | 文件 | 描述 |
|------|------|------|
| 规则强制执行引擎 | rule_enforcer.py (1454行) | 14条铁律代码级强制，R14三阶段开发 |
| 三省六部多Agent编排 | ministry_abc.py (914行) | RoleOrchestrator + WorkflowStateMachine |
| 弹性模式10组件 | resilience_patterns.py (446行) | 熔断器/重试/限流/降级/审计/指标 |
| 审计追踪系统 | audit_system.py (858行) | 对标Scale AI + AWS CloudTrail |
| 统一错误框架 | error_framework.py (549行) | RFC 7807/9457 Problem Details |
| 双AI互审系统 | dual_review_engine.py (202行) | 不同模型互审，pre_tool_call强制 |
| 环境变量安全加载 | env_loader.py (101行) | API Key安全管理 |
| 自动CI循环 | auto_ci.py (142行) | lint→test→coverage→security 30分钟循环 |
| 模型智能路由 | model_router插件 | 自动切换链，deepseek→nvidia→openrouter→google |
| 上下文压缩引擎 | force_compressor + lossless_claw | 三层压缩，使用量降低60-70% |
| 齿轮驱动自动化 | gear_enforcer.py (954行) + G0-G7齿轮系统 | 8齿轮互锁驱动，1分钟粒度强制 |
| 情报采集管道 | unified_collector_v5.py (2093行) | 48个采集器 |
| 记忆系统 | memory_engine.py (918行) + memory_evolution_v2.py (749行) | LLM双轨架构记忆 |
| Agent Company 130人 | agent_company_engine.py (485行) + runner/cron | 12部门130Agent编排 |

## 与官方Hermes对比

| 维度 | 官方v0.16.0 | Enhanced |
|------|------------|----------|
| 规则强制 | 无 | 14条代码级引擎 |
| 多Agent编排 | delegate_task | 三省六部系统 |
| 弹性模式 | 无 | 10组件 |
| 审计追踪 | 无 | 858行审计系统 |
| 错误处理 | 基础异常 | RFC 7807 Problem Details |
| CI/CD | 无内建 | auto_ci.py 30分钟循环 |
| 双AI互审 | 无 | pre_tool_call强制 |
| 模型路由 | 手动 | 自动切换链 |
| 上下文压缩 | 基础 | 三层压缩60-70% |
| 齿轮驱动 | 无 | 8齿轮互锁，1分钟粒度 |
| 自愈能力 | 无 | auto_healer + 自动恢复 |
| 记忆系统 | 基础 | LLM双轨架构 + 记忆演化 |

## 快速开始

```bash
# 克隆仓库
git clone git@github.com:Nurburgring-Zhang/hermes-agent-enhanced.git
cd hermes-agent-enhanced

# 创建虚拟环境 (推荐)
python3 -m venv venv
source venv/bin/activate

# 安装
pip install -e .

# 验证版本
hermes-enhanced-version
# 输出: 0.16.0-enhanced

# 导入测试
python3 -c "import scripts; print(scripts.__version__)"

# 运行测试
cd scripts && python -m pytest -v

# 运行CI
make check
```

> 详细安装步骤请参阅 [INSTALL.md](INSTALL.md)

## 项目结构

```
~/.hermes/
├── README.md              # 项目文档（本文件）
├── SOUL.md                # 核心契约 — 8条永久规则 + 双AI互审 + 模型路由
├── AGENTS.md              # 规则索引 + 全能力激活声明
├── CLAUDE.md              # Claude专用配置指引
├── pyproject.toml         # 项目元数据 + 依赖声明
├── config.yaml            # Hermes Agent主配置（模型/Provider/工具集）
│
├── scripts/               # 核心增强模块（346个.py文件）
│   ├── rule_enforcer.py          # R1-R14规则强制执行引擎
│   ├── ministry_abc.py           # 三省六部多Agent编排
│   ├── resilience_patterns.py    # 弹性模式10组件
│   ├── audit_system.py           # 审计追踪系统
│   ├── error_framework.py        # 统一错误框架（RFC 7807）
│   ├── dual_review_engine.py     # 双AI互审引擎
│   ├── env_loader.py             # 环境变量安全加载
│   ├── auto_ci.py                # 自动CI循环
│   ├── unified_collector_v5.py   # 情报采集管道（48采集器）
│   ├── engine_core.py            # 核心引擎
│   ├── gear_enforcer.py          # 齿轮强制执行器
│   ├── gear_master.py            # 齿轮主控制器
│   ├── gear_context_compressor.py # 齿轮上下文压缩
│   ├── gear_task_validator.py    # 齿轮任务验证器
│   ├── lossless_claw.py          # 无损压缩抓取
│   ├── memory_engine.py          # 记忆引擎
│   ├── memory_evolution_v2.py    # 记忆演化系统v2
│   ├── hierarchical_memory.py    # 分层记忆
│   ├── hy_memory_p0.py           # Hy记忆P0
│   ├── hy_memory_orchestrator.py # Hy记忆编排
│   ├── agent_company_engine.py   # Agent Company引擎
│   ├── agent_company_runner.py   # Agent Company运行器
│   ├── agent_company_cron_orchestrator.py # Agent Company定时编排
│   ├── ai_sixdim_scorer.py       # AI六维评分器
│   ├── self_pua_engine.py        # 自我提升引擎
│   ├── eternal_loop.py           # 永恒循环
│   ├── omni_loop.py              # 全知循环
│   ├── guardian.py               # 守护进程
│   ├── plan_switcher.py          # 计划切换器
│   ├── phase2_actors.py          # 阶段2角色
│   ├── forced_executor.py        # 强制执行器
│   ├── experience_extractor.py   # 经验提取器
│   ├── episodic_injector.py      # 情景注入器
│   ├── gefa_variator.py          # GEFA变异器
│   ├── gbrain_bridge.py          # GBrain桥接
│   ├── hermes_tools.py           # Hermes工具集
│   ├── hermes_multi_agent_orchestrator.py # 多Agent编排器
│   ├── hermes_intelligence_v2.py # 情报系统v2
│   ├── hermes_ai_scoring.py      # AI评分系统
│   ├── hermes_all_in_one_deploy.py # 一键部署
│   ├── hermes_memory_engine.py   # Hermes记忆引擎
│   ├── hermes_memory_engine_v2.py # Hermes记忆引擎v2
│   ├── fix_freshness.py          # 新鲜度修复
│   ├── page_snapshot.py          # 页面快照
│   ├── task_queue_manager.py     # 任务队列管理
│   ├── unified_memory_core.py    # 统一记忆核心
│   ├── unified_memory_orchestrator.py # 统一记忆编排
│   ├── parallel_memory_orchestrator.py # 并行记忆编排
│   ├── memory_orchestrator_v3.py # 记忆编排v3
│   ├── memory_tools.py           # 记忆工具
│   ├── memory_highway.py         # 记忆高速公路
│   ├── memory_index.py           # 记忆索引
│   ├── memory_compress.py        # 记忆压缩
│   ├── memory_integration.py     # 记忆集成
│   ├── memory_stats.py           # 记忆统计
│   ├── active_memory.py          # 主动记忆
│   ├── run_company_pipeline.py   # Company管道运行器
│   ├── engine_core.py            # 引擎核心
│   ├── conftest.py               # Pytest配置
│   ├── test_*.py                 # 测试文件
│   └── ...
│
├── skills/               # 378+技能模块（SKILL.md + references/）
│   ├── software-development/    # 软件开发（知影引擎/TDD/代码审计）
│   ├── engineering/             # 工程化（深度审计/数据平台/UI架构）
│   ├── autonomous-systems/      # 自主系统（模型路由/双AI互审）
│   ├── hermes/                  # Hermes运维
│   └── ...
│
├── plugins/              # 系统插件
│   ├── model_router/            # 模型智能路由插件
│   ├── force_compressor/        # 强制压缩插件
│   ├── dual_review/             # 双AI互审插件
│   ├── auto_workflow/           # 自动工作流插件
│   ├── auto_compressor/         # 自动压缩插件
│   ├── openclaw-weixin/         # 微信集成插件
│   ├── openclaw-web-search/     # 网络搜索插件
│   ├── openclaw-superintelligence/ # 超智能插件
│   ├── openclaw-airi/           # Airi插件
│   ├── plugin_system/           # 插件系统框架
│   └── ...
│
├── agents_company/       # Agent Company 240+输出文件
│   └── outputs/                 # 各部门交付物
│
├── profiles/             # Hermes多Profile配置
│   ├── ops-agent/
│   ├── commander/
│   ├── radar-agent/
│   ├── brainstorm-agent/
│   └── writing-agent/
│
├── hermes-agent/         # 上游Hermes Agent v0.16.0源码
│   ├── plugins/
│   ├── locales/
│   ├── optional-skills/
│   └── pyproject.toml
│
├── memories/             # 记忆存储
├── memory/               # 记忆运行时状态
├── state/                # 持久化状态
├── state-snapshots/      # 状态快照
├── logs/                 # 运行日志（gear_enforcer/workflow/memory等）
├── reports/              # 运行报告（审计/压缩/工作流状态）
├── outputs/              # 输出产物
└── lsp/                  # LSP语言服务器（Pyright）
```

## 架构概览

```
                    ┌──────────────────────────────────────┐
                    │         Hermes Agent v0.16.0         │
                    │         (NousResearch 上游)           │
                    └──────────────┬───────────────────────┘
                                   │
                    ┌──────────────▼───────────────────────┐
                    │      规则强制执行引擎 (R1-R14)         │
                    │   rule_enforcer.py — 每次tool调用前后   │
                    └──────────────┬───────────────────────┘
                                   │
         ┌─────────────────────────┼─────────────────────────┐
         │                         │                         │
  ┌──────▼──────┐          ┌──────▼──────┐          ┌──────▼──────┐
  │  三省六部     │          │ 双AI互审     │          │ 弹性模式     │
  │ ministry_abc │          │ dual_review │          │ resilience  │
  │ 多Agent编排   │          │  pre+post   │          │ 10组件      │
  └──────┬──────┘          └──────┬──────┘          └──────┬──────┘
         │                         │                         │
         └─────────────────────────┼─────────────────────────┘
                                   │
                    ┌──────────────▼───────────────────────┐
                    │          齿轮驱动系统 (G0-G7)           │
                    │     gear_enforcer — 1分钟粒度强制       │
                    └──────────────┬───────────────────────┘
                                   │
         ┌─────────────────────────┼─────────────────────────┐
         │                         │                         │
  ┌──────▼──────┐          ┌──────▼──────┐          ┌──────▼──────┐
  │  记忆系统     │          │ 审计追踪     │          │ 自动CI       │
  │ memory_eng  │          │ audit_sys   │          │ auto_ci.py  │
  │ 双轨架构     │          │ 858行审计    │          │ 30分钟循环   │
  └─────────────┘          └─────────────┘          └─────────────┘
```

## 技术栈

- **语言**: Python >= 3.10
- **LLM**: OpenAI / Anthropic / DeepSeek / NVIDIA / OpenRouter
- **框架**: Pydantic v2 / httpx / aiohttp
- **测试**: pytest
- **构建**: setuptools + wheel
- **许可**: MIT

## 许可证

MIT License — Copyright (c) 2024-2026 Nous Research

本项目基于 [NousResearch Hermes Agent](https://github.com/NousResearch/hermes-agent) v0.16.0 增强开发，所有增强模块以MIT协议开源。
