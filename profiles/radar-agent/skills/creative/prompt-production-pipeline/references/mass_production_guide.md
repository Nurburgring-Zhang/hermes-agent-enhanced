# Mass Prompt Generation from Dimension Libraries

## Overview
Generate 100K+ high-quality AIGC prompts by randomly sampling from pre-built dimension libraries (V7_api_v7, ~2M entries) and combining fragments via DeepSeek API.

## Architecture

```
V7 Dimension Libraries (~2M entries)
        ↓
Combinatorial Engine (gen_one: 12 mandatory + 3 optional dims, scene-consistent)
        ↓
DeepSeek API Assembly (fragments → flowing 500-800 word prose)
        ↓
Post-clean (三手裁剪/服装堆叠/比喻词/科技词/风格开篇补全/裸体检测)
        ↓
Physical Conflict Check (9 patterns → None → retry up to 5x)
        ↓
Output File (每行一条prompt，空行分隔)
```

## Key Quality Rules (v8.0 — Learned Through 4 Iterations)

### CRITICAL: Each Dimension Gets ONLY 1 Fragment
This is the single most important rule for preventing physical contradictions:

- **A05_姿势**: 1 fragment only (NOT 2 — was 2 in v1-v6, caused 三手)
- **A04_表情眼神**: 1 fragment only (NOT 2 — was 2 in v1-v6, caused 闭眼+看矛盾)
- **B02_活动行为**: 1 fragment only (NOT 2 — caused 三手 from multiple动作)
- **D01_服装款式**: 1 fragment only (NOT 2 — caused 服装堆叠 like 连衣裙+胸罩+丝袜)
- **ALL other dims**: 1 fragment each

### Scene Consistency (3-layer filter)
1. **Scene choice**: random.choice(["indoor","outdoor"]) — determined ONCE per prompt
2. **B01 filter**: `any(k in p for INDOOR_KW)` AND `not any(k in p for OUTDOOR_KW)` — ensures B01 fragments are pure scene type
3. **A05 filter**: When outdoor, reject A05 fragments containing INDOOR_KW ("床","沙发","枕头","浴缸")
4. **D05**: Only added to outdoor prompts
5. **C02**: Light-type filter — indoor→灯/窗/柔, outdoor→自然光/阳光/日/夕/晨
6. **System prompt**: "场景一致性：室内/户外必须全文一致"

### Post-Clean Operation Order (Critical! Order matters)
1. **Physical conflict check** — returns None if any of 9 patterns match → triggers retry
2. **Remove 比喻词** — 6 replacements (仿佛/犹如/就像/好似/宛如/如同). Multiple replace calls ensure clean.
3. **Remove 标题/序号** — `【】` `[]` `#` `第X条` `数字.` prefix removal
4. **Remove 科技词** — 量子/夸克/粒子/齿轮/全息/数据/光纤/纳米/芯片/电路/像素/矩阵
5. **三手裁剪** — sentence-level scan: track seen hand types (L/R/B). Skip sentence if:
   - Same sentence has >=2 hand types (双臂+右手 in same sentence)
   - Already seen >=2 hand types and current sentence introduces a NEW type (L+R then B)
6. **服装堆叠裁剪** — scan for TOP_KW (连衣裙/长袍/旗袍/外套/夹克/大衣/上衣/衬衫/T恤/毛衣/背心/吊带/比基尼). Keep first occurrence, delete sentences containing second occurrence of different top type.
7. **缺风格开篇自动补** — if first 80 chars don't contain "风，" or "风格" or "美学", prepend a random style from C01 dimension library
8. **Nude+clothing fix** — when "裸体/赤裸" appears near human pronoun, remove CLOTH_KW within 150 chars
9. **Cleanup** — collapse repeated punctuation/whitespace

### Physical Conflict Detection (9 Patterns, returns None)
| # | Pattern | Example |
|---|---------|---------|
| 1 | 站 + (浴缸\|浴池\|淋浴\|水中) | "站立在浴缸中" |
| 2 | 躺 + (站\|走\|行\|迈) | "躺在地上行走" |
| 3 | (坐\|蹲) + (浸\|泡) + (水\|浴缸) | "坐在浴缸中浸泡" |
| 4 | 双臂.{5,30}(右手\|左手) | "双臂交叉，右手握着东西" |
| 5 | 双手.{5,30}(右手\|左手) | "双手交叉，右手拿着" |
| 6 | 闭眼 + (注视\|凝视\|阅读\|盯着) | "紧闭双眼凝视远方" |
| 7 | (床上\|枕头上\|被子里) + (站立\|站着) | "床上站立" |
| 8 | 卧室 + (沙滩\|海滩\|户外) | "卧室里的沙滩" |
| 9 | 客厅 + (浴缸\|淋浴) | "客厅里的浴缸" |

### System Prompt Critical Lines
- 绝对禁止使用比喻词（5次强调）
- 绝对禁止三手描述。一个人只有两只手
- 场景一致性：室内/户外必须全文一致
- 服装合理性：一个人一次只穿一套服装
- 开篇必须是：「[风格名]风，」+特征描述
- 字数不得少于500字（3次强调）

### Retry Logic (Per-Prompt)
```
for attempt in range(5):
    call_api(segments, temperature=0.88, max_tokens=2500)
    cleaned = post_clean(raw)
    if cleaned is None: continue  # physical conflict
    cn = count_chinese(cleaned)
    if cn >= 300: break  # v8: relaxed from 500 to 300
```

## Non-Destructive Restart Rule (CRITICAL — Learned at Cost)

**NEVER have `os.remove(OUTPUT_FILE)` in a production script.** It destroys all data on restart.

**Always write in append mode** with progress tracking:
```python
# Check existing progress on startup
if os.path.exists(OUTPUT_FILE):
    with open(OUTPUT_FILE) as f:
        existing = sum(1 for l in f if l.strip()) // 2  # each prompt = 2 lines + blank
    print(f"Resuming from {existing} existing prompts")
    # Skip already-produced count
    total_produced = existing
```

This way, a crash only loses the in-flight batch (10-80 items), not everything before it.

### v8.0 Optimal Configuration
- **80 threads x 1 prompt/thread** (fully parallel — NOT batched)
- Each API call: ~700 input + ~1200 output = ~2300 tokens
- Throughput: ~160 prompts/minute (verified)
- 100K prompts cost: ~$49 at DeepSeek pricing (input $0.14/M, output $0.28/M)
- 100K prompts time: ~10 hours at full speed (auto-pause at 10 hours)

### Why NOT Batch Per Thread
Earlier versions used `5 threads x 10 prompts/thread(serial)` = 50 sec per batch = 60 prompts/min.
v8 uses `80 threads x 1 prompt/thread(parallel)` = ~12 sec per batch = ~160 prompts/min.
Same token cost per prompt. 2.6x faster due to full parallelism.

### Token Usage (Same Per Prompt Regardless of Serial/Parallel)
- system prompt: ~400 tokens
- user prompt (segments): ~300 tokens  
- API output: ~1200 tokens
- Total per prompt: ~1900 tokens

## v8.0 Quality Results (2,279 prompts sampled)

| Issue | Count | % | v7.6 | v8.0 |
|-------|-------|---|------|------|
| 字数不足(<300) | ~341* | 15% | 15% | 15% (ignored per user) |
| 缺风格开篇 | 77 | 3.4% | 3.4% | → 0% (auto-fix) |
| 比喻词'仿佛' | 46 | 2.0% | 2.0% | → 0% (post-clean kills them) |
| 服装堆叠 | 34 | 1.5% | 未检测 | → ~0% (post-clean kills duplicates) |
| 三手多手 | 16 | 0.7% | 0.7% | → ~0% (post-clean kills conflicts) |
| 场景矛盾 | 0 | 0% | 0% | 0% |
| **Physical conflicts** | ~11 | 0.5% | 未检测 | → 0% (retry on detection) |

## Known Remaining Issues

### 服装堆叠 still happens (low rate)
Root cause: D01 picks 1 fragment, but API sometimes adds additional clothing descriptions from other segments (B02动作 mentioning clothing, or A05姿势 describing what someone is wearing). 
Current fix: Post-clean TOP_KW scan removes second top-type. But if the second type appears in a different sentence structure, the regex misses it.
Potential improvement: More aggressive post-clean — remove ALL clothing keywords except the first one found.

## 逐字审核 Protocol（格林主人极端严格标准）

**这条prompt引发格林主人暴怒：**
> 休闲日常生活生活方式摄影风...一名长发凌乱的黑色短发女子坐在城市公园的婴儿车里...紫色毛绒内衣...红色乳胶带厚实而富有弹性，覆盖下腹部并延伸至大腿上部...

### 这条prompt的7个错误逐层分析

| 层 | 问题 | 根因 |
|:--:|------|------|
| 1 | "黑色短发"+"长发凌乱" | A02取了2个互斥发型，后处理没检测"长发"+"短发"共存 |
| 2 | 成年人在婴儿车 | B01取了"婴儿车"片段但没做年龄-用品合理性检查 |
| 3 | "休闲日常生活"+"乳胶带" | C01风格和D01服装没有风格匹配检查 |
| 4 | 紫色毛绒内衣+红色乳胶带 | D01取了2个服装片段，服装堆叠检测只查TOP_KW没查内衣类 |
| 5 | "头发湿润" | API在组合片段外自发添加了不合理描述 |
| 6 | 整条未被19条检测拦截 | 19条规则里没有"成人在婴儿车"和"乳胶+日常"这两条 |
| 7 | 未被qc_two拦截 | 逐字审核认为合理的内容AI自动检测认定为"通过" |

### 强制Protocol

批处理产出后，格林主人要求：

1. **随机抽样100条 → 逐字阅读 → 逐条标记问题**
2. **找出所有不合理组合**（不限于已有的19条模式）
3. **把新发现的模式加入检测规则**（不是只过滤这批，要永久加固）
4. **批量过滤产出的所有数据**
5. **格林主人亲自验收** — 他会逐字读你过滤后的数据

### 两轮200条逐字审核的关键发现

详见 `references/dimension_conflict_matrix.md`。核心数据：

- **47%的问题=场景矛盾**: 室内4+特征+户外4+特征共存，或3个场景组共存
- **7.5%的问题=男+女装**: 男子+蕾丝/胸罩/高跟鞋/裙子
- **7.5%的问题=风格开篇异常**: "线风""代风""度风"等截断
- **6.7%的问题=亚裔+非天然特征**: 亚裔+蓝眼/金发

### 后处理绝对命令

**下面的19种情况必须后处理拦截(pass None → 触发重试，最长重试5次):**

```
成人在婴儿车/摇篮 → 删除
乳胶/皮革束缚 + 日常/休闲/公园 → 删除  
长发 + 短发同一人 → 删除
休闲风格 + 乳胶服装 → 删除
亚裔 + 金发描述 → 删除
亚裔 + 蓝眼描述 → 删除
男子 + 任何裙装/蕾丝/内衣/丝袜 → 删除
站 + 床/浴缸/水中 → 删除
躺 + 站/行走 → 删除
闭眼 + 看/注视/凝视 → 删除
卧室 + 户外元素 → 删除
客厅 + 浴缸/淋浴 → 删除
户外 + 室内家具(床/浴缸/沙发) → 删除
室内 + 户外自然元素(森林/沙滩/海浪) → 删除
晴 + 阴/乌云/暴雨 → 删除
户外 + 厨房设施(铁板烧/灶台) → 删除
裸体 + 穿衣服/遮住 → 删除
风格开篇"风"前少于2字 → 修复(不删除，替换完整风格名)
"的"字密度>28% → 警告标记(不删除但记录)
```

## v9 File Locations
- Production script: `/mnt/d/Hermes/1000000提示词/大生产/代码/mass_production_v9.py`
- V7 library: `/mnt/d/Hermes/1000000提示词/高质量模板/维度库_api_v7/` (2,011,891 entries)
- Output dir: `/mnt/d/Hermes/1000000提示词/大生产/`
- Filtered (post-QC): `/mnt/d/Hermes/1000000提示词/大生产/_batch_qc_filtered/`
- QC scripts dir: `/mnt/d/Hermes/1000000提示词/大生产/代码/`
- Backup dir: `/mnt/d/Hermes/备份/`
