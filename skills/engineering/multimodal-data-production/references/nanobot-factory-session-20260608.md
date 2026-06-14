# NanoBot Factory Multimodal Data Pipeline — Session Detail (2026-06-08)

## Project Context

- Project: NanoBot Factory (FastAPI + React/Electron + Vite)
- Path: `/mnt/d/minimax/nanobot-factory/nanobot-factory/`
- Backend port 8001, Frontend port 5173
- GPU: RTX 4090 (CUDA available)

## Files Created in This Session

| File | Lines | Purpose |
|------|-------|---------|
| `backend/data_quality_engine.py` | 668 | 质量评估引擎: 图像属性分析/人脸检测/感知哈希去重/AI图文匹配 |
| `backend/data_annotation_pipeline.py` | 500+ | 标注管线: COCO/YOLO/LabelStudio/CVAT互转+批量标注 |
| `backend/data_watermark.py` | 415 | 水印引擎: 可见/不可见DWT/LSB水印+版权管理 |
| `backend/tests/test_quality_engine.py` | 39 tests | 质量引擎测试 |
| `backend/tests/test_annotation_pipeline.py` | 28 tests | 标注管线测试 |
| `backend/tests/test_dataset_manager.py` | 44 tests | 数据集管理测试 |
| `backend/tests/test_watermark.py` | 40 tests | 水印测试 |
| `backend/tests/test_data_api.py` | 17 tests | 数据API集成测试 |
| `backend/tests/conftest.py` | fixtures | 共享测试夹具 |

## AI Model Loading (Offline Environment)

The environment has no outbound internet access to huggingface.co. All model loading must use local cache.

**Available locally:**
- `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` (392MB cached)
- NOT available: `openai/clip-vit-base-patch32`, `openai/clip-vit-large-patch14`

**Critical env vars:**
```python
os.environ['TRANSFORMERS_OFFLINE'] = '1'
os.environ['HF_HUB_OFFLINE'] = '1'
```

**Loading time:** ~5.5s for SentenceTransformer (import 3.4s + load 2.1s)
**Encode time:** ~0.5s per image-text pair

## Common Bugs Found and Fixed

### np.float32 not JSON serializable
`score.sharpness` returns `np.float32` → `json.dumps` fails with `TypeError: Object of type float32 is not JSON serializable`.
**Fix:** Wrap in `float()`: `round(float(score.sharpness), 4)`

### PosixPath not JSON serializable
`DatasetManager.create_hf_json()` returns `PosixPath` object.
**Fix:** `str(out)` in API response

### get_quality_engine skip_model_init paradox
If first call uses `skip_model_init=True` (creates singleton with `_initialized=True`), subsequent `skip_model_init=False` does NOT re-trigger model loading because the singleton already exists and `_initialized` prevents re-init.
**Fix:** Added `force_reinit` parameter; also changed status endpoint to use `skip_model_init=False`

### DatasetManager split_dataset argument name
`split_dataset(entries, ratios=[0.8,0.1,0.1])` fails → method signature is `split_dataset(entries, train_ratio=0.8, val_ratio=0.1, test_ratio=0.1, shuffle=True, seed=42)`.

### create_hf_json no output_path parameter
`create_hf_json(name, entries)` uses `self.base_dir / name` as output path. The `output_path` must be set via `DatasetManager(base_dir=output_path)`.

## Audit Results

Full 14-dimension audit produced 104 findings (P0:3, P1:5, P2:56, P3:40).

**P0 fixes completed:**
- Test suite: pytest framework with 237 tests across 6 files
- pytest-timeout with 30s timeout per test
- pyproject.toml testpaths updated

**P1 fixes completed:**
- ~34/38 bare `except:` → specific exception types with logging
- Backup directories cleaned (3 directory trees)
- Dead test scripts removed (6 files)
- Path traversal fix in nanobot_scan_directory (os.path.realpath)
- Font path made cross-platform (Linux/macOS/Windows fallback)

**P2 fixes completed:**
- TypeScript strict mode enabled (8 checks: strict/noImplicitAny/strictNullChecks/...)
- pyproject.toml dependencies synchronized with requirements.txt
- .gitignore confirmed present

**P2 remaining:**
- infrastructure/storage.py — 14 bare excepts remaining (storage layer)
- server.py 8962 lines — split pending
- TypeScript strict errors — ~100+ type errors to fix after enabling strict mode
