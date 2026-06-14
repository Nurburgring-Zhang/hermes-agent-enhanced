# Frontend Slides 设计规范参考

来源: https://github.com/zarazhangrui/frontend-slides (20.6K Stars)

## 核心原则
- "Show, Don't Tell" — 生成视觉预览而不是让用户做抽象选择
- 零依赖 — 单个自包含HTML文件，内联CSS/JS，无需npm或构建工具
- 渐进式加载 — 先读轻量级风格索引，详细内容按需加载
- 视觉探索 — 生成3个单页预览→用户选择→构建完整演示
- 反AI俗套 — 避免紫色渐变+白色卡片等典型AI外观

## 导航系统（Presentation Controller）
- 键盘箭头导航
- 滚轮导航
- 触摸滑动
- 点击导航
- 每页slide固定100vh，overflow:hidden

## 风格预设约束
- viewport-safe CSS基础
- 密度限制（每页1-3个要点）
- 预设目录（34+套模板可选）
- CSS陷阱指南

## PPT/PPTX转换
使用python-pptx提取内容到结构化数据，再重新渲染为HTML slide。

## Bold Template Pack
可选的强设计感模板包，提供前卫设计风格。渐进式加载确保默认安全预设兜底。

## 导出
- 使用Playwright无头浏览器遍历所有slide
- 每页截图
- 合并为PDF（通过page.pdf()）
- 支持compact模式（1280×720）
