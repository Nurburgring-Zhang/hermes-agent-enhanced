# Extraction Strategy Benchmark Results (2026-05-23)

## Test Setup
- 100 samples from to_chi (50 javrate + 50 xhs filtered for person content)
- Each strategy evaluated on: extract rate, unique values, dirty data presence

## Results Summary

| Strategy | Extract Rate | Unique Values | Dirty Data | Best For |
|----------|-------------|---------------|------------|----------|
| **A** Regex Semantic Split | 100% | 300 | ⚠️ Yes | Breadth |
| **B** Two-Stage Cleanse | 66% | 197 | ⚠️ Reduced | Precision |
| **C** Semantic Template | 95% | 147 | ⚠️ Yes | Technical dims |
| **D** A+B+C Fusion | 66% | 212 | ⚠️ Medium | Balanced |
| **F** Multi-Strategy Pipeline | 52% | 213K total | ✅ Clean | Production Winner |

## Strategy Descriptions

### A: Regex Semantic Split
Separate text into description section + technical section, then apply targeted regex patterns per dimension. Broad but catches noise.

### B: Two-Stage Cleanse
First filter invalid data (non-person, multi-person), THEN extract. Removes ~34% of data but improves precision.

### C: Semantic Template
Use fixed sentence patterns like `身着(XX)` and `站在(XX)` for extraction. High precision but misses dimensions outside templates.

### D: A+B+C Fusion
Run all three, merge results, deduplicate. Balanced but inherits some noise from A.

### F: Multi-Strategy Pipeline (Winner)
3-layer architecture: Cleansing → Boundary-Aware Extraction → Quality Scoring.

## Key Innovations in Strategy F

1. **Boundary-Aware Extraction** — instead of cutting at "搭配" keyword, detects connector words and decides whether to keep or cut
2. **Quality Scoring** — discard results with <30/100 score
3. **javrate-first** — all javrate data passes cleansing; xhs gets strict filtering
4. **Sub-library split** — 01_人物外貌 split into 5 independent sub-libs to prevent logic conflicts

## Production Pipeline Output

260 to_chi files (518,013 total lines) → 270,516 passed cleansing → 268,229 extraction attempts → 213,938 final entries

## Production Costs
- Runtime: ~5 minutes on local CPU for all 260 files
- Memory: ~200MB peak
- Output: 18 library files, 213K entries
