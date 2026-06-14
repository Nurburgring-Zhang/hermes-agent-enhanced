# PromptLibraryNode Design Patterns (V15.1 — Enhanced Subject Filtering)

## Architecture

Multi-function node that reads prompts from folder of .txt files, picks one (random/sequential/shuffle/weighted), optionally filters by subject, optionally runs AI polish/generation, outputs STRING+metadata.

```
folder_path → scan_files(.txt/.csv/.md/.jsonl) → load_lines → 
  _smart_filter (exclude still life / product shot) → 
  [V15] _filter_by_subject (exclude lifeless-only prompts) → 
  [V15.1] THREE-TIER subject detection (false-positive stripping + signal scoring + density scoring) →
  pick_n_lines (4 modes) → 
  [optional] AI polish → output
```

## Critical: IS_CHANGED for Cacheless Nodes

```python
@classmethod
def IS_CHANGED(cls, **kwargs):
    return time.time()
```

Without this, ComfyUI returns first execution's cached result forever.

## Chinese Parameter Names

ComfyUI parameter names become Python keyword argument names:
- ✅ `"随机种子_0为真随机": ("INT", ...)` — Chinese + underscore works
- ❌ `"固定种子(0=真随机)": ...` — `()` not allowed in Python keyword names
- ❌ `"固定种子=0": ...` — `=` is keyword arg separator

## The Validator + String Input Pattern

Use STRING instead of dropdown for backward-compatible parameters:

```python
"读取模式": ("STRING", {"default":"随机抽取"})
# Then in get_prompt() handle both old and new values
mode_map = {"Random":"随机抽取", "Sequential":"顺序循环"}
```

## BOOLEAN Toggle for Multi-Mode Nodes

```python
"启用主体过滤": ("BOOLEAN", {"default":True}),
"开启AI润色": ("BOOLEAN", {"default":False}),
"开启AI生成": ("BOOLEAN", {"default":False}),
```

## V15.1: Three-Tier Subject Content Filtering

The V15 single-pass filter had a critical flaw: **product names containing character substrings of body parts/animals** produced false positives (e.g., "手链" matched "手", "三文鱼" matched "鱼", "背景" matched "背"). The V15.1 enhancement adds two additional layers:

### Layer 1 — False-Positive Stripping (65+ compound words)

Strip known compound words from the text BEFORE matching WITH_SUBJECT_KEYWORDS. These are common Chinese nouns where a character substring happens to match a person/animal/body-part keyword:

| Category | Count | Examples |
|----------|-------|---------|
| 手 (hand) | 28 | 手链, 手表, 手机, 手套, 手工, 手法, 手镯, 手写, 手绘, 手柄 |
| 背 (back) | 9 | 背景, 背光, 背面, 背包, 背板, 背带, 脊椎, 驼背, 背心 |
| 鱼 (fish-food) | 28 | 三文鱼, 金枪鱼, 鱼片, 鱼丸, 鱼汤, 鱼头, 鱼排, 炸鱼, 烤鱼, 鱼缸 |
| 马 (horse) | 6 | 马铃薯, 马桶, 马路, 马达, 马赛克, 马甲 |
| 龙 (dragon) | 6 | 龙眼, 龙井, 龙须面, 龙头, 龙虾, 龙舌兰 |
| 蝴蝶 (butterfly) | 4 | 蝴蝶结, 蝴蝶酥, 蝴蝶兰, 蝴蝶袖 |
| 眼 (eye) | 6 | 眼镜, 眼影, 眼线, 眼霜, 眼膜, 眼罩 |
| 头 (head) | 6 | 头盔, 头饰, 头花, 头巾, 头绳, 头枕 |
| 指 (finger) | 6 | 指示, 指引, 指纹, 指针, 指挥, 指令 |
| 穿 (wear) | 5 | 贯穿, 穿梭, 穿越, 穿插, 穿透 |
| 其他 | 3 | 手机壳, 手机链, 天鹅绒 |

```python
FALSE_POSITIVE_COMPOUNDS = {
    "手链", "手表", "手机", ...  # 28 手类
    "背景", "背光", "背面", ...  # 9 背类
    "三文鱼", "金枪鱼", ...     # 28 鱼品类
    "马铃薯", "马桶", ...       # 6 马类
    "龙眼", "龙井", ...         # 6 龙类
    "蝴蝶结", "蝴蝶酥", ...     # 4 蝴蝶类
    "眼镜", "眼影", ...         # 6 眼类
    "头盔", "头饰", ...         # 6 头类
    "指示", "指引", ...         # 6 指类
    "贯穿", "穿梭", ...         # 5 穿类
    "手机壳", "手机链", "天鹅绒",
}

def _has_subject(self, text):
    t = text.lower()
    t_clean = t
    for fp in self.FALSE_POSITIVE_COMPOUNDS:
        t_clean = t_clean.replace(fp.lower(), "")
    for kw in self.WITH_SUBJECT_KEYWORDS:
        if kw.lower() in t_clean:
            return True
    return False
```

**Discovered via:** Scanning 6,000+ lines from RedNote (小红书) prompt folders. ~30% of "product description" prompts matched body-part keywords through substring collisions.

### Layer 2 — Strong Signal Score (Signal ≥ 2 → lifeless)

```python
STRONG_LIFELESS_SIGNALS = {
    "产品摄影", "商品摄影", "产品展示", "产品图", "商品图",
    "产品照", "商品照", "产品拍摄", "商品拍摄",
    "珠宝展示", "首饰展示", "展示架", "陈列",
    "平铺", "俯拍", "平拍", "微距拍摄",
    "商业摄影", "美食摄影", "食物摄影",
    "静物摄影", "静物",
    "室内设计", "装修风格", "装修效果", "家居设计",
    "室内效果图", "家装", "样板间",
    "工作室灯光",
}
```

Rules:
- ≥2 strong signals AND no explicit person marker (一位/一名/她的) → return False (no subject)
- Single pure trigger (PURE_PRODUCT_TRIGGERS) → return False immediately
- Strong signals ≥ 1 AND lifeless keywords ≥ 1 → return False

### Layer 3 — Keyword Density Score (Lifeless ≥ 3 → lifeless)

```python
def _is_only_lifeless(self, text):
    if self._has_subject(t): return False    # Layer 1 passed → not lifeless
    lifeless_count = count_lifeless(t)        # count LIFELESS_KEYWORDS hits
    strong_count = count_strong_signals(t)   # count STRONG_LIFELESS_SIGNALS hits
    
    if strong_count >= 2: return True        # Layer 2: signal score
    if lifeless_count >= 3: return True      # Layer 3: density score
    if strong_count >= 1 and lifeless_count >= 1: return True  # composite
    for kw in self.LIFELESS_KEYWORDS:       # fallback: standard match
        if kw.lower() in t: return True
    return False
```

Without density scoring, a "product shot of a necklace on a stand with a woman in the background" description might barely fail keyword checks either way. Density scoring catches borderline cases where lifeless attributes dominate.

### V15.1 _has_subject() — Complete

```python
def _has_subject(self, text):
    t = text.lower(); original = text
    
    # Layer 1: strip false-positive compounds
    t_clean = t
    for fp in self.FALSE_POSITIVE_COMPOUNDS:
        t_clean = t_clean.replace(fp.lower(), "")
    
    # Layer 2: strong signal check
    strong_count = sum(1 for sig in self.STRONG_LIFELESS_SIGNALS if sig.lower() in t)
    if strong_count >= 2:
        if not any(m in original for m in ["一位","一名","她的","他的","她们","他们"]):
            person_kw = count_person_keywords(t_clean)
            if person_kw <= 2:
                return False
    
    # Layer 2b: pure product triggers
    for trig in self.PURE_PRODUCT_TRIGGERS:
        if trig.lower() in t:
            if not any(m in original for m in ["一位","一名","她的","他的"]):
                return False
    
    # Layer 1+: standard WITH_SUBJECT matching on cleaned text
    for kw in self.WITH_SUBJECT_KEYWORDS:
        if kw in self.FALSE_POSITIVE_COMPOUNDS: continue
        if kw.lower() in t_clean:
            return True
    return False
```

### V15.1 _is_only_lifeless() — Complete

```python
def _is_only_lifeless(self, text):
    t = text.lower()
    if self._has_subject(t): return False
    
    lifeless_count = sum(1 for kw in self.LIFELESS_KEYWORDS if kw.lower() in t)
    strong_count = sum(1 for sig in self.STRONG_LIFELESS_SIGNALS if sig.lower() in t)
    
    # Pure product triggers
    for trig in self.PURE_PRODUCT_TRIGGERS:
        if trig.lower() in t: return True
    # Context scores
    if strong_count >= 2: return True
    if lifeless_count >= 3: return True
    if strong_count >= 1 and lifeless_count >= 1: return True
    # Standard keyword match
    for kw in self.LIFELESS_KEYWORDS:
        if kw.lower() in t: return True
    return False
```

### Rule set sizes (V15.1)

| Category | Count | Examples |
|----------|-------|---------|
| WITH_SUBJECT (人物) | ~50 | 女孩, 模特, 女子, 男子, 穿着, 双手, 微笑 |
| WITH_SUBJECT (动物) | ~20 | 猫, 狗, 鱼, 天鹅, 蝴蝶 |
| WITH_SUBJECT (风景) | ~30 | 森林, 海洋, 日落, 沙滩 |
| WITH_SUBJECT (角色) | ~20 | 公主, 精灵, 战士, 汉服 |
| WITH_SUBJECT (英文) | ~20 | woman, cat, landscape, portrait |
| LIFELESS (食物) | ~40 | 蛋糕, 咖啡, 刺身, 寿司, 蜡烛 |
| LIFELESS (室内) | ~30 | 客厅, 家具, 沙发, 墙壁 |
| LIFELESS (首饰) | ~20 | 项链, 钻石, 戒指, 珍珠 |
| LIFELESS (静物) | ~15 | 静物, 产品摄影, still life |
| FALSE_POSITIVE_COMPOUNDS | ~65 | 手链, 背景, 三文鱼, 马铃薯, 龙眼, 蝴蝶结 |
| STRONG_LIFELESS_SIGNALS | ~30 | 产品摄影, 美食摄影, 静物, 室内设计 |
| PURE_PRODUCT_TRIGGERS | 5 | 产品摄影, 商品摄影, 静物摄影, flat lay, still life |

### _filter_by_subject(lines) — The skip-and-retry pattern

```python
def _filter_by_subject(self, lines):
    passed, skipped = [], 0
    for line in lines:
        if self._has_subject(line["text"]):
            passed.append(line)
        elif self._is_only_lifeless(line["text"]):
            skipped += 1     # ← SKIP THIS LINE
        else:
            passed.append(line)  # ← conservatively keep
    return passed
```

If ALL lines are lifeless-only, returns empty list → upper layer returns error.

## V15.1: The RedNote Discovery Method (Real-Data Validation)

The V15.1 false-positive fixes came from scanning real production data. The method:

```python
# 1. Scan 2,000+ lines per file from RedNote prompt folder
# 2. Run _has_subject() on each, collect false positives
# 3. Cluster by MATCHED KEYWORD:
#    - "手链/手表/手机/手套" all matched "手" → add ALL to FALSE_POSITIVE_COMPOUNDS
#    - "背景/背包/背光" all matched "背" → add ALL
#    - "三文鱼/鱼片/鱼丸/鱼汤" all matched "鱼" → add ALL known fish-dish words
# 4. Verify fix doesn't break legitimate person descriptions ("女子戴手表" still has subject)
#    because "女子" is in WITH_SUBJECT and "手表" is stripped before matching
```

**Key insight from real data:** When you find one false positive (e.g., "手链"), the entire semantic class is likely affected. Add ALL members of that class, not just the one found. Pattern: "手链" → all 手 compound words → 28 entries.

## V15: Thread Safety

PromptLibraryNode caches state for Sequential/Shuffle modes (`self._cache`). With multiple node instances in one workflow, thread safety is needed:

```python
import threading

def __init__(self):
    self._cache_lock = threading.Lock()
    self._cache = {}

def _get_cache(self, k, d):
    with self._cache_lock:  # ← prevents concurrent pool depletion
        if k not in self._cache:
            self._cache[k] = d
        return self._cache[k]
```

**Without the lock:** Two threads calling `_pick_n_lines(Shuffle)` simultaneously can pop the same item from the pool → duplicates or index errors.

## V15: Smart Filter v2 — Chinese product photo support

The original _smart_filter only had English regex:
```python
r'\bproduct\s+shot\b'
```

This missed Chinese "产品摄影", "商品摄影", "静物摄影". V15 adds explicit Chinese blocklist:

```python
cn_block = {"产品摄影", "产品拍照", "商品摄影", "商品图", "静物摄影"}
for cb in cn_block:
    if cb in tl:
        is_blocked = True
        break
```

## V15: 500MB File Protection

```python
max_size = 500 * 1024 * 1024  # 500MB
try:
    file_size = os.path.getsize(fp)
    if file_size > max_size:
        continue  # skip silently (logs warning)
except OSError:
    continue
```

## V15: Max Lines Limit

New optional parameter `最大读取行数` stops loading after N lines, preventing OOM on huge folders:

```python
for n, raw in enumerate(fh, 1):
    ...
    if max_lines > 0 and total_read >= max_lines:
        break
```

## V15: URL Format Validation

```python
if not api_url.startswith(("http://", "https://")):
    self._last_ai_error = f"API地址格式无效: {api_url[:40]}..."
    return None
```

Prevents confusing `_call_ai` failures when user forgets protocol.

## V15: Enhanced Metadata

get_prompt returns detailed filtering stats in the JSON metadata:

```python
meta_info = {
    "过滤统计": {
        "总行数": 10000,
        "smart过滤": 50,       # excluded by _smart_filter
        "主体过滤跳过": 200,   # excluded by _filter_by_subject
        "最终有效": 9750
    },
    "elapsed_seconds": 0.03,
    "source": "提示词库(9750行)",
    ...
}
```

## V15: _smart_filter + _filter_by_subject Double-Pass

The two filters are **independent** and **sequential**:

1. `_smart_filter` — catches generic "no visual content" patterns (still life, product shots in both languages)
2. `_filter_by_subject` — catches "technically a visual scene but no person/animal/landscape" (pure food, interior decor, jewelry)

They should NOT merge — `_smart_filter` is conservative (~5% exclusion), `_filter_by_subject` is aggressive (can exclude 30-50% of prompt lines).

## The Extreme Test Cycle Pattern

Discovered in V15 development: a 3-round debug loop is the minimum for production-quality ComfyUI code.

### Round 1: Comprehensive unit tests
- Test every method in isolation
- Test every boundary: empty input, long input, missing files, concurrent access
- **Must hunt for bugs, not just verify known paths**
- Example bugs found: `len(t) < 3` filtering short Chinese lines,天鹅绒 false positive, complex false_positive logic bug

### Round 2: Fix + full regression
- Fix each bug with minimal change
- Re-run ALL tests (not just the failing ones)
- Verify no regressions

### Round 3: Real-data validation
- Run against actual production files (RedNote prompt folder)
- Verify false negative rate (prompts that should be filtered but aren't)
- Verify false positive rate (prompts that should be kept but got filtered)
- Iterate on the false-positive compound list based on real data

**V15.1 real-data test:** 15 RedNote product prompts all correctly filtered, 5 legitimate person/animal prompts all correctly kept. Zero false positives or false negatives.

### Known limits in V15.1

The FALSE_POSITIVE_COMPOUNDS list is Chinese-specific. English prompts with product brand names containing body-part words (e.g., "iPhone" contains "phone" not "ear" or "hand") are unlikely to trigger false positives, but the system is not tested on this scenario.

The context-scoring thresholds (≥2 strong signals, ≥3 lifeless keywords) were tuned on the RedNote dataset. Different prompt genres (e.g., pure food photography with no "美食摄影" tag) may need different thresholds.

## AI Integration Pattern

See `references/ai-api-integration-20260520.md` for full pattern. Key changes in V15:
- URL format validation before any network call
- Exponential backoff with capped retries (2 max)
- Thread-safe _last_ai_error (single var, no lock needed for writes)

## GLOBAL_CACHE vs Instance Cache

```python
# BAD: module-level, shared across all node instances
GLOBAL_CACHE = {}

# GOOD: per-instance, independent
def __init__(self):
    self._cache = {}
```

## Sync Between Source and ComfyUI

V15.1 lives at `D:\ComfyUI\custom_nodes\PromptLibraryNode\__init__.py`. The source copy at `D:\Hermes\1000000提示词\PromptLibraryNode\__init__.py` is the "backup." After each version, sync both directions.

## Known Failure Modes (V15.1)

| Scenario | Symptom | Fix |
|----------|---------|-----|
| No files in folder | `[错误] 文件夹中无匹配文件` | User creates .txt file |
| All lines filtered by subject filter | `所有提示词均无人/动物/风景/角色描述` | User disables subject filter or adds person prompts |
| Empty file | `无有效行` | Add content to file |
| API URL without http:// | `API地址格式无效` | Add protocol prefix |
| AI returns empty content | `API返回内容为空` (retries 2x) | Check model response |
| Overly aggressive filtering | Legitimate person prompts excluded | Prepend "一位/一名" to prompt (explicit person marker bypasses signal check) |

## Parameter Defaults (User-Facing)

```python
"文件夹路径": ("STRING", {"default":""}),
"读取模式": (["随机抽取","顺序循环","洗牌遍历","权重随机"], {"default":"随机抽取"}),
"循环模式": (["无限循环","读完停止","历史不重复(50条)"], {"default":"无限循环"}),
"输出数量": ("INT", {"default":1, "min":1, "max":50}),
"启用主体过滤": ("BOOLEAN", {"default":True}),
"最大读取行数": ("INT", {"default":0, "min":0, "max":100000}),  # 0 = unlimited
```

## Version History

| Version | Date | Changes |
|---------|------|---------|
| V13.2 | Pre-2026-05 | Initial subject filter; English-only smart_filter; no thread safety |
| V15.0 | 2026-05-21 | Chinese smart_filter; thread safety; 500MB protection; URL validation; enhanced metadata |
| V15.1 | 2026-05-22 | 65+ FALSE_POSITIVE_COMPOUNDS (RedNote analysis); 3-tier subject scoring; real-data validation |
