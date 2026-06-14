# V17.1+/V17.2 Storyboard Upgrade: 9 Modes, Director-Level Prompt Engineering

## Summary

The storyboard generator was upgraded from 8 basic modes to **9 professionally engineered modes**. All 8 legacy modes were rewritten with complete 6-section prompt architecture. A new 9th mode "剧情分镜" (Narrative Storyboard) was added based on a professional trailer director's prompt framework.

## Upgrade Trace

### What Changed

| Aspect | Before (V16.4) | After (V17.1+) |
|--------|---------------|----------------|
| System prompts | ~150 chars one-liner | 527-1220 chars multi-section |
| Structure | Single format skeleton | 4-step: Breakdown→Arc→Technique→KF |
| Consistency rules | None | Non-negotiable rules section |
| Visual anchors | Not included | 3-6 persistent visual anchors |
| Emotional arc | Not included | 4-stage: Setup/Build/Turn/Climax |
| Cinematography | Not included | Lens strategy+camera plan+focal length+lighting |
| Frame format | `【镜头N】【景别】【运镜】` | Complete: composition/action/camera/focus/lighting |
| Shot types | Basic set (5-6) | Professional: ELS/LS/MLS/MS/MCU/CU/ECU/Low/High |
| 剧情分镜 mode | ✗ not present | ✓ Special 3×3 grid, single cohesive prompt output |

### 9 Modes and Their Roles

| Mode | Role | Prompt Length | Format Focus |
|------|------|-------------|-------------|
| 电影分镜 | 预告片导演+分镜设计师 | 869 chars | 4-step workflow, ELS→ECU progression |
| 广告故事板 | 广告导演+创意总监 | 702 chars | Brand anchors, 3-beat rhythm, Slogan timing |
| 动画故事板 | 动画导演+分镜艺术家 | 652 chars | Physics squash/stretch, color script arc |
| 漫画分镜 | 漫画家+页面设计师 | 550 chars | Panel shapes, Z-path eye flow, dialog balloons |
| MV故事板 | 音乐视频导演 | 632 chars | Song structure mapping, light-by-music, VFX |
| 教程步骤 | 教程设计师+可视化专家 | 527 chars | Operation focus, arrow system, info hierarchy |
| 短视频分镜 | 爆款短视频导演 | 568 chars | First-3s hook, copy+CTA, timing marks |
| 品牌故事板 | 品牌策略总监 | 582 chars | Brand touchpoint map, 4-act arc, POV choice |
| 剧情分镜 | 电影分镜设计师+叙事专家 | **1220 chars** | **3×3 strict grid, absolute consistency, ECU/低角度/高角度** |

### 剧情分镜 Special Design

This mode is different from the other 8:

**System prompt** contains:
- Strict 3×3 grid structure (3 rows × 3 columns)
- Row 1: Establishing (ELS→LS→MLS) — builds the world
- Row 2: Core coverage (MS→MCU→CU) — captures emotion
- Row 3: Details & angles (ECU→Low Angle→High Angle) — visual impact

**User prompt** contains:
- The full 3×3 grid template with placeholder markers
- Requirements to output "故事梗概（解读）：" before the prompt body
- "不要生成新主体" rule — only use subjects from the story

**Output format:** A single cohesive AI image prompt containing all 9 frames labeled 1-9.

**Frame count:** NOT hardcoded to 9. Users can select 4/9/16 frames via the `故事板镜头数量` parameter. The 3×3 structure is a *default template suggestion* in the prompt, not a code-enforced limit. When user selects 4 frames, the prompt adapts to output only 4 frames.

### The Frame Count Fix

**Bug:** V17.1 initially hardcoded `actual_shot_count = 9 if 模式 == "剧情分镜"` — this was wrong.

**Fix:** Removed the hardcoded override entirely. The user's `故事板镜头数量` parameter is always respected. The 3×3 grid description in the system/user prompt serves as a *structural suggestion* to the AI, not a code-level constraint.

### NODE_CLASS_MAPPINGS Trap

When reconstructing a ComfyUI custom node from broken parts (e.g. after file truncation during multi-edit), the registration block at the bottom is extremely easy to forget:

```python
NODE_CLASS_MAPPINGS = {"PromptLibraryNodePro": PromptLibraryNodePro}
NODE_DISPLAY_NAME_MAPPINGS = {"PromptLibraryNodePro": "提示词库节点 V17.0"}
```

**Symptom:** "(IMPORT FAILED): D:\ComfyUI\custom_nodes\PromptLibraryNode" — ComfyUI silently ignores the node.

**Root cause:** The file is valid Python (AST parses fine), but lacks the two mandatory module-level variables that ComfyUI scans.

**Prevention:** After any file rebuild that involves appending a suffix (e.g. concatenating 4 temp files), always verify:
```python
import ast
code = open('__init__.py').read()
tree = ast.parse(code)
has_mappings = any(
    isinstance(n, ast.Assign) and any(
        isinstance(t, ast.Name) and 'NODE_CLASS_MAPPINGS' in t.id
        for t in n.targets
    )
    for n in ast.walk(tree)
)
```

## Test Results

V17.2: 29/29 tests pass (100%):
- 9 modes system prompts loaded correctly
- 剧情分镜 system prompt contains: 3×3, ELS/LS, absolute consistency, ECU, low angle, high angle
- 剧情分镜 user prompt works for 4/9/16 frames
- All 8 legacy modes unaffected
- Layout descriptions for 4/6/8/9/10/12/14/16 frames
- AST syntax valid
- All return statements produce 7 values
- Actual ComfyUI-style loading passes (with NODE_CLASS_MAPPINGS)

## Key Prompt Engineering Choices

1. **Continuous tone:** All prompts speak to the AI as a *professional practitioner* ("屡获殊荣的电影分镜设计师", "资深广告导演"), not an abstract instruction generator
2. **Non-negotiable rules:** Each mode has a "不可违反规则" section listing hard constraints the AI must not violate (continuity, consistency, environment matching)
3. **Structured output:** Each mode specifies the exact output format per frame/step, including technical parameters like focal length in mm, camera movement in %, and lighting setup labels
4. **Multiple scales:** The same prompt works for 4, 9, or 16 frames by embedding the grid structure as a *recommendation* rather than a *requirement*
