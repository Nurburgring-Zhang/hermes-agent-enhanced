# ComfyUI Reference Image Upload with DOM Widget (V19)

## The Right Way: Custom DOM Widget + `/upload/image` API

**Session (2026-05-27):** User rejected the 9-port IMAGE approach and the temp-file+`/view` approach. The correct approach is a **custom DOM widget** embedded in the node.

### Architecture

```
User clicks "选择文件上传" button in node widget
  → <input type="file" multiple accept="image/*"> opens native file picker
  → User selects 1-9 images
  → For each file:
      1. Frontend pre-checks size via createImageBitmap() — skip if >4096×4096
      2. Display thumbnail (FileReader.readAsDataURL → img.src)
      3. POST to /upload/image (ComfyUI's built-in upload endpoint)
      4. Store returned {filename, subfolder, type: "input"} in node._refImageFiles[]
  → Serialize to "参考图列表" STRING widget as JSON
  → Python reads "参考图列表" on next execution
```

### Python Side

No IMAGE input ports needed. Just a single hidden STRING widget:

```python
INPUT_TYPES = {
    "optional": {
        "参考图列表": ("STRING", {"default": "[]", "multiline": True}),
    }
}
```

The Python `get_prompt` parses this JSON and loads images from disk:

```python
def _parse_ref_image_list(self, ref_list_str):
    """Parse JSON array of {filename, subfolder, type} from the hidden widget"""
    if not ref_list_str or ref_list_str.strip() in ("", "[]"):
        return []
    try:
        items = json.loads(ref_list_str)
        return [item for item in items if isinstance(item, dict) and "filename" in item][:9]
    except (json.JSONDecodeError, TypeError):
        return []

def _load_ref_image_tensors(self, file_items):
    """Load images from ComfyUI input directory, filter >4096"""
    import folder_paths, numpy as np
    from PIL import Image
    tensors = []
    for item in file_items:
        # file is in ComfyUI/input/ directory
        img_path = folder_paths.get_annotated_filepath(f"{item['filename']} [input]")
        pil_img = Image.open(img_path).convert("RGB")
        w, h = pil_img.size
        if w > 4096 or h > 4096:
            continue  # silently skip oversized
        img_np = np.array(pil_img).astype(np.float32) / 255.0
        img_tensor = torch.from_numpy(img_np)[None,]
        tensors.append(img_tensor)
    return tensors
```

**Design rule:** The "参考图列表" widget is hidden (`computeSize = () => [0, -4]`) — its only purpose is to persist file references in the workflow JSON. The DOM widget handles all UI interaction.

### JavaScript Side

**Critical pattern — Use `addCustomWidget` with a DOM element, NOT `onDrawForeground`:**

```javascript
app.registerExtension({
    name: "PromptLibraryNode.RefImageUpload",

    async getCustomWidgets(app) {
        return {
            REF_IMAGE_UPLOAD(node, inputName, inputData, app) {
                // Create container DOM element
                const container = document.createElement('div')
                container.style.cssText = `...`
                
                // Header: title + "选择文件上传" button
                const uploadBtn = document.createElement('button')
                const fileInput = document.createElement('input')
                fileInput.type = 'file'
                fileInput.accept = 'image/png,image/jpeg,image/webp'
                fileInput.multiple = true
                fileInput.style.display = 'none'
                uploadBtn.onclick = () => fileInput.click()
                
                // Thumbnail grid (3 columns)
                const grid = document.createElement('div')
                grid.style.cssText = `display:grid; grid-template-columns:repeat(3,1fr); gap:3px;`
                
                // When file is selected:
                fileInput.onchange = async () => {
                    for (const file of filesToUpload) {
                        // 1. Pre-check size
                        const bitmap = await createImageBitmap(file)
                        if (bitmap.width > 4096 || bitmap.height > 4096) continue
                        bitmap.close()
                        
                        // 2. Generate thumbnail (FileReader → data URI)
                        const reader = new FileReader()
                        reader.onload = (e) => node._refImagePreviews.push(e.target.result)
                        reader.readAsDataURL(file)
                        
                        // 3. Upload to ComfyUI
                        const formData = new FormData()
                        formData.append('image', file)
                        formData.append('type', 'input')
                        const resp = await fetch('/upload/image', { method: 'POST', body: formData })
                        const result = await resp.json()
                        node._refImageFiles.push({
                            filename: result.filename || result.name,
                            subfolder: result.subfolder || '',
                            type: 'input',
                        })
                    }
                    // 4. Sync to hidden widget (persist in workflow JSON)
                    node._syncRefListWidget()
                    // 5. Redraw grid
                    redrawGrid()
                }
                
                // Return widget object
                const widget = {
                    type: 'REF_IMAGE_UPLOAD',
                    name: inputName,
                    element: container,
                    computeSize: function(width) {
                        const rows = Math.max(1, Math.ceil(count / 3))
                        return [width || 260, rows * 90 + 30]
                    },
                    serializeValue: function() {
                        return JSON.stringify(node._refImageFiles || [])
                    },
                }
                node.addCustomWidget(widget)
                return widget
            }
        }
    }
})
```

### Thumbnail Grid Features

Each thumbnail card in the grid has:

1. **Full image fill** — `object-fit:cover` on the img element
2. **左上角编号** — Blue badge with number (1, 2, 3...)
3. **右上角删除按钮** — Red ×, hidden by default, appears on hover
4. **Hover effects** — Border highlight on mouseenter

### ComfyUI Upload API

```
POST /upload/image
Content-Type: multipart/form-data

Fields:
  image: <file>       (required)
  type: "input"        (or "temp", "output")
  subfolder: ""        (optional)
  overwrite: "false"   (optional)

Response:
  { "name": "<filename>", "subfolder": "", "type": "input" }
```

The uploaded file goes to `ComfyUI/input/<filename>`. The `folder_paths.get_annotated_filepath(f"{filename} [input]")` Python call resolves it correctly.

### Workflow Persistence

When saving/loading workflows:

1. `serializeValue()` returns JSON string: `[{"filename":"img1.png","subfolder":"","type":"input"}, ...]`
2. On load (`loadedGraphNode` / `onNodeCreated`), read the widget value back
3. Load existing images' previews via `api.apiURL('/view?filename=...')`
4. Redraw the grid

**Key rule:** Only filenames (strings) go into the workflow JSON, NOT base64 data URIs. The thumbnails are reconstructed on load from the actual files.

### Output Ports Design

For reference image output from the node, add a 5th IMAGE port:

```python
RETURN_TYPES = ("STRING", "STRING", "STRING", "STRING", "IMAGE",)
RETURN_NAMES = ("提示词", "模式输出", "负面提示词", "元数据JSON", "回调图片",)
```

The 5th port (`回调图片`) passes through the first reference image tensor. Optional — returns `None` when no reference image is loaded.

### Design Rule: Why NOT 9 IMAGE Ports

| Approach | Pros | Cons |
|----------|------|------|
| 9 IMAGE ports | Standard ComfyUI pattern | Extremely bloated UI (9 visible ports), needs 9 external LoadImage nodes connected, user must manage 9 separate files |
| Single IMAGE port + batch | Cleaner, single port | User must pre-batch images externally, no control over which image is which |
| Custom DOM upload widget | **Native file picker**, inline preview, delete capability, persists in workflow, zero external nodes needed | Requires JS extension, more complex implementation |
| Save-to-temp + /view API | Works with existing IMAGE ports | Requires external LoadImage connections, doesn't solve the "too many ports" problem |

**Conclusion:** Custom DOM widget is the right approach when the user wants "Upload image like LoadImage but support multiple selection".

### Pitfalls

- **DO NOT use 9 separate IMAGE input ports** — user will rightfully complain
- **DO NOT use base64 encoding for thumbnails in JSON** — workflow files become huge and slow to load
- **DO NOT pre-create Image() inside onDrawForeground** — async loading + stale ctx = invisible thumbnails
- **DO NOT forget to reset `fileInput.value = ''` after upload** — otherwise selecting the same file doesn't trigger `onchange`
- **DO check image dimensions before uploading** via `createImageBitmap()` — the `/upload/image` endpoint accepts the file but doesn't check size
- **Hidden widget must use `computeSize = () => [0, -4]`** — ComfyUI's layout engine will give it zero space
- **Always call `app.graph.setDirtyCanvas(true)` after updating the grid** — otherwise the node won't resize
