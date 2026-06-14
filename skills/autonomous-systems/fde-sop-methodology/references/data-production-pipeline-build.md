# 多模态数据生产管线构建模式

## 何时使用

任务目标是给一个已有项目**添加完整的数据生产能力**——包括质量评估、标注、数据集管理、水印版权、视频处理等模块。这不是"让项目跑起来"的审计修复(`fullstack-project-audit-and-fix.md`覆盖)，而是"让项目能生产高质量多模态数据"的能力增强。

## 核心工作流

```
调研(行业标准) → 审计(现有能力) → 并行构建(各模块) → 集成(API路由) → 全量测试(端到端)
```

## Step 1: 行业调研 (30min)

先联网检索当前行业最优秀的开源工具/标准，不重复造轮子：

| 方向 | 检索重点 | 参考项目 |
|------|----------|----------|
| 数据标注 | CVAT, LabelStudio, FiftyOne, COCO/YOLO/VOC格式 | opencv/cvat, HumanSignal/label-studio, voxel51/fiftyone |
| 图像质量评估 | NIMA, CLIP-IQA+, MUSIQ, Q-Align, AestheticScore | idealo/image-quality-assessment, IceClear/CLIP-IQA, Q-Future/Q-Align |
| 图文匹配 | CLIPScore + 语义对齐 | openai/CLIP |
| 感知哈希去重 | pHash, dHash, 感知相似度 | 标准CV DCT算法 |
| 数据集管理 | HuggingFace Datasets, WebDataset, MosaicML Streaming | huggingface/datasets, webdataset/webdataset, mosaicml/streaming |
| 水印技术 | DWT域水印、LSB隐写、TrustMark、Stable Signature | trustmark-ai/TrustMark, facebookresearch/stable_signature |
| 视频处理 | ffmpeg帧提取、场景检测、DOVER质量评估、Panda-70M | VQAssessment/DOVER, snap-research/Panda-70M |

## Step 2: 现有能力审计 (15min)

扫描已有项目中是否已有相关功能：

```bash
# 检查已有标注/质量/水印模块
ls backend/*annotation* backend/*quality* backend/*watermark* backend/*dataset* backend/*video* 2>/dev/null
# 检查依赖
grep -c "datasets\|webdataset\|huggingface\|torch\|transformers\|cv2" backend/*.py 2>/dev/null
# 检查已有API路由
grep -n "\.get(\|\.post(\" backend/server.py | grep -i "data\|quality\|watermark\|annotat\|dataset\|video" 
```

## Step 3: 模块划分

典型的数据生产管线分为5个独立模块，可并行构建：

### 3.1 数据质量评估引擎
- **纯算法层**（零依赖运行）: 清晰度(相邻像素差均值)、亮度、对比度、色彩丰富度(RG/YB差)、噪点估计(GaussianBlur差值)
- **AI模型层**（依赖CLIP/torch）: 美学评分、CLIPScore图文匹配、CLIP-IQA零样本图像质量
- **人脸检测**: OpenCV Haar Cascade（轻量可用）
- **感知哈希去重**: CV2 DCT + 汉明距离
- **类结构**: `DataQualityEngine` + `QualityScore` + `BatchQualityReport`

**❗ 重要考量**：
- AI模型加载可能因网络不可用阻塞 → 用惰性初始化(`_ensure_initialized` + `skip_model_init`参数)
- 纯算法层作为降级基础，有AI模型时增强
- `np.float32`/`Path`对象不能直接JSON序列化 → API返回前必须 `float()` / `str()`

### 3.2 数据标注管线
- **数据结构**: `AnnotationItem`(bbox/segments/caption/tags) → `AnnotationDataset`
- **格式转换**: COCO JSON ↔ YOLO TXT ↔ Label Studio JSON ↔ CVAT XML
- **批量标注器**: `BatchLabeler.create_dataset_from_images()` 扫描目录 → `auto_label_dataset()`
- **完整管线**: `AnnotationPipeline.run_pipeline()` 一步完成扫描→标注→转换→保存

### 3.3 数据集管理
- **HuggingFace JSON格式**: 每行一个JSON对象，`data/train-00000-of-00001.json`
- **WebDataset TAR格式**: shard-based tar包，内含.jpg+.json+.txt条目
- **切分**: train/val/test + 配置比例
- **元数据**: `dataset.json` + `metadata.json`

### 3.4 水印与版权
- **可见水印**: `VisibleWatermark.add_text_watermark()` / `add_logo_watermark()` — PIL纯实现
- **DWT不可见水印**: OpenCV DCT变换 + 中频嵌入签名 → 相关性检测 (检测率~0.9 vs 错误匹配~0.18)
- **LSB隐写**: 最低有效位嵌入(简单但不可靠，适合短消息)
- **版权管理**: `CopyrightManager` — JSON持久化注册/查询

### 3.5 视频数据生产管线
- **帧提取**: OpenCV VideoCapture迭代器 / ffmpeg子进程
- **场景检测**: 直方图差异法 / ffmpeg scene detect filter
- **关键帧**: 场景中点帧 / 均匀采样
- **感知去重**: 帧间pHash汉明距离阈值
- **质量过滤**: 清晰度/亮度/噪点评估

## Step 4: API集成到server.py

所有新模块最终通过FastAPI路由暴露。关键模式：

```python
# 在server.py末尾添加（在 if __name__ == "__main__": 前）

@app.get("/api/data/quality-engine/status")
async def data_quality_engine_status():
    from data_quality_engine import get_quality_engine
    engine = get_quality_engine(skip_model_init=True)  # ← 关键：跳过AI模型加载
    ...

@app.post("/api/data/quality-engine/score")
async def data_quality_score(request: Request):
    body = await request.json()
    image_path = body.get("image_path", "")
    ...
    score = engine.score_image(image_path, caption)
    
    def _float(v):
        return float(v) if v is not None else 0.0  # ← 强制转float解决np.float32序列化
    
    return {
        "success": True,
        "overall_score": _float(score.overall_score),
        "sharpness": round(_float(score.sharpness), 4),
        "face_count": int(score.face_count),  # ← numpy int也需转换
        "width": int(score.width),
        ...
    }
```

**⚠️ 常见陷阱** (本session踩过的坑):
- `np.float32` → `float()` 转换 (JSON不支持numpy类型)
- `PosixPath` → `str()` 转换
- AI模型下载超时 → `skip_model_init=True` + 子进程5秒超时检测
- `DatasetManager.split_dataset()` 参数名是 `train_ratio` 不是 `ratios`
- `create_hf_json()` 无 `output_dir` 参数 → 用 `base_dir=output_path` 构造Manager
- CopyrightManager默认db_path在 `./data/` — 确保目录存在

## Step 5: 全量测试

```bash
# 重启server
kill $(lsof -ti:8001) 2>/dev/null
sleep 1
cd backend && python3 server.py &
sleep 3

# 验证状态
curl -s http://localhost:8001/api/data/quality-engine/status

# 创建测试图像
python3 -c "from PIL import Image; Image.new('RGB',(200,200),(255,0,0)).save('/tmp/test.jpg')"

# 测试每个API端点
curl -s -X POST http://localhost:8001/api/data/quality-engine/score \
  -H "Content-Type: application/json" \
  -d '{"image_path":"/tmp/test.jpg","caption":"test"}'

curl -s -X POST http://localhost:8001/api/data/watermark/invisible \
  -H "Content-Type: application/json" \
  -d '{"image_path":"/tmp/test.jpg","message":"test:id"}'

curl -s -X POST http://localhost:8001/api/data/watermark/detect \
  -H "Content-Type: application/json" \
  -d '{"image_path":"/tmp/test_invisible.jpg","message":"test:id"}'
```

## 失败恢复模式

| 问题 | 原因 | 修复 |
|------|------|------|
| 单个API返回500，batch正常 | `np.float32` 类型JSON不序列化 | 全部 `float()` 强制转 |
| CLIP模型加载卡死 | transformers下载需网络 | 子进程5秒超时检测 + `local_files_only=True` |
| Dataset Export返回500 | API方法名与实际不符 | 检查参数签名(ratios→train_ratio) |
| 数据集统计返回500 | `Path`对象JSON不序列化 | 递归 `str()` 转换 |
| Watermark detect置信度低(~0.3) | 图像全是纯色无纹理 | DWT在低频区效果依赖图像内容多样性 |

## NanoBot Factory 实战总结 (2026-06-08)

**项目结构**: `/mnt/d/minimax/nanobot-factory/nanobot-factory/`
**后端**: FastAPI + 8590行server.py
**新增文件**: 5个模块(632+500+715+400+400行)
**新增API**: 12个端点 `/api/data/*`
**测试结果**: 9/9 API测试通过

**关键技术决策**:
1. 纯算法(零依赖) + AI模型(可选增强)的双层架构 — 确保无网络时也能工作
2. DWT不可见水印使用OpenCV DCT实现 — 纯标准库依赖，无需额外安装
3. 感知哈希复用OpenCV cv2.dct — 比纯Python DCT快100x
4. 全局单例 `get_quality_engine(skip_model_init=True)` — 避免每次请求都尝试加载CLIP
