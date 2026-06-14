---
name: library-prompt-composition
description: "Compose high-quality text-to-image prompts by combining multiple dimension libraries. Enforces logical consistency via 55-rule conflict detection engine + mutex matrix + dimension governance. Covers 500-item word-by-word audit methodology."
trigger: "User asks to generate structured prompts from existing dimension libraries, or to build/compose prompts using a multi-dimensional template system. User asks to audit or QC existing prompt batches. User reports contradictory, illogical, or nonsensical prompt output. User asks about dimension library governance or classification."
---

# Library-Driven Prompt Composition + Mass Production QC

## Overview

## 触发条件
- 用户提及此功能相关关键词时
- 遇到此领域的标准问题时
- 需要执行该领域的标准操作时


Master skill for the 10万-prompt mass production pipeline. Built from **500 prompts × word-by-word audit** across 5 batches. Covers:

1. Composing prompts from 17 dimension libraries
2. **55-rule conflict detection engine** (from 500-item audit)
3. **Dimension governance** (B01/A02/A04/D01/D02/A05 annotation and filtering)
4. **Mutex matrix** (pre-composition dimension pair checking)
5. **6-layer defense architecture**
6. **Batch QC at scale** (抽检100条/10000条)
7. **Dimension error mining** methodology

## Core Workflow

### Phase 1: Library Preparation + Governance

**17 dimension libraries** under `维度库_api_v7/` (or governed version `维度库_api_v7_governed/`).

Governance applied to 7 key dimensions:

| Dimension | Classification | Purpose |
|-----------|---------------|---------|
| B01_场景环境 | indoor_only / outdoor_only / mixed | mixed删除,碎片(<10字)删除 |
| A02_发型 | NATURAL / UNNATURAL | UNNATURAL在A01为亚裔时丢弃 |
| A04_表情眼神 | NATURAL / UNNATURAL | UNNATURAL在A01为亚裔时丢弃 |
| D01_服装款式 | MALE_ONLY / FEMALE_ONLY / UNISEX | A01男性→只取MALE+UNISEX |
| D02_配饰鞋帽 | MALE_ONLY / FEMALE_ONLY / UNISEX | 同上 |
| A05_姿势 | STAND / SIT / LIE / KNEEL / BEND / MIXED | MIXED拆分,同一prompt只取1个姿势类 |
| A01_年龄性别 | MALE / FEMALE / CHILD / BABY / NUDE | 用于组合时做性别/年龄匹配 |

Governance script: `_dimension_governance.py` (output in `维度库_api_v7_governed/`)

### Phase 2: Composition Engine (gen_one)

**Dimension Mutex Matrix (pre-composition check):**

| Dim A | Dim B mutex rule |
|-------|-----------------|
| A01亚裔 | A02≠金发/铂金/亚麻/银白/紫/绿/蓝/粉/红/灰/挑染 |
| A01亚裔 | A04≠蓝眼/绿眼/碧眼/紫眼/灰眼/金眼/红眼/银眼 |
| A01男性 | D01≠裙子/蕾丝/文胸/内衣(女)/丝袜/高跟鞋/比基尼 |
| A01男性 | D02≠头纱/面纱/珍珠发夹/耳环(女) |
| A01幼儿 | D01≠比基尼/性感/蕾丝/丁字裤/高跟鞋 |
| A01婴儿 | A05≠瑜伽/下犬式/站/走(成人化姿势) |
| A05站姿 | 同时出现躺/坐/跪/趴=矛盾 |
| B01室内 | 另一B01片段含户外元素=矛盾 |
| B01户外 | 含床/沙发/浴缸/马桶/灶台=矛盾 |
| C02自然光 | C02=人工光/影棚光=矛盾 |
| D05白天 | D05=夜晚/深夜=矛盾 |
| D06欢快 | D06=忧郁/悲伤=矛盾 |

**Composition rules:**
- ✅ A01年龄性别 → sample once
- ✅ A01+A02: 亚裔发色强制过滤 (NATURAL only for Asian)
- ✅ A01+A04: 亚裔瞳色强制过滤 (NATURAL only for Asian)
- ✅ A01+D01: 男性服装强制过滤 (MALE_ONLY + UNISEX)
- **⛔️ B01: 只取1个场景片段 (NEVER 2)**
- **⛔️ B02: 只取1个活动行为**
- **⛔️ D01: 只取1个服装款式 (非裸体时)**
- ✅ C01: 只取1个风格
- ✅ C02: 光照与场景匹配 (室内→灯/窗/柔光, 户外→自然光/阳光/黄昏)
- ✅ 其余维度: 各取1个

### Phase 3: API Call

```python
model = "deepseek-v4-flash"
headers = {"Content-Type": "application/json", "Authorization": f"Bearer {DK}"}
payload = {
    "model": "deepseek-v4-flash",
    "messages": [system_prompt, user_prompt],
    "thinking": {"type": "disabled"},
    "stream": False,
    "temperature": 0.88,
    "max_tokens": 2500
}
# 5 retry attempts on failure
```

### Phase 4: Post-API Defense (6 layers)

**Layer 1 — gen_one()前置过滤 (pre-API fragment matching):**
4 pre-filters: Asian+hair, Asian+eye, male+clothing (50+ keywords), B01 single-scene

**Layer 2 — 55-rule post-API conflict regex:**
See `CONFLICT_PATTERNS_V9` rules 1~55:
- **1~17**: original rules (stand+water, lie+stand, sit+soak, double-arm+single-hand, closed-eye+see, bed+stand, bedroom+outdoor, livingroom+bath, outdoor+furniture, indoor+outdoor, Asian+gold-hair, Asian+blue-eye, male+dress, sun+cloud, outdoor+kitchen, nude+cover)
- **18~25**: first extension (style truncation, adult+baby-items, latex+everyday, hair-length-conflict, hair-color-conflict, human+nonhuman, male+chest, scene-group)
- **26~41**: second extension from 400-item audit (human+nonhuman expanded, baby+adultification, double-shoes, gore/violence, Asian+unnatural-hair expanded, Asian+unnatural-eye expanded, male+female-clothing expanded, scene+clothing mismatch, outdoor+furniture expanded, floor-type conflict, style-format anomaly, indoor-style+outdoor-content, animal anthropomorphism, child+sexualization, outdoor+indoor-floor)
- **42~55**: third extension from 5th-batch 100-item audit (**NEW** 2026-05-26):
  - #42: 风格开篇2字截断 (标风/度风/格风/对风/术风/影风/纹风/染风/密风/和风/亚风/间风/主风/焦风/实风/产风/郁风/氛风/然风/理风/深风/夜风/远风, plus 50+ color/element characters)
  - #43: 男+女装通用 (比基尼底裤/婚纱/蕾丝内衣/珍珠发夹/文胸/胸罩/吊带袜/高跟鞋/连衣裙/及膝裙/百褶裙/蕾丝裙/纱裙/蓬蓬裙/包臀裙/鱼尾裙/抹胸裙)
  - #44: 亚裔+非天然发色2 (银白/银发/渐变/虎斑/挑染/彩虹/荧光/奶奶灰/雾霾紫/北极星绿/脏橘/樱花粉)
  - #45: 亚裔+非天然瞳色2 (绿色眼睛/垂直瞳孔/竖瞳/猫眼瞳/异色瞳/变色瞳/紫色眼睛/灰色眼睛/金色眼睛/红色眼睛/银色眼睛)
  - #46: 人类+非人特征2 (垂直瞳孔/竖瞳/虹膜+红色/紫色/金色/银色/发型+猫/虎斑/豹/斑马/熊/兔/狐/狼/胡须/猫耳/犬耳/兽耳)
  - #47: 伤病/昏迷检测 (昏迷/受伤/流血/伤口/面色苍白/嘴唇干裂/看似昏迷/晕倒/失去意识/重伤/病危/急救/伤痕/淤青/绷带/石膏/拐杖/轮椅)
  - #48: 裸露+服装补充 (裸露/袒露/暴露 + 穿着/身着/身穿+上衣/连衣裙/衬衫/外套等)
  - #49: 物理不可能(物体拟人) (天鹅/月亮/星星/太阳/云朵/海浪/石头/树木/花朵 + 载人/带脸/表情/微笑/哭泣/说话)
  - #50: 性别矛盾(她+他混用) (她...{50-200}他...)
  - #51: 风格开篇格式异常2 (摄影作品，风/照片，风/图片，风/画面，风/写真，风)
  - #52: 悬崖+室内家具 (悬崖/峭壁/山峰/山顶/山脊/陡坡 + 床/沙发/茶几/衣柜/书桌/餐桌/淋浴/浴缸/床头柜/梳妆台)
  - #53: 洞穴+室内家具 (洞穴/山洞/岩洞/溶洞/石窟 + 床/沙发/餐桌/茶几/衣柜/书桌/台灯/落地灯/梳妆台/床头柜)
  - #54: 街道+床上用品 (街道/马路/人行道/马路中央/十字路口/公路/高速公路 + 床/床单/枕头/被子/床垫/毛毯/铺盖)
  - #55: 烹饪+卧室 (火锅/烤肉/铁板烧/灶台/炉灶/炒锅/煎锅/烤箱/蒸锅 + 床/沙发/枕头/被子/卧室/床头/床单)

**Layer 3 — Style preamble integrity:**
- Check "风"前 ≥2 chars (if 0-1 → discard via rule #18)
- Check 2-char truncation (标风/度风/格风 etc → discard via rule #42)
- Check format anomaly (摄影作品，风 → discard via rule #51)
- If none of above but no style in first 80 chars → replace with complete style name

**Layer 4 — Multi-scene coexistence (16 scene types):**
Detect 3+ incompatible scene groups → abort. Groups:
- 卧室, 厨房, 浴室, 户外自然, 教室, 餐厅, 车内, 交通工具, 摄影棚, 医疗场所, 办公室, 城市街道, 阳台, 洞穴, 悬崖, 水边

**Layer 5 — People count consistency + gender consistency:**
- "一人" + "二人" → abort
- "她" + "他" within 200 chars → abort (rule #50)

**Layer 6 — API system prompt (embedded in AI instruction):**
Must include all prohibitions in SYSTEM_PROMPT.

### Phase 5: Batch QC (qc_two)

For every 10,000 prompts:
1. Random sample 100
2. Run full qc_two:
   - 55-rule engine
   - scene_groups ≥3 detection (16 groups)
   - Length check (400-1000 CN chars)
   - Style opening check (first 80 chars)
   - Simile/tech word check
   - Three-hand detection
   - Clothing stacking (≥3 TOP_KW)
   - Nude+clothing
   - Sentiment conflict (D06)
3. If pass rate < 90% → flag alert to _qc_alerts_v9.txt
4. Write qc report to _qc_report_part*.txt

## Dimension Governance Script

File: `大生产/代码/_dimension_governance.py`

Governance results (2026-05-26):

| Dimension | Raw | After Governance | Key Action |
|-----------|:---:|:----------------:|------------|
| B01_场景环境 | 449,266 | 287,204 | 碎片删除162K + mixed分类 |
| A02_发型 | 52,576 | 28,743 NATURAL | 非天然5,378移入UNNATURAL |
| A04_表情眼神 | 36,192 | 20,728 NATURAL | 非天然1,539移入UNNATURAL |
| D01_服装款式 | 88,673 | 65,106 | 性别标注M/F/U |
| D02_配饰鞋帽 | 55,051 | 44,815 | 性别标注M/F/U |
| A05_姿势 | 128,596 | 7-class classified | mixed 2,602需拆分 |
| A01_年龄性别 | 57,282 | 全标注 | M/F/CHILD/BABY/NUDE |

## 500-Item Audit Results Summary

| Batch | Pass+Warn | Efficiency | Key Change |
|:-----:|:---------:|:----------:|------------|
| Batch 1 | 36/100 | 36% | Baseline |
| Batch 2 | 45/100 | 45% | First correction |
| Batch 3 | 62/100 | 62% | 17 rules + qc_two |
| Batch 4 | 60/100 | 60% | +9 rules to 26 |
| Batch 5 | 53/100 | 53% | +14 rules to 55, stricter |
| **500 total** | **256/500** | **51.2%** | **88 problems → 87 covered (99%)** |

## Error Taxonomy (6 Dimensions)

| Dimension | Issues Found | % of Total | Coverage |
|-----------|:-----------:|:----------:|:--------:|
| **Ⅰ 维度组合冲突** | ~65 | 74% | 100% |
| **Ⅱ API扩写失控** | ~8 | 9% | 95% |
| **Ⅲ 风格开篇异常** | ~7 | 8% | 100% |
| **Ⅳ 后处理漏检** | ~4 | 5% | 100% |
| **Ⅴ 维度库数据缺陷** | ~3 | 3% | 100% (via governance) |
| **Ⅵ API输出截断** | ~1 | 1% | 未完全覆盖 |

## Critical Pitfalls

### ⛔️ THE #1 LESSON: B01场景只取1个
从v8.1到v9的最大改进就是B01从2个片段→1个片段。两个不同来源的场景片段一定会矛盾。

### ⛔️ 维度组合冲突的六个维度
| 维度 | 占比 | 典型问题 |
|------|:----:|---------|
| **Ⅰ 维度组合冲突** | 74% | 场景矛盾、亚裔+非天然发色/瞳色、男+女装 |
| **Ⅱ API扩写失控** | 9% | 动物拟人、暴力、非人特征 |
| **Ⅲ 风格开篇异常** | 8% | 截断、格式错误 |
| **Ⅳ 后处理漏检** | 5% | 裸露+服装、性别矛盾 |
| **Ⅴ 维度库数据缺陷** | 3% | B01含混合场景、A02含非天然发色 |
| **Ⅵ API输出截断** | 1% | 末尾不完整 |

### ⛔️ 55条规则仍无法覆盖的
- API扩写的超现实内容, 维度库源数据缺陷 → 只能在qc_two抽检中拦截
- 任何规则引擎都无法穷举所有可能的场景组合矛盾 → 这是维度组合的固有限制

## User Preferences (格林主人)

| Rule | Enforcement |
|------|------------|
| No batch/loop-generated worker configs | Skill is defective |
| No Docker (native only) | Abort generation |
| No placeholder/sample code stubs | Complete implementation |
| Task begins with full-context audit | Skip = bug |
| Every tool call → checkpoint | Gear system enforces |
| Prompts: no title/number/section | Pure paragraph |
| Prompts: no simile words | Rule 6 in qc_two |
| Prompts: no tech words | Rule 6 in qc_two |
| Prompts: no digital measurements | System prompt |
| Prompts: 400-800 Chinese chars | qc_two checks |
| Subject has exactly TWO hands | Three-hand detection |
| Each dimension sampled ONCE per prompt | gen_one enforces |
| When nude → no clothing descriptions | Rule 17 + 48 |
| 删除前必须先备份 | Hard rule in memory |
| 任何QC必须逐字审核，不能靠抽样推断 | 500-item audit methodology |

## Reference Files

- `references/400-prompt-audit-summary.md` — Summary of 4 batches × 100 prompts word-by-word audit
- `references/2026-05-25-mass-production-audit.md` — First 100-sample deep audit
- `references/dimension-conflict-matrix.md` — Complete mutex matrix for 17 dimensions
- `references/500-prompt-final-audit.md` — 5th batch + merged 500-item final audit (88 problems, 99% coverage)
- `scripts/deep_qc.py` — Standalone advanced QC script with 55-rule engine
- `scripts/dimension_governance.py` — Full dimension library governance pipeline (7 dimensions annotated)
- `templates/v9_script.py` — Reference template for mass_production_v9.py structure

## 回滚方案
### 快速回滚
如果部署后发现问题：
1. 使用版本控制回退到上一个提交：`git revert HEAD`
2. 确认回滚后系统状态正常
3. 通知相关方变更已撤销

### 数据安全
- 所有修改前确认有备份
- 配置变更记录版本历史
