---
name: garden-skills-bridge
description: ConardLi garden-skills 7K Stars 全面集成 — 视频制作Skill(web-video-presentation) + 网页设计Skill(web-design-engineer) + 图片生成Skill(gpt-image-2)。将AI内容创作从"一次抽卡"升级为"稳定生产线"。
version: 1.0.0
author: Hermes Agent
domain: creative
tags:
  - garden-skills
  - web-video
  - web-design
  - gpt-image
  - content-creation
  - video-production
  - web-design-engineer
triggers:
  - "garden-skills"
  - "视频制作"
  - "网页设计"
  - "图片生成"
  - "web-video"
  - "视频Skill"
  - "gpt-image"
  - "内容创作"
---

# Garden Skills Bridge

## 核心理念

基于 ConardLi 的 garden-skills (GitHub 7K Stars) 全面集成：

**Skill的价值不在提示词写得多漂亮。它的价值在于把一套可重复稳定工作的方法交给Agent。**

### 三个核心问题

一个好Skill要提供：
1. **明确的工作流程** — 什么时候该问、什么时候该做、什么时候该停
2. **明确的质量标准** — 什么算好、什么算AI味太重
3. **明确的迭代接口** — 不满意时该反馈什么、Agent知道该改哪一层

## 1. 视频制作Skill (web-video-presentation)

### 原理
把文章/脚本/课程/产品Demo/技术分享等文字内容，转化为**基于网页制作的演示视频**。

不是直接生成mp4，而是生成一个用网页模拟的视频效果——章节、旁白、画面、主题、进度控制，全都可以被代码控制。

### 11套主题模板

| 主题 | 风格 | 适合场景 |
|------|------|---------|
| bold-signal | 大色块+大标题 | 产品发布、营销片头、投资人pitch |
| terminal-green | 终端感 | CLI教程、安全话题、黑客风 |
| newsroom | 报纸特稿 | 热点解读、深度报道 |
| electric-studio | 白底电光蓝 | B2B产品演讲、企业财报 |
| bauhaus-bold | 包豪斯+布鲁塔利 | 观点宣言、设计演讲 |
| creative-voltage | 设计工作室风 | 创意分享、设计周 |
| neon-cyber | 霓虹感 | AI/大模型/Web3 |
| vintage-editorial | 专栏作者风 | 个人观点、文化随笔 |
| split-canvas | 左右双色画布 | 对比、辩论、故事讲述 |
| dark-botanical | 时尚杂志风 | 品牌故事、美妆 |
| forest-ink | 国家地理感 | 自然、可持续、户外 |

### 使用方式

```python
# 在Claude Code/Hermes中
"用web-video-presentation skill，主题选bold-signal，
 把下面的文章转成演示视频：[文章内容]"
```

### 关键成功因素
- 模型：Opus 4.7效果最好
- 第一轮Review必须认真看脚本 → 方向定好再完整生成
- 局部迭代：不满意某一章就单独反馈
- TTS可插拔：MiniMax / OpenAI / ElevenLabs / edge-tts

## 2. 网页设计Skill (web-design-engineer)

### 原理
把Agent从"套默认审美"拉回到真正的网页设计流程：
先判断产品类型和受众 → 确定视觉方向 → 信息层级 → 排版节奏 → 组件密度 → 交互细节

### 25套设计主题

部分核心主题：
- linear — B2B SaaS、开发者工具
- raycast — 效率工具、暗色风格
- aesop — 留白+文字比例+产品图
- tufte-dataink — 数据叙事、研究报告
- field-io — 艺术科技、互动装置
- active-theory — 电影感发布页
- bloomberg — 杂志封面、观点专题
- balenciaga — 时装、潮流、反常规
- mailchimp-freddie — 社区、创业工具
- headspace — 健康、心理、教育
- y2k-retrofuturism — Y2K、复古科技

### 使用方式

```python
"用web-design-engineer skill，风格选linear，
 为我的[产品名]做官网设计，包含以下功能..."
```

## 3. 图片生成Skill (gpt-image-2)

### 原理
把图像任务拆成不同类别，提供结构化模板。目前包含：
- **18大类**图像任务
- **79个**结构化Prompt模板
- 覆盖生成和编辑两类工作流

### 三种运行模式

| 模式 | 适用环境 | 工作方式 |
|------|---------|---------|
| 本地模式 | 有API Key | 直接调接口出图并落盘 |
| 宿主工具模式 | CodeX等 | 把Prompt交给Agent自带的图像工具 |
| 顾问模式 | 无图像工具 | 退化成Prompt顾问 |

### 好的图片Prompt结构

```
画面目标 + 主体与关系 + 构图 + 材质 + 光线 + 字体文字限制 + 输出尺寸 + 编辑空间
```

## Hermes集成方式

### 直接使用
```python
# 视频制作
"用 garden-skills 的 video presentation，把[链接/文本]转成演示视频"

# 网页设计
"用 garden-skills 的 web-design，风格[xxx]，做[xxx]的官网"

# 图片生成
"用 garden-skills 的 gpt-image-2，模式[local/host/consult]，做[xxx]"
```

### Skills即SOP的延伸
garden-skills 完美诠释了"任何重复两次的流程就该变成Skills"：
- 视频制作：不是每次重新写提示词，而是用同一套工作流
- 网页设计：不是每次从零构思风格，而是从主题库选
- 图片生成：不是碰运气，而是用结构化模板确保稳定

## 在线体验地址

- 图片生成: https://gpt-image2.mmh1.top/
- 网页设计: https://mmh1.top/#/ai-application/web-design-engineer
- 视频生成: https://mmh1.top/#/ai-application/web-video-presentation

## 验证清单

- [ ] 视频制作Skill可生成网页版演示视频
- [ ] 可切换11种主题模板
- [ ] TTS可插拔
- [ ] 网页设计Skill可生成有设计感的网页
- [ ] 可切换25种风格
- [ ] 图片生成Skill支持3种运行模式
- [ ] 79个结构化模板可用
- [ ] 局部迭代可单独调整
