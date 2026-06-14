# Story-Sense Narrative Framework for AI Prompt Systems

## What this is
A class of knowledge about embedding world-class narrative theory (story arcs, emotional curves, plot structures, hooks, reversals) into LLM system prompts for content generation systems. Specifically designed for ComfyUI PromptLibraryNode but applicable to any system that generates narrative content via AI.

## Key Lessons from PromptLibraryNode Implementation (2026-06-01)

### Problem
25 story-sense templates were deployed but AI ignored them in output — stories remained flat and procedural ("do this → do that → done") without emotional arcs, reversals, or hooks.

### Root Cause 1: Abstract instructions don't work
Old template format was purely abstract:
```
情感曲线：低→升→降→高
```
AI can't translate "low→high" into concrete plot beats. It just writes what it knows (the fairy tale structure).

**Fix:** Each story-sense template must include a full **情节结构** with 7 numbered beats:
```
情节结构：
1. 开场：具体画面（被忽视的日常）
2. 触发事件：具体事件（机会/比赛/任务出现）
3. 第一波阻碍：具体场景（搞砸了被嘲笑）
4. 第二波阻碍（最低点）：具体时刻（最信任的人说放弃）
5. 转折：具体契机（无意中帮了谁）
6. 高潮：具体行动（用笨拙方式完成）
7. 闭环：具体心情（回家路上买颗糖）
```
Each beat must be concrete enough that the AI can map it to the user's story premise.

### Root Cause 2: Forcing emotion into every frame
Original instruction said "每个镜头体现情感" — this made AI scatter shallow emotional labels everywhere while the overall structure stayed flat.

**Fix:** Change instruction to "用总纲的情感曲线来设计整体情节的起伏——开场建立好奇，前段有小挫折，中段有真正的困境和最低点，之后出现转折，高潮解决问题，结尾温暖闭环。不要在每个分镜硬塞表情，而是让故事本身的走向有波折有悬念有反转。"

### Root Cause 3: Story-sense buried under format instructions
The story-sense template was placed at the start of system prompt, but immediately followed by "角色设定：你是一位世界顶级的导演..." which primed the AI to think "I'm a professional, I know how to tell stories" — overriding the novel template.

**Fix:** Add an explicit directive between story-sense and role-setting:
```
上述故事感总纲是本片的故事结构设计核心。你必须用该总纲的情感曲线来设计整体情节的起伏——...
```

### User Preferences Captured (格林主人)
- Story must have real emotional arc: curiosity → small挫折 → genuine困难 → lowest point →转折 →高潮 → warm closure
- Plot must have reversals and suspense, not linear "task completion"
- Emotion expressed at APPROPRIATE story moments, not forced into every frame
- Output must be gripping and attractive, not procedural
- 25 story-sense templates are expected, each with unique plot structure
- Each template must reference world-class storytelling theory

### Architecture Pattern
```
system_prompt = random_story_sense_template + 
                enforce_directive + 
                role_setting + 
                output_format + 
                rules + 
                constraints
```

### Story-Sense Library Maintenance
- Each entry has: 一句话核心 + 情节结构(7 beats) + 情感节奏
- Library file at `story_sense_library_complete.md` in PromptLibraryNode dir
- 25 entries, randomly selected per generation
- `_pick_story_sense()` method reads file, splits on `【故事感总纲` marker, filters header

### Pitfalls
- Don't put story-sense at END of system prompt — AI treats it as afterthought
- Don't use markdown formatting symbols in system prompt (`#` `##` `**` `- `) — AI mimics them in output
- Don't put multiple `{sense}` variable references — each call to `_pick_story_sense()` gets a DIFFERENT random template
- Don't skip the `sense = self._pick_story_sense()` variable assignment — calling inline in f-string repeats the call per reference
