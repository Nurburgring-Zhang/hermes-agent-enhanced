# PromptLibraryNode V18.3 — Output Port Redesign + Timeout Fix

**Date:** 2026-05-24  
**Session context:** User enabled all 3 outputs (storyboard + picture book + short drama) simultaneously. Hit timeout then redesigned output port behavior.

## Changes Applied

### 1. HTTP timeout 30s → 300s

```python
# __init__.py line 1159-1160
# BEFORE:
with urllib.request.urlopen(req, timeout=30) as resp:
# AFTER:
with urllib.request.urlopen(req, timeout=300) as resp:
```

### 2. max_tokens default 2048 → 10000, max 8192 → 100000

```python
# __init__.py line 76
# BEFORE:
"AI最大Token数": ("INT", {"default": 2048, "min": 256, "max": 8192, "step": 256}),
# AFTER:
"AI最大Token数": ("INT", {"default": 10000, "min": 256, "max": 100000, "step": 256}),

# __init__.py line 152 (function signature default)
# BEFORE:
AI最大Token数=2048,
# AFTER:
AI最大Token数=10000,
```

### 3. 提示词 port: single-line only

```python
# Folder mode (line 320-321)
# BEFORE:
final_prompt = "\n".join(result_texts)
# AFTER:
final_prompt = result_texts[0] if result_texts else ""

# AI batch mode (line 392)
# BEFORE:
final_prompt = "\n---\n".join(batch_results)
# AFTER:
final_prompt = batch_results[0] if batch_results else ""

# Storyboard mode (line 217-218)
# BEFORE:
final_prompt = ai_result
storyboard_prompt = ai_result
# AFTER:
storyboard_prompt = ai_result  # final_prompt NOT assigned — stays empty
```

### 4. Storyboard header (injected at line 218-228)

```python
sb_header = (
    f"【故事板总定义】生成一组完整的故事板分镜，模式为「{故事板模式}」，共{故事板镜头数量}个镜头，"
    f"风格为「{故事板风格}」。每个镜头包含：景别（7级好莱坞分类：极远景/全景/中全景/中景/近景/特写/极特写）、"
    f"500字以上极致细腻中文画面描述（主体动作+场景环境+光线氛围+色彩基调+构图+情绪）、500字以上中文"
    f"AI文生图Prompt（可直接用于Midjourney/SD/ComfyUI）、运镜方式（11种运镜+速度）、转场效果（8种转场）、"
    f"备注（叙事功能+情绪节奏+时长建议）。要求全组镜头交替使用远景/中景/近景/特写，避免连续3个同景别，"
    f"保持角色位置道具光线连贯性（180度法则），镜头之间具有因果关系推动剧情，"
    f"整体情绪曲线起承转合：开头吸引→中间推进→高潮爆发→收尾留悬念。色彩基调：{故事板色彩基调}。"
    f"景别偏好：{故事板常用景别}。运镜风格：{故事板运镜风格}。\n\n"
)
storyboard_prompt = sb_header + ai_result
```

### 5. Picture book header (lines 464-473)

```python
book_header = (
    f"【绘本总定义】生成一本完整的儿童绘本画册，共{绘本页数}页，风格为「{绘本风格}」。"
    f"每页包含：页码、300字以上极致细腻画面描述（主体角色+动作神态+场景环境+光线氛围+色彩+构图+细节纹理）、"
    f"300字以上中文AI文生图Prompt、绘本正文文案（适合亲子朗读）、视觉连续性提示（与前后页的关联）、"
    f"翻页惊喜设计（page-turn surprise）。要求角色外貌服饰颜色在所有页面高度一致，画面风格统一，"
    f"叙事遵循起承转合结构，每2-3页设置视觉高潮或翻页悬念，全景/中景/特写交替使用。色调：{绘本色调}。"
    f"年龄段：{绘本年龄段}。\n\n"
)
picture_book_prompt = book_header + picture_book_raw
```

### 6. Short drama header (lines 533-542)

```python
drama_header = (
    f"【短剧总定义】创作一部完整的AI短剧分镜头剧本，共{短剧镜头数}个镜头，风格为「{短剧风格}」。"
    f"每个镜头包含：镜头编号、景别（7级好莱坞景别分类）、400字以上极致细腻画面描述（角色动作+表情神态+"
    f"场景环境+光线氛围+色彩基调+构图+情绪+道具细节到眼神方向衣角飘动光影变化级）、400字以上中文"
    f"AI文生图/视频Prompt、台词/旁白、运镜方式（11种运镜+速度描述）、用途标注（叙事功能+建议时长）。"
    f"开场第1镜头必须是强钩子（黄金3秒法则），每15-20秒一个反转，竖屏9:16构图，"
    f"对白每句不超过15字，结尾镜头的悬念或反转让观众想看下一集。节奏：{短剧节奏强度}。"
    f"运镜：{短剧运镜风格}。\n\n"
)
short_drama_prompt = drama_header + short_drama_raw
```

## Key Design Decisions

1. **Storyboard no longer populates `final_prompt`** — because 提示词 port is now single-line only, storyboard content (which is inherently multi-shot/multi-paragraph) should only go to its dedicated port. If the user wants storyboard content as the main prompt, they should connect the 故事提示词 port to their downstream node instead.

2. **Headers are parameter-injected, not static** — uses `f-string` to incorporate `{故事板风格}`, `{绘本色调}`, `{短剧节奏强度}`, etc. This means every user's output has a customized header that reflects their exact settings.

3. **Raw + header pattern** — The AI call result is stored in a `_raw` variable first, then conditionally prefixed only if non-empty. This prevents "header + empty" output on AI failure.

4. **Serial execution unchanged** — Storyboard → Picture book → Short drama order remains. No parallelization needed since each is an independent API call.

## Testing Verification

```python
# Syntax check
python3 -c "import py_compile; py_compile.compile('__init__.py', doraise=True)"

# String presence check
grep -c "【故事板总定义】" __init__.py  # should be 1
grep -c "【绘本总定义】" __init__.py   # should be 1
grep -c "【短剧总定义】" __init__.py   # should be 1
grep -c "result_texts\[0\]" __init__.py  # should be 1
grep -c "batch_results\[0\]" __init__.py  # should be 1

# Verify no more "final_prompt = ai_result" in storyboard block
grep -n "final_prompt = ai_result" __init__.py  # should NOT match storyboard block (only AI gen block)
```

## File Stats (post-V18.3)

- **Total lines:** 1445
- **Total bytes:** 76,906
- **Return tuple:** 5 elements
- **Output ports:** 5 STRING
- **max_tokens default:** 10000
- **HTTP timeout:** 300s
