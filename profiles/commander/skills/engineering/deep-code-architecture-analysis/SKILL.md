---
name: deep-code-architecture-analysis
description: >
  深度源码架构分析与系统对比方法论。从GitHub或其他公开仓库下载源码，逐文件解读核心模块，追踪关键执行路径，
  对比Hermes或其他系统的现有能力，产出架构图、能力差距矩阵、优先级+工时估算的集成方案。
  适用于：反向工程未知系统、技术选型调研、竞品架构对标、集成可行性评估。
version: 1.0.0
author: Hermes Agent
metadata:
  hermes:
    tags: [architecture-analysis, reverse-engineering, code-review, technical-research, comparison]
    related_skills: [systematic-debugging, extreme-code-audit-triple-agent, cross-review-autoresearch]
---

# 深度源码架构分析与系统对比

## 概述

当需要分析一个外部系统的源码结构、理解其架构设计、并与Hermes或特定目标系统进行对比时，使用本Skill。

**核心原则**：不要读README/文档就下结论——必须读实际源代码。代码不说谎。

### Absorbed Skills (consolidated)

| Former Skill | Absorbed As | Reference File |
|---|---|---|
| `extreme-code-audit-triple-agent` | Subsection — 3-agent parallel code audit + 6-layer review | `references/extreme-code-audit-triple-agent-skill.md` |

The absorbed skill provides an extreme version of this methodology: 3-parallel-leaf-agent code review with 6 audit layers (base stats, asset audit, compile check, runtime logic, cross-domain, parameter mapping), plus racing-game-specific benchmarks. Use it when the user demands "极端严苛审核" or "商用级审核" — load `deep-code-architecture-analysis` and read the reference for the triple-agent protocol. See also `references/racing-game-physics-benchmarks.md` and `references/racing-game-audit-methodology.md` for domain-specific audit checklists.

### ComfyUI Node Audit

For auditing ComfyUI custom nodes (custom_nodes/*), this skill now includes `references/comfyui-node-audit-checklist.md` — a 12-dimension checklist covering: file structure, node class basics, IS_CHANGED behavior, single-file/big-class analysis, input parameters, thread safety, AI/LLM calls, frontend JS extensions, performance, security, dead code, and output template. Load the reference when the user asks to audit a ComfyUI node or when analyzing a ComfyUI custom_node's code quality.

### FastAPI Full-API Audit

For systematically testing ALL endpoints of a FastAPI backend — including state management bug patterns (copy-vs-mutation trap), Body vs Query parameter binding detection, group-by-group route testing methodology — see `references/fastapi-full-api-audit.md`. This covers the NanoBot Factory audit session (2026-06-06) where 3 bugs were found and fixed across 85 API endpoint tests.

### AI Generation Parameter Completeness Audit

When the user requires **all parameter dimensions of every generation/edit function to be wired through** — or asks "are the settings/choices/adjustments all added" — this is a special class of audit that requires layered parameter mapping:

**The Multi-Layer Parameter Completeness Pattern:**

AI generation projects often have multiple independent generation systems (aigc.py / production_workbench.py / unified_generation_service.py / diffuser_engine.py / omni_gen.py) that each define their own parameter set. The bug pattern is that parameters defined in the API layer never reach the engine layer.

**The 3-pass approach:**
1. **Pass 1 (Field Audit):** Read every request/params dataclass in every file. List all fields. Compare across layers — the engine layer (diffuser_engine.py) may have 32 fields while the API layer (server.py) only maps 4.
2. **Pass 2 (Parameter Wiring):** For each generation endpoint, trace which fields from the request actually get passed to the generate() call. The common failure: `settings.get("seed", -1)` never gets mapped to the engine call.
3. **Pass 3 (Enrichment):** Create a unified superset model (see `references/unified-params-model.md`) and backfill every layer: API endpoint → service layer → engine layer → provider-specific conversion.

**Common missing parameter categories across layers:**
- Image: sampler/scheduler/batch/clip_skip/eta/vae/guidance_rescale
- LoRA: model/weight/clip_weight/trigger_words/type
- ControlNet: type/image/weight/guidance_start/end/preprocessor/mode
- Video: duration/fps/frames/camera(3 subfields)/motion_bucket/noise_aug/loop
- Edit: edit_type/source_image/mask(4 subfields)/strength/edit_prompt
- Filter: filter_type/strength/output_format/quality/kernel
- Color: brightness/contrast/saturation/vibrance/temperature/tint/exposure/highlights/shadows
- Upscale: model/scale/face_enhance/tile_size/pad/denoise
- 3D: export_format/texture_resolution/mesh_simplification/remove_bg/num_views
- Canvas: x/y/w/h/canvas_w_h/context_images/overlap/seam_blend/scene/story

**Backup before editing:** `cp file.py backup/params/file.py.bak` — each edit touches a different file across the project.

### AI Generation Platform Capability Matrix (Internal + External Audit)

When the user asks **"are all these [20+ AI generation] features fully working?"** or demands a comprehensive capability audit across multiple platforms (ComfyUI/Kling/Seedance/Midjourney/etc.), use this dual-track methodology:

**Track A: Internal Code Audit (delegate_task)**
Spawn a subagent to read ALL relevant backend source files and produce a per-file report:
```yaml
TARGET_FILES:
  - production_workbench.py     # Provider implementations
  - omni_gen.py                 # OmniGen engine
  - diffuser_engine.py          # Local diffusers engine
  - aigc.py / aigc_adapter.py  # AIGC adapter layer
  - comfyui_env_manager.py     # ComfyUI lifecycle
  - unified_generation_service.py  # Unified generation
  - classification.py           # CLIP + keyword classification
  - production_agents.py       # Production agents
  - image_filter_compare.py    # Image filter/comparison
  - annotation_system*.py      # Annotation pipelines
```
For each file, report: lines, real API calls (not mock), supported generation types, parameter dimensions, ComfyUI integration depth, mock/simulation ratio.

**Track B: External Platform Research (web_search)**
Simultaneously search for latest API capabilities of ALL platforms the user mentioned. For each platform capture:
- All supported generation types (txt2img/img2img/txt2vid/img2vid/first-last-frame/multi-image-ref/video-edit/infinite-canvas/3d/etc.)
- All adjustable parameters (with exact names and ranges)
- Model options and versions
- API endpoints and pricing
- Open source / self-hostable status

**Output: Capability Gap Matrix**

```
| Feature | Current Project | ComfyUI | Kling | Runway | Pika | Status |
|---------|----------------|---------|-------|--------|------|--------|
| txt2img | ✅ local+cloud | ✅ | ❌ | ❌ | ❌ | available |
| txt2vid | ⚠️ via KlingAPI | ✅ AnimateDiff | ✅ native | ✅ Gen-4 | ✅ 2.0 | partial |
| infinite canvas | ❌ | ✅ CanvasTab | ❌ | ✅ Infinite | Expansion | missing |
```

**Output deliverables:**
1. `references/ai-generation-capability-matrix-YYYYMMDD.md` — full matrix
2. SKILL.md body update pointing to it
3. If the gap analysis reveals a clear integration plan: include P0-P4 prioritized roadmap with estimated days

**Common bug patterns to detect in internal audit:**
- `state.assets` returns `.copy()` but write back is missing (copy-vs-mutation trap)
- `Body(...)` vs `Query(...)` parameter binding confusion in FastAPI
- `skill.dict()` instead of `skill.model_dump()` (Pydantic v2 deprecation)
- Mock/placeholder methods masquerading as real implementations

### Full-API Depth Test Protocol

When the user demands "极细粒度的功能测试" after a round of fixes, use the 30-item depth test protocol:

- **30 test items** organized into 8 groups: System → Agents → Assets → Generation(8 critical) → Canvas → DB → AIRI → LLM/GPU
- Each generation type tested with its FULL parameter set, not just defaults
- Canvas operations tested for scene/page count correctness, not just HTTP status
- Bug regression tests included (empty settings, negative seed, wrong generator)

See `references/full-api-depth-test-protocol.md` for the complete test matrix, execution pattern, and common failure patterns.

### Python LLM-Generated Code Bug Patterns
When auditing any Python/FastAPI backend, load `references/python-llm-bug-patterns.md` for 6 recurring bug patterns that standard linters miss because the code is syntactically valid:

1. **Object Method Confusion** — `float.cos()` → `math.cos(t)` (the most commonly missed semantic error)
2. **FastAPI Body vs Query** — Dict params silently treated as query params without `Body()`
3. **State Copy-vs-Mutation** — Property returns `.copy()`, endpoints mutate the copy, never write back
4. **Async Task KeyError** — `active_tasks[task_id]` may be GC'd before the async coroutine fires
5. **Pydantic V2** — `.dict()` → `.model_dump()` migration
6. **Vite Asset Path** — Relative paths in index.html trigger module resolution on public dir files

Run these checks during any code audit pass — they catch the bugs that standard linters miss.

## 触发条件

- 用户要求"分析XXX的架构"、"对比XXX和Hermes"、"研究XXX的实现"
- 需要评估一个外部工具/框架是否值得集成到Hermes
- 需要理解一个GitHub仓库的核心设计思路
- 做技术选型调研时（A vs B vs C）

**跳过**：需要部署/安装/运行的项目（那属于spike skill）、需要本地调试的bug（属于systematic-debugging）

## 7步工作流

### Step 1: 准确定位并获取目录结构

```bash
# 先用curl获取GitHub仓库信息
curl -sL "https://api.github.com/repos/{owner}/{repo}" | python3 -c "
import json,sys
d=json.load(sys.stdin)
print(f'Stars: {d.get(\"stargazers_count\",\"?\")}')
print(f'Language: {d.get(\"language\",\"?\")}')
print(f'Description: {d.get(\"description\",\"?\")}')
print(f'Last push: {d.get(\"pushed_at\",\"?\")}')
"

# 获取目录树（定位核心入口）
curl -sL "https://api.github.com/repos/{owner}/{repo}/contents/{path}" | python3 -c "
import json,sys
for item in json.load(sys.stdin):
    t = '📁' if item['type']=='dir' else '📄'
    print(f'{t} {item[\"name\"]}  ({item[\"path\"]})')
"
```

**关键判断**：找到真正的核心模块（入口文件、状态管理、存储层、hooks/pipelines），忽略test/example/docs目录。

### Step 2: 按重要性顺序获取核心文件

优先级排序：
```
P0 - 入口/主调度器（index.ts/main.py/__init__.py）
P0 - 核心类型定义（types.ts/types.py/schema.py）
P1 - 状态管理器（state-manager/state.py）
P1 - 存储/持久化层（storage.py/repository.py）
P2 - Hooks/Pipelines（作用域内注册的逻辑）
P3 - 工具类/辅助函数
```

获取方式：
```bash
# 小文件直接全量获取
curl -sL "https://raw.githubusercontent.com/{owner}/{repo}/main/{path}"

# 大文件分片读取
curl -sL "..." | head -500         # 前500行（获取import、类型定义、核心函数签名）
curl -sL "..." | wc -l             # 总行数
curl -sL "..." | sed -n '500,1000p' # 中间部分（核心执行逻辑）
curl -sL "..." | tail -200         # 末尾（导出/注册代码）
```

### Step 3: 追踪关键执行路径

对于事件驱动架构（如Plugin/Hook系统），从Hook注册点开始追踪：

```
register() → api.on("hook_name") → handler(event, ctx)
    ↓
handler内部分支：
    ├─ 条件A (token > 50%) → compressMild()
    ├─ 条件B (token > 85%) → compressAggressive()
    └─ 默认路径 → normalFlow()
```

**追踪方法**：
- 找到`registerOffload()`/`register*()`等注册函数
- 列出所有注册的hooks（api.on / registerHook）
- 对每个hook，阅读handler函数体
- 识别状态转换点（if/switch/case）

### Step 4: 识别关键设计决策

在阅读源码时特别关注：

| 设计决策 | 问题 | 例子 |
|:---------|:-----|:-----|
| 同步/异步 | 为什么选这个？ | 长任务用async是合理的 |
| 状态存储 | 内存/文件/DB？ | SQLite更适合agent场景 |
| 压缩策略 | 触发条件是什么？ | 50/85/90% 三级级联 |
| 容错机制 | 失败后怎么办？ | retry→fallback→fail-safe |
| 资源回收 | 不用的数据怎么清理？ | 24h reclaim scheduler |

### Step 5: 对比已有系统（编制能力差距矩阵）

对比维度：
1. **功能存在性** — 对方有我们没有的？我们有对方没有的？
2. **实现深度** — 对方更深的实现（容错、退化处理）？我们更深的实现？
3. **架构哲学** — 对方更侧重什么？（Hy-Memory: 主动遗忘 vs Hermes: 事件持久化）
4. **集成成本** — 对方的核心机制能否在现有架构中实现？（语言差异、依赖差异）

输出格式：
```markdown
| 能力维度 | 目标系统 | 本系统 | 差距 | 集成成本 |
|:---------|:--------|:-------|:----:|:--------:|
| 能力A | ✅ 实现方式描述 | ❌/⚠️ 现状描述 | 🔴/🟡/🟢 | N天 (代码量) |
```

### Step 6: 深度分析被截断/合并的文件

当大文件被分片读取时，需要拼接关键部分：

```bash
# 方法：记录下每段读取的范围，用sed拼接
# 比如：第500-1000行和第2000-2306行是关键

# 合并成临时文件做全文分析
curl -sL "..." > /tmp/full_source.ts
# 然后在这个完整文本上做grep/search
grep -n "functionName\|class KeyClass\|interface Config" /tmp/full_source.ts
```

### Step 7: 产出行动方案

对比分析完成后输出：
1. **值得集成的能力**（按P0-P4排序，估算工时）
2. **不值得集成的理由**（坦诚地说"不需要"）
3. **集成风险**（依赖、架构冲突、性能影响）
4. **替代方案**（不集成该能力，用现有体系的替代做法）

格式：
```markdown
## 行动方案

### P0（本周完成·核心价值最高）
- 能力A: N天, ~N行代码
  - 预期收益: X%节省
  - 实现路径: 具体怎么做

### P1（下周·锦上添花）
- 能力B: N天

### 不值得集成
- 能力C: 理由...（已有替代/成本过高/不匹配架构）
```

## 典型陷阱

### 🕳️ 陷阱1: 把README当源码读
**现象**: 根据README的描述写分析报告，但实际实现完全不同
**对策**: 必须有`read_file`或`curl`直接读过的源码行作为证据引用。源码中出现过的class/function名字才是可靠的。

### 🕳️ 陷阱2: 只看一个文件下结论
**现象**: 只读了index.ts就说"架构是这样"，但实际逻辑分布在多个hooks文件中
**对策**: 先读目录树，确认所有相关文件。事件驱动系统的逻辑可能在5-8个不同文件中。

### 🕳️ 陷阱3: 忽略容错/退化路径
**现象**: 只分析了正常流程，没分析error handling / fallback / retry策略
**对策**: 搜索代码中的 `catch` / `error` / `fallback` / `retry` / `degraded` / `fail-safe` 关键词

### 🕳️ 陷阱4: 被大文件吓住
**现象**: 看到2306行的index.ts就放弃逐行分析
**对策**: 分片读。前500行=结构/类型/import/注册；中间=主要handler逻辑；末尾=class定义和工具函数。核心逻辑通常在100-300行范围内，剩下是配置参数和工具函数。

### 🕳️ 陷阱5: 忘记对比自己的系统
**现象**: 把对方分析得很详细，但没有回到"这个能力和我们的有什么区别/能不能集成"
**对策**: 每分析完一个功能模块，立即追问：Hermes有这个能力吗？实现方式一样吗？能否直接复用？差异点在哪里？

### 🕳️ 陷阱6: 因为看到相似概念就认为'一样'
**现象**: 看到对方有"分层记忆"（L0-L3），自己也有structmem的3层，就说"大差不差"
**对策**: 对比必须精确到机制层面——对方的分层是怎么生成的（自动/手动/LLM提取），自己的分层是怎么维护的。概念名一样不等于实现一样。

## 实用技巧

### 快速判断一个仓库的架构风格

```bash
# 检查依赖（看框架倾向）
grep -c "import\|require" src/index.ts  # TypeScript项目
grep -c "^from\|^import" src/main.py     # Python项目

# 检查是否是插件架构
grep -rn "register\|plugin\|hook" src/ --include="*.ts" --include="*.py" | head -20

# 检查测试覆盖率（高质量项目的标志）
find . -name "test_*" -o -name "*.test.ts" -o -name "*.spec.ts" | wc -l
```

### 大文件阅读策略

```
文件 2306 行 → 分 5 段：
[0-500]    导入/类型/配置/注册函数签名 ← 最关键，理解架构入口
[500-1000] 核心handler/调度逻辑         ← 第二关键，理解执行路径
[1000-1500] 次级handler/工具函数         ← 根据需要阅读
[1500-2000] 辅助类/fallback逻辑          ← 容错机制确认
[2000-2306] class定义/导出               ← 最后确认完整接口
```

每段读完后立即总结该段的3个关键发现，而不是读完整个文件再回头想。

### 对比报告的写作节奏

不一次性写完整报告。按模块顺序：
1. 读入口文件 → 写"核心架构"章节初稿
2. 读hooks/pipelines → 写"执行流程"章节
3. 读配置/容错 → 写"容错机制"章节
4. 读对比能力 → 写"能力矩阵"章节
5. 读自己的系统确认 → 填充矩阵中的"本系统"列
6. 最后写"行动方案"和总结

## 产出物结构

```
reports/xxx-analysis/
├── analysis.md                # 主分析报告（对比+行动方案）
├── references/                # 可选：源码关键片段摘录
│   └── hooks-flow.md          # 关键执行流程图
└── skills/                    # 可选：如果分析产出了可重用的技能配置
    └── xxx-integration.md     # 集成方案配置参考
```

也可保存到已有技能下作为 reference 文件，如 `structmem-hierarchical-memory/references/xxx-comparison-YYYYMMDD.md`

## 回滚方案
### 快速回滚
如果部署后发现问题：
1. 使用版本控制回退到上一个提交：`git revert HEAD`
2. 确认回滚后系统状态正常
3. 通知相关方变更已撤销

### 数据安全
- 所有修改前确认有备份
- 配置变更记录版本历史
