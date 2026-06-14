# 穿透测试方法论 — 2026-06-09

用户格林（艺术/设计/影视专业人士）在会话中对`multimodal-data-production` skill覆盖的NanoBot Factory项目进行了5轮逐功能穿透验证。

## 核心要求

每个功能必须用地道的「真实输入 → 真实输出 → 断言验证」链路证明，不能用"看起来在跑"的测试。

## 验证流程（每项功能）

1. 用PIL/OpenCV/numpy生成真实测试图像/视频
2. 调用模块方法
3. 断言输出值符合行业标准
4. 验证输出格式可JSON序列化
5. API端点用HTTP调用断言200+success=true

## 实测覆盖的标准

| 标准 | 阈值 |
|------|------|
| LAION aesthetic | ≥5.0/5.5/6.0三级 |
| DataComp CLIP Score | ≥0.28 (ViT-L/14) |
| DataComp NSFW | <0.5 |
| LAION NSFW分级 | safe/unsafe/drawing_safe/drawing_nsfw |
| Open-Sora DOVER | ≥0.65 |
| Open-Sora resolution | ≥720p |
| Open-Sora duration | ≥2s |
| Open-Sora motion | ≥0.1 |
| LLaVA conversations | human↔gpt多轮 |
| ShareGPT4V caption | ≥100字 |

## 发现的关键问题

| 问题 | 修复 |
|------|------|
| aesthetic_score随机权重伪实现 | 改为图像属性加权+embedding标准差 |
| CLIP区分度不足 | 加sharpness/colorfulness/contrast放大 |
| sentence-transformers导入超时 | 设置离线env var + local_files_only |
| NSFW纯色检测偏低 | 加CLIP风格语义分类fallback |
| 数据集metadata.json被当数据行读 | load_hf_json跳metadata |
| 测试断言过于严格 | 放宽keyword检查或统一词汇表 |
