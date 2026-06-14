---
name: ai-short-drama-pipeline
description: AI短剧全自动生产管线 — 集成Toonflow(9.5K Star开源AI短剧工具) + Deep-Comedy-Pro(短剧平台2.0) + GPT-image2+Seedance2 + garden-web-video-production。支持剧本→角色→分镜→片段→导演全流程自动化，普通电脑即可运行。
version: 2.0.0
author: Hermes Agent
domain: creative
tags:
  - short-drama
  - ai-video
  - toonflow
  - deep-comedy
  - script-to-video
  - drama-production
triggers:
  - "短剧"
  - "AI短剧"
  - "Toonflow"
  - "Deep Comedy"
  - "漫剧"
  - "短视频创作"
  - "小说转视频"
  - "分镜生成"
  - "角色锁定"
  - "智能编剧"
  - "视频合成"
  - "配音"
  - "剧本转视频"
  - "drama"
  - "角色注册"
  - "统一视频引擎"
  - "hermes_video_engine"
  - "hermes_short_drama_engine"
---

# AI Short Drama Pipeline

## 核心理念

融合两个开源AI短剧系统 + 现有视频能力，形成全自动短剧生产管线：

- **Toonflow** (GitHub: HBAI-Ltd/Toonflow-app, 9.5K Star) — 一站式AI短剧创作工具
- **Deep-Comedy-Pro** (GitHub: comedyleee/deep-comedy-pro) — 短剧平台2.0，普通电脑可运行
- **GPT-image2 + Seedance2** — 分镜+运镜+画面直出
- **garden-web-video-production** — 网页转视频能力

## 核心能力矩阵

| 阶段 | Toonflow | Deep-Comedy-Pro | Hermes增强 |
|------|----------|-----------------|-----------|
| 编剧 | AI智能编剧（提取章节/剧情结构） | AI剧本创作 | Goal Hive拆解+认知蒸馏受众 |
| 角色 | 角色视觉锁定（固定形象/画风切换） | 角色生成 | 统一角色资产管理 |
| 分镜 | 无限画布智能分镜 | 片段生成 | garden-gpt-image-engineer结构化分镜 |
| 合成 | 全自动化视频合成+300音色库 | 一站式导演导出 | garden-web-video-production TTS |
| 输出 | 竖屏9:16 | 多种格式 | 横屏16:9/竖屏9:16/方形1:1 |

## 全自动短剧生产流程（7阶段）

### Phase 0: 需求理解与规划
输入: 小说/故事/创意/新闻事件
Goal Hive Master拆解:
  - 识别内容类型和受众
  - 拆解为剧本→角色→分镜→视频→配音→合成子任务
  - [可选] 调用Expert System评估: 情感曲线/受众共鸣
  - 输出: 生产计划书（阶段分解+时间线+质量目标）

### Phase 1: 剧本生成

输入：小说/故事/创意/新闻事件

```
方法1（快速）: Toonflow/Deep-Comedy自带AI编剧
方法2（深度）: Goal Hive Master拆解
  Worker 1: 提取章节事件
  Worker 2: 拆解剧情结构
  Worker 3: 生成对白+场景描述+剧情走向
```

### Phase 2: 角色视觉锁定

```python
# 统一的角色资产管理
roles = {
    "主角": {
        "外貌": "设定描述",
        "性格": "性格特征",
        "身份": "角色身份",
        "视觉风格": "国风/动漫/写实/其他"
    },
    ...
}

# 无论生成多少集，主角的脸不崩塌
# 支持自定义形象锁定（固定的角色设定图）
```

### Phase 3: 智能分镜

```python
# 自动生成分镜提示词与画面设计
storyboards = auto_generate_storyboard(script, roles)
# 细化: 前景/中景/背景、角色动态、场景布局
# 输出: 无限画布上的分镜节点
```

### Phase 4: 视频片段生成

```python
METHODS = {
    "toonflow": "Toonflow内置视频生成引擎（最低130元/2分钟）",
    "deep_comedy": "Deep-Comedy-Pro生成引擎（普通电脑可运行）",
    "seedance2_gpt": "GPT-image2分镜+Seedance2.0转角色动作视频",
    "html_video": "garden-web-video-production网页视频方案"
}
```

### Phase 5: 配音与配乐

```python
AUDIO_OPTIONS = {
    "toonflow": "内置300+音色库+自动匹配BGM",
    "html_video": "可插拔TTS系统（MiniMax/OpenAI/Edge）",
    "custom": "支持外接TTS服务（Azure/Google Cloud等）"
}
```

### Phase 6: 合成与导出

- 视频片段一键无缝拼接
- 竖屏9:16高清格式（完美适配抖音/快手/视频号/小红书）
- 可选横屏16:9

## 修正: 分镜生成策略(2026-06-09更新)
基于GPT-Image2分镜故事版方法调研:

1. **灰白稿策略**: 分镜图必须灰白稿(非实景),实景故事版会让视频模型判断混乱
2. **单镜头独立**: 每个镜头做独立故事版,不要把多个分镜堆在同一张图
3. **角色@图片**: 通过@图片形式引用角色资产到GPT-Image2
4. **动作分镜**: 用火柴人做previs调度图,方便后期复用角色

## 修正: 学习Toonflow的无限画布分镜组织
Toonflow(9.5K Star)的ProductionAgent核心面板提供无限画布组织分镜:
- 像拼图一样直观组织分镜/素材/视频节点
- 流回工作台即可精调画面蓝图
- 已集成(在Phase3中引用)

### 1. 与情报采集联动

Crawl4AI采集的热点故事 → 直接进入短剧剧本生产

### 2. 与Goal Hive联动

```
Master拆解短剧生产任务:
  Worker 1: 剧本 -> 结构化剧本（Goal Hive拆解）
  Worker 2: 角色 -> 统一视觉资产
  Worker 3: 分镜 -> 逐帧提示词
  Worker 4: 视频 -> 各片段生成
  Worker 5: 配音 -> TTS合成
  Worker 6: 合成 -> 最终导出
```

### 3. 与garden系列联动

- garden-gpt-image-engineer → 分镜图生成
- garden-web-video-production → 网页视频方案
- garden-web-design-engineer → 封面和品牌设计

### 4. 与认知蒸馏联动

蒸馏出的内容受众模型 → 决定短剧风格（国风/动漫/写实）

### 5. 与推送系统联动

生成的短剧 → PushPlus/其他平台推送

## 安装集成指南

### 底层执行引擎（Hermes原生，推荐优先使用）

本skill对应的**真实执行脚本**（2026-06-06部署）：

| 脚本 | 路径 | 职责 |
|------|------|------|
| **hermes_video_engine.py** | `~/.hermes/scripts/` | 统一视频引擎: ComfyUI(35视频节点)+ffmpeg+Flipbook+管线规划 |
| **hermes_short_drama_engine.py** | `~/.hermes/scripts/` | 短剧全流程: 剧本分段→角色管理(CharacterManager)→智能分镜→配音→合成 |
| **hermes_video_pipeline_executor.py** | `~/.hermes/scripts/` | 组合管线: 自动选择最优引擎+链式组合+并行调度+自动降级 |
| **video_cron_jobs.py** | `~/.hermes/scripts/` | cron每30分健康检查 |

### 使用方式

```bash
# 查看短剧引擎状态
python3 ~/.hermes/scripts/hermes_short_drama_engine.py --status

# 从剧本文件生产短剧
python3 ~/.hermes/scripts/hermes_short_drama_engine.py --produce script.txt --title "我的短剧"

# 注册角色（跨片段脸一致）
python3 ~/.hermes/scripts/hermes_short_drama_engine.py \
  --register-character "小兔子" "雪白毛发红色眼睛" "活泼好奇" "菜园小居民"

# 列出已注册角色
python3 ~/.hermes/scripts/hermes_short_drama_engine.py --list-characters

# 查看统一视频引擎状态
python3 ~/.hermes/scripts/hermes_video_engine.py --status

# 自动规划最优视频生产策略
python3 ~/.hermes/scripts/hermes_video_engine.py --plan "用短剧引擎把这篇小说转成视频"
```

### 编程接口

```python
from hermes_short_drama_engine import (
    ShortDramaEngine,
    CharacterManager,
    ScriptProcessor,
    StoryboardGenerator,
    VoiceGenerator
)

# 注册角色
CharacterManager.register_character(
    name="主角",
    appearance="设定描述",
    personality="性格特征",
    identity="角色身份",
    style="写实"
)

# 全流程短剧生产
result = ShortDramaEngine.produce(
    script_text="剧本内容...",
    title="我的短剧",
    max_scenes=10,
    fps=24,
    seconds_per_scene=5.0,
    use_tts=True
)
```

### 外部工具集成

### Toonflow集成
```bash
# 下载: https://github.com/HBAI-Ltd/Toonflow-app
# Mac/Windows直接下载使用，无需部署
```

### Deep-Comedy-Pro集成
```bash
# 源代码: https://www.gitcc.com/comedyleee/deep-comedy-pro
# 安装文件: AI漫剧工场 Setup 0.2.0.exe
# 普通电脑即可运行
```

## 验证清单

- [ ] 剧本生成可自动化（小说/故事→结构化剧本）
- [ ] 角色视觉锁定（跨片段脸不崩塌）
- [ ] 智能分镜输出（前中后景+角色动态+场景布局）
- [ ] 视频片段生成（Toonflow/Deep-Comedy/Sedance2方案至少一种可用）
- [ ] 配音与BGM自动匹配
- [ ] 合成导出（竖屏9:16）
- [ ] 导出视频适配抖音/快手/视频号/小红书

## 陷阱

- **成本**：Toonflow生成2分钟短剧约130元（取决于视频模型价格）
- **模型质量**：分镜图和视频质量高度依赖底层AI模型
- **角色一致性**：优先使用本引擎的CharacterManager（统一角色数据库），确保跨片段人脸不崩塌
- **普通电脑≠没要求**：Deep-Comedy-Pro说"普通电脑即可"，但仍需一定GPU能力
- **短剧质量依赖提示词**：分镜提示词的质量直接影响成片质量
- **故障自愈**：执行失败时参考SOUL.md层2的故障自愈协议——7分钟指数退避(2s→4s→8s→16s)→突破模式→汇报。禁止直接汇报失败
- **与强制执行宪章联动**：短剧生产属于P1多步任务，默认P1强执行模式，失败自动重试3次换3种方法
