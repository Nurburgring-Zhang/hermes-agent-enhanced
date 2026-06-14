---
name: flipbook-vidu-bridge
description: Flipbook+Vidu 视频/图像生成能力桥架 - 非Docker视频生成引擎。现已集成到统一视频生产引擎(hermes_video_engine.py)，可自动化调用ComfyUI 35个视频节点、ffmpeg管线、短剧生产引擎。
version: 2.0.0
author: Hermes Agent
trigger: 用户要求视频生成、图像序列动画、Flipbook、Vidu集成、文生视频、图生视频、视频处理
tags:
  - flipbook
  - vidu
  - video-generation
  - comfyui
  - video-engine
  - integrated
---

# Flipbook+Vidu Video Bridge v2.0

## 架构升级

v2.0 已从独立脚本升级为 **Hermes 统一视频生产引擎的组件**：

```
hermes_video_engine.py (统一入口)
    │
    ├── ComfyUIVideoGenerator — 35个视频节点(Wan/Hunyuan/AnimateDiff/CogVideoX/LTXVideo)
    ├── FFmpegProcessor — 拼接/音频/缩放/录屏
    ├── ShortDramaPipeline — 短剧全流程生产
    ├── HTMLVideoEngine — 网页视频生成
    └── VideoPipeline — 组合管线调度器
    
flipbook (保留) → hermes_video_engine.py 兼容层
```

## 核心能力

### 1. ComfyUI视频生成
ComfyUI位于 `/mnt/d/ComfyUI/`，**35个视频相关自定义节点**：
- WanVideo (10+节点)
- HunyuanVideo (6+节点)
- AnimateDiff Evolved (4+节点)
- CogVideoX Wrapper
- LTXVideo
- 帧插值/上采样套件
- VideoHelper Suite

### 2. 视频处理（ffmpeg）
- 片段拼接（concat）
- 音频添加/替换
- 缩放/裁剪
- 屏幕录制
- 格式转换

### 3. 短剧生产
通过 `hermes_short_drama_engine.py`：
- 剧本分段→角色管理→分镜生成→视频片段→配音→合成
- 角色视觉一致性（跨片段脸不崩塌）
- 全流程自动化

### 4. 网页视频（HTML-Video）
- 11种主题模板
- 可插拔TTS
- 局部迭代编辑

## 使用方式

```bash
# 1. 统一查看所有视频引擎状态
python3 ~/.hermes/scripts/hermes_video_engine.py --status

# 2. ComfyUI健康检查
python3 ~/.hermes/scripts/hermes_video_engine.py --healthcheck

# 3. 列出可用视频模型
python3 ~/.hermes/scripts/hermes_video_engine.py --video-models

# 4. 规划视频生产
python3 ~/.hermes/scripts/hermes_video_engine.py --plan "用WanVideo生成一个10秒的日落视频"

# 5. 拼接视频文件
python3 ~/.hermes/scripts/hermes_video_engine.py --concat clip1.mp4 clip2.mp4 output.mp4

# 6. 短剧生产（从剧本文件）
python3 ~/.hermes/scripts/hermes_short_drama_engine.py --produce script.txt --title "我的短剧"

# 7. 注册角色（短剧用）
python3 ~/.hermes/scripts/hermes_short_drama_engine.py \
  --register-character "小兔子" "雪白毛发红色眼睛" "活泼好奇" "菜园小居民"

# 8. cron健康检查
python3 ~/.hermes/scripts/video_cron_jobs.py healthcheck
python3 ~/.hermes/scripts/video_cron_jobs.py clean --dry-run false
```

## 编程接口

```python
from hermes_video_engine import (
    ComfyUIVideoGenerator,
    FFmpegProcessor,
    VideoPipeline,
    HTMLVideoEngine,
    get_status
)

# 检查状态
status = get_status()
print(f"ComfyUI: {status['comfyui']['exists']}, {status['comfyui']['video_nodes']} nodes")

# 规划管线
plan = VideoPipeline.plan_pipeline("做一个10秒的AI短剧")
result = VideoPipeline.execute_pipeline(plan)

# 视频拼接
result = FFmpegProcessor.concat_videos(["clip1.mp4", "clip2.mp4"], "output.mp4")

# 短剧生产
from hermes_short_drama_engine import ShortDramaEngine, CharacterManager
CharacterManager.register_character("主角", "设定描述", "性格", "身份")
drama = ShortDramaEngine.produce(script_text, title="我的短剧")
```

## 系统集成

- **cron**: `video_cron_jobs.py healthcheck` 每30分钟
- **系统钩子**: 
  - PRE: 检测到视频/短剧任务时自动准备ComfyUI
  - POST: 视频生成完成自动更新输出目录
- **记忆**: 自动记录用户偏好的视频风格/主题/参数
- **Goal Hive**: 短剧生产自动拆解为6+ Worker并行执行
- **推送**: 视频完成可推送（PushPlus）

## 验证清单

- [ ] `hermes_video_engine.py --healthcheck` 返回健康状态
- [ ] ComfyUI 35个视频节点可调用
- [ ] ffmpeg拼接/音频/缩放可用
- [ ] 短剧角色可注册
- [ ] 剧本分段正常
- [ ] 短剧全流程可触发
- [ ] cron健康检查正常运行
- [ ] 所有视频/短剧相关的Hermes响应自动调用统一引擎

## 配套执行脚本

This skill has 3 companion execution scripts (created 2026-06-06):

| 脚本 | 位置 | 用途 |
|------|------|------|
| `hermes_video_engine.py` | `~/.hermes/scripts/` | 统一视频引擎: ComfyUI(35视频节点)+ffmpeg+flipbook |
| `hermes_short_drama_engine.py` | `~/.hermes/scripts/` | 短剧全流程: 剧本分段+角色管理+分镜+配音+合成 |
| `hermes_video_pipeline_executor.py` | `~/.hermes/scripts/` | 组合管线: 自动选择引擎+链式组合+并行调度 |
| `video_cron_jobs.py` | `~/.hermes/scripts/` | cron健康检查: 每30分钟守护 |

## 陷阱

- **ComfyUI需要先启动**: 生成视频前先检查 `python3 ~/.hermes/scripts/hermes_video_engine.py --healthcheck`。ComfyUI不在运行则先启动：`python3 ~/.hermes/skills/creative/comfyui/scripts/comfyui_setup.sh`
- **视频输出默认保存到**: `~/.hermes/outputs/video/` 和 `~/.hermes/outputs/short_drama/`
- **短剧角色数据库**: `~/.hermes/data/drama_characters.json`，角色注册后永久有效
- **旧视频不自动清理**: 定期运行 `python3 ~/.hermes/scripts/video_cron_jobs.py clean --dry-run false`（默认保留7天）
- **组合管线会自动降级**: 如果ComfyUI不可用，自动fallback到html-video方案

## 依赖

- ComfyUI (`/mnt/d/ComfyUI/`)
- FFmpeg (已安装 `/usr/bin/ffmpeg`)
- Python 3.10+
- 可选: edge-tts (配音), playwright (录屏)
