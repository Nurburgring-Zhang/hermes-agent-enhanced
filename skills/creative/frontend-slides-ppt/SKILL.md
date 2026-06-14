---
name: frontend-slides-ppt
description: 基于Frontend Slides方法论（zero-dependency HTML幻灯片生成），从内容直接生成精美网页PPT。零依赖、34+顶美模板、支持PPT转换、可导出PDF。无需PowerPoint/Keynote。
---

# Frontend Slides PPT 生成器

**⚠️ 集成状态: 方法论已就绪，34套真实模板尚未安装到本地。**
系统中有这个skill的"设计理念"和"工作步骤"，但没有实际安装
[zarazhangrui/frontend-slides](https://github.com/zarazhangrui/frontend-slides) 源码库（20.5K★, 34套模板）。
使用前先 clone 代码库以获取真实模板：
```bash
git clone https://github.com/zarazhangrui/frontend-slides.git /home/administrator/.hermes/references/frontend-slides
```
# Frontend Slides PPT 生成器

**来源**: zarazhangrui/frontend-slides (⭐20,500) — 开源界PPT Skill第一名
**仓库**: https://github.com/zarazhangrui/frontend-slides

## 何时使用
当需要将文章/报告/方案/数据/课程内容转化为HTML网页PPT时使用。也支持将已有的PPT/PPTX文件转换为网页幻灯片。

## 核心原则
## 核心原则(Claude Design设计理念继承)
1. 零依赖 — 单个自包含HTML文件，内联CSS/JS，无需npm/构建工具
2. 视觉探索 — 先生成2-3个单页风格预览让用户选择，再构建完整演示文稿
3. 反AI味: 禁止Inter字体+紫粉渐变+(Claude Design原则)
4. 设计系统先行: 写HTML前先宣告配色+字体+间距+圆角
5. oklch配色: 保持亮度(L)和色度(C)不变调色相角(h)
4. 固定16:9比例 — 每页slide必须100vh，overflow:hidden
5. 导航系统 — 键盘箭头/滚轮/触摸/点击导航

## 工作流程
```
Step 0: 检查本地是否有frontend-slides源码
  → 有: 直接从templates/挑选真实模板
  → 无: 使用skill描述的方法论自行生成
Step 1: 理解内容 → 提取核心观点和结构
Step 2: 生成2-3个单页风格预览 → 让用户选择
Step 3: 构建完整HTML幻灯片（所有slide在一个HTML中）
Step 4: 验证：排版正确、导航正常、动画正常
Step 5: 可选：导出为PDF（通过browser的print to PDF）
```

## 34套真实模板类型（来自frontend-slides项目）
- **封面型**: 大字标题+干净留白（适合产品发布、项目启动）
- **内容型**: 信息模块化、漏斗图、流程图、对比表、增长曲线
- **数据型**: 数据图表、KPI卡片、财报摘要
- **技术型**: 架构图、API文档、代码演示
- **品牌型**: 企业介绍、案例研究、品牌故事

## 设计规范
- 色彩：主色+强调色（非AI标准色），克制使用
- 配色: 使用oklch色彩空间替代HSL（L+C不变调hue，颜色自动和谐）
- 字体：推荐 Instrument Serif(Space Grotesk/Plus Jakarta Sans/Sora/Newsreader 等。**禁止**: Inter, Roboto, Arial, Fraunces, system-ui
- 间距：网格系统，一致性
- 信息密度：每页1-3个要点，不过载
- 动画：适度，不干扰阅读
- 背景：可用轻微纹理/渐变，避免纯白
- **反AI味**: 紫色渐变/大圆角卡片/emoji当图标/假数据填充 — 全部禁止

## 典型用途
- 技术方案演示
- 数据分析报告
- 产品介绍
- 教学课件
- 商业计划书
- 文章精读/摘要展示
