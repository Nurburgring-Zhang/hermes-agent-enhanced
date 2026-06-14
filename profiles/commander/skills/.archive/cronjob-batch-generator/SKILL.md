---
name: cronjob-batch-generator
description: |-
  Orchestrate massive AI content generation using parallel cronjobs.

  Key idea: for 100K-scale generation, delegate_task is too slow (~8-10 items per call before timeout).
  Instead, spawn N cronjobs (one per output file), each running every 1-5 minutes,
  each producing ~5 items per run. 9 parallel cronjobs × 5 items × 60 runs/hour = 2,700 items/hour.

  State management: each cronjob checks file length at start, skips if target reached.
  This provides automatic self-termination and crash recovery (file content is never lost).
trigger: |-
  User asks to generate large-scale AI content (10K+, 100K+, etc.)
  Tasks involving: 'produce 10,000 prompts', 'generate 50,000 images' type requests
version: 2.0.0
author: Hermes AI Agent
license: MIT
---

# Cronjob Batch Generator

**Pattern for large-scale AI content generation via parallel self-terminating cronjobs**

## When to Use This Skill

## 触发条件
- 用户提及此功能相关关键词时
- 遇到此领域的标准问题时
- 需要执行该领域的标准操作时


Use this when you need to:
- Generate 10,000+ AI-crafted items (prompts, descriptions, captions, summaries)
- Each item requires AI-level reasoning (not simple template filling)
- Items must meet strict quality constraints (length, format, style)
- Must survive conversation timeouts/interruptions

**Do NOT use for**:
- Simple batch operations (use a Python script + loop)
- < 1,000 items (delegate_task directly is fine)
- Tasks where items are independent of AI reasoning (template-based)

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│              Cronjob Batch Generator                     │
│                                                          │
│  cronjob-1 (file_01.txt) ── 5 items/run ── target N     │
│  cronjob-2 (file_02.txt) ── 5 items/run ── target N     │
│  ...                                                     │
│  cronjob-N (file_N.txt) ── 5 items/run ── target N      │
│                                                          │
│  Each cronjob:                                           │
│  1. wc -l <file> → skip if >= target                    │
│  2. Generate 5 items via AI                             │
│  3. echo >> <file> (append each item immediately)       │
│  4. Verify length constraints with wc -m                │
│  5. Exit (next run in N minutes)                        │
└─────────────────────────────────────────────────────────┘
```

## Critical Prerequisite: Template Libraries First

**NEVER start production without building template libraries first.** This session wasted hours because generation was started prematurely with empty/incomplete libraries. The user approved the sequence: "先做好准备在生成" (prepare first, then generate).

### Phase 1: Build Template Libraries (3 files × 1000+ items each)

Location: `{project_dir}/高质量模板/`

| File | Content | Item format | Count |
|------|---------|-------------|-------|
| 15_女性风格库.txt | Visual style descriptions (主流审美/时尚/潮流) | 100-150字 pure text | 1000+ |
| 16_女性穿搭库.txt | Outfit descriptions (发型+妆容+上衣+下装+鞋+配饰) | 100-150字 pure text | 1000+ |
| 17_女性姿势库.txt | Pose/scene descriptions (时尚生活场景) | 100-150字 pure text | 1000+ |
| 18_摄影风格库.txt | Photography style descriptions | 100-150字 pure text | 60+ (quality over quantity) |

**Library content rules** (from user corrections):
- **Pure content only** — no row numbers, no headers, no style labels like `（性感魅惑10）` or `001|`
- Each line is standalone: `{content only}`
- 100-150 characters per line
- Must reflect mainstream aesthetics, fashion trends, social media appeal
- 女性主题 with style combinations: 美艳/冷艳/性感/可爱/萌萌哒/青春/活力/性冷淡 etc.

**Generation method**: Use `delegate_task` with 3 parallel subagents, each building one library. Each subagent uses Python scripts to bulk-generate 50 items per call. Repeat until 1000+ is reached.

### Phase 2: Prepare Style Domain Mapping

Distribute the 100K items across N style domains:

| Shard | Domain | Styles | Target |
|-------|--------|--------|--------|
| 01 | Art classics | 古典油画/印象派/现代主义/东方传统 | 10,000 |
| 02 | Aesthetic Life | 法式慵懒/韩系奶油/北欧冷淡/新中式/森系治愈/美式复古 | 11,111 |
| 03 | Travel & Outdoors | 美式复古/波西米亚/夏日度假/地中海 | 11,111 |
| 04 | Urban & Home | 温暖家居/都市极简/工业风/复古港风 | 11,111 |
| 05 | Vacation | 旅行度假/民宿/海岛/山川/草原 | 11,111 |
| 06 | Night & Food | 都市夜景/深夜治愈/烟火美食 | 11,111 |
| 07 | Fashion | 时尚杂志/商业摄影/奢侈品广告 | 11,111 |
| 08 | Vintage | 怀旧复古/王家卫港风/电影胶片 | 11,111 |
| 09 | Social Life | 小红书生活（煮咖啡/瑜伽/浇花/看书/插花/撸猫等） | 11,111 |
| 10 | Portrait | 专业写真/杂志封面/商业模特/奢侈品广告 | 11,111 |

### Phase 3: Launch Cronjobs

See [Quick Start](#quick-start) below.

## Quick Start

### 1. Create N cronjobs (one per output shard)

```bash
hermes cron create \
  --name pg-02 \
  --schedule "every 1m" \
  --repeat 5000 \
  --deliver local \
  --prompt '【高速生成-02.txt】wc -l /path/file_02.txt>=11111则退出。生成5条（严格600-700字！wc -m验证！一段完整文字！）。echo逐条追加。风格：法式慵懒/韩系奶油。7维度完整+传统色名。写完后"ok02"。'
```

### 2. Trigger all cronjobs immediately

```bash
hermes cron run <job_id_1>
hermes cron run <job_id_2>
```

### 3. Monitor progress

```bash
for f in /path/files_*.txt; do echo "$(basename $f): $(wc -l < $f)条"; done; echo "总计: $(cat /path/files_*.txt | wc -l)条"
```

## Cronjob Prompt Template

```
【高速生成-{FILE_NAME}】wc -l {FULL_PATH}>={TARGET}则退出。
生成{N}条（严格{MIN}-{MAX}字！wc -m验证！一段完整文字不要标题序号！）echo逐条追加。
风格：{STYLE_DOMAIN_LIST}
7维度完整。用中国传统色名。
写完后"ok{SHORT_NAME}"。
```

Keep cronjob prompts under ~800 chars. Use abbreviations (pg-02 not prompt-generation-batch-02).

## Nine-Layer Template (九层模板法)

**This is the core quality framework. Use it for every generated item. It comes from the user's template library (`01_模板结构.txt`).**

Each item is one continuous paragraph weaving all 9 layers:

### Layer 1: Style name + technique description (2-4 sentences)
Style name followed by 2-4 sentences describing brushwork, medium, canvas/texture, technique-specific visual effects and imperfections.

Key points:
- Describe brushstroke length/thickness/pattern
- Describe paint thickness/dryness/transparency/gloss
- Describe canvas/paper texture, absorbency, effect on pigment spread
- Describe technique-specific effects like glazing, palette knife texture, soaking penetration, paper collage

Example: "巴洛克卡拉瓦乔暗调主义风格，画面背景沉入近乎绝对的黑色调中，只有一束锐利的光从画面左上角斜射进来精准地照亮主体的面部和手部。光线与暗影之间没有任何中间调过渡形成了极端强烈的明暗对照效果。"

### Layer 2: Camera + composition (1-2 sentences)
Shot type (close-up/medium/wide), angle (eye-level/overhead/underslung), composition rule (rule of thirds/diagonal/symmetry/framing/leading lines/negative space/triangle)

### Layer 3: Subject position + pose + expression (5-8 sentences)
Body position, head angle, eye direction, expression details, arm/hand details, leg position.

Write about: where subject is in frame, body posture, head angle (lowered/tilted/turned/looking back), eye direction (at camera/into distance/sideways/downward/closed), expression (smile corner/furrowed brow/focused/distant gaze), arm pose (natural/crossed/in pocket/on surface/raised), hand details (finger bending/grip strength/fingertip touch), leg position (together/crossed/extended/one bent/one straight)

### Layer 4: Material detail layer — THE QUALITY CORE (8-12 sentences, most text)

**Hair details**: color + gloss + length + style (straight/curly/bun/braids/ponytail/shoulder-length) + current state (wind-blown/rain-wet/sweat-damp/natural-falling) + texture (coarse/fine/smooth/frizzy/curly) + lighting effect (backlit translucent/overhead shiny/side-lit texture)

**Skin details**: color (fair/tan/olive/ivory/pink-white) + texture (smooth/pores/dry/wrinkled/tight) + features (cheekbones/nose/lip shape/eye shape/eyebrow/jaw line) + marks (freckles/moles/scars/age spots/sun spots) + veins (hand veins/eye capillaries/temples) + special state (sweat glow/flushed cheeks/cold-red nose/teary eyes) + makeup (lipstick color/eyeshadow layers/eyebrow grooming/blush position/highlight area)

**Upper garment**: fabric (velvet/wool/linen/silk/cotton/denim/leather/knit/lace/chiffon/satin/tweed) + color + pattern (solid/stripe/plaid/floral/tie-dye/gradient/embroidery/print/polkadot) + design details (neckline: round/V/stand/turn/collar; sleeve: long/short/puff/flare; front: zipper/button/tie/snap; hem: straight/curved/slit) + physical properties (reflectance/transparency/drape/fluffiness/stretch) + wearing state (neat/messy/half-buttoned/half-zipped/slipped-strap/rolled-cuff/lifted-hem/open-collar)

**Lower garment folds**: type (stretch/stack/crush/drape/grip) + distribution (elbows/ knees/abdomen/armpit/hips) + wear (thinned-elbows/yellowed-collar/faded-knees/frayed-cuffs/unhemmed-edge/worn-pocket/loose-button/open-seam) + aging (faded/shrunk/pilled/faded/color-difference/wash-marks/uneven-sun-exposure) + stains (coffee-spread/oil-semi-transparent/paint-splotches/mud-penetration/sweat-rings)

**Accessories**: jewelry (metal-luster/oxidation-dark/diamond-fire/pearl-rainbow/chain-weave/pendant-shape) + watch (dial-position/crystal-reflection/strap-wear/metal-band-gaps) + glasses (lens-transmission/reflection-color/temple bend/nose-pad-mark) + hat (brim-curve/fabric-texture/crown-dent/hat-band-sweat) + scarf (wrap-style/draped-tassel/knit-pattern/edge-fray) + bag (leather-pore/hardware-scratch/handle-luster/bottom-scuff) + shoes (leather-grain/toe-wear/lace-method/sole-dirt/upper-deform)

**Other materials**: metal (rust/hardware-scratch/oxidation-color/disorted-reflection) + glass (transparency/bubbles/scratches/fingerprint/condensation/green-fracture-edge) + wood (grain-texture/varnish-aging/cracks/worm-holes/knots) + stone (crystal-reflect/weathering/moss/grid-marks/cut-surface) + water (surface-tension/ripple-frequency/reflection-distortion/water-depth/clarity) + plant (leaf-veins/flower-translucency/petal-texture/roots-in-soil) + paper (fiber-texture/crease/yellowing/ink-penetration/curled-edge/water-stain) + plastic (scratches/white-bend/fading/mold-line/surface-gloss) + leather (pore-texture/uneven-dyeing/use-shine/crease/edge-stitching)

### Layer 5: Foreground + Midground + Background (3-5 sentences)
- Foreground: guides eye, creates depth, sets environmental context. Most detail-rich, most realistic texture. Elements: table objects/plant leaves/door frame/window frame/hands/shoulders/railing/glass beads/ground texture.
- Midground: subject's activity space, furniture around subject, objects subject interacts with. Describe spatial relationship between subject and surroundings.
- Background: sets time and place, enhances atmosphere, provides color contrast. Can be blurred but describe the shapes and colors in the blur. If wide-angle, clear perspective.

### Layer 6: Color system (3-4 sentences)
Main color + auxiliary color + contrast color + warm/cold tendency.

**MUST use Chinese traditional color names**:
- Red: 朱红/胭脂/银红/殷红/绛紫/绯红/檀色/赭色/赤金/彤色
- Orange-Yellow: 琥珀/橘黄/藤黄/鹅黄/杏黄/姜黄/蜜色/牙色/金色/铜色/麦秆黄
- Green: 石绿/翠绿/竹青/苍绿/黛绿/碧色/草绿/松花绿/豆绿/茶绿
- Blue: 群青/靛蓝/钴蓝/黛蓝/天青/月白/景泰蓝/宝石蓝/海军蓝/普鲁士蓝
- Purple: 藕荷/丁香/紫檀/玫瑰紫/茄色/雪青/紫罗兰
- Brown: 赭石/檀褐/栗色/茶色/褐色/咖啡/古铜/驼色/卡其/玳瑁
- Black-Gray-White: 墨黑/纯白/月白/象牙白/银灰/烟灰/铅灰/骨白/米色/霜色
- Other: 秋香/螺黛/鸦青/花青/藏青/品红/芍药红/蔷薇色/琥珀色/松烟墨

### Layer 7: Light and shadow (4-6 sentences)
Light source direction (front/side/back/top/bottom/diffuse), light quality (hard/soft/scattered), highlight description (position/shape/brightness/color), shadow description (position/color/edge/layer), rim light (position/width/brightness/color)

### Layer 8: Atmosphere and emotion (2-3 sentences)
Sentence 1: Summarize atmosphere. Sentence 2: Connect atmosphere to subject state. Sentence 3: Use metaphor or synesthesia to describe physical sense of emotion in the scene.

### Layer 9: Viral element (1-2 sentences, naturally integrated)
Type A: Style homage — "以当代超写实技法向维米尔的戴珍珠耳环的少女致敬"
Type B: Surreal visual paradox — "一面破碎的镜子中倒映的不是当前房间的景象而是一片星空"
Type C: Subversive contrast — "在整体极度写实的画面中故意留下一处失控的颜料滴落的痕迹"
Type D: Object displacement — "身穿维多利亚时期华丽长裙的古典淑女坐在现代地铁站的塑料椅上"

**禁止输出"破圈要素"或"破圈元素"这几个字**

## Reference-level Detail Density (示例级细节密度)

**THIS IS THE QUALITY BASELINE. Every generated item must match this density. User explicitly rejected anything below this level.**

Reference example that defines the standard:

> 吉卜力动漫治愈风，如宫崎骏动画般梦幻、治愈的手绘质感。画面通常伴有轻柔的空气感、水彩般的天空与云朵，以及极具生活化与情感表达力的人物微表情。这是一幅中近景平视镜头捕捉的女性肖像，画面采用极近的主体构图，聚焦于模特精致的上半身与面部细节，光线柔和明亮，呈现出一种清透的日系杂志质感。主体位于画面中央偏左，呈微侧身姿态，头部微微向左倾斜并回望镜头，眼神清澈且充满灵气。她拥有一头乌黑柔顺的长直发，前额留有空气刘海，发丝自然垂落在脸颊两侧，妆容精致，橘红色的唇妆与深邃的眼妆相得益彰，鼻梁小巧挺翘。她身穿一件蓝黑撞色的华丽露肩上衣，主体面料为深蓝色丝绒，带有褶皱花边设计，内搭黑色透视蕾丝，蕾丝花纹繁复立体，质感细腻；颈间佩戴着一条银色链条项链，链尾缀有一颗醒目的蓝色丝绒大花，双手优雅地轻抚锁骨处，手指修长，指甲修剪整齐。画面整体笼罩在一层淡淡的冷调蓝色滤镜下，增强了丝绒的质感与整体氛围的深邃感。光线采用柔和的正面漫射光，均匀地打亮模特的面部，使皮肤呈现出细腻的瓷白光泽，阴影过渡自然，没有强烈的明暗对比，突出了五官的立体感与妆容的精致度，营造出一种梦幻且高级的视觉体验。镜头采用平视角度，视线与模特的眼睛处于同一水平线上，这种构图拉近了人物与观众的心理距离，使得人物表情更加生动亲切。同时，镜头略微带有一点点的仰视感，微微拉长下颚线条，修饰脸型，增添了一份自信与妩媚。画面构图采用了经典的三分构图法，模特的眼睛位置大致落在画面的黄金分割点上，视觉重心稳定。背景中的海报作为虚化的装饰元素，既交代了拍摄环境，又通过色彩呼应了主体的蓝黑色调，形成了一种微妙的层次感，使得主体在繁复的细节中依然突出。背景是一面洁白的墙壁，墙上贴着几张模特的时尚海报，海报内容虽被虚化，但依稀可辨是同款模特的不同造型，色彩以暖色和米色为主，与前景的冷色调形成冷暖对比。背景的虚化处理得当，有效地将视觉焦点牢牢锁定在前景的模特身上，同时增加了画面的空间纵深感，避免了背景的单调。整体的氛围是温柔中带着快乐，传递出一种纯粹的、无杂念的幸福感与性欲，在大胆的展示自我的魅力与性感。

Key markers of this density level:
- 头发：颜色+光泽+长度+发型+刘海类型+发丝垂落位置+光照效果
- 皮肤：肤色质感+颧骨+鼻梁+唇形+眼型+眉毛+妆容细节(唇色/眼影/腮红/高光)
- 服装：颜色+撞色描述+款式名+主面料+工艺特征(褶皱/花边/印花/刺绣)+内搭+内搭面料+花纹+立体感
- 配饰：金属材质+链条类型+坠子位置+形状+大小+光泽
- 手部：动作描述(轻抚/交叠/握持/自然垂等)+手指长度+指甲修饰
- 画面处理：整体色调滤镜+氛围统一
- 光影：光源方向+光线性质+高光+阴影过渡+轮廓光+高级感用词(瓷白/通透/梦幻)
- 构图：景别+视角+构图法则+视觉重心+黄金分割
- 背景：元素+虚化程度+色彩呼应+冷暖对比+空间纵深感
- 氛围：具体情感词+性张力/幸福感/治愈感等氛围传递

## 女性主题多风格组合

For social media aesthetic content, use 女性主体 with style combinations:

**Style tokens**: 美艳/冷艳/性感/魅惑/可爱/萌萌哒/青春/活力/性冷淡/优雅/慵懒/甜美/飒爽/清纯/妩媚/知性/元气/温柔/酷飒/复古

**Combination method**: Pick 2-3 tokens per item and blend:
- 美艳+冷艳, 可爱+性感, 清纯+魅惑, 青春+元气
- 性冷淡+优雅, 萌萌哒+活力, 酷飒+美艳

Embed the combination naturally into the opening style description — don't just list the tokens.

## Word Count Enforcement (Critical Pitfall)

### The Problem
- AI generates 900-1700 chars when asked for 500-700
- AI writes 300+ chars when asked for 100-150
- Each subagent run must iterate 3-5 times to trim down

### Solution
1. **In the cronjob prompt itself**, include explicit verification:
```
每条严格{MIN}-{MAX}字！用 wc -m 验证！超{MAX}字必须删减！低{MIN}字补充！
```

2. **After each write**, verify:
```bash
echo "内容" | wc -m
# If > MAX: delete and rewrite shorter
# If < MIN: delete and add more detail
```

3. **For library files (100-150字)**: Check distribution:
```bash
python3 -c "
with open('/path/to/library.txt') as f:
    lens = [len(l.strip()) for l in f.readlines()[1:] if l.strip()]
print(f'合格: {sum(1 for l in lens if 100<=l<=150)}条')
print(f'过短: {sum(1 for l in lens if l<100)}条')
print(f'过长: {sum(1 for l in lens if l>150)}条')
"
```

4. **For production (600-700字)**: Keep `wc -m` as a mandatory cronjob step.

### Root Cause
Subagents don't accurately estimate Chinese character counts during generation. They produce ~1.5-2x the intended length. Plan for 2-3 rounds of trimming per batch.

## Prompt Quality Cleanup (Post-Generation)

After large-scale generation (~200K items), run these cleaning passes:

### 1. Face Color Terms Removal

Remove all explicit face color/cosmetics terms from generated prompts. These are unnatural in prompts and cause AI models to produce unrealistic face textures.

Target terms:
```
腮红, 晒红, 晒伤, 红润, 潮红, 绯红, 嫣红, 酡红, 晕红,
泛红, 透红, 涨红, 羞红, 红晕, 红潮,
面色红润, 面色潮红, 脸颊红润, 脸颊泛红, 皮肤红润, 肌肤红润,
橘粉晒伤腮红, 粉色腮红, 桃色腮红, 杏色腮红
```

**Approach**: Simple string replacement with empty string. Do NOT remove whole lines — just delete the offending words. Backup originals first (`.bak` suffix).

**Verification**: `grep -c '<term>' *.txt` should return 0 for all terms.

**Real-world scale**: 27,800 removals across 206,851 items in 40 files.

### 2. Multi-Limb Description Detection & Removal (三手/三腿清理)

Generated prompts sometimes describe 3 hands, 3 legs, or 3 feet in a single prompt (e.g., "一手拿手机，一手拿帽子，一手扶栏杆"). These produce deformed images.

**Detection method**: Split text by Chinese comma `，` period `。` semicolon `；`. Count segments that begin with hand/leg/foot keywords like:
- `左手` `右手` `一手` `另一只手` `一只手` `双手`
- `左腿` `右腿` `一条腿` `另一条腿`
- `左脚` `右脚` `一只脚` `另一只脚`

**Exclude false positives**: Product names containing "手" like 手表/手链/手机/手套/手工/手法/手镯 must NOT count.

**Fix**: When ≥3 hand/leg segments detected, remove the LAST one:
```python
segments[last_hand_idx] = re.sub(r'^(?:左手|右手|一手|另一只手|一只手).*', '', segments[last_hand_idx])
new_line = '，'.join(s for s in segments if s.strip())
```

**Real-world scale**: ~7,000 lines with ≥3 hand segments fixed; ~16 legs; ~66 feet.

### 3. Lighting/Glow Wording Cleanup (光影清理)

Replace overly flowery lighting descriptions with cleaner equivalents:
```
"泛着" → "带着"
"光晕" → "光"  
"镀上" → "染上"
"红润" → "透亮"
"倾泻" → "照入"
"投下斑驳" → "落下斑驳"
```

## PromptLibraryNode Extreme Audit Methodology

When developing ComfyUI prompt nodes, use this 3-round audit cycle:

### Round 1: Functional Multi-Condition Test
- ALL boundary inputs: empty string, long string (50K+ chars), missing args
- ALL error paths: nonexistent path, no files, empty files, max files
- ALL modes: random/sequential/shuffle/weighted
- ALL features combined: filter+edit+export simultaneously
- Thread safety: 20 concurrent calls
- Performance: 100K rows < 3 seconds

### Round 2: Deep Code Defect Audit
Check for these common issues in prompt node code:
1. **Dead code** — Old keyword lists still present but unused (WITH_SUBJECT_KEYWORDS)
2. **Duplicate logic** — Two methods doing same thing (_has_subject vs _in_whitelist)
3. **Performance waste** — Sets defined inside methods (rebuild every call) vs class variables
4. **Short word misdetection** — Single-char lifeless keywords ("面" matching "湖面", "酒" matching "酒红")
5. **Concurrent write conflicts** — History dedup file shared across threads without lock
6. **Nested try/catch** — Overcomplicated error handling that hides actual errors

### Round 3: Integration Regression
After fixes, re-run Round 1 completely + verify each specific fix doesn't break other features.

## Phase 2 Feature Expansion (ComfyUI Nodes)

After core prompt library functionality is stable, expand with:

### Phase 2-1: Prompt Editing Pipeline
- **正则替换** (regex find/replace with error handling)
- **字符长度裁切** (min/max char length clipping)
- **移除HTML标签** (strip `<tag>` content)
- **移除多余空格** (collapse multiple spaces/newlines)

### Phase 2-2: Negative Prompt Generation
- 48项标准负面词库 (ugly/deformed/blurry/bad anatomy/etc.)
- 从正面prompt提取特定负面词 (手→bad hands, 脸→bad face)
- 用户自定义扩展 (通过逗号分隔)
- 输出到第5个端口 (负面提示词)

### Phase 2-3: Export & Format Conversion
- **CSV导出**: 标准CSV格式，多行prompt每行一条记录
- **JSON导出**: `{"prompts": [...], "count": N, "negative_prompt": ""}`
- **SD3格式**: 逗号分隔的标签式prompt
- **Flux格式**: 去掉SD权重符号 `(( ))` `{ }`
- 所有导出与格式转换可与过滤/编辑/负面词同时工作

## Pitfalls

1. **字数控制困难** — AI generates over the limit. Solution: always add `wc -m verification` after each write with explicit rejection logic.

2. **Cronjob doesn't run when parent conversation is idle** — Cronjobs run in their own session but may be affected by system load. Use `every 1m` schedule, repeat large (5000), and explicitly run each once after creation.

3. **Library content must be pure text** — Users strongly reject formatting artifacts. No numbers, headers, labels, or category markers. Each line must be standalone readable content.

4. **delegate_task too slow for scale** — Never use delegate_task for large-scale generation. Each call produces only 5-8 items. Cronjobs are ~10x more efficient.

5. **Lost content on cleanup** — Always backup old files before clearing (`_old_backup/` directory).

6. **File path issues** — Subagents may use wrong paths. Use absolute paths, verify with `ls -la`.

7. **Format drift** — Subagents sometimes add titles/numbers/blank lines. Be explicit: "不要标题！不要序号！不要分段！一段完整文字！"

8. **Cronjob prompt size** — Keep prompts under ~800 chars. Must contain: check-condition + generate-command + quality-constraints + write-command.

9. **Template-first, production-second** — Never start production without reading and optimizing template libraries first.

10. **THREE-HAND CONTRADICTION IS THE #1 BUG** — The most common structural error in generated prompts is describing a person doing three things with only two hands (e.g., "一只手自然垂落，另一只手轻触窗台边缘。她正在用锅铲翻动食材" = 3 hands for 1 person). This MUST be prevented at generation time, not cleaned up post-hoc. Rules:
    - Every person has exactly 2 hands
    - Use "左手XX, 右手XX" pattern once per person, never twice
    - Never combine static hand description ("一只手自然垂落") with active doing ("正在煮饭")
    - Never use "轻触XXX的边缘" as a stock phrase — it contradicts when paired with an active activity
    - Post-generation scan: if a prompt has both "自然垂落" and "正在[活动]" → regenerate

11. **delegate_task is unreliable for sustained batch production** — In practice, 3 concurrent delegate_task calls fail ~30% of the time due to timeout/max_iterations. For 10K+ generation, use cronjob pattern instead. For 1K batches, expect to retry failed ones.

12. **Library quality audit BEFORE generation** — Always verify these before starting production:
    - Count unique items per library: `wc -l` is not enough — check for duplicates
    - Check for "一只手自然垂落" / "另一只手" patterns in library files — these will cause three-hand bugs when combined
    - Check 12_配饰鞋帽库 for mixed-in scene descriptions (should not contain "天空/树木/草地/窗户/建筑/墙/道路/风景" when describing accessories)
    - Verify 14_色彩搭配库 has meaningful variety (not 10 identical copies of "互补色")
    - Sample check: pick 3 random items from each library and manually verify they make sense

13. **Multi-dimensional library architecture requires carefully designed combinator** — A "15 libraries → random pick → concatenate" approach ALWAYS produces broken results:
    - Problem: each library is independent, but when combined, body parts multiply (2 × 角色 + 1 × 活动 = 3 hands)
    - Solution: Use a SINGLE monolithic prompt template where each slot is filled from libraries but WITH CONTEXT of what other slots are doing
    - Better approach: generate each prompt as ONE AI call with all 9 layers, referencing libraries as reference material, not as pre-cut puzzle pieces
    - If using script-based combination: the script must be aware of hand-count constraints and skip contradictory combinations

14. **Accessory mismatch is invisible until generation** — When 12_配饰鞋帽库's "项链" entries actually describe "袜子/手套/眼镜/发簪/腰带/胸针", the generated prompt says "颈间佩戴着一条精致的手套/袜子". Solution: verify each accessory entry actually describes the tagged accessory before using it in combination.

15. **Cronjob vs Script tradeoff**:
    - Cronjob pattern: 5 items/run, auto-resume, survives disconnection, but ~9 items/min
    - Python script pattern: ~500 items/sec, single run, but no crash recovery
    - Rule of thumb: cronjob for >10K items, script for 1K-5K items with solid checkpointing

## Prompt Quality Cleanup (Post-Generation)

After large-scale generation (~200K items), run these cleaning passes:

### 1. Face Color Terms Removal

Remove explicit face color/cosmetics terms. String replacement with empty string, don't remove whole lines.

Terms: 腮红, 晒红, 晒伤, 红润, 潮红, 绯红, 嫣红, 酡红, 晕红, 泛红, 透红, 涨红, 羞红, 红晕, 红潮, 面色红润, 面色潮红, 脸颊红润, 脸颊泛红, 皮肤红润, 肌肤红润, 橘粉晒伤腮红, 粉色腮红, 桃色腮红, 杏色腮红

**Scale**: 27,800 removals across 206,851 items in 40 files.

### 2. Multi-Limb Detection & Cleanup (三手/三腿)

Prompts sometimes describe 3 hands/legs/feet in one line → deformed images.

**Detection**: Split by comma/semicolon. Count segments starting with: 左手/右手/一手/另一只手/一只手 (hand); 左腿/右腿/一条腿(leg); 左脚/右脚/一只脚(foot).

**Exclude false positives**: 手表/手链/手机/手套/手工/手法/手镯/手术/首饰等(contain "手" but not body part).

**Use regex boundary**: r'(?<!\w)(?:左手|右手|一手|另一只手|一只手)(?!\w)'

**Fix**: Remove the LAST excess segment:
```python
segments[last_idx] = re.sub(r'^(?:左手|右手|一手...).*', '', segments[last_idx])
```

**Scale**: 6,953 three-hand, 16 three-leg, 66 three-foot fixed. 0 residual.

### 3. Lighting Wording Cleanup

Replace over-flowery descriptions: "泛着→带着", "光晕→光", "镀上→染上", "红润→透亮", "倾泻→照入", "投下斑驳→落下斑驳"

## PromptLibraryNode Extreme Audit (3-Round Cycle)

### Round 1: Functional Multi-Condition Test
- ALL boundary inputs: empty string, 50K+ chars, missing args
- ALL error paths: nonexistent path, no files, empty files, max files
- ALL modes: random/sequential/shuffle/weighted
- ALL combinations: filter+edit+export+negative simultaneously
- Thread safety: 20 concurrent calls
- Performance: 100K rows < 3 seconds

### Round 2: Deep Code Defect Audit
Check for:
1. **Dead code** — unused keyword lists (WITH_SUBJECT_KEYWORDS was 37 lines)
2. **Duplicate logic** — _has_subject vs _in_whitelist doing same thing
3. **Performance waste** — sets defined inside methods (rebuild every call) vs class variables
4. **Short word misdetection** — char "面" matching "湖面", "酒" matching "酒红"
5. **Concurrent write conflicts** — history dedup file shared across threads without lock

### Round 3: Integration Regression
Re-run Round 1 completely after fixes. Verify each specific fix doesn't break other features.

## Phase 2 Feature Expansion

### Phase 2-1: Prompt Editing Pipeline
- **正则替换**: regex find/replace with error handling for malformed patterns
- **字符长度**: min/max char length clipping
- **移除HTML标签**: strip `<tag>` content
- **移除多余空格**: collapse 2+ spaces, 3+ newlines

### Phase 2-2: Negative Prompt Generation
- 48项标准负面词库 (ugly/deformed/blurry/bad anatomy/extra limbs/etc.)
- 从正面prompt提取特定负面 (手→bad hands, 脸→bad face)
- 用户自定义扩展 (comma-separated)
- 输出到第5个端口

### Phase 2-3: Export & Format Conversion
- **CSV导出**: standard format, each line = one record
- **JSON导出**: {"prompts": [...], "count": N, "negative_prompt": ""}
- **SD3格式**: comma-separated tag-style prompt
- **Flux格式**: strip SD weight notation (( )) { }
- All export+format work simultaneously with filter+edit+negative

## Pitfalls

When quality allows template-combination (vs pure AI reasoning), use `scripts/massive_generator.py`:

```
# single run, 9 files × 5000 items each
python3 autonomous-systems/cronjob-batch-generator/scripts/massive_generator.py
```

**Performance**: ~500 items/sec vs cronjob's ~9 items/min.
**Trade-off**: Template-combination lacks AI-level coherence. Use for bulk-fill after cronjobs set the quality baseline, OR when user explicitly approves template-based approach.

## Scaling Math

| Method | Items/min | Items/hour | Time for 90K items |
|--------|-----------|------------|-------------------|
| Cronjob (every 5m × 9 × 5) | 9 | 540 | 7 days |
| Cronjob (every 1m × 9 × 5) | 45 | 2,700 | 33 hours |
| Script (`massive_generator.py`) | ~30,000 | 1,800,000 | ~3 minutes |

## Recovery After Interruption

```bash
# Check current state
for f in /path/shards_*.txt; do echo "$(basename $f): $(wc -l < $f)条"; done

# Cronjobs auto-resume — they check file length and continue
# Just verify they're still scheduled:
hermes cron list | grep "pg-"

# If any missing, recreate and run
```

## 回滚方案
### 快速回滚
如果部署后发现问题：
1. 使用版本控制回退到上一个提交：`git revert HEAD`
2. 确认回滚后系统状态正常
3. 通知相关方变更已撤销

### 数据安全
- 所有修改前确认有备份
- 配置变更记录版本历史
