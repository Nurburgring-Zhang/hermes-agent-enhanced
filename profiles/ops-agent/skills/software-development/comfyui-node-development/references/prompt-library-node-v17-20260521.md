# PromptLibraryNode V17.0 Reference

## Overview

V17.0 is a full rebuild from V16.4 (1229 lines, 58 parameters, 7 output ports). It adds:
- **Phase 4-2**: Scoring/Sorting system (4-dimension weighted scoring)
- **Phase 4-2**: Multi-output split (automatic prompt line distribution)
- Template variable nested resolution
- Improved negative keyword robustness

## Key Stats

| Metric | V16.4 | V17.0 |
|--------|-------|-------|
| Lines | ~1,390 | 1,229 |
| Parameters | 38 | 58 |
| Output ports | 5 | 7 |
| Test count | 37 | 45 |
| Pass rate | 100% | 100% |

## Pipeline Order (Final)

```
read folder → scan files → load lines → _smart_filter → _filter_by_subject →
  pick_n_lines (4 modes) → history_dedup → [AI generation / storyboard] →
  AI polish → template variable replace (with nested resolution) →
  editing pipeline (regex→HTML→whitespace→length trim) →
  negative prompt generation → format conversion (SD/SDXL/SD3/Flux) →
  export (CSV/JSON) → batch AI generation → AI translation →
  scoring/sorting → multi-output split → OUTPUT
```

## Output Port Mapping (V17.0)

```
index 0: 提示词 (STRING) — the final prompt(s), \\n-separated if multiple
index 1: 元数据JSON (STRING) — JSON with filtering stats, timing, source chain
index 2: 来源说明 (STRING) — human-readable pipeline description
index 3: 负面提示词 (STRING) — comma-separated negative prompt terms
index 4: 输出行数 (INT) — number of prompt lines in output
index 5: 输出分流 (STRING) — multi-output split (2nd stream or first line)
index 6: 评分报告 (STRING) — JSON scoring report (best/avg/sorted count)
```

## Test Suite Summary (45 tests)

All tests pass. Critical edge cases:
- Empty folder, non-existent path, no files
- All lines filtered → error
- Unicode characters in prompts
- Multi-threaded concurrent access (5 threads)
- 10 continuous calls with same node instance
- Maximum read lines with 100-file folder
- Seed reproducibility across calls
- Template variable replacement with none, some, and all variables
- Negative prompt generation with body-part-specific terms
- Scoring with 0-weight dimensions
- Multi-output with single-line prompt (graceful fallback)

## Scoring Algorithm Detail

```python
score = 50  # base
# Length: weight * saturation at 800 chars
score += weight_length * min(length/800, 1.0)
# Diversity: weight * unique punct types / 5
punct_set = set(c for c in line if c in "，。、；：？！""''【】（）…—·")
score += weight_diversity * min(len(punct_set)/5, 1.0)
# Detail: weight * adjective-like particles / 10
detail = len(re.findall(r'[的之地]+', line))
score += weight_detail * min(detail/10, 1.0)
# Emotion: weight * emotion chars / 3
emotion = len(re.findall(r'[喜怒哀乐愁悲欢爱恨憎惧惊忧思恋羡慕感动温暖冷漠孤寂]', line))
score += weight_emotion * min(emotion/3, 1.0)
```

All scores are normalized such that the theoretical max is 50 + sum(weights). With default weights (30+25+25+20=100), max score ≈ 150.

## File Recovery (This Session)

See `references/file-safety-recovery-20260521.md` for the complete recovery of this file from truncation (2.8K → 24K → 63K).
