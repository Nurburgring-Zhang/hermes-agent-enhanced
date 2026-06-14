# NanoBot Factory v3.0 升级日志 — 2026-06-09

6小时深度重构：从基础数据工具集升级为世界级多模态AI训练数据生产平台。

## 新增6个P0模块

P0-1 NSFW分类器 + 标准Aesthetic (对齐LAION/DataComp)
- data_nsfw_classifier.py — 4维NSFW(CLIP风格+YCbCr+FFT+轮廓)
- 阈值: aesthetic>=5.0/5.5/6.0, CLIP>=0.28, NSFW<0.5
- 测试: 257通过

P0-2 视频质量管线 (对齐Open-Sora/Panda-70M)
- data_video_quality.py (909行) — DOVER/运动/光流/视频CLIP
- data_video_dedup.py (508行) — spatial pHash + temporal
- 阈值: DOVER>=0.65, >=720p, >=2s, motion>=0.1
- 测试: 284通过

P0-3 MLLM管线 (LLaVA/ShareGPT4V/Qwen-VL/MMC4)
- data_mllm_pipeline.py (1166行) — 5格式
- 陷阱: sentence-transformers需离线env var

P0-4 编辑指令 + 人脸 + 分辨率桶 + Caption Dropout
- data_edit_pipeline.py, data_face_pipeline.py
- ResolutionBucket(FLUX/SDXL/SD15), CaptionDropout(10%)

P0-5 REST API 45路由
- 6新路由模块 + 17新端点

P0-6 项目清理+模块化
- 删除37垃圾文件, pyproject.toml, routes/11文件28路由
- infinite_canvas_engine重写: 10Agent+Goal Hive

## 关键经验
- 统一用 paraphrase-multilingual-MiniLM-L12-v2 + local_files_only=True
- CLIP embedding区分度不足 -> sharpness/colorfulness/contrast加权
- NSFW纯肤色对非人像无效 -> 加CLIP风格fallback
- MLLM测试断言不可过于严格
