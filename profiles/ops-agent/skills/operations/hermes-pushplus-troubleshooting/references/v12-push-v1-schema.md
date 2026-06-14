# V12 Push v1 Schema & Optimization

> Last updated: 2026-05-31

## Pipeline Stages (push_v12)

```
1. load_recent_pushed(72h)    → already_pushed set
2. get_candidates_balanced()  → 300 candidates (72h window)
3. score_quality()            → time-decayed preference score
4. is_trash()                 → keyword/pattern filter
4.5 freshness_filter          → discard old/no-date items (NEW)
5. exclude_already_pushed     → remove from already_pushed set
6. dedup_by_title             → exact title dedup
7. chinese_first              → 80% chinese + 20% english target
8. enforce_diversity          → max 30% per platform
9. second_trash_check         → final quality gate
10. build_html_message        → clickable links + platform colors
11. push_wechat(pushplus)     → deliver
12. record_pushed             → write to push_records
```

## score_quality() Weight Distribution

| Component | Weight | Details |
|-----------|--------|---------|
| `ai_score_total` | 0.40 | AI 6-dimension score |
| tag direction bonus | 0.25 | P0→+20pts, P1→+12pts, other→+5pts |
| keyword_bonus | 0.25 | matched user keywords ×2.0 each |
| personal_match | 0.10 | stored preference score |
| P0 tag bonus | +20 (additive) | only when ai_score > 0 |
| AI>=60 bonus | +10 (additive) | high quality signal |

## Time Decay (NEW)

```python
time_decay = 1.0
if pub_days_old > 14:
    time_decay = max(0.1, 1.0 - (pub_days_old - 7) * 0.05)
elif not pub_str:
    time_decay = 0.7  # no published_at
total = raw_total * time_decay
```

## Freshness Filter (NEW)

Inserted between step 4 (is_trash) and step 5 (exclude_already_pushed):
- `published_at > 14 days OR empty` + `ai_score < 80` → discard
- `empty published_at` + `ai_score < 50` + `collected_at > 24h` → discard
- Otherwise keep
