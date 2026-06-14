# AI Generation Platform Capability Matrix (2026-06-06)

Created from NanoBot Factory full audit + multi-platform research.
Covers: what each major AI generation platform supports, parameters, models, and API access.

---

## Matrix: Feature Support by Platform

| Feature | NanoBot Current | ComfyUI(local) | Kling(云端) | Seedance(云端) | Runway Gen-4 | Pika 2.0 | Stability AI | MiniMax |
|---------|----------------|----------------|-------------|---------------|-------------|----------|-------------|---------|
| 文生图 | ✅ local+cloud | ✅ all models | ❌ | ✅ | ✅ Gen-4 image | ❌ | ✅ SD3.5 | ✅ |
| 图生图 | ✅ | ✅ | ❌ | ✅ | ✅ | ❌ | ✅ | ✅ |
| 多图生图 | ❌ | ✅ IP-Adapter | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| 单图编辑(inpaint) | ✅ | ✅ | ❌ | ✅ | ✅ | ✅ Modify | ✅ | ❌ |
| 双图编辑 | ❌ | ✅ Comfy nodes | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| 多图编辑 | ❌ | ✅ advanced | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| 文生视频 | ⚠️ via API | ✅ AnimateDiff | ✅ native | ✅ | ✅ | ✅ | ❌ | ✅ |
| 单图生视频 | ⚠️ via API | ✅ SVD/AnimateDiff | ✅ | ✅ | ✅ | ✅ | ✅ SVD/SV3D | ✅ |
| 首尾帧生视频 | ⚠️ via API | ❌ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| 多图参考生视频 | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ |
| 视频编辑 | ❌ | ✅ v2v | ✅ | ✅ | ✅ Restyle | ✅ v2v | ❌ | ✅ Extend |
| 参考图视频编辑 | ❌ | ❌ | ❌ | ❌ | ✅ MotionBrush | ✅ SceneIngred | ❌ | ❌ |
| 3D生成 | ⚠️ via API | ✅ TripoSR nodes | ❌ | ❌ | ❌ | ❌ | ✅ TripoSR | ❌ |
| 无限画布生图 | ❌ | ✅ Canvas Tab | ❌ | ❌ | ✅ Infinite | ✅ Expand | ❌ | ❌ |
| 无限画布编辑图 | ❌ | ✅ Canvas Edit | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| 无限画布生视频 | ❌ | ❌ | ❌ | ❌ | ✅ Infinite | ❌ | ❌ | ❌ |
| 无限画布短剧 | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| 无限画布绘本 | ❌ | ✅ storyboard | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| 图像放大 | ✅ 4x/8x | ✅ many nodes | ❌ | ❌ | ✅ | ✅ Upscale | ✅ | ❌ |
| 提示词优化 | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |

## Platform Detail: Parameters & Capabilities

### 1. ComfyUI (Open Source, Self-Hosted)
- **API**: `POST /prompt` — full workflow JSON, `GET /history/{id}`, `GET /queue`
- **Models**: SD1.5, SDXL, SD3, SD3.5, FLUX.1-dev/schnell, Flux Pro, all custom checkpoints
- **Video**: AnimateDiff (context/stride/loop/motion_scale), SVD (motion_bucket/noise_aug), ModelScope, VideoCrafter
- **3D**: TripoSR, Zero123++, Stable Zero123
- **ControlNet**: Canny/Depth/OpenPose/Scribble/MLSD/Normal/Lineart/SoftEdge/Segmentation/Tile/Inpaint/IP2P — with start/end %
- **IP-Adapter**: weight, start/end, image input
- **Samplers**: Euler/EulerA/DPM++2M/DPM++2MSDE/DPM++SDE/DDIM/LMS/PNDM/UniPC/LCM/TCD + schedulers (normal/karras/exponential/simple)
- **Canvas**: Canvas Tab for infinite outpainting (multi-pass directional expand)
- **Cost**: Free (self-hosted, GPU required)

### 2. Kling (可灵AI - klingai.com)
- **API Base**: `https://api.klingai.com`
- **Endpoints**: 
  - `POST /v1/videos/text2video` — txt2vid
  - `POST /v1/videos/image2video` — img2vid (with `image_tail` for first-last-frame)
  - `POST /v1/images/text2image` — txt2img
- **Models**: Kling 1.0, 1.5, 1.6, Pro, Standard
- **Key Params**: `single_loop`, `duration`(5/10s), `mode`("pro"/"standard"), `image_tail`, `cfg_scale`, `seed`, `camera_control`, `style`
- **Pricing**: ~10-20 credits/gen

### 3. Seedance/即梦 (ByteDance - seedance.com)
- **API Base**: `https://api.seedance.com/v1`
- **Endpoints**:
  - `POST /v1/video/generate` — main with `mode`: text2video/image2video/firstlast2video/multiimage2video
  - `POST /v1/image/generate`
  - `POST /v1/image/edit`
  - `POST /v1/video/edit`
- **Key Params**: `image`, `image_tail`, `reference_images[]`, `duration`, `motion_intensity`(1-10), `style_preset`, `aspect_ratio`
- **Models**: Seedance 1.0, 2.0

### 4. Runway Gen-4 (runwayml.com)
- **API Base**: `https://api.runwayml.com/v1`
- **Endpoints**:
  - `POST /v1/generations` — txt2vid
  - `POST /v1/generations/image-to-video`
  - `POST /v1/generations/video-to-video` — style transfer/restyle
  - `POST /v1/generations/infinite-canvas` — endless expansion
  - `POST /v1/generations/motion-brush` — selective motion
- **Models**: Gen-3 Alpha, Gen-3 Turbo, Gen-4, Gen-4 Turbo
- **Key Params**: `duration`(5-15s), `resolution`(720p/1080p/4K), `cfg_scale`(1-30), `motion`, `canvas_mode`, `brush_mask`, `upscale_factor`
- **Pricing**: $15-95/month subscription

### 5. Pika 2.0 (pika.art)
- **API Base**: `https://api.pika.art/v1`
- **Endpoints**:
  - `POST /v1/video/generate` — with `mode`: text2video/image2video/scene_ingredients
  - `POST /v1/video/edit` — v2v
  - `POST /v1/video/expand` — outpainting
  - `POST /v1/video/lipsync` — audio-driven
  - `POST /v1/video/sfx` — sound effects
- **Models**: Pika 1.5, 2.0, 2.0 Turbo
- **Key Params**: `scene_ingredients[{object,description,position}]`, `camera`(pan/zoom/orbit), `motion`(1-10), `strength`(0-1), `expand_direction`
- **Pricing**: $10-70/month

### 6. Stability AI (platform.stability.ai)
- **API Base**: `https://api.stability.ai/v2beta`
- **Endpoints**:
  - `POST /stable-image/generate/sd3` — SD3/3.5 txt2img
  - `POST /stable-image/edit/inpaint` / `/outpaint` / `/search-and-replace` / `/erase`
  - `POST /stable-image/upscale/creative`
  - `POST /stable-image/remove-background` / `/replace-background`
  - `POST /stable-image/control` — ControlNet
  - `POST /stable-video/generate` — SVD/SV3D
  - `POST /3d/generate` — TripoSR
- **Models**: SD3.5 Large/Turbo/Medium, SD3, SDXL, SVD/SV3D, TripoSR
- **Key Params**: `style_preset`(35+), `sampler`, `control_type`, `aspect_ratio`
- **Pricing**: $0.01-0.10/gen

### 7. MiniMax (minimax.com)
- **API Base**: `https://api.minimax.chat/v1`
- **Endpoints**: `POST /v1/video/text-to-video`, `/image-to-video`, `/extend`
- **Special**: Video extension (续写/延长) — unique feature
- **Models**: Video-01, Video-01-Pro, abab-video-1

### 8. OpenAI DALL-E 3 (api.openai.com)
- **Endpoint**: `POST /v1/images/generations`
- **Key Params**: `model`("dall-e-3"/"dall-e-2"), `quality`("standard"/"hd"), `size`(1024x1024/1024x1792), `style`("vivid"/"natural")
- **Pricing**: $0.04-0.12/image
- **Sora**: NOT publicly available as API (limited alpha only)

### 9. Midjourney (midjourney.com)
- **No REST API** — Discord-only. Not directly integrable.
- **Latest**: MJ V7, Niji 6 (anime)

### 10. HunyuanVideo/3D (Tencent)
- Open source on HuggingFace
- Self-host via Diffusers
- Cloud API via Tencent Cloud Gateway

### 11. Open Source Video Models
- **AnimateDiff**: txt2vid/v2v via SD, 16-80 frames, motion_module/scale/context/loop params
- **LTX Video**: txt2vid/img2vid, 25-121 frames, open source
- **Mochi 1**: txt2vid, 37-145 frames, open source via Genmo
- **SVD**: img2vid by Stability, 14-25 frames, motion_bucket_id(1-255)

### 12. 3D Generation
- **TripoSR**: img→3D via Stability API ($0.10/model) or self-host
- **Trellis** (Microsoft): txt/img→3D, open source
- **Zero123++**: img→multi-view→3D, open source
- **Hunyuan3D**: txt/img→3D, open source v2.0

## Common Integration Patterns

```
NanoBot Local Engine → diffuser_engine.py (StableDiffusionPipeline/FluxPipeline from diffusers)
NanoBot ComfyUI     → POST /prompt with full workflow JSON
NanoBot Cloud API   → unified_generation_service.py routes to Kling/Seedance/Doubao/OpenAI
```

## Key Gaps for NanoBot Factory

| Missing Feature | Integration Path | Effort | Notes |
|---------------|-----------------|--------|-------|
| Multi-image ref | IP-Adapter multi-image encoding fusion | 2-3d | Need custom ComfyUI workflow |
| Infinite canvas | Canvas Tab API + multi-pass outpainting | 3-5d | New engine needed |
| Video editing | Kling/Seedance/Pika edit APIs | 1-2d | API integration only |
| AnimateDiff | ComfyUI workflow parameter mapping | 1-2d | Workflow template |
| Short drama pipeline | Storyboard→multi-scene→composite | 5-7d | Complex pipeline |
| Multi-image 2 video | Seedance multiimage2video | 0.5d | API endpoint only |
