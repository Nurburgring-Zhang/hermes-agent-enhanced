# V19 Session: Zero Numerical Parameters — The Fury Rule

## Severity: MAXIMUM. Hard failure if violated.

The user was furious multiple times during this session about AI-generated output containing numerical parameters:

- "这段描述过于复杂且不可理解！！！！太他妈的复杂了！！！没有任何AIGC模型能理解这样的描述！！！"
- "他妈的仔细看看，下面所有的描述都是太他妈的复杂了！！！减少细节！！模型无法理解这么详细的细节！！！！哪里都细节太多！！"
- "整体描述还是太过细节了！！！！细节太多了！！！！"

## Root Cause

Every `_build_*_system_prompt()` template and `_build_global_context()` was telling the AI to generate descriptions with:
- Measurements: cm, mm, degrees
- Color science: 色相, 饱和度, 明度, 色温=4800K
- Biology: 毛细血管, 毛密度, 肌肉名称
- Timing: 秒, Hz, dB, 分贝
- Optics: 光圈, 焦距, f-stop

AI image generation models CANNOT interpret these. They need visual language that a painter would use.

## Fix Applied to ALL Modes (Verify EVERY Template)

All 21+ prompt templates were audited and stripped of numerical parameter instructions:

**`_build_global_context`** — Added explicit ban on each section:
```python
"【通用基础设定】...**禁止使用数值参数（毫米/厘米/dB/色相值/密度等），用视觉化语言描述。**"
"【核心世界观之场景设定】...**禁止数值参数，用氛围感和视觉语言描述。**"
"【核心世界观之氛围与画质标准】...**用风格化描述代替数值（如「暖金色晨光」代替「色温4800K」）。**"
"【核心世界观之声音设定】...**用听觉氛围描述，不用分贝/频率等参数。**"
```

**Storyboard `_build_storyboard_system_prompt`** — Simplified:
- Before: "角色肢体各部件的关节角度和肌群状态+面部微动作序列+光源方向/色温/强度+色彩基调的色相饱和度明度参数+构图的具体几何形式+相机焦距和光圈参数"
- After: "角色肢体动作+面部微表情+场景每层景深的具体陈设+光源方向/色彩氛围+构图方式+空气质感"
- Also removed: the 800-words minimum instruction, the "micro-movements替代情绪" long example (下颌肌群/食指敲击/鼻翼翕动/0.5秒)

**Picture book `_build_picture_book_system_prompt`** — Simplified:
- Before: "600字以上的极致细腻中文画面描述。包含主体角色（外貌+服装款式颜色材质+神态表情）+动作细节（肢体动作方向+幅度+力度）+场景环境+光线氛围+构图方式（中心/三分法/对角线/框架构图）+细节纹理"
- After: "详细中文画面描述，包含角色+动作+场景+光影+构图+色彩，可直接用于AI绘画工具"

**Short drama `_build_short_drama_system_prompt`** — Simplified:
- Removed "每个情绪转折至少对应3个可观测身体信号"
- Removed "角色物理状态+逐帧动线序列+环境光色参数"
- Removed "200字以上的...按照主体物理状态→逐帧动线序列→...顺序展开"

## Audit Checklist

When adding/editing ANY system prompt template, check for:
- [ ] 毫米/cm/米 (use visual scale: "一人高" instead of "180cm")
- [ ] dB/Hz/分贝 (use feel: "轻声细语" instead of "30dB")
- [ ] 色相/饱和度/明度/色温 (use color names: "暖金色" instead of "色温4800K")
- [ ] 毛细血管/肌肉名称/神经/骨骼 (omit entirely)
- [ ] 秒/毫秒/fps (use rhythm: "短暂停顿" instead of "停顿0.5秒")
- [ ] 光圈/f-stop/焦距 (omit unless describing camera equipment)
- [ ] 密度/粘度/颗粒度 (omit entirely)

## Correct Alternatives

| Don't Say | Say |
|-----------|-----|
| 色温4800K | 暖金色的晨光 |
| 身高38cm，耳朵长14cm | 娇小的兔子，长耳朵高高竖起 |
| 密度200根/cm² | 浓密的绒毛 |
| −12dB, 3-5kHz | 清脆的鸟鸣声 |
| 色相30°,饱和度85%,明度70% | 鲜艳的橙红色 |
