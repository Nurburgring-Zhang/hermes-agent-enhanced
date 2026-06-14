# 短内容条目评分模式 (content < 50 chars)

## 来源模式

这些条目因 `LENGTH(content) <= 50` 被 `ai_scoring_v2.py` 和 `real_ai_scorer.py` 跳过，需要在规则引擎/AI评分跑完后手动处理尾数。

### 1. 微博热点条目
**Content pattern**: `Label: Score:NNNNNN`
**来源**: `weibo` 平台，采集器只抓到了微博热点标签，没有正文
**处理策略**: 
- 仅凭标题判断价值，技术/行业相关给中低分(30-60)
- 明星八卦/娱乐向/电影类：15-25分
- 纯互动/活动贴：0-15分
- 加分项：标题含 华为/比亚迪/AI/芯片/模型/智能驾驶 等关键词

### 2. 百度热搜条目
**Content pattern**: `Baidu Hot Search`
**来源**: `baidu` 平台，只有热搜标题
**处理策略**:
- 按标题评估涨跌/趋势类内容：30-40分
- 仅仅是个热点标题没有下文：不高于40分

### 3. 微信公众号摘要
**Content pattern**: `来自微信公众号 [公众号名] 的文章`
**来源**: `sogou_wechat` 采集，只有搜狗搜索结果摘要
**处理策略**:
- 检查 `published_at`：如果 > 7天，给0分（过时垃圾）
- 如果标题明显是招募/放假/活动通知：0分
- 少数有价值公众号（36氪/虎嗅等）即使摘要短也尝试打低分(20-30)

### 4. B站视频/互动条目
**Content pattern**: `-` 或空
**来源**: `bilibili` / `photo_match`
**处理策略**:
- 摄影/互动活动类：0-15分
- 追查看url中的视频ID是否可解析

### 5. 今日头条条目
**Content pattern**: 标题和content几乎一样
**来源**: `toutiao`
**处理策略**:
- 标题和content重复，说明只采集到了标题
- 按标题判断：筛选出含技术/行业关键词的给中等分，纯娱乐/电影/社会给低分(15-25)

## 六维评分映射表（短内容版本）

| 维度 | 低质(0-10) | 中质(30-50) | 中高质(50-65) |
|------|-----------|------------|--------------|
| scarcity | 0-3 | 5-12 | 12-16 |
| impact | 0-5 | 8-15 | 12-18 |
| tech_depth | 0-3 | 4-8 | 8-12 |
| timeliness | 0-3(旧) / 3-5(近日) | 4-5 | 5-8 |
| preference | 0-3 | 4-8 | 7-10 |
| credibility | 0-4(微博) | 4-7(媒体) | 6-8(官方/华为系) |

## 执行流程

### 推荐方法（2026-05-29经验）：统一base评分法

相比逐个来源做pattern判断，**base=22 + 关键词/来源加分**的方式更简洁统一：

```python
base = 22.0
if content_len > 60: base += 4
elif content_len > 30: base += 2
elif content_len > 10: base += 1
if title_len > 30: base += 3
elif title_len > 15: base += 1

# 关键词加分（各来源统一处理）
impact_kws = ['发布','上市','融资','收购','重大','新','首',
              'ai','模型','芯片','开源','安全','漏洞','技术','科技']
hits = sum(1 for kw in impact_kws if kw in combined.lower())
base += hits * 1.5

# 来源质量分
quality_sources = {'ithome':4, 'huxiu':3, 'hackernews':2, 'github':4, 'arxiv':5}
```

完整脚本见 `references/unscored-items-handling.md`。

### 旧方法（按来源模式分类，仍可用但更复杂）

```bash
# 1. 先跑规则引擎清大部分
cd ~/.hermes && python3 scripts/ai_scoring_v2.py --batch 200

# 2. 再跑AI评分清有内容的
python3 scripts/hermes_ai_scoring.py --batch 200

# 3. 最后处理短内容尾数
python3 -c "
import sqlite3, json
from datetime import datetime

db = sqlite3.connect('intelligence.db')
now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

# 找出剩余未评分
rows = db.execute('''
    SELECT id, title, COALESCE(content,\"\"), source, published_at
    FROM cleaned_intelligence 
    WHERE ai_score_total IS NULL OR ai_score_total = 0 OR ai_score_total = \"\"
''').fetchall()

if not rows:
    print('库存已清空')
    exit(0)

for r in rows:
    item_id, title, content, source, pub_at = r
    # 根据source pattern和标题关键词判定
    has_tech = any(k in (title or '').lower() for k in ['ai','芯片','模型','华为','比亚迪','智能','开源','算法','nlp'])
    is_entertainment = any(k in (title or '').lower() for k in ['明星','电影','综艺','cos','摄影','宠物','美食'])
    is_old = pub_at and '2026-05-2' not in str(pub_at)[:9]  # 非最近一周
    
    if 'Label: Score:' in content:
        score = 54 if has_tech else (17 if is_entertainment else 36)
    elif 'Baidu Hot Search' in content:
        score = 36
    elif '来自微信公众号' in content:
        score = 0 if is_old else 20
    else:
        score = 27 if has_tech else 17
    
    reasoning = json.dumps({
        'scarcity_reason': '短内容，仅标题评分',
        'impact_reason': '短内容，仅标题评分',
        'tech_depth_reason': '短内容，仅标题评分',
        'timeliness_reason': '短内容，仅标题评分',
        'preference_reason': '短内容，仅标题评分',
        'credibility_reason': f'来源:{source}',
        'summary': '短内容条目手动评分'
    }, ensure_ascii=False)
    # 分配六维分数（总和=score）
    sc = min(16, max(0, score // 2))
    im = min(20, max(0, score - sc))
    td = max(0, min(12, score - sc - im))
    tl = min(8, score - sc - im - td)
    pr = min(10, score - sc - im - td - tl)
    cr = max(0, score - sc - im - td - tl - pr)
    
    db.execute('''UPDATE cleaned_intelligence SET
        ai_score_scarcity=?, ai_score_impact=?, ai_score_tech_depth=?,
        ai_score_timeliness=?, ai_score_preference=?, ai_score_credibility=?,
        ai_score_total=?, importance_score=?, ai_score_reasoning=?, ai_scored_at=?
        WHERE id=?''',
        (sc, im//2, im//2, tl, pr, cr, score, round(score/10,2), reasoning, now, item_id))
    print(f'ID={item_id}: {score}分')

db.commit()
db.close()
print('短内容评分完毕')
"
```

## 2026-05-29 实测数据

处理了9条短内容条目（content=1-26字符），最终分值：

| ID | 来源 | 标题 | 分值 | 判定依据 |
|----|------|------|:----:|----------|
| 801319 | weixin | 【NE时代】春节放假通知 | 0 | 过时通知(pub=2026-02-12) |
| 801321 | weixin | 招募令 \|欢迎加入电动星球! | 0 | 招募令(pub=2022-09-19) |
| 801351 | baidu | 暴涨后腰斩 二手手机回收价"巨震" | 36 | 热点行情(中等价值) |
| 801354 | weibo | 舒淇为小米YU7车主交付新车 | 20 | 明星+小米(娱乐向) |
| 801356 | weibo | 比亚迪为城市领航及智能泊车兜底 | 54 | 比亚迪+智能驾驶技术 |
| 801358 | weibo | 华为超新星手表今日开售 | 46 | 华为新品 |
| 801363 | bilibili | 评论区摄影大赛... | 11 | 用户互动活动 |
| 801364 | toutiao | 一部"虐恋PUA"女性爽片... | 19 | 电影票房(不相关领域) |
| 801366 | weibo | 猛士x华为乾崑全新猛士M817预售 | 61 | 华为合作+新车预售(高价值) |
