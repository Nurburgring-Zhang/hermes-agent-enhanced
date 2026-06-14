---
name: api-batch-data-processing
description: Batch-process local data files through external LLM APIs — read source data, split into batches, call API with structured output schema, parse JSON, save to dimension libraries. Covers pipeline design, prompt engineering for key-name stability, quality validation, and cost estimation.
version: 1.2.0
author: Hermes Agent
triggers:
  - "批量调用API"
  - "拆解提示词"
  - "维度库建库"
  - "to_chi"
  - "批处理建库"
  - "17维度"
  - "维度拆解"
  - "批量数据提取"
  - "API批处理"
  - "大规模生产"
  - "提示词生成"
  - "高并发"
  - "组合引擎"
  - "combine_engine"
  - "标签化建库"
  - "纯标签"
  - "v10"
  - "v11"
  - "final_build"
  - "性别断裂"
  - "query_filter"
---

# API Batch Data Processing

Batch-process local text data through external LLM APIs to produce structured dimension libraries, and recombine them into generated prompts.

## 🛑 Critical: Pre-Check Before Any Dimension Library Work

## 触发条件
- 用户提及调试、修复、分析代码问题时
- 需要系统性排查复杂Bug时
- 执行架构分析或代码审核时


**When the user asks about dimension library quality / classification / filtering / combination, ALWAYS do this check first:**

1. Check `/mnt/d/Hermes/1000000提示词/高质量模板/维度库_final_build/` — 828,791条17维库（已建好）
2. Read `final_build.py` — 这是建库脚本。**已知问题**：关键词硬匹配分类不准、C01_美学风格仅840条/C03_色彩调性仅449条/C04_构图镜头仅2635条严重不足、条目是整句拷贝不是精确片段、无组合引擎脚本
3. Check `新建库/` 中的文档 — `完整维度拆解与组合规则体系_最终版.txt` (1198行规则)、`_完整维度规则体系.txt` (15大类94子维度)
4. Check `gen_prompts.py` / `variant_engine.py` — 现有生成脚本是硬编码模板/替换词库模式，不是从维度库组合
5. **然后才有资格汇报当前状态**

**汇报格式必须是四段式**：有什么 → 有什么问题 → 解决了没有 → 要不要搞。每个问题标注具体根因（不是笼统说"质量不好"）。

## User Preferences (格林主人)

- **Direct API calls > delegate_task**: For bulk processing, write a Python script that calls the API directly. delegate_task wastes ~42K tokens/round on system overhead. The user explicitly rejected this approach for batch work.
- **Test before scale**: Always run 1 batch (40-50 rows) and verify quality before launching full production. Do 3-5 rounds of iteration if needed — the user demanded this.
- **No batch templates for prompts**: Never use loops/templates to generate hundreds of similar prompts. Each output must be individually validated by the API's understanding, not programmatic recombination.
- **Every production run gets a NEW output file**: The user got angry when old and new data were mixed in the same file. Create a new file per run (e.g. `mass_prompts_v7.6.txt`). Never append to an old production output.
- **Before proposing research, check 新建库**: The user stores completed research in `D:\\Hermes\\1000000提示词\\高质量模板\\新建库\\`. The 100 scene templates, 30 art styles, and 10 breakout logics are already done. Do not re-research.
- **Report in files, not terminal**: Terminal output gets corrupted by gear system noise. Write results to files.

---

## Part 1: Dimension Extraction Pipeline

### Architecture

```
Source files → Read + split into batches → ThreadPoolExecutor → DeepSeek API
  → Parse JSON → Write to 17 dimension library files
```

### 0. Prompt Key-Name MUST Be Explicit JSON Template

**This is the #1 bug.** If you just define dimensions in natural language, the API will invent its own key names (e.g. "主体", "发型", "服装" instead of "A01_年龄性别").

**Fix**: Put the full JSON template at the TOP of the system prompt. With this template, the API reliably uses the exact keys you specified. Without it, every API call produces different key names.

### 0a. Batch Format

**Flat array only:**
```json
{"条目N": {"A01_年龄性别":[], "A02_发型":[], ..., "D06_氛围情感":[]}}
```

Nested formats (`{"segments":{...}, "connective_fragments":[...]}`) add ~100 tokens/row and push 30-row batches past DeepSeek's 16K output limit, causing ~55% JSON truncation failure.

### 0b. Batch Size Tuning (Flat Array Format)

| Rows | Output tokens | Success rate |
|:----:|:------------:|:-----------:|
| 20 | ~7K | 100% |
| 30 | ~11K | 100% |
| 40 | ~15K | ~90% |
| 50 | ~18K+ | ~60% |

**30 rows/batch is the sweet spot.**

### 0c. Concurrency for DeepSeek Paid API

DeepSeek paid tier supports high concurrency (up to 500 requests/minute).

| Concurrency | Effective throughput | Production time for 10K rows |
|:-----------:|:-------------------:|:---------------------------:|
| 5 | ~100 rows/min | ~100 min |
| 20 | ~400 rows/min | ~25 min |
| 40 | ~800 rows/min | ~12 min |
| **80** | **~1,600 rows/min** | **~6 min** |

**Base cost**: ~$5 per 10K rows (input $0.14/M + output $0.28/M, ~2300 tokens/row).

```python
from concurrent.futures import ThreadPoolExecutor, as_completed

with ThreadPoolExecutor(max_workers=40) as ex:
    futs = {ex.submit(process_batch, b): b for b in batches}
    for f in as_completed(futs):
        result = f.result()
```

### 0d. Fallback-On-Failure Strategy

When JSON parsing fails, recursively split the batch in half and retry:

```python
def process_with_fallback(lines, depth=0):
    try:
        return call_api(lines)
    except json.JSONDecodeError:
        if len(lines) > 10 and depth < 2:
            mid = len(lines) // 2
            r1 = process_with_fallback(lines[:mid], depth+1)
            r2 = process_with_fallback(lines[mid:], depth+1)
            return r1 + r2
        return []
```

This recovers ~80% of failed batches. Ensure sub-batch results increment the session counter so progress logging fires correctly.

### 0e. Reversible Extraction Verification

For every fragment written to a dimension library, verify it exists as a substring in the original source text. If not, it's a hallucination — discard it. This is enforced at write-time.

---

## Part 2: Prompt Generation from Dimension Libraries

### Source Data

V7 dimension libraries at `D:\\Hermes\\1000000提示词\\高质量模板\\维度库_api_v7\\` (2,011,891 fragments total).

### 12 Mandatory Dimensions + 3 Optional

```
[OPEN]    A01_年龄性别 + A02_发型            → 人物出场
[SCENE]   A05_姿势 + B01_场景环境             → 人物与空间
[DRESS]   D01_服装款式                       → 穿着（只取1个！）
[ACTION]  B02_活动行为 + A04_表情眼神          → 动作表情（各只取1个！）
[LIGHT]   C02_光照条件 + C03_色彩调性          → 光影色彩
[FRAME]   C04_构图镜头                       → 画面框架
[CLOSE]   C01_美学风格 + D06_氛围情感          → 风格收尾
```

**Critical — fragment count limits:**
- `D01_服装款式`: take exactly **1** fragment (not 2). Taking 2+ causes clothing stacking (user reported "blue striped dress + lace bra + pink stockings + lace panties + high heels = 5 items at once").
- `A05_姿势`: take exactly **1** fragment. Taking 2+ causes three-hand contradictions.
- `B02_活动行为`: take exactly **1** fragment. Taking 2+ causes three-hand and body contradictions.
- `A04_表情眼神`: take exactly **1** fragment. Taking 2+ causes "head tilted down" + "head turned to shoulder" contradiction.
- `B01_场景环境`: take **2** fragments, but with strict INDOOR/OUTDOOR consistency filter.

### Scene Consistency

Decide `scene_choice = "indoor"` or `"outdoor"` at composition time, then:
- `B01_场景环境`: filter to match scene_choice, **exclude** fragments that contain keywords from the opposite scene
- `A05_姿势`: exclude indoor keywords ("床", "枕头", "沙发", etc.) when scene_choice is outdoor
- `C02_光照条件`: match lighting type to scene (indoor→柔光/灯光, outdoor→自然光/阳光)
- `D05_天气时间`: only include for outdoor scenes

### Physical Conflict Detection (Post-Generation)

After the API generates a prompt, check for these physical contradictions before saving. If found, retry (up to 5 attempts):

| Pattern | Example | Regex |
|---------|---------|-------|
| 站+浴缸/水 | "standing in the bathtub" | `站.{0,15}(浴缸\|浴池\|淋浴\|水中)` |
| 躺+站/走 | "lying down... standing up" | `躺.{0,15}(站\|走\|行)` |
| 双臂+单手 | "arms crossed" + "right hand holding" | `双臂.{5,30}(右手\|左手)` |
| 双手+单手 | "both hands" + "left hand" | `双手.{5,30}(右手\|左手)` |
| 闭眼+凝视 | "eyes closed... staring" | `(闭.\|紧闭).{0,20}(注视\|凝视\|阅读\|盯着)` |
| 床+站立 | "on the bed... standing" | `(床上\|枕头上).{0,15}(站立\|站着)` |
| 卧室+户外 | "bedroom... beach" | `卧室.{0,20}(沙滩\|海滩\|草地)` |
| 客厅+浴缸 | "living room... bathtub" | `客厅.{0,20}(浴缸\|淋浴)` |

### Clothing Reasonability (Post-Generation)

**A person wears one outfit at a time, not 5 items stacked.** The API will produce "blue striped dress + lace bra + pink stockings + lace panties + high heels" if given multiple clothing fragments. Fix: take only 1 D01 fragment, and tell the API in system prompt to pick ONE outfit and ignore contradictory others.

### The 5-Retry Loop

For each prompt generation, retry up to 5 times:
1. First attempt at temperature=0.88, max_tokens=2500
2. If output < 500 Chinese chars → retry with same params
3. If post_clean returns None (physical conflict detected) → retry
4. After 5 failures, accept the longest output even if under 500 chars

### Order Template (for composing fragments)

1. A01_年龄性别 → A02_发型
2. A05_姿势 → B01_场景环境
3. D01_服装款式
4. [D02_配饰鞋帽] [D03_材质质感] (optional)
5. B02_活动行为 → A04_表情眼神
6. [D05_天气时间] (optional, outdoor only)
7. C02_光照条件 → C03_色彩调性
8. C04_构图镜头
9. C01_美学风格 → D06_氛围情感

### Prohibitions (Enforced in System Prompt + Post-Processing)

- **比喻词**: 仿佛/犹如/就像/好似/宛如/如同 — delete in post-processing
- **科技词**: 量子/夸克/粒子/齿轮/全息/数据/芯片/像素/矩阵 — delete in post-processing
- **三手多手**: must enforce via fragment count limits (1 per dimension) + physical conflict detection
- **服装堆叠**: take only 1 D01 fragment; explicit instruction in system prompt
- **场景矛盾**: enforce INDOOR/OUTDOOR consistency at composition time
- **数字化描述**: distance/thickness/angle with numeric values
- **标题/序号**: output must be a single paragraph, no headings, no line breaks

---

---

## Part 3: Local Rule-Based Combination Engine (No API)

When generating prompts from dimension libraries WITHOUT using an LLM API (local only), use the combine_engine approach.

### Architecture

```
Dimension library files (tag format v3 or v5)
  → load_all() reads 16-17 dimension files
  → gen_one() picks 1 entry from each dimension
  → Fixed template assembles into coherent Chinese paragraph
  → Post-gate validates gender/scene/hand conflicts
  → Output: 250-350 char Chinese prompt
```

### The 3 Engine Classes

| Class | Approach | File | Best for |
|-------|----------|------|----------|
| **v8-style** | Fragment concatenation | `combine_engine_v8_1.py` | High diversity, accepts lower quality |
| **v10-style** | Fixed template + gender cloth filter | `combine_engine_v10_1.py` | **Production** — 80% manual pass rate |
| **v11-style** | Pure label + TBD | `combine_engine_v11.py` | Future — requires v5 tag library |

### Critical: The v5 Tag Library Fix

The root cause of all quality issues is that v3 dimension library entries are **full sentences** (e.g. "女性留着深色长发并带有蓝色挑染") not **pure labels** ("深色长发带蓝色挑染").

**The fix must happen at the dimension library build layer**, not the engine layer. Engine-layer fixes (gender filters, inline cleaning, post-gates) can only get you to ~80% quality.

**Build approach**: `final_build_v5_tag.py` splits source text into sentences → clauses → each clause classified to 1 dimension → person prefix + verb removed → only core description word(s) saved.

See `references/local-combination-engine-evolution.md` for the full iteration history.

### QC Score vs Manual Review

**NEVER trust QC scores alone.** The `quality_filter.py` checks 10 mechanical rules only — it doesn't detect:
- Multi-person entries ("两位","一对","情侣")
- Gender-ambiguous clothing on male A01
- Scene-confused C02 entries
- Fragment readability / naturalness

**Always do a 100-line manual review** before declaring an engine "production ready." Look for:
1. Gender consistency (pronoun + clothing)
2. Single person (no multi-person entries)
3. Scene consistency (indoor/outdoor)
4. No three-hand descriptions
5. Readable Chinese sentences

### File Location Pattern

```
/mnt/d/Hermes/1000000提示词/高质量模板/维度库/
├── combine_engine_v10_1.py     ← current best engine
├── combine_engine_v11.py       ← next gen (requires v5 tag lib)
├── final_build_v5_tag.py       ← tag library builder
└── quality_filter.py           ← QC (10 mechanical rules)
```

### PromptFactory.py

The unified tool at `/mnt/d/Hermes/1000000提示词/PromptFactory.py` wraps:
1. Build dimension library (final_build_*.py)
2. Supplement dimensions (supplement_*.py)
3. Trial produce (100 lines via combine_engine)
4. Batch produce (N lines via batch_produce_*.py)
5. QC sampling + clean

Update the ENGINE_VERSION + DIM_VERSION in PromptFactory.py when switching engines.

---

## Pitfalls (in addition to Part 1/2)

- **API key-name bug**: If you don't include the full JSON template in the prompt, the API invents its own key names. Always include the template.
- **V6 nested format failure**: V6's `{"segments":{}}` wrapper added 100 tokens/row. At 30 rows that's 3K extra output — pushing past 16K limit. Use flat format.
- **Thread-safety for progress writes**: JSON file writes from concurrent threads can race. Use append-mode per-write for dimension files (atomic on Linux). For progress tracking, a periodic timer (every 3 min) is more reliable than chunk-count-based triggers.
- **Failures cluster on certain files**: ~5-8 files have unusual Unicode or very long lines that consistently trigger JSON errors. Pre-scan.
- **Chinese paths**: `/mnt/d/` paths with Chinese chars work in Python open() but cause issues in shell. Use Python, not bash.
- **Process noise**: The gear system cron jobs (self_enhance, task_monitor) write to stdout at unpredictable times, corrupting terminal output. Always redirect background process output to a file.
- **Read-then-write file clobber**: NEVER do `for line in open(file): ... open(file, 'w')` — the write truncates the file you're reading from. Always read into a list first, close, then write. This bug emptied a 7K-entry A02_发型.txt file in this session.
- **Inline cleaning hurts more than it helps**: v10.2 attempted to clean dimension entries at pickup time (inline_clean_hair/cloth/accessory). This over-cleaned useful entries and made quality worse. Trust the dimension library's format — if the library has bad entries, fix the library, not the engine.
- **API retry cost**: Each failed retry costs the same tokens as a success (because input is the same). 5 retries = 5× cost. Balance retry count vs success rate.

---

## Verification Checklist

### For Dimension Extraction:
- [ ] Process 1 batch (30-40 rows) from a random file
- [ ] All 17 dimension files created with content
- [ ] Key names match expected schema (check any 3 rows)
- [ ] B02_活动行为 has reasonable extraction (not empty for human data)
- [ ] D02_配饰鞋帽 extracts human-worn accessories, not product_photography shoes
- [ ] Hallucination rate < 1% (all fragments should be source substrings)
- [ ] Token cost per batch matches estimate (~$0.005 per 30-row batch)
- [ ] Progress tracking works across chunks

### For Prompt Generation:
- [ ] 500-800 Chinese characters per prompt
- [ ] Opening style name present (e.g. "吉卜力治愈风，")
- [ ] No 比喻词 (仿佛/犹如/就像)
- [ ] No physical contradictions (scene, pose, clothing)
- [ ] No three-hand descriptions
- [ ] Single coherent outfit (not stacked clothing)
- [ ] Consistent scene type (indoor or outdoor, not both)

## 回滚方案
### 快速回滚
如果部署后发现问题：
1. 使用版本控制回退到上一个提交：`git revert HEAD`
2. 确认回滚后系统状态正常
3. 通知相关方变更已撤销

### 数据安全
- 所有修改前确认有备份
- 配置变更记录版本历史
