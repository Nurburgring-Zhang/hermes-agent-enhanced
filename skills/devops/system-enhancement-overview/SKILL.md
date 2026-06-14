---
name: system-enhancement-overview
description: 系统增强总览 — 三重冗余(记忆/任务/数据) + 6必备技能索引 + 全增强模块清单。作为Hermes增强版与官方版的差异查询入口。
---

# System Enhancement Overview

## 我们 vs 官方：增强总览 (2026-06-12更新)

当前Hermes v0.16.0 (upstream d62979a6) 基础上做了约250,000+行自定义代码增强。以下按23大分类组织。

### 核心规模数据
| 指标 | 原版 | 增强版 | 增长 |
|------|------|--------|------|
| 自定义Python脚本 | ~0 | ~293 个 | ∞ |
| Skills | ~18 组 | ~180 组 (163自定义) | 10x |
| 插件 | ~0 | 13 个 (6正式+7子模块) | ∞ |
| Cron jobs | ~0 | 66+ 独立任务 (137行crontab) | ∞ |
| Agent Company | 无 | 117+ 员工, 12部门 | ∞ |
| Expert System | 无 | 390+ 专家, 30+领域 | ∞ |
| 总代码量 | ~50-80K 行 | ~250,000+ 行 | 3-5x |
| 修改官方文件 | — | 5个 (conversation_loop/tool_executor/model_tools/run_agent/hermes_cli) | — |

### 核心代码注入 (5处修改的官方文件)
- `agent/conversation_loop.py` — PRE hook，每次LLM调用前注入增强指令
- `agent/tool_executor.py` — 工具执行前拦截，规则引擎注入
- `run_agent.py` — POST hook，每次对话turn后触发复盘+记忆+进化
- `model_tools.py` — 系统启动层自动加载rule_enforcer.py (967行, 13条SOUL.md规则全部代码强制)
- `hermes_cli/__init__.py` — 启动时加载双审规则

### 13条SOUL.md规则（全部代码强制）
| 规则 | 功能 | 强制方式 |
|------|------|---------|
| R1 反幻觉铁律 | 工具调用结果真实性验证 | model_tools自动注入 |
| R2 前置三查 | 每任务自动session_search+memory+skill | conversation_loop自动执行 |
| R3 改前备份 | 所有修改前自动cp到/mnt/d/Hermes/备份/ | tool_executor拦截 |
| R4 交付铁律 | 提交前验证真实运行证据 | run_agent检查 |
| R5 深度审核 | 审核必须包含运行测试证据 | rule_enforcer检查 |
| R6 沟通风格 | 禁用37个AI味词汇+4种模糊表述+AI开场白 | 正则匹配 |
| R7 自主边界 | 18条敏感操作三级响应(block/warn/alert) | 分级拦截 |
| R8 问责制 | 被忽略的产出自动标记 | 记录追踪 |
| R9 双AI互审 | 执行AI vs 监督AI不同provider | 强制pre/post_review |
| R10 防降级实现 | 24种降级模式检测(占位词/未完成/mock/固定返回) | 代码扫描 |
| R11 迭代验证 | 循环上限保护+完成状态验证 | run_count超限STOP |
| R12 SDLC强制执行 | 7步SDLC别名匹配+步骤完整性强制 | 步骤链验证 |
| R13 模型路由 | 按任务难度自动选择最优模型 | 路由链强制

### 6插件系统 (不可绕过)
| 插件 | 注入点 | 功能 |
|------|--------|------|
| dual_review | pre_tool_call hook | 双AI互审, 执行AI vs 监督AI不同模型 |
| model_router | post_tool_call hook + pre_tool_call | 7层路由链, 自动切换 |
| force_compressor | pre_context_load + post_tool_call 双hook | 强制上下文压缩, SHA256校验 |
| auto_compressor | post_response hook | 响应后自动压缩 |
| auto_workflow | post_llm_call hook | LLM调用后自动触发Workflow |
| plugin_system | 框架 | Plugin/Registry/Manager/EventBus |

### G0-G8 齿轮系统 (8层可靠性链)
| 齿轮 | 频率 | 功能 |
|------|------|------|
| G1 gear_enforcer | 每分钟 | 中断检测+AI评分+wake_guide写入 |
| G2 context_failsafe | 每5分钟 | 合并断点+恢复包 |
| G3 gear_context_compressor | 每5分钟 | 上下文压缩检查点 |
| G4 hermes_retrospect | 每15分钟 | 复盘审计 |
| G5 hermes_super_guardian | 每15分钟 | 全系统兜底 |
| G6 gear_task_validator | 每30分钟 | 全链完整性验证 |
| G7 wake_guide | 每分钟 | 醒来指南 |
| G8 production_loop_cron | 每10分钟 | 生产可靠性 |

### 智能系统
| 系统 | 规模 | 说明 |
|------|------|------|
| Agent Company | 130员工,12部门 | 市场→设计→架构→计划→开发→测试→交付 |
| Expert System | 390专家,30领域 | AI/云/安全/金融/医疗等 |
| 模型路由 | 5级自动切换 | flash→chat→pro→glm→gemini/Claude |
| 双AI互审 | PRE+POST | 不同模型监督，高风险自动拦截 |

### 情报系统 (30+平台全自动)
| 平台 | 采集方式 | 频率 |
|------|----------|------|
| 微信公众平台 | 多路冗余v9 (Bing+搜狗+Playwright) | 每3小时 |
| 今日头条 | 增强采集v4 (多API端点) | 每3小时 |
| 小红书 | Playwright SSR DOM提取 | 每3小时 |
| 微博/快手/CSDN | 多Context轮换 | 每3小时 |
| 海外平台 | 海外增强采集 | 每6小时 |
| RSS订阅 | 统一RSS订阅源 | 每3小时 |
| **核心** | unified_collector_v5.py (2,089行, parallel=8/14) | — |

### 清洗评分系统
- 采集时预筛: blog>150字符, 垃圾过滤
- 增量清洗: 基于raw_id去重
- 六维AI评分: 时效性/权威性/相关性/创新性/实用性/可读性
- 热点保底: 前20条/平台自动放行
- 偏好匹配: 方向标签+649宽泛白名单(16分类)
- 低分数据自动归档清理

### 推送系统
- PushPlus微信推送: 4次/天 (8:00/14:00/20:00/22:00)
- 时间衰减评分: AI评分+时间衰减排序
- 72小时三保险去重
- 兴趣偏好P0/P1/P2分类+讨厌内容过滤

### 记忆系统 (Hy-Memory v2 三层认知架构)
| 层 | 周期 | 功能 | 文件 |
|-----|------|------|------|
| L1 LLM提取 | 每2小时 | 对话→结构化记忆 | l1_extractor.py (770行) |
| L2场景归纳 | 每6小时 | 情景→模式聚合 | l2_scene_scheduler.py (420行) |
| L3画像生成 | 每天5:00 | 用户画像+领域知识 | l3_persona_scheduler.py (390行) |
| RAG索引 | 实时 | 向量嵌入+语义搜索 | hermes_vector_engine.py (164行) |
| 跨会话缓存 | 每30分钟 | session间记忆共享 | cross_session_cache.py |
| 经验提取 | 每60分钟 | 复盘→经验→Skill | experience_extractor.py (600行) |
| 情景注入 | 每30分钟 | 唤醒时自动注入 | episodic_injector.py (280行) |
| 记忆进化 | 每天03:00 | 自动技能沉淀 | memory_evolution_v2.py (744行) |

### 安全系统
- CaMeL审计: 每30分钟
- tirith预执行扫描: 命令执行前
- 路径验证: 文件操作前
- SSRF加固: web请求前

### 上下文系统
- Lossless-Claw无损压缩: QMD+三级策略
- gear_context_compressor: 每5分钟
- 段切换: 每50轮自动归档
- 三明治协议: 信息无损交接

### 守护系统
- long_task_guardian: 15分钟三路冗余
- task_resumer: 断点续跑
- auto_healer: 每5分钟退化修复
- hermes_super_guardian: 每15分钟全系统兜底

### 6必备技能索引
- 对抗式内容审核 — 三Agent互审
- AI文本润色 — text-humanizer-unified
- 素材搜索大师
- 热点雷达
- 多Agent调度中心
- 记忆与知识库

## 使用场景

**问我们都做了什么增强**: 优先读这个skill + 展开各域子skill。完整23类对比报告在 /mnt/d/Hermes/备份/hermes_pre_upgrade_20260612_221543/Hermes_增强对比总结.md

**升级前对比**: 读这个skill + zhiying-dev-engine skill的 Hermes自身升级工作流 部分 + references/hermes-upgrade-and-compare-workflow.md

**需要诊断某模块**: 找到对应域的skill并用skill_view加载
