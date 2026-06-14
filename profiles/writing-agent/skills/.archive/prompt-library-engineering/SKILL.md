---
name: prompt-library-engineering
description: "Build high-quality specialized prompt dimension libraries from raw data — extraction, surgical cleaning, dimension analysis, combinatorial rules, and quality validation"
version: 1.0.0
tags: ["prompt-generation", "data-extraction", "library-building", "dimension-analysis", "quality-engineering"]
trigger: when user asks to build prompt libraries, analyze dimensions, extract from to_chi, create combinatorial rules, or generate large-scale prompts; ALSO auto-load on any work involving to_chi data, dimension extraction, prompt composition, or library construction
---

# Mass Prompt Generation from Dimension Libraries

## Overview

## 触发条件
- 用户提及此功能相关关键词时
- 遇到此领域的标准问题时
- 需要执行该领域的标准操作时

Generate 100K+ high-quality AIGC prompts by randomly sampling from pre-built dimension libraries (V7_api_v7, ~2M entries) and combining fragments via DeepSeek API.

## v9 Architecture (Current Best — 2026-05-26)

Major improvements over v8:

1. **B01: 只取1个场景片段** — 完全禁止两个场景共存。v8.1的问题：B01取了2个片段（室内+户外），即使过滤了关键词，API也会强行融合。
2. **亚裔特征前置过滤** — A01含"亚裔"时，A02过滤金发/铂金/亚麻/银白，A04过滤蓝眼/绿眼/紫瞳
3. **男性服装强化过滤** — 男性排除的不限于"裙子"，还包括"蕾丝/胸罩/内衣/丝袜/比基尼/高跟鞋/口红"等所有女性化元素
4. **19条冲突检测** — 从v8.1的9条扩展到19条，覆盖亚裔+金发/蓝眼、男+女装、户外+厨房设施、户外+室内家具等
5. **风格开篇修复** — 检查"风"前面的字长度，少于2个字就替换为完整风格名
6. **B02活动行为只取1个** — 减少三手矛盾（多个动作=多个手部描述）
7. **维度前置兼容性检查** — 在gen_one()中做语义兼容性检查，不依赖后处理

### v9 vs v8.1 变化摘要

| 项目 | v8.1 | v9 |
|------|------|----|
| B01场景 | 取2个，过滤关键词 | **取1个** |
| 冲突检测 | 9条 | **19条** |
| 亚裔发色 | 未过滤 | **强制过滤金发** |
| 亚裔瞳色 | 未过滤 | **强制过滤蓝/绿/紫** |
| 男性服装 | 过滤"裙" | **过滤全套女性元素** |
| B02活动 | 取1个 | **取1个(强制)** |
| 场景检测 | 二元(室内/户外) | **场景组检测(卧室/厨房/浴室/户外)** |
| 质检验收 | qc_one(9项) | **qc_two(17项)** |
| 风格开篇修复 | 无 | **检查<2字时替换** |

## Core Principle: Data-Driven, Not Preset
**NEVER preset a fixed number of dimensions** (like "15 dimensions"). Instead:
1. Sample 10,000 random entries from `to_chi`
2. Exhaustively analyze what dimensions naturally emerge
3. Let the data reveal the dimension count and boundaries
4. Only then build libraries for the natural dimensions

## The Surgical Clean Approach (CRITICAL)

### DON'T (the hammer approach):
- Discard whole sentences that contain person descriptions
- Use keyword blacklists that filter out good content
- One-shot extraction without quality validation

### DO (the scalpel approach):
- Keep sentences intact, REMOVE only the person-description parts
- A sentence like "她穿着一件白色连衣裙，脖子上戴着一条银色项链" → keep "脖子上戴着一条银色项链"
- A sentence like "窗框由风化的浅棕色木材制成" → keep entirely (no person description)
- Use regex to cut: `r'，[她他]穿着[^。，]{5,30}'` → `'，'`

## Exhaustive Dimension Analysis Workflow

### Step 1: Sample big
- Sample 10,000 random lines from `to_chi`
- Each line should be >50 chars (skip short fragments)
- Randomize across all files in both `javrate/` and `xhs/` directories

### Step 2: Define fine-grained concept detectors
- NOT "人物" as one dimension — split into: 年龄, 性别, 种族/地域, 发型, 发色, 肤色, 脸型五官, 表情, 目光/眼神, 姿势, 手部动作, 身体动作, 身体裸露部位
- NOT "服装" as one dimension — split into: 上装, 下装, 内衣, 袖型, 领型, 服装细节, 服装颜色, 面料
- Each concept = name + keyword list (10-50 keywords)
- Keywords must be actual words that appear in the data, not hypothetical

### Step 3: Analyze coverage
- For each concept, count how many lines contain any keyword
- Sort by coverage descending
- Core dimensions = coverage > 10% (typically 60-80 dimensions)
- Rare dimensions = coverage 1-10% (typically 20-30 more)

### Step 4: Extract combinatorial patterns
- **Pair co-occurrence**: which dimension pairs appear together most often (>90%)
- **Sequential patterns**: typical order dimensions appear in (person→clothing→lighting→color)
- **Exclusion rules**: which dimensions should NOT appear together (nude + clothing)
- **Maturity levels**: basic (6-8 dims) → standard (9-12) → advanced (13-16) → pro (17+)

## Library Building Workflow

### Step 1: Extract raw sentences
```python
for each file in to_chi:
    for each line:
        split on period/comma into short sentences
        if sentence contains accessory keyword → save to acc_pool
        if sentence contains material keyword → save to mat_pool
        # ... etc
```

### Step 2: Clean with surgical cuts
```python
for each sentence in pool:
    # Remove leading person descriptors
    sentence = re.sub(r'^[她他]', '', sentence)
    sentence = re.sub(r'^一位|^一名|^[男女]子|^[男女]性', '', sentence)
    
    # Remove inline person actions
    sentence = re.sub(r'，[她他](?:穿着|身着|留着|梳着|扎着)[^。，]{5,30}', '，', sentence)
    
    # Keep if still meaningful (>15 chars)
```

### Step 3: Deduplicate
```python
seen = set()
unique = []
for item in pool:
    key = item[:20]  # first 20 chars as key
    if key not in seen:
        seen.add(key)
        unique.append(item)
```

### Step 4: Split large files
- Files >10MB should be split into 80K-line chunks (~7-8MB each)
- Named with `_p1`, `_p2` suffix

## File Splitting Rule
When a library file exceeds 10MB, split into parts:
```bash
cd lib_dir/
split -l 80000 -d --additional-suffix=.txt large_file.txt part_prefix
# Then rename to match library naming convention
```

## Quality Validation Checklist
- [ ] Each entry describes ONLY its dimension (accessory → no person/clothing)
- [ ] No forbidden patterns ("一只手自然垂落，另一只手")
- [ ] No比喻词 (仿佛/犹如/就像/好似/宛如/如同)
- [ ] Sentences are complete, not fragments
- [ ] Covers multiple sub-categories with balanced distribution
- [ ] File size < 10MB per part

## 100-Scene Template Architecture

For large-scale prompt generation (10K+ prompts), use the 100-scene template system:

### Category Structure (10×10)
Group 100 scenarios into 10 categories of 10 templates each:
1. **日常人物生活** (#01-10) — Daily life, home atmosphere, lazy morning, bedroom, balcony
2. **城市街头时尚** (#11-20) — Street snap, urban fashion, cafe, rooftop, subway, red carpet
3. **自然田园治愈** (#21-30) — Forest, flower field, stream, lake, mountain, beach, greenhouse
4. **东方意境与新中式** (#31-40) — Courtyard, ink painting, Zen, qipao, bamboo, red wall, opera
5. **复古怀旧与时代记忆** (#41-50) — Retro film, Hong Kong style, 80s disco, old classroom, jazz club
6. **暗黑浪漫与废墟美学** (#51-60) — Ruins, gothic castle, abandoned theater, dark garden, midnight pool
7. **色情写真与性感诱惑** (#61-70) — Lingerie, wet shirt, silk sheets, bathtub, high heels, back nude
8. **魅惑勾引与禁忌美学** (#71-80) — Red lip seduction, leather jacket, translucent gauze, shoulder strap slip
9. **超现实梦境与破圈艺术** (#81-90) — Floating ruins, mirror maze, giant portal, reverse gravity, painting portal
10. **情感叙事与戏剧光影** (#91-100) — Rainy farewell, reunion hug, graduation, bonfire, sunrise hope

### Template Format
Each template follows this structure:
```
● N. Template Name（X个维度）
  维度: 场景+天气+人物+发型+服装+材质+活动+道具+手部动作+表情+光照+色彩+构图+动态+氛围+破圈
  ──────────────────────────────────────────────────────────────────────
  [180-280 word example description — natural prose, no titles/numbers/分段]
  ──────────────────────────────────────────────────────────────────────
```

### Dimension Requirements per Template
- Minimum: 12 dimensions (absolute floor — never below)
- Target range: 16-18 dimensions (core sweet spot)
- Maximum: 24 dimensions (unlikely in single-paragraph form)
- All dimensions must be naturally integrated into flowing prose, not listed

### FORBIDDEN Template Categories
- ❌ 餐饮甜品静物 (food/dessert/still life) — no artistic narrative
- ❌ 单纯室内环境建筑描述无主体 (bare interior/architecture without human subject or artistic merit)
- ❌ Scenes lacking emotional/atmospheric dimension

### REQUIRED Content Categories (格林主人 additions)
- ✅ 小红书/社交媒体网红热点 (social media influencer trends)
- ✅ Artstation / art gallery high-aesthetic scenes
- ✅ 色情写真 (erotic photography / boudoir)
- ✅ 诱惑魅惑 (seduction / temptation / provocative)
- ✅ Story-driven scenes with emotional narrative depth

## Combinatorial Rules for Prompt Generation
Documented in `references/combinatorial_rules.md` — the key rules from this session:

1. **Core ordering**: style → scene → character → clothing → accessory → activity → props → material → lighting → color → composition → dynamic → atmosphere
2. **Mandatory core**: character + clothing + activity + lighting + color + scene
3. **Two-hand rule**: exactly 2 hands described; never "three hands"
4. **Nude rule**: skip clothing + accessories when nude
5. **Weather-clothing match**: winter ≠ summer clothes
6. **Scene-light match**: indoor ≠ direct sunlight; outdoor night ≠ natural light
7. **Deduplication within prompt**: same dimension only once
8. **Segment count**: 8-14 dimensions per finished prompt

## CRITICAL: Task Resumption Protocol for 格林主人

This user has a **very low tolerance** for getting stuck in analysis loops or "freezing" between context windows. The following protocol is MANDATORY:

### When user says "为什么不继续执行？？？" or "操你妈为什么又卡死了"
1. **Immediately stop** whatever analysis/thinking you're doing
2. **Check wake_guide.json and todo list** to identify exact state
3. **Report to user**: what was last completed, what the next step is
4. **Start executing the next step** — do NOT re-analyze or ask permission

### PITFALL: Perfect-Planning Delay
**Symptom**: Spending too long designing the "perfect" script before writing any code
**Fix**: Write a minimal test script first. Run on ONE file. Check. Then scale.

### PITFALL: Context Compression Amnesia  
**Symptom**: After a context reset, forgetting that research was already done in a PREVIOUS session. User had already created files in 新建库/ but the agent offered to "do the research phase."

**Fix — mandatory pre-check before any task:**
1. Scan the project working directory (e.g. 高质量模板/新建库/) for existing research docs — count them and note file sizes
2. Read task_current.json for exact state
3. session-search the project name AND task description
4. Report what was found: "[X] already done (N files found), continuing from [Y]"

### PITFALL: Terminal Gear Interference
Gear system cron jobs (self_enhance, gear_enforcer) inject output into stdout, corrupting Python output.

**Fix:**
- Run batch scripts from /mnt/c/Users/Administrator/ (Windows) to avoid gear cron interference
- Write all output to files, don't rely on stdout
- Use nohup + write to log file: nohup script.py > /tmp/out.log 2>&1 &
- Use atexit + signal.signal to save state on interruption
- Check progress by reading log files, not process polling

## Semantic Extractor: The Highest-Quality Extraction Method (V3.0)

The **semantic_extractor.py** approach (developed 2026-05-23) produces the highest quality dimension libraries by using **sentence-level extraction** instead of character-level boundary detection.

### Key Innovation: Sentence-as-Unit

Instead of `extract_segment(text, keyword, max_left, max_right)` which does character-level expansion (causing truncation), use **sentence-level** extraction:

```python
def get_sentences(text):
    \"\"\"Split text into independent semantic units (sentences)\"\"\"
    raw = re.split(r'[。；！？\\n]', text)
    sentences = []
    for s in raw:
        s = s.strip()
        if s and len(s) >= 4:
            # Further split on commas for finer granularity
            parts = re.split(r'[,，]', s)
            for p in parts:
                p = p.strip()
                if p and len(p) >= 4:
                    sentences.append(p)
    return sentences
```

Then for each dimension, search within these sentences using the keyword as anchor:

```python
def extract_hair(sentences, raw_text):
    results = []
    for sent in sentences:
        for kw in hair_kws:
            if kw in sent:
                # Find full hair description within sentence
                idx = sent.find(kw)
                start = sent.rfind('，', 0, idx) + 1 if '，' in sent[:idx] else max(0, idx - 15)
                end = sent.find('，', idx) if '，' in sent[idx:] else min(len(sent), idx + 20)
                segment = sent[start:end].strip()
                # Verify it's actually about hair
                if '发' in segment and 4 <= len(segment) <= 30:
                    results.append(segment)
                break  # one entry per sentence
    return results
```

### Why Sentence-Level Beats Character-Level

| Approach | Problem | Fix |
|----------|---------|-----|
| **Character-level** (v1-final) | `extract_segment(text, "棕色长", 4, 10)` → `"留着棕色长"` — truncated! | v2 used sentences |
| **Sentence-level** (v3-semantic) | `for sent in sentences: if "棕色长" in sent:` → `"留着棕色长发的年轻亚裔女性"` — complete! | Works because sentence is the natural semantic boundary |

### Semantic Validation Layer

Each extraction must pass a dimension-specific semantic validator before being added to the library:

```python
def validate_hair(seg): return '发' in seg
def validate_skin(seg): return bool(re.search(r'[肤白皙麦古粉红润]', seg))
def validate_expression(seg): return bool(re.search(r'(表情|神情|目光|眼神|面带|微笑)', seg))
def validate_pose(seg): return bool(re.search(r'(站立|坐着|躺|跪|趴|倚|蹲|盘腿|侧卧)', seg))
def validate_activity(seg): return bool(re.search(r'(站在|坐在|走在|正在|行走|自拍|拍照|看书)', seg))
```

Entries that pass validation AND have length 4-60 chars AND don't contain known dirty patterns are accepted. Everything else is rejected.

### Complete Dimension Library Schema (17 Libraries)

Based on actual to_chi data analysis (not predefined), the natural dimensions are:

| Code | Dimension | Description | Count (typical) |
|------|-----------|-------------|-----------------|
| A01 | 年龄性别 | 年轻亚裔女性, 少女... | 18K+ |
| A02 | 发型 | 黑色长发梳成高马尾... | 48K+ |
| A03 | 肤色 | 皮肤白皙, 小麦色肌肤... | 661 |
| A04 | 表情眼神 | 面带微笑, 直视镜头... | 2K+ |
| A05 | 姿势 | 盘腿坐在床上, 倚靠在窗边... | 94K+ |
| B01 | 场景环境 | 在卧室, 站在咖啡馆... | 101K+ |
| B02 | 活动行为 | 正在阅读, 端起咖啡杯... | 187K+ |
| C01 | 美学风格 | 写实风格, 复古胶片... | 11K+ |
| C02 | 光照条件 | 柔和自然光, 暖黄灯光... | 39K+ |
| C03 | 色彩调性 | 暖色调, 高对比度... | 103K+ |
| C04 | 构图镜头 | 特写, 中景, 浅景深... | 24K+ |
| D01 | 服装款式 | 身着白色露肩上衣... | 170K+ |
| D02 | 配饰鞋帽 | 颈间金色项链... | 12K+ |
| D03 | 材质质感 | 丝缎光泽, 木质纹理... | 358K+ |
| D04 | 动态效果 | 微风吹动, 花瓣飘落... | 34K+ |
| D05 | 天气时间 | 清晨, 午后, 黄昏... | 13K+ |
| D06 | 氛围情感 | 温馨, 私密, 浪漫... | 71K+ |

**Total: ~1.29M entries across 17 libraries**

### Post-Extraction Deep Clean

After initial extraction, run `deep_clean_v2.py` to remove:
- Entries with truncation markers (ending in `色长`, `色短`, `色$`, `右$`, `左$`)
- Cross-dimension contamination (e.g. skin library entries containing `"马尾"` — that's a hair description, not skin)
- Entries with dirty patterns (`人穿`, `搭配未`, `们穿`)
- Entries from non-person data that slipped through cleansing

## Multi-Strategy Extraction Pipeline (Preferred Method)

When extracting dimension libraries from `to_chi` raw data (260 files, javrate~13.5万 + xhs~38.5万 lines), use the **Multi-Strategy Fusion Pipeline** developed in session 2026-05-23:

### Architecture: 3-Layer Pipeline

```
Input → Layer1: Cleansing → Layer2: Extraction → Layer3: Quality Scoring → Output
```

### Layer 1: Data Cleansing Pipeline

Filter out invalid data before extraction:

```python
def cleansing_pipeline(text):
    # 1. Length filter
    if len(text) < 60: return False, 'too short'
    
    # 2. Exclude non-person content (xhs-specific)
    exclude_patterns = [
        (r'^(现代|简约|极简|北欧).{0,10}(室内|客厅|卧室|家居|装修|设计|空间)', '室内设计'),
        (r'^(一张|特写|展示).{0,15}(美甲|指甲油)', '美甲'),
        (r'^(一张|特写|俯拍).{0,10}(甜品|蛋糕|菜肴|美食|料理)', '食物'),
        (r'产品摄影展示一件', '产品'),
        (r'展示一个模特躯干', '无脸模特'),
        (r'人体模型躯干', '人台'),
    ]
    
    # 3. Person keyword check (for xhs files)
    person_keywords = ['女性','女子','男子','模特','女孩','身穿','人像','肖像','自拍']
    has_person = any(kw in text[:150] for kw in person_keywords)
    if not has_person: return False, 'no_person'
    
    # 4. Multi-person filter (>2 persons = quality degradation)
    multi_count = len(re.findall(r'(?:两人|三人|群人|两名|三名)', text))
    if multi_count > 0: return False, 'multi_person'
    
    return True, 'pass'
```

**Key insight:** javrate files (~13.5万条) are ALL person portraits — pass them through. xhs files (~38.5万条) are mixed — need strict filtering. The cleansing pipeline removes ~48% of xhs data but ensures extracted quality.

### Layer 2: Boundary-Aware Extraction

The core innovation — instead of regex keyword matching, use **boundary-aware segment extraction**:

```python
def boundary_extract(text, keyword, max_left=8, max_right=30):
    """Extract segment around keyword with smart boundary detection"""
    idx = text.find(keyword)
    if idx == -1: return None
    
    # Extend left to sentence/word boundary
    left = idx
    for _ in range(max_left):
        if left <= 0: break
        if text[left-1] in '。，；：！？': break
        left -= 1
    
    # Extend right to boundary OR connector words
    right = idx + len(keyword)
    connector_words = ['搭配', '和', '与', '以及', '还有', '并', '且']
    for _ in range(max_right):
        if right >= len(text): break
        if text[right] in '。，；：！？': break
        # Stop at connectors unless it's continuing a clothing description
        if any(text[right:right+len(cw)] == cw for cw in connector_words):
            next_part = text[right+2:right+15]
            if re.match(r'[^，。]{1,6}(裤子|裙子|短裤|鞋|靴|包|帽|项链)', next_part):
                right += 2; continue  # Keep connector for clothing chains
            break
        right += 1
    
    segment = text[left:right].strip().strip('，。')
    segment = re.sub(r'^(她|他|它|一位|一名|这个|照片[中里]|画面[中里])', '', segment)
    
    if len(segment) < 3: return None
    if re.match(r'^无可见|^没有|^不包含', segment): return None
    return segment
```

**Why this works:** Traditional regex extraction fails because it cuts off at "搭配XXX" mid-description. Boundary detection keeps connector words when they link to another clothing item, but cuts at sentence boundaries.

### Layer 3: Quality Scoring

Score each extraction and discard low-quality results:

```python
def quality_score(dims):
    score = 0
    core_dims = ['01_人物外貌', '02_服装款式', '04_光照条件', '05_色彩系统', '07_场景环境']
    for d in core_dims:
        if dims.get(d): score += 15
    ext_dims = ['06_构图镜头', '11_氛围情感', '12_美学风格', '15_色彩搭配']
    for d in ext_dims:
        if dims.get(d): score += 5
    total_items = sum(len(v) for v in dims.values())
    if total_items < 3: score -= 30
    for bad in ['人穿', '搭配未', '们穿']:
        if bad in str(dims): score -= 50
    return max(0, min(100, score))
```

### Strategy Benchmark Results (on 100 test samples)

| Strategy | Extract Rate | Unique Values | Dirty Data | Best For |
|----------|-------------|---------------|------------|----------|
| **A** Regex Semantic Split | 100% | 300 | ⚠️ Yes | Breadth |
| **B** Two-Stage Cleanse | 66% | 197 | ⚠️ Reduced | Precision |
| **C** Semantic Template | 95% | 147 | ⚠️ Yes | Technical dims |
| **D** A+B+C Fusion | 66% | 212 | ⚠️ Medium | Balanced |
| **F** **Multi-Strategy Pipeline** (final) | **52%** (after filtering) | **213K total** | **✅ Clean** | **PRODUCTION WINNER** |

**Winner: Strategy F** — the 3-layer pipeline. It extracts fewer items (~270K vs 475K) but quality is dramatically higher. The 02_服装款式 library went from dirty 85K to clean 85K with full descriptions like `身着白色露肩上衣` instead of fragments.

### Post-Extraction: 01_人物外貌 Sub-Library Split

After extraction, the `01_人物外貌` library mixes age/gender/hair/expression/pose/skin into one pool. This causes **logic conflicts** when composing prompts (e.g. picking "老年男子" for a subject then "湿漉漉的黑发" for hair).

**Fix:** Split into 5 independent sub-libraries:

| Sub-Library | Content | Typical Count | 
|-------------|---------|---------------|
| `01A_年龄性别` | 年轻亚裔女性、中年男子... | 13 |
| `01B_发型` | 黑色长发、高马尾、麻花辫... | 7,502 |
| `01C_表情` | 面带微笑、直视镜头、表情平静... | 763 |
| `01D_姿势` | 站立姿势、坐着姿势、盘腿姿势... | 9 |
| `01E_肤色` | 皮肤白皙、小麦色肌肤... | 226 |

**Why 01A is small (13 unique):** Age+gender categories are inherently limited. The 13 entries cover all needed combinations. **Do NOT artificially expand this** — just ensure they're clean.

### Technical Dimension Enrichment

Technical dimensions (05_色彩系统, 06_构图镜头, 09_动态效果, 10_天气时间, 11_氛围情感, 12_美学风格, 13_材质质感, 15_色彩搭配) typically extract only 10-20 unique values because they're keyword categories, not open-ended text.

**Enrichment strategy:** Scan the large extracted libraries (02_服装款式, 08_活动行为, 04_光照条件) for sentences matching technical keywords, extract the matching value:

```python
# For 11_氛围情感 — scan 02_服装款式 for "温馨" etc.
supporting_libs = ['02_服装款式.txt', '04_光照条件.txt', '01_人物外貌.txt', '07_场景环境.txt']
synonym_map = {'温馨': '温馨', '宁静': '宁静', '浪漫': '浪漫', ...}
for sf in supporting_libs:
    for line in open(sf):
        for kw, val in synonym_map.items():
            if kw in line and val not in found:
                found.add(val)
```

This typically expands technical dimensions from 10 → 20-34 entries.

### Complete Production Pipeline Output

After running the full pipeline on 260 to_chi files (518K total lines):

| Library | Entries | Quality |
|---------|---------|---------|
| 02_服装款式 | 85,288 | ⭐⭐⭐⭐⭐ |
| 08_活动行为 | 45,416 | ⭐⭐⭐⭐⭐ |
| 04_光照条件 | 42,741 | ⭐⭐⭐⭐ |
| 03_配饰鞋帽 | 16,643 | ⭐⭐⭐⭐ |
| 07_场景环境 | 15,111 | ⭐⭐⭐⭐ |
| 01B_发型 | 7,502 | ⭐⭐⭐ |
| +13 other dims | 763-9 | ⭐⭐⭐-⭐⭐⭐⭐⭐ |

**Total: ~213K entries across 18 libraries**

### IMPORTANT: Task Persistence Across Context Windows

This session revealed a CRITICAL workflow pattern for the user (格林主人):

**Problem:** After context compression (session summarization), the agent often loses track of exactly where it was in a multi-step task sequence, leading to:
- "卡死" (getting stuck analyzing instead of executing)
- Re-doing work already completed
- Losing task memory across windows

**Solution encoded as mandatory step:**
1. **Every wake/resume** → read `wake_guide.json` AND check `task_current.json`
2. **Before ANY new work** → session_search for the ongoing task first
3. **Use `todo` tool** to track granular progress (not just "in_progress" — track exact step)
4. **Notify the user** of exactly where you are resuming: "从[已完成步骤]继续，下一步是[待完成步骤]"
5. **If user says "卡死" or "为什么不继续"** → immediately stop, read the todo list, report exact state, and start executing the next pending step. Do NOT apologize verbosely or re-analyze — just execute.

### IMPORTANT: Phase-Based Execution Pattern for 格林主人

The user repeatedly insists on **分阶段、分文件、分步执行** (phase-by-phase, file-by-file, step-by-step). **DO NOT** try to write one giant script and run it all at once. Instead:

1. Write a minimal test script
2. Run it on ONE file
3. Check results
4. Fix bugs
5. THEN scale to more files

This pattern was explicitly demanded and every violation was met with frustration.

## Pitfalls

### PITFALL: Presetting dimension count
**WRONG**: "I'll build 15 libraries"  
**RIGHT**: Analyze the data first, let it reveal dimension count

### PITFALL: Keyword filtering as the only cleaning method
**WRONG**: `if '图案' in line: discard` — this throws away good entries that mention "图案" as material pattern  
**RIGHT**: Surgical cut — remove only the person-description parts, keep the rest

### PITFALL: One-shot extraction
**WRONG**: Extract once and declare done  
**RIGHT**: Extract → validate sample → iterate cleaning → re-extract if quality insufficient

### PITFALL: Output truncation during analysis
**WRONG**: "Outputting key parts only" when results get truncated  
**RIGHT**: Split into phases/stages, output each phase completely. Never simplify output.

## BERTopic Integration for Theme Discovery

This session (2026-05-24) integrated **BERTopic** for automatic semantic theme discovery. This is complementary to the manual distribution analysis — BERTopic finds latent topics that regex rules miss.

### Installation

```bash
pip3 install --break-system-packages --default-timeout=300 bertopic sentence-transformers umap-learn hdbscan
```

Uses the `paraphrase-multilingual-MiniLM-L12-v2` embedding model (~470MB, downloaded once).

### Usage Pattern

```python
from bertopic import BERTopic
from sentence_transformers import SentenceTransformer

embedding_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
topic_model = BERTopic(
    embedding_model=embedding_model,
    min_topic_size=50,
    nr_topics='auto',
    verbose=True
)
topics, probs = topic_model.fit_transform(data)
```

### Results on to_chi (20,000 sample)

BERTopic discovered **17 themes** from to_chi data:

| T# | Theme | Count | Interpretation |
|----|-------|-------|---------------|
| T0 | 浅景深_写实风格_暖色调 | 10,234 | Standard indoor portrait |
| T1 | 特写视角_微距镜头 | 1,574 | Close-up / detail |
| T2 | 户外人像摄影 | 1,311 | Outdoor portrait |
| T3 | 高分辨率_高对比度 | 966 | High-quality portrait |
| T4 | 特写_双眼紧闭 | 301 | Face close-up |
| T5-T9 | Various outdoor/nature | 176-223 | Outdoor scenes |
| T10 | 临床环境_制服 | 114 | Medical/uniform |
| T11 | 家庭室内场景 | 106 | Family indoor |
| T12 | 海滩场景 | 99 | Beach |
| T13 | 户外_宁静氛围 | 83 | Nature calm |
| T14 | 汽车内饰 | 68 | Car interior |
| T15 | 职业着装_办公室 | 62 | Office |

**Key finding:** BERTopic primarily clusters by **photography parameters** (景深、风格、光源) rather than content semantics (年龄、服装、道具). This is because the embedding model gives high weight to these frequent technical terms. **Use BERTopic as complementary signal, not replacement for regex-based extraction.**

## Data Distribution Analysis (CRITICAL for Composition)

**格林主人's insight (2026-05-24):** Without knowing the real distribution of dimensions in the source data, prompt composition samples blindly — producing unrealistic proportions.

### Mandatory Pre-Composition Step

Before composing prompts, run `analyze_distribution.py` to measure:

```python
stats = {
    'age_sex': {       # e.g. 年轻亚裔女性: 30.7%, 年轻男性: 1.8%
    'hair': {          # e.g. 黑色: 20.3%, 棕色: 6.1%
    'scene': {         # e.g. 卧室: 8.6%, 摄影棚: 7.5%
    'pose': {          # e.g. 站立: 27.5%, 坐着: 15.6%
    'nude': int,       # e.g. 6.6%
    'lingerie': int,   # e.g. 7.9%
    'swimsuit': int,   # e.g. 2.3%
}
```

### Distribution Results from to_chi (518,013 lines)

| Category | Top Items | Proportion |
|----------|-----------|------------|
| **Age/Sex** | 年轻亚裔女性 | 30.7% |
| | 年轻女性(无种族) | 2.6% |
| | 女孩/少女 | 1.9% |
| **Hair Color** | 黑色 | 20.3% |
| | 棕色 | 6.1% |
| | 银发 | 6.0% |
| **Scene** | 卧室 | 8.6% |
| | 摄影棚/工作室 | 7.5% |
| | 阳台/天台 | 6.6% |
| | 花园/公园 | 4.8% |
| **Pose** | 站立 | 27.5% |
| | 坐着 | 15.6% |
| | 躺着 | 4.3% |
| **Special** | 内衣描述 | 7.9% |
| | 裸体描述 | 6.6% |
| | 泳衣描述 | 2.3% |

**Application:** When composing, sample dimensions proportional to real data distribution. E.g., 50% of prompts should feature 年轻亚裔女性, 25% should use 卧室 as scene, 40% should use 站立 as pose.

## The `final_build.py` Approach (Preferred Method, 2026-05-24)

This is the **current best method** for building dimension libraries from scratch. It uses **sentence-level classification without truncation** and **per-dimension caps of 100K**.

### Core Principle
- Split text by periods (。), each sentence is an independent unit
- Classify each **complete sentence** into exactly ONE dimension
- Do NOT do character-level boundary detection or segment extraction — causes truncation
- Each dimension cap: 100,000 entries (when reached, stop extraction for that dim)
- Do NOT deduplicate or clean — full coverage first

### Priority Order for Technical Dims (Critical Fix)

In `final_build.py`, technical paragraphs (sentences containing `摄影/景深/对焦/构图` etc.) are matched by keywords. **Dims with few entries must be checked FIRST**, otherwise they get starved by high-match dims like C02_光照条件:

```python
# WRONG: C02 checked first — it captures all tech sentences, starving others
if any(kw in s for light_kws) and can_add('C02_光照条件'): return ('C02_光照条件', s)
if any(kw in s for mood_kws) and can_add('D06_氛围情感'): return ('D06_氛围情感', s)  # Never reached!

# RIGHT: Low-coverage dims checked first
if any(kw in s for texture_kws) and can_add('D03_材质质感'): return ('D03_材质质感', s)  # Priority!
if any(kw in s for mood_kws) and can_add('D06_氛围情感'): return ('D06_氛围情感', s)  # Priority!
if any(kw in s for light_kws) and can_add('C02_光照条件'): return ('C02_光照条件', s)  # Check last — already has enough
```

### Scan Order for Description Dims

Similarly, low-coverage description dims like `D04_动态效果` must be checked BEFORE high-coverage dims in the description section.

### PITFALL: Starvation from Priority Order

**SYMPTOM:** D03/D04/D06 show 0-7 entries even though source data contains them.
**ROOT CAUSE:** High-coverage dims (C02_光照条件 with 248K stored) are checked first in the if-chain and catch all tech sentences.
**FIX:** Sort the if-chain by **current entry count ascending** — dims with fewest entries get first priority.

### Results (260 files, 518K lines, no dedup, 100K cap per dim)

| Library | Entries | Status |
|---------|---------|--------|
| A02_发型 | 100,000 | ✅ Capped |
| B02_活动行为 | 100,000 | ✅ Capped |
| C01_美学风格 | 100,000 | ✅ Capped |
| C02_光照条件 | 100,000 | ✅ Capped |
| D01_服装款式 | 100,000 | ✅ Capped |
| D03_材质质感 | 100,000 | ✅ Capped |
| D06_氛围情感 | 100,000 | ✅ Capped |
| A01_年龄性别 | 55,640 | OK |
| A05_姿势 | 44,657 | OK |
| A04_表情眼神 | 40,779 | OK |
| C03_色彩调性 | 67,767 | OK |
| D02_配饰鞋帽 | 69,852 | OK |
| +4 others | 1K-28K | OK |

**Total: 828,791 entries across 17 libraries**

## Distribution Analysis (Mandatory Before Composition)

**格林主人's command (2026-05-24):** Without knowing the real distribution of dimensions in the source data, prompt composition samples blindly — producing unrealistic proportions.

### Mandatory Pre-Composition Step

Run `analyze_distribution.py` which counts:

```python
stats = {
    'age_sex': {       # e.g. 年轻亚裔女性: 30.7%, 年轻男性: 1.8%
    'hair': {          # e.g. 黑色: 20.3%, 棕色: 6.1%
    'scene': {         # e.g. 卧室: 8.6%, 摄影棚: 7.5%
    'pose': {          # e.g. 站立: 27.5%, 坐着: 15.6%
    'nude': int,       # e.g. 6.6%
    'lingerie': int,   # e.g. 7.9%
    'swimsuit': int,   # e.g. 2.3%
}
```

### Full Distribution Report (from 518,013 lines)

Output to `distribution_report.json`. Key findings:

| Category | Top Items | Proportion |
|----------|-----------|------------|
| **Age/Sex** | 年轻亚裔女性 | 30.7% |
| | 年轻女性(无种族) | 2.6% |
| | 女孩/少女 | 1.9% |
| **Hair Color** | 黑色 | 20.3% |
| | 棕色 | 6.1% |
| | 银发 | 6.0% |
| **Scene** | 卧室 | 8.6% |
| | 摄影棚/工作室 | 7.5% |
| | 阳台/天台 | 6.6% |
| | 花园/公园 | 4.8% |
| **Pose** | 站立 | 27.5% |
| | 坐着 | 15.6% |
| | 躺着 | 4.3% |
| **Special** | 内衣描述 | 7.9% |
| | 裸体描述 | 6.6% |
| | 泳衣描述 | 2.3% |

### Weighted Sampling Table

```python
SAMPLING_WEIGHTS = {
    'A01': {
        '年轻亚裔女性': 0.50,
        '年轻女性(无种族)': 0.12,
        '女孩/少女': 0.08,
        '年轻男性': 0.08,
        '儿童': 0.05,
        '婴儿': 0.03,
        '其他(中年/老年/无标记)': 0.14,
    },
    'scene': {
        '卧室': 0.25,
        '摄影棚': 0.15,
        '阳台/天台': 0.12,
        '花园/公园': 0.10,
        '街道/城市': 0.08,
        '户外自然': 0.08,
        '其他': 0.22,
    },
    'pose': {
        '站立': 0.40,
        '坐着': 0.25,
        '躺着': 0.08,
        '趴着': 0.05,
        '倚靠': 0.04,
        '盘腿': 0.03,
        '跪着': 0.02,
        '其他': 0.13,
    },
    'special': {
        '内衣描述': 0.08,
        '裸体描述': 0.07,
        '泳衣描述': 0.02,
        '常规': 0.83,
    },
}
```

## BERTopic Integration for Theme Discovery

**Added 2026-05-24:** BERTopic automatically discovers latent themes. Use `paraphrase-multilingual-MiniLM-L12-v2` embedding model.

### Installation
```bash
pip3 install --break-system-packages --default-timeout=300 bertopic sentence-transformers umap-learn hdbscan
```

### Results on 20K to_chi sample
Discovered 17 themes. Key finding: BERTopic clusters by **photography parameters** (景深、风格、光源), not content semantics (年龄、服装). Use as **complementary signal**, not replacement.

## Token Cost Analysis for delegate_task

**CRITICAL insight from session 2026-05-24:** Each `delegate_task` call has a **~42,000 token fixed overhead** (SOUL.md + 327 skill descriptions + tools + memory). This is confirmed by two independent measurements:

```
Test A: 5 items → 43,326 input → 42,000 + 5×310 = ~42,000 overhead
Test B: 20 items → 48,110 input → 42,000 + 20×310 = ~42,000 overhead
```

### Breakdown of 42,000 overhead

| Component | Tokens | Needed? | Can We Remove? |
|-----------|--------|---------|----------------|
| SOUL.md (G0-G7+8 rules+永久禁令) | ~4,000 | ✅ | No — essential instructions |
| 327 skills (name + description) | ~18,000 | ❌ | No — system injects automatically |
| TOOL definitions (all function schemas) | ~8,000 | ✅ | No — needed for function calling |
| USER_PROFILE + MEMORY | ~4,000 | ✅ | No — needed for context |
| Task instructions + data | ~310/item | ✅ | This is the actual useful content |
| Other system overhead | ~5,690 | ❌ | No — system-level |

### Impact: delegate_task is WRONG for batch extraction

```python
# DON'T: 72 items per delegate_task round wastes 42K tokens/round
result = delegate_task(items, "extract dimensions for 72 items")

# Cost for 30K items:
#   (42,000 + 72×310 + 72×270) × (30,000/72) = 348,000,000 tokens = ~$50
#   Waste: 42,000 × 416 rounds = 17,500,000 tokens wasted = ~$25 down the drain
```

### The Fix: Direct API Script

Write a standalone Python script that calls the DeepSeek API directly — **no delegate_task overhead**:

```python
import openai, os, json

client = openai.OpenAI(
    api_key=os.environ.get('DEEPSEEK_API_KEY') or open('/home/administrator/.deepseek_key').read().strip(),
    base_url="https://api.deepseek.com"
)

BATCH = 500  # Much larger batch since no overhead
for i in range(0, len(all_items), BATCH):
    batch = all_items[i:i+BATCH]
    prompt = f"Extract 17 dimensions from each prompt. Return JSON array.\n\n---DATA---\n" + \
             "\n".join(f"---ENTRY {j+1}---\n{item}" for j, item in enumerate(batch))
    
    resp = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        max_tokens=4000
    )
    
    results = json.loads(resp.choices[0].message.content)
    # Write results to dimension library files
```

**Cost savings:**
```
delegate_task: 30K items → 416 rounds → 348M tokens → ~$50
Direct API:    30K items → 60 rounds  → 174M tokens → ~$25
Savings: 50% cost, 6x faster
```

### When to Use Each Method

| Method | Best for | Cost | Speed |
|--------|----------|------|-------|
| **Regex/Python** | Quick analysis, distribution stats, pre-filtering | Free | 50K/sec |
| **Direct API script** | Production-quality dimension extraction | ~$25/30K items | 500 items/round |
| **delegate_task** | Complex single-task, reasoning, multi-step | High | 72 items max/round |

**Rule of thumb:** If you're processing >100 items of data, write a direct API script. If you need reasoning or multi-step logic, use delegate_task (but accept the overhead cost).

## API-Based Batch Decomposition (Alternative to Regex)

⚠️ **IMPORTANT: The final_build.py regex approach has a known truncation bug.** Regex-based sentence classification cannot distinguish between complete sentences and truncated fragments. Example from production: `[A01_年龄性别]一位红发长直发年轻女子趴在铺着白色床` — the `单` is missing.

### When to Use API Decomposition

| Condition | Choose | 
|:----------|:-------|
| Building new libraries from scratch | **API decomposition** (better quality) |
| Rebuilding/expanding existing libraries | **Regex as fast pass** + API for cleanup |
| Quick analysis/prototyping | Regex (free, instant) |
| Production-quality final libraries | **API decomposition** (no truncation) |

### Proven Method (validated 2026-05-25)

**Batch size: 50 items/round** — fills 16K output window without truncation.
**Cost: ~$0.00005/item** (vs delegate_task's $0.00012/item with 83% overhead waste).

Full reference: `references/api_batch_decomposition.md`

## Post-Clean Pipeline (v8.0 — Critical Lessons from 2026-05-25)

The most-iterated part of the pipeline. **Detailed in `references/v8_post_clean_pipeline.md`.**

Key lessons from this session:
- **1 fragment per dimension** — prevents 三手/服装堆叠/场景矛盾
- **8-step post-clean pipeline** in exact order (conflict check → 比喻词 → 三手裁剪 → 服装裁剪 → 风格补全 → 裸体检测)
- **三手裁剪**: sentence-level L/R/B hand-type conflict detection (same-sentence ≥2 types OR cross-sentence ≥3 types = skip)
- **服装堆叠裁剪**: keep first TOP_KW, delete sentences with second
- **缺风格开篇自动补**: prepend random style if missing
- **Physical conflict detection**: 9 patterns, returns None → retry (up to 5 attempts)

### Critical: Prompt Fix Needed for 2 Dimensions

Testing revealed two dimensions with near-zero coverage that need the system prompt's dimension definitions broadened:

**B02_活动行为 fix:** The definition must include **micro-actions** — `"整理头发"`, `"望向窗外"`, `"左手轻握布料"`, `"向左看"`. The model only extracts obvious actions like "看书""跳舞" — it misses subtle hand/head/gaze movements.

**D02_配饰鞋帽 fix:** The definition needs more explicit examples — `"金色耳环"`, `"银色高跟凉鞋配踝带"`, `"彩色手链"`, `"黑色发圈"`. Without these, the model skips accessories mentioned mid-sentence.

### 15_美学风格库.txt — Known Quality Issue

This file (500 lines, 76KB) has two problems:
1. **Content duplicated**: First 250 lines and last 250 lines are identical
2. **Character corruption**: All `的` replaced with `式` (e.g., "极简主义的" → "极简主义式")

**Impact:** Low — this file is only used for style reference, not for decomposition. The API reads raw to_chi data directly.

## Banned Content Categories (格林主人 2026-05-24)

These are **permanently banned** from all prompt generation:

- ❌ 餐饮甜品静物 (food/dessert/still life — no artistic narrative value)
- ❌ 单纯室内环境/建筑描述无主体 (bare interior/architecture without human subject or artistic merit)
- ❌ Scenes lacking emotional/atmospheric dimension

## Required Content Categories (格林主人 2026-05-24)

These must be **actively included**:

- ✅ 小红书/社交媒体网红热点 (social media influencer trends: 氛围感写真/居家日常/探店)
- ✅ Artstation / art gallery high-aesthetic scenes
- ✅ 色情写真 (erotic photography: 私房写真/内衣/蕾丝/身体美学)
- ✅ 诱惑魅惑 (seduction: 眼神勾引/暧昧光影/挑逗姿势)
- ✅ 日常场景与生活写真 (10x diversity required)

## Phase-Based Execution Commandment

The user (格林主人) has explicitly and repeatedly demanded:

1. **Write minimal test → run on ONE file → check → fix → THEN scale**
2. **Do NOT write one giant script and run it whole** — always decompose into phases
3. **After each phase: review + report** to user before starting next phase
4. **Do NOT ask permission for the next step if it's obvious** — just do it and report
5. **If user says "操你妈为什么又卡死了" or "为什么不继续"** → immediate stop, check todo/wake_guide, report state, execute next step. No verbose apology, no re-analysis.

### Core Principle
- Do NOT extract segments from within sentences (causes truncation)
- Do NOT do character-level boundary detection
- Split text by periods (。), each sentence is an independent unit
- Classify each **complete sentence** into exactly ONE dimension
- A sentence either IS about age, or IS about hair, or IS about clothing — not both

### Implementation

```python
def classify_sentence(sent):
    """Return (dim_name, content) or None"""
    # Match age/sex patterns at sentence start
    age_match = re.match(r'^(一位|一名)(年轻[亚白东]?[裔人]?[女男]|中年[女男]|老年[女男]|少女|女孩|男孩|儿童|婴儿)', sent)
    if age_match:
        if not re.search(r'(摄影|照片|镜头|相机)', sent[:20]):
            cut = sent.find('，')
            if 6 <= cut <= 18: return ('A01_年龄性别', sent[:cut])
            elif len(sent) <= 18: return ('A01_年龄性别', sent)
    
    # Match hair descriptors
    hair_indicators = ['长发', '短发', '卷发', '马尾', '丸子头', ...]
    if sum(1 for hi in hair_indicators if hi in sent) >= 1 and '发' in sent:
        return ('A02_发型', sent)
    
    # Match clothing
    if re.match(r'^(身着|身穿|穿着|搭配)', sent):
        if len(sent) >= 6: return ('D01_服装款式', sent)
    
    # ... (similar for each dimension)
```

### Coverage Gaps Warning

The `rebuild_libs.py` approach is strict, leading to low coverage in some dimensions:

| Dimension | Rebuild Count | Target | Gap Reason |
|-----------|--------------|--------|------------|
| A01_年龄性别 | 1,078 | 8,000+ | Only matched `一位XX` sentence starts |
| C01_美学风格 | 163 | 5,000+ | Style words mostly in tech paragraphs |
| C03_色彩调性 | 2,605 | 15,000+ | Tone words in tech paragraphs |
| D01_服装款式 | 4,110 | 20,000+ | Only matched `身着/身穿` sentence starts |
| D06_氛围情感 | 90 | 5,000+ | Mood words in tech paragraphs |

**Fix strategy:** For low-coverage dimensions, **also extract from technical paragraph sentences** (shorter sentences containing photography parameters). These paragraphs are rich in style/color/mood keywords but were excluded because they're not "description" sentences.

## Combined Pipeline (Best Practice)

For the highest quality dimension libraries, use this **3-phase combined pipeline**:

### Phase 1: BERTopic Theme Discovery
```bash
python3 bertopic_analysis.py  # → discovers latent themes + topic keywords
```
Use BERTopic topics to understand the **semantic landscape** of the data.

### Phase 2: Sentence-Level Classification
```bash
python3 rebuild_libs.py  # → 17 dimension libraries, ~418K total entries
```
Classify each sentence into exactly one dimension. **Strict but clean.**

### Phase 3: Distribution Analysis
```bash
python3 analyze_distribution.py  # → distribution_report.json
```
Count real-world proportions of each dimension value.

### Phase 4: Weighted Composition
Use distribution data to guide sampling weights. Never sample uniformly.

```python
SAMPLING_WEIGHTS = {
    'A01': {'年轻亚裔女性': 0.50, '年轻女性': 0.12, '女孩': 0.08, 
            '年轻男性': 0.08, '儿童': 0.05, '婴儿': 0.03, '其他': 0.14},
    'scene': {'卧室': 0.25, '摄影棚': 0.15, '阳台': 0.12, '花园': 0.10, 
              '街道': 0.08, '户外自然': 0.08, '其他': 0.22},
    'pose': {'站立': 0.40, '坐着': 0.25, '躺着': 0.08, '趴着': 0.05, 
             '倚靠': 0.04, '盘腿': 0.03, '跪着': 0.02, '其他': 0.13},
}
```

### PITFALL: Truncation During Extraction — Real Examples

**格林主人's exact complaint (2026-05-24):** The final_build.py output produced fragments like:

```
[A01_年龄性别]一位红发长直发年轻女子趴在铺着白色床     ← "白色床单" truncated
[A01_年龄性别]一名留着齐肩棕色头发的年轻女子背对着       ← "背对着镜头" truncated
[A01_年龄性别]一位年轻女性  [A01_年龄性别]一位25岁左右  ← fragmented
[A01_年龄性别]一位年轻女性  [A01_年龄性别]一张特写肖像照  ← corrupted
```

**ROOT CAUSE:** Using sentence-level classification in `final_build.py` combined with a **slice-based matching**: the script matched "一位红发长直发年轻女子" from one variant but then cut off the sentence at `white bed` instead of `white bed sheets`. The regex-based extraction didn't detect the incomplete boundary.

**The deeper problem:** Regex has NO understanding of semantic boundaries. It matches patterns but cannot distinguish between:
- `"白色床单"` (complete — the full material being described)
- `"白色床"` (truncated — missing the actual subject)

**FIX applied in this session:** Documented in the "API Extraction vs Regex Extraction" section. The only reliable fix is **API-based extraction** where the model understands complete sentence boundaries.

## PITFALL: Cross-Dimension Contamination

**SYMPTOM:** Skin library contains `[A03_肤色]马尾，肤色白皙，面带微笑` — the `马尾` and `面带微笑` are hair and expression, not skin.
**ROOT CAUSE:** The extraction function found `肤色` in a long sentence and extended right past a comma.
**FIX:** 
- For dimensions where description is delimited by commas (like 肤色), split on `，` and take the first segment
- Add per-dimension validators (e.g., `validate_skin` checks for `[肤白皙麦古]` and rejects if `马尾` in first 8 chars)
- Never trust `extract_segment()` to keep boundaries clean across commas

## PITFALL: Repetitive Truncation Loop

**WARNING:** If you've tried to fix truncation 3+ times and it keeps happening, **the extraction approach is fundamentally wrong** — don't patch it, replace it with sentence-level classification.

## System Command: 7-Point Task Execution Protocol

This protocol applies to ALL complex tasks, not just prompt library engineering. It was issued as a permanent system command.

1. **Pre-execution Review**: Before any task, review historical information + search relevant info for full context. Understand requirements, rules, standards. Form a global overview and prediction. Create detailed task plan. Decompose complex tasks into phases/stages/directions. If something needs clarification, ASK THE USER.

2. **Token Overload Handling**: When encountering large token counts, model limits, output truncation, or length issues → decompose the task. Output in phases/stages/directions. Never simplify output when truncated — split and continue.

3. **Phase Review**: After each phase, review what was done + re-check historical info. Ensure direction hasn't drifted.

4. **Final Review**: After full completion, review historical info + do global check. Ensure ALL requirements, standards, and conditions are satisfied.

5. **Real Implementation Check**: Verify everything is truly implemented to production quality. Web-search for latest/best/highest-quality implementation methods as reference. Perform rigorous multi-condition commercial-grade testing. Then continue with optimization/improvement as needed. Followed by deep code review + functional testing. Do NOT cut corners, avoid defects, or slack off.

6. **Quality Cycle**: Loop: comprehensive optimization/iteration → extreme detailed commercial-grade code review → extreme detailed commercial-grade testing → comprehensive optimization/iteration. Repeat until perfect.

7. **Quality Mandate**: ALL implementations must be HIGH QUALITY. Forbidden: simplified implementation, batch implementation, degraded implementation, simulated implementation, example-only, placeholder-only, core-code-only. Must be fully real, complete, production-grade. No code abbreviations, no feature degradation, no virtual implementations, no placeholders.

## Research-First Workflow for 100K Prompt Generation (格林主人 2026-05-25)

When the user demands "深度分析文件夹内的文档 → 研究现代艺术展/美术馆/AIGC站最受欢迎作品 → 启动子代理生产10万条高质量prompt", this is a **research-first workflow** that differs from the usual library-building or batch-generation tasks.

### Phase 0: Document Analysis + Trend Research

Before ANY generation, do:

1. **Scan the template folder**: `D:\Hermes\1000000提示词\高质量模板\` — read 15_美学风格库.txt, 100个场景模板, and the dimension rule docs
2. **Analyze existing libraries**: 17 dimension libraries (2M+ entries) can be used as reference for style/color/lighting descriptions
3. **Compile style catalog**: Extract 1000+ mixable modern visual art styles from the style library + web research
4. **Map breakthrough logic**: Three types — A) Stylized homage B) Surreal paradox C) Subversive contrast

### Phase 1: 10-Sub-Agent Parallel Generation

The user explicitly demanded 10 sub-agents × 10,000 each = 100,000 total. 

⚠️ **Key constraint**: The user ALSO said "严禁简单实现，严禁批量实现，严禁降级实现" — this means NO Python random-combination scripts. Each prompt must be genuinely thought-generated by an AI sub-agent.

**Architecture:**

```
1. Create 10 output files: modern_art_prompts_S1.txt through S10.txt
2. Assign each sub-agent a unique style domain (prevents cross-agent duplication)
3. Each sub-agent generates in batches of 20-30 prompts per delegate_task call
4. Each sub-agent maintains its own dedup set (first 50 chars as key)
5. After all 10 done → global dedup across files → fill remaining to reach 100,000
```

### Phase 2: Global Dedup + Quality Check

After all sub-agents finish:

```bash
# Concatenate
cat S*.txt > all_prompts_temp.txt

# Dedup using first 50 chars
python3 -c "
seen = set()
with open('all_deduped.txt', 'w') as out:
    for line in open('all_prompts_temp.txt'):
        key = line[:50]
        if key not in seen:
            seen.add(key)
            out.write(line)
print(f'Total: {len(seen)}')
"
```

Then run quality checks:
- Jaccard similarity > 0.7 → remove duplicates
- Three-hand detection
- Metaphor word detection  
- Scene contradiction detection
- Word count check (450-850 chars)

### Reference Files

Full workflow details in the sister skill `creative/chinese-aesthetic-prompt-engineering/references/10subagent-workflow.md`

## Non-Destructive Restart Rule (CRITICAL)

**NEVER `os.remove(OUTPUT_FILE)` in a production script.** Always append. Track progress by checking file line count on restart. Losing data to a restart will make the user furious.

## v8.0 Post-Clean Pipeline Summary

See `references/v8_post_clean_pipeline.md` for the 8-step pipeline. Key patterns:

- **三手裁剪**: Track seen hand types (L/R/B) per sentence. Skip if ≥2 types in same sentence OR ≥3 types across sentences.
- **服装堆叠裁剪**: Keep first TOP_KW sentence, delete subsequent ones.
- **缺风格开篇自动补**: Prepend random style if first 80 chars lack "风，".
- **Physical conflict return None** → triggers up to 5 retries with different fragment combos.
- **OS module added to the imports in the actual prompt used for generation.**
- External frustration signal is a FIRST-CLASS signal for correcting approach, not just memory
- "高质量的" = must be production-ready, not MVP
- Never batch-generate employee configs or skill configs
- Always do historical review before executing any task
- Execute in phases with review between phases
- **When user says "为什么不继续执行？？？" or similar frustration — STOP and review: check what step was last completed, what the user's last request was, and resume from that exact point. Do NOT apologize excessively; just show you reviewed history and are continuing.**
- **When user bans a content category (e.g. "禁止本类型"), that prohibition is permanent for this class of task unless explicitly un-banned. Treat it as a hard constraint in combinatorial rules.**
- **User demands "十倍丰富度补充" (10x diversity boost) means: add more scene types, more poses, more subjects, more emotional tones. Not just more of the same — genuinely expand the variety space.**

## 回滚方案
### 快速回滚
如果部署后发现问题：
1. 使用版本控制回退到上一个提交：`git revert HEAD`
2. 确认回滚后系统状态正常
3. 通知相关方变更已撤销

### 数据安全
- 所有修改前确认有备份
- 配置变更记录版本历史
