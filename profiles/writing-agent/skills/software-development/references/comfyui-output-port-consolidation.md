# ComfyUI Output Port Consolidation Pattern

## Problem

A node with multiple output ports for each AI generation mode (绘本/短剧/故事板/儿童) wastes downstream connections. The user needs to connect 4 separate ports even when only one mode is active.

## Solution: Consolidate to "模式输出" Single Port

### Before (6 ports)

```python
RETURN_TYPES = ("STRING", "STRING", "STRING", "STRING", "STRING", "STRING")
RETURN_NAMES = ("提示词", "绘本提示词", "短剧提示词", "故事提示词", "负面提示词", "儿童提示词")
```

Each mode writes to its own port; user picks which port to use downstream.

### After (5 ports)

```python
RETURN_TYPES = ("STRING", "STRING", "STRING", "STRING", "IMAGE")
RETURN_NAMES = ("提示词", "模式输出", "负面提示词", "元数据JSON", "回调图片")
```

All mode outputs route through "模式输出". A "元数据JSON" port tells downstream which mode was active.

### Dispatch Logic

```python
if mode == "电影分镜":
    mode_output = storyboard_result(...)
    meta = {"mode": "电影分镜", "type": "故事板"}
elif mode == "绘本模式":
    mode_output = picture_book_result(...)
    meta = {"mode": "绘本模式", "type": "绘本"}
elif mode == "短剧模式":
    mode_output = short_drama_result(...)
    meta = {"mode": "短剧模式", "type": "短剧"}
# ... etc

return (final_prompt, mode_output, negative_prompt, json.dumps(meta), callback_image)
```

### When to Consolidate vs Keep Separate

**Consolidate when:**
- Modes are mutually exclusive (only one active at a time)
- User already selects mode from a dropdown
- Different modes produce the same data type (all STRING)
- User wants to reduce node width/complexity

**Keep separate when:**
- Multiple modes can run simultaneously (user wants all ports)
- Different ports feed different downstream nodes
- Ports have different data types (STRING vs IMAGE vs LATENT)

## Related Pattern: Hidden Widget for Metadata

"元数据JSON" can also be a hidden output (not shown on node but accessible downstream). ComfyUI supports this with `"hidden": {"unique_id": "UNIQUE_ID"}` in INPUT_TYPES for node identification.

## History
- **2026-05-27**: PromptLibraryNode V19 consolidated from 6 ports (提示词/绘本/短剧/故事/负面/儿童) to 5 ports (提示词/模式输出/负面/元数据JSON/回调图片). User explicitly approved this consolidation.
