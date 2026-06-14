# V18.9: Universal Settings in Headers + Child Format Refinements + Rule File Sync

**Date:** 2026-05-26
**Session:** Full day of PromptLibraryNode refinements, culminating in universal settings in 总纲 and child content format tweaks.

## Universal Settings in All Ports 总纲

### The Core Change

All non-提示词 output ports now have a 【通用设定】+【输出格式】双层总纲 structure. The general settings (角色/形象/环境/场景/物品/背景/氛围/画面/声音/世界观) are **all in the header/总纲**, not scattered in system prompts.

### 故事板总纲 (`sb_header`)

```python
f"【故事板总定义】\n"
f"【通用设定】模式：{故事板模式}，共{故事板镜头数量}个镜头，风格：{故事板风格}。"
f"主题：{故事板主题 or '未指定'}。角色：{故事板角色描述 or '未指定'}。"
f"色彩基调：{故事板色彩基调}。景别偏好：{故事板常用景别}。运镜风格：{故事板运镜风格}。"
f"画质标准：电影级超写实/8K/胶片颗粒/变形宽银幕。"
f"氛围要求：根据风格匹配色调，光线描述含光源方向+强度+阴影效果。\n"
f"【输出格式】每个镜头包含：景别（7级好莱坞分类）、画面描述（主体动作/场景/光线/色彩/构图/情绪/纹理/视角/画质）、"
f"运镜方式（11种运镜+速度）、转场效果（8种转场）、备注（叙事功能+时长）。"
f"镜头交替使用远景/中景/近景/特写，避免连续3个同景别，保持180度法则，情绪曲线起承转合。\n\n"
```

### 绘本总纲 (`book_header`)

```python
f"【绘本总定义】\n"
f"【通用设定】共{绘本页数}页，风格：{绘本风格}，色调：{绘本色调}，"
f"年龄段：{绘本年龄段}，文字量：{绘本文字量}。"
f"主题：{绘本主题 or final_prompt or '童话森林探险'}。"
f"角色设定：所有角色外貌+服装+颜色在所有页面高度一致。"
f"场景设定：整体画面风格统一，明亮温暖，适合亲子朗读。"
f"画质标准：8K细腻/超写实/水彩质感/细节丰富。"
f"光线氛围：自然柔和光线，根据场景匹配光源方向和色彩倾向。\n"
f"【输出格式】每页包含：页码、画面描述（主体角色/动作细节/场景环境/光线氛围/色彩基调/构图/纹理/视角/画质）、"
f"绘本正文文案（适合亲子朗读）、视觉连续性提示（与前后页的关联）。"
f"叙事遵循起承转合，每2-3页设置视觉高潮，全景/中景/特写交替使用。\n\n"
```

### 短剧总纲 (`drama_header`) — Already Had This Pattern (V18.7)

No change needed — it already had `# 【总纲】` with 4 core worldview sections.

### 儿童内容总纲 (`child_header`)

```python
f"【儿童内容总定义】\n"
f"【通用设定】模式：{儿童内容模式}，主题：{儿童故事主题 or '小动物的冒险'}，"
f"共{儿童片段数}个片段/页，画风：{儿童画风}，年龄段：{儿童年龄段}。"
f"角色设定：角色外貌+服装+性格在所有内容中保持一致。"
f"场景设定：画面明亮温暖，色彩鲜艳饱和，适合儿童观看。"
f"氛围要求：语言简单温暖，情节积极向上，情绪曲线温和。"
f"画质标准：明亮清晰/色彩饱和/角色表情可爱/构图简洁。"
f"教育元素：每段内容需隐含正向教育目标（分享/勇敢/友善/探索/认知）。"
f"语言规则：短句、重复句式、拟声词，每句不超过10字。\n"
f"【输出格式】按照{儿童内容模式}的格式输出内容。\n\n"
```

### System Prompt 同步告知

Every system prompt added: **"注意：通用设定（角色/场景/氛围/画质等）已在总纲中提供，输出内容中只输出具体内容，不再重复通用设定。"**

Affected files:
- storyboard `_build_storyboard_system_prompt` ✅
- picture book `book_sys` ✅
- short drama `drama_sys` (already had this from V18.7) ✅
- child video1 `_build_child_video1_prompt` ✅
- child video2 `_build_child_video2_prompt` ✅
- child GIF `_build_child_gif_prompt` ✅
- child book `_build_child_book_prompt` ✅

## Child Content Format Refinements (All 4 modes)

### Format 1: 儿童视频格式一

**Old:** 直接以【片段N】开头
**New:** 先分**第一部分**、**第二部分**、**第三部分**、**第四部分**......每部分下分【片段1】、【片段2】...跨部分连续编号。旁白/对话改为可选（不是每个片段都有）。特效/TIPS改为可选（不是每个片段都有）。

### Format 2: 儿童视频格式二

**Old:** 直接分第一幕/第二幕/第三幕/第四幕（起承转合即幕）
**New:** 起承转合四大部分，每部分下再分第一幕、第二幕...TIPS改为可选（不是每幕都需要）。

### Format 3: 儿童微动视频/GIF格式

**Old:** 【旁白】→【画面】→【对话】→【动效描述】
**New:** 【旁白】→【画面】→【动效描述】（在画面下方，可选）→【对话】（可选，按需出现，不是每页都有）

### Format 4: 儿童绘本格式

**Old:** `"1. **画面描述**：..."` + `"2. **文字**：..."`（编号列表，分多行）
**New:** `"- **画面**：..."` + `"- **文字**：..."`（直接跟在标签后面，不分行。文字直接跟在【文字】标签后面，不换行）

## Rule File Sync (4 Files)

用户要求将复盘/自检/循环/高质量实现的规则写入**所有**底层设定文件，不仅是SOUL.md：

| File | Purpose | Status |
|------|---------|--------|
| `~/.hermes/SOUL.md` | Hermes core soul file | ✅ |
| `~/.hermes/AGENTS.md` | All AI agents (Claude Code/Copilot/Cline) | ✅ |
| `~/.hermes/CLAUDE.md` | Claude CLI specific | ✅ |
| `~/.hermes/.cursorrules` | Cursor/Windsurf IDE | ✅ |

All 4 files now have identical 规则2-7强化内容:
- R2: 主动自检+自动恢复+不等指令+不得终止任务
- R3: 阶段性复盘+确认无误才进下一阶段
- R4: 深度自检+严禁虚假/降级/占位
- R5: 完整结束后深度自检+商用级测试+循环
- R6: 强制循环至少3轮，不因"看起来可以了"就停止
- R7: 所有形式降级禁止+发现缺陷主动修复不等用户指出

## 格林主人 User Profile (从本次对话提炼)

### Communication Style
- 直接、指令明确，下达要求后期待立即执行不移问
- 出问题时直接质问"为什么没有主动做"
- 对质量问题极度敏感，不接受"看起来可以了"作为完成标准

### Quality Expectations (6 Iron Rules)
1. 每个阶段完成后必须阶段性复盘+历史回顾，确认无误才能进入下一阶段
2. 完整执行后必须全局复盘+深度自检+输出报告
3. 必须联网检索最新最佳方案做参考
4. 必须多次循环（至少3轮）：完善优化→极端详细代码审核→极端详细测试→再完善
5. 所有降级实现绝对禁止
6. 中断后必须主动自检恢复，不等指令，不得终止任务

### ComfyUI Node Work Preferences
- 所有端口必须完全独立不互斥（10个独立if块）
- 总纲必须包含完整通用设定（角色/场景/氛围/画质/声音），system prompt告知AI不再重复
- 画面描述和AI Prompt合并为一条完整描述
- 禁用英文Prompt（仅保留专业术语）
- 儿童内容4种格式严格遵循参考文件结构
- 每一行输出内容、每个维度的位置、什么合并什么删除，全部由格林主人亲自指定
- 总纲和system prompt是分离概念，改动时必须分别处理
- 每次迭代后必须执行完整复盘循环（R1→R2→R3→R4→R5）
- 所有修改后重启ComfyUI生效
