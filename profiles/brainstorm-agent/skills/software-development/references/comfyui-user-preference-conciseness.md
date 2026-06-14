# ComfyUI Template Conciseness: 格林主人 Rules

## Core Principle: AI Models Cannot Process Numerical Detail

AI image/video generation models (Stable Diffusion, Flux, DALL-E, Sora etc.) understand **visual language**, not **numerical parameters**. Writing "暖金色晨光" works; writing "色温4800K, 色相40°饱和度70%明度80%" does not.

## Banned Content in All Prompt Templates

### 🚫 Absolute Bans
- **Any numerical measurement**: 毫米/厘米/米/dB/Hz/kHz/秒/度/百分比/色值/像素/DPI
- **Biological/microscopic details**: 毛细血管, 毛密度, 肌肉名称(股二头肌/半腱肌), 器官名称, 细胞级描述
- **Physical parameters**: 色温(K), 色相(°), 饱和度(%), 明度(%), 焦距(mm), 光圈(f/), ISO
- **Quantified descriptors**: "每秒2次", "直径0.8cm", "长度25cm", "厚度5mm", "间隔4秒"
- **Overly granular enumeration**: "触须6根", "左右各3", "三瓣嘴", "每平方厘米200根"

### ✅ Allowed (Visual Language)
- **Color words**: 暖金色/橙红色/翠绿色/淡蓝色/粉红色 — use color names, not color values
- **Lighting**: 晨光/侧光/逆光/暖光/柔光/自然光 — use qualitative, not quantitative
- **Atmosphere**: 温暖/宁静/清新/梦幻/田园感 — emotional/atmospheric, not measured
- **Scale**: 巨大的/小巧的/细小的/蓬松的 — relative, not absolute
- **Texture**: 光滑/粗糙/毛绒/湿润/干裂 — tactile, not measured

## Template Writing Rules

### System Prompt Generation Instructions

When building system prompts for AI that generates content (prompts, storyboards, picture books, etc.):

1. **Never include "极致细腻" or "800字以上" or "600字以上"** — these trigger AI to dump excessive detail
2. **Limit per-frame/per-page descriptions**: "用5-10句话描述画面，写清楚角色+动作+场景+光线即可"
3. **Add explicit ban**: `**禁止写任何数值参数、器官名称、生物学细节、微观结构。画面描述不超过10句话。**`
4. **Character descriptions**: "只写可见的大特征（体型/毛色/服装/标志物）" — not microscopic features
5. **Scene descriptions**: "用一两句话描述场景氛围" — not detailed measurements

### 总纲 (Summary Header) Generation

The 总纲 block (通用设定与核心世界观) should follow:

```
【通用基础设定】— 每个角色2-3句：体型/毛色/服装/标志物。NO numbers.
【场景设定】— 1-2句氛围描述。NO dimensions/coordinates.
【氛围与画质标准】— 1句风格描述（如"暖金色晨光的田园感"）。NO parameters.
【声音设定】— 1句听觉感受。NO dB/frequency.
```

### Example: Before vs After

**BEFORE** (数值参数堆砌):
```
身高38cm（站立时耳朵最高点62cm），全身覆盖纯白色短毛（密度约200根/cm²），
耳廓内侧可见粉红色血管网，鼻尖直径0.8cm，胡须6根（左右各3，最长2cm）
```

**AFTER** (视觉化语言):
```
全身蓬松的白色绒毛，耳朵竖直笔挺，粉红色的小鼻头湿润发亮，
几根银白色的触须在鼻翼两侧微微颤动
```

## Auto-Verification Checklist

After writing a system prompt template, check:
- [ ] Contains NO `极致细腻` or `600字/800字以上`
- [ ] Contains a CONCISENESS constraint ("不超过X句话", "拒绝冗长")
- [ ] Character description template says "只写可见的大特征" without numerical parameters
- [ ] Scene description template says "氛围描述" without dimensions
- [ ] Voice/sound template says "听觉感受" without dB/Hz

## History

- **2026-05-27**: After THREE rounds of user correction ("细节太多!!! 模型无法理解这么详细的细节!!!"), all 6 templates (storyboard/picture book/short drama/child/ecommerce/poster/brand/PPT/logic diagram/exploded view/pipeline) were retrofitted with conciseness constraints. The `_build_global_context()` function became the universal enforcement point, appended to every mode's system prompt.
