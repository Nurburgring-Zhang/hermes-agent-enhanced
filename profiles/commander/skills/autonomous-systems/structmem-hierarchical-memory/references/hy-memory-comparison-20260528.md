# TencentDB Hy-Memory 架构分析 vs Hermes 记忆系统对比

> 分析日期: 2026-05-28
> 来源: Tencent/TencentDB-Agent-Memory (GitHub 4367★)
> 核心文件: src/offload/index.ts (117KB), src/offload/storage.ts (23KB), src/core/types.ts

## 一、Hy-Memory 核心架构

### 记忆分层金字塔 L0→L3

```
L3 Persona（用户画像） ← mindset/interests/work_style/communication/values
    ↑ LLM 归纳（每50条触发一次）
L2 Scenario（场景块） ← 按主题/任务聚合的事实群
    ↑ LLM 归纳（≥3条同一mmdName的null entry触发）
L1 Atom（结构化事实） ← LLM提取的工具调用结果简要摘要
    ↑ LLM 提取（每5轮对话触发、含tool_call_id绑定）
L0 Conversation（原始对话）← 完整消息记录，无压缩
```

### 短期记忆压缩（Context Offload）

工具调用结果的处理流程：

```
工具调用 → 完整结果写入 refs/{tool}_{timestamp}.md（外部文件）
        → 摘要提取为 OffloadEntry（持久化到 JSONL）
        → 汇总成 Mermaid 符号图（注入 Agent 上下文）
        → Agent 在上下文中只看到轻量 Mermaid 图（几百 tokens）
        → 如需原文：按 node_id grep refs/*.md → 恢复
```

三级级联压缩策略（llm-input-l3.ts 中的 `compressByScoreCascade`）：
1. **温和压缩**（mildOffloadRatio=0.5）：当上下文 token 占用超过 50% 时触发
2. **激进压缩**（aggressiveCompressRatio=0.85）：超过 85% 时触发
3. **紧急压缩**（emergencyCompress）：token overflow 异常时触发，只保留最后 N 条消息

### 跨 session 自动召回

```typescript
// 在每轮 before-prompt-build 时自动执行
function recall(sessionKey, userText) {
  1. 读取当前 session 的 offload entries
  2. 对所有 entries 做 BM25 + 向量 + RRF 混合检索
  3. 取 top 5 匹配条目
  4. 注入到下一轮 Agent 的 prompt 前缀
}
```

### 架构中立性

通过 `HostAdapter` 接口解耦宿主框架：

```typescript
interface HostAdapter {
  getRuntimeContext(): RuntimeContext; // userId, sessionId, platform
  getLLMRunnerFactory(): LLMRunnerFactory; // 统一的 LLM 调用接口
  getLogger(): Logger;
}
```

目前支持：OpenClaw插件, Hermes Gateway适配, 独立Gateway HTTP接口。

## 二、与 Hermes 现状逐项对比

### 短期记忆（上下文管理）

| 能力 | Hy-Memory | Hermes 现状 |
|:-----|:----------|:------------|
| 工具结果卸载到外部文件 | ✅ refs/*.md 自动卸载 | ❌ 全部保留在对话上下文中 |
| Mermaid符号任务图 | ✅ graph LR 格式，几百 tokens | ❌ 无 |
| 三级级联token压缩（温和50%→激进85%→紧急） | ✅ 自动触发 | ❌ 只有齿轮系统+context_packer（文件级85.6%压缩） |
| node_id下钻溯源码 | ✅ 沿符号图→node_id→refs恢复原文 | ❌ 无法追溯压缩前上下文 |
| 任务边界自动检测（L1.5） | ✅ 用LLM判断任务切换/延续/新任务 | ❌ 无 |
| 每轮对话前自动召回相关记忆 | ✅ BM25+向量+RRF混合检索注入 | ❌ 手动用memory工具查询 |

### 长期记忆（用户理解）

| 能力 | Hy-Memory | Hermes 现状 |
|:-----|:----------|:------------|
| L0→L3分层（对话→事实→场景→画像） | ✅ 完整4层自动蒸馏 | ⚠️ structmem(8377事件) + semantic(32条) + procedural(13条) + memory_palace，有碎片化分层但**未形成自动化蒸馏管道** |
| 人物画像自动生成 | ✅ 每50条自动生成persona.md | ❌ 只有USER.md手工维护 |
| 知识图谱 | ✅ Neo4j三元组（实体-关系） | ⚠️ mp_entities(3)+mp_relations(2)在active_memory.db，但不活跃未集成 |
| 混合检索（BM25+向量+RRF） | ✅ 统一召回API | ⚠️ 有FTS5索引和向量库，但**系统检索仅通过session_search，无统一召回API** |
| 跨session自动召回注入 | ✅ 每轮对话前自动执行 | ❌ 无主动召回注入机制 |

### Hermes 有但 Hy-Memory 没有的能力

| 能力 | Hermes | 说明 |
|:-----|:-------|:-----|
| 50平台情报采集→清洗→评分→推送全链路 | ✅ | Hy-Memory不覆盖情报领域 |
| 齿轮系统G0-G6互审互推 | ✅ | 系统自我监督 |
| 生产级可靠性引擎（确定性执行+降级拦截+专家委员会） | ✅ | 长链任务保障 |
| 343个可执行skill库 | ✅ | 跨领域专业知识 |
| 自进化集群（每日03:00自跑） | ✅ | 系统自我进化 |
| context_packer对话历史压缩（85.6%） | ✅ | 已有但不如Hy-Memory细粒度 |

## 三、最值得Hermes借鉴的两项能力

### 1. 短期记忆Mermaid符号化压缩

Hy-Memory在SWE-bench测试中节省**33% tokens**，WideSearch节省**61% tokens**。核心做法：
- 工具调用结果 → 卸载到外部文件（每次40-100KB）
- Mermaid图 → 注入上下文（每次200-500 tokens）
- node_id → 可按需恢复原文

**Hermes的实现思路**: 在`unified_collector_v5.py`或`gear_enforcer.py`中，对每次 `write_file/read_file` 等工具调用做拦截，把超过5KB的结果卸载到 `refs/` 目录，只保留 `<ref key=xxx>` 占位符在上下文中。

### 2. 跨session自动召回机制

Hy-Memory在每轮对话前**自动从长期记忆中检索相关事实**注入Agent prompt。Hermes需要手动用`memory`工具查询。

**Hermes的实现思路**: 在`gear_enforcer.py`的`build_wake_guide()`或`context_packer`中，加入从`active_memory.db`的`memory_semantic`和`memory_episodic`表中检索相关条目的逻辑，在每轮对话启动前注入到系统prompt。

## 四、参考资料

- Hy-Memory 源码: https://github.com/Tencent/TencentDB-Agent-Memory
- 核心文件: `src/offload/index.ts` (117KB, 2306行)
- 存储层: `src/offload/storage.ts` (23KB)
- 类型定义: `src/core/types.ts` (8KB) — 含HostAdapter/LLMRunner/RuntimeContext接口
- 中文README: `README_CN.md` (22KB) — 完整架构文档
