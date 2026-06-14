# final_build.py Pipeline — Dimension Library Construction

## Architecture: 3-Phase Pipeline

```
to_chi (260 files, 518K lines)
  → Phase 1: Data Cleansing (排除非人物/多人/垃圾)
  → Phase 2: Sentence-Level Classification (17 dims, no truncation)
  → Phase 3: Distribution Analysis (加权采样指导)
```

## Phase 1: Data Cleansing (`final_build.py` → `should_exclude()`)

### Exclusion Rules (in order)

1. **Non-person content** (xhs-specific): 室内设计照片, 美甲, 甜品/食物, 产品摄影, 模特躯干/人台
2. **Person keyword check**: must contain `女性/男子/身着/留着/人像/肖像/写真` in first 150 chars
3. **Multi-person filter**: `两人/三人/四人/五人/群人/两名/三名` → reject

**Key insight:** javrate files are ALL person portraits — pass through. xhs files are mixed — 48% exclusion rate.

## Phase 2: Sentence-Level Classification

### Core Algorithm

```python
def classify_sentence(sent, buffers):
    """
    1. Split source text by periods (。)
    2. Each sentence is an independent unit
    3. Classify each sentence into exactly ONE dimension
    4. No character-level segmentation — no truncation
    """
    # Check if tech paragraph (contains 摄影/景深/对焦 etc.)
    is_tech = sum(1 for m in tech_markers if m in sent) >= 2
    
    if is_tech:
        # Priority: low-coverage dims FIRST
        if texture_kw_match and can_add('D03'): return ('D03', sent)
        if mood_kw_match and can_add('D06'): return ('D06', sent)
        if dynamic_kw_match and can_add('D04'): return ('D04', sent)
        # Then high-coverage dims
        if light_kw_match and can_add('C02'): return ('C02', sent)
        if style_kw_match and can_add('C01'): return ('C01', sent)
        ...
    else:
        # Description paragraph — same priority logic
        ...
```

### Priority Fix (Critical)

**Problem:** D03/D04/D06 showed 0-7 entries because C02 (光照条件) with 248K stored was checked first and caught all tech sentences.

**Solution:** Sort the if-chain by **current entry count ascending**. Dims with the fewest stored entries get first-priority matching. Use `can_add(dim)` which checks `len(buffers[dim]) < MAX_PER_DIM`.

### Per-Dim Max

Each dimension caps at 100,000 entries (`MAX_PER_DIM = 100000`). When all dims are full, extraction stops early.

### Results

| Phase 2 Run | Entries | Key Changes |
|---|---|---|
| **Run 1** (no priority fix) | 828,778 | D03=1, D04=0, D06=7 ❌ |
| **Run 2** (priority fix applied) | 828,791 | D03=100K ✅, D04=18K, D06=100K ✅ |

## Phase 3: Distribution Analysis (`analyze_distribution.py`)

### What It Counts

- **Age/Sex**: 年轻亚裔女性, 年轻女性, 女孩, 男孩, 婴儿, etc.
- **Hair color**: 黑色, 棕色, 金色, 红色, 银发
- **Scene**: 卧室, 摄影棚, 阳台, 花园, 街道, 海滩, 浴室, etc.
- **Pose**: 站立, 坐着, 躺着, 趴着, 倚靠, 跪着, 盘腿
- **Special**: nude(6.6%), lingerie(7.9%), swimsuit(2.3%)
- **Indoor/Outdoor**: indoor(25.4%), outdoor(17.5%)
- **Upper wear**: 有上装 vs 裸体/无上装

### Output

`distribution_report.json` — used to guide weighted sampling during prompt composition.

### Weighted Sampling Table (use during composition)

```python
SAMPLING_WEIGHTS = {
    'A01': {'年轻亚裔女性': 0.50, '年轻女性': 0.12, '女孩': 0.08, 
            '年轻男性': 0.08, '其他': 0.22},
    'scene': {'卧室': 0.25, '摄影棚': 0.15, '阳台': 0.12, '花园': 0.10, '其他': 0.38},
    'pose': {'站立': 0.40, '坐着': 0.25, '躺着': 0.08, '其他': 0.27},
}
```

## Output Directory

```
/mnt/d/Hermes/1000000提示词/高质量模板/维度库_final_build/
```

17 files, totaling 828,791 entries.
