# v8 Final Scoring — 2026-05-28

## Best Run: combine_engine_v8.py + 维度库_final_build_v3

```
100/100 gen success
Avg: 86.8
Scene conflict: 90% pass (10% fail)
Hands(3+): 99% pass
Race: 99% pass
Gender: 100% pass
Metaphor: 100% pass
Tech words: 100% pass
Clothing stacking: 100% pass
Stand+bed: 100% pass
Duplicate: 100% pass
Word count: 100% pass
```

### v8 Final Failure Breakdown (12/100)

```
3 hand (1x):  #31
    scene (9x): #13, #33, #41, #49, #57, #58, #67, #88, #100
    race (1x):  #73
```

9/12 scene failures are style-seed-driven (style seed contains "咖啡馆窗边" + B01 chooses outdoor scene). The remaining ~3% are C02 scene-word false negatives.

## All-Engine Iteration Summary

| Version | Gen% | Avg | Scene | Hands | Race | Words | When | 
|---------|:---:|:---:|:-----:|:-----:|:----:|:-----:|:----:|
| v4.1 | 100 | 83.0 | 79% | 92% | 99% | 500-800 | 5/27 |
| v6 | 100 | 84.8 | 85% | 99% | 98% | 301 | 5/28 |
| v7 | 100 | 81.8 | 79% | 94% | 99% | 352 | 5/28 |
| v8final | 100 | 86.8 | 90% | 99% | 99% | 302 | 5/28 |

## Key File Locations

```bash
Engine:       维度库/combine_engine_v8.py
Dim lib v3:   维度库_final_build_v3/ (110,235 entries)
Dim lib v4:   维度库_final_build_v4/ (C02 split into 3 sub-dims)
QC filter:    维度库/quality_filter.py
Build v3:     维度库/final_build_v3_clean.py
C02 split:    维度库/rebuild_c02_v4.py
Supplement:   维度库/supplement_v3_dims.py
Trial v8:     /mnt/d/Hermes/1000000提示词/试生产100条_v8_final.txt
Trial v6:     /mnt/d/Hermes/1000000提示词/试生产100条_v6.txt
```
