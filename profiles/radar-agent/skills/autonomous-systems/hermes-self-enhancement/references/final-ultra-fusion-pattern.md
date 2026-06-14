# FinalUltraFusion — ComfyUI超分辨率节点开发实战模式
## 源文件: `upscale/FinalUltraFusion/__init__.py` (1119行, 48KB)
## 2026-05-19 格林主人会话实战验证

### 项目概述
逆向分析3个现有超分节点(ZC-Upscale-v1.3.0-ultra_minimax / ZC_Upscale GLM5 / ZC_Upscale_Ultimate_kimi)，
提取总共20+种超分辨率算法的核心架构，融合成一个最终版节点。

### 架构设计

```
FinalUltraFusion/
  └── __init__.py (1119行, 单文件节点)
        ├── 工具函数(tensor2pil/pil2tensor/tensor格式转换)
        ├── 基础模块(LayerNorm/SimpleGate/UpsampleBlock/Mlp)
        ├── 注意力机制家族(9种)
        │   ├── ChannelAttention — SE-Net风格
        │   ├── EnhancedChannelAttention — ECA-Net风格(1D卷积避免降维)
        │   ├── SpatialAttention — 平均+最大池化融合
        │   ├── WindowAttention — SwinIR风格(相对位置偏置)
        │   ├── OverlapCrossAttention — HAT风格(多尺度窗口融合)
        │   ├── ChannelAttentionLayer — DAT风格(归一化+温度缩放)
        │   ├── SpatialAttentionLayer — DAT风格(窗口划分+温度缩放)
        │   ├── PixelAttention — 逐像素加权
        │   └── NonLocalAttention — 长距离依赖建模
        ├── 高频增强模块
        │   ├── HighPassFilter(3x3/5x5拉普拉斯变体)
        │   ├── MultiScaleHighPassFilter(多尺度融合)
        │   ├── SpatialGateFeedForward(SGFN)
        │   └── RRDB/RDB(Real-ESRGAN核心)
        ├── 9种放大算法
        │   ├── UltraSR(终极融合架构: 6种注意力并行+RRDB前端+Transformer后端)
        │   ├── DAT(双聚合Transformer)
        │   ├── MDAT(多尺度双聚合)
        │   ├── HAT(混合注意力Transformer)
        │   ├── SwinIR(窗口注意力)
        │   ├── EDSR(残差通道43.1M参数)
        │   ├── RCAN(残差通道注意力29.1M参数)
        │   ├── TaylorEIUM(泰勒展开式)
        │   └── BirdSR(双向奖励引导)
        ├── 图像调整(亮度/对比度/色温/色调/HSL/伽马/鲜艳度)
        ├── 分块处理(tiled_process, 自适应tiling+权重融合)
        ├── 算法调度器(get_algorithm, 全局缓存)
        └── ComfyUI节点注册(NODE_CLASS_MAPPINGS/FinalUltraFusion)
```

### 测试结果(两轮审核+测试)

| 轮次 | 测试数 | 通过 | 通过率 | 修复问题 |
|------|--------|------|--------|----------|
| R1审核 | 36项 | 34 | 94% | `except:` → `except Exception:`, SwinIRBlock窗口划分修复, OUTPUT_NODE补全 |
| R1测试 | 75项 | 73 | 97.3% | meshgrid兼容性修复 |
| R2测试 | 79项 | 79 | **100%** | 全部通过 |

### PyTorch Module开发陷阱

#### 1. `nonlocal`是Python保留字
```python
# ❌ 错误
self.nonlocal = NonLocalAttention(dim)
# ✅ 正确
self.nl_attn = NonLocalAttention(dim)
```

#### 2. `torch.meshgrid` 在新旧版PyTorch签名不一致
```python
# PyTorch <2.0 (位置参数)
coords = torch.stack(torch.meshgrid([a, b]))  # 列表参数

# PyTorch >=2.0 (关键字参数)
coords = torch.stack(torch.meshgrid(a, b, indexing='ij'))  # 变长参数
```

#### 3. SwinIR窗口注意力必须配合window partition/reverse
SwinIR的WindowAttention接收窗口化的输入(B*nW, ws*ws, C)，不能在全局特征图上直接调用。
```python
# 窗口划分
xw = x.reshape(b, c, hp//ws, ws, wp//ws, ws)
xw = xw.permute(0, 2, 4, 3, 5, 1).reshape(-1, ws*ws, c)
# 注意力
xw = xw + self.attn(self.norm1(xw))
# 窗口还原
xr = xw.reshape(b, hp//ws, wp//ws, ws, ws, c)
xr = xr.permute(0, 5, 1, 3, 2, 4).reshape(b, c, hp, wp)
```

#### 4. 分块处理必须用权重融合消除接缝
```python
# 创建渐变权重(靠近边缘权重小)
fs = int(overlap * scale // 2)
for k in range(fs):
    wt[:,:,k,:] *= (k+1)/fs  # 上边渐变
    wt[:,:,th-1-k,:] *= (k+1)/fs  # 下边渐变
# 加权求和
output += upscaled * wt
weight += wt
output = output / (weight + 1e-8)  # 归一化
```

#### 5. model.eval() 被误判为eval()
代码审核脚本检查 `eval(` 时会把 `model.eval()` 误判为危险调用。
修复: 在审核脚本中增加 `code.count('eval(') == code.count('model.eval')` 判断。

### 算法调度器缓存模式

```python
_algorithm_instances = {}

def get_algorithm(name, scale, device):
    key = f"{name}_{scale}_{device}"
    if key not in _algorithm_instances:
        model = create_model(name, scale)
        model.to(device).eval()
        _algorithm_instances[key] = model
    return _algorithm_instances[key]
```
- 相同name+scale+device → 命中缓存
- 不同scale → 不同实例(不同网络结构)
- 不同device → 不同实例(模型移动到不同设备)

### 测试覆盖必须维度

| 测试维度 | 本节点覆盖 | 测试方法 |
|----------|-----------|----------|
| 算法forward | 9/9 ✅ | 输入1x3x64x64 → 验证输出1x3x256x256 |
| 注意力机制 | 9/9 ✅ | 输入1x64x16x16 → 验证输出shape一致 |
| 增强模块 | 6/6 ✅ | 输入1x64x32x32 → 验证输出shape一致 |
| Tensor管线 | 6/6 ✅ | PIL→tensor(NHWC)→nchw→nhwc→PIL完整循环 |
| 图像调整 | 11/11 ✅ | 8种参数单独+全组合, 验证输出同尺寸 |
| 基础放大 | 4/4 ✅ | lanczos/bicubic/bilinear/nearest 100x100→400x400 |
| 分块处理 | 2/2 ✅ | 128x128→512x512 + 不同tile_size |
| 算法调度 | 11/11 ✅ | 9种算法加载+缓存命中+缓存隔离 |
| ComfyUI接口 | 11/11 ✅ | INPUT_TYPES/RETURN_TYPES/CATEGORY/FUNCTION/OUTPUT_NODE |
| 端到端集成 | 2/2 ✅ | Basic:Lanczos 2x + Basic:Bicubic 4x+tiling+调整 |
