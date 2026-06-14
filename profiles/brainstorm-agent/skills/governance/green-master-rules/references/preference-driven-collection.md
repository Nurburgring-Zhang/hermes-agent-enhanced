# Preference-Driven Collection Filtering

Captured from 2026-05-27 session where the user asked "是经过过滤之后才进行采集吗？"

## Architecture

Two-level filtering, both happening BEFORE data hits the database:

### Level 1: Platform-level (waste avoidance)
Before calling a platform's API, check `is_worth_collecting(source, platform)`:
- **High priority** (22 platforms): always collect
- **Medium priority** (12 platforms): normal
- **Low priority** (4 platforms): 50% random skip
- Config: `reports/collector_preferences.json` → `collector_priority`

### Level 2: Content-level (relevance gating)
Every item passes through `is_user_interest(title, content)` before any other check:
1. **Discard directions** (股票/基金/房产/娱乐八卦/养生/星座/综艺/直播带货) → immediate reject
2. **P0 core** (AI/LLM/Open Source/Phone/Chip/EV/Military/Robot/Security/Politics) → weight ×2.5
3. **P1 high** (Fighting/NBA/Photography/Movie/Music/Game/Science/Space/Auto) → weight ×1.5
4. **P2 general** (Travel/Food/History/Fashion) → weight ×1.0
5. **No match** → reject (not user interest, don't waste scoring compute)

### Fallback
If `collector_preferences.json` doesn't exist, all content passes through (no-op).

## Key Files
- `scripts/unified_collector_v5.py` — `is_user_interest()` and `is_worth_collecting()`
- `reports/collector_preferences.json` — the **single source of truth** for user interests
- `scripts/hermes_v12_push.py` — `TAG_TO_TIER` dict for push-stage preference ranking (same tier names)

## Pitfalls
1. **Don't put preference logic in code.** It goes in `collector_preferences.json` only. Code reads the JSON.
2. **Don't rely on post-hoc tags for pre-collection filtering.** Tags (`extract_tags()`) are for push-stage ranking. Pre-collection filtering uses keyword matching against title+content.
3. **Blacklist is still needed** for anti-spam (clickbait headlines, NSFW). The preference filter handles *relevance*, the blacklist handles *quality*.

## Cron Jobs Affected
- `unified-collector` (uses the v5 collector with new filtering)
- Blacklist reloads from `spam_filter_keywords` table on first call in each cron cycle
