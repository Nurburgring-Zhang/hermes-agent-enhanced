---
name: infinite-canvas-engine
description: >-
  无限画布引擎：AI生成项目的画布式创作工作台，支持定位生图/区域编辑/Outpaint扩展/短剧生成/绘本生成。
  覆盖后端引擎 + REST API路由 + 前端编辑器组件 + 统一参数面板的完整集成。
version: 1.0.0
author: Hermes Agent
metadata:
  hermes:
    tags: [canvas-editor, image-generation, video-generation, frontend-react, backend-fastapi, layer-management]
    related_skills: [unified-params-layer, deep-code-architecture-analysis]
---

# 无限画布引擎 (Infinite Canvas Engine)

## 概述

无限画布引擎为AI生成项目提供一个**画布式创作工作台**，用户可以在大画布上定位生成图像、编辑区域、向任意方向扩展画布、以及自动生成多场景短剧和多页绘本。

## 架构

```
┌─────────────────────────────────────────────────┐
│  CanvasStudio Page (React)                      │
│  ├── CanvasEditor (画布区 + 工具栏 + 图层)      │
│  ├── UnifiedParamsPanel (72参数右面板)           │
│  └── 3个模式: 画布/短剧/绘本                    │
└──────────────┬──────────────────────────────────┘
               │ HTTP (fetch)
┌──────────────▼──────────────────────────────────┐
│  API Routes (/api/canvas/*)                     │
│  create / gen-image / edit / outpaint / drama   │
│  picture-book / export / undo / list            │
└──────────────┬──────────────────────────────────┘
               │
┌──────────────▼──────────────────────────────────┐
│  InfiniteCanvasEngine (Python)                  │
│  CanvasState (图层栈 + undo/redo history)       │
│  _generate_canvas_tile() — 瓦片生成(可替换)     │
│  _blend_tile() — 边缘羽化混合                   │
│  _split_story_into_scenes() — 故事拆分          │
└─────────────────────────────────────────────────┘
```

## 触发条件

- 用户要求实现"无限画布"、"画布工作室"、"画布编辑"
- 需要定位在画布上生成/编辑图像
- 需要自动生成短剧/绘本（连贯故事→多场景/多页）
- 项目已有AI生成能力，需要画布式交互界面

## 核心设计

### 1. CanvasState (图层模型)

画布状态是图层栈 + undo/redo历史：

```python
@dataclass
class CanvasState:
    canvas_width: int = 2048
    canvas_height: int = 2048
    layers: List[Dict]  # {id, name, image(base64), visible, opacity, x, y, w, h, blend_mode}
    active_layer: int
    history: List[snapshots]  # 最多50步
    history_index: int
```

每个图层存储 base64 编码的图像数据。导出时按 x/y 坐标叠合成完整画布。

### 2. Canvas Operations

#### gen_image_on_canvas()
在画布指定位置(x,y)生成指定大小(w,h)的图像。
1. 取周围context_images作为风格参考
2. 调用底层生成引擎产生瓦片
3. 对瓦片边缘做alpha渐变混合（seam_blend）
4. 作为新图层添加到栈

#### edit_canvas_region()
提取区域当前内容作为mask上下文，重新生成该区域，淡入淡出混合。

#### outpaint_canvas()
向 left/right/up/down/all 方向扩展画布尺寸，生成扩展区域内容并与原画布边缘混合。

#### generate_short_drama()
将故事拆分为N个场景，在画布上按grid_cols/grid_rows排列，每个场景一个瓦片。

#### generate_picture_book()
将故事拆分为N页，垂直排列在画布上，每页占一个水平条。

### 3. 故事拆分策略

```python
# 3级级联拆分
1. 标点拆分（中英文句号/逗号/分号/感叹号/问号）
2. 单词拆分（按空格等分单词数）
3. 字符等分（每段至少15字符）

# 最终确保 len(scenes) == scene_count，每段描述唯一
```

如果拆分后句子数仍然不够，按字符数等分。每段至少15字符，否则自动减少场景数。

### 4. Seam Blending

```
feather = min(overlap, min(w, h) // 4)
mask = Image.new("L", (w, h), 255)
for i in range(feather):
    alpha = int(255 * (i / feather))
    # 在4个边缘上渐变
    draw.rectangle([i, 0, i+1, h], fill=alpha)  # 左侧
    draw.rectangle([w-i-1, 0, w-i, h], fill=alpha)  # 右侧
    draw.rectangle([0, i, w, i+1], fill=alpha)  # 上侧
    draw.rectangle([0, h-i-1, w, h-i], fill=alpha)  # 下侧
```

## 前端组件

### CanvasEditor (src/renderer/components/CanvasEditor.tsx)
- **CanvasToolbar**: 选择/平移/生图/编辑/放大/缩小/网格
- **CanvasArea**: 拖拽缩放渲染区，选区交互（生图工具=框选区域，编辑工具=框选编辑）
- **LayerPanel**: 图层列表（缩略图+可见性+透明度滑杆）

### UnifiedParamsPanel (src/renderer/components/UnifiedParamsPanel.tsx)
12个可折叠分区，72+参数控件：
- 生成类型/Provider/Prompt/图像参数/LoRA/ControlNet/编辑/放大/滤镜色彩/视频/3D
- 滑块字段、选择字段、输入字段、复选框 4种控件模式

### CanvasStudio (src/renderer/pages/CanvasStudio.tsx)
- 集成编辑器+参数面板
- 3个模式tab：画布（交互编辑）/ 短剧（文本→多场景）/ 绘本（文本→多页）
- 定时刷新（3s轮询canvas state）
- API调用层将所有参数映射到后端端点

## 路由集成

```typescript
// App.tsx
import CanvasStudio from './pages/CanvasStudio';
<Route path="/canvas" element={<CanvasStudio />} />

// NewLayout.tsx 侧边导航
{ path: '/canvas', label: '画布工作室', icon: LayoutDashboard, category: 'tools' }
```

## 陷阱

### 🕳️ 陷阱1: 故事拆分对英文不友好
`re.split(r'[，。、；;\n!！?？]', text)` 对英文句子无效（没有句号分隔符）。
**对策：** 先按标点分隔，不够再按空格分单词，再不够按字符等分。三级级联确保中英文都工作。

### 🕳️ 陷阱2: 画面base64数据过大
图层base64数据可能很大（全尺寸PNG几十MB）。
**对策：** 生产环境中应使用 UUID + 文件系统存储，而不是base64存内存。当前实现用base64做快速原型可行。

### 🕳️ 陷阱3: 生成时间不可控
`_generate_canvas_tile` 当前返回模拟数据，实际生图可能需要10-30秒。
**对策：** 生产环境应使用异步任务队列，前端轮询生成结果。

### 🕳️ 陷阱4: Canvas坐标系统不一致
前端拖拽缩放后的坐标需要转换回画布原生坐标。
**对策：** `scale = zoom`，`nativeX = (mouseX - offsetX) / zoom`。

### 🕳️ 陷阱5: Pydantic required字段阻塞可选body
`CanvasGenRequest` 中 `prompt: str`（无默认值）导致短剧/绘本请求如果只传 `story_prompt` 而不传 `prompt` 会返回 422。
**对策：** `prompt: str = ""`，路由中用 `request.story_prompt or request.prompt` 处理两种输入。

## 前端参数面板模式

### UnifiedParamsPanel 结构
每个参数分区是一个可折叠的 `Section` 组件：
```tsx
<Section title="图像参数" icon={Image} defaultOpen={true}>
  <SliderField label="宽度" value={...} min={256} max={2048} step={64} onChange={...}/>
  <SelectField label="采样器" value={...} options={SAMPLERS} onChange={...}/>
  <InputField label="种子" value={...} onChange={...}/>
  <label className="flex items-center gap-2 text-xs text-gray-400">
    <input type="checkbox" checked={...} onChange={...} className="accent-primary-500"/>
    选项名
  </label>
</Section>
```
12个标准分区：生成类型/Provider/Prompt/图像参数/编辑/LoRA/ControlNet/放大/滤镜色彩/视频/3D. 所有参数通过 `UnifiedParams` 数据类管理。

### Provider一致性检查
前端 `PROVIDERS` 常量必须与后端 `get_unified_service()` 中注册的 Provider 保持同步。不同步时，用户选择的Provider在后台不存在会导致调用失败。
**检查时机：** 添加新Provider后立即更新前端列表。检查方法：

```bash
# 后端注册的provider列表（从 unified_generation_service.py 提取）
grep "provider=" unified_generation_service.py | grep -o '"[^"]*"' | sort -u

# 前端列表（从 UnifiedParamsPanel.tsx 提取）
grep "value: '" UnifiedParamsPanel.tsx | grep -o "'[^']*'" | sort -u
```

交集应为前端列表 == 后端列表的超集（前端可以包含预留项）。

## 参考文件

- `references/nanobot-factory-phase-de-audit-20260607.md` — 实现细节和bug修复记录
- `unified-params-layer/references/nanobot-factory-params-reference.md` — 统一参数模型对照
