# Local Combination Engine Evolution (v8→v10.1→v11)

## The Core Problem

**Dimension library entries are full sentences, not pure labels.**

Example:
- v3 entry (bad): `[A02_发型]女性留着深色长发并带有蓝色挑染`
- What we want: `[A02_发型]深色长发带蓝色挑染`

The v3 `classify_sentence()` uses `extract_segment_around()` which extracts content between punctuation marks — this preserves the full sentence structure including person subjects and verbs.

## Engine Iteration History

| Version | Strategy | Success | QC avg | Manual quality (top-10) | Key issue |
|---------|----------|---------|--------|------------------------|-----------|
| **v8_1** | Fragment concatenation + v3 | 98% | 87.1 | 4/10 (40%) | Gender fracture 58%, scene mixing |
| **v9** | Fixed template paragraphs | 72% | — | 2/10 (20%) | Too many failures |
| **v9.1** | extract_tag + gender filter | 100% | 87.8 | 6/10 (60%) | extract_tag regex can't catch all person subjects |
| **v10** | Label template + v4 lib | 100% | 88.5 | 3/10 (30%) | v4 label lib has bugs (D02 1 entry) |
| **v10.1** | Gender cloth filter + v3 | 100% | 89.6 | 8/10 (80%) | **Current best** — best tradeoff |
| **v10.2** | Inline cleaning + v3 | 100% | 88.2 | 4/10 (40%) | Over-cleaning destroyed useful entries |
| **v11** | Pure label + v5 tag lib | in progress | — | — | v5 being built from to_chi source |

## v10.1 — The Best Production Engine

**File**: `/mnt/d/Hermes/1000000提示词/高质量模板/维度库/combine_engine_v10_1.py`
**Dimension library**: v3 (107K entries)
**QC**: 89.6 average, 0% gender fracture, 5% scene conflict, 0% three-hand, 0% tech keywords

### Three-layer gender protection:
1. **Pick-time**: male A01 auto-filters D01/D02 containing female-only clothing words
2. **Template-time**: uses `她/他` pronoun matching gender
3. **Post-gate**: she/he count check — if male A01 has more `她` than `他`, reject

### Fixed template structure:
```
[Style seed sentence]。在[scene]中，[A01 age+gender]，留着[A02 hair]，[A04 expression]。
[pronoun]身着[D01 clothing]，搭配[D02 accessories]。
[pronoun][B02 activity]。
[C02 lighting]。[C01 aesthetics]。[C03 color]。
```

### Critical: QC scores don't match manual quality
- QC 89.6 → manual review: ~80% pass rate
- QC measures 10 mechanical rules only (no readability, no multi-person detection, no subject duplication)
- Manual 100-line review is the ONLY reliable quality metric

## The v5 Tag Library Fix (fundamental solution)

**Root cause**: `final_build_v3_clean.py` uses `extract_segment_around()` which grabs text between punctuation marks — preserving full sentence structure.

**v5 approach**: `final_build_v5_tag.py` splits each source line into:
1. Sentences (by `。！？；`)
2. Clauses (by `，、：；`)
3. Each clause → classified to 1 dimension → tag extracted (person subjects/verbs removed)

### Tag extraction rules per dimension:
- **A02_发型**: remove person prefix + verb prefix, truncate at "的年轻女性" / "坐在" / punctuation
- **D01_服装款式**: extract content AFTER "身着/身穿/穿着", truncate at first punctuation
- **D02_配饰鞋帽**: similar to D01, extract accessory keyword context
- **B01_场景环境**: remove person descriptions, keep scene/core words
- **所有C类**: already largely pure tags (technical terms like "浅景深", "自然光")

## v11 Engine (in progress)

**File**: `/mnt/d/Hermes/1000000提示词/高质量模板/维度库/combine_engine_v11.py`
**Dimension library**: v5 tag library (in build)

Key differences from v10.1:
- Uses pure-label dimension library — no `inline_clean_*()` needed
- Adds A03_肤色 and A05_姿势 to template
- Simpler code path (no cleaning step)
- Expected: ~95% manual pass rate

## Implementation Lessons

1. **Never modify dimension library files in-place** — use a write-to-memory, flush-to-new-file pattern. The `repair_v4_labels.py` script had a `for line in open(file)` write loop that clobbered the file.
2. **Always backup before batch operations** on dimension library files
3. **QC scores are not reliable** for real quality — you MUST do manual 100-line review
4. **The 80/20 rule applies hard** — v10.1 gets 80% quality. The remaining 20% (multi-person entries, scene-confused C02 items, gender-ambiguous clothing) requires a dimension-library rewrite to fix.
5. **False starts are expensive** — v4 label lib took 2 attempts (bug in D02 processing), v10.2 over-cleaning wasted time. Test with 20 lines before full build.
