---
name: comfyui-custom-node
description: >-
  ComfyUI自定义节点开发：从节点类定义、INPUT_TYPES、OUTPUT_NODE机制，
  到前端JS扩展（addCustomWidget/addDOMWidget/onDrawForeground）、
  参考图上传、websocket推送等全链路开发。
version: 1.5.0
author: Hermes Agent
tags:
  - comfyui
  - custom-node
  - widget
  - javascript
  - dom-widget
  - thumbnail-preview
  - content-density
  - system-prompt
  - template-engineering
  - industry-standard
  - prompt-engineering
triggers:
  - "自定义节点"
  - "ComfyUI节点"
  - "custom_nodes"
  - "addDOMWidget"
  - "addCustomWidget"
  - "JS扩展"
  - "节点开发"
  - "PromptLibraryNode"
  - "参考图上传"
  - "内容密度"
  - "模板约束"
  - "提示词库节点"
  - "模式输出端口"
  - "变化标注"
  - "绘本规则"
  - "儿童绘本提示词生图规则"
  - "时空锚定"
  - "场景切换规则"
  - "22种模板"
  - "总纲格式"
  - "角色物品设定"
  - "模板独立性"
  - "变化规则"
  - "单起一行"
  - "叙事功能简写"
  - "场景切换时在分镜内"
---

# ComfyUI Custom Node Development

**Class-level umbrella** for developing ComfyUI custom nodes: Python node definition, frontend JavaScript extensions, custom widgets, image upload, and preview rendering.

## 节点架构基础

## 触发条件
- 用户提及此功能相关关键词时
- 遇到此领域的标准问题时
- 需要执行该领域的标准操作时


### 最小节点定义

```python
class MyNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "输入名": ("STRING", {"default": ""}),
            },
            "optional": {
                "可选输入": ("INT", {"default": 1, "min": 1, "max": 10, "step": 1}),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("输出名",)
    FUNCTION = "my_function"
    CATEGORY = "分类名"
    OUTPUT_NODE = True  # 如果是输出节点

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return _time.time()  # 强制每次执行
```

### 模块级变量（ComfyUI自动识别）

```python
NODE_CLASS_MAPPINGS = {"MyNode": MyNode}
NODE_DISPLAY_NAME_MAPPINGS = {"MyNode": "中文名"}
WEB_DIRECTORY = "./web"  # JS扩展目录
```

### 输出节点多值返回

```python
# 固定元组
return (output1, output2, ...)

# OUTPUT_NODE可通过ui回传额外数据到前端
return {"ui": {"ref_images": [...]}, "result": (output1, output2)}
```

## 输入类型参考

| ComfyUI类型 | Python类型 | 示例 |
|------------|-----------|------|
| STRING | str | `("STRING", {"default": ""})` |
| INT | int | `("INT", {"default": 1, "min": 0, "max": 100})` |
| FLOAT | float | `("FLOAT", {"default": 0.8, "min": 0.0, "max": 1.0})` |
| BOOLEAN | bool | `("BOOLEAN", {"default": False})` |
| 下拉列表 | str | `(["选项A", "选项B"], {"default": "选项A"})` |
| IMAGE | torch.Tensor | `("IMAGE",)` — 输入端口 |
| MASK | torch.Tensor | `("MASK",)` |

STRING特殊选项：
- `"multiline": True` — 大输入框（多行文本）
- `"multiline": False` — 单行输入

IMAGE类型特殊选项：
- `{"image_upload": True}` — 显示上传按钮（单文件）
- 不带option — 作为输入端口，接收其他节点的IMAGE输出

## image_upload机制（单图上传）

```python
# Python端：从input目录读取
input_dir = folder_paths.get_input_directory()
files = [f for f in os.listdir(input_dir) if os.path.isfile(...)]
return {"required": {"image": (sorted(files), {"image_upload": True})}}
```

加载时：
```python
image_path = folder_paths.get_annotated_filepath(image)
img = Image.open(image_path).convert("RGB")
img_np = np.array(img).astype(np.float32) / 255.0
img_tensor = torch.from_numpy(img_np)[None,]  # (1, H, W, C)
```

## 多文件批量上传（自定义DOM widget方案）

**不要用9个独立的IMAGE输入端口！** 用隐藏的STRING widget存储文件列表 + 前端JS自定义DOM widget实现上传按钮和缩略图预览。

### Python端

```python
# INPUT_TYPES中定义隐藏存储widget
"参考图列表": ("STRING", {"default": "[]", "multiline": True}),
```

解析和加载：
```python
def _parse_ref_image_list(self, ref_list_str):
    items = json.loads(ref_list_str or "[]")
    return [item for item in items if isinstance(item, dict) and "filename" in item][:9]

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

# 输出时concat成batch
callback_image = torch.cat(tensors, dim=0) if tensors else None  # (N, H, W, C)
```

### 前端JS扩展

核心实现方式（`addDOMWidget`）：

```javascript
// 1. 隐藏原始STRING widget
const origWidget = this.widgets.find(w => w.name === '参考图列表')
origWidget.computeSize = () => [0, -4]
origWidget.hidden = true

// 2. 创建DOM容器
const container = document.createElement('div')
container.style.cssText = 'width:100%;display:flex;flex-direction:column;gap:4px;'

// 3. 创建上传按钮+file input
const fileInput = document.createElement('input')
fileInput.type = 'file'
fileInput.accept = 'image/png,image/jpeg,image/webp'
fileInput.multiple = true
fileInput.style.display = 'none'
const uploadBtn = document.createElement('button')
uploadBtn.textContent = '+ 选择文件上传'
uploadBtn.onclick = () => fileInput.click()

// 4. 文件上传处理
fileInput.onchange = async () => {
    for (const file of files) {
        const bitmap = await createImageBitmap(file)
        if (bitmap.width > 4096 || bitmap.height > 4096) continue
        const reader = new FileReader()
        reader.readAsDataURL(file)
        await new Promise(r => { reader.onload = r })
        const fd = new FormData()
        fd.append('image', file); fd.append('type', 'input')
        const resp = await fetch('/upload/image', { method: 'POST', body: fd })
        const result = await resp.json()
        node._refImageFiles.push({
            filename: result.filename || result.name,
            subfolder: result.subfolder || '',
            type: 'input',
        })
    }
}

// 5. 同步到隐藏widget
const syncWidget = () => {
    origWidget.value = JSON.stringify(node._refImageFiles)
    origWidget.callback?.(origWidget.value)
}

// 6. 注册DOM widget
const domWidget = this.addDOMWidget('upload_widget', 'customwidget', container)
domWidget.computeSize = (width) => {
    const count = this._refImagePreviews?.length || 0
    if (count === 0) return [width || 260, 50]
    return [width || 260, 50 + Math.ceil(count / 3) * 86]
}
```

### 缩略图网格自适应（grid方案）

用 `grid-template-columns:repeat(auto-fill,minmax(70px,1fr))` 替代 `flex-wrap`：

```javascript
grid.style.cssText = 'display:grid;grid-template-columns:repeat(auto-fill,minmax(70px,1fr));gap:6px;width:100%;box-sizing:border-box;'
```

- 节点拉宽时每行自动增加卡片数
- 卡片用 `aspect-ratio:1/1` 保持正方形
- 不需要手动计算卡片大小

### addDOMWidget 越界修复

```javascript
// 1. 容器加 max-width:100%
container.style.cssText = '...;max-width:100%;'

// 2. 节点过窄时撑大
if (this.size && this.size[0] < 280) {
    this.setSize([280, this.size[1]])
}

// 3. widget高度通过 computeSize 控制
domWidget.computeSize = (width) => {
    const count = this._refImagePreviews?.length || 0
    if (count === 0) return [width || 260, 50]
    return [width || 260, 50 + Math.ceil(count / 3) * 86]
}
```

**不要做的事情：**
- ❌ 在 redrawGrid 里调 this.setSize — 导致"删一张图节点变高一节"
- ❌ 用固定 px 宽度的卡片 — 不随节点缩放自适应
- ❌ 在 computeSize 里调 querySelectorAll 改卡片大小 — grid自动处理

## 控件排列顺序

ComfyUI节点控件的排列顺序由INPUT_TYPES字典中的定义顺序决定：
- **required**区全部显示在**optional**区上方
- 要跨区段穿插控件的唯一方式：把想显示在上方的控件全部放到required区

## 系统提示词的内容密度约束（格林主人核心偏好）

**AI输出的内容不能太干也不能过度堆细节。** 所有模板必须遵循以下约束。

### 核心规则

```
总纲设定（每个板块3-5句话）：
  - 角色：精确描写外貌、体型、服装、标志特征，禁止数值参数和微观生物学细节
  - 场景：充分描述空间环境、时间光线、氛围特征，禁止写尺寸方位数量
  - 画质：生动描述画面质感、色彩倾向、光线风格
  - 声音：描述环境声音氛围

画面/镜头描述（每个3-6句话，根据情节调节）：
  - 用有画面感的叙事语言，充分描写场景、动作和氛围
  - ❌ 禁止写任何数值参数（毫米/厘米/dB/色值/百分比等）
  - ❌ 禁止写器官名称、肌肉名称、生物学细节、微观结构
  - ✅ 用正常叙事语言，让内容有血有肉
```

### 全局强制约束配置（V19 final）

注意：V19 第二轮重构删除了 `_build_global_context`（改为每个模式独立的约束）。**不要再创建全局约束方法**——每个模式的约束写在它自己的 format_templates 或 system prompt 中。

正确做法：
```python
# 每个模式各自的 format_template 字典
format_templates = {
    "电影分镜": "# 输出格式（电影分镜专用）\n每个镜头...",
    "广告故事板": "# 输出格式（广告故事板专用）\n每个镜头...",
    # ...9个模式各不同
}
```

### 系统提示词工程策略

**追加在system prompt末尾的约束会覆盖前面的啰嗦指令。** 把强制约束放在 `_build_global_context` 中（在所有模式末尾追加调用），它覆盖前面所有冗长描述。

### 诱导细节的关键词黑名单

**检查所有 `_build_*` 方法，确保没有残留：**
- ❌ "极致细腻""800字以上""600字以上""200字以上"
- ❌ "逐帧动线序列""空间锚点法""色相饱和度明度参数"
- ❌ "肢体关节角度""肌群状态""空气质感"
- ❌ "可观测的身体信号""至少X个""毛细血管""毛密度"

9. **格林主人强制格式约束（2026-05-31固化 v3）**

所有system prompt模板中的变化描述和总纲输出必须遵守：

1. **禁止过度描述** — 变化标注只说「场景/角色/服装/道具变化时写明前后对比」，不写长解释
2. **正常描述与变化描述之间不留空行** — AI输出中变化描述紧接在画面描述之后，不单独分段
3. **不要变化追踪标签，不要罗列所有维度** — 不在输出格式中写五维标签。只在真正变化的维度写对应描述，无变化不写
4. **不要**、-等markdown符号** — 模板中用纯文本，不用粗体和列表符号。去符号用Python `str.replace('"- **', '"')` 和 `str.replace('**', '')` 批量处理
5. **总纲不含硬编码角色物品和场景设定**：
   - 总纲标题去掉`# `前缀，直接以`【xxx总纲】`开头
   - 总纲header中不写【角色物品设定】和【场景设定】——这些由AI在正文输出中根据用户输入自行生成
   - 总纲只包含风格/色调/画风等元信息，后接氛围/声音/方向。不直接拼接用户输入的角色描述和环境描述
   - 在system prompt开头的任务描述中加入「注意：在故事板/绘本/剧本正文开头，先输出【角色设定】和【环境设定】」
6. **用户输入必须传透** — 检查每个模式的`_build_*_user_prompt`函数：绘本、短剧、儿童模式的user prompt需要包含角色描述和场景描述参数。容易遗漏：`_build_picture_book_user_prompt`原本只有`(topic, pages, style, color_tone, text_amount, age_group)`，需要加`character_desc`和`env_desc`
7. **总纲和正文之间无分隔线** — 4个总纲header后紧跟AI生成的正文，不用`---`分隔。修改位置：`_process_storyboard_mode`/`_process_picture_book_mode`/`_process_short_drama_mode`/`_process_child_mode`中的`return f"{header}\\n---\\n\\n{ai_result}"`改为`return f"{header}\\n\\n{ai_result}"`
8. **场景/角色变化时在分镜内单起一行** — 不在总纲中写变化信息，而是在变化发生的分镜/页面/镜头内单起一行写：
   ```
   分镜场景：场景改变时增加，描述新环境特征
   角色特征：角色改变时增加，描述变化后的角色特征
   ```
   两者都变化时同时增加。不变化则不写这两行。所有22种模板都必须有这个结构。
9. **叙事功能仅在必要时输出** — 不是每个镜头/步骤/页面都必须有叙事功能。只在需要说明镜头在故事中的作用时才输出，一句话简写。
10. **总纲格式统一编号结构（2026-06-01固化 v4）** — 所有模板总纲使用以下编号结构，禁止空行：
    ```
    【xxx总纲】
    1、整体视觉风格：
        ...
    2、角色物品设定：
        ...
    3、道具/武器：
        ...
    4、场景设定：
        ...
    5、氛围与画质标准：
        ...
    6、声音设定：
        ...
    7、核心叙事设定：
        ...
    ```
    - 使用 `N、` 编号前缀（`1、` `2、` 等），缩进4个空格
    - 角色描述在「角色物品设定」section内，不单独输出【角色设定】引导
    - 道具/武器统一设为「待补充」，AI在内容中自行扩展
    - 旧格式（分段section名且不编号）已废弃，不要再使用
10. **场景切换规则必须按模板类型定制** — 不能所有模板用同一套描述。每个format_template中的创作原则末尾都必须追加自己的变化规则。具体规则见`references/promptlibrary-scene-switch-rules-per-mode.md`
11. **分镜场景/角色特征仅在变化时输出** — 不在每个分镜都写场景/角色字段。场景改变时才在分镜内增加「分镜场景：」一行，角色特征改变时才增加「角色特征：」一行，两者都变时同时增加。叙事功能同理——仅在需要说明镜头作用时才输出，不是每个镜头必须有。
12. **22种模板每种必须独立** — 故事板9种 + 绘本1种 + 短剧1种 + 儿童4种 + 专业设计7种=22种。每种有自己的变化规则和输出格式，不能归类后共享。专业设计7种虽然没有画面分镜，但也要在输出格式末尾追加变化规则（如「产品形态/场景环境变化时在对应图描述中单起一行写新信息」）
13. **行业标准升级** — format_templates中的9种故事板输出格式必须引入该领域核心法则（详见`references/promptlibrary-industry-standard-upgrades.md`）
14. **模板独立性质量检测** — 每次修改后运行审计：4个总纲无#前缀/无硬编码、每模板独立变化规则、无**残留、语法通过

这些约束对故事板/绘本/短剧/儿童4种模式全部生效。写模板时直接嵌入约束。

### 正确的描述示例

**太干（1句话无细节）：**
野猪鼻子拱泥土。

**适中（3-5句话，有氛围无参数）：**
野猪鼻子拱开湿润的泥土，鼻尖沾满黑泥。短小的獠牙蹭过草叶，带起几滴露珠。

**太细节（有数值参数+微观结构）：**
野猪鼻尖以每秒3次的频率翕动，鼻孔微观结构可见。

## Pitfalls

1. **addDOMWidget可能渲染到节点边界之外** — 节点宽度不足时DOM容器被推到可视区域外。加 `max-width:100%` + 节点最小宽度
2. **image_upload不支持多选** — ComfyUI原生只支持单文件上传。多选必须用自定义JS
3. **required/optional顺序不可混排** — all required before all optional
4. **IMAGE端口只能输出batch tensor** — 形状(N, H, W, C)。要独立输出需要多端口
5. **onExecuted接收ui数据** — 从message拿到Python端返回的额外数据
6. **工作流恢复时widget值自动还原** — 在loadedGraphNode或onNodeCreated中从widget值restore
7. **在redrawGrid里调this.setSize导致节点越删越高** — 用computeSize控制widget高度，不动节点大小
8. **addDOMWidget不自动参与节点高度计算** — **正确做法**：重写节点的 `this.computeSize` 方法，手动遍历 `this.widgets` 累加所有widget（含DOM widget）的高度。**千万不要**在redrawGrid里调setSize——节点会越删越高。也**不要**硬编码偏移量（widget列表变化时失效）。正确方案见 `references/addDOMWidget-height-fix.md`
9. **下拉列表的默认值决定节点首次加载时的显示** — 如果"画面风格"是自由字符串且默认"电影感"，用户看不到其他选项。✅ 用预设下拉（24种风格）让用户立刻看到所有选择
10. **不要所有模式共用同一套输出格式** — 9个故事板模式需要9套不同的格式，不能统一用"景别+画面+运镜+转场+时长"。每个模式的字段名、维度、输出结构都必须不同。参 `references/PromptLibraryNode-V19-content-density.md`
12. **addDOMWidget高度越界修复——唯一正确方法（2026-05-27验证通过）：**
    ```javascript
    // 核心：只重写节点的computeSize，不调setSize
    // addDOMWidget创建的widget在this.widgets里，但LiteGraph不自动汇总它的高度

    const domWidget = this.addDOMWidget('name', 'type', container, options)

    // 1) domWidget的computeSize——告诉引擎这个widget自身占多高
    domWidget.computeSize = (width) => [width || 260, calcHeight()]

    // 2) 重写节点的computeSize——手动累加所有widget的高度
    //    这是唯一正确的方法。不要在这里调setSize。
    this.computeSize = function(nodeWidth) {
        const w = nodeWidth || this.size?.[0] || 280
        let totalH = 0
        if (this.widgets) {
            for (const wgt of this.widgets) {
                if (wgt.hidden) continue  // 跳过隐藏widget
                if (wgt.computeSize) {
                    const sz = wgt.computeSize(w)
                    totalH += (sz?.[1] || 30)
                } else {
                    totalH += 30
                }
            }
        }
        // 多加50-60px保底，确保DOM widget不超出下边框
        return [Math.max(w, 280), totalH + 50 + 60]
    }
    ```
    **绝对不要做这些（每个都被用户骂过）：**
    - ❌ 在redrawGrid里调this.setSize([w, h]) — 节点会越删越高
    - ❌ 在computeSize里调this.setSize — 死循环
    - ❌ 硬编码偏移量数字（如560+30）— widget列表变化后失效
    - ❌ 用this.setSize([w, h+0.1]) hack — 不稳定
    - ❌ 找this.el.parentNode.appendChild — this.el在ComfyUI中不存在
    - ❌ 重写onResize来修正高度 — computeSize正确的话onResize不需要动
    - ❌ 用requestAnimationFrame + setSize组合 — 多次尝试都不起作用
    - ✅ 唯一正确做法：computeSize遍历所有widget累加高度，末尾加保底值
13. **user prompt遗漏角色/场景传递** — 修改`_build_picture_book_user_prompt`或`_build_short_drama_user_prompt`等函数时，必须同步更新调用处的函数签名。容易遗漏的点：绘本和短剧的user prompt原本没有角色描述和环境描述参数，需要手动添加

## 格林主人偏好（ComfyUI开发类）

### 节点格式
- ❌ 9个独立IMAGE输入端口的方案
- ❌ 在computeSize里用setSize撑大节点
- ✅ 用addDOMWidget + computeSize返回自适应高度
- ✅ 用hidden widget存储数据（避免工作流序列化丢失）
- ✅ 上传前前端预检尺寸（createImageBitmap），>4096的直接跳过

### 总纲格式（2026-06-01 最终版）
- ✅ 总纲输出以【xxx总纲】开头，使用1~7编号结构，缩进4空格
- ✅ 角色物品设定在总纲section 2内，多角色每角色一行带缩进
- ✅ 角色物品设定**末尾不加句号**（避免多角色时句号单独一行）
- ✅ 道具/武器统一在section 3输出「待补充」，AI在内容中自行扩展
- ✅ 场景设定**末尾不加句号**（用户输入可能自带句号导致双重句号）
- ✅ 总纲满7个编号section，无冗余空行
- ✅ 字段内容直接以4空格开始，不用 IND 变量拼接（避免多级缩进）

### 变化标注规则（2026-06-01 最终版）
- ✅ 有变化才输出，无变化时整个「变化标注：」段不出现
- ✅ 只写有变化的维度，不写无变化维度的占位文字
- ✅ 维度名称用中文文字（场景变化/角色变化/服装变化/道具变化/时间变化），不用emoji符号
- ✅ 有变化时格式：`变化标注：场景变化——从XX切换到XX；角色变化——XXX`
- ❌ 严禁输出：emoji维度标签（🔄👤👗📦☀️）、无变化写「无」、五维度逐项罗列

### 分镜场景/角色特征变化输出规则（2026-06-01 最终版）
- ✅ 分镜场景变化时输出完整场景描述（地点/时间/光线/环境/道具），2-4句
- ✅ 角色特征变化时输出完整角色描述（外貌/服装/表情/状态），2-3句
- ✅ 两者都变化时各行一行
- ❌ 严禁只输出简短地名（如"中午·小兔子家厨房"）而不带详细场景描述
- ✅ `分镜场景`和`角色特征`两行**仅在变化时输出**，无变化时这两行（含标题）整行不出现
- ✅ 其他所有维度标题（时间·空间锚定、场景描述、画面、文字、旁白等）正常输出

### 总纲缩进禁令（2026-06-01 固化）
- ❌ 内容前不允许任何缩进空格。字段内容直接顶头写
- 示例正确格式：
```
2、角色物品设定：
一只毛茸茸的小兔子
一只圆滚滚的小野猪
3、道具/武器：
待补充。
```
- ❌ 不要用 IND 变量拼接缩进
- ❌ 不要 `.replace("\\n", "\\n    ")` 加缩进
- ✅ 直接输出角色描述原文，不带额外空格

### 故事感总纲（2026-06-01 新增）
所有叙事模板的system prompt最前面必须嵌入故事感总纲：
- 核心叙事结构：开场钩子（3秒内好奇）→情感建置→冲突升级（3波难度递增阻碍）→转折点（最低谷到新希望）→高潮（情感释放）→情感闭环（开场问题=结尾答案）
- 情感曲线：波动上升，不是直线
- 儿童故事：愿望→障碍→坚持→突破→分享五段式
- 钩子设计：开场反直觉或带疑问，每3个节点小反转
- 价值观通过故事自然展现不说教

### 儿童绘本格式（参考鲸鱼科普示例）
- 每页格式：`第X页：页面标题` + `画面：` + `文字：`
- 不输出时间·空间锚定前缀
- 分镜场景/角色特征仅在变化时作为额外行出现
- 参考示例文件：`D:\试生产 剧本.txt`中的儿童绘本部分

### 符号禁令（2026-06-01 固化）
- ❌ 所有system prompt中不得出现：`# `开头的标题、`## `、`**`、`- `开头的列表、`🔴`、emoji符号
- ❌ `「第X幕：标题」`中的`「」`符号也要去掉，改为纯文字
- ✅ 段标题用纯文字（"角色设定"而非"# 角色设定"）
- ✅ 创作原则列表项去掉`- `前缀（"节奏变化"而非"- 节奏变化"）
- ✅ 每个system prompt末尾加指令："重要：输出中不要包含任何** - 等符号标记，不要用星号或横线装饰文字。直接输出纯文字。"

### 其他
- ✅ 变化描述只用纯文本
- ✅ user prompt必须包含角色描述和场景描述，确保AI有完整信息
- ✅ 角色描述多行时通过`.replace("\n", "\n    ")`确保每行带缩进

## 回滚方案
### 内容回退
1. 恢复到上一个版本的文件
2. 确认生成内容无退化
3. 必要时重启生成流程

### 恢复步骤
1. 从备份目录恢复原始文件
2. 验校内容完整性
3. 对比前后差异确认回退成功

### 手动全量检测命令
```
# 语法
python3 -m py_compile __init__.py

# 变化规则统计
python3 -c "open('__init__.py') as f: c=f.read(); print(f'变化规则: {c.count(\"变化规则\")}处 | ---: {c.count(chr(92)+\"n---\")}处 | **: {c.count(\"**\")}处 | #前缀: {c.count(\"\\\"# 【\")}处 | 单起一行: {c.count(\"单起一行写\")}处')"
```
