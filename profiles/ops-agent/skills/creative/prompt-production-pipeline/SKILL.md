---
name: prompt-production-pipeline
description: >-
  End-to-end AI prompt production pipeline: build dimension libraries from raw data, 
  compose high-quality prompts with conflict detection, generate at scale (1K-100K+), 
  and produce aesthetic-grade Chinese text-to-image prompts. Consolidates library-engineering,
  composition, batch-generation, and content-craft into one class-level workflow.
version: 2.0.0
author: Hermes Agent
tags:
  - prompt-generation
  - text-to-image
  - chinese-aesthetic
  - massive-generation
  - dimension-library
  - batch-processing
  - cronjob
triggers:
  - "生成提示词"
  - "维度库"
  - "批量生成"
  - "prompt组合"
  - "批次生成"
  - "to_chi"
  - "100万提示词"
  - "大规模生产"
  - "批处理建库"
  - "清洗库文件"
  - "组合引擎"
  - "质量审核"
  - "试生产"
  - "性别矛盾"
  - "C02"
  - "场景矛盾"
  - "维度拆分"
  - "维度筛选"
  - "批量生产"
  - "性别过滤"
  - "大生产"
---

# Prompt Production Pipeline

**Class-level umbrella** for the complete AI prompt production lifecycle: raw data analysis → dimension library building → prompt composition → conflict detection → mass generation → quality control.

This skill consolidates 4 sibling skills into subsections. Each retains its specialized detail in `references/` files.

## Pipeline Overview

## 触发条件
- 用户提及此功能相关关键词时
- 遇到此领域的标准问题时
- 需要执行该领域的标准操作时


```
┌─────────────┐    ┌──────────────┐    ┌─────────────┐    ┌───────────────┐
│ Library     │ →  │ Prompt       │ →  │ Mass        │ →  │ Quality       │
│ Engineering │    │ Composition   │    │ Generation   │    │ Control       │
│ (data→libs) │    │ (libs→prompt)│    │ (scale up)   │    │ (audit+fix)   │
└─────────────┘    └──────────────┘    └─────────────┘    └───────────────┘
```

## Section A: Dimension Library Engineering

*Absorbed from: `prompt-library-engineering`*

### Core Principle: Data-Driven, Not Preset

**NEVER preset a fixed number of dimensions** (like "15 dimensions"). Instead:
1. Sample 10,000 random entries from source data
2. Exhaustively analyze what dimensions naturally emerge
3. Let the data reveal the dimension count and boundaries
4. Only then build libraries for the natural dimensions

### The 17 Natural Dimension Libraries (from to_chi analysis)

| Code | Dimension | Typical Count | Extraction Keywords |
|------|-----------|:-------------:|---------------------|
| A01 | 年龄性别 | 18K+ | 一位/一名/年轻/中年/老年/少女/女孩 |
| A02 | 发型 | 48K+ | 长发/短发/卷发/马尾/丸子头 |
| A03 | 肤色 | 661 | 白皙/小麦/古铜/红润/粉嫩 |
| A04 | 表情眼神 | 2K+ | 表情/神情/目光/微笑/直视 |
| A05 | 姿势 | 94K+ | 站立/坐着/躺/跪/趴/倚/盘腿 |
| B01 | 场景环境 | 101K+ | 在卧室/站在/位于/场景/环境 |
| B02 | 活动行为 | 187K+ | 正在/阅读/端起/行走/自拍 |
| C01 | 美学风格 | 11K+ | 写实/复古/胶片/清新/暗调 |
| C02 | 光照条件 | 39K+ | 柔光/自然光/暖光/侧光/逆光 |
| C03 | 色彩调性 | 103K+ | 暖色调/冷色/高对比/饱和度 |
| C04 | 构图镜头 | 24K+ | 特写/中景/全景/浅景深/三分法 |
| D01 | 服装款式 | 170K+ | 身着/身穿/穿着/上身/下身 |
| D02 | 配饰鞋帽 | 12K+ | 项链/耳环/手链/戒指/帽子/鞋 |
| D03 | 材质质感 | 358K+ | 丝绸/棉麻/皮革/金属/木质 |
| D04 | 动态效果 | 34K+ | 飘动/吹动/飘扬/飞舞/摇曳 |
| D05 | 天气时间 | 13K+ | 清晨/午后/黄昏/夜晚/晴天 |
| D06 | 氛围情感 | 71K+ | 温馨/浪漫/忧郁/神秘/宁静 |

### The Surgical Clean Approach (CRITICAL)

**DON'T** (hammer approach): Discard whole sentences that contain person descriptions.

**DO** (scalpel approach): Keep sentences intact, REMOVE only the person-description parts.
- `"她穿着一件白色连衣裙，脖子上戴着一条银色项链"` → keep `"脖子上戴着一条银色项链"`
- `"窗框由风化的浅棕色木材制成"` → keep entirely (no person description)
- Use regex: `r'，[她他]穿着[^。，]{5,30}'` → `'，'`

### Extraction Methods (by quality)

| Method | Quality | Speed | Best For |
|--------|---------|-------|----------|
| **Sentence-level regex** (final_build.py) | Good | Fast (50K/sec) | Quick bulk extraction |
| **Boundary-aware extraction** (3-layer pipeline) | Better | Moderate | Production libraries |
| **API batch decomposition** | Best | Slow ($0.00005/item) | Final quality pass |

### Priority Order Bug (Critical Fix)

In extraction scripts, low-coverage dims must be checked **first** in the if-chain, otherwise high-coverage dims (C02) starve them:

```python
# WRONG: C02 checked first — captures all tech sentences, starving D06
if any(kw in s for light_kws): return ('C02_光照条件', s)
if any(kw in s for mood_kws): return ('D06_氛围情感', s)  # Never reached!

# RIGHT: Low-coverage dims checked first
if any(kw in s for mood_kws) and can_add('D06_氛围情感'): return ('D06_氛围情感', s)
if any(kw in s for light_kws) and can_add('C02_光照条件'): return ('C02_光照条件', s)
```

### Distribution Analysis (Mandatory Before Composition)

**Never sample uniformly.** Real distribution from to_chi (518K lines):

| Category | Top Items | Proportion |
|----------|-----------|:----------:|
| Age/Sex | 年轻亚裔女性 | 30.7% |
| Hair Color | 黑色 | 20.3% |
| Scene | 卧室 | 8.6% |
| Pose | 站立 | 27.5% |
| Special | 内衣描述 | 7.9%, 裸体 6.6%, 泳衣 2.3% |

### BERTopic Integration

For automatic theme discovery, use `paraphrase-multilingual-MiniLM-L12-v2` embedding model. BERTopic primarily clusters by **photography parameters** (景深、风格、光源), not content semantics — use as complementary signal.

---

## Section B: Prompt Composition Engine (Local, No API)

### v10.1 Engine: Label-Template + Gender-Filtered Picks (2026-05-29, CURRENT BEST)

**100/100 success, QC 89.6, gender 0%, scene 5%, three-hand 0%.**

Supersedes v6/v8.1 for all new production. The key innovation is moving gender filtering from a post-generation check to the DIMENSION PICK level:

```python
FEMALE_ONLY = ['文胸','蕾丝','比基尼','丁字裤','胸罩','抹胸','内衣','内裤',
    '连衣裙','裙子','短裙','长裙','吊带裙','丝袜','渔网袜','高跟鞋','凉鞋',
    '婚纱','头纱','珍珠项链','发箍','发带','手链','腮红','唇膏','口红']

def pick(items, seen=None, gender_filter=None):
    if gender_filter == 'male':
        candidates = [i for i in items if not any(w in i for w in FEMALE_ONLY)]
        if not candidates: candidates = items
    ...
```

#### Fixed 5-Paragraph Template

```
P1: Style seed intact
P2: "在[场景]中，[A01]，留着[发型]，[表情]。"
P3: "[pronoun]身着[服装]，搭配[配饰]。"
P4: "[pronoun][活动]。"
P5: max 3 tech dims (C02/C01/C03/D03/D06/C04/D05/D04)
```

#### Key differences from v8.1: gender filtering now at pick-time (not post-hoc), B01 trailing-char stripped, D02 only attached if D01 exists. Speed: 0.9s vs 22s per 100 items.

### Known Ceiling: ~80% Manual Pass Rate (v10.1)

After 6 engine iterations, the ceiling is QC 89.6 (gender 100%, scene 95%, three-hand 100%) with ~80% manual pass rate. Residual 20%: D01 fragments from full-sentence library entries. **Engine-level unfixable** — requires rebuilding dimension libraries as pure labels.

See `references/2026-05-29-v10_1-label-template-gender-fix.md`.

### v6/v8.1 (Historical — superseded by v10.1)

The following sections document the architecture that v10.1 replaces. Keep for reference, do NOT use for new production.

### Output Architecture: Paragraphic vs. Mechanical Join

**MECHANICAL JOIN (DON'T):** `"。".join(parts)` — Every dimension entry is a fragment. Joining 17 fragments with sentence separators produces line-internal concatenation noise, not coherent text. This is what `combine_engine_v4` produced (100% lines had cross-fragment pollution).

**PARAGRAPHIC (DO, v6 architecture):** Organize dimensions into 5 semantic paragraphs:

```
P1: Style seed (complete style description) — kept intact
P2: Person description (scene + age/gender + hair + expression + pose) — one continuous sentence
P3: Clothing (garments + accessories) — attached to person paragraph
P4: Activity + motion effects
P5: Technical layer (lighting + weather + material + color + composition + atmosphere) — max 3 dims
```

```python
para = []
para.append(s.strip('，。'))  # P1: style seed
person_parts = [a01, "在" + b01_clean, a02_clean, a04_clean]  # P2: person
para.append("，".join(person_parts))
cloth_parts = [d01, d02]  # P3: clothing
if cloth_parts:
    para[-1] += "，身着" + "，搭配".join(cloth_parts)
act_parts = [b02, d04]  # P4: activity
para.append("，".join(act_parts))
tech_parts = [wth, c02, c03, c04, d06]  # P5: technical — max 3
para.append("，".join(tech_parts[:3]))
txt = "。".join(para)
```

**Key rules for paragraphic output:**
- P2 subject must be created ONCE and reused. Never start a new "她" or "他" mid-paragraph.
- P5 is limited to 3 dimensions MAX. More than 3 introduces scene-group collision (see scene conflict section below).
- Between paragraphs, use full stop "。" — never merge across paragraphs.
- Remove scene-word pollution at each paragraph boundary (detect `|scene=` markers).

### Gender State Machine (v6 soft → v7 hard)

**Gender consistency is the #1 composition quality bug.** A gender mismatch ("年轻男子穿着粉色蕾丝文胸") destroys prompt credibility immediately. The state machine must enforce it:

```python
MALE_KEYWORDS = ['男性','男子','男人','男孩','少年','男模','男士','小伙']
FEMALE_KEYWORDS = ['女性','女子','女人','女孩','少女','女模','女郎','姑娘','女士']

def guess_gender(a01_text):
    for w in MALE_KEYWORDS:
        if w in a01_text: return 'male'
    for w in FEMALE_KEYWORDS:
        if w in a01_text: return 'female'
    return 'unknown'

def gender_filter(items, gender):
    if gender == 'male':
        bad = ['她','女性','女子','女模','姑娘','女士','女孩','少女','女郎']
    elif gender == 'female':
        bad = ['他','男性','男子','男模','男士','小伙','男孩','少年']
    else:
        return items
    result = [i for i in items if not any(w in i for w in bad)]
    return result if result else items  # fallback to all if over-filtered
```

**Apply to dimensions:** A02 (hairstyle), D01 (clothing), D02 (accessories), A04 (expression — rarely gendered but safe), B02 (activity). D01 is the most critical — female garments (蕾丝/文胸/胸罩/裙子/吊带/丝袜/比基尼/高跟鞋) MUST be excluded for male gender.

### Hard vs. soft filter behavior (v8.1 finding, 2026-05-28)
- **Soft (v6):** gender_filter is a preference only, falls back to unfiltered list if empty. This lets through ~5-10% gender mismatches.
- **Hard (v8.1):** Three-layer enforcement: (1) B01 scene entries filtered for gender pronouns, (2) D01 clothing filtered for female-garment keywords via regex, (3) final "她" vs "他" pronoun count check. Achieves 100% gender consistency on test corpus. See `references/2026-05-28-v8_1-hard-gender-production.md` for full architecture.

**CRITICAL LIMITATION:** Current dimension libraries (v3) contain almost exclusively female-coded clothing entries (蕾丝/文胸/丝袜/比基尼/高跟鞋). When gender=male, hard_filter_gender excludes ~95% → falls back to unfiltered → still female clothing. True male clothing requires a dedicated male clothing library. The pragmatic compromise: accept ~5% gender mismatch (v6 approach) rather than building male clothing from scratch.

### Scene Conflict: Engine-Level Limit (v6→v8 Empirical Bound)

**Fundamental finding after 6 engine iterations:** Engine-level composition CANNOT reduce scene conflict below ~6-15%. The remaining failures are caused by data-level contamination that no engine can fix.

**Why 6-15% is the engine-level floor:**

| Infection Path | % of v8 failures | Root Cause | Engine Fixable? |
|:--------------:|:----------------:|------------|:----------------:|
| Style seed carries its own scene (19% of seeds contain INDOOR or OUTDOOR words) | ~6% | 300+ char pre-written prose containing "咖啡馆" "摩洛哥花园" "布达佩斯链桥" — cannot detect/modify at composition time | ❌ No — would require rewriting the style library |
| C02 dim entry contains scene words (4,388/21,625 entries tagged \|scene=) | ~4% | C02 describes light "at" a scene not pure light ("站在阳光明媚的城市住宅区户外") | ✅ Partial — scene-tag catch reduces but ~30% false-negative rate |
| B01 dim entry contains secondary scene clause | ~2% | "坐在客厅的床上"+场景词"花园" — extracted from multi-clause sentence | ❌ No — would require sentence-level quality filtering |
| P5 technical filler accumulation triggers quality_filter "3+ scene groups" rule | ~1% | Multiple tech dim entries each with slight scene reference → "卧室+户外自然+城市街道" | ✅ Partial — limit P5 to ≤2 dims |

**The true resolution path is DATA-LEVEL, not ENGINE-LEVEL:**
1. Split C02 into sub-libraries by scene type (already done: v4 created C02_室内光照 3,387 + C02_户外光照 1,463 — neutral 16,775 preserved as C02)
2. Rewrite or reclassify 19% of style seeds that hardcode scene locations
3. Build a scene-classified B01 (tag every entry as INDOOR/OUTDOOR for conflict-free matching)
4. Build a dedicated text-only C02 variant containing zero scene references

**v6 empirical scores represent the engine ceiling:** 84.8 avg, 15% scene conflict, 99% on all other rules, 100/100 success rate.

### Space Filler Architecture (字数不足修复)

When output is below 500 chars, use a CONTROL LED filler pass, NOT random dimension picks:

```python
# WRONG: Random filler picks from all tech dims — introduces scene fragments
fillers = [pick(C02), pick(C03), pick(D06), pick(D03)]
txt += "，" + "。，".join(fillers)  # BAD — fragment chain

# RIGHT: Sequential controlled filler — same scene type, same source
while len(txt) < 500:
    # Take from the same dim the style seed used (neutral)
    filler = pick(C02_light_entries_that_match_scene)
    if not filler: break
    txt += "，" + filler.strip('，')
    # Never add more than 2 fillers (3+ causes scene-group collision)
    if len(filler_attempts) >= 2: break
```

**Actually the best approach is to accept shorter prompts (300-400 chars) rather than dilute quality with scene-conflicting fillers.** V6's 301-354 char range with clean content is vastly preferable to v7.1's filler-contaminated text.

### Dimension Library Purification: Cross-Dimension Contamination (v3, 2026-05-28)

**CRITICAL: The #1 source of prompt quality defects is cross-dimension contamination** — entries in dim C that belong to dims A, B, or D. V2 libraries had severe contamination; v3 fixed it with targeted exclusion lists.

#### Identified Contamination Patterns

| Dim | Contaminant | Examples from v2 | Impact | v3 Fix |
|-----|-------------|------------------|--------|--------|
| C04_构图镜头 | Scene/person description | "画面中是一位年轻亚裔女性" / "她居中站立" | 100% of C04 entries were scene/person, not composition | Exclude all (亚裔/亚洲/年轻/女子/女性/年纪/画面中/画面中央/画面主体/着装/皮肤/肤色/留着) — 16K entries → 1.2K pure composition entries |
| D06_氛围情感 | Action/scene/object description | "坐在一把华丽复古风格的扶手椅上" / "墙壁为柔和的米白色" / "亚裔女性身处亲密的室内环境中" | 70% pollution: entries were scene/action not emotion | Exclude all (坐在/站在/躺着/留着/头发/沙发/椅子/桌子/柜子/墙壁/亚裔/女性) — 3.4K entries → 1K pure atmosphere entries |
| C02_光照条件 | Scene word mixing | "站在阳光明媚的城市住宅区户外" / "阳光透过树叶洒下" | 20% entries contain scene references → scene=both false positive | Tag with |scene=1 marker (4388/21625 entries tagged) — engine reads tag to skip |
| A01_年龄性别 | Insufficient variety | Only 15 entries: "儿童" "年轻男性" "年轻亚裔男子" "年轻女子" etc. | No gender/age diversity → engine repeats same | Hand-inject 45+ entries spanning 年轻/中年/老年 × 男性/女性 × 亚洲/白人/黑人 |
| D01_服装款式 | Almost entirely female-coded | 蕾丝/文胸/丝袜/比基尼/高跟鞋 dominate. <1% male-garment entries | Gender filter for male always falls through — no male clothing exists | Requires new male clothing library (fundamental data gap, not solvable by filter) |

#### Purification Rule Sets (from final_build_v3_clean.py)

```python
# C04 exclusion: scene/person description words
C04_EXCLUDE_WORDS = set(
    '亚裔 亚洲 东亚 年轻 女孩 男孩 少女 少年 '
    '画面中 画面中央 画面主体 画面左侧 画面右侧 画面 '
    '女子 女性 男人 女人 男士 女士 '
    '站在 坐在 躺在 跪在 趴在 蹲在 '
    '身着 身穿 穿着 留着 梳着 皮肤 肤色'.split()
)

# D06 exclusion: action/scene/object words
D06_EXCLUDE_WORDS = set(
    '坐在 站在 躺在 跪在 趴在 蹲在 靠在 '
    '留着 梳着 头发 长发 短发 卷发 直发 马尾 '
    '身穿 身着 穿着 搭配 上衣 裙子 裤子 '
    '墙壁 沙发 椅子 桌子 柜子 地毯 窗户 '
    '金色 银色 白色 黑色 红色 蓝色 绿色 '
    '亚裔 亚洲 女性 女子'.split()
)
```

#### C02 Scene Tagging (for engine-level filtering)

When combiling C02, any entry containing a SCENE_WORDS keyword gets a `|scene=1` suffix:

```python
SCENE_WORDS = set('室内 卧室 客厅 厨房 浴室 卫生间 阳台 天台 屋顶 '
                  '咖啡馆 餐厅 酒吧 办公室 教室 图书馆 摄影棚 '
                  '公园 花园 森林 海滩 湖边 街道 地铁 泳池 '
                  '户外 雪地 海岸 沙漠 运动场 草地 沙滩 田野'.split())

if any(w in seg for w in SCENE_WORDS):
    entry = f"{seg}|scene=1"
else:
    entry = seg
```

The engine then marks these to skip or match against B01's scene type.

#### Deduplication Strategy

V2 libraries had massive duplicate counts (C01: 10万→7930 after dedup, i.e. 92% duplication). Dedup on `clean_text.split('|scene=')[0]` to ignore scene markers:

```python
seen = set()
result = []
for item in items:
    clean = item.split('|scene=')[0] if '|scene=' in item else item
    if clean in seen:
        continue
    seen.add(clean)
    result.append(item)
```

### Architecture Decision: Local > API

**API generation was the primary source of hallucinated content (55% of all trial-production violations).** The replacement approach:

```
127 scene templates (骨架) + 17 dim libraries (填充) → 90-rule filter → Pure local prompt
```

| Approach | Quality | Speed | Cost | Hallucination Rate |
|----------|:-------:|:-----:|:----:|:------------------:|
| **Pure local composition** | ★★★☆ | ~500/s | $0 | 0% |
| API free generation | ★★★★ | ~1/min | $0.05 | ~40% |
| **API strict template** | ★★★★☆ | ~1/min | $0.05 | ~10-15% |
| Hybrid (local + API polish) | ★★★★ | ~1/min + $0.05 | TBD |

### 127 Scene Template Library (Skeleton Source)

File: `13_场景库.txt` — 127 scenes across 10 categories (70% daily life, 30% portrait photography).

**CRITICAL: Scene templates contain hardcoded person descriptions, clothing, and poses.** These must be replaced before use:

1. Extract person descriptions from scene text using regex patterns
2. Replace with randomly selected A01_年龄性别 entries (matched by gender)
3. Replace hardcoded clothing with D01_服装款式 entries
4. Use the modified scene as the paragraph skeleton

### Pure Local Composition Flow

**CRITICAL: Gender matching is the #1 source of composition bugs.** Scene text implicitly carries gender ("男人" / "女人"), but the replacement A01 entry must match. The `extract_gender_from_scene()` function scans for gender keywords in the first 60 characters of the scene — this catches ~90% of cases. For gender-neutral scenes ("坐在长椅上"), default to FEMALE and warn in output if mismatch suspected.

**CRITICAL: Scene text may contain non-human subjects** (e.g. "一只猫趴在玻璃橱窗前"). If the matched person pattern hits "一只猫", the replacement will produce "一位年轻亚裔女性一只猫" — nonsensical. Check for animal keywords in the matched segment before replacing.

**CRITICAL: Male clothing must be filtered.** When gender=MALE, only pick D01 entries tagged [TOP], [OUTER], or [BOTTOM]. Exclude [DRESS], [UNDER] (unless context is explicit). 

```python
if g == "M":
    d01_items = [x for x in dim_data["D01_服装款式"] 
                 if x.startswith("[TOP]") or x.startswith("[OUTER]") or x.startswith("[BOTTOM]")]
else:
    d01_items = dim_data["D01_服装款式"]
```

```python
def build_prompt():
    # 1. Pick style
    c01 = pick("C01_美学风格")  # e.g. "高分辨率摄影"
    
    # 2. Pick scene, extract and replace person+clothing
    scene = random.choice(SCENE_LINES)
    person, scene_after, gender = extract_and_replace(scene)
    cloth, scene_after_cloth = replace_clothing(scene_after)
    
    # 3. Pick remaining dimensions
    a02 = pick("A02_发型")    # e.g. "黑色长发自然垂落"
    a04 = pick("A04_表情眼神") # e.g. "面带温柔微笑"
    c02 = pick("C02_光照条件") # e.g. "柔和自然光"
    c03 = pick("C03_色彩调性") # e.g. "温暖的米色调"
    c04 = pick("C04_构图镜头") # e.g. "中景构图"
    d06 = pick("D06_氛围情感") # e.g. "宁静氛围"
    
    # 4. Compose into one paragraph (transition word library)
    segments = [
        f"{c01}风，{scene_after_person}",
        f"{he_she}{a02}，{a04}",
        f"身着{cloth}",
        f"在{c02}中",
        f"画面呈现出{c03}的色调",
        f"以{c04}取景",
        f"整体氛围{d06}"
    ]
    return "，".join(segments) + "。"
```

**Transition word library** (to avoid mechanical concatenation):

| Position | Transitions |
|----------|-------------|
| scene → person | 画面中，/ 一眼望去，/ 镜头聚焦处，/ 只见 |
| hair → cloth | 身着 / 身穿 / 穿着 / 一袭 / 搭配 |
| cloth → light | 在 / 被 / 沐浴在 / 笼罩在 |
| light → color | 映衬出 / 烘托出 / 将色调渲染成 / 让画面呈现出 |
| color → compose | 镜头以 / 构图采用 / 取景为 |
| compose → atmosphere | 整个画面 / 氛围 / 空气中弥漫着 / 场景传递出 |

### gen_one() Composition Rules

**CRITICAL RULE: B01只取1个场景片段, B02只取1个活动行为, D01只取1个服装款式 (非裸体时)**

#### Dimension Mutex Matrix (Pre-Composition Check)

| Dim A | Dim B mutex rule |
|-------|-----------------|
| A01亚裔 | A02≠金发/铂金/亚麻/银白/紫/绿/蓝/粉/红/灰/挑染 |
| A01亚裔 | A04≠蓝眼/绿眼/碧眼/紫眼/灰眼/金眼 |
| A01男性 | D01≠裙子/蕾丝/文胸/内衣(女)/丝袜/高跟鞋/比基尼 |
| A01男性 | D02≠头纱/面纱/珍珠发夹/耳环(女) |
| A01幼儿 | D01≠比基尼/性感/蕾丝/丁字裤/高跟鞋 |
| A05站姿 | 同时出现躺/坐/跪/趴=矛盾 |
| B01室内 | 另一B01片段含户外元素=矛盾 |
| B01户外 | 含床/沙发/浴缸/马桶/灶台=矛盾 |
| C02自然光 | C02=人工光/影棚光=矛盾 |
| D05白天 | D05=夜晚/深夜=矛盾 |
| D06欢快 | D06=忧郁/悲伤=矛盾 |

### Dimension Library Rebuild (v8 Standard, 2026-05-26)

**CRITICAL: Always rebuild dimension libraries before mass production.** Raw extracted libraries contain fragmented entries, banned words, and cross-dimension contamination. The v8 rebuild pipeline fixes all three.

#### Rebuild Pipeline (17 Dimensional Libraries → Clean, Tagged, Deduplicated)

```
Raw library (1.4M lines) → Clean by dimension rules → Tag by 108 sub-dimensions → Dedup → Clean library (691K lines, 100% tagged)
```

| Step | Action | What it removes | Threshold |
|------|--------|----------------|:---------:|
| 1 | Clean tags | [NATURAL] [UNNATURAL] [MALE] etc. | All |
| 2 | Min char filter | Fragments < 6 characters | ≥6 chars |
| 3 | Banned word filter | Metaphors (仿佛/犹如/宛如), tech terms (量子/粒子/芯片), photography jargon (对焦/景深/快门/光圈/ISO), English words | 0 tolerance |
| 4 | Dedup (first 30 chars) | Duplicate content | First 30 chars |
| 5 | Tag assignment | Per-dimension tag function (see below) | 100% tagged |

#### Per-Dimension Tag Functions (v8 Standard)

Each library file entry gets a canonical tag prefix `[TAG]` based on content analysis:

| Dimension | Tags | Function |
|-----------|------|----------|
| A01_年龄性别 | MALE / FEMALE / CHILD / GROUP | 性别/年龄关键词匹配 |
| A02_发型 | LONG / SHORT / CURLY / STRAIGHT / UP / COLORED | 发长+造型匹配 |
| A03_肤色 | FAIR / TAN / DARK / OLIVE / OTHER | 肤色描述匹配 |
| A04_表情眼神 | HAPPY / SAD / CALM / SURPRISED / ANGRY / EYE / OTHER | 情绪+眼部动作匹配 |
| A05_姿势 | STAND / SIT / LIE / KNEEL / BEND / HAND / OTHER | 身体姿态匹配 |
| B01_场景环境 | INDOOR / OUTDOOR / UNKNOWN | 室内/室外场景词匹配 |
| B02_活动行为 | STATIC / MOVE / HAND / FACE / OTHER | 活动类型匹配 |
| C01_美学风格 | REALISM / PHOTO / ART / FASHION / ABSTRACT / MINIMAL / OTHER | 艺术风格类别匹配 |
| C02_光照条件 | NATURAL / ARTIFICIAL / SOFT / HARD / OTHER | 光源类型+软硬匹配 |
| C03_色彩调性 | WARM / COOL / NEUTRAL / VIVID / MONO / OTHER | 色温+饱和度匹配 |
| C04_构图镜头 | CLOSE / MEDIUM / FULL / CENTER / FRAME / ANGLE / OTHER | 景别+构图法则匹配 |
| D01_服装款式 | TOP / BOTTOM / DRESS / OUTER / UNDER / UNIFORM / OTHER | 服装类型匹配 |
| D02_配饰鞋帽 | NECK / EARRING / RING / BRACELET / HEAD / SHOE / BAG / GLASSES / SCARF / OTHER | 配饰部位匹配 |
| D03_材质质感 | FABRIC / LEATHER / METAL / GLASS / WOOD / STONE / SKIN / TEXTURE / OTHER | 材质类型匹配 |
| D04_动态效果 | WIND / WATER / LIGHT / SMOKE / MOTION / OTHER | 动态类型匹配 |
| D05_天气时间 | SUNNY / CLOUDY / RAINY / SNOWY / FOGGY / DAY / NIGHT / SEASON / OTHER | 天气+时段匹配 |
| D06_氛围情感 | PEACEFUL / WARM / MELANCHOLY / ROMANTIC / ELEGANT / VIBRANT / MYSTERIOUS / SOLEMN / OTHER | 情感类型匹配 |

#### Banned Words (0 tolerance in all dimensions)

- **Metaphors:** 仿佛, 犹如, 就像, 好似, 宛如, 如同, 宛若
- **Tech terms:** 量子, 夸克, 粒子, 齿轮, 青铜, 全息, 芯片, 像素, 矩阵, 光纤, 纳米
- **Photography jargon:** 对焦, 焦平面, 景深, 快门, 光圈, ISO, 感光度, 曝光补偿, 白平衡, 焦点清晰, 浅景深, f/
- **English words (4+ chars):** foliage, texture, lighting etc. (exception: brand names like Nike/Gucci)
- **Min length:** 6 Chinese characters minimum per entry

#### Dimension Governance (Legacy v7 — replaced by v8 rebuild)

*Previous governance rules for the 7-key-dimension approach. Now superseded by the full v8 automated rebuild.*

### 90-Rule Conflict Detection Engine (v9.4+)

The 90-rule engine detects conflicts across 7 dimensions. Rules 1-55 were developed from 400-item word-by-word audits; rules 56-70 from v9.3 trial production; rules 71-90 from comprehensive 10-trial audit revealing 46 violations across 14 dimensions.

| Rule Group | Coverage | Issues Found | 
|------------|----------|:-----------:|
| 1-25 (Original) | Basic contradictions (stand+water, lie+stand, Asian+hair, male+dress...) | ~65% |
| 26-41 (Extension 1) | Baby+adultification, double-shoes, gore, Asian+unnatural hair/eye expanded | ~9% |
| 42-55 (Extension 2) | Style 2-char truncation, male+female-clothing universal, Asian+hair v2, injury/unconscious, nude+clothing, physics impossible, gender conflict | ~8% |
| 56-70 (Extension 3) | Outdoor-style+indoor-content, soldier+female-jewelry, building-material conflict, person-count, rural+modern mix, professional+unmatched-clothing | ~10% |
| 71-90 (Extension 4) | Lighting system conflict (sunlight+stage-light), depth-of-field+all-details clear, close-up+wide-shot conflict, pose contradiction, clothing stacking enhanced, style-name format, night+day time, nude+warm-family, photography meta-instructions, English words, multi-focus-plane physics impossible, bedroom+tile floor | ~8% |

**Key new rules (71-90, from 10-trial full audit):**

| # | Rule | Example match | Source issue |
|---|------|--------------|-------------|
| 71 | 光照系统矛盾(自然光+舞台光) | 夕阳+聚光灯同prompt | Trial 5: forest sunset + stage spotlight |
| 72 | 景深+全细节矛盾 | 浅景深+每个细节都清晰 | Trial 1/3: DOF claim + full detail |
| 73 | 特写+大场景矛盾 | 特写+湖泊占据下半部分画面 | Trial 3/7 |
| 74 | 跪+面向+侧脸姿态矛盾 | 跪着面向镜头又侧脸仰望 | Trial 4 |
| 75 | 蜷腿+举手姿态矛盾 | 膝盖靠近胸部+同时抬手握风车 | Trial 8 |
| 76 | 服装堆叠(内+外+裙) | 衬衫+裙子+外套同时 | Trial 4 (9 items) |
| 77 | 风格名格式异常(照片风前缀) | "一张肖像照片风" | Trial 8 |
| 78 | 夜晚+白天时间矛盾 | 星空+阳光/夕阳 | Trial 5/7 |
| 79 | 裸体女性+穿衣男性 | 裸体+男子穿着西装 | Trial 1 |
| 80 | 摄影元指令 | "对焦""快门""光圈""ISO" | Cross-cutting |
| 81 | 多焦段矛盾(三焦平面都清晰) | 前景清晰+中景清晰+背景清晰 | Trial 1 |
| 82 | 室内+外部建筑构件 | 室内+天空/立柱/屋顶瓦片 | Trial 10 |
| 83 | 亚裔+非天然棕发 | 亚裔+棕色长发/栗色 | Trial 8 |
| 84 | 床+食物矛盾 | 床上+鸡肉/饺子/菜肴 | Trial 6 |
| 85 | 三手增强(左+右+双手跨段) | 左手+右手+双手分段出现 | Trial 3 |
| 87 | 风格名+内容重复 | "一张肖像照片风，一张肖像照片" | Trial 8 |
| 88 | 全裸+温馨家庭矛盾 | 裸体+温馨/家庭氛围 | Trial 1 |
| 89 | 非必要英文词混入 | "foliage""texture" | Trial 3/10 |
| 90 | 卧室+瓷砖地面矛盾 | 卧室+瓷砖/大理石 | Trial 1 |

### User Preferences (格林主人, captured 2026-05-26)

- **Creative/cosplay animal descriptors OK:** "他白色毛发和尖耳朵" passes QC (acceptable as stylistic/creative choice)
- **Gender mismatch is a hard FAIL:** "她留着胡须" fails. Male-pattern descriptors on female pronoun = reject.
- **Mechanical rhythm is acceptable:** Clear factual description > fancy transitions. Don't over-engineer fluency at the expense of precision.
- **Single paragraph only:** No multi-section prompts. One continuous paragraph per prompt.
- **Pure local composition is the PRIMARY method** — API is only for optional polish pass.
- **Application scenario text-to-image width is the default.** ~200 words for a typical prompt.
- **Staging/testing must be separated from mass production.** Never import mass_production_v9.py as a module — it triggers the main loop. Use standalone scripts instead.

### Local LLM Polish (LM Studio + Ollama)

**LM Studio** (installed on Windows, API on `http://172.31.32.1:8080`):
- `/api/v1/chat` — Native API (returns `reasoning` + `message` blocks)
- `/v1/chat/completions` — OpenAI-compatible
- `POST /api/v1/models/load` — Load model to memory (takes 3-5s for 9B)
- **All "heretic/uncensored/thinking" models force-output reasoning tokens** — `thinking: False` does NOT disable model-internal reasoning. These models waste 80% of tokens on thinking and produce no clean output.
- **Best for prompt polish:** Models without built-in reasoning (like NQLSG on Ollama — not available on LM Studio)

**Ollama** (installed on Windows, API on `http://172.31.32.1:11434`):
- NQLSG:latest (8.4GB) — ~6s/item, no thinking, clean output
- OpenAI-compatible endpoint: `/v1/chat/completions`
- Loaded models respond in ~1s; cold-start models take 10-15s

**WARNING:** Starting LM Studio may crash Ollama (port conflict or GPU memory exhaustion). Only one inference engine can run at a time on this 4090 (48GB).

### Worst Dimension Library Contamination (v8 Audit Results + v3 Fix)

| Dimension | v2 Contamination | v3 Clean Rate | v3 Entry Count | v3 Fix |
|-----------|:----------------:|:-------------:|:--------------:|--------|
| C04_构图镜头 | 94% pollution — 16K/17K entries were scene/person descriptions | 100% pure | 1,221 | Excluded all (亚裔/亚洲/年轻/女子/女性/画面中/画面中央/画面主体/皮肤/肤色) |
| D06_氛围情感 | 70% pollution — 2.4K/3.4K entries were action/scene descriptions | 100% pure | 1,077 | Excluded all (坐在/站在/躺着/留着/头发/墙壁/女性/亚裔) |
| C02_光照条件 | 20% entries with mixed scene words | Tagged (4,388 marked) | 21,625 | `|scene=1` marker for engine-level skip |
| A04_表情眼神 | 59% kept (v8: 10,775→6,389) | N/A (kept v2 baseline) | 1,731 | Transferred from v2 with scene-word filter |
| A05_姿势 | 93% kept (v8: 74,557→69,676) | N/A (kept v2 baseline) | 4,007 | Transferred from v2 with scene-word filter |
| A01_年龄性别 | Only 15 hand-curated entries | Expanded | 45 | Manual inject of age/gender/race combinations |

### Dimension Library v8 File Locations (2026-05-26)

```bash
v7 raw (original):     /mnt/d/Hermes/1000000提示词/高质量模板/维度库_api_v7/
v7 governed (cleaned): /mnt/d/Hermes/1000000提示词/高质量模板/维度库_api_v7_governed/
v8 rebuilt (tagged):   /mnt/d/Hermes/1000000提示词/高质量模板/维度库_v8_rebuilt/
v8.1 clean (fine):     /mnt/d/Hermes/1000000提示词/高质量模板/维度库_v8.1_clean/
```

### Dimension Library v3 / v10.1 File Locations (2026-05-29, CURRENT BEST)

```bash
v3 (purified):         /mnt/d/Hermes/1000000提示词/高质量模板/维度库_final_build_v3/
                       107,762 entries — CURRENT BEST library (17 dims)
Combine engine (v10.1):   /mnt/d/Hermes/1000000提示词/高质量模板/维度库/combine_engine_v10_1.py
                       CURRENT BEST engine: 100/100 gen, 89.6 avg, gender 0%, scene 5%, three-hand 0%
Batch script (v10):    /mnt/d/Hermes/1000000提示词/大生产/代码/batch_produce_v10.py
QC filter:             /mnt/d/Hermes/1000000提示词/高质量模板/维度库/quality_filter.py
PromptFactory.py:      /mnt/d/Hermes/1000000提示词/PromptFactory.py (defaults to v10.1)

```bash
v2 (baseline):         /mnt/d/Hermes/1000000提示词/高质量模板/维度库_final_build_v2/
                       1,043,271 entries — most rows but contaminated C04/D06/D03
v3 (purified):         /mnt/d/Hermes/1000000提示词/高质量模板/维度库_final_build_v3/
                       110,235 entries — purified C04 (0% contamination), marked C02, pure D06
v4 (C02 split):        /mnt/d/Hermes/1000000提示词/高质量模板/维度库_final_build_v4/
                       110,265 entries — C02 split into C02_光照条件(16,775 neutral) + C02_室内光照(3,387) + C02_户外光照(1,463)
Combine engine (v6):   /mnt/d/Hermes/1000000提示词/高质量模板/维度库/combine_engine_v6.py
                       Best composition engine: 100/100 gen, 84.8 avg, 15% scene conflict
Combine engine (v8):   /mnt/d/Hermes/1000000提示词/高质量模板/维度库/combine_engine_v8.py
                       Highest scoring: 88.5 avg, 94% scene pass, 100% hands/gender/race, uses v3 lib
QC filter:             /mnt/d/Hermes/1000000提示词/高质量模板/维度库/quality_filter.py
                       10-rule standalone filter (metaphor/tech/scene/race/hand/stacking/word-count/sex)
Trial outputs:         /mnt/d/Hermes/1000000提示词/试生产100条_v{6,7,7_1,8,8_final,9}.txt
Final build script:    /mnt/d/Hermes/1000000提示词/高质量模板/维度库/final_build_v3_clean.py
C02 rebuild script:    /mnt/d/Hermes/1000000提示词/高质量模板/维度库/rebuild_c02_v4.py

### 2026-05-28 Session Outputs (Mass Production)

- `/mnt/d/Hermes/1000000提示词/大生产/v8_1_batch/` — 100,007 items (primary, v8.1 engine)
- `/mnt/d/Hermes/1000000提示词/大生产/v8_clean/` — 44,409 items (post-filtered v8)
- Total usable: 144,416 items
- Duration: 43,322s (12h) for 100K, 8 threads, 2.3 items/s
- QC pass rate: 90.6%
- Production scripts: `/mnt/d/Hermes/1000000提示词/大生产/代码/batch_produce_v8.py` and `batch_produce_v8_1.py`
- Clean script: `/mnt/d/Hermes/1000000提示词/大生产/代码/clean_v8_batch.py`
- Full reference: `references/2026-05-28-v8_1-hard-gender-production.md`

### 6-Layer Post-API Defense

1. **Layer 1** — gen_one()前置过滤 (4 pre-filters: Asian+hair, Asian+eye, male+clothing, B01 single-scene)
2. **Layer 2** — 55-rule post-API conflict regex
3. **Layer 3** — Style preamble integrity (check "风"前≥2 chars, 2-char truncation, format anomaly)
4. **Layer 4** — Multi-scene coexistence (16 scene types, 3+ incompatible = abort)
5. **Layer 5** — People count consistency + gender consistency ("她"+"他" within 200 chars = abort)
6. **Layer 6** — API system prompt (embedded prohibitions)

---

## Section C: Mass Generation at Scale

*Absorbed from: `cronjob-batch-generator`*

### Method Selection Guide (2026-05-26 Updated)

| Method | Items/min | Quality | Cost | Best For |
|--------|:---------:|:-------:|:----:|----------|
| **Pure local composition** (v1.5) | **~40,000** | ★★★★☆ | $0 | **Primary method: 10K-100K+** |
| Hybrid: local + API polish strict | ~1/min | ★★★★☆ | $0.05/item | Premium batch, <500 |
| Hybrid: local + Ollama polish (NQLSG) | ~10/min | ★★★★☆ | $0 (GPU) | Medium batch, <1000 |
| Python template combo (legacy) | ~30,000 | ★★★ | $0 | Quick bulk fill (lower quality) |
| Single AI call (legacy) | ~1/min | ★★★★ | $0.05 | <100, premium quality test |

### Cronjob Architecture

```bash
# Create N cronjobs (one per output shard)
hermes cron create --name pg-02 --schedule "every 1m" --repeat 5000 \
  --deliver local \
  --prompt '【高速生成-{FILE_NAME}】wc -l {PATH}>={TARGET}则退出。生成5条（严格{MIN}-{MAX}字！wc -m验证！）echo逐条追加。7维度完整+传统色名。写完后"ok{N}"。'
```

**State management:** Each cronjob checks file length at start, skips if target reached. Provides automatic self-termination and crash recovery.

### 九层模板法 (Core Quality Framework)

Each generated item is one continuous paragraph weaving all 9 layers:

| Layer | Content | Word Count |
|:-----:|---------|:----------:|
| 1 | **风格技法**: 风格名+技法特征+笔触+画布 | 10% |
| 2 | **镜头构图**: 景别+视角+构图法则 | 5% |
| 3 | **主体姿势**: 位置+姿态+头角度+眼神+手指+腿 | 20% |
| 4 | **材质细节**(核心): 头发+皮肤+服装面料+褶皱+配饰 | 30% |
| 5 | **前中后景**: 前景→中景→背景 | 10% |
| 6 | **色彩系统**: 主色+辅色+对比(传统色名) | 10% |
| 7 | **光影系统**: 光源+软硬+高光+阴影+轮廓 | 10% |
| 8 | **氛围情感**: 收尾+氛围+主体状态 | 3% |
| 9 | **出圈要素**: 风格致敬/悖论/反差/错位 | 2% |

### Python Template Combination Engine

When quality allows template-combination:

```python
styles = load_lines("15_女性风格库.txt")
outfits = load_lines("16_女性穿搭库.txt")
poses = load_lines("17_女性姿势库.txt")
scenes = load_lines("13_场景库.txt")

def gen():
    style = random.choice(styles)
    scene = random.choice(scenes)
    # ... layer-by-layer assembly
```

**Performance:** ~500 items/sec. Use for bulk-fill after cronjobs set the quality baseline.

---

## Section D: Chinese Aesthetic Prompt Content

*Absorbed from: `chinese-aesthetic-prompt-engineering`*

### 7-Dimension Natural Fusion Framework

Each high-quality prompt must naturally weave these 7 dimensions into a single 500-800 character Chinese paragraph:

| # | Dimension | Key Elements | Approx Words |
|---|-----------|-------------|:------------:|
| 1 | **风格技法** | Style name + technique specifics (brushwork, medium, canvas) | 2-4 sentences |
| 2 | **镜头构图** | Shot type, angle, composition rule | 1-2 sentences |
| 3 | **主体姿势动作** | Position, body posture, head angle, eyes, hands, legs | 5-8 sentences |
| 4 | **材质细节** | Hair, skin, clothing fabric, wrinkles, accessories | 8-12 sentences |
| 5 | **前中后景** | Foreground → Midground → Background | 3-5 sentences |
| 6 | **色彩系统** | Main + aux + contrast colors, **must use Chinese traditional names** | 3-4 sentences |
| 7 | **光影氛围** | Light source + quality + highlights + shadows + rim light | 4-6 sentences |

### Format Banned
- ❌ No titles, numbers, or sections
- ❌ No tech words (量子/夸克/粒子/齿轮/青铜/全息/赛博)
- ❌ No simile words (仿佛/犹如/就像/好似/宛如/如同)
- ❌ No digital measurements (45度/3厘米/5毫米)
- ❌ No template openings like "一幅xxx风格的画作"

### Model-Specific Format Adaptation

| Model Architecture | Prompt Format | Quality Tokens | Markers |
|:-----------------:|:-------------|:--------------:|:-------:|
| **SD1.5/SDXL/FLUX.1** (CLIP) | English comma-separated tags | masterpiece, best quality | use (()) weighting |
| **Z-Image/Qwen-Image** (Qwen) | Chinese natural language | None needed | Complete sentences only |
| **FLUX.2 Dev/Klein** (Mistral) | English natural language | None needed | Avoid SD markers |

### Traditional Chinese Color Name Dictionary

**Red:** 朱红/胭脂/银红/殷红/绛紫/绯红/檀色/赭色/赤金/彤色
**Orange-Yellow:** 琥珀/橘黄/藤黄/鹅黄/杏黄/姜黄/蜜色/牙色/金色/铜色
**Green:** 石绿/翠绿/竹青/苍绿/黛绿/碧色/草绿/松花绿/豆绿/茶绿
**Blue:** 群青/靛蓝/钴蓝/黛蓝/天青/月白/景泰蓝/宝石蓝/普鲁士蓝
**Purple:** 藕荷/丁香/紫檀/玫瑰紫/茄色/雪青/紫罗兰
**Brown:** 赭石/檀褐/栗色/茶色/褐色/咖啡/古铜/驼色/卡其/玳瑁
**Black-Gray-White:** 墨黑/纯白/月白/象牙白/银灰/烟灰/铅灰/骨白/米色/霜色

### Women's Style Combination Tokens

**Style tokens:** 美艳/冷艳/性感/魅惑/可爱/萌萌哒/青春/活力/性冷淡/优雅/慵懒/甜美/飒爽/清纯/妩媚/知性/元气/温柔/酷飒/复古

**Combination method:** Pick 2-3 per item: 美艳+冷艳, 可爱+性感, 清纯+魅惑, 青春+元气, 性冷淡+优雅, 萌萌哒+活力, 酷飒+美艳

---

## Section E: Post-Generation Quality Cleanup

### Face Color Terms Removal

Remove these from all generated prompts (string replacement, not line deletion): 腮红, 晒红, 晒伤, 红润, 潮红, 绯红, 嫣红, 酡红, 晕红, 泛红, 透红, 涨红, 羞红, 红晕, 红潮, 面色红润, 面色潮红, 脸颊红润, 脸颊泛红, 皮肤红润, 肌肤红润

### Multi-Limb Detection (三手/三腿清理)

Split by comma/semicolon. Count segments starting with hand/leg keywords (excluding false positives like 手表/手链/手机). When ≥3 detected, remove the last excess segment.

### Lighting Wording Cleanup

- "泛着" → "带着"
- "光晕" → "光"
- "镀上" → "染上"
- "红润" → "透亮"
- "倾泻" → "照入"
- "投下斑驳" → "落下斑驳"

---

## Section F: 格林主人 Rules (Cross-Cutting Constraints)

| Rule | Enforcement |
|------|------------|
| No batch/loop-generated worker configs | Skill is defective |
| No Docker (native only) | Abort generation |
| No placeholder/sample code stubs | Complete implementation |
| Task begins with full-context audit | Skip = bug |
| Every tool call → checkpoint | Gear system enforces |
| 删除前必须先备份 | Hard rule |
| 任何QC必须逐字审核，不能靠抽样推断 | 500-item audit methodology |
| 禁止本类型 — permanent ban for this task class | Hard constraint in combinatorial rules |
| "十倍丰富度补充" = genuinely expand variety space | Diversity mandate |
| **No batch/preset/hammer approaches to content generation** | Each prompt must be individually reasoned |

### Banned Content Categories (Permanent)
- ❌ 餐饮甜品静物 (food/dessert/still life — no artistic narrative)
- ❌ 单纯室内环境/建筑描述无主体 (bare interior/architecture without human subject)
- ❌ Scenes lacking emotional/atmospheric dimension

### Output Content Density Constraint (格林主人 2026-05-27)

**AI生成的提示词不能太干也不能过度堆细节。** 适用于所有模板。

- ❌ **禁止数值参数**：毫米/厘米/dB/色值/百分比/角度等
- ❌ **禁止微观生物学细节**：器官名称、肌肉名称、毛细血管、毛密度等
- ❌ **禁止过度技术参数**：色温4800K、焦距50mm、f/2.0、ISO等
- ✅ **用视觉化、氛围化语言**："暖金色晨光"代替"色温4800K"
- ✅ **正常叙事语言**：每个场景2-5句话，写清楚角色+动作+环境+氛围即可

#### 内容密度示例

**❌ 太干（无细节）：**
```
一位年轻女性站在阳光中。
```

**✅ 适中：**
```
一位年轻女性站在午后阳光中，长发被微风轻轻吹起，米色长裙在光线下泛着柔和的光泽。身后是老旧的砖墙，爬满常春藤。
```

**❌ 过度堆细节（有数值参数+微观结构）：**
```
一位年轻女性站在阳光中，鼻尖翕动频率每秒3次，眼睑边缘3根睫毛，毛细血管清晰可见。光照角度45度，色温5500K，阴影长度2倍身高...
```

### Required Content Categories
- ✅ 小红书/社交媒体网红热点
- ✅ Artstation / art gallery high-aesthetic scenes
- ✅ 色情写真 (erotic photography/boudoir)
- ✅ 诱惑魅惑 (seduction/provocative)
- ✅ 日常场景与生活写真 (10x diversity required)

### Phase-Based Execution Commandment
1. Write minimal test → run on ONE file → check → fix → THEN scale
2. Do NOT write one giant script and run it whole
3. After each phase: review + report before starting next phase
4. Do NOT ask permission for obvious next steps — just execute and report
5. If user says "操你妈为什么又卡死了" or "为什么不继续" → immediate stop, check todo/wake_guide, report state, execute next step. No verbose apology, no re-analysis.

### Task Resumption Protocol
- Every wake/resume → read `wake_guide.json` AND check `task_current.json`
- Before ANY new work → session_search for ongoing task first
- Use `todo` tool to track granular progress
- Notify user: "从[已完成步骤]继续，下一步是[待完成步骤]"

### Non-Destructive Restart Rule
**NEVER `os.remove(OUTPUT_FILE)` in a production script.** Always append. Track progress by checking file line count.

---

## Pitfalls (Consolidated, v8.1+)

1. **User will spot ANY laziness. Zero tolerance for batch/placeholder/partial implementation.** ← #1 rule. Every prompt must be individually composable.
2. **Never use API as primary generator** — API hallucinates 55% of content (soldier+hair-ornament, depth-of-field+all-details-clear, 3-person-in-one-person-scene, mixed lighting systems). API is ONLY for final fluency polish under strict SYSTEM_PROMPT constraints.
3. **Dimension library quality determines final prompt quality.** Raw libraries contain up to 60% garbage (fragments <8 chars, metaphors, photography jargon, English words, animal descriptions). Always rebuild before mass production.
4. **Scene library hardcodes person/clothing/pose** — must extract and replace before composing. Otherwise A01/D01 are locked to scene defaults.
5. **Gender matching is the #1 composition bug.** Scene text gender must propagate correctly to pronoun (她/他), clothing selection (D01 filter), and hairstyle (A02 gender match). One mismatch = subjectively broken prompt.
6. **Non-human subjects in scene text** — Animal/pet scenes (猫/狗/鸟) must be detected and rejected if the scene wants a human subject.
7. **Tag coverage must be 100%** on at least 5 core dimensions (A01, A02, A04, C01, D01) — the rest on v8 standard. Untagged entries cause gender/pose/style mismatches in composition.
8. **A04_表情眼神 is the dirtiest dimension in raw data** — Contains pose descriptions (站/坐/跪), animal features (猫耳/竖瞳), clothing descriptions (穿着/戴着). The v8.1 clean removed 41% of A04 entries.
9. **C04_构图镜头 has the most photography jargon** — 41K/172K entries (24%) contain 对焦/景深/快门 etc. These must be removed before composition.
10. **Creative/cosplay descriptors OK** — "白色毛发和尖耳朵" passes QC as stylistic. Only clear errors (gender mismatch, photography jargon, banned words) are failures.

1. **三手矛盾 = #1 bug** — Every person has exactly 2 hands. Never combine static hand description with active doing.
2. **B01只取1个** — Two different scene fragments will always conflict. This is THE #1 composition rule.
3. **B02只取1个** — Prevents three-hand conflicts (multiple actions = multiple hand descriptions)
4. **D01只取1个** — Single outfit. Taking 2+ causes clothing stacking.
5. **A05只取1个** — Prevents pose contradiction (standing + lying = impossible)
6. **字数控制困难** — AI generates 1.5-2x intended length. Always verify with `wc -m` post-generation.
7. **delegate_task too slow for scale** — Each call produces only 5-8 items with 42K token overhead. Use cronjob or Python script for scale.
8. **Cronjob prompt size limit** — Keep under ~800 chars. Must contain: check-condition + generate-command + quality-constraints + write-command.
9. **格式不是通用的** — Different model architectures (CLIP/Qwen/Mistral) need different prompt formats. Never assume SD format works for all.
10. **Cross-dimension contamination** — Skin library contains hair keywords. Never trust `extract_segment()` to keep boundaries clean across commas.
11. **Random weights trap** — When loading upscale models, verify weight loading. `strict=False` with >30% missing = random weights.
12. **API key-name bug** — Without explicit JSON template in system prompt, API invents its own key names.
13. **Accessory mismatch** — 12_配饰鞋帽库 may contain non-accessory descriptions. Verify before composing.
15. **Repetitive truncation loop** — If extraction truncation persists after 3 fixes, the approach is fundamentally wrong — replace with sentence-level classification.
16. **Scene inconsistency in dimension entries (~30% false-positive)** — Dimension library entries carry scene words mixed in: C02 entries say "户外阳光", D06 entries say "海滩落日". Even with correct B01→D05 scene matching, other dims introduce conflicting scene words. True fix: split dimension libraries by scene type (C02_光照_室内 / C02_光照_户外).

17. **Engine-level scene conflict resolution has a ~15% floor (PROVEN v6→v7.1, 2026-05-28).** No amount of engine logic can fix data-level contamination. The 4 infection paths are: (a) style seeds with hardcoded scenes (19%), (b) C02 entries with embedded scene words (20%), (c) B01 entries with secondary scene clauses (2%), (d) P5 filler accumulation (1%). Any combination hits 3+ scene groups = quality_filter FAIL. True fix requires sub-library splitting at the data level.

18. **Gender filter is useless for D01 without male clothing data.** All current dimension library D01 entries are female-coded (蕾丝/文胸/丝袜/高跟鞋/比基尼). When gender=male, gender_filter() excludes ~95% → falls through to unfiltered → still female clothing. Either accept gender mismatch at ~5% rate (v6 choice) or build a dedicated male clothing library.

19. **Paragraphic output is strictly superior to mechanical join for quality.** V6's paragraphic architecture (5 segments × logical grouping) eliminated v4.1's line-internal concatenation noise and improved readability despite shorter char length (301-354 vs 500-800). The trade-off is shorter text but cleaner structure — which is the correct trade for aesthetic-grade text-to-image prompts.

20. **NEVER read-and-write the same file in one loop.** Python's `open(path)` for reading while `open(path, 'w')` is also open truncates the file. Re-read the iterator sees EOF. Always read entire content into memory first, then write: `lines = list(open(path)); with open(path,'w') as f: for l in lines: ...` This bug collapsed D02_配饰鞋帽 from 2,498 to 1 entry in `repair_v4_labels.py`.

## References

### Library Engineering
- `references/extraction-strategy-benchmark.md` — Multi-strategy extraction pipeline benchmark (2026-05-23)
- `references/extraction_evolution_v1_to_v4.md` — Evolution of extraction methods
- `references/dimension_analysis_results.md` — Exhaustive dimension analysis from to_chi
- `references/final_build_pipeline.md` — final_build.py approach
- `references/api_batch_decomposition.md` — API-based batch decomposition
- `references/tochi_distribution_analysis.md` — Full distribution report (518K lines)
- `references/bertopic_tochi_analysis.md` — BERTopic integration for theme discovery
- `references/combinatorial_rules.md` — Rule set for prompt composition
- `references/100_scene_template_guide.md` — 100-scene template architecture
- `references/2026-05-27-dimension-rebuild-v2-combine-v4-quality-filter.md` — v2 dimension rebuild (1,043K entries, multi-level classification) + v4 combine engine (scene consistency) + quality filter deployment

### Composition & QC
- `references/400-prompt-audit-summary.md` — 4 batches × 100 prompts word-by-word audit
- `references/500-prompt-final-audit.md` — 5th batch + merged 500-item final audit (88 problems, 99% coverage)
- `references/dimension-conflict-matrix.md` — Complete mutex matrix
- `references/dimension_conflict_matrix.md` — Dimension conflict matrix (alternate)
- `references/v8_post_clean_pipeline.md` — 8-step post-clean pipeline
- `references/mass_production_guide.md` — Mass production guide

### Aesthetic Content & Mass Generation
- `references/model-format-specs.md` — Model format adaptation guide
- `references/10subagent-workflow.md` — 10-sub-agent parallel generation workflow
- `references/massive-generation-pitfalls.md` — Python batch generation pitfalls
- `references/100k-prompt-campaign.md` — 100K prompt campaign session notes
- `references/female-template-library-guide.md` — Template library building guide
- `references/three-hand-detection.md` — Three-hand detection algorithm
- `references/2026-05-23-10万-prompt-generation.md` — 10万 prompt generation session
- `references/2026-05-23-dimension-library-building.md` — Library building session
- `references/2026-05-23-library-cleaning-battle.md` — Library cleaning session
- `references/2026-05-24-trial-production-session.md` — Trial production session
- `references/2026-05-25-mass-production-audit.md` — Mass production audit

### Full Prompt Examples
- `references/prompt-library-02-format.md` — modern_art_prompts_02.txt format spec
- `references/prompt-library-06-format.md` — modern_art_prompts_06.txt format spec
- `references/prompt-library-07-format.md` — modern_art_prompts_07.txt format spec
- `references/prompt-library-09-format.md` — modern_art_prompts_09.txt format spec
- `references/full-examples.md` — 7-dimension generation examples
- `references/library-index.md` — Library file index
- `references/library-tag-cleanup.md` — Library tag cleanup scheme
- `references/composer-engine-v15.md` — V15 composition engine session
- `references/quality-loop-methodology.md` — Quality loop methodology
- `references/storyboard-director-framework.md` — Storyboard director framework
- `references/source-library-defect-diagnosis.md` — 13-class defect diagnosis
- `references/2026-05-28-engine-v6-v7-paragraphic-scene-gender-fix.md` — v6 paragraphic architecture, gender state machine, scene conflict engine-level ceiling proof, cross-dimension contamination patterns
- `references/2026-05-28-v8_1-hard-gender-production.md` — v8.1 hard gender filter (3-layer), child protection, pronoun consistency check, batch production deployment (8-thread, 100K items in 12h), QC rejection statistics
- `references/2026-05-28-v8_1-hard-gender-production.md` — v8.1 hard gender filter, child protection, pronoun consistency check, batch production deployment notes

### Scripts
- `scripts/exhaustive_dim_analysis.py` — Exhaustive dimension analysis
- `scripts/surgical_clean.py` — Surgical clean extraction
- `scripts/dimension_governance.py` — Dimension governance pipeline
- `scripts/deep_qc.py` — Advanced QC with 55-rule engine
- `scripts/compose_trial_v2.py` — Trial composition
- `scripts/composer_v15.py` — V15 composer
### Scripts
- `scripts/massive-prompt-generator.py` — Alternative batch generator
- `scripts/clean-lighting-overdescriptions.py` — Lighting description cleaner
- `scripts/quality_filter.py` — 10-rule standalone quality filter (metaphor, tech, 3-hand, scene-conflict, race-conflict, etc.) — CLI and Python API

### Templates
- `templates/cronjob-config.md` — Cronjob config template
- `templates/composer-engine-template.py` — Composer engine template
- `templates/v9_script.py` — v9 production script template

## 回滚方案
### 内容回退
1. 恢复到上一个版本的文件
2. 确认生成内容无退化
3. 必要时重启生成流程

### 恢复步骤
1. 从备份目录恢复原始文件
2. 验校内容完整性
3. 对比前后差异确认回退成功
