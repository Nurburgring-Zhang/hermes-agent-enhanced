# Zero-Content Title-Only Scoring Pattern

## Problem

Some `cleaned_intelligence` entries have `ai_scored_at IS NULL` because they were collected as **title-only fragments** — the content field is empty (0 characters, not even whitespace). These are usually from:

| Source | Reason |
|--------|--------|
| `zhihu_browser` | Only captured the question title, no answer/content body |
| `bilibili` | Only captured video title |
| `douyin` | Only captured short video text |
| `36kr` | Rare — link-only or JS-rendered page that failed content extraction |

These entries fall through ALL existing scoring mechanisms:
- `ai_scoring_v2.py` — skips `content <= 50 chars`
- `ai_sixdim_scorer.py` — skips `content <= 100 chars`
- `hermes_ai_scoring.py --batch` — queries `content > 0` but the *existential crisis* is the entries have no meat for real AI understanding
- `real_ai_scorer.py` — skips `content <= 50 chars`

## Detection

```sql
SELECT COUNT(*) FROM cleaned_intelligence 
WHERE (ai_score_total IS NULL OR ai_score_total = 0 OR ai_scored_at IS NULL)
  AND (content IS NULL OR content = '' OR LENGTH(COALESCE(content,'')) = 0);
```

## Scoring Method: Pure Title-Based Rule Engine

When content is 0 characters, score using **only** (1) title text, (2) source platform, and (3) `published_at`. No content analysis is possible.

### Algorithm

```python
def rate_title_only(title, source, published_at):
    title_lower = title.lower() if title else ""
    
    # === scarcity (0-30) — based on source+title uniqueness ===
    scarcity = 5  # default
    
    # scarcity: source-based
    source_high = ["36kr", "hackernews", "infoq", "github", "ithome", "huxiu"]
    source_low  = ["bilibili", "douyin", "tieba"]
    if any(s in source.lower() for s in source_high):
        scarcity = 12
    elif any(s in source.lower() for s in source_low):
        scarcity = 3  # user-generated, low scarcity
    
    # scarcity: title-based boost
    if any(kw in title_lower for kw in ["独家", "首发", "leak", "爆料", "内部", "深度"]):
        scarcity = max(scarcity, 20)
    elif any(kw in title_lower for kw in ["分析", "研究", "报告", "解读"]):
        scarcity = max(scarcity, 15)
    
    # === impact (0-30) ===
    impact = 3
    impact_kw_high = ["变革", "革命", "改变", "颠覆", "里程碑", "重大", "战略",
                       "发布", "开源", "推出", "合作", "收购", "投资"]
    impact_kw_mid  = ["趋势", "发展", "影响", "升级", "创新", "增长"]
    
    high_hits = sum(1 for kw in impact_kw_high if kw in title_lower)
    mid_hits  = sum(1 for kw in impact_kw_mid if kw in title_lower)
    
    if high_hits >= 2: impact = 20
    elif high_hits == 1: impact = 12
    elif mid_hits >= 2: impact = 10
    elif mid_hits == 1: impact = 6
    
    # === tech_depth (0-20) — title-only, limited signal ===
    tech_depth = 3
    tech_kw = ["技术", "代码", "架构", "算法", "模型", "gpu", "芯片", "训练",
               "开源", "工具", "框架", "库", "api", "部署", "教程", "python",
               "rust", "kubernetes", "docker", "agent", "rag", "llm", "ai"]
    tech_hits = sum(1 for kw in tech_kw if kw in title_lower)
    if tech_hits >= 3: tech_depth = 15
    elif tech_hits >= 2: tech_depth = 10
    elif tech_hits == 1: tech_depth = 6

    # === timeliness (0-10) ===
    timeliness = 3
    if published_at:
        try:
            pub = datetime.strptime(published_at[:19], "%Y-%m-%d %H:%M:%S")
            diff = now - pub
            if diff < timedelta(hours=24): timeliness = 9
            elif diff < timedelta(days=2): timeliness = 7
            elif diff < timedelta(days=7): timeliness = 5
            elif diff < timedelta(days=30): timeliness = 3
            else: timeliness = 1  # > 1 month old
        except:
            timeliness = 3

    # === preference (0-10) — user interest match ===
    preference = 3
    pref_kw = ["ai", "llm", "大模型", "深度学习", "机器学习", "开源", "技术", 
               "代码", "芯片", "python", "rust", "kubernetes", "docker", "agent",
               "rag", "训练", "模型", "gpu", "程序", "软件", "架构", "安全",
               "华为", "英伟达", "比亚迪", "新能源", "智能", "机器人"]
    pref_hits = sum(1 for kw in pref_kw if kw in title_lower)
    preference = min(3 + pref_hits * 2, 10)

    # === credibility (0-10) ===
    credibility_map = {
        "36kr": 7, "hackernews": 8, "infoq": 8, "github": 9, "arxiv": 9,
        "weixin": 6, "zhihu": 5, "bilibili": 4, "douyin": 3, "toutiao": 4,
        "weibo": 4, "kuaishou": 3, "ithome": 8, "huxiu": 7
    }
    credibility = 4
    for key, val in credibility_map.items():
        if key in source.lower():
            credibility = val
            break
    
    total = min(scarcity + impact + tech_depth + timeliness + preference + credibility, 100)
    return total, scarcity, impact, tech_depth, timeliness, preference, credibility
```

### Real-World Run (2026-05-29)

Processed **7 zero-content entries** from `ai_scored_at IS NULL`:

| ID | Source | Title | Score | Note |
|----|--------|-------|:-----:|------|
| 803702 | bilibili | 菜市场内为啥不让剥蚕豆？ | 21 | 民生科普, 无技术词, bilibili低可信 |
| 803933 | zhihu | 全女Love Live! Only展流展事件 | 21 | 二次元圈层事件, 无商业/技术价值 |
| 803938 | zhihu | 父母骗女儿去戒网瘾学校 | 21 | 社会新闻, 中可信度(zhihu) |
| 803939 | zhihu | 最漂亮的女演员？ | 21 | 纯娱乐投票, 低价值 |
| 803940 | zhihu | 中央空调省电问题 | 21 | 消费科普, 非技术向 |
| 803952 | zhihu | 荷兰军舰到西沙群岛 | 21 | 地缘政治话题, 但纯标题无分析 |
| 803944 | 36kr | 海航与中旅合作推动海南消费升级 | 46 | 36kr高可信+合作/战略词加分 |

**36kr entry scored 46 vs all others at 21** — the source credibility bonus + "合作/战略" keyword hits made a significant difference in the rule engine.

## When to Use vs LLM Scoring

| Criteria | Rule-based (this doc) | Real AI (delegate_task) |
|----------|----------------------|------------------------|
| Content length | 0 characters (title only) | ≥ 50 characters |
| Speed | ~0.05s for 200 items | ~64s for 20 items |
| Accuracy | Medium — keyword limited | High — content understanding |
| Use case | Last-mile cleanup of zero-content tail | High-value data with real content |

**Rule**: If content is 0 chars, ALWAYS use rule-based scoring. LLM has nothing to understand.
