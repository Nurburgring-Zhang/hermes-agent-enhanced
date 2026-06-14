# V19 Session: DOM Widget Reference Image Upload + NO Numerical Parameters (2026-05-27)

## What Changed

### 1. Reference Image Upload: 9 IMAGE Ports → Custom DOM Widget

**The wrong approach (rejected by user):** 9 `("IMAGE",)` optional input ports. "参考图有9个独立输入端口？？这合理吗？？？"

**The correct approach:**
- Hidden STRING widget (`"参考图列表": ("STRING", {"default": "[]", "multiline": True})`) persists file references as JSON in workflow
- Custom DOM widget in JS (`addDOMWidget` not `addCustomWidget`) provides native file picker with `multiple=true`
- Upload via `fetch('/upload/image', ...)` to ComfyUI input directory
- Thumbnail preview grid with: object-fit:cover, 3-column flex-wrap layout, numbered badges (1-9), hover-delete buttons
- Python `_load_ref_image_tensors()` reads from ComfyUI input dir on execution
- 5th output port (`回调图片`, type IMAGE) passes first ref image through

**DOM widget size management:**
- `addDOMWidget` returns a widget object — override `computeSize()` to return height based on image count
- Images 0: 30px height. 1-3: 112px. 4-6: 194px. 7-9: 276px.
- ONLY the widget area changes height — node's other controls stay fixed
- NO `this.setSize()` calls — let ComfyUI's layout engine manage it
- `app.graph.setDirtyCanvas(true)` after grid update to trigger re-layout

**Three UI bugs that happened and were fixed:**
1. Images stacking on top of each other → `display:grid` changed to `display:flex;flex-wrap:wrap` with fixed-size (78px) cards
2. Node growing infinitely on image delete → removed `this.setSize()` calls
3. Widget overflowing node bounds → added `box-sizing:border-box` and `flex:none` on cards

### 2. NO Numerical Parameters in AI Output (User Fury)

**Signal:** User pasted AI-generated 总纲 with cm/mm/dB/色相等 values and said "没有任何AIGC模型能理解这样的描述！！！模型无法理解这么详细的细节！！！！"

**Fix:** `_build_global_context()` now has explicit `**禁止使用数值参数**` instruction on EACH section:
- 角色: `**禁止一切数值参数（厘米/毫米/度/色值/dB等），禁止微观生物学细节（毛细血管、毛密度、肌肉名称等）**`
- 场景: `**用氛围描写代替空间参数，禁止数值**`
- 氛围画质: `**用风格化语言，禁止数值参数**`
- 声音: `**用听觉感受描述，不用分贝/频率等参数**`

**Storyboard 画面描述 simplified:**
- BEFORE: `角色肢体各部件的关节角度和肌群状态+面部微动作序列+场景每层景深的具体陈设+光源方向/色温/强度+色彩基调的色相饱和度明度参数+构图的具体几何形式+相机焦距和光圈参数`
- AFTER: `角色肢体动作+面部微表情+场景每层景深的具体陈设+光源方向/色彩氛围+构图方式+空气质感`

**Still needs work:** All 21 prompt templates (storyboard, picture book, short drama, 4 child content, 7 design modes) need individual audit. Many still have instructions that encourage numerical output. This session only fixed the global context and the most obvious offenders.

### 3. Input Layout (Reordered 3 Times)

Final correct order (user-validated after 3 attempts):
```
required:  ① 文件夹路径 ~ 翻译方向（traditional library — TOP）
           ② API地址 ~ AI最大Token数（after translation）
           ③ 参考图列表（after API — NOT in optional!）
           ④ 模式选择 ~ 运镜风格（after ref images）
optional:  ⑤ 镜头数量 ~ 背景类型（BOTTOM）
```

**Key lesson:** `required` renders ABOVE `optional`. To intersperse three visual sections, ALL three must be in `required`.

### 4. Output Ports: 6→5

| Port | Type | Content |
|------|------|---------|
| 提示词 | STRING | Traditional library/AI gen/design mode output |
| 模式输出 | STRING | Storyboard/picture book/short drama/child content |
| 负面提示词 | STRING | Auto-generated negative words |
| 元数据JSON | STRING | `{"mode":"...","type":"...","shots":N}` |
| 回调图片 | IMAGE | First reference image (None if no ref) |

## Commands Used

```bash
# Python import test
cd /mnt/d/ComfyUI && python3 -c "import sys; sys.path.insert(0, 'custom_nodes/PromptLibraryNode'); import importlib.util; spec = importlib.util.spec_from_file_location('node', 'custom_nodes/PromptLibraryNode/__init__.py'); mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); print('OK:', list(mod.NODE_CLASS_MAPPINGS.keys()))"
```
