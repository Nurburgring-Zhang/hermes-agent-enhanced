---
name: push-preference-matching-tags
description: "Push推送引擎的格林主人偏好匹配优化——将extract_tags方向标签集成到推送评分系统，替代旧的关键词→category映射。核心：TAG_TO_TIER映射45+方向标签到P0/P1/P2三层权重、score_quality整合AI评分+tags方向评分、get_candidates_balanced三阶段优先候选策略。"
trigger: "User asks to improve push content matching, fix recommendation quality, or integrate direction tags into the push pipeline."
---

# Push Preference Matching via Tags-Direction Scoring

## Overview

## 触发条件
- 用户提及Hermes系统状态、配置、诊断时
- 需要检查或修复Hermes自身功能时
- 执行系统升级、能力激活、模块检查时


The Hermes v12 push system (`hermes_v12_push.py`) delivers curated intelligence to WeChat via PushPlus. This skill covers the **preference matching overhaul** that replaced the old keyword→category scoring system with a **tags-direction-label-based scoring system**, integrated with AI scores.

## Architecture Changes

### Old System (Broken)
- `CATEGORY_MULTIPLIER` — only 15 categories hardcoded
- `score_quality()` — keyword-only matching, no tag awareness
- `get_candidates_balanced()` — per-platform blind fetch, no direction preference
- `is_trash()` — had undefined `DB` variable bug, `import sqlite3` inside loop

### New System
- **`TAG_TO_TIER`** — 45+ direction tags mapped to P0/P1/P2 tiers
- **`score_quality()`** — integrates `tags` field (from `extract_tags()`) + AI score + keyword matching
- **`get_candidates_balanced()`** — 3-stage candidate selection: P0/P1 tagged → all tags → General fallback
- **`is_trash()`** — relaxed for AI-scored content (score ≥ 50 → only block hard trash)

## Implementation Steps

### 1. Database Preparation: Backfill Tags

Before modifying the push script, ensure the database has direction tags:

```python
# Run extract_tags() backfill on all existing data
sql = """
UPDATE cleaned_intelligence SET tags = ? 
WHERE id = ? AND (tags IS NULL OR tags = '' OR tags = 'General')
"""
# Expected: 99%+ coverage after backfill
```

### 2. Replace CATEGORY_MULTIPLIER with TAG_TO_TIER

Delete the old 15-entry category multiplier dict. Replace with:

```python
TAG_TO_TIER = {
    # P0 (weight 2.5x) — core interests
    "AI": "P0", "AI_LLM": "P0", "AI_News": "P0",
    "Dev_OpenSource": "P0", "Dev": "P0", "OpenSource": "P0",
    "Mobile_PC": "P0", "IT": "P0", "Consumer_Electronics": "P0",
    "Tech": "P0",
    "Military_Intl": "P0", "Military": "P0",
    "EV": "P0", "Auto": "P0", "Auto_Moto": "P0",
    "Security": "P0",
    "Politics": "P0",
    "Robot": "P0",
    # P1 (weight 1.5x) — high interest
    "Sports_Fight": "P1", "Martial_Arts": "P1",
    "Beauty_Photo": "P1",
    "Movie_Video": "P1", "Movie": "P1",
    "Music": "P1",
    "Art": "P1", "Photography": "P1",
    "Game": "P1",
    "Science": "P1",
    "Space": "P1",
    "Sports": "P1",
    # P2 (weight 1.0x) — general
    "Travel_Food": "P2", "Travel": "P2",
    "History_Culture": "P2", "History": "P2",
    "Fashion": "P2", "Entertainment": "P2",
    "Social_News": "P2", "Life": "P2",
    "News": "P2", "Platform": "P2",
    "Video": "P2", "Startup": "P2",
    "Paper": "P2", "ArXiv": "P2",
    "Hot": "P2",
    "General": "P2",
}
TIER_MULTIPLIER = {"P0": 2.5, "P1": 1.5, "P2": 1.0}
```

### 3. Rewrite score_quality()

The core scoring function — **combines AI score + tags direction score + keyword bonus + personal match**:

```python
def score_quality(item):
    ai_score = float(item.get('ai_score_total', 0) or 0)
    text = ((item.get('title', '') or '') + ' ' + (item.get('content', '') or '')).lower()
    
    # Part 1: Tags direction label scoring
    tags_str = item.get('tags', '') or ''
    tags = [t.strip() for t in tags_str.split('|') if t.strip()]
    tag_bonus = 0.0
    tag_tiers = set()
    
    # AI-available content gets full weight; un-scored content gets 30%
    ai_available = ai_score > 0
    tag_weight = 1.0 if ai_available else 0.3
    
    for tag in tags:
        tier = get_tier_for_tag(tag)  # uses TAG_TO_TIER
        mult = TIER_MULTIPLIER.get(tier, 1.0)
        if tier == "P0":
            tag_bonus += 20.0 * mult * tag_weight  # ~50 pts with multiplier
        elif tier == "P1":
            tag_bonus += 12.0 * mult * tag_weight  # ~18 pts with multiplier
        elif tag not in ("General", "News"):
            tag_bonus += 5.0 * mult * tag_weight   # ~5 pts
    
    # Part 2: Keyword matching (preserved from old system)
    kw_rows = load_user_keywords()
    kw_bonus = sum(weight * 2.0 for kw, weight, cat in kw_rows if kw.lower() in text)
    
    # Composite score
    total = ai_score * 0.4 + tag_bonus * 0.25 + kw_bonus * 0.25 + personal_match * 0.1
    
    # Tier bonus (only if AI-scored)
    if "P0" in tag_tiers and ai_available: total += 20.0
    elif "P1" in tag_tiers and ai_available: total += 10.0
    if ai_score >= 60: total += 10.0
    
    item['_matched_tiers'] = tag_tiers
    return total, len(tags) + len(matched_kws)
```

### 4. Rewrite get_candidates_balanced()

Three-stage candidate fetching — **prefer tagged content, fall back to General**:

```python
def get_candidates_balanced():
    """
    Stage 1: Fetch P0/P1 direction-tagged + high AI score content (limit ~300)
    Stage 2: If < 80 candidates, expand to all non-General tagged (limit ~500)
    Stage 3: If still < 120, supplement with low-score tagged + General high-score
    """
    cutoff = (datetime.now() - timedelta(hours=72)).isoformat()
    
    # Stage 1 SQL: direction tags match P0/P1 interests
    sql_stage1 = """
        SELECT ... FROM cleaned_intelligence
        WHERE collected_at >= ?
          AND (COALESCE(ai_score_total,0) >= 15 OR COALESCE(importance_score,0) >= 15)
          AND tags IS NOT NULL AND tags != '' AND tags != 'General'
          AND (tags LIKE '%AI%' OR tags LIKE '%Military%' OR tags LIKE '%Tech%' ...)
        ORDER BY ai_score_total DESC LIMIT 300
    """
```

### 5. Fix is_trash()

Two bugs and one enhancement:

```python
# BUG 1: str(DB) was undefined → should be str(DB_PATH)
# BUG 2: item.get('id') called item which wasn't passed → add item parameter
# Enhancement: High AI-score content bypasses strict trash filtering

def is_trash(title, content="", item=None):
    item_score = float(item.get('ai_score_total', 0) or 0) if item else 0
    if item_score >= 50:
        # Only block the hardest trash for high-quality content
        HARD_TRASH = {"目瑙纵歌", "小说", "修仙", ...}
        for kw in HARD_TRASH:
            if kw.lower() in text: return True
        return False  # Auto-pass
    # Normal strict filtering for low-score content
    ...
```

### 6. Update HTML Builder

Replace keyword→category tier lookup with tags-based lookup in `build_html_message()` and preview:

```python
# OLD (broken after CATEGORY_MULTIPLIER removal):
matched_tiers.add(get_tier_for_category(cat))

# NEW (uses tags field):
item_tags = item.get('tags', '') or ''
for t in item_tags.split('|'):
    if t.strip():
        matched_tiers.add(get_tier_for_tag(t.strip()))
```

## Common Pitfalls

### 1. `log()` function missing after edits
The v12 script is large (720+ lines) — `log()` is a helper function defined around line ~108. If a patch removes it, the script crashes with `NameError: name 'log' is not defined`. Always check `grep -n "def log"` after batch edits.

### 2. `is_trash()` uses `DB` and `item` as globals (bug)
The original script had:
```python
sdb = sqlite3.connect(str(DB))        # DB should be DB_PATH
(item.get('id'), title[:60], kw)      # item not passed as parameter
```
Fix: change `DB` → `DB_PATH`, add `item=None` parameter, pass it from callers.

### 3. `get_tier_for_category()` was removed but still referenced
After deleting `CATEGORY_MULTIPLIER` and related functions, remaining references to `get_tier_for_category()` in `build_html_message()` and preview section cause `NameError`. Replace with `get_tier_for_tag()` + tags field parsing.

### 4. Duplicate function definitions
When patching, `get_tier_marker()` was defined twice (old and new versions). Check with `grep -n "def.*tier"` after edits.

### 5. AI-score discount for un-scored content
Un-scored (ai_score=0) content with direction tags can rank too high. Key fix: `ai_available = ai_score > 0` → set `tag_weight = 0.3` for un-scored content.

### 6. is_trash too aggressive for good content
Original `TRASH_KEYWORDS_HARD` blocked 91% of candidates. Fix: add `if item_score >= 50: return False` bypass for high-AI-score content.

### 7. 🔴 重复推送 — 三保险去重（2026-05-31 修复）
- **症状**: `push_records` 表同一条 `cleaned_id` 被推送3次（间隔约24h），如 `id=570932` 出现3次
- **根本原因（3层）**:
  1. **候选池层** — `get_candidates_balanced()` 所有4个SQL不排除已推送的 `cleaned_id` → 同条数据每次都能进候选
  2. **写入层** — `record_pushed()` 用**标题+24h窗口**去重 → 推送间隔12h，第2天(24h+)自动放行
  3. **过滤层** — Step 5只有标题去重 → 标题截断/空格差异导致很多已推送标题匹配不上
- **修复**: 三保险全链路：
  1. **候选池SQL根源排除** — 4个SQL全部加 `AND id NOT IN (SELECT DISTINCT cleaned_id FROM push_records WHERE push_time >= 72h)` 
  2. **写入层72h窗口** — `record_pushed()` 改按 `cleaned_id` 检查72h（旧: 标题+24h）
  3. **Step 5双重去重** — 标题去重 + `cleaned_id` 去重并行检查
- **教训**: 
  - 标题去重不可靠（截断差异/unicode同形异码/空格）— 永远用 `cleaned_id` 做主键
  - 所有候选SQL必须带已推送排除，不能依赖代码层面二次过滤
  - 去重窗口(24h)必须与推送间隔(12h)协调 — 窗口 < 2×间隔 = 必然产生重复
  
### 8. 🟡 旧闻推送 — AI评分>=80的无限放行（2026-05-31 修复）
- **症状**: 发布时间超过30天的旧文章（如"华为韬定律"系列）持续出现在候选池
- **原因**: 时效性过滤对AI评分>=80的内容**完全放行**，不做时间上限检查
- **修复**: AI>=80的内容也检查不超过30天（旧: 无限放行）
- **教训**: 任何"放宽"条件都要有上限，不能无限放行

## Verification

Run DRY RUN (no `--push` flag):

```bash
cd ~/.hermes && python3 scripts/hermes_v12_push.py
```

Expected output:
```
📡 方向标签优先模式: 取P0/P1方向数据
P0/P1方向候选: XX条
总候选: XXX条, X个平台
✅ 最终: XX条, X个平台
📋 推送预览(HTML):
  1. [✅] 🔥 [ithome] ⭐88 | 图灵测试...
  2. [✅] ⭐🔥 [hackernews] ⭐82 | Launch HN...
```

Quality checks:
- **7+ platforms**: hackernews, ithome, arxiv, weibo, bilibili, bilibili_tech, tieba
- **40-50 final items**: balanced diversity
- **Top items AI-scored ≥60**: high-value content first
- **🔥/⭐ markers**: P0 content gets 🔥, P1 gets ⭐
- **No un-scored trash in top 20**: low-quality content pushed to bottom

## Collector-Side Preference Filtering (2026-05-27)

The **push-side** preference scoring happens at push time — this is downstream. To reduce noise before it reaches the push pipeline, **collector-side** preference filtering was added:

### Architecture: Two-Layer Filtering

```
API/Web Fetch → parse → Layer 1: preference check (is_user_interest)
                          → hit P0/P1/P2? continue
                          → hit filter_discard? discard
                          → no match? discard
                       → Layer 2: spam keyword check (is_collect_filtered)
                       → Layer 3: quality pre-screen (min content length)
                       → INSERT into raw_intelligence
```

### Preference Config File: `reports/collector_preferences.json`

A **single JSON config file** replaces hardcoded keyword lists. Three interest tiers + discard list:

```json
{
  "p0_core": {
    "keywords": ["AI大模型", "ChatGPT", "新能源汽车", "军事", "机器人", ...],
    "tags": ["AI", "Dev_OpenSource", "Mobile_PC", "EV", ...]
  },
  "p1_high": {
    "keywords": ["格斗", "MMA", "UFC", "摄影", "电影", ...],
    "tags": ["Sports_Fight", "Beauty_Photo", "Movie_Video", ...]
  },
  "p2_general": {
    "keywords": ["旅游", "美食", "历史", ...],
    "tags": ["Travel_Food", "History_Culture", ...]
  },
  "filter_discard": {
    "keywords": ["股票", "基金", "房产", "娱乐八卦", "星座", "直播带货", ...]
  },
  "collector_priority": {
    "high_priority": { "platforms": ["weibo_hot", "zhihu_hot", "hackernews", ...] },
    "medium_priority": { "platforms": ["csdn_blogs", "juejin", ...] },
    "low_priority": { "platforms": ["weixin_accounts", "xiaohongshu_search", "douyin_hot", ...] }
  }
}
```

### Two Filter Functions in `unified_collector_v5.py`

| Function | When | What it checks |
|----------|------|----------------|
| `is_user_interest(title, content)` | Per-item, in `insert_raw_item()` | Title+content matches P0/P1/P2 keywords? Hits discard list? |
| `is_worth_collecting(source, platform)` | Per-platform, in `collect_all()` | Is this platform in high/med/low priority? Low gets 50% skip rate |

### Key Design Decisions

1. **Filter before insert, not before fetch** — We still fetch from the source, but check preference before writing to DB. This avoids wasting API quota on low-value platforms (via `is_worth_collecting`), but we can't know individual item content before fetching.

2. **Title-level matching is sufficient** — Most content's topic is clear from the title. Content field is appended for extra signal.

3. **Spam keywords cleaned up** — 21 false-positive words disabled (`夫妻`, `主播`, `荣耀`, `性感`, etc.), 28 new precise words added (`股票`, `基金`, `娱乐八卦`, `星座`, etc.).

4. **Single source of truth** — `collector_preferences.json` is the only place to edit preferences. Both `unified_collector_v5.py` and `hermes_v12_push.py` read from it (push side reads `TAG_TO_TIER` still in code — TODO: unify).

### Updating Preferences

Edit `reports/collector_preferences.json`:
- Add new P0 keywords → content with those keywords will get priority in insert + higher push score
- Add new filter_discard keywords → content with those keywords won't enter DB at all
- Platform priority changes → affects which platforms get API calls during collection

### Platform Priority Reference

| Priority | Platforms | Behavior |
|----------|-----------|----------|
| High | weibo_hot, zhihu_hot, hackernews, github_trending, 36kr, arxiv, bilibili_tech, sogou_wechat, ithome, huxiu, ifanr, tmtpost, infoq | Always fetch full data |
| Medium | baidu_hot, tieba, csdn, juejin, segmentfault, cnblogs, devto, freebuf, oschina, tencent_cloud, techmeme, kuaishou, sina_tech | Fetch normally |
| Low | weixin_accounts, xiaohongshu_search, douyin_hot | 50% chance to skip per cycle |

## Cron Integration

The push cron is in `crontab` and `guardian.py`:
```
0 8,12,18,0 * * * cd ~/.hermes && python3 scripts/guardian.py push
```

`guardian.py push` → calls `hermes_v12_push.py` → automatically runs with the new preference matching.

AI scoring cron (ensures newer data gets scored):
```
every 15m → ai-scoring-backfill cron job with DEEPSEEK_API_KEY
```

## Files

| File | Purpose |
|------|---------|
| `~/.hermes/scripts/hermes_v12_push.py` | Main push script (all modifications in this file) |
| `~/.hermes/scripts/hermes_ai_scoring.py` | AI scoring engine (needs API key for DeepSeek/OpenRouter) |
| `~/.hermes/logs/v12_push.log` | Push execution log |
| `~/.hermes/intelligence.db` | Database with `cleaned_intelligence` table containing `tags` field |
| `reports/推送优化完成.json` | Checkpoint report written after completion |

## References

- `references/collector-filtering-investigation-20260527.md` — 采集过滤机制调查：过滤发生在采集后入库前，351个黑名单关键词误杀问题，偏好方向缺乏采集前增强
- `references/2026-05-27-push-fix-log.md` — Push fix log
- `references/2026-05-31-dedup-old-article-investigation.md` — 推送去重与旧闻过滤深度调查记录：三保险去重修复（候选池SQL排除/写入72h窗口/双重去重）+ 旧闻30天上限

## 回滚方案
### 快速回滚
如果部署后发现问题：
1. 使用版本控制回退到上一个提交：`git revert HEAD`
2. 确认回滚后系统状态正常
3. 通知相关方变更已撤销

### 数据安全
- 所有修改前确认有备份
- 配置变更记录版本历史
