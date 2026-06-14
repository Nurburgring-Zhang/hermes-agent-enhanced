---
name: garden-gpt-image-engineer
description: ConardLi garden-skills 图片生成工程师全面集成 — 面向GPT Image 2和OpenAI兼容图像API。18大类79个结构化Prompt模板，覆盖海报/UI Mockup/产品图/信息图/论文图/技术架构图/漫画/头像/分镜/品牌板。三模式运行：本地模式/宿主工具模式/顾问模式。
version: 1.1.0
author: Hermes Agent (from ConardLi garden-skills)
domain: creative
tags:
  - image-generation
  - gpt-image-2
  - prompt-templates
  - structured-prompt
  - poster-design
triggers:
  - "图片生成"
  - "GPT Image"
  - "生图"
  - "海报"
  - "产品图"
  - "信息图"
  - "架构图"
  - "漫画"
  - "分镜"
  - "头像"
  - "品牌板"
  - "绘图"
  - "图片编辑"
  - "UI Mockup"
  - "论文图"
---

# Garden GPT Image Engineer

## 核心理念

来自 ConardLi garden-skills 的 gpt-image-2 全面集成。

**问题**：一句Prompt"生成一张科技感海报"——这种方式能出图，但结果不稳定。
尺寸是多少？主体放在哪里？文字区域要不要留白？风格参考是什么？要不要分层？

**解法**：把图像任务拆成不同类别，提供结构化Prompt模板。好的图片Prompt同时描述：画面目标+主体与关系+构图+材质+光线+字体与文字限制+输出尺寸+后续编辑空间。

## 18大类79个结构化Prompt模板

### 生成类

| 类别 | 模板数 | 典型输出 |
|------|--------|---------|
| 海报 | 8 | 活动海报、产品海报、宣传海报 |
| UI Mockup | 6 | App界面、Web界面、Dashboard |
| 产品图 | 6 | 产品展示、生活方式、场景化 |
| 信息图 | 5 | 数据可视化、流程图、时间线 |
| 论文图 | 5 | 架构图、模型图、对比图 |
| 技术架构图 | 4 | 系统架构、网络拓扑、数据流 |
| 漫画 | 5 | 分镜漫画、条漫、四格 |
| 头像 | 4 | 写实头像、插画头像、品牌头像 |
| 分镜 | 4 | 故事板、previs调度 |
| 品牌板 | 4 | Mood Board、风格板、品牌色板 |
| 更多8类综合 | 28 | 封面/插画/图标/背景/纹理/模因/编辑/修复 |

## 三模式运行

```python
MODE_MAP = {
    "local":     "直接调生图API接口，出图并落盘（需要API Key）",
    "host_tool": "把整理好的Prompt交给当前Agent自带的图像工具（如CodeX环境）",
    "advisor":   "退化为Prompt顾问，把Prompt写到可执行水平（无图像工具时）"
}
```

## Prompt模板结构

每个结构化Prompt包含以下维度：

```yaml
- 画面目标: 完成什么任务（产品展示/概念表达/信息传达）
- 主体与关系: 主元素是谁/什么，与背景的关系
- 构图: 主体位置、视角、透视
- 材质与纹理: 视觉质感（金属/玻璃/纸质/数字）
- 光线与氛围: 光源方向、色彩基调、情绪
- 尺寸: 宽高比、分辨率
- 文字与排版: 字体风格、文字区域、可编辑空间
- 限制: 禁止出现的元素、风格偏移容忍度
```

## 工作流

### Step 1: 任务分类

判断图像任务属于18大类中的哪一类。

### Step 2: 模板匹配

从79个模板中选择最合适的模板。

### Step 3: 模板填充

```python
template = prompt_templates[category][template_name]
filled = template.fill({
    "subject": "xxx",
    "style": "xxx",
    "text": "xxx",
    "size": "xxx",
    ...
})
```

### Step 4: 环境检测

```python
# 1. 检查是否有本地生图API
# 2. 检查当前Agent环境（CodeX/Claude Code/Hermes）
# 3. 检查是否有视觉输出工具
# 4. 决定运行模式
mode = detect_mode()  # "local" | "host_tool" | "advisor"
```

### Step 5: 出图

根据运行模式执行。

### Step 6: 后续编辑

记录可编辑参数，支持后续局部修改。

## 与Hermes现有系统融合

### 1. 与视频制作联动

garden-gpt-image-engineer 生成的分镜图 → garden-web-video-production 的视频素材

### 2. 与网页设计联动

garden-web-design-engineer 的视觉元素 → garden-gpt-image-engineer 的UI素材补充

### 3. 与情报采集联动

Crawl4AI采集的图片+描述 → 作为风格参考模板输入

### 4. 与认知蒸馏联动

蒸馏出的受众审美偏好 → 决定生成的视觉风格方向

### 5. 与Goal Hive联动

```
Master拆解图片生成任务:
  Worker 1: 任务分类和模板匹配
  Worker 2: 模板填充和细节丰富
  Worker 3: 环境检测和模式选择
  Worker 4: 出图和质量检查
```

## 验证清单

- [ ] 能准确判断图像任务类别
- [ ] 能从79个模板中匹配最合适的
- [ ] 模板填充后Prompt完整且结构清晰
- [ ] 环境检测正确（本地API vs 宿主工具 vs 无工具）
- [ ] 出图成功（或输出可用Prompt）
- [ ] 支持后续编辑反馈
- [ ] 生图结果符合画面目标和风格方向
- [ ] 图片分辨率/尺寸符合使用场景
- [ ] 与视频制作和网页设计联动

## 陷阱

- **默认模式不会自动选对**：如果不手动指定，Agent可能选了错误的运行模式。每次出图前先声明mode
- **模板不是万能**：复杂场景可能需要手动调整模板结构
- **尺寸冲突**：不同的下游使用场景（封面/文章配图/社交媒体）有固定尺寸要求，别忘了确认
- **文字准确性问题**：AI生图的文字经常出错。如果文字是关键内容，考虑后续编辑或确保文字区域可替换
- **风格匹配不是一次到位**：可能需要多次迭代才能达到理想风格。先出草图确认方向再精修
