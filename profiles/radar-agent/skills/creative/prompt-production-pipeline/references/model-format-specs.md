# 文生图模型提示词格式规格对照

> 不同模型的文本编码器架构不同，提示词格式规则完全不同。
> 将SD时代的(masterpiece, best quality, ((加重)))认知套用到非SD模型上——**输出质量会下降**。

## 模型架构分类

### A类：CLIP文本编码器（SD1.5/SDXL/SD3/FLUX.1）
- **编码器**: CLIP-L / CLIP-G / T5-XXL 组合
- **格式化标记**: 支持 `(word)`加重、`[word]`减轻
- **质量词**: 有效（masterpiece, best quality 等CLIP理解这些词）
- **中文**: ❌ 不支持（会导致质量下降）
- **推荐格式**: 英文逗号分隔的tag式，质量词前缀
- **代表模型**: SD1.5, SDXL, SD3, FLUX.1-dev

### B类：Qwen文本编码器（Z-Image-Turbo, Z-Image-Base, Qwen-Image, Z-Image）
- **编码器**: Qwen2.5 / Qwen3 4B
- **格式化标记**: ❌ 不兼容 `()` `[]` 加重语法（视为字面字符）
- **质量词**: ❌ 无效（masterpiece/best quality对Qwen架构无意义）
- **中文**: ✅ **原生支持**中英文自然语言混合
- **推荐格式**: 自然语言描述，逗号分隔要素，保留中文原文
- **注意**: Z-Image-Turbo 是蒸馏版，Z-Image-Base 是完整版。两者格式一致
- **代表模型**: Z-Image-Turbo, Z-Image-Base, Qwen-Image, Qwen2.5-VL Image Gen

### C类：Mistral文本编码器（FLUX.2 Dev, FLUX.2 Klein）
- **编码器**: Mistral 3 Small
- **格式化标记**: ❌ 不兼容 `()` `[]` 加重语法
- **质量词**: ❌ **无效且有害**（mistral将masterpiece视为字面词）
- **中文**: ❌ 不支持（需纯英文）
- **推荐格式**: 简洁英文自然语言描述
- **注意**: FLUX.2 Klein 4B 对超长prompt敏感，建议≤150词
- **代表模型**: FLUX.2 Dev, FLUX.2 Klein 4B

## 格式转换对照表

| 目标格式 | 移除中文 | 移除()加重 | 移除[]减轻 | 添加质量词 | 长度限制 |
|----------|---------|-----------|-----------|-----------|---------|
| 保持原样 | ✗ | ✗ | ✗ | ✗ | 无 |
| SD格式 | ✓ | ✗（保留） | ✗（保留） | ✓ | 无 |
| SDXL格式 | ✓ | ✗（保留） | ✗（保留） | ✓ | 无 |
| SD3格式 | ✓ | ✗（保留） | ✗（保留） | ✓ | 无 |
| FLUX.1格式 | ✓ | ✓ | ✓ | ✓ | 无 |
| **Z image** | **✗（保留中文）** | ✓ | ✓ | **✗（不要加）** | 无 |
| **Qwen image** | **✗（保留中文）** | ✓ | ✓ | **✗（不要加）** | 无 |
| **Flux 2** | **✓** | ✓ | ✓ | **✗（不要加）** | 无 |
| **Flux Klein** | **✓** | ✓ | ✓ | **✗（不要加）** | **≤150词** |

## 负面词适配

不同模型对负面词的敏感度完全不同：

| 目标格式 | 推荐负面词策略 | 示例 |
|----------|--------------|------|
| 保持原样/SD | 全量SD负面词 | ugly, deformed, bad anatomy, extra limbs... |
| Z image / Qwen image | 仅通用负面（精简） | blurry, low quality, watermark, text, logo |
| Flux 2 / Flux Klein | 仅通用负面（精简） | blurry, low quality, watermark, text, logo |

## 实用检查

```bash
# 检查prompt是否含中文
echo "$prompt" | grep -P '[\x{4e00}-\x{9fff}]'

# 检查prompt是否含()加重
echo "$prompt" | grep -P '\(\([^)]*\)\)'

# 检查prompt是否含masterpiece等质量词（对非SD模型无意义）
echo "$prompt" | grep -i -E 'masterpiece|best quality|high quality'
```

## 来源

- ComfyUI blueprints: `blueprints/Text to Image (Z-Image-Turbo).json`, `Text to Image (Flux.2 Dev).json`
- HuggingFace: ByteDance/Z-Image-Turbo, black-forest-labs/FLUX.2-dev, Qwen/Qwen2.5-VL
- GitHub: Comfy-Org/ComfyUI, black-forest-labs/flux2
