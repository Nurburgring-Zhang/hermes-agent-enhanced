# PromptLibraryNode V19 — Template "添肉" Refinement (2026-05-27)

格林主人要求: 每个模板的输出太干，要"添肉"，但禁止过度描述细节和数值参数。

## Core Problem

All templates' "画面描述" requirements were skeleton-level:
- "写清楚角色+场景+光线即可"
- "角色+动作+场景"
- "2-3句"

These instructions are too vague. The AI doesn't know WHAT to describe. The fix: give the AI **specific narrative dimensions** for each template type.

## Fix Pattern

Each template's format section was rewritten with:

1. **Specific narrative layers** — "围绕这三层展开：①角色在做什么 ②场景里发生了什么能推动剧情的事 ③光线和色彩在说什么情绪"
2. **Writing tone guidance** — "像给小说写段落，让读者眼睛里有画面" / "用孩子的眼睛看世界"
3. **Counter-examples for bad output** — "不是干巴巴的'他走了过去'，是'他穿过人群时肩膀擦过每个人的肩，却好像谁也没碰到'"
4. **"禁止参数" added as universal rule** — "不能写焦距mm、色温K、分辨率dpi等数值参数"

## Per-Template Dimension Changes

| Template | What was added |
|----------|----------------|
| 电影分镜 | 三层展开：动作→剧情推动→光线情绪 |
| 广告故事板 | 产品在场景中的存在方式(被使用/被注视/被烘托) |
| 动画故事板 | 动作比现实大、表情比现实夸张、可违反物理规律 |
| 漫画分镜 | 每格在页面中的角色(定场/推进/高潮/收尾) |
| MV故事板 | 歌词对位/反差/延展意境 + 音乐节点与画面切换咬合 |
| 教程步骤 | 操作前vs操作后对比 + 做错了怎么补救 |
| 短视频分镜 | 1-3秒怎么抓住人不让划走 + 心理时间快/慢 |
| 品牌故事板 | 品牌成为场景的一部分而非生硬植入 |
| 剧情分镜 | "你站在这场景里会看到什么、感觉到什么" |
| 绘本模式 | 用孩子的眼睛看世界 + 颜色形状给人的感受 |
| 短剧模式 | 有画面感——不是动作描述，是让读者能想象出画面 |
| 儿童格式一 | 光线和颜色让人开心还是紧张 |

## 总纲 Multi-Dimensional Setup

每个模式的总纲从单行参数列表改为 **3-4个维度的段落展开**:

```
# 【X模式总纲】
## 一、故事基调
[风格+色调+景别+运镜的融合描述]

## 二、角色与场景
[角色和环境的设定描述]

## 三、叙事结构/镜头节奏/内容结构
[镜头数/页数 + 节奏安排 + 叙事逻辑]

## 四、画面风格指引
[该模式特有的叙事语言和约束]
```

设计模式(7种)不改——它们输出的是SD/Flux提示词，不需要叙事总纲。
