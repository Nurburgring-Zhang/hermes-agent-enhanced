---
name: garden-web-video-production
description: ConardLi garden-skills 网页视频制作方法全面集成 + HTML-Video开源工具。支持将文章/脚本/课程/Demo/技术分享等文字内容，转化成基于网页的演示视频。多套内置主题模板，可插拔TTS，支持局部迭代修改。
version: 1.1.0
author: Hermes Agent (from ConardLi garden-skills)
domain: creative
tags:
  - web-video
  - presentation
  - html-video
  - tts
  - theme-templates
  - video-production
triggers:
  - "视频制作"
  - "网页视频"
  - "演示视频"
  - "文章转视频"
  - "web-video"
  - "html-video"
  - "Seedance"
  - "GPT-image2 视频"
  - "Toonflow"
  - "短剧"
  - "知识视频"
  - "产品演示视频"
  - "视频脚本"
  - "网页动画演示"
  - "演讲视频"
  - "视频化"
---

# Garden Web Video Production

## 核心理念

来自 ConardLi garden-skills 的 web-video-presentation + HTML-Video(nexu-io/html-video) 全面集成。

不是直接生成mp4视频。而是生成一个**用网页模拟的视频效果** — 章节、步骤、旁白、画面、主题、进度控制全部可被代码控制。录屏时就像在播放精心设计过的视频。

### 为什么用网页做视频

长视频最麻烦的地方是随机抽卡和消耗爆炸。网页能把视频拆成工程：章节、步骤、旁白、画面、主题、进度控制，全都可以被代码控制。

### HTML-Video集成

OpenDesign团队的html-video项目（GitHub: nexu-io/html-video）基于hyperframes框架构建：
- 内置20多套顶级HTML视频模板
- 自带Studio支持分页预览/分页编辑/帧文字编辑
- 自动识别6种code agent CLI（Codex/Claude Code/Hermes/cursor agent等）
- 已接入MiniMax TTS + BGM
- 支持横屏16:9/竖屏9:16/方形1:1/小红书4:5多种尺寸

## 主题模板库

| 主题 | 风格 | 适合 |
|------|------|------|
| bold-signal | 大色块+大标题 | 产品发布、营销片头、投资人Pitch |
| terminal-green | 终端黑暗风 | CLI教程、黑客风、技术演示 |
| newsroom | 报纸特稿风格 | 热点解读、深度报道、AI分析 |
| electric-studio | 白底电光蓝 | B2B演讲、投资人路演、行业研究 |
| bauhaus-bold | 包豪斯+布鲁塔利 | 观点宣言、设计演讲、品牌主张 |
| creative-voltage | 创意工作室风格 | 创意分享、设计周、作品集 |
| neon-cyber | 霓虹赛博 | AI/大模型/Web3/网络安全 |
| vintage-editorial | 复古专栏 | 个人观点、文化随笔、美学话题 |
| split-canvas | 左右双色画布 | 双主题对比、过去vs现在 |
| dark-botanical | 自然博物馆 | 品牌故事、时尚、美妆、旅行 |
| forest-ink | 旧版国家地理 | 自然/可持续/户外/纪录片 |

## 工作流

### Phase 1: 内容分析

```
输入: 文章/脚本/课程/Demo说明/技术分享
输出: 结构化视频大纲

1. 分析内容类型和受众
2. 提取核心章节和关键信息点
3. 确定叙事节奏和情感曲线
4. 建立结构化的视频大纲
```

### Phase 2: 主题匹配

```
输入: 内容类型 + 受众 + 风格偏好
输出: 推荐主题 + 视觉方向

1. 根据内容类型匹配最适合的主题
2. 确认色调、字体、排版风格
3. 调整信息密度和动画节奏
```

### Phase 3: 脚本+大纲确认

```
输入: 原始内容 + 主题
输出: 分章节脚本 + 大纲

每个章节:
  - 章节标题
  - 旁白文本（要朗读的内容）
  - 画面描述（每页展示什么）
  - 时长建议
  - 可选的动画效果
```

### Phase 4: 生成HTML视频

```
输入: 大纲 + 主题配置
输出: 可预览的HTML文件

Agent 生成完整的HTML文件:
  - 导航/进度机制
  - 每页动画效果
  - TTS音频集成
  - 主题配色和字体
```

### Phase 5: 局部迭代

```
用户反馈:
  "第三章节奏太平了" → 调整1个章节的动画
  "这一页文字太多" → 调整1页排版
  "结尾没有记忆点" → 添加1个总结页

Agent: 只修改指定部分，不影响整体
```

### Phase 6: 视频化导出

支持多种最终产出方式：

```bash
# 1. HTML-Video 导出（首选，带Studio支持）
# 安装: git clone https://github.com/nexu-io/html-video.git
# 生成: 在html-video的模板目录下创建新项目
# 导出: html-video/Scripts/build.sh → mp4

# 2. 录屏方案
# 用浏览器打开HTML文件，全屏后录屏
# 推荐: OBS Studio / 浏览器自带录屏

# 3. 如果存在GPT-image2 + Seedance2组合可用:
#    GPT生成分镜 → Seedance2生成连贯短片
```

## 可插拔TTS配置

```python
TTS_CONFIG = {
    "minimax": {
        "script": "~/.hermes/scripts/minimax_tts.py",
        "install": "pip install minimax-tts"
    },
    "openai": {
        "script": "~/.hermes/scripts/openai_tts.py",
        "api": "tts-1",
        "voice": "alloy"
    },
    "edge": {
        "script": "~/.hermes/scripts/edge_tts.py",
        "install": "pip install edge-tts"
    }
}
```

## GPT2image + Seedance2 集成
如果环境中有这两个工具，可以组合使用：

```python
# Step 1: GPT → 文字版动作分镜
#   建立专业角色 -> 写出场景的动作调度(角色位置/运动轨迹/镜头角度)

# Step 2: GPT Image 2 → 电影级previs调度分镜图
#   用火柴人+运动轨迹线

# Step 3: Seedance 2.0 → 调度图转角色动作视频
#   提示词: "这是角色xx设定图 {{Portrait 1}}，
#   严格按照这张图 {{Portrait 2}} 中的N镜头PREVIS演绎动作"
```

## 与Hermes现有系统融合

### 1. 与情报采集管道

Craw4AI采集的网页 → 清洗 → 直接进入视频制作流程

### 2. 与认知蒸馏

蒸馏出的受众模型 → 决定视频风格和节奏配置

### 3. 与Goal Hive

```
Hive Master: 拆解视频制作任务
  - Worker 1: 内容分析和大纲
  - Worker 2: 主题选择和风格
  - Worker 3: 脚本和旁白
  - Worker 4: HTML生成和迭代
```

### 4. 与推送系统

生成的视频 → PushPlus或其他平台推送

## 验证清单

- [ ] 能根据不同内容类型推荐主题
- [ ] 生成的HTML视频可预览可导航
- [ ] TTS音频同步到旁白
- [ ] 支持局部迭代修改
- [ ] 支持多种输出尺寸
- [ ] 与HTML-Video项目集成
- [ ] 录屏后导出mp4可用
- [ ] 如果GPT2image+Seedance2可用，能组合使用
- [ ] 与认知蒸馏联动（受众风格匹配）

## 陷阱

- 模型很关键：效果最好的是Opus 4.7。视频制作有很多审美判断、章节规划、代码实现和返工决策。模型能力不行效果差异大
- 第一轮Review一定要认真看：脚本、主题、章节大纲、视觉方向在前面定得越清楚，后面返工越少
- 别期待一次到位：先让Agent做完整版本，整体跑通后挑不满意的章节继续调
- 局部迭代最好："第二章太平"、"第四章信息太密"、"缺少动画效果"——Agent很擅长这种局部迭代
