# NanoBot Factory 多模态数据生产管线 — 实现记录 (2026-06-08)

## 项目背景
NanoBot Factory 是一个 FastAPI + Electron/Vite/React/TypeScript 桌面应用，原为 AI 内容生成平台(文生图/视频/3D)。本次增强将其扩展为完整的多模态数据生产平台。

## 新增文件

| 文件 | 路径 | 行数 | 作用 |
|------|------|------|------|
| data_quality_engine.py | `backend/` | ~676 | 图像质量评估引擎 |
| data_annotation_pipeline.py | `backend/` | ~500 | 数据标注管线+格式转换 |
| data_dataset_manager.py | `backend/` | ~715 | 数据集管理+HF/WebDataset导出 |
| data_video_pipeline.py | `backend/` | ~900 | 视频数据生产管线 |
| data_watermark.py | `backend/` | ~450 | 水印+版权引擎 |

## 修改文件

| 文件 | 修改内容 |
|------|---------|
| `backend/server.py` | 新增12个 `/api/data/*` 路由（约350行） |

## 环境依赖

已安装（无需额外操作）：
- `numpy 2.4.4`, `torch 2.12.0`, `torchvision 0.27.0`, `transformers 5.3.0`
- `sentence-transformers 5.2.3` (paraphrase-multilingual-MiniLM-L12-v2 已缓存)
- `opencv-python 4.13.0`, `Pillow 12.1.1`

未缓存但可用：
- `openai/clip-vit-base-patch32` — 需要网络首次下载，本环境网络不通

## 关键决策记录

1. **CLIP不可用 → sentence-transformers 回退**
   本地缓存了 `paraphrase-multilingual-MiniLM-L12-v2`。离线环境下设置 `TRANSFORMERS_OFFLINE=1` 和 `HF_HUB_OFFLINE=1`，然后用 `local_files_only=True` 加载。图文匹配效果：匹配caption CLIPScore ~72，不匹配 ~55（cosine similarity差值0.17）。

2. **延迟初始化 + 单例锁**
   质量引擎初始化耗时约10秒（sentence-transformers加载），首次API请求会触发。用 `skip_model_init=True` 跳过，用 `force_reinit=True` 强制重试。

3. **浮点类型转换**
   numpy数值(np.float32/64, np.floating, np.integer) 在FastAPI JSON序列化时报错。所有API返回值必须用 `float()`/`int()` 包裹。

4. **pHash用OpenCV DCT**
   手动DCT实现4重循环极慢。用 `cv2.dct()` 替代，从O(n⁴)降为O(n²)。

5. **缩放到64×64才分析属性**
   原始分辨率下 `_analyze_image_properties()` 极慢。统一resize到64×64后再计算。

6. **函数名匹配问题**
   `DatasetManager` API调用了不存在的 `import_from_directory()` → 应为 `create_from_image_dir()`。参数名 `ratios=` 不存在→ 应为 `train_ratio=, val_ratio=, test_ratio=`。返回值含 `PosixPath` 需 `str()` 转换。

## 已知限制

- `VideoPipeline` 需要真实视频文件才能测试（当前仅单元测试通过）
- `DOVER` 视频质量模型未集成（需额外下载权重）
- 批量标注需要 `auto_label_fn` 回调实现
