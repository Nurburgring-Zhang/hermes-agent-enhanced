# PromptLibraryNode V19: Unified Modes, 7 Design Prompts, Reference Image Upload Widget, 5-Output Ports

**Session: 2026-05-27**

## Summary

Complete V18→V19 rewrite of `D:\ComfyUI\custom_nodes\PromptLibraryNode\__init__.py`. 4 major architectural changes driven by user feedback.

## Change 1: Unified Mode Selector

**Before (V18):** 6 independent control groups (storyboard dropdown + 绘本 BOOLEAN + 短剧 BOOLEAN + 儿童 BOOLEAN + 4 seed modes). 57+ widgets.

**After (V19):** Single `"模式选择"` dropdown with 25 options (including "关闭").

**Dispatch pattern:** `if/elif/elif/elif/elif` based on `MODE_CATEGORIES_STORYBOARD`, `MODE_CATEGORIES_CHILD`, `MODE_CATEGORIES_DESIGN` sets. Each mode group calls its own `_process_*_mode()` method.

### Mode Categories

| Category | Modes | Count |
|----------|-------|:-----:|
| 关闭 | "关闭" | 1 |
| 故事板 | 电影分镜, 广告故事板, 动画故事板, 漫画分镜, MV故事板, 教程步骤, 短视频分镜, 品牌故事板, 剧情分镜 | 9 |
| 绘本 | 绘本模式 | 1 |
| 短剧 | 短剧模式 | 1 |
| 儿童 | 儿童视频格式一, 儿童视频格式二, 儿童微动视频/GIF, 儿童绘本格式 | 4 |
| 设计 | 电商套图, 海报设计, 品牌设计, PPT设计, 逻辑关系图设计, 三视图设计, 爆炸拆解图设计, 流水线图设计 | 8 |
| **Total** | | **24** |

## Change 2: 7 Professional Design Prompts

Each prompt has 3 mandatory sections: `# 角色设定` (world-class expert identity with real designer references), `# 核心设计哲学` (3-4 actionable rules), `# 输出要求` (structured output spec).

### Designer References Per Mode

| Mode | Reference Designers |
|------|-------------------|
| 电商套图 | Apple/戴森/三宅一生 product visual directors |
| 海报设计 | 福田繁雄, 杉浦康平, 保罗·兰德, David Carson |
| 品牌设计 | Apple/MUJI/Patagonia/Aesop brand VPs |
| PPT设计 | TEDx/世界经济论坛/Apple keynote consultants |
| 逻辑关系图 | Edward Tufte, 瑞士国际主义, Richard Saul Wurman |
| 三视图 | Dieter Rams, Apple industrial design team |
| 爆炸拆解图 | 任天堂Labo, IKEA instructions, 《万物运转的秘密》 |
| 流水线图 | Toyota Production System, BPMN 2.0, Google Material Design |

## Change 3: Reference Image Upload Widget

**User rejected 9-port approach** — "参考图有9个独立输入端口？？这合理吗？？？"

**Correct implementation:** Custom DOM widget using `addCustomWidget` + `getCustomWidgets`. See `references/comfyui-ref-image-upload-download-dom-widget.md` for complete pattern.

Key files:
- Python: `_parse_ref_image_list()`, `_load_ref_image_tensors()` — parse JSON, load images from input dir
- JS: `REF_IMAGE_UPLOAD` widget via `getCustomWidgets` — file picker + thumbnail grid + upload
- JS: `beforeRegisterNodeDef` hides the original "参考图列表" widget

## Change 4: 5-Output Ports

**Before (V18):** 6 ports (提示词, 绘本提示词, 短剧提示词, 故事提示词, 负面提示词, 儿童提示词)

**After (V19):** 5 ports

| Port | Type | Description |
|------|------|-------------|
| 提示词 | STRING | AI single-line / library / design mode |
| 模式输出 | STRING | Storyboard / picture book / short drama / child content |
| 负面提示词 | STRING | Negative prompt string |
| 元数据JSON | STRING | `{"mode":"...","type":"...","shots":N}` |
| 回调图片 | IMAGE | First reference image passthrough |

## Files

| File | Lines | Size |
|------|:-----:|:----:|
| `__init__.py` | 1467 | 95KB |
| `web/PromptLibraryNode.js` | 286 | 13KB |

## Code Review Findings

### Critical Bugs Found and Fixed
1. **Missing `import base64` and `import io`** — `NameError` on thumbnail attempt
2. **Line 290 double-tuple return** — `return ("", ""), ("", "")` returned `(("", ""), ("", ""))` instead of `("", "")`
3. **JS async image loading in draw loop** — `new Image()` inside `onDrawForeground` with `onload` callbacks referencing potentially stale `ctx`
4. **Unused imports** — `hashlib`, `math`, `Path` removed

### Clean Code Decisions
- All methods present (65 methods, 31 core)
- Syntax check passes
- All 24 modes route correctly in tests
- V18 functionality preserved (AI gen, library, polish, translation, smart filter, subject filter)
