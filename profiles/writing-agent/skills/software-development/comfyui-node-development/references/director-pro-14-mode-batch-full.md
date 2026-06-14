# DirectorPromptPro 14种非故事板模式批处理架构

## 新增模式（2026-06-03补齐）

在原有9种故事板批处理基础上，新增14种模式，实现23种模式全覆盖。

## 批处理函数

### 绘本模式 — `process_picture_book_batched()`

**参数**: topic, character_desc, env_desc, pages, style, color_tone, text_amount, age_group, api_url/api_key/model/temperature/max_tokens, ref_images, pick_story_sense_fn

**循环逻辑**: 逐页生成（pages次），每次system prompt包含:
- 故事感总纲（pick_story_sense_fn）
- 角色设定（世界顶级儿童绘本作家）
- 7维度输出格式模板
- 年龄段适配指南
- "请只输出第N页，只输出这一页"

**输出**: 每段 = 绘本总纲 + 【第N/pages页】 + LLM输出

### 短剧模式 — `process_short_drama_batched()`

**参数**: topic, character_desc, env_desc, shot_count, style, rhythm, camera_style, color_tone, api_url/api_key/model/temperature/max_tokens, ref_images, pick_story_sense_fn

**循环逻辑**: 逐镜头生成（shot_count次），system prompt包含:
- 故事感总纲
- 短剧7条铁律（精简版：禁止抽象词/竖屏9:16/时空锚定/180度不越轴/单镜凝固动作/风格统一/对话框绑定）
- 输出格式：镜头N：标题，脚本正文后景别/台词/运镜/备注

**输出**: 每段 = 短剧总纲 + 【镜头N/shot_count】 + LLM输出

### 儿童内容（4种） — `process_child_batched()`

**参数**: mode, topic, character_desc, env_desc, count, age_group, art_style, api_url/api_key/model/temperature/max_tokens, ref_images, pick_story_sense_fn

**循环逻辑**: 逐片段/逐页生成（count次），根据mode切换输出格式模板:

| mode | 格式描述 | 分段单位 |
|------|----------|----------|
| 儿童视频格式一 | 时间·空间/场景描述/动态/变化/旁白对话/特效 | 片段 |
| 儿童视频格式二 | 四幕结构(起承转合)/场景/画面/旁白/对话/TIPS | 片段 |
| 儿童微动视频/GIF | 核心动作/画面/动效循环 | 片段 |
| 儿童绘本格式 | 画面/文案/旁白对话/视觉连续性/构图景别 | 页 |

**通用system prompt包含**:
- 故事感总纲
- 年龄段适配描述（0-3低幼/3-6幼儿/6-9学龄）
- 画风描述（水彩插画/卡通动画/彩铅手绘/黏土定格/扁平矢量）
- 8大红线 + 不说教公式 + 情绪始终正向
- 年龄段文字量适配

**输出**: 每段 = mode总纲 + 【片段N/count】或【第N/count页】 + LLM输出

### 专业设计（8种） — `process_design_batched()`

**参数**: mode, topic, character_desc, env_desc, count, style, color_tone, product_material, product_color, shoot_angle, lighting_scheme, bg_type, api_url/api_key/model/temperature/max_tokens, ref_images, pick_story_sense_fn

**循环逻辑**: 逐张/逐组生成（count次）

**system prompt构建**:
用modes_design中的 *builder_map* 根据mode选取对应的 _build_*_prompt 函数（_build_ecommerce/poster/brand/ppt/logic_diagram/three_view/exploded_view/pipeline_diagram），传入所有参数构建一次系统提示词，然后在user_prompt中指定当前是第N张。

**输出**: 每段 = mode总纲 + 【设计N/count】 + LLM输出

## 通用架构模式

所有5个批处理函数遵循相同的模式：

```python
def process_xxx_batched(..., pick_story_sense_fn):
    # 1. 快速失败：无API或数量<1时返回空字符串
    if not api_url or count < 1:
        return ""
    
    # 2. 获取故事感总纲
    sense_text = pick_story_sense_fn() if pick_story_sense_fn else ""
    
    # 3. 自动补全未填信息（通过random_content模块）
    if not topic: topic = random_topic(mode)
    
    # 4. 构建总纲头（共享header，每段前面都带）
    header = f"{mode}总纲\n角色物品设定：...\n场景设定：...\n"
    
    # 5. 循环生成每个内容块
    segments = []
    for idx in range(count):
        # 构建system prompt（包含格式模板+约束）
        # 构建user prompt（指定当前是第几个）
        # 调用LLM
        # 组合：header + 块标记 + LLM输出
        segments.append(segment)
    
    # 6. 用===SEGMENT_BREAK===拼接
    return PromptSegmenter.join_outputs(segments)
```

## 与故事板批处理的差异

| 特性 | 故事板批处理 | 其他模式批处理 |
|------|-------------|---------------|
| 故事弧引擎 | ✅ StoryArc + ShotConstraints | ❌ 不使用（设计/绘本/短剧/儿童不需要景别追踪） |
| 连续性约束 | ✅ 每镜头后更新约束状态 | ❌ 无连续性追踪 |
| 格式模板 | 9种独立模板 | 每个模式自己的输出格式 |
| LLM调用次数 | shot_count次 | count次 |
