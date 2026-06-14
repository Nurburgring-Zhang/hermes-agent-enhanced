# V7 Production Run — 10-Hour Post-Mortem (2026-05-24)

## What Happened

Built `build_v7_final.py` — a 5-concurrent-worker pipeline processing to_chi source files through DeepSeek API, producing 17 dimension libraries. Ran for 10 hours then auto-paused.

## Results

| Metric | Value |
|--------|-------|
| Runtime | 10 hours (auto-paused) |
| Source files processed | ~190/261 |
| Source lines processed | ~19,500 |
| Total fragments extracted | **2,011,891** |
| Failure rate | ~3% (618 log entries, mostly recovered by fallback) |
| Hallucination rate | ~0% (all fragments verified as source substrings at write-time) |

## Dimension Library Sizes

| Dimension | Lines | Notes |
|-----------|-------|-------|
| B01_场景环境 | 449,266 | Environment/location — biggest, richest |
| C01_美学风格 | 275,477 | Style/photo type |
| C04_构图镜头 | 215,114 | Composition/depth of field |
| C02_光照条件 | 135,061 | Lighting |
| C03_色彩调性 | 133,684 | Color tone |
| A05_姿势 | 128,596 | Poses/limb positions |
| B02_活动行为 | 103,407 | Human actions **✅** |
| D01_服装款式 | 88,673 | Clothing |
| D02_配饰鞋帽 | 55,051 | Accessories **✅** |
| A01_年龄性别 | 57,282 | Age/gender |
| A02_发型 | 52,576 | Hairstyle |
| A04_表情眼神 | 36,192 | Expression/eye gaze |
| D05_天气时间 | 32,218 | Weather/time |
| A03_肤色 | 23,908 | Skin tone |
| D04_动态效果 | 11,420 | Dynamic effects |

## Problems Encountered

1. **Progress file never written** (`_progress.json` was empty) — the `threading.Lock` around JSON serialization + file write wasn't sufficient because `save_progress()` was only called every 5 chunks but the Session counter had a bug: fallback-recovered sub-batches incremented the fragment counter but not the session counter, so the "every 5 chunks" trigger never fired.

2. **Some files consistently fail** — about 5-8 files have unusual Unicode or very long single lines that consistently trigger JSON parse errors even at 10-row fallback. These need pre-filtering.

3. **Fallback sometimes skips counting** — the `process_batch()` return value from fallback was `True/False` but the main loop didn't track it correctly for the `completed_chunks` list.

## What To Fix In V8

- Use SQLite for progress tracking instead of JSON file (solves the concurrency race condition)
- Pre-scan files for problematic content before processing
- Track completed chunks in the main loop properly, not in worker threads
- Add a periodic progress flush timer (every 3 minutes) independent of chunk count
