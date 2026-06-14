# ComfyUI Custom Node: Reference Image Thumbnail Preview (via /view API)

## Two Approaches

### Approach A: base64 via `ui` (discarded — user rejected)
```python
def _encode_ref_images_for_frontend(self, ref_images):
    for img_tensor in ref_images[:9]:
        img = img_tensor.cpu()
        if img.dim() == 4: img = img[0]
        img_np = (img.numpy() * 255).astype(np.uint8)
        pil_img = Image.fromarray(img_np, 'RGB')
        buf = io.BytesIO()
        pil_img.thumbnail((160, 160), Image.LANCZOS)
        pil_img.save(buf, format='PNG', optimize=True)
        b64 = base64.b64encode(buf.getvalue()).decode('utf-8')
        data_uris.append(f"data:image/png;base64,{b64}")
    return {"ui": {"ref_images": data_uris}, "result": result_tuple}
```
**Problems:** bloated workflow JSON, no cache reuse, quality limits.

### Approach B: Save to temp dir + /view API (user preferred — USE THIS)
```python
import folder_paths

def _save_ref_images_temp(self, ref_images):
    temp_dir = folder_paths.get_temp_directory()
    os.makedirs(temp_dir, exist_ok=True)
    file_paths = []
    for img_tensor in ref_images[:9]:
        img = img_tensor.cpu()
        if img.dim() == 4: img = img[0]
        img_np = (img.numpy().clip(0, 1) * 255).astype(np.uint8)
        pil_img = Image.fromarray(img_np, 'RGB')
        pil_img.thumbnail((200, 200), Image.LANCZOS)
        filename = f"ref_thumb_{int(time.time()*1000)}_{i}.png"
        pil_img.save(os.path.join(temp_dir, filename), format='PNG', optimize=True)
        file_paths.append({"filename": filename, "subfolder": "", "type": "temp"})
    return file_paths
```

```javascript
// JS — load via /view API
PromptLibraryNodePro.prototype._loadRefImages = function () {
    const files = this._refImageFiles || [];
    this._refImagesLoaded = new Array(files.length).fill(null);
    files.forEach((file, idx) => {
        const img = new Image();
        img.onload = () => {
            this._refImagesLoaded[idx] = img;
            if (allLoaded) { this._adjustNodeSize(); app.graph.setDirtyCanvas(true); }
        };
        const params = new URLSearchParams({filename: file.filename, type: file.type||'temp', subfolder: file.subfolder||''});
        params.append('preview', 'true');
        img.src = api.apiURL(`/view?${params.toString()}`);
    });
};
```
**Advantages:** zero bloat, ComfyUI cache reuse, full quality.

## JS Extension Architecture

### File Structure
```
custom_nodes/YourNode/
├── __init__.py              # WEB_DIRECTORY = "./web" at module level
└── web/
    └── YourNode.js          # auto-loaded by ComfyUI
```

### Critical Rules
1. **NEVER `new Image()` inside draw loop** — preload in `onExecuted`.
2. **Preload pattern:** `onExecuted(message)` → save file list → `_loadRefImages()` → each Image.onload → `app.graph.setDirtyCanvas(true)` only after ALL loaded.
3. **Node resize:** `this.setSize([w, h])` once after preload. Never in draw loop.
4. **`WEB_DIRECTORY`** must be at module level (not inside class).
5. **Redraw:** `app.graph.setDirtyCanvas(true)` triggers next frame.
6. **RoundRect:** use `ctx.roundRect?.()` with optional chaining for browser compat.
7. **Background clip:** `ctx.save()` → `ctx.beginPath()` → `ctx.rect(x,y,w,h)` → `ctx.clip()` → `ctx.drawImage(...)` → `ctx.restore()` for square thumbnails.
8. **Number overlay:** Draw as filled rect + white text in upper-left corner of each thumbnail.
