# Collector/Scoring/Push Version Waterfall Cleanup (2026-05-27)

## Scope

Cleaned up 54 redundant/debug scripts from `~/.hermes/scripts/` — the largest single cleanup event.

## Rationale

Over months of development, each collector (微信/小红书/头条/unified) accumulated multiple iterative versions:
- 微信: 12 files (v3→v9 + bing + MCP + agent)
- 小红书: 9 files (v1→v5 + debug + login)
- 头条: 4 files (v1→v4 + enhanced)
- Unified collectors: 5 files (v1→v5, mega, ultimate)
- Push engines: 3 files (v9→v11→v12)
- Scoring: 5 files (ai_score_25, backfill, checker, apply, generate)
- Cleaners: 7 files (v1→v2, bulk, final, old)
- Debug/test: 17 files (test_*, debug_*)

## Cleanup Pattern

1. **Identify latest version** by modification date: `ls -lt *.py | grep pattern`
2. **Keep latest 1-2 versions** per function group
3. **Backup all removed files** to `/mnt/d/Hermes/备份/collector_cleanup_20260527/`
4. **Remove files** with `os.remove()` (after verifying no active cron references them)
5. **Verify** no cron references old filenames: `grep -r "old_script_name" ~/.hermes/scripts/*.py`

## What Was Kept

### Collection (25 kept from 62)
| Group | Kept | Removed |
|-------|------|---------|
| 微信 | wechat_mp_mcp_collector.py, wechat_agent_collector.py, wechat_mp_direct.py, wechat_content_enhancer.py | 8 old versions |
| 小红书 | xhs_collector_v4.py, v5, xhs_get_cookie.py, xhs_login_helper.py | 5 old/debug |
| 头条 | toutiao_browser_collector_v4.py | 3 old + debug |
| Unified | unified_collector_v5.py, hermes_ultimate_collector.py | 3 old/mega |
| Others | browser_collector.py, douyin_account_collector.py, csdn_blog_collector.py, etc. | — |

### Cleaning (11 kept from 19)
Kept: unified_cleaning_pipeline.py, hermes_deep_clean_v2.py, lowscore_cleaner.py, spam_filter.py, content_enricher.py, purge_dup_raw.py, context_token_filter.py, etc.

### Scoring (kept 2 main + hermes_ai_scoring)
Kept: hermes_ai_scoring.py, real_ai_scorer.py (removed 5 helpers: ai_score_25_items, backfill, checker, apply_scores, generate_scores)

### Push (kept 3)
Kept: hermes_v12_push.py, feedback_push.py, push_status.py (removed v9, v11)

## Cron Impact

No cron directly referenced removed scripts (guardian.py uses its own cycle/heal/push modes and calls scripts by function, not name). Verified with `grep -r "old_script_name" .`.

## Backup Location

All 54 removed files: `/mnt/d/Hermes/备份/collector_cleanup_20260527/`

## Collected Skill Lessons

### The "Is This Filtered Before or After Collection?" Debugging Pattern

When user asks about data pipeline integrity:
1. Trace the data flow: source → fetch → parse → `insert_raw_item()` → DB
2. Check `insert_raw_item()` for filter calls: `is_collect_filtered()` runs at line ~299
3. Check the filter keyword table: `spam_filter_keywords` in `intelligence.db`
4. Check the keyword severity: severity ≥ 3 = blocks insertion, severity < 3 = tags only

### The 351黑名单误杀 Problem (Discovered 2026-05-27)

The `spam_filter_keywords` table has 351 active keywords (334 at severity ≥ 3). Several are too aggressive:
- `"夫妻"` — blocks all marriage/family content
- `"荣耀"` — blocks Honor phone news
- `"主播"` — blocks livestreaming industry news
- `"性感"` — blocks all fashion/beauty content
- `"泰国"` — blocks Thailand-related news

These need auditing: either remove or lower severity. The filter runs on title + first 500 chars of content.

### Preference-Driven Collection Gap

The system has 40+ direction tags (AI, EV, Military, etc.) but these only apply **after** collection as classification labels. There is no preference-config file that injects格林主人's specific interests into the **collection phase** to boost certain directions. All platforms are collected equally, then filtered/ranked by tags at push time.
