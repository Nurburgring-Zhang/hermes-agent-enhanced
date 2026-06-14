---
name: imdf-infinite-canvas
description: IMDF无限画布 — Agent驱动的多模态生产系统。7大引擎(视频/短剧/PPT/网页/故事弧/3D/数据)+Penguin Canvas v2.1.4完全集成。输入需求自动规划，EngineRouter自动选最优引擎，Quality Gate审计。纯Python+FastAPI后端，41/41测试通过。
---

# IMDF — Infinite Multimodal Data Foundry

## 何时使用
当用户要求：生成图片/信息图/视频/短剧/PPT/网页/训练数据/3D场景，或提及"无限画布"/IMDF时

## 项目位置
`/mnt/d/Hermes/infinite-multimodal-data-foundry/`
Web UI: `python3 api/canvas_web.py --port 8765` → http://localhost:8765

## 核心架构
```
用户意图
  → Master Agent (ContentAnalyzer判型 → EngineRouter选引擎 → Worker分解)
    → 具体引擎执行 (7引擎/数据引擎)
      → Quality Gate (Reviewer审计 + Checkpoint)
        → 输出
```

## 7大生产引擎
| 引擎 | 文件 | 能力 |
|------|------|------|
| Video (5合一) | engines/video_engine.py | html-video/HyperFrames/ComfyUI/garden/Manim + 真实CLI调用 + fallback |
| ShortDrama | engines/drama_engine.py | 7阶段(需求→剧本→角色→分镜→镜头→音频→合成→审计) |
| PPT | engines/ppt_engine.py | 34模板+Claude Design+18图表+设计系统先行 |
| WebDesign | engines/web_engine.py | 21风格+Claude Design+反AI味清单+Reviewer |
| StoryArc | engines/story_arc_engine.py | 25故事总纲+情绪引擎+镜头连续性追踪+独立Reviewer |
| Data T2I | engines/data/data_t2i.py | 预训练/微调/ControlNet数据 → WebDataset/COCO |
| Data Edit | engines/data/data_edit.py | Outpaint/Inpaint/超分数据对 |
| 3D全景 | engines/data/data_3d.py | 场景管理/姿势库20+预设/12动作/18关节/遮挡板/导演视角 |

## EngineRouter (智能引擎选择)
根据内容类型自动选最优引擎+fallback:
- "做PPT" → frontend-slides
- "做短视频" → html-video (fallback garden-video)
- "做信息图" → html-screenshot (0成本,像素级精确)
- "做品牌宣传片" → gpt-image-2 (fallback hyperframes)
- "做短剧" → story-arc (7阶段)
- "生成训练数据" → data-engine (T2I/edit/video/drama/book)

## Penguin Canvas v2.1.4 完全集成(16功能)
| # | 功能 | 实现位置 |
|---|------|---------|
| 1 | 3D全景/导演台/姿势/动作/遮挡板 | engines/data/data_3d.py + api/canvas_3d.py |
| 2 | Figma联动 | canvas_web.py → /api/figma/* |
| 3 | 阿里云OSS/腾讯云COS | api/cloud_storage.py (原生crypto签名) |
| 4 | 放置栏 | canvas_web.py placement API |
| 5 | veo-omni计费 | canvas_web.py engine路由 |
| 6 | 提示词模板系统 | canvas_web.py CRUD + 8分类+6内置 |
| 7 | ComfyUI remote+Docker | canvas_web.py remote mode |
| 8 | NewAPI分组令牌 | canvas_web.py /api/newapi/* |
| 9 | 流式删除 | canvas_web.py DELETE端点 |
| 10 | APIKEY删除 | canvas_web.py DELETE端点 |
| 11 | 即梦CLI+Seedance+Seedream | canvas_web.py 即梦路由+模型映射 |
| 12 | @上游联动 | canvas_web.py /api/upstream-materials |
| 13 | 上传20M上限 | canvas_web.py max_size配置 |

## 数据生产能力
| 方向 | 生产内容 | 输出格式 |
|------|---------|---------|
| 文生图 | 预训练图文对/微调/ControlNet | WebDataset/COCO/Parquet |
| 图片编辑 | Outpaint/Inpaint/超分数据对 | 输入输出+蒙版+JSON |
| 视频 | 帧提取/视频Caption/编辑对 | ffmpeg管线+JSON |
| 影视 | 多镜头叙事对/角色一致性 | JSON |
| 绘本 | 页面布局/风格一致/适龄参数 | JSON |

## 使用陷阱
1. **html-video CLI未安装时自动fallback到HTML截图** — 截图是静态的，不是真视频
2. **3D引擎是Python后端管理,前端Three.js渲染需额外开发** — 后端API已完整
3. **云存储需要配置access_key/secret_key** — 通过/api/cloud/config配置
4. **国内网络限制** — git clone npm install 可能超时,用vendor/目录离线方式
