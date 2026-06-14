# Hermes Auto-Tune — Current Parameter Values

> Last tuned: 2026-05-31
> Source: `reports/auto_tune/current_params.json`

## Active Parameters

| Parameter | Value | Range | Last Adjusted |
|-----------|-------|-------|---------------|
| `retrospect_threshold` | 60.0 | 30-80 | default (10 retro records, avg 70.9 → trend: improving → no change needed) |
| `quality_wall_check_interval` | 3 | 1-10 | default |
| `cron_push_frequency` | 4 | 2-6 | default |
| `skillopt_threshold` | 0.80 | 0.60-0.95 | default |
| `max_task_steps_before_checkpoint` | 10 | 5-20 | default |

## Decision Logic

### retrospect_threshold
```python
if avg_score > 70:           → 75.0   # quality high, raise bar
elif avg_score < 50:         → 45.0   # quality low, lower bar
else:                        → 60.0   # stable
```

### quality_wall_check_interval
```python
if avg_score > 75:           → 5 steps  # high quality, less checking
elif avg_score < 55:         → 2 steps  # low quality, more checking
else:                        → 3 steps  # default
```

### cron_push_frequency
```python
if ok_ratio < 70:            → freq - 1  # cron failures, reduce load
else:                        → 4         # default
```

### skillopt_threshold
```python
if avg_score > 72:           → 0.88     # high quality, raise bar
elif avg_score < 55:         → 0.70     # low quality, lower bar
else:                        → 0.80     # default
```

## A/B Test Framework Usage

```bash
# Create test
python3 scripts/hermes_auto_tune.py ab-test
# → creates 48h test comparing retrospect_threshold=55 vs 65

# Check results after 48h
python3 scripts/hermes_auto_tune.py ab-test
# → auto-evaluates based on retrospect scores during test window
```
