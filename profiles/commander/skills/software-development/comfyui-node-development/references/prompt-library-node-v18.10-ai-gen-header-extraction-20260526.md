# V18.10: AI-Generated 总纲 with Extraction — Universal Settings Restructure

## Date: 2026-05-26
## Session: PromptLibraryNode V18.10

## Problem

The `总纲` (header/preface) for each output port (故事板/绘本/短剧/儿童) was a **static Python f-string** with parameterized but
generic templates like "风格：X，色调：Y，年龄段：Z". These were:

1. **Not specific enough** — "画质标准：8K细腻/超写实/水彩质感" is a bullet list, not a vivid description
2. **Not matched to content** — same template regardless of whether the theme is sci-fi, fairy tale, or period drama
3. **Not useful for downstream AI tools** — a downstream CLIP/LLM can't use "色调：暖色调" to generate anything specific

User explicitly demanded: "将角色设定、形象、环境、场景、物品、背景、氛围、画面、声音、世界观等所有通用设定，全部写到每份提示词的总纲中",
referencing the detailed example (robot cleaner, zombie farm, atomic punk) where every character/item/scene had vivid concrete descriptions.

## Solution: AI-Generated 总纲 with Automatic Extraction

### Core Pattern

1. **System prompt instructs AI to output 总纲 first** — before the actual content
2. **Code automatically extracts** the 总纲 section from AI output using delimiter markers
3. **总纲 + actual content** are concatenated with the `# 【总纲】` wrapper format
4. **Fallback** — if AI output doesn't match expected format, use a short default header

### Implementation (4 Ports)

Each port follows the identical pattern:

#### Step 1: Inject Instructions into System Prompt

```python
# In the global_ctx injected before _call_ai:
global_ctx = (
    f"\n\n# 全局设定（本任务所有输出必须基于以下设定）\n"
    f"你必须严格按照以下要求输出：\n"
    f"1. **先在输出最开头输出一个完整的【通用设定与核心世界观】板块**，包含：\n"
    f"   - 【通用基础设定】：基于主题「{theme}」和风格「{style}」，"
    f"为每个角色写出具体的外貌描述（性别/年龄/身高/体型/发型/服装款式颜色材质/标志性道具）\n"
    f"   - 【核心世界观之场景设定】：写出具体的场景空间描述，至少2个核心场景\n"
    f"   - 【核心世界观之氛围与画质标准】：画质要求、色彩基调、光线风格、美学参考\n"
    f"   - 【核心世界观之声音设定】：本任务的同期声环境描述\n"
    f"2. 然后空一行，输出分隔线：---\n"
    f"3. 再输出具体内容。\n"
    f"总纲中的设定必须具体、有细节、高质量，不能是通用模板。\n\n"
)
sys_p += global_ctx
```

#### Step 2: Extract from AI Output

```python
world_pos = ai_result.find("【通用设定与核心世界观】")
sep_pos = ai_result.find("\n---\n")
if world_pos >= 0 and sep_pos > world_pos:
    extracted_header = ai_result[world_pos:sep_pos].strip()
    actual_content = ai_result[sep_pos+5:].strip()
    final_output = f"# 【总纲】\n{extracted_header}\n\n---\n\n{actual_content}"
else:
    # Fallback default
    default = f"# 【总纲】\n**通用设定与核心世界观**\n..."
    final_output = default + ai_result
```

#### Step 3: The `# 【总纲】` + `---` Wrapper

All four ports now output the same format:

```
# 【总纲】
[AI-generated 通用设定内容: 角色/场景/氛围/声音]

---

[actual content: 分镜/页面/片段/镜头]
```

### 4 Ports Updated

| Port | Location | global_ctx variable | Extraction variable |
|------|----------|---------------------|---------------------|
| 故事板 | Step 1 in get_prompt | `global_ctx` | `sb_extracted_header`/`sb_content` |
| 绘本 | Picture book section | `book_global_ctx` | `book_extracted`/`book_content` |
| 短剧 | Short drama section | appended to `drama_sys` | `drama_extracted`/`drama_content` |
| 儿童 | Child content section | `kid_global_ctx` | `kid_extracted`/`kid_content` |

### Before/After Comparison

**Before (static template):**
```
【绘本总定义】生成一本完整的儿童绘本画册，共8页，风格为「水彩插画」。
每页包含：页码、画面描述（主体角色/动作细节/场景环境/光线氛围/色彩基调/构图/纹理/视角/画质）、
绘本正文文案（适合亲子朗读）、视觉连续性提示（与前后页的关联）。
要求角色外貌服饰颜色在所有页面高度一致...
```

**After (AI-generated, example for a unicorn fairy tale):**
```
# 【总纲】
**通用设定与核心世界观**
【通用基础设定】
**小月**：6岁的小女孩，齐肩黑发扎成两条小辫子，穿粉色碎花连衣裙和红色小皮鞋，脸上总是带着
好奇的笑容。小月最喜欢在花园里探险。

**小独角兽**：只有巴掌大小的白色小独角兽，鬃毛是彩虹色的，角尖会发出柔和的银色光芒。
它很害羞但特别温柔，只有心地善良的孩子才能看到它。

【核心世界观之场景设定】
场景一：小月家的后花园，开满了五颜六色的花朵，有向日葵、玫瑰和薰衣草，中央有一棵老橡树，
树下有一个用树枝搭成的小棚子，那是小月的秘密基地。阳光透过树叶洒下斑驳的光影。

场景二：迷雾森林，高大的树木遮天蔽日，空气中漂浮着闪闪发光的魔法尘埃，
地面上长满了发光的蘑菇。一条蜿蜒的小路通向森林深处。

【核心世界观之氛围与画质标准】
水彩插画风格，柔和温暖色调，以粉紫+草绿+暖黄为主色。画面细腻梦幻，
光线柔和自然，带有轻微的空气感。8K细腻度，水彩晕染质感。
---

第1页
- **画面**：阳光明媚的后花园，小月蹲在老橡树下，用手指轻轻碰触一朵蒲公英...
- **文字**：小月有一个秘密，她的花园里住着一只小独角兽...
```

### 4-Rule-File Sync

The same session also synchronized the 7 rules across all 4 agent configuration files:

| File | Scope |
|------|-------|
| `~/.hermes/SOUL.md` | Hermes core soul file |
| `~/.hermes/AGENTS.md` | Claude Code / Copilot / Cline / Aider |
| `~/.hermes/CLAUDE.md` | Claude CLI |
| `~/.hermes/.cursorrules` | Cursor / Windsurf |

Rules 2-7 were strengthened: 阶段性复盘 before entering next phase, 深度自检 for complete review, 
强制循环 at least 3 rounds, 发现缺陷主动修复不等用户指出, 中断主动自检恢复不等指令.
