# PromptLibraryNode V19 实现参考

**日期**: 2026-05-27  
**格林主人 ComfyUI 自定义节点开发**

## 核心变更（V18→V19）

| 变更 | 旧方案 | 新方案 |
|------|--------|--------|
| 模式选择 | 6个独立开关+下拉 | 1个统一下拉（24种模式） |
| 输入区 | 分散控件 | 归纳为故事剧本/角色/环境3个大框（multiline） |
| 参考图 | 9个IMAGE输入端口 | 自定义DOM widget上传+缩略图预览 |
| 输出端口 | 6端口 | 5端口（提示词/模式输出/负面/元数据JSON/回调图片） |
| 新增模式 | 无 | 7种专业设计（电商/海报/品牌/PPT/逻辑关系图/三视图/爆炸拆解图/流水线图） |
| 系统提示词 | 诱导堆细节（"800字以上""极致细腻"） | 强制简洁（"2-5句话""禁止数值参数"） |

## 24种模式列表

```
["关闭", "电影分镜","广告故事板","动画故事板","漫画分镜","MV故事板",
 "教程步骤","短视频分镜","品牌故事板","剧情分镜",
 "绘本模式","短剧模式",
 "儿童视频格式一","儿童视频格式二","儿童微动视频/GIF","儿童绘本格式",
 "电商套图","海报设计","品牌设计","PPT设计",
 "逻辑关系图设计","三视图设计","爆炸拆解图设计","流水线图设计"]
```

## 控件排列顺序（Python代码从上到下）

```
required:
  文件夹路径 ~ 翻译方向（传统提示词库，最上方）
  API地址 ~ AI最大Token数（翻译功能下方）
  参考图列表（AI下方）← 隐藏STRING widget，JS DOM widget替代
  模式选择 ~ 运镜风格（参考图下方）

optional:
  镜头数量 ~ 背景类型（模式专属参数，最下方）
```

## 输出端口

```
RETURN_TYPES = ("STRING", "STRING", "STRING", "STRING", "IMAGE")
RETURN_NAMES = ("提示词", "模式输出", "负面提示词", "元数据JSON", "回调图片")
```

## 参考图实现方案（V19最终版）

### Python端

```python
# INPUT_TYPES中定义
"参考图列表": ("STRING", {"default": "[]", "multiline": True})

# 解析JSON文件列表
def _parse_ref_image_list(self, ref_list_str):
    items = json.loads(ref_list_str or "[]")
    return [item for item in items if isinstance(item, dict) and "filename" in item][:9]

# 加载为IMAGE tensor
def _load_ref_image_tensors(self, file_items):
    import folder_paths, numpy as np
    from PIL import Image
    tensors = []
    for item in file_items:
        img_path = folder_paths.get_annotated_filepath(f"{item['filename']} [input]")
        if not os.path.isfile(img_path):
            continue
        pil_img = Image.open(img_path).convert("RGB")
        if pil_img.width > 4096 or pil_img.height > 4096:
            continue
        img_np = np.array(pil_img).astype(np.float32) / 255.0
        tensors.append(torch.from_numpy(img_np)[None,])
    return tensors

# 输出时concat成batch tensor
callback_image = torch.cat(tensors, dim=0) if tensors else None  # (N, H, W, C)
```

### JS端（addDOMWidget方案）

```javascript
// 1. 隐藏原始STRING widget
const origWidget = this.widgets.find(w => w.name === '参考图列表')
origWidget.computeSize = () => [0, -4]
origWidget.hidden = true

// 2. 容器设置
const container = document.createElement('div')
container.style.cssText = 'width:100%;display:flex;flex-direction:column;gap:8px;padding:10px 8px;border:1px solid var(--border-color);border-radius:6px;background:var(--comfy-menu-bg);'

// 3. 上传按钮
const fileInput = document.createElement('input')
fileInput.type = 'file'; fileInput.accept = 'image/png,image/jpeg,image/webp'
fileInput.multiple = true; fileInput.style.display = 'none'

// 4. 网格（flex-wrap自动换行）
const grid = document.createElement('div')
grid.style.cssText = 'display:flex;flex-wrap:wrap;gap:4px;'

// 5. 卡片大小自适应节点宽度
const S = Math.max(50, Math.min(90, (nodeWidth - 40) / 3))

// 6. 同步到隐藏widget
const syncWidget = () => {
    origWidget.value = JSON.stringify(node._refImageFiles)
    origWidget.callback?.(origWidget.value)
}

// 7. 注册DOM widget
const domWidget = this.addDOMWidget('ref_image_upload', 'customwidget', container)
domWidget.computeSize = (width) => {
    const count = node._refImagePreviews?.length || 0
    if (count === 0) return [width || 260, 50]
    return [width || 260, 50 + Math.ceil(count / 3) * 86]
}

// 8. 确保节点宽度足够
if (this.size[0] < 280) this.setSize([280, this.size[1]])
```

### 工作流恢复

```javascript
// 从widget值恢复已上传的文件
const restore = () => {
    if (origWidget.value && origWidget.value !== '[]') {
        const files = JSON.parse(origWidget.value)
        node._refImageFiles = files
        node._refImagePreviews = files.map(f => {
            const p = new URLSearchParams({filename: f.filename, type: f.type || 'input', subfolder: f.subfolder || ''})
            p.append('preview', 'true')
            return api.apiURL('/view?' + p.toString())
        })
    }
}
```

## 系统提示词约束（所有模式通用）

参见 `SKILL.md` 中的"系统提示词的内容密度约束"章节。

## 关键文件

- `__init__.py` — 1456行，95KB（主节点）
- `web/PromptLibraryNode.js` — 202行（JS扩展）
- 备份：`__init__.py.v19.backup.*`
