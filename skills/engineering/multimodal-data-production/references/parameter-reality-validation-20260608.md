# 参数真实性验证协议 — NanoBot Factory 集成记录 (2026-06-08)

## 适用场景

当用户要求验证"所有功能都是真实运行、所有参数都是真实选择设置且真实生效"时，使用本验证协议。

## 四阶段穿透验证

### Phase 1: 参数控制变量法
每个参数构造**极端差异测试对**，验证差异方向正确：

```python
# 验证sharpness: 棋盘格 > 模糊棋盘格
img_sharp = Image.new('L', (64,64))  # 棋盘格
img_blur = img_sharp.filter(ImageFilter.GaussianBlur(3))

p_sharp = engine._analyze_image_properties(img_sharp)
p_blur = engine._analyze_image_properties(img_blur)
assert p_sharp['sharpness'] > p_blur['sharpness'], \
    f"sharpness should decrease: {p_sharp['sharpness']} vs {p_blur['sharpness']}"
```

常见的差异对：
| 参数 | A (高) | B (低) |
|------|--------|--------|
| sharpness | 棋盘格 (二值0/255交替, 2px周期) | GaussianBlur(3)处理后 |
| brightness | 纯白 (255,255,255) | 纯黑 (0,0,0) |
| contrast | 棋盘格 | 50%灰度 |
| colorfulness | RGB三通道差异大图 | 灰度图 |
| 图文匹配 | 图+正确描述 | 图+错误描述 |
| 感知哈希 | 同图两次hash | 不同图hash |

### Phase 2: 格式转换端到端验证
标注/数据集格式转换要做"归一化→像素→归一化"循环不变性验证：

```python
bbox = BoundingBox(x=0.1, y=0.2, width=0.5, height=0.3)

# COCO (像素坐标)
coco_bbox = [bbox.x*W, bbox.y*H, bbox.width*W, bbox.height*H]
assert abs(coco_bbox[0] - 10.0) < 0.01  # W=100

# YOLO (归一化坐标, 重新加载)
yolo_line = f"{cls_id} {bbox.x:.6f} {bbox.y:.6f} {bbox.width:.6f} {bbox.height:.6f}"
parts = yolo_line.split()
assert 0 <= float(parts[1]) <= 1 and 0 <= float(parts[2]) <= 1
```

### Phase 3: 水印检测二元区分度验证
正确消息 vs 错误消息的置信度必须有显著差异：

```python
r_correct = InvisibleWatermark.detect_dwt(img_wm, correct_msg)
r_wrong = InvisibleWatermark.detect_dwt(img_wm, wrong_msg)
assert r_correct.confidence - r_wrong.confidence > 0.3
```

### Phase 4: 数据集管理读回验证
导出的数据集必须能完整读回，数据不丢失：

```python
entries_orig = ...  # 原始条目
out = manager.create_hf_json('test', entries_orig)
entries_loaded = manager.load_hf_json(out)
assert len(entries_loaded) == len(entries_orig)
assert sum(e.width for e in entries_loaded) == sum(e.width for e in entries_orig)
```

## 已知真实bug

本会话中通过穿透验证发现的真实bug：

| Bug | 位置 | 代码 | 修复 |
|-----|------|------|------|
| `load_hf_json`读入metadata文件 | `data_dataset_manager.py:268` | 遍历所有.json文件没跳过`dataset_metadata.json` | 加 `if jf.name == "dataset_metadata.json": continue` |
| 数据集统计key命名 | `data_dataset_manager.py:118` | `compute_stats`返回key是`total_entries`不是`total` | 调用方改用`stats['total_entries']` |
| `split_dataset`参数名称 | `data_dataset_manager.py:572` | 签名是`(self, entries, train_ratio, val_ratio, test_ratio)` | 不能用`ratios=[0.8,0.1,0.1]`，必须用命名参数 |
| `create_hf_json`不接受output_path | `data_dataset_manager.py:200` | 路径由`self.base_dir`控制 | 初始化时传`DatasetManager(base_dir=path)` |
| numpy→JSON序列化崩溃 | server.py API路由 | `np.float32`值不能被`json.dumps`序列化 | 所有输出字段加`float()`/`int()`转换 |
| 全局单例模型加载跳过 | `data_quality_engine.py:657` | `skip_model_init=True`创建单例后，后续`skip_model_init=False`不触发重试 | 增加`force_reinit`参数，重置全局单例 |

## 验证脚本模板

```python
import requests, json

BASE = "http://localhost:8001"

def test_parameter_reality():
    results = {"passed": 0, "failed": 0}
    
    # 1. 质量引擎 — 不同图不同分
    r_white = requests.post(f"{BASE}/api/data/quality-engine/score",
        json={"image_path": "/tmp/white.jpg", "caption": "white"})
    r_check = requests.post(f"{BASE}/api/data/quality-engine/score",
        json={"image_path": "/tmp/checker.jpg", "caption": "checker"})
    
    assert r_check.json()["sharpness"] > r_white.json()["sharpness"], \
        "Sharpness should differ between checker and white"
    results["passed"] += 1
    
    # 2. 水印 — 不同位置不同像素
    # 3. DWT — 正确vs错误区分
    # 4. LSB — 写入读出一致
    # 5. 版权 — 持久化
    # 6. 数据集 — 读回一致性
    # ...
```
