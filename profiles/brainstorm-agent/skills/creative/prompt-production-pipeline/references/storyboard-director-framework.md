# Storyboard Prompt Engineering: 4-Step Director Framework

Professional storyboard/director-level prompt structure imported from reference trailer director system. Used by the V17.0 PromptLibraryNode storyboard generator's 9 modes.

## Core Structure: 4 Steps

```
1. 场景分解 (Scene Breakdown)
2. 故事弧线 (Story Arc)  
3. 电影手法 (Cinematography Plan)
4. 关键帧序列 (Key Frame List)
```

Each step has a non-negotiable rules section, consistent with professional film/trailer production.

## Step 1: Scene Breakdown

### Must Cover
- **Subject list**: Each key subject (A/B/C...) with: clothing/materials/style/relative position/orientation/current action
- **Environment & Lighting**: indoor/outdoor, spatial layout, background elements, light direction (hard/soft), key/fill/rim lights, 3-8 atmosphere keywords
- **Visual anchors**: 3-6 features that MUST stay identical across ALL frames (color palette, signature props, main light direction, weather/fog/rain, texture grain)

### Example
```
主体：一位身穿深灰色长风衣的中年男性侦探（A），头戴软呢帽，面容疲惫但眼神锐利。
环境与照明：室外深夜，老城区砖石巷道，地面湿漉反射灯光。主光源来自A身后的路灯（暖黄硬光），前方暗巷（冷调补光）。
氛围关键词：悬疑、孤寂、潮湿、压抑、怀旧、冷峻
视觉锚点：深灰风衣、软呢帽、昏黄路灯、雨幕、砖石墙面、冷蓝色夜雾
```

## Step 2: Story Arc

### Format
- **Theme**: One sentence
- **Logline**: One punchy trailer-style sentence
- **Emotional arc**: 4 stages — Setup → Build → Twist → Climax, one sentence each

### Example
```
Theme：一个孤独侦探在查案途中驻足沉思。
梗概：雨夜。巷口。一盏灯。一个男人。他要去的地方没有回头路。
情感弧线：铺垫——疲惫中的习惯性停顿；构建——望向暗巷时的决意；转折——帽檐阴影下的眼神变化；高潮——迈入暗黑前的最后回望。
```

## Step 3: Cinematography Plan

### Components
- **Shot progression strategy**: How to move from wide to tight (or reverse) to serve the story
- **Camera movement plan**: Dolly/push/pull/track/truck/pan/tilt/handheld/gimbal — with WHY
- **Focal length roadmap**: 18/24/35/50/85/100/135mm + depth-of-field preference (shallow/medium/deep)
- **Lighting & color**: Contrast ratio, dominant palette, texture rendering priority

### Example Progression
```
ELS→LS→MLS→MS→MCU→CU→ECU→low angle→bird's eye
(9-shot grid for 3×3 剧情分镜 mode)
```

### Format per shot
```
[Shot type — ELS/LS/MLS/MS/MCU/CU/ECU/low angle/high angle/overhead/POV]
Composition: subject position, fg/mg/bg, gaze direction, leading lines
Action/rhythm: what happens (simple, executable)
Camera: height, angle, movement (e.g., slow 5% dolly-in/1m lateral track/handheld micro-shake)
Focal length/depth: xxmm, DoF (shallow/medium/deep), focus target
Lighting & color: consistent, note highlight/shadow emphasis
Sound/atmosphere (optional): one-line sound cue
```

## Step 4: Frame-by-Frame List

### Required Shot Mix (copy-paste rule)
- 1 establishing wide shot (ELS)
- 1 intimate close-up (CU)
- 1 extreme detail (ECU)
- 1 power angle (low or high angle)
- Remaining shots vary depending on story needs

### Continuity Rules (Hard Requirements)
- Same subject across ALL frames
- Same clothing/hairstyle/props
- Same lighting conditions and color grading
- Same environment and weather
- Correct photorealism and cinematic depth-of-field per shot
- Photo-grade texture details
- Cinematic camera behavior and focal length accuracy
- **NO new subjects** — only what already exists in the story summary

## 9-Shot Grid Structure (for 剧情分镜 mode)

```
Row 1 — Establish the World
  Frame 1: ELS (Extreme Long Shot) — full environment, subject is small
  Frame 2: LS (Long Shot) — subject full body, naturally placed
  Frame 3: MLS (Medium Long Shot / American shot) — knees up

Row 2 — Core Coverage
  Frame 4: MS (Medium Shot) — waist up, key action/attitude
  Frame 5: MCU (Medium Close-Up) — chest up, emotion/micro-interaction
  Frame 6: CU (Close-Up) — face tight, cinematic DoF

Row 3 — Details & Angles
  Frame 7: ECU (Extreme Close-Up) — eyes/hands/symbolic object/texture
  Frame 8: Low angle (worm's eye) — dramatic/heroic/menacing
  Frame 9: High angle (bird's eye) — spatial clarity/vulnerability/panorama
```

## 8 Background Modes

| Mode | Role | Section 1 (Breakdown) | Section 2 (Story) | Section 3 (Cinematography) | Section 4 (Output) |
|------|------|----------------------|-------------------|---------------------------|-------------------|
| 电影分镜 | Trailer director | Subject + environment + anchors | Theme + logline + 4-stage arc | Shot progression + camera plan + focal length + lighting | ELS→ECU per-frame, 9-12 shots |
| 广告故事板 | Ad director | Product + environment + visual anchors | Core message + emotional tone + 5-beat rhythm | Product-oriented progression + studio lighting | Per-frame with brand element positions |
| 动画故事板 | Animation director | Character + spatial layout + lighting | Theme + 4-beat emotional arc | Animation physics + color script per act | Per-frame with transition type |
| 漫画分镜 | Manga artist | Characters + setting + atmosphere | Theme + 4-part rhythm (起承转合) | Panel layout + Z-line guide + white space | Per-panel with dialog bubbles |
| MV故事板 | MV director | Performers + stage/venue + visual style | Song structure mapped + emotional color per section | Camera sync to beat + lighting color changes | Per-frame with lyric node |
| 教程步骤 | Tutorial designer | Content + demonstration environment | Learning goal + difficulty progression | Highlighted area + annotation system | Per-step with keyboard shortcuts |
| 短视频分镜 | Short-video creator | Host + scene + hook design | Hook + content expansion + CTA | Fast intro→slow content→wrap | Per-shot with script + captions |
| 品牌故事板 | Brand strategist | Brand core + audience + color palette | 4-stage narrative (pain→appear→value→emotion) | Brand visual system + font timing | Per-frame with brand touchpoints |
| 剧情分镜 | Trailer director | NO breakdown (AI generates full 3×3 grid) | Story interpretation sentence → full prompt | NOT separated (merged into grid) | **3×3 grid** with labeled frames, single cohesive prompt |

## Reference: Professional Film Nomenclature

| Abbr | Name | Covers | Use Case |
|------|------|--------|----------|
| ELS | Extreme Long Shot | Full landscape | Establishing the world |
| LS | Long Shot | Head to toe | Body language in context |
| MLS | Medium Long Shot / American | Knees up | Classic cowboy framing |
| MS | Medium Shot | Waist up | Conversation/action |
| MCU | Medium Close-Up | Chest up | Emotion + context mix |
| CU | Close-Up | Face | Emotion, intimacy |
| ECU | Extreme Close-Up | Eyes/hands/prop | Detail, symbolism |
| Low Angle | Worm's Eye | Looking up at subject | Power, drama |
| High Angle | Bird's Eye | Looking down | Vulnerability, layout |

## Integration Point

This framework is embedded in `_build_storyboard_system_prompt()` and `_build_storyboard_user_prompt()` in the PromptLibraryNode V17.0+ `__init__.py`. The 剧情分镜 mode specifically uses the 3×3 grid structure and single-cohesive-prompt output format.
