# 无限画布系统 v2 架构研究笔记

**调研时间**: 2026-06-09
**调研规模**: 53个项目/文章（7批跨公众号+GitHub+论文）
**架构设计目标**: Agent驱动 + 4层可插拔生产管线 + 无限画布核心(CanvasState/EditHistory/SceneGraph/CharacterManager)

## 市场方案全景

### ComfyUI无限画布（7个）
- zml-w/ComfyUI-Infinite-Canvas (⭐4) + Infinite-Canvas前端(⭐10) — 前端+节点组合，支持Wan视频
- Acly/comfyui-inpaint-nodes (⭐1201) — 最流行inpaint，LaMa/MAT/Fooocus
- Azornes/Comfyui-LayerForge (⭐322) — 类PS图层编辑器节点
- taabata/LCM_Inpaint_Outpaint_Comfy (⭐262) — LCM快速outpaint
- GiusTex/ComfyUI-DiffusersImageOutpaint (⭐92) — SDXL diffusers outpaint
- stuttlepress/ComfyUI-Wan-VACE-Prep (⭐88) — 视频outpaint/拼接/扩展（context_frames/replace_frames/new_frames三层控制）
- NickPittas/DirectorsConsole (⭐297) — 故事板无限画布

### 开源无限画布项目（6个）
- InvokeAI (⭐27,396) — Unified Canvas，最完整开源方案
- AUTOMATIC1111 (⭐150k+) — 内置outpaint + openOutpaint(⭐527) / mosaic-outpaint(⭐114)
- Fooocus (⭐43k+) — 简易单向outpaint

### 视频无限画布（7个）
- FollowYourCanvas (⭐168) — AAAI 2025, 2K视频outpainting
- M3DDM (⭐108) — ACM MM 2023, 层级3D扩散
- Wan VACE Prep (⭐88) — ComfyUI最实用视频拼接
- 商业: Runway Gen-3 / Pika / Kling
- html-video: nexu-io/html-video (⭐2368) — HTML→MP4统一引擎, Content-Graph多场景

### 短剧/多场景生成（7个）
- ToonFlow (⭐9,786) — 一站式桌面短剧工具, 300+音色库
- Jellyfish (⭐3,786) — 端到端短剧工作空间, shot-state-machine架构
- ArcReel (⭐2,509) — Agent驱动+多供应商, 角色设计图先行策略
- CineGen (⭐411) — 多镜头视频
- shortdrama-pipeline (⭐106)
- Deep-Comedy-Pro — 短剧平台2.0, 普通电脑可运行
- AI漫剧工场 Setup 0.2.0

### API层面（5个）
- Leonardo.ai Canvas / Midjourney Pan / DALL-E Outpaint / Seedance / Flux Fill Pro

### 论文（15篇）
- Flexible Diffusion / Dynamic Scenes / Gen-L-Video / CoNo / Long Context Tuning
- VideoGen-of-Thought / STAGE / StoryMem
- Sora 2 / Veo 3/3.1 / Seedance 1.0+2.0 / ShotStream

## 核心架构设计

### 5大生产引擎
1. **图片生产**: HTML截图(免费,5s) → ComfyUI(高质量) → GPT-Image2(18类79模板)
2. **图片编辑**: Outpaint/Inpaint/调色/局部重绘/尺寸调整
3. **视频生成**: html-video(Content-Graph) → HyperFrames(确定性) → ComfyUI(创意)
4. **短剧生产**: hermes_short_drama_engine → Toonflow → Seedance2.0
5. **PPT生成**: Frontend Slides 34模板 (20.5K★)

### 无限画布四模块
1. CanvasStateManager: 元素/层级/场景管理
2. EditHistoryManager: undo/redo/版本分支/检查点
3. SceneGraphManager: 场景定义/镜头切换/故事状态维护
4. CharacterManager: 角色数据库/跨镜头一致性/角色状态追踪

### Goal Hive Master调度
用户输入 → 判型 → Worker拆解 → Expert System辅助 → 执行 → 验证

### 集成的外部项目
- html-video (nexu-io, ⭐2368): HTML→MP4统一引擎 + Content-Graph故事板
- Frontend Slides (⭐20,500): 34套PPT模板
- Deep-Comedy-Pro: 短剧平台
- Crawl4AI (⭐67,300): LLM友好爬虫（强化情报采集层）
- Clypra (⭐1,737): Tauri+React+TS视频编辑器

### Expert System辅助
| 阶段 | 可调用Expert |
|------|-------------|
| 角色设计 | expert-ai-cv |
| 剧本质量 | marketing-experts |
| 视频剪辑 | expert-content-creative |
| PPT设计 | design-experts |
| 短剧编剧 | psychology-cognition-experts |

## 关键发现：Agent驱动视频管线（来自NL156真实实践）
1. 文字→口播稿→画面→字幕→语音→合成（6分钟竖屏视频全自动）
2. 多模型分工：推理Pro / 检索Flash / 生图seedream / 语音mimo-tts
3. 犯错CheckList：Agent失败后自动更新防止再犯
4. 知识巡游：每天中午自动翻知识库补关联
