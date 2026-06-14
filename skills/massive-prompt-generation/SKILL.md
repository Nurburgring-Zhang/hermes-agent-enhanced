---
name: massive-prompt-generation
description: '高质量中文文生图提示词批量生产——从to_chi原始语料直接输出，按审美/艺术关键词过滤。不做维度拆解和碎片拼凑。'
category: intelligence
---

# Massive Prompt Generation 技能

### Absorbed Skills (consolidated)

| Former Skill | Absorbed As | Reference File |
|---|---|---|
| `api-batch-data-processing` | Historical reference — v8-v14 dimension library pipeline (replaced by v15) | `references/api-batch-data-processing-complete.md` |

The absorbed skill `api-batch-data-processing` documents the v8-v14 dimension-library extraction-and-recombination approach that the current v15 methodology (this skill) replaced. It is preserved as a historical reference covering: DeepSeek API batch extraction of 17-dimension libraries, combine_engine v10-v13 fragment recombination, physical conflict detection, scene consistency filters, and production concurrency patterns. **Do not use the dimension-library approach for new production runs** — v15 direct-to_chi is the current methodology.

## ★ 核心方法论（2026-05-30 最终方案 v15）

**不要用维度库拼凑。直接用to_chi原始语料 + 审美关键词过滤。**

所有v8-v13版本都在做同一件事：从碎片维度库里随机pick条目然后拼凑。无论加多少规则、过滤、模板，碎片拼碎片永远是碎片——因为维度库本身是从to_chi用正则暴力拆出来的句子片段，不是标签。

**根本解决方案：直接用to_chi原始文本。** 261个文件、52万行原始描述文本，本身就是完整、可读、有逻辑的prompt。每条to_chi原始文本平均200-400字，写的是"一位年轻亚裔女性，留着黑色长发，站在阳光明媚的卧室窗边，身穿白色衬衫…"——本身就是合格的prompt。

### v15引擎（当前最优，2026-05-30最终方案）

`大生产/代码/batch_produce_v15.py` — 在v14基础上增加了审美/艺术/时尚关键词过滤：

## v15最终版（2026-05-30）

**这一轮从v8迭代到v14，最终确认：不要用维度库，直接用原始语料。**

核心转折：
- v8-v13：维度库碎片拼凑，无论加多少规则/过滤/模板解决不了碎片问题
- v14（180°转向）：直接从to_chi原始语料选取，过滤+去重，零逻辑错误
- v15：在v14基础上增加审美关键词过滤，确保风格多样性和质量

### 百万级生产

`大生产/代码/batch_produce_million.py` 和 `batch_produce_million_v2.py` — 审美集→基础集→原始语料三级池，自动去重已产出

**实际产出：约51万条**（to_chi语料全部用完后的上限）

### PromptFactory 统一工具

`/mnt/d/Hermes/1000000提示词/prompt_factory.py` — 包装所有流程为可复用的单文件工具：

```bash
# 新机器首次使用
python3 prompt_factory.py --mode full --to-chi /path/to/to_chi/ --output ./output/ --target 50000

# 仅过滤后二次使用（更快）
python3 prompt_factory.py --mode produce --output ./output/ --target 100000

# 查看统计数据
python3 prompt_factory.py --mode stats
```

特点：
- 三级过滤：审美(S)/基础(A)/原始(B)，S优先→A→B自动降级
- 去重：自动查重已有产出，跨批次不重复
- 配置化：支持yaml配置文件覆盖所有参数
- 可移植：单文件，复制到任何机器直接运行

### 300+审美关键词体系

审美关键词分9类200+词，覆盖所有主流风格方向。详见`batch_produce_v15.py`中的AESTHETIC_KW列表。

### 可复用的参考资料

`高质量模板/完整维度拆解与组合规则体系_最终版.txt` 包含：
- 100个场景模板（**仅作风格参考和灵感来源**，不可自动执行）
- 108原子子维度定义
- 11条核心逻辑规则（三手禁令/裸体逻辑/一致性等，可作为质量checklist）
- 30种现代艺术风格定义
- 10种破圈逻辑

1. 加载全部to_chi文本（约52万条）
2. 基础过滤：去掉比喻词/多人词/非人物（约24万条可用）
3. **审美过滤**：只保留含审美/艺术/时尚/摄影/潮流等关键词的条目（约20万条）
4. 随机选取+前100字去重（避免跨批次重复）
5. 直接输出

**审美关键词覆盖：** 200+个，包括：
- 现代艺术风格（极简/波普/浮世绘/赛博朋克/蒸汽波/Y2K/废土等）
- 摄影艺术（电影感/胶片感/黄金时刻/高调/低调等）
- 时尚审美（老钱风/静奢风/美拉德/多巴胺/芭蕾核等）
- 场景丰富（画廊/美术馆/天台/庭院/花田/古堡/教堂等）
- 情感氛围（治愈/诗意/颓废/慵懒/冷艳/空灵等）
- 服饰细节（蕾丝/缎面/珍珠/链条/泡泡袖/一字肩等）
- 美学风格（ins风/韩系/奶油风/工业风等）

**特征：**
- ✅ 无碎片（原始文本是完整段落）
- ✅ 无性别断裂（原始文本自带一致性别）
- ✅ 无逻辑错误（原始文本是人类写的）
- ✅ 无三只手/重复肢体（原始文本自洽）
- ✅ 无场景矛盾（原始文本在单一场景中）
- ✅ 字数200-560字，avg 280
- ✅ 200+审美关键词过滤，质量更高
- ✅ 每条含艺术/时尚/潮流的描述
- ✅ 30条手工验证全部合格（100%）
- ✅ 可保留成人内容（不过滤性描写）

### 参考文档

`高质量模板/完整维度拆解与组合规则体系_最终版.txt` 是风格/审美方向的**参考文档**，包含：
- 100个场景模板（可作为风格灵感和质量标准）
- 108个原子子维度定义
- 11条核心规则（三手禁令/裸体逻辑/一致性等）
- 30种现代艺术风格
- 10种破圈逻辑

**注意：** 这个文档不能直接用于自动执行（其中的示例是500字人工写的完整段落），但其中的风格定义、规则和审美方向可以作为筛选标准和质量checklist。

## 生产流程

```bash
# 小规模试产（审美过滤版）
cd /mnt/d/Hermes/1000000提示词/高质量模板/维度库
python3 combine_engine_v15.py  # 输出100条到试生产100条_v15.txt

# 批量生产
cd /mnt/d/Hermes/1000000提示词/大生产/代码
python3 batch_produce_v15.py  # 10000条，审美过滤
python3 batch_produce_million.py  # 100万条，审美过滤+基础补足

# 去重已存在的所有产出（百万批次脚本会自动处理）
```

## 产出目录

```
/mnt/d/Hermes/1000000提示词/大生产/
├── v14_batch/           ← v14直出版（50条×基础过滤）
│   └── v14_batch_*.txt
├── v15_batch/           ← v15审美过滤版
│   └── v15_batch_*.txt  (10个文件，共10万条)
└── million_batch/       ← 百万批量版（20个文件×5万条/文件）
    └── million_batch_*.txt
```

## 过滤规则

```python
# ===== 基础过滤 =====
MULTI = {'两位','两名','三位','三名','四人','情侣'}
PRODUCT = {'产品摄影','美食摄影','风景','景观','建筑摄影','静物摄影'}
# 必须含人物关键词（前80字）
has_person = any(w in text[:80] for w in ['女性','男性','女子','男子','女人',...
    '男人','女孩','男孩','少女','少年','裸体'])

# ===== 审美过滤（200+关键词，参考batch_produce_v15.py中的AESTHETIC_KW）=====
# 含任意一个即保留
any_kw_in_text(kw for kw in AESTHETIC_KW)
```

## 文件索引

| 文件 | 路径 | 说明 |
|------|------|------|
| to_chi原始语料 | `/mnt/d/ComfyUI/提示词/to_chi/` | 261个文件，52万条 |
| 完整规则文档 | `高质量模板/完整维度拆解与组合规则体系_最终版.txt` | 100个模板/108子维度/30风格/11规则（**风格参考，不可自动执行**） |
| v15脚本 | `大生产/代码/batch_produce_v15.py` | 审美过滤，10000条/批 |
| 百万脚本 | `大生产/代码/batch_produce_million.py` | 100万条，自动去重，50000条/文件 |
| v14参考 | `references/v14-raw-corpus-method.md` | v14直出法详细说明 |
| v15产出 | `大生产/v15_batch/` | 10万条审美过滤产出 |
| v14产出 | `大生产/v14_batch/v14_batch_1780071590.txt` | 5万条基础过滤产出 |
| 产出索引 | `references/production-outputs-index.md` | 全部产出文件清单 |

## ⚠️ 重要：不要走老路

以下方案已被证明无效，不要再用：
- **v8-v13: 维度库碎片拼凑** → 碎片/性别断裂/逻辑错误无法消除
- **combine_engine_v10_1/v12/v13** → 无论加多少规则过滤模板，碎片拼碎片永远是碎片
- **维度库_final_build_v3/ 和 _v4_label/ 和 _v5_tag/** → 不要用这些建库脚本

**核心原因：** 维度库条目本身就是从to_chi用正则提取的完整句子片段（"女性留着深色长发并带有蓝色挑染"），不是标签（"深色长发带蓝色挑染"）。任何用正则从完整句子里提纯标签的方法都有漏网之鱼。建库层修复需要NLP/LLM级别的理解，正则不可行。

**v15才是正确答案。审美关键词过滤确保风格多样性，原始文本确保完整性。**
