---
name: frontend-slides-ppt
description: 基于Frontend Slides方法论（zero-dependency HTML幻灯片生成），从内容直接生成精美网页PPT。零依赖、34+顶美模板、支持PPT转换、可导出PDF。无需PowerPoint/Keynote。
---

# Frontend Slides PPT 生成器

## 何时使用
当需要将文章/报告/方案/数据/课程内容转化为HTML网页PPT时使用。也支持将已有的PPT/PPTX文件转换为网页幻灯片。

## 核心原则
1. 零依赖 — 单个自包含HTML文件，内联CSS/JS，无需npm/构建工具
2. 视觉探索 — 先生成2-3个单页风格预览让用户选择，再构建完整演示文稿
3. 告别AI风 — 避免白色背景+紫色渐变等典型AI外观
4. 固定16:9比例 — 每页slide必须100vh，overflow:hidden
5. 导航系统 — 键盘箭头/滚轮/触摸/点击导航

## 工作流程
```
Step 1: 理解内容 → 提取核心观点和结构
Step 2: 生成2-3个单页风格预览 → 让用户选择
Step 3: 构建完整HTML幻灯片（所有slide在一个HTML中）
Step 4: 验证：排版正确、导航正常、动画正常
Step 5: 可选：导出为PDF（通过browser的print to PDF）
```

## 设计规范
- 色彩：主色+强调色（非AI标准色），克制使用
- 字体：系统字体，安全字体栈
- 间距：网格系统，一致性
- 信息密度：每页1-3个要点，不过载
- 动画：适度，不干扰阅读
- 背景：可用轻微纹理/渐变，避免纯白

## 典型用途
- 技术方案演示
- 数据分析报告
- 产品介绍
- 教学课件
- 商业计划书
- 文章精读/摘要展示
