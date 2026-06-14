# ComfyUI Custom DOM Widget for Image Upload + Thumbnail Preview

## Problem
ComfyUI's native `image_upload` widget only supports single-file upload. For multi-reference-image input (up to 9 images), using 9 separate `IMAGE` input ports is clunky and wastes node space.

## Solution: Hidden STRING Widget + addDOMWidget

### Architecture

```
┌──────────────────────────────────────────┐
│  载入参考图：  [+ 选择文件上传]            │  ← DOM button
│  ┌───┐ ┌───┐ ┌───┐                      │
│  │1  │ │2  │ │3  │ ← thumbnail grid     │  ← flex-wrap, auto-height
│  └───┘ └───┘ └───┘                      │
│  [hidden: 参考图列表] = "[{\"filename\":...}]" │  ← STRING widget, serialized JSON
└──────────────────────────────────────────┘
```

### Python Side

```python
# In INPUT_TYPES, add a hidden STRING widget:
"参考图列表": ("STRING", {"default": "[]", "multiline": True}),

# In get_prompt, parse and load:
ref_image_files = self._parse_ref_image_list(kwargs.get("参考图列表", "[]"))
ref_image_tensors = self._load_ref_image_tensors(ref_image_files)

# Parse: simple JSON array of {filename, subfolder, type}
def _parse_ref_image_list(self, ref_list_str):
    if not ref_list_str or ref_list_str.strip() in ("", "[]"):
        return []
    try:
        items = json.loads(ref_list_str)
        return [item for item in items 
                if isinstance(item, dict) and "filename" in item][:9]
    except (json.JSONDecodeError, TypeError):
        return []

# Load: use folder_paths to find files on disk
def _load_ref_image_tensors(self, file_items):
    import folder_paths, numpy as np
    from PIL import Image
    tensors = []
    for item in file_items:
        img_path = folder_paths.get_annotated_filepath(
            f"{item['filename']} [input]")
        pil_img = Image.open(img_path).convert("RGB")
        w, h = pil_img.size
        if w > 4096 or h > 4096:  # filter oversized
            continue
        img_np = np.array(pil_img).astype(np.float32) / 255.0
        img_tensor = torch.from_numpy(img_np)[None,]  # (1, H, W, C)
        tensors.append(img_tensor)
    return tensors
```

### JavaScript Side

```javascript
// Core pattern in beforeRegisterNodeDef.onNodeCreated:
requestAnimationFrame(() => {
    // 1. Hide the original STRING widget
    const refWidget = this.widgets?.find(w => w.name === '参考图列表')
    refWidget.computeSize = () => [0, -4]
    refWidget.hidden = true

    // 2. Create DOM container with upload button + thumbnail grid
    const container = document.createElement('div')
    container.style.cssText = 'width:100%;display:flex;flex-direction:column;gap:4px;'

    // ... build header row (label + upload button + hidden file input)
    // ... build grid (display:flex;flex-wrap:wrap;gap:4px)

    // 3. Add as DOM widget with computeSize for auto-height
    const domWidget = this.addDOMWidget('ref_image_upload', 'customwidget', container)
    domWidget.computeSize = (width) => {
        const c = this._refImagePreviews?.length || 0
        if (c === 0) return [width || 260, 30]
        return [width || 260, 30 + Math.ceil(c / 3) * 82]
    }
    
    // 4. Ensure node is wide enough
    if (this.size && this.size[0] < 280) this.setSize([280, this.size[1]])
})
```

### Upload Flow

1. User clicks "+ 选择文件上传" button
2. Hidden `<input type="file" multiple>` opens file picker
3. For each selected file:
   a. `createImageBitmap()` checks dimensions (reject >4096)
   b. `FileReader.readAsDataURL()` generates base64 thumbnail preview
   c. `POST /upload/image` with FormData uploads to ComfyUI input directory
   d. Response returns `{name, subfolder}` — push to `_refImageFiles[]`
4. Sync `_refImageFiles` to hidden STRING widget: `refWidget.value = JSON.stringify(files)`
5. Redraw thumbnail grid

### Thumbnail Grid Layout

```css
/* Container */
display: flex; flex-wrap: wrap; gap: 4px;

/* Card size: responsive to node width */
const S = Math.min(78, Math.max(50, (nodeWidth) / 4 - 8))

/* Each card */
position: relative; width: S px; height: S px; flex: none;
border-radius: 4px; overflow: hidden;

/* Number badge (左上角编号) */
position: absolute; top: 1px; left: 1px;
background: rgba(0,100,220,0.92); color: #fff;

/* Delete button (×, hover show) */
position: absolute; top: 1px; right: 1px; display: none;
card.onmouseenter = () => { del.style.display = 'block' }
```

### Key Pitfalls

1. **Node grows unbounded on delete** — NEVER call `this.setSize()` in the redraw function. Let `computeSize` on the DOM widget handle auto-height. `setSize` while the DOM widget is within the node will push other widgets down and cause layout loops.
2. **DOM widget renders outside node** — This happens when the node is too narrow. Set a minimum width in `onNodeCreated`.
3. **Workflow serialization loses previews** — Store file metadata (filename/subfolder/type) in the hidden STRING widget, NOT base64 previews. On workflow load, reconstruct thumbnails from stored filenames via `api.apiURL('/view?filename=...')`.
4. **Flex-wrap vertical-only resize** — Only the widget's height changes. Other node widgets stay at their original size.

### Comparison: addDOMWidget vs addCustomWidget

| Feature | addDOMWidget | addCustomWidget |
|---------|-------------|-----------------|
| DOM rendering | Automatic, positioned in node | Manual draw() callback |
| Height calculation | computeSize() callback | computeSize() on widget object |
| Overlap with other widgets | No (ComfyUI manages space) | Must calculate y position |
| Button/file input support | Yes (native HTML) | No (canvas only) |
| Risk of rendering outside node | Medium (if node too narrow) | Low (canvas clipped) |

**Use addDOMWidget for interactive controls (buttons, file inputs). Use addCustomWidget for canvas-only content that must never overflow.**

## History
- **2026-05-27**: Original pattern developed for PromptLibraryNode V19. Replaced 9 separate IMAGE input ports with single DOM upload widget. The user explicitly rejected the 9-port approach as "不合理".
