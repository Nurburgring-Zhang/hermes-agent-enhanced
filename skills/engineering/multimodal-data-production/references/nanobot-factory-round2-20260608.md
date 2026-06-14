# NanoBot Factory 多模态数据生产 — 第二轮扩展 (2026-06-08)

## 本次新增6个模块

| 文件 | 功能 |
|------|------|
| data_quality_advanced.py | 高级质量评分: Aesthetic/CLIP/NSFW/人脸/水印+Gap分析 |
| data_controlnet_pipeline.py | ControlNet条件图: Canny/Depth/Pose/Seg |
| data_dense_caption.py | 密集描述: Full/Short/Region/BLIP-3/ShareGPT4V |
| data_video_caption.py | 视频Caption: 逐帧/叙事/分段/Open-Sora |
| data_multimodal_benchmark.py | 评测数据: MMMU/VBench/VQA/LLaVA |

## 关键知识

1. AdvancedQualityScorer.aesthetic_score 原用随机权重，改为图像属性+embedding方差加权
2. comprehensive_report 返回 AdvancedQualityProfile dataclass, 字段: aesthetic/clip_score/nsfw_score/face_quality/watermark_detect/score_mean
3. 评分区分度验证: 精细艺术品 7.22 vs 退化 4.09 vs 纯白 1.02 (跨度0.34)
4. NSFW检测: 肤色 1.00 vs 自然 0.20 (有效区分)

## 参数真实性6步协议

1. 评分区分度: 不同图像跨度>=0.25
2. 标注互转: COCO/YOLO/LS/CVAT坐标验证
3. 水印二元: correct>wrong, PNG保存后仍可检测
4. 数据集: HF JSON读写一致, WebDataset正确
5. ControlNet: 4种条件图非纯色
6. Benchmark: MMMU/LLaVA格式验证

## 覆盖数据类型

文生图/图生图/ControlNet条件/视频/评测/微调/标注/筛选/水印/视频Caption
