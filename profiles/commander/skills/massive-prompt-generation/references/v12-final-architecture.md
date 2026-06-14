# v12 Final Architecture & Cleaning Pipeline

## Files

| File | Path | Purpose |
|------|------|---------|
| v12 engine | `维度库/combine_engine_v12.py` | Final engine with gender fix + 3-layer logic + fixed template |
| A02 cleaner | `维度库/clean_v3_a02.py` | Cleaned A02_发型 7518→2991 (pure hair tags only) |
| All-dims cleaner | `维度库/clean_v3_all_dims.py` | Cleaned ALL dims 107K→88K |
| All-dims diagnostic | `维度库/diagnose_v3_all.py` | Showed purity % per dimension before cleaning |
| v5 builder (reference) | `维度库/final_build_v5_tag.py` | Built 591K tag library but purity insufficient |
| v4 cleaner (buggy) | `维度库/repair_v4_labels.py` | Had D02 bug (cleared to 1 entry) |
| v4 builder (reference) | `维度库/final_build_v4_label.py` | Direction correct, D01/D02 cleaning buggy |

## Cleaning Output

```
A02_发型：   7518 → 2991 (40% pure hair tags)
A04_表情：   1731 → 1629 (94%)
A05_姿势：   4007 → 2651 (66%) — removed "裸体女性跪在" etc
B01_场景：  15009 → 12653 (84%) — removed "裔女性在浴室" etc
B02_活动：   5011 → 3700 (74%) — removed "女子站在" etc
D01_服装：  15026 → 6088 (41%) — removed entries with person/place words
D02_配饰：   5014 → 4747 (95%)
D03_材质：    283 → 256  (90%)
D04_动态：    259 → 220  (85%)
D05_天气：   2502 → 2467 (99%)
D06_氛围：   1077 → 978  (91%)
Total:     107762 → 88705
```

## v12 Gender Check: 200+ Female Words

The key improvement over v10.1 was expanding FEMALE_WORDS from ~60 to 200+ and applying it at TWO points:

1. **`pick()` phase**: Pre-filter D01/D02 candidates (same as v10.1)
2. **After `clean_text()`**: Re-check cleaned D01/D02 content — if any female word detected and A01 is male, CLEAR the item entirely (not just re-pick)

The expanded word set covers:
- Garments: 文胸/蕾丝/比基尼/丁字裤/胸罩/抹胸/内衣/内裤/纱裙/薄纱/连衣裙/裙子/吊带裙/蕾丝裙/蓬蓬裙/百褶裙/雪纺/吊带/露肩/高跟鞋/凉鞋/丝袜/渔网袜/黑丝/白丝/过膝袜/吊袜带/婚纱/头纱/发箍/发带/手链/腮红/唇膏/口红/眼影/耳坠/耳钉/指甲油/公主裙/娃娃领/荷叶袖/泡泡袖/女仆装/连体泳衣/细肩带/低背剪裁
- Styles: 粉色/樱花粉/裸粉/粉红/浅粉/粉嫩/腮红粉
- Patterns: 花卉图案/花卉刺绣/花卉纹/花卉印花/花朵装饰/蝴蝶结装饰

## 3-Layer Logic Check (`check_logical()`)

```
Layer 1 - Body Parts: hand < 5, leg < 4 (catches "三只手" etc)
Layer 2 - Logic: 
  - No multi-person words (两名/一对/她们 etc)
  - No scene contradiction (indoor+outdoor words)
  - No race contradiction (亚裔+金发)
Layer 3 - Pronoun: 她/他 count consistent with A01 gender
```

## Engine Architecture

```python
# gen_one() flow:
1. Pick A01 → determine gender
2. Pick style seed (from 15_女性风格库.txt, 2000 entries)
3. Pick B01 scene → clean_text (strip prefixes, cut at punctuation)
4. Pick A02/A04/A05/B02 → clean_text
5. Pick D01/D02 with gender filter → clean_text → RE-CHECK with FEMALE_WORDS
6. Pick C01/C02/C03/D03/D06 (tech layer)
7. Fixed template assembly:
   "[style seed]。在[scene]中，[A01]，[a02]，[a04]。[pronoun]穿着[d01]，搭配[d02]。[pronoun][a05]，[b02]。[c02]。[c01]。[c03]。"
8. check_logical(txt, gender) → reject if fails
9. Length check: 200-1000 chars
```

## v12 vs v10.1 Comparison (100条 blind test)

| Metric | v10.1 | v12 |
|--------|-------|-----|
| 性别断裂(前30条) | ~5/30 (17%) | **0/100 (0%)** |
| 逻辑错误 | ~3/30 (10%) | **0/100 (0%)** |
| Success rate | 100% | 100% |
| Avg length | 268 | 256 |
| 速度 | 0.6s/100 | 0.9s/100 |
