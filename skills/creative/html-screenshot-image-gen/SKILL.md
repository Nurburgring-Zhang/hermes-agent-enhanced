---
name: html-screenshot-image-gen
description: 不使用生图API，通过HTML模板+浏览器截图生成结构化信息图/数据卡片/教程图/封面图。支持多风格模板切换。
---

# HTML Screenshot Image Generator

## 何时使用
当需要生成结构化信息图、数据卡片、教程步骤图、公众号封面图、对比图时使用。不使用任何生图API。

## 核心理念
把浏览器渲染引擎当免费图像生成器。HTML天生为"结构化内容+精确排版"设计——颜色、字体、间距、对齐全部像素级可控，中文渲染完美，零成本。

## 与Hermes集成(2026-06-09)
```python
# 用户说"做成信息图"时:
1. Agent选模板(暖色/深色/数据卡片)
2. 注入内容 → 生成HTML文件
3. browser_navigate打开HTML → browser_vision截图
4. 输出高清PNG
# 整个过程5秒内,免费,可无限次
```

## 核心原理
1. 把内容填入HTML模板（CSS精确控制排版）
2. 用write_file保存到临时目录
3. 用browser_navigate打开HTML文件
4. 用browser_vision截图保存为PNG

## 风格模板

### 风格A：米色暖系
适合公众号配图、教程步骤图、微信群精华摘要
- 背景：#f5f0e8，强调色：#8b6f47（棕褐）
- 字体：PingFang SC
- 布局：1080px宽，圆角卡片，带编号的步骤列表
- HTML模板：米色底 + 白色卡片 + 棕褐数字编号

### 风格B：深色极简
适合数据卡片、金句图、朋友圈传播
- 背景：#0d0d0d，强调色：#4ade80（荧光绿）
- 字体：PingFang SC
- 布局：1080px宽，深色卡片+荧光绿高亮数据
- HTML模板：深色底 + 暗色卡片 + 绿色数据高亮

### 风格C：Frontend Slides（PPT风格）
适合演示文稿、分享PPT
- 固定16:9比例
- 多slide导航（键盘/鼠标/触摸）
- 动画reveal效果
- 可导出为PDF

## 输出格式
- 信息图：1080×? px PNG
- 数据卡片：1080×? px PNG
- 封面图：自定义尺寸
- PPT：HTML文件或PDF

## 约束
- 不使用任何图像生成API
- 文字由HTML CSS渲染，中文完美
- 风格全局预设，不临时设计
- 截图前确保字体/资源加载完成

## 模板文件
- templates/style-warm-card.html — 米色暖系信息图（步骤/列表）
- templates/style-dark-data.html — 深色极简数据卡片（统计/对比）

使用模板时，将{{TITLE}}、{{STEPS}}、{{STATS}}等占位符替换为实际内容后保存为HTML文件，再用browser_navigate + browser_vision截图。
