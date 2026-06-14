# V8 Post-Clean Pipeline — Mass Production Quality Assurance

## Context
From the 2026-05-25 session: After building V7 dimension libraries (~2M fragments across 17 dimensions), we deployed an 80-thread parallel prompt generation system that composes fragments from these libraries and calls DeepSeek API to produce complete 500-800 word prompts.

Early v7.5 runs had ~19.5% defect rate. V8 reduced this to ~2-3% through aggressive post-processing.

## The 8-Step Post-Clean Pipeline (EXACT ORDER MATTERS)

Each generated prompt passes through these steps in sequence:

### Step 1: Physical Conflict Detection
Before any text processing, check for physical impossibilities. Return `None` if found (triggers regeneration with different fragments).

```python
CONFLICT_PATTERNS = [
    (re.compile(r'站.{0,15}(浴缸|浴池|淋浴|水中|水池)'), "站+水中"),
    (re.compile(r'躺.{0,15}(站|走|行|迈)'), "躺+站"),
    (re.compile(r'(坐|蹲).{0,15}(浸|泡).{0,10}(水|浴缸|浴池)'), "坐+浸"),
    (re.compile(r'双臂.{5,30}(右手|左手)'), "双臂+单手"),
    (re.compile(r'双手.{5,30}(右手|左手)'), "双手+单手"),
    (re.compile(r'(闭.{0,4}眼|眼.{0,4}闭|紧闭).{0,20}(注视|凝视|阅读|看书|翻书|盯着|瞄准)'), "闭眼+看"),
    (re.compile(r'(床上|枕头上|被子里|床单上).{0,15}(站立|站着)'), "床+站"),
    (re.compile(r'卧室.{0,20}(沙滩|海浪|海滩|户外|草地)'), "卧室+户外"),
    (re.compile(r'客厅.{0,20}(浴缸|淋浴|浴池)'), "客厅+浴缸"),
]
```

### Step 2: 比喻词 Removal (Multiple Replace)
```
"仿佛","犹如","就像","好似","宛如","如同" → all replaced with ""
```
Use `.replace()` not regex — simpler and more reliable.

### Step 3: Title/Header Cleanup
Remove leading `【xxx】`, `[xxx]`, `#xxx`, `第N条`, `数字.` from each line.

### Step 4: Three-Hand (三手) Conflict Detection
**Logic:** Track which hand types (L/R/B) appear across sentences. A sentence is skipped if:
- Same sentence contains ≥2 different hand types (e.g., "双臂交叉于胸前，右手握着" → B + R)
- ≥2 types already seen across prior sentences and a new type appears (L + R seen, now B appears)

```python
seen = set()  # e.g., {'L', 'R'}
for s in sentences:
    cur = set()
    if "左手" in s: cur.add("L")
    if "右手" in s: cur.add("R")
    if "双手" in s or "双手" in s or "双臂" in s: cur.add("B")
    if cur:
        if len(cur) >= 2: continue       # same-sentence conflict
        if len(seen) >= 2 and not cur.issubset(seen): continue  # cross-sentence
        seen.update(cur)
```

### Step 5: Clothing Stacking (服装堆叠) Detection
Track first encountered TOP_KW. Delete sentences containing subsequent TOP_KW entries.

```python
TOP_KW = ["连衣裙","长袍","旗袍","外套","夹克","大衣","上衣","衬衫","T恤","毛衣","背心","吊带","比基尼"]
```

### Step 6: Auto-Prepend Style Opening
If first 80 chars lack `"风，"`, `"风,"`, `"风格"`, or `"美学"`, prepend a random style from the C01美学风格 library:

```python
if not any(k in text[:80] for k in ["风，","风,","风。","风格","美学"]):
    style = random.choice(dim_data.get("C01_美学风格", ["写实风格"]))
    text = f"{style}风，{text}"
```

### Step 7: Nude + Clothing Contradiction
When `"裸体"` or `"赤裸"` appears with human keywords nearby, delete clothing keywords within 100 characters.

### Step 8: Final Cleanup
```
- Multiple 句号 → single
- Multiple 逗号 → single  
- Multiple spaces → single
- Multiple newlines → single
```

## Non-Destructive Restart Rule
**CRITICAL: Never `os.remove(OUTPUT_FILE)` at the start of a production script.** If the script crashes mid-run, all data is lost. Instead:
- Write in append mode (`"a"`)
- Track progress by checking file line count at restart
- User will be extremely angry if data is lost to a restart

## Production Configuration (Final)
- Threads: 80 (DeepSeek paid API handles this easily — 500 req/min limit)
- Batch per thread: 1 item (maximize parallelism)
- Max retries: 5 per item (any attempt that hits ≥300 中文字符 is accepted)
- Temperature: 0.88
- Max tokens: 2500
- Auto-stop: 10 hours
- Output speed: ~126-165 prompts/min (~75K-99K in 10 hours)
