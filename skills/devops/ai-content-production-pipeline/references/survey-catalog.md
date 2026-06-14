# 无限画布系统调研项目清单 (2026-06-09)

## 批1: 40+项目 (前期调研)
### ComfyUI无限画布(7个)
| 项目 | Stars | 关键点 |
|------|-------|--------|
| zml-w/ComfyUI-Infinite-Canvas | ⭐4 | 前端+节点组合, Wan视频支持 |
| Acly/comfyui-inpaint-nodes | ⭐1201 | 最流行inpaint, LaMa/MAT/Fooocus |
| Azornes/Comfyui-LayerForge | ⭐322 | 类PS图层编辑器 |
| taabata/LCM_Inpaint_Outpaint_Comfy | ⭐262 | LCM快速outpaint |
| GiusTex/ComfyUI-DiffusersImageOutpaint | ⭐92 | SDXL diffusers |
| stuttlepress/ComfyUI-Wan-VACE-Prep | ⭐88 | 视频拼接/扩展 |
| NickPittas/DirectorsConsole | ⭐297 | 故事板无限画布 |

### 开源画布(6个)
| 项目 | Stars | 关键点 |
|------|-------|--------|
| InvokeAI | ⭐27,396 | Unified Canvas最完整 |
| AUTOMATIC1111 | ⭐150k+ | 内置outpaint |
| Fooocus | ⭐43k+ | 简易单向outpaint |

### 视频画布(7个)
| 项目 | Stars | 关键点 |
|------|-------|--------|
| FollowYourCanvas | ⭐168 | AAAI 2025, 2K视频outpainting |
| M3DDM | ⭐108 | 层级3D扩散 |

### 短剧(7个)
| 项目 | Stars | 关键点 |
|------|-------|--------|
| Toonflow | ⭐9,786 | 一站式桌面短剧, ProductionAgent |
| Jellyfish | ⭐3,786 | shot-state-machine, 端到端短剧工作空间 |
| ArcReel | ⭐2,509 | Agent驱动+多供应商, 角色设计图先行 |
| CineGen | ⭐411 | |
| Deep-Comedy-Pro | 开源 | 短剧平台2.0, 普通电脑可运行 |

### API层(5个)
Leonardo.ai Canvas, Midjourney Pan, DALL-E Outpaint, Seedance, Flux Fill Pro

## 批2-7: 微信文章(11篇)
| # | 文章 | 核心能力 |
|---|------|---------|
| 1 | html-video (Open Design, 2.4K★) | HTML→MP4统一引擎, 21模板, Content-Graph |
| 2 | GPT-Image2分镜故事版 | 灰白稿+@图片角色引用 |
| 3 | Sora→Seedance综述(15篇论文) | VGoT/STAGE/StoryMem/ShotStream |
| 4 | Hermes+HTML截图免费出图 | 浏览器渲染引擎当免费图像生成器 |
| 5 | Frontend Slides(20.5K★) | 34套顶美模板, 零依赖 |
| 6 | Claude Design Skill | 420行提示词核心+独立Reviewer |
| 7 | GPT-Image-2完全指南 | 18类79模板, Arena第一 |
| 8 | ConardLi视频制作Skill | 4Phase+2人工Checkpoint+独立Reviewer |
| 9 | 女娲+PPT Director | 认知蒸馏+PPT导演+17种页型 |
| 10 | GPT-Image2+Seedance2导演级分镜 | 武术专家→Previs→角色动作视频 |
| 11 | Toonflow(9.5K★) | 一站式AI短剧创作, 无限画布分镜 |

## 额外项目
| 项目 | Stars | 关键点 |
|------|-------|--------|
| Clypra | ⭐1,737 | Tauri+React+TS, CapCut免费替代 |
| Crawl4AI | ⭐67,300 | LLM爬虫, 情报采集 |
| Odysseus | 24h⭐36K | 私有AI工作台(低优先级) |
| PromptLibraryNode | Nurburgring-Zhang | ComfyUI节点, 25故事总纲+情绪引擎 |

## 最终融合方案(IMDF)
5大引擎: html-video + HyperFrames + ComfyUI + garden-video + Manim
7阶段短剧: 需求理解→剧本→角色锁定→分镜→镜头→音频→合成+审计
PPT: Frontend Slides 34模板 + Claude Design + PPT Director
网页: Claude Design 420行设计思想 + 21套风格
