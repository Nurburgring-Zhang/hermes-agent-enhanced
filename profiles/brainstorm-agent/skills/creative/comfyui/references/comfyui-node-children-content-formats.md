# Children's Content Module — Architecture & Patterns

**Source:** PromptLibraryNode __init__.py (PromptLibraryNode Pro V18+)
**Last Updated:** 2026-06-02 (session: 角色特征 fix + symbol ban + missing format dimensions)

## Overview

A ComfyUI custom node module that generates 4 types of children's content via LLM API calls. Each mode has a dedicated `_build_child_*()` method in the `PromptLibraryNode` class.

| Mode | Method | Output Structure |
|------|--------|-----------------|
| 儿童视频格式一 | `_build_child_v1` | 7-field per fragment: 时空锚定/场景描述/动态描述/分镜场景(变化)/角色特征(变化)/旁白对话/特效TIPS |
| 儿童视频格式二 | `_build_child_v2` | Qi-Cheng-Zhuan-He 4-act structure → segments with 场景/画面描述/旁白/对话(带表情动作标注)/TIPS/分镜场景(变化)/角色特征(变化)/动态描述 |
| 儿童微动视频/GIF | `_build_child_gif` | Page-based (第N页) → 核心动作/画面/动效 + 分镜场景(变化)/角色特征(变化) |
| 儿童绘本格式 | `_build_child_book` | Page-based (第N页) → 画面/文案/旁白对话/视觉连续性提示/构图景别 + 分镜场景(变化)/角色特征(变化) |

## Implementation Architecture (V18+)

### All 4 methods follow a consistent pattern:

```python
def _build_child_XX(self, style_text, age_text, ref_section, env_section):
    sense = self._pick_story_sense()  # Random story template
    return (
        f"{sense}\n"
        f"故事感总纲...\n"
        "角色设定\n你是一位世界顶级的儿童动画编剧兼分镜师。\n"
        "输出格式\n<format dimensions here>\n"
        "<example output if needed>\n"
        "创作原则\n<rules here>\n"
        f"年龄段适配\n{age_text}\n画面风格\n{style_text}\n{ref_section}{env_section}\n"
        "输出约束：严禁使用任何符号标记——禁止#、禁止**、禁止-开头、禁止→、禁止1. 2. 3.编号、禁止---分隔线。直接用纯文字叙述。各维度之间用换行分隔，不要用符号装饰维度名称。\n"
    )
```

### 4-Header hardcoded total sections (pre-pended before AI result)

ALL 4 total definition sections must use PURE TEXT without symbols:
- ❌ `【{mode}总纲】` → ✅ `{mode}总纲`
- ❌ `1、整体视觉风格：` → ✅ `整体视觉风格：`
- ❌ `2、角色物品设定：` → ✅ `角色物品设定：`
- ❌ `3、道具/武器：` → ✅ `道具或武器：`
- ❌ `4、场景设定：` → ✅ `场景设定：`
- ❌ `5、氛围与画质标准：` → ✅ `氛围与画质标准：`
- ❌ `6、声音设定：` → ✅ `声音设定：`
- ❌ `7、核心叙事设定：` → ✅ `核心叙事设定：`

These are Python f-string hardcoded in 4 places in __init__.py, NOT LLM-generated:
- `_build_storyboard_system_prompt` (L583-600) — storyboard mode
- `_process_picture_book_mode` (L632-646) — picture book mode
- `_process_short_drama_mode` (L675-689) — short drama mode
- `_process_child_mode` (L722-738) — child video modes

Every time someone touches `__init__.py`, run:
```bash
grep -n '【.*总纲】\|[1-7]、' __init__.py | grep -v '故事感总纲\|story_sense\|story_sense_library'
```

## Output Format Reference per Mode

### 儿童视频格式二 (CURRENT — 2026-06-02)

The COMPLETE format definition. Was previously missing entirely (only had principles, no format structure).

```
第一幕起
【场景】森林·晴·日·外
画面描述：晴朗的夏天，大森林里暖洋洋的。小蛇溜溜正蜷在软软的草地上晒太阳，晃着细细的小尾巴。
旁白：太阳暖暖照下来，溜溜今天好开心。
对话：小蛇溜溜（开心扭身体）：太阳暖暖真舒服，溜溜今天好开心！
TIPS：该片段的关键提示

（以下维度仅在有变化时出现：分镜场景——地点/时间/光线/环境氛围变化，2-3句。角色特征——外貌/服装/状态变化，2-3句。动态描述——动效和运动方式。）
```

### 儿童微动视频/GIF (CURRENT — 2026-06-02)

Was previously only 4 lines of principles. Now has full format:

```
第N页
核心动作：该页的核心情节节点/动作，一句话概括（带情绪关键词）。
画面：场景氛围、角色位置、关键视觉元素、光线色彩情绪，2-3句。用孩子的语言描述。
动效：标注该页的动效和循环方式。首帧等于末帧。
（分镜场景和角色特征仅在有大变化时输出。）
```

### 儿童绘本格式 (CURRENT — 2026-06-02)

Was previously half-baked with no format dimensions. Now has full format:

```
第N页
画面：场景氛围、角色位置和表情动作、关键视觉元素、光线色彩情绪，2-4句。用孩子的语言描述。
文案：绘本正文文字，适合亲子朗读，注意节奏感和韵律美。
旁白/对话：多角色时标注角色名。
视觉连续性提示：该页与上一页/下一页的视觉关联说明（可选）。
构图与景别：构图方式（居中/三分法/对角线等）和景别（远景/中景/近景/特写）。
（分镜场景和角色特征仅在有大变化时输出。）
```

## Critical Prompt Engineering Rules (格林主人 2026-06-02)

### Rule 1: "角色特征" must be a VISIBLE-APPEARANCE-CHANGE dimension, NOT an action dimension

**WRONG** (produces action narrative that overlaps with 画面/画面描述):
```
角色特征：有角色特征变化时输出完整角色描述（外貌、服装、表情变化，2-3句）。无变化时不出现
```

**RIGHT** (forces LLM to interpret it as visible appearance changes only):
```
角色特征：仅在角色外貌/服装/状态有实质性变化时输出（换装/变脏/受伤/新增饰品等可见变化）。禁止写角色动作叙事（那是画面维度的事）。无变化时此行整行不出现。
```

Key additions:
- "仅在角色外貌/服装/状态有实质性变化时" — not every shot, only when something visible changed
- "换装/变脏/受伤/新增饰品等可见变化" — concrete examples of what counts
- "禁止写角色动作叙事（那是画面维度的事）" — explicit boundary between 角色特征 and 画面
- Apply to ALL 4 methods (v1, v2, gif, book) + the "变化标注规则" in 画面铁律

### Rule 2: ABSOLUTE SYMBOL BAN

Every `_build_child_*()` method must end with:
```
输出约束：严禁使用任何符号标记——禁止#、禁止**、禁止-开头、禁止→、禁止1. 2. 3.编号、禁止---分隔线。直接用纯文字叙述。各维度之间用换行分隔，不要用符号装饰维度名称。
```

LLM will STILL produce `**第1页：标题**` `---` `1、` `2、` `- 核心动作` etc. if the system prompt doesn't explicitly ban them.

### Rule 3: Every mode MUST have a complete format dimension definition

If a `_build_child_*()` method only has principles (创作原则) and no format structure (输出格式), the LLM will produce free-form narrative. Every mode needs:

```python
"角色设定\n你是一位...\n"
"输出格式\n<numbered or bulleted dimension list>\n"
"创作原则\n<principles>\n"
```

### Rule 4: 对话格式 with 表情动作标注

对话 must include parenthesized action/emotion annotations:
```
小蛇溜溜（开心扭身体）：太阳暖暖真舒服，溜溜今天好开心！
小兔子（耷拉着小脑袋，轻轻叹气）：呜呜，到底哪里才有躲雨的地方呀？
```

This goes in both the system prompt definition AND the output example.

### Rule 5: 儿童视频格式二 must be Qi-Cheng-Zhuan-He 4-act structure

Not just numbered fragments. The 4 acts provide narrative rhythm:
- 第一幕起 — setup, introduce character + problem
- 第二幕承 — attempt, meet obstacles, meet helper
- 第三幕转 — turning point, resolution approach
- 第四幕合 — conclusion, emotional closure

## Symbol Ban Coverage Check

To verify all `_build_*` methods have symbol constraint:

```python
import re
with open('__init__.py') as f: content = f.read()
for m in re.findall(r'def (_build_\w+)\(self', content):
    idx = content.find(f'def {m}(self')
    body = content[idx:idx+1500]
    has_ban = '禁止' in body and ('**' in body or '符号' in body)
    print(f"{'✅' if has_ban else '❌'} {m}")
```

Required coverage: all `_build_child_*` + `_build_storyboard_system_prompt` + `_build_picture_book_system_prompt` + `_build_short_drama_user_prompt`.

## Backup Protocol

Before ANY change to `__init__.py` in PromptLibraryNode:
```bash
cp /mnt/d/ComfyUI/custom_nodes/PromptLibraryNode/__init__.py \
   /mnt/d/Hermes/备份/PromptLibraryNode_init_bak_$(date +%Y%m%d_%H%M%S).py
```

After ANY change, run:
```bash
python3 -c "import py_compile; py_compile.compile('/mnt/d/ComfyUI/custom_nodes/PromptLibraryNode/__init__.py', doraise=True)"
```

## Pitfalls

1. **patch tool fails on f-string escapes** — `__init__.py` has complex f-string quotes `f\"...\"` inside Python multiline strings. The `patch` tool's escape-drift detector falsely flags these. Use `python3 << 'PYEOF'` heredoc with `.replace()` instead.
2. **`_build_child_v2` is NOT in `format_templates`** — children's modes bypass `format_templates` entirely. They're dispatched via `_build_child_system_prompt()` → `_build_child_v2()`. Fixing `format_templates` has no effect on children's output.
3. **Total headers are HARDCODED f-strings** — `【{mode}总纲】`, `1、整体视觉风格：` etc. are in the 4 `header = (...)` blocks (L583-L600, L631-L647, L674-L690, L722-L738). These are NOT LLM-generated. System prompt symbol bans have zero effect on them. They must be changed in code.
4. **DUPLICATE child_v2 code path** — There appear to be TWO `_process_child_mode` sections in __init__.py (one for old architecture, one V18). The `_build_child_v2` method lives in the V18 section. Make sure edits target the right one.
