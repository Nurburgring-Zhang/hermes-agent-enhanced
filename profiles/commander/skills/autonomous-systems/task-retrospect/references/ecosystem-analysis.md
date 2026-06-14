# Hermes Ecosystem Deep Analysis (2026-05-30)

基于实际源码分析的4个Hermes生态开源项目，用于复盘→Skill进化参考。

## 1. hermes-curator-evolver (pingchesu)

**GitHub**: https://github.com/pingchesu/hermes-curator-evolver
**源码分析**: 1379行Python, 5核心文件
**核心模式**: 证据驱动Skill进化闭环

### 核心机制
- **证据收集** (`hooks.py`, ~200行)：3个Hermes Plugin Hook（on_post_tool_call/on_post_llm_call/on_session_end），无侵入SQLite存储
- **证据存储** (`storage.py`, 356行)：SQLite三表（tool_events/turn_events/session_events），含`_quarantine_corrupt_db()`优雅处理
- **语义分类** (`candidates.py`, ~400行)：规则引擎将证据分类为 memory/skill_update/skill_new/replay_benchmark/ignore，含中英文Workflow正则识别
- **变体生成** (`auto_evolve.py`, 1321行)：4种确定性变体策略：
  - verify-first: 先验证当前方案，再决定是否改写
  - evidence-first: 基于证据重写
  - errors-first: 只修复已知错误
  - spillover-minimal-inline: 最小改动+内联补丁
- **受保护写入** (`guarded_apply.py`, ~500行)：SHA256校验→备份→内置结构检查→分阶段校验(廉价→昂贵)→自动回滚→来源溯源→Pin检测→容量限制
- **来源溯源** (`skill_sources.py`, ~200行)：读取bundled_manifest/hub/lock.json/external_dirs，只允许写入local-agent-created skill
- **恢复演练** (`restore_drill.py`, ~200行)：将回滚Manifest回放到临时目录验证

### 可借鉴设计
- **零LLM成本**：全部用规则引擎，不依赖LLM调用
- **分阶段校验**：内置结构检查(廉价)→Pre-verify(可选)→主Verify(昂贵)
- **来源溯源门禁**：保护核心skill不被误改

## 2. SkillClaw (AMAP-ML)

**GitHub**: https://github.com/AMAP-ML/SkillClaw
**源码分析**: Client Proxy + Evolve Server双组件架构

### 核心机制
- **API代理拦截** (`api_server.py`, 3438行)：FastAPI代理v1/chat/completions和v1/messages，拦截时注入Skill到System Prompt
- **Session Summarizer** (`pipeline/summarizer.py`, ~500行)：LLM从轨迹构建结构化摘要
- **Session Judge** (`pipeline/session_judge.py`, ~300行)：4维度加权评分(completeness/difficulty/efficiency/reusability)
- **Aggregation** (`pipeline/aggregation.py`, ~200行)：按引用的skill分组
- **Evolution Executor** (`pipeline/execution.py`, ~400行)：4种LLM决策类型(create/update/merge/archive)
- **Multi-Agent适配器** (`claw_adapter.py`, 1708行)：8+ Agent统一注册到`_ADAPTERS`字典

### 可借鉴设计
- **Collective进化**：N个用户共享同一个Evolve Loop
- **Session评判**：4维度评分可复用为复盘引擎的增强
- **适配器模式**：_ADAPTERS字典统一管理多Agent

## 3. hermes-agent-camel (nativ3ai)

**GitHub**: https://github.com/nativ3ai/hermes-agent-camel
**源码分析**: 信任边界安全护栏

### 核心机制
- **信任分离** (`camel_guard.py`, 964行)：可信控制输入 vs 不可信数据输入，后者添加 `[CaMeL: UNTRUSTED TOOL DATA]` 前缀
- **敏感工具分类**：9类能力(command_execution/file_mutation/external_messaging/skill_mutation/persistent_memory/browser_interaction/delegation/scheduled_action/external_side_effect)
- **懒惰LLM分类器**：从用户输入提取意图，返回allowed_capabilities和denied_capabilities
- **注入检测**：5种正则模式(ignore previous instructions/hide from user/secret exfiltration/system prompt override/embedded side effect)
- **工具循环防护** (`tool_guardrails.py`, 455行)：ToolCallSignature(工具名+参数Hash)+三级响应(allow/warn/block/halt)
- **三模式运行时**：off/monitor/enforce

### 可借鉴设计
- Trusted↔Untrusted分离是安全Agent架构的黄金模式
- 懒惰分类器以最低成本实现安全门控

## 4. hermes-plugin-lineworks (Unayung)

**GitHub**: https://github.com/Unayung/hermes-plugin-lineworks

### 核心机制
- **Webhook处理** (`adapter.py`, 797行)：HMAC-SHA256验证+JWT Bearer Token+Refresh skew+single-flight锁
- **多账号管理**：LineWorksAccount数据类支持多个Bot账号
- **工具注册**：lineworks_calendar/lineworks_task/lineworks_drive三个Hermes Tool

### 可借鉴设计
- 完整企业级Plugin模板：Auth→Webhook验证→消息归一化→工具注册
- 双配置键名兼容：CamelCase+snake_case向后兼容
