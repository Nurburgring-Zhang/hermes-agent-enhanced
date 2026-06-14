# DWT 水印测试陷阱

## 问题

DWT (离散余弦变换域) 水印在小图像或纯色图上测试时置信度极低（如 100×100 纯色图只有 0.003）。

## 根因

DWT水印在中频DCT系数中嵌入签名序列。图像需要：
- **最小尺寸** ≥ 128px（推荐 256×256）—— 才有足够的频率空间容纳64位签名
- **纹理丰富度** —— 纯色/渐变图的中频系数接近0，嵌入的水印信号无法与噪声区分

## 正确测试方法

### 测试图构造

```python
from PIL import Image
import numpy as np

# 256x256 纹理图（正弦波叠加 —— 模拟真实图像频率分布）
img = Image.new('RGB', (256, 256), (128, 128, 128))
for x in range(256):
    for y in range(256):
        r = int(128 + 50 * np.sin(x / 10) + 30 * np.cos(y / 15))
        g = int(128 + 40 * np.cos(x / 12) + 20 * np.sin(y / 8))
        b = int(128 + 30 * np.sin((x + y) / 20))
        img.putpixel((x, y), (max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b))))
```

### 强度选择

```python
# strength < 0.5: 检测置信度不稳定
# strength 0.5-2.0: 最佳平衡（置信度 0.57-0.65）
# strength ≥ 5.0: 置信度可能反而略降（DCT系数饱和）
wm = InvisibleWatermark.embed_dwt(img, "test_message", strength=1.0)
```

### 预期结果

| 测试条件 | 置信度 | 备注 |
|---------|--------|------|
| 正确消息 + 纹理图 | **0.57 - 0.65** | 检测成功 |
| 错误消息 + 纹理图 | **-0.10 到 0.08** | 检测失败 |
| PNG保存后重新检测 | **~0.59** | 无损压缩不影响 |
| JPEG压缩(quality=95) | **~0.35-0.40** | 有损压缩衰减 |
| 正确消息 + 纯色图 | **~0.003** | ❌ 不可检测 |

### Fail-fast 断言

```python
r_correct = InvisibleWatermark.detect_dwt(img_wm, correct_msg)
r_wrong = InvisibleWatermark.detect_dwt(img_wm, wrong_msg)

# 正确测试必须验证区分度，不是绝对值
assert r_correct.confidence > r_wrong.confidence + 0.3, \
    f"Distinction too small: correct={r_correct.confidence:.4f} wrong={r_wrong.confidence:.4f}"
```

## 生产注意事项

- **JPEG压缩敏感**: 生产部署时考虑在检测前不做有损压缩
- **裁剪/缩放影响**: 水印在全图DCT域，裁剪会破坏同步
- **阈值设置**: API中的 `success=confidence > 0.3` 是合理的保守阈值
