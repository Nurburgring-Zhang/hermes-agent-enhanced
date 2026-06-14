# PromptLibraryNode Filter — 6-Layer Fix for Pure Interior/Food/Furniture Prompts

## The Problem

Prompts containing only indoor scenes, food items, or furniture were passing through the filter. Root cause: 6 independent bugs that had to be fixed simultaneously.

## Layer 1: `_smart_filter` Skip-Entire-Batch Bug

**Original code:**
```
_check STRONG_LIFELESS_SIGNALS — if found, skip entire batch_
combined_text = " ".join(l["text"][:200] for l in lines[:50])
for signal in self.STRONG_LIFELESS_SIGNALS:
    if signal in combined_lower:
        return None  # skips ALL filtering for this batch
```

**Problem:** STRONG_LIFELESS_SIGNALS contained "场景","氛围","室内","温馨" — any pure interior/food prompt containing these words caused the entire batch to skip filtering.

**Fix:** Remove the early-return block entirely. Let every line go through individual keyword checks.

## Layer 2: WHITELIST_WORDS Overly Permissive

**Original WHITELIST contained:**
"城市", "都市", "街道", "巷子", "建筑", "教堂", "城堡", "宫殿", "村庄", "小镇", "庭院"

**Problem:** These words appear in both real subject prompts (人物+建筑) AND pure interior prompts (室内+建筑). WHITELIST acts as a bypass — if ANY whitelist word matches, the line is kept without subject check.

**Fix:** Remove them from WHITELIST_WORDS.

## Layer 3: `_filter_by_subject` "Whitelist OR Subject" Logic

**Original code:**
```
if self._has_subject(clean_text) or self._white_list_override(text):
    filtered.append(entry)
```

**Problem:** `_white_list_override()` alone could trigger a pass — no subject required. Pure interior prompts like "室内客厅，沙发茶几" passed because "菜" in WHITELIST triggered override.

**Fix:** Remove `_white_list_override` from the OR. Only `_has_subject(clean_text)` can pass.

## Layer 4: `_has_subject` Single-Char False Match

**Original body words:**
```
["脸", "头", "眼", "眉", "鼻", "嘴", "唇", "耳", "站", "坐", "躺"...]
```

**Problem:** "摆盘" matched "摆". "沙发" matched "发" (in "长发" list). "马卡龙" matched "马" (in STRONG_SUBJECT_SIGNALS). "龙井茶" matched "龙".

**Fix:** All body words must be 2+ characters. Remove single-char animals "马","龙","猫","狗" from STRONG_SUBJECT_SIGNALS. Replace with compound forms: "骏马","雄鹰","猫咪","狗狗","橘猫". Add fallback guard for single-char animal checks using anti-false-match list:

```python
# Anti-false-match guard — clean pattern using not any() for maintainability
# Add future false-match triggers to the tuple without changing the logic
if "猫" in text and not any(no in text for no in ["猫粮", "天猫", "猫砂", "猫眼", "猫耳"]):
    return True
if "狗" in text and not any(no in text for no in ["狗粮", "热狗", "狗仔"]):
    return True
```

## Layer 5: LIFELESS_KEYWORDS Missing Common Items

**Added:**
"甜点", "蛋糕", "面包", "马卡龙", "咖啡", "卡布奇诺", "家具", "沙发", "餐桌", "茶几", "柜子", "置物架", "窗帘"

**Problem:** Pure food prompt "精致的法式甜点摆盘，马卡龙排列整齐" — none of the old LIFELESS_KEYWORDS matched "甜点","马卡龙".

## Layer 6: STRONG_SUBJECT_SIGNALS Containing Non-Subject Words

**Removed from STRONG_SUBJECT_SIGNALS:**
"建筑", "城堡", "教堂", "宫殿", "桥梁", "灯塔"

**Problem:** "建筑" appears in pure indoor prompts AND real subject prompts. Having it in STRONG_SUBJECT meant pure indoor prompts got a false positive subject match.

## Fixed Filter Logic

_smart_filter (per-line):
1. Check STRONG_SUBJECT_SIGNALS for real subject → if found, KEEP (skip lifeless check)
2. Check body word list (2-char only) → if found, KEEP
3. Fallback: check single-char animals with anti-false-match guards
4. Check LIFELESS_KEYWORDS → if found and no subject, FILTER
5. Otherwise KEEP (conservative fallback)

_filter_by_subject (per-line):
1. Strip FALSE_POSITIVE_COMPOUNDS from text
2. Check _has_subject(clean_text) → if found, KEEP
3. Otherwise FILTER (NO _white_list_override fallback)

## Verification Test Cases

| Prompt | Expected |
|--------|----------|
| "室内客厅，沙发茶几，落地窗" | FILTER |
| "法式甜点，马卡龙，慕斯蛋糕" | FILTER |
| "橡木餐桌，伊姆斯椅，陶瓷花瓶" | FILTER |
| "一位优雅的女性坐在客厅沙发上" | PASS |
| "一只橘猫蜷缩在窗台上" | PASS |
| "壮丽的日落山脉，金色阳光" | PASS |
