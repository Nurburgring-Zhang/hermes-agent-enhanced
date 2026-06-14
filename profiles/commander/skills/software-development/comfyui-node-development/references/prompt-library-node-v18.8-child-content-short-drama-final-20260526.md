# PromptLibraryNode V18.8 — Child Content Module + Short Drama Chapter Structure Finalization

**Date:** 2026-05-26
**Session:** Short drama chapter-style narrative finalization, child content module (4 modes)

## V18.8 Changes

### 1. Short Drama — Chapter-Style Narrative (Final)

**Output structure now guaranteed:**
```
# 【总纲】
**通用设定与核心世界观**
【通用基础设定】...角色设定（从用户参数注入）
【核心世界观之场景通用设定】...场景/时间/光线/天气/环境细节
【核心世界观之氛围与画质标准】...画质/色彩/光线规则（模式自动匹配5种风格色调）
【核心世界观之声音设定】...同期声/音效

# 【镜头1】
**镜头1的分镜脚本1：标题篇**
（200字以上自然语言画面描述，深度融合全部画面元素）

**景别**：[Medium Wide Shot中全景]
**台词/旁白**：角色名（语气）："对话内容"
**运镜方式**：[固定镜头] 中速，俯拍角度
**用途标注**：铺垫 + 情绪：沮丧/无奈 / 2级 / 建议时长：3秒 + 转场：叠化
```

**Key structural rules:**
1. **总纲**置于所有镜头之前，包含完整的角色/场景/画质/声音四板块
2. **每个镜头**直接从分镜脚本开始，不重复输出通用设定（system prompt明确告知AI该部分已置于总纲）
3. **每个分镜脚本**：
   - 粗体标题 `**镜头N的分镜脚本M：标题篇**`
   - 200字以上自然语言画面描述（深度融合：拍摄方式+角色动作+表情+服装+场景+光线+色彩+构图+情绪+特效+画质+视角+竖屏）
   - 脚本正文结束后，**单独输出4个字段**：`**景别**` / `**台词/旁白**` / `**运镜方式**` / `**用途标注**`
4. **景别**使用7级好莱坞分类全称+中文译名，不简化
5. **运镜方式**含11种运镜+速度+角度（平视/俯视/仰视/过肩/鸟瞰）
6. **用途标注**含：叙事功能+情绪标记+情绪强度等级(1-5级)+建议时长(秒)+转场效果(硬切/叠化/淡入淡出/划像/匹配剪辑/白闪/黑场)

### 2. Child Content Module — New 6th Port "儿童提示词"

**Node UI position:** Bottom of the node (after short drama parameters)
**Port:** 6th output (儿童提示词)

**Parameters:**
| Parameter | Type | Default | Choices |
|-----------|------|---------|---------|
| 输出儿童内容 | BOOLEAN | False | - |
| 儿童内容模式 | DROPDOWN | 儿童视频格式一 | 儿童视频格式一/儿童视频格式二/儿童微动视频/GIF格式/儿童绘本格式 |
| 儿童故事主题 | STRING(multiline) | "" | - |
| 儿童角色描述 | STRING(multiline) | "" | - |
| 儿童片段数 | INT | 8 (3-30) | - |
| 儿童年龄段 | DROPDOWN | 3-6岁幼儿 | 0-3岁低幼/3-6岁幼儿/6-9岁学龄 |
| 儿童画风 | DROPDOWN | 卡通动画 | 水彩插画/卡通动画/彩铅手绘/黏土定格/扁平矢量 |

**4 Output Formats:**

| Mode | Reference From | Structure |
|------|---------------|-----------|
| 儿童视频格式一 | "糖豆和皮皮" style | 【片段N】→ 场景描述 → 【动态】→ 【旁白/对话】→ 【特效/TIPS】 |
| 儿童视频格式二 | "蛇下雨天会干嘛" style | 第X幕：标题 → 角色介绍(仅第一幕) → 【场景】→ 画面描述 → 对话 → 旁白 → TIPS |
| 儿童微动视频/GIF格式 | "草船借箭" style | 第X页 → 【旁白】→ 【画面】→ 【对话】→ 【动效描述】 |
| 儿童绘本格式 | "鲸鱼科普" style | 第X页 → 画面描述 → 文字 |

**5 Art Styles:**
- 水彩插画: 水彩晕染，柔和通透，边缘自然过渡
- 卡通动画: 明亮卡通，粗轮廓线，纯色填充，表情夸张可爱
- 彩铅手绘: 彩色铅笔纹理，线条有铅笔质感，色彩层叠柔和
- 黏土定格: 黏土动画质感，立体感强，材质真实
- 扁平矢量: 简洁几何形状，纯色块面，现代清新

**Age groups (3 levels with detailed guidance in system prompt):**
- 0-3岁低幼: 极简画面+5-15字文字+重复句式+认知主题
- 3-6岁幼儿: 丰富画面+10-30字文字+简单情节+教育提示
- 6-9岁学龄: 细节丰富+20-50字文字+起承转合+科普知识

### 3. New Methods Added

```python
_build_child_system_prompt(self, mode, style, age_group)  # Router
_build_child_video1_prompt(self, style_text, age_text)     # Format 1 system prompt
_build_child_video2_prompt(self, style_text, age_text)     # Format 2 system prompt
_build_child_gif_prompt(self, style_text, age_text)        # GIF format system prompt
_build_child_book_prompt(self, style_text, age_text)       # Book format system prompt
_get_age_range_for_mode(self, age_text)                    # Duration helper
```

### 4. All Returns Now 6-Element

All `return` statements and `_error_result()` were upgraded to 6-element tuples to match the new 6th port. Every error/early-return path must include `child_prompt=""`.

### 5. Short Drama 画面描述 800→200 words

User explicitly requested reduction from 800 to 200 after observing total output length. System prompt updated accordingly.

## Design Patterns from This Session

### Pattern A: Header = Total Definition + All Settings

When the user provides a detailed reference example showing the EXACT structure they want, replicate the STRUCTURE (heading hierarchy, field order, section labels) but NEVER the CONTENT. Fill content based on user's parameters.

### Pattern B: Separate 4 Fields After Script Body

Moving 景别/台词/运镜/用途标注 OUT of the script body and into standalone fields after it is better for AI video generation pipelines — the 200-word body is the T2V/T2I prompt, the 4 fields are scheduling metadata. Don't merge metadata into prompts.

### Pattern C: Child Content = Age-Specific + Style-Specific + Mode-Specific

The child content module demonstrates a clean pattern for multi-mode generation:
1. A router method (_build_child_system_prompt) dispatches by mode
2. Each mode has its own _build method with unique structure
3. Common parameters (age/art style) are mapped into descriptive text and injected per-mode
4. Age descriptions are comprehensive (sentence-level, not label-level)
5. Art style descriptions are visual (how it looks, not label)
