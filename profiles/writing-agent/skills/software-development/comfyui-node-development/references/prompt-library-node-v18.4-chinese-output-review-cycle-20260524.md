# PromptLibraryNode V18.4 — Chinese-only Output + 提示词库 Independence + 复盘 Review Cycle

**Date:** 2026-05-24 23:07+ → 2026-05-25 01:30+
**Session context:** Follow-up to V18.3. Four rounds of fixes in one session:
1. Chinese-only output for all direction ports
2. 提示词库 independence from 故事板/AI生成 (structural if/elif→if change)
3. 负面词 依赖修复 (fallback to any content port)
4. Full 复盘 review cycle per rules 4-6

## Changes Applied

### 1. Chinese-only Output (3 system prompts + 3 headers)

All `AI文生图Prompt` instructions changed from English to Chinese:

| Location | Before | After |
|----------|--------|-------|
| Storyboard sys prompt (line 1287) | `完整的英文视觉描述prompt（500字符以上）...subject, action, scene, lighting...` | `完整的中文画面描述prompt（500字以上）...主体描述+动作+场景+光线+配色...` |
| Picture book sys prompt (line 426) | `完整英文prompt（300字符以上）...subject, action, scene, lighting...` | `完整中文prompt（300字以上）...主体描述+动作+场景+光线+配色...` |
| Short drama sys prompt (line 504) | `完整的英文prompt（400字符以上）...subject, action, scene, lighting...` | `完整的中文prompt（400字以上）...主体描述+动作+场景+光线+配色+景别+运镜+氛围+竖屏格式` |
| Storyboard header | `500字符以上英文AI文生图Prompt` | `500字以上中文AI文生图Prompt` |
| Picture book header | `300字符以上英文AI文生图Prompt` | `300字以上中文AI文生图Prompt` |
| Short drama header | `400字符以上英文AI文生图/视频Prompt` | `400字以上中文AI文生图/视频Prompt` |

**Conversion pattern:** `英文字符` → `中文字` and `subject, action, scene, lighting...` → `主体描述+动作+场景+光线+配色...`

**Retained English:** Professional terminology only (景别 names like `Close-Up`, `Dolly In`, tool names like `Midjourney/SD/ComfyUI`).

### 2. 提示词库 Independence from 故事板/AI生成 (Critical Structural Fix)

**Problem:** Original `if/elif/else` made storyboard mode and prompt library mode mutually exclusive:

```python
# OLD (broken):
if 开启AI生成 or 故事板模式 != "关闭":
    if 故事板模式 != "关闭":  # storyboard — no final_prompt
    elif 开启AI生成:          # AI gen — sets final_prompt
else:
    # 提示词库 — SKIPPED when storyboard is ON!
```

When storyboard ON + 文件夹路径 provided → 提示词 port stayed empty.

**Fix:** Three independent steps:

```python
# NEW (fixed):
# 步骤1: 故事板 — independent, only sets storyboard_prompt
if 故事板模式 != "关闭": ...

# 步骤2: AI生成 — only when no storyboard
elif 开启AI生成: ...  # sets final_prompt

# 步骤3: 提示词库 — independent, only fires when final_prompt still empty
if not final_prompt and 文件夹路径: ...  # sets final_prompt from folder
```

**Key insight:** The condition for step 3 is `if not final_prompt and 文件夹路径`. This ensures:
- When storyboard is ON but user also provided 文件夹路径 → folder is used for 提示词 port
- When AI生成 is ON → AI result is used (step 2 fires, so step 3 is skipped)
- When nothing is ON and no path → 提示词 port stays empty (expected)

### 3. 负面词 依赖修复 — Fallback to Any Port

**Problem:** `if 启用负面词生成 and final_prompt:` — stories mode made final_prompt empty → no negative words.

**Fix:**

```python
if 启用负面词生成 and (final_prompt or storyboard_prompt or picture_book_prompt or short_drama_prompt):
    neg_main_content = final_prompt or storyboard_prompt or picture_book_prompt or short_drama_prompt or ""
    pos_text = neg_main_content.lower()
```

**Fallback priority:** `final_prompt → storyboard_prompt → picture_book_prompt → short_drama_prompt`

### 4. Retry Backoff: Linear → Exponential

```python
# BEFORE (linear): 2s, 4s, 6s
_time.sleep(2 * (attempt + 1))

# AFTER (exponential): 2s, 4s, 8s — position: format error retry
_time.sleep(2 ** (attempt + 1))  # 指数退避
```

### 5. Full Execution Flow (Post-V18.4)

```
1. 种子处理
2. 步骤1: 故事板 → if 故事板模式 ≠ "关闭" → storyboard_prompt (独立)
3. 步骤2: AI生成 → elif 开启AI生成 → final_prompt (仅当没开故事板)
4. 步骤3: 提示词库 → if not final_prompt and 文件夹路径 → final_prompt
5. AI润色 → if 开启AI润色 and final_prompt
6. 负面词 → if 启用 and any port has content → neg_main_content
7. 批量AI → if 开启AI生成 and final_prompt and 批量>1
8. 翻译 → if 开启翻译 and final_prompt
9. 绘本 → if 输出绘本提示词 → independent AI call → +book_header
10. 短剧 → if 输出短剧提示词 → independent AI call → +drama_header
11. 返回5元组
```

### 6. 复盘 Review Cycle Applied

User invoked rules 4-6 from SOUL.md:

#### Phase 0: Global Review (规则4)
- Cross-referenced all 9 user requirements against code
- All passing

#### Phase 1: Web Best-Practice Research (规则5)
- Delegated task to search ComfyUI best practices
- Key finding: Output headers before content may be a risk if port is connected to CLIP Text Encode (header text gets encoded into embedding). Flagged but not changed — user's design intent.
- Key finding: Serial 3-call is safe but 3x slower than parallel.

#### Phase 2: Multi-Condition Commercial-Grade Testing (规则5-6)
- 5 automated test suites: syntax, AST, call signatures, string integrity, line count
- All passed

#### Phase 3: Deep Code Audit (规则5)
- Confirmed all 11 code changes correct
- Found and fixed: retry backoff linear→exponential

#### Phase 4: Optimization Iteration (规则6)
- One change applied: retry backoff
- No other defects found

## Lessons for Future ComfyUI Work

1. **Chinese-only rule for direction ports:** Never output English AI prompts in storyboard/绘本/短剧 ports unless user asks.
2. **Review cycle protocol:** Rules 4-6 sequence is fixed: global review → web research → test → audit → iterate. Do all phases even if first pass looks clean.
3. **Risk note on output headers:** `【XX总定义】` header is visible to downstream ComfyUI nodes. If connected to CLIP Text Encode, header text becomes part of encoded prompt.
4. **Independent step pattern:** When multiple features share the same output variable (final_prompt), use `if/elif/if` with `not variable and condition` for the fallback — never nest them in `if/elif/else`.
5. **Fallback chain for supplemental features:** Any feature that depends on "what was generated" should have a priority chain: `final_prompt → storyboard_prompt → picture_book_prompt → short_drama_prompt`. Never depend on a single variable.
