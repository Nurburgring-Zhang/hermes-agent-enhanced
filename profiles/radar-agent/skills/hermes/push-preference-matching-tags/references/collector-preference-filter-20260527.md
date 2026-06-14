# Collector Preference Filter — Session Record 2026-05-27

## Problem
格林主人 asked: "过滤发生在采集前还是采集后？采集覆盖全面吗？我的偏好都采到了吗？"

Investigation found:
1. Filter was **after collection**, not before — API quota wasted on unwanted content
2. 351 spam keywords had 21+ false-positive words (`夫妻`, `主播`, `荣耀`, `性感`) that blocked legitimate content
3. No **preference configuration file** existed — TAG_TO_TIER only used at push time, not at collect time
4. All 38 platforms were fetched equally, no priority-based skipping

## Solution

### 1. Preference Config File
Created `reports/collector_preferences.json` with structured interest levels and platform priorities.

### 2. Two New Functions

#### `is_user_interest(title, content)` — in `unified_collector_v5.py`
```python
def is_user_interest(title, content=""):
    """
    Returns (is_interesting: bool, tier: str, matched_keyword: str)
    Order: P0 keywords → P1 keywords → P2 keywords → filter_discard → reject
    """
```

#### `is_worth_collecting(source, platform)` — in `unified_collector_v5.py`
```python
def is_worth_collecting(source, platform):
    """High priority = always; Medium = always; Low = 50% skip"""
```

### 3. Modified Functions

#### `insert_raw_item()` — 3-layer filter added:
1. `is_user_interest()` — preference gate (new)
2. `is_collect_filtered()` — spam keyword check (existing, reordered)
3. Quality pre-screen — min content length (existing)

#### `collect_all()` — platform-level pre-filter:
```python
filtered = []
for name, (fn, pri, _) in sorted_collectors:
    if is_worth_collecting(name, name):
        filtered.append((name, fn, pri))
```

### 4. Spam Keywords Cleanup

| Operation | Count | Examples |
|-----------|-------|---------|
| Disabled (false positives) | 21 | `夫妻`, `主播`, `荣耀`, `性感`, `泰国`, `想吃` |
| Added (precise) | 28 | `股票`, `基金`, `A股`, `房产`, `娱乐八卦`, `星座`, `直播带货` |
| Active after cleanup | 341 | |

## Verification

```bash
# Test preference matching
python3 -c "
from unified_collector_v5 import is_user_interest, is_worth_collecting

# Should pass: P0 AI content
assert is_user_interest('ChatGPT发布GPT-5')[0] == True

# Should be blocked: stock/real estate/finance
assert is_user_interest('楼市重磅：一线城市取消限购')[0] == False
assert is_user_interest('A股3000点保卫战')[0] == False
assert is_user_interest('明星夫妇官宣离婚')[0] == False

# Platform priority
assert is_worth_collecting('weibo_hot', 'weibo_hot') == True
# weixin_accounts is low priority — 50% chance
"
```
