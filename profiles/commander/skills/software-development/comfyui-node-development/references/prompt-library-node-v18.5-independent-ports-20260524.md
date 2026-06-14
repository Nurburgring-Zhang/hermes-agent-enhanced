# V18.5: All Ports Fully Independent + Header Definition Cleanup (2026-05-24)

## Background

User discovered that after V18.4 changes, when 故事板/绘本/短剧 ports were outputting, the "提示词" and "负面提示词" ports were empty. Root cause: the original `if/elif/else` structure made storyboard/AI generation/prompt library **mutually exclusive**.

## Fix 1: Complete Structural Independence (All Ports)

**Problem:** Three data sources for "提示词" port were in a nested if/elif/else chain:
```python
if 故事板模式 or 开启AI生成:       # ← storyboard AND AI gen AND prompt library all fight here
    if 故事板模式: ...             # storyboard only writes storyboard_prompt, not final_prompt
    elif 开启AI生成: final_prompt = ai_result  # AI gen only
else:                             # ← THIS IS SKIPPED when storyboard/AI gen is ON
    # prompt library: final_prompt = result_texts[0]
```

When storyboard mode was ON: storyboard branch runs → skip AI gen → **skip prompt library** → `final_prompt` stays empty → 提示词 port = `""`, 负面词 port = `""`.

**Fix:** Split into 3 independent sequential steps, each with its own `if`:

```python
# 步骤1: 故事板模式（独立执行，不干预final_prompt）
if 故事板模式 != "关闭":
    # ... only sets storyboard_prompt ...
    # Failure → silent skip (storyboard_prompt = ""), NOT return

# 步骤2: AI生成单条（完全独立）
if 开启AI生成:
    # ... sets final_prompt ...
    # Failure → silent skip, NOT return

# 步骤3: 提示词库（完全独立）
if 文件夹路径:
    # ... always executes if folder path is provided ...
    # sets final_prompt from first line
```

**Critical design rule:** Every port's source must be an **independent `if` block** — no nesting, no `elif`, no `else`. 10 independent `if` blocks in `get_prompt()`:

| Index | Condition | Writes | 
|-------|-----------|--------|
| #0 | 固定种子 | random.seed |
| #1 | 故事板模式 != "关闭" | storyboard_prompt |
| #2 | 开启AI生成 | final_prompt |
| #3 | 文件夹路径 | final_prompt |
| #4 | 开启AI润色 and final_prompt | final_prompt (polished) |
| #5 | 启用负面词生成 and any port | negative_prompt |
| #6 | 开启AI生成 and final_prompt and >1 | final_prompt (batch, first only) |
| #7 | 开启翻译 and final_prompt and API | final_prompt |
| #8 | 输出绘本提示词 and API地址 | picture_book_prompt |
| #9 | 输出短剧提示词 and API地址 | short_drama_prompt |

## Fix 2: Silent Failure — No `return` in Individual Ports

**Problem:** Storyboard/AI gen failures used `return (error, "", "", "", "")` — this interrupted ALL subsequent ports (绘本, 短剧, 提示词库, 负面词).

**Fix:** Replace `return` with silent skip:
```python
# BEFORE: Early return kills all downstream ports
if not API地址:
    return (f"[故事板] 请设置API地址...", "", "", "", "")
if not ai_result:
    return (f"[故事板生成失败] ...", "", "", "", "")

# AFTER: Silent skip, other ports continue
if not API地址:
    storyboard_prompt = ""  # skip quietly
    # continue to next if block
if not ai_result:
    storyboard_prompt = ""  # skip quietly
    # continue to next if block
```

**Exception:** The `_error_result()` path in prompt library (步骤3) still returns because it's a **structural error** (folder not found, no files, all filtered). These mean the user's input is invalid — no point continuing. Individual API failures should NOT trigger structural returns.

## Fix 3: Negative Prompt Independence

**Problem:** `启用负面词生成 and final_prompt` — in storyboard-only mode, `final_prompt` was empty → negative prompt never generated.

**Fix:** Check ALL ports for content:
```python
if 启用负面词生成 and (final_prompt or storyboard_prompt or picture_book_prompt or short_drama_prompt):
    neg_main_content = final_prompt or storyboard_prompt or picture_book_prompt or short_drama_prompt or ""
    pos_text = neg_main_content.lower()
```

## Fix 4: Prompt Library Independence (V18.5 re-refinement)

**V18.4 had `if not final_prompt and 文件夹路径:`** — this condition prevented prompt library from running when AI gen had set `final_prompt`.

**V18.5 corrected this to `if 文件夹路径:`** — prompt library ALWAYS runs when a folder path is provided, regardless of whether AI gen also ran. The execution order determines priority:
- If AI gen ran first → `final_prompt = AI result`
- Then prompt library runs → `final_prompt = folder line` (overwrites AI result because it's the more explicit user input)

**User confirmed:** "提示词端口无论什么时候都进行输出从文件夹选的单行提示词" — prompt library is the primary source for 提示词 port.

## Fix 5: Header Definitions — Removed Word Counts and AI Prompt References

**User request:** Three header definitions (故事板总定义/绘本总定义/短剧总定义) should NOT contain word count requirements or references to "AI文生图Prompt" — those are system prompt details, not header content.

### Storyboard Header (After)
```
【故事板总定义】生成一组完整的故事板分镜，模式为「X」，共Y个镜头，
风格为「Z」。每个镜头包含：景别（7级好莱坞分类）、
画面描述（主体动作+场景环境+光线氛围+色彩基调+构图+情绪）、
运镜方式（11种运镜+速度）、转场效果（8种转场）、
备注（叙事功能+情绪节奏+时长建议）。要求全组镜头交替使用...
```

Removed: `500字以上极致细腻中文画面描述...500字以上中文AI文生图Prompt（可直接用于Midjourney/SD/ComfyUI）`

### Picture Book Header (After)
```
【绘本总定义】生成一本完整的儿童绘本画册，共X页，风格为「Y」。
每页包含：页码、画面描述（主体角色+动作神态+场景环境+光线氛围+色彩+构图+细节纹理）、
绘本正文文案（适合亲子朗读）、视觉连续性提示（与前后页的关联）、
翻页惊喜设计（page-turn surprise）。要求角色外貌服饰颜色在所有页面高度一致...
```

Removed: `300字以上极致细腻画面描述...300字以上中文AI文生图Prompt`

### Short Drama Header (After)
```
【短剧总定义】创作一部完整的AI短剧分镜头剧本，共X个镜头，风格为「Y」。
每个镜头包含：镜头编号、景别（7级好莱坞景别分类）、
画面描述（角色动作+表情神态+...到眼神方向衣角飘动光影变化级）、
台词/旁白、运镜方式（11种运镜+速度描述）、用途标注（叙事功能+建议时长）。
开场第1镜头必须是强钩子（黄金3秒法则）...
```

Removed: `400字以上极致细腻画面描述...400字以上中文AI文生图/视频Prompt`

**Key rule:** Headers describe **what fields the content contains** and **core quality rules**. They do NOT include AI generation instructions (word counts, prompt format requirements) — those belong in the system prompt.

## Session Timeline (this session)

```
Round 1: User reports hint port empty → Analysis: if/elif/else mutual exclusion
Round 2: Fix: split into independent steps, elif→if, silent failures
Round 3: User reports "提示词" port still empty → Fix: remove `not final_prompt` guard
Round 4: User refines three headers → Remove word counts and AI Prompt references  
Round 5: Full 复盘 cycle (history review → test → audit → 完善 → 再测试)
```

## Verification

```python
# AST check: verify all get_prompt if-blocks are independent
for n in ast.walk(tree):
    if isinstance(n, ast.FunctionDef) and n.name == 'get_prompt':
        if_blocks = [s for s in n.body if isinstance(s, ast.If)]
        all_independent = all(not bool(ifn.orelse) for ifn in if_blocks)
        # Should be: 10 independent blocks, no elif/else
```
