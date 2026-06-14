# Hy-Memory (TencentDB-Agent-Memory) 深度源码分析

> 分析日期: 2026-05-28
> 来源: https://github.com/Tencent/TencentDB-Agent-Memory (4367★)
> 核心语言: TypeScript (11.7万行)
> 核心文件: src/offload/index.ts (2306行)

## 一、项目定位

腾讯推出的 Agent 记忆增强插件，为 OpenClaw/Hermes Agent 框架添加"持久化记忆"能力。
**不替代对话能力，而是让 Agent 记得过去的交互**。

## 二、核心架构

### 记忆分层金字塔 L0→L3

```
L3 Persona（用户画像）← mindset/interests/work_style/communication/values
    ↑ LLM 归纳（每50条触发一次）
L2 Scenario（场景块）← 按主题/任务聚合的事实群
    ↑ LLM 归纳（≥3条同一mmdName的null entry触发）
L1 Atom（结构化事实）← LLM提取的工具调用结果简要摘要
    ↑ LLM 提取（每5轮对话触发、含tool_call_id绑定）
L0 Conversation（原始对话）← 完整消息记录，无压缩
```

### 短期记忆三级压缩

| 级别 | 触发阈值 | 执行点 | 行为 |
|:-----|:---------|:-------|:-----|
| **Mild** | token > 50% contextWindow | before_prompt_build + llm_input | 按score从低到高替换为摘要 |
| **Aggressive** | token > 85% contextWindow | before_prompt_build + llm_input | 从头删除旧轮次，保留最后2条+MMD |
| **Emergency** | token > 90% 或 force | before_prompt_build 最后兜底 | 仅保留最后2条，其余变极致摘要 |

### 关键Hook链（从index.ts 2306行源码反推）

```
registerOffload()
  ├─ api.on("before_tool_call")     → 缓存toolCallId + params
  ├─ api.on("after_tool_call")      → 抓取result, >2KB→writeRef (), 加入pendingToolPairs
  ├─ api.on("before_prompt_build")  → L1 flush + L1.5 judge + L3压缩 + MMD注入
  ├─ api.on("llm_output")           → 只是记录pending计数
  ├─ api.on("llm_input")            → 缓存上下文, MMD注射
  ├─ api.on("before_agent_start")   → L4 skill命令解析
  ├─ registerContextEngine()        → 装配OffloadContextEngine(bootstrap/ingest/compact/assemble/afterTurn)
  └─ Reclaim Scheduler              → 5min后首次执行, 24h周期清理过期数据
```

## 三、核心机制详解

### 1. L1 原子事实提取
- 触发: pendingToolPairs ≥ 4 或 每轮before_prompt_build时flush
- 执行: 后端L1 API调用（或本地LLM fallback）
- 每批处理5对工具调用
- 失败重试3次 → 退化为本地fallback（无LLM摘要）
- refs写入: `~/refs/{toolName}_{timestamp}.md`

### 2. L1.5 任务边界判断
- 触发: 每轮assemble()（context engine调用点）
- LLM判断: taskCompleted / isContinuation / isLongTask / newTaskLabel
- 结果→boundary (long/short, 关联activeMmd)
- failSafe: 如果LLM调用完全失败（2次重试后），push boundary=short, activeMmd=null
- 超时保护: 等待60s后force-settle，防止L2 scheduler永久阻塞

### 3. L2 Mermaid生成
- 调度器: 5s轮询, 模块级单例（_l2Running互斥锁）
- 触发条件A: null entry ≥ l2NullThreshold(3)
- 触发条件B: timeout ≥ l2TimeoutSeconds(60)
- 执行: runL2WithBackend() → 分batch(30条/批) → 发送给后端L2 Generate API
- 结果: 更新MMD文件 + backfillNodeIds()写回offload entries
- taskSwitchFlush: 当L1.5检测到任务切换，flush旧mmd的残留null entry

### 4. L3 用户画像
- 触发: 每50条L1记忆
- LLM生成: 从所有L2 scene + L1 atom综合
- 输出: persona.md（思维模式/兴趣/工作风格/沟通偏好/价值观/行为模式）
- 三级级联压缩策略（compressByScoreCascade）→ 从低分到高级联替换

### 5. L4 技能生成
- 通过 `/create-skill` 命令触发
- 后端L4 Generate API → 生成SKILL.md
- 写入: `~/skills/{skillName}/SKILL.md`

### 6. 召回机制
- 支持: keyword (BM25 FTS5), embedding (sqlite-vec), hybrid (RRF)
- 在 historyMmdInjection 中间接使用（通过后端API）
- 跨session自动注入: 在before_prompt_build中从offload entries检索

## 四、代码架构关键发现

### 真正的大局：不是"一个文件"，而是"5个独立触发点"

```
触发点1: after_tool_call → 卸载 + L1 flush
触发点2: assemble() → L1.5 judge
触发点3: L2 Poll Scheduler (5s) → Mermaid生成
触发点4: before_prompt_build → L3压缩 + MMD注入
触发点5: Reclaim Scheduler (24h) → 清理过期
```

这5个触发点在2306行的index.ts中注册，但逻辑实际分布在：
- `src/offload/hooks/after-tool-call.ts` — 卸载逻辑
- `src/offload/hooks/before-prompt-build.ts` — L3压缩入口
- `src/offload/hooks/llm-input-l3.ts` — 三级压缩算法
- `src/offload/state-manager.ts` — 状态机
- `src/offload/storage.ts` — 存储层
- `src/offload/pipelines/l2-mermaid.ts` — Mermaid生成
- `src/offload/reclaimer.ts` — 回收
- `src/offload/mmd-injector.ts` — MMD注入

### 容错机制的重点
- L1: 3次retry → 本地fallback（无LLM摘要）
- L1.5: 1次retry (3s) → fail-safe（short boundary, null activeMmd）
- L2: 逐batch失败继续（不中断整个L2），失败entry保持"wait"状态下次重试
- L3: noLlmFallback=allOffloaded（如果不能压缩，不降级保留）
- Context Engine: slot竞争检测（如果被另一个plugin占了，disable全部offload）

## 五、与 Hermes 对比结论

### 最值得Hermes借鉴的2项能力

1. **工具结果卸载 + 三级压缩** — 长链任务token节省40-60%
   - 实现成本: ~2天Python 500行
   - 零外部依赖（只用到文件系统+SQLite FTS5已有）

2. **跨session自动召回** — 让Agent自动记住过去的用户偏好
   - 实现成本: ~0.5天（FTS5+structmem已有）

### Hermes有但Hy-Memory没有的能力
- 50平台情报采集→清洗→评分→推送全链路
- 齿轮系统G0-G6互审互推
- 生产级可靠性引擎（8模块）
- 343个可执行skill库
- 自进化集群（每日03:00自跑）

### 架构哲学差异
- Hy-Memory: **主动遗忘** — 只保留当前最有用的，其他卸载/压缩/丢弃
- Hermes: **事件持久化** — 所有事件平等存储，structmem 8377条全部保留
- 两者不冲突，可以互补

## 六、参考资料

- 源码: https://github.com/Tencent/TencentDB-Agent-Memory
- 核心文件: `src/offload/index.ts` (2306行)
- 中文README: `README_CN.md` (22KB)
- 分析工具: deep-code-architecture-analysis skill
- 简版能力对比（structmem视角）: `skills/autonomous-systems/structmem-hierarchical-memory/references/hy-memory-comparison-20260528.md`
