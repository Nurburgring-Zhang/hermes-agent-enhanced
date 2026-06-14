# V18.11: World-Class Director-Level System Prompt Upgrade

**Date:** 2026-05-26
**Context:** User required upgrading all 4 output ports (storyboard, short drama, picture book, children's content) from "functionally correct" to "world-class director/creator level".

## Core Methodology

### Universal: 画面描述铁律 (Applied to Storyboard + Short Drama)

Four inviolable rules for scene description — no abstraction, only physical-world observations:

1. **禁止抽象词** — Forbidden: 悲伤、紧张、孤独、温暖、美丽. Only measurable physical descriptions.
2. **微动作替代情绪** — Every emotion turn needs ≥3 observable body signals. Not "sad look" but "jaw muscles contracting making jawline sharp, index finger tapping table at 2Hz, nostrils flaring three times then breath pausing for 0.5s".
3. **主体+动线+光色三要素** — Every frame must contain: character's current physical state + frame-by-frame movement path (A→B through C) + environmental light/color parameters (direction/temperature/intensity/focal length/depth of field).
4. **空间锚点法** — Minimum 1 spatial reference object per frame for AI to understand depth and proportion (e.g., "a fly resting 30cm left of the window frame", "a red flagpole stuck diagonally 2m from camera").

### Storyboard-Specific: Blake Snyder Beat Sheet

Map shots to professional beat types instead of generic labels:

| Beat | Position | Function |
|------|----------|----------|
| 开场定调 | Shot 1 | Visual tone, character-in-original-world |
| 催化事件 | ~10% | Trigger event, breaks equilibrium |
| 进入新世界 | ~12% | Visual threshold crossing |
| 中点转折 | ~55% | Major reversal, stakes double |
| 全线溃败 | ~75% | Lowest point |
| 灵魂黑夜 | ~75-85% | Brief reflective pause |
| 最终对决 | ~85-100% | Climax action |
| 闭环画面 | 100% | Visual bookend |

### Short Drama-Specific: Vertical Screen Visual Language

| Rule | Detail |
|------|--------|
| **黄金3秒三联序列** | 0-0.5s反物理/反常理视觉冲击 → 0.5-1.5s可完整理解的动作 → 1.5-3s开放式悬念. 3秒内完成微型正反合 |
| **15秒反转信息量对折** | 第一次反转揭示1个信息，第二次揭示2个相关联但矛盾的信息 |
| **情绪断崖法则** | 同一情绪状态不超过3秒，之后必须用更强烈视觉反转打断。通过身体动作幅度变化+物体空间比例变化+颜色饱和度色温突变+镜头稳定度突变传递 |
| **禁止画外音解释情绪** | 所有内心独白在后期剪掉。情绪仅通过可观测物理信号传递 |
| **竖屏9:16构图** | 上半画幅展示环境变化，下半画幅展示微表情。关键反转用垂直动线 |
| **超大面部特写** | 情绪引爆点前0.5秒必须出现从额头到下巴占画幅60%+的超大面部镜头 |

### Children's Content: Four Pillars (Applied to Picture Book + 4 Child Formats)

1. **皮克斯「四个箱子」法则** — Every story element must simultaneously satisfy: character's external goal (drawable action) + character's internal need (shown through physical action, never said) + scene's visual interest (color/shape/movement peak) + dialogue's subtext (children understand literal, adults understand subtext).

2. **五感锚定法** — Every new concept presented through ≥2 sensory channels (visual+tactile / auditory+olfactory / visual+auditory). Children "feel" the knowledge through character's physical experience. Never directly explain: not "water evaporates into vapor" but "the pot bubbles and burps, white steam puffs the plastic bag round as a balloon, fingers inside feel damp and warm".

3. **不说教公式** — Never state conclusions directly. Structure: Character A's wrong assumption → observable chaos (concrete consequences) → Character B solves it more cleverly → child realizes "oh, that's how it works" on their own.

4. **好奇心驱动20-7-3节奏** (for science content): First 20% shows counterintuitive visual phenomenon → 7-12% character asks open question (NEVER say the answer) → final 3% must have a hands-on visual demonstration where children feel they "discovered" the answer.

### Practical Prompt Engineering Rules

1. **Word count guidance**: Storyboard and short drama 画面描述 start at 200+ words (not 800+ — user reduced from 800 to 200 after observing total output length). The count in system prompt is MINIMUM guidance.
2. **Structure order for scene descriptions**: 主体当前物理状态 → 逐帧动线序列 → 环境光色参数 → 空间参照物 → 微动作序列 → 衣物/道具动态
3. **情绪色温标签** for 备注/用途标注: 高饱和暖光=欢乐/激动, 高对比侧光=冲突/紧张, 低饱和冷光=低谷/悲伤, 极端景深模糊=回忆/迷茫
4. **视觉桥接** for scene transitions between shots: 物体延续(同一支笔在前后场景出现) / 光影渐变(月光渐变到顶灯) / 镜面反射过渡

## Pitfalls

- **禁止比喻** — User explicitly rejected metaphors like "eyes carrying 2000 light-years of loneliness, fingertips smelling of cyborg-era machine oil." Only physical-world describable content. Abstract = rejected.
- **Seven-sensory writing over five** — Children's content uses visual+tactile+auditory+olfactory+proprioceptive (balance/gravity). Science content especially benefits from the "weight/heaviness" sense.
- **Don't over-apply the "four boxes" to simple children's content** — For 0-3 year olds, the internal need/subtext layers are less relevant. Use 五感锚定 and 不说教公式 primarily, with lighter 四箱子 application.
- **The 20-7-3 rhythm doesn't fit all content** — Only for science/科普 content. Story-based content uses standard 起承转合 or 四箱子.
