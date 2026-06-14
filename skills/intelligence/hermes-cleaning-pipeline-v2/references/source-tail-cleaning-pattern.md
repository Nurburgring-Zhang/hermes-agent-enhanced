# 源跳过尾部清洗模式 — 应对单源噪声阻塞队列

## 场景

`unified_cleaning_pipeline.py` 按 `r.id ASC` 顺序处理 raw→cleaned。当某个源（如CSDN）产生大量空内容入门教程标题时：
1. 该源的765+条记录全部被 `is_noise()` 过滤 (`noise_filtered=200/批次`)
2. 但因为它们占据了查询队列头部，后续有内容的非CSDN记录（36kr/cnblogs/ithome等）永远排不到
3. 结果：`new_cleaned=0` 但 `remaining=800+`

## 诊断SQL

```sql
-- 1. 检查未清洗的源分布
SELECT r.source, COUNT(*) as cnt
FROM raw_intelligence r
LEFT JOIN cleaned_intelligence c ON c.raw_id = r.id
WHERE c.id IS NULL
GROUP BY r.source ORDER BY cnt DESC;

-- 2. 检查噪声源的数据质量
SELECT r.id, r.title, LENGTH(COALESCE(r.content,'')) as content_len
FROM raw_intelligence r
LEFT JOIN cleaned_intelligence c ON c.raw_id = r.id
WHERE c.id IS NULL AND r.source = 'csdn'
ORDER BY r.collected_at DESC LIMIT 20;
```

## 判断标准

如果满足以下条件，应该使用源跳过清洗：
- 单源占未清洗队列的 85%+
- 该源的数据内容长度 < 50 字符且都是入门科普标题
- 剩余非噪声源的记录有实质内容（`content > 50`）

## 完整清洗+评分脚本模板

```python
#!/usr/bin/env python3
"""定向清洗非噪声源 + 立即评分"""
import sqlite3, json, time
from datetime import datetime
from pathlib import Path

HERMES = Path("/home/administrator/.hermes")
DB_PATH = HERMES / "data/intelligence.db"

# ---------- 工具函数 ----------
def is_noise(item):
    title = str(item.get('title','') or '')
    content = str(item.get('content','') or '')
    full = content + title
    noise_patterns = [
        '热度值:', 'Label:新', '关键词搜索:', 
        '非常感谢@', '喜欢的话可以留下一个三连吗',
        'Click:0', 'Votes:0',
    ]
    for p in noise_patterns:
        if p in full: return True
    if len(title) < 6: return True
    if not content.strip() and len(title) < 20: return True
    if '关键词搜索' in full: return True
    return False

def matches_whitelist(item):
    text = (str(item.get('title','') or '') + ' ' + str(item.get('content','') or '')).lower()
    WHITELIST = [
        'ai','人工智能','大模型','llm','gpt','agent','机器学习','训练','模型','算法',
        'python','rust','golang','typescript','react','vue','docker','kubernetes',
        '芯片','gpu','cpu','nvidia','amd','intel','rtx',
        '特斯拉','比亚迪','电动汽车','自动驾驶','智能驾驶',
        '融资','收购','上市','IPO','618','京东','快充','花洒',
        '安全','漏洞','加密','军事','国防','无人机',
        '6g','wifi','蓝牙','卫星','航天',
    ]
    return any(kw in text for kw in WHITELIST)

def score_item(item):
    text = (str(item.get('title','') or '') + ' ' + str(item.get('content','') or '')[:500]).lower()
    scarcity = 25 if any(k in text for k in ['独家','首次','首发','首款','纪录']) else \
               18 if any(k in text for k in ['发布','推出','上线','宣布','成立']) else 5
    impact = 25 if any(k in text for k in ['行业','全球','纪录','纪录','亿']) else \
             20 if any(k in text for k in ['融资','收购','上市','IPO']) else \
             18 if any(k in text for k in ['合作','战略','联盟','成立']) else 5
    tech_depth = 18 if any(k in text for k in ['架构','算法','框架','源码','训练','推理','agent']) else \
                 10 if any(k in text for k in ['方法','方案','实践']) else 5
    timeliness = 5
    try:
        pub = datetime.fromisoformat(str(item.get('published_at','')).replace('Z','+00:00'))
        now = datetime.now(pub.tzinfo) if pub.tzinfo else datetime.now()
        hours = (now - pub).total_seconds() / 3600
        timeliness = 10 if hours <= 24 else 7 if hours <= 48 else 4 if hours <= 168 else 1
    except: pass
    pref = min(5 + sum(2 for kw in ['ai','人工智能','大模型','llm','gpt','agent','模型','芯片','算法','训练','自动驾驶','智能'] if kw in text), 10)
    src = str(item.get('source','')).lower()
    credibility = 6 if any(k in src for k in ['ithome','36kr','solidot']) else \
                  3 if any(k in src for k in ['weibo','zhihu','bilibili','douyin']) else 5
    total = min(round(scarcity + impact + tech_depth + timeliness + pref + credibility, 1), 100)
    return {'total': total, 'scarcity': scarcity, 'impact': impact,
            'tech_depth': tech_depth, 'timeliness': timeliness,
            'preference': pref, 'credibility': credibility}

# ---------- 执行 ----------
conn = sqlite3.connect(str(DB_PATH))
c = conn.cursor()

c.execute('''
    SELECT r.id, r.title, r.content, r.url, r.source, r.platform,
           r.author, r.author_id, r.category, r.tags, r.category_tags,
           r.hot_score, r.published_at, r.collected_at
    FROM raw_intelligence r
    LEFT JOIN cleaned_intelligence c ON c.raw_id = r.id
    WHERE c.id IS NULL AND r.source NOT IN ('csdn')
    ORDER BY r.collected_at DESC
''')
cols = [d[0] for d in c.description]
rows = c.fetchall()

noise, whitelisted, dup, cleaned = 0, 0, 0, 0
results = []

for row in rows:
    item = dict(zip(cols, row))
    if is_noise(item):
        noise += 1; continue
    title = str(item.get('title','')).strip()
    title_count = conn.execute("SELECT COUNT(*) FROM cleaned_intelligence WHERE title=?", (title[:500],)).fetchone()[0]
    if title_count > 0:
        dup += 1; continue
    if not matches_whitelist(item):
        whitelisted += 1; continue
    
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    conn.execute('''INSERT INTO cleaned_intelligence 
        (raw_id,title,content,url,source,platform,author,author_id,
         category,tags,importance_score,value_level,value_reasons,
         is_ai_related,language,chinese_ratio,is_processed,
         published_at,collected_at,cleaned_at,agent,
         personal_match_score,source_type)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
        (item['id'], title[:500], (item.get('content','') or '')[:2000],
         item.get('url',''), item.get('source',''), item.get('platform',''),
         item.get('author',''), item.get('author_id',''),
         item.get('category',''), '', 0.0, 1,
         f'定向清洗-{item.get(\"source\",\"?\")}', 0, 'zh', 1.0, 1,
         item.get('published_at',''), item.get('collected_at',''), now,
         'direct_clean_score', 0, item.get('source','')))
    new_id = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
    
    score = score_item(item)
    conn.execute('''UPDATE cleaned_intelligence SET
        ai_score_total=?, ai_score_scarcity=?, ai_score_impact=?,
        ai_score_tech_depth=?, ai_score_timeliness=?, ai_score_preference=?,
        ai_score_credibility=?, importance_score=?, ai_scored_at=?
        WHERE id=?''', (
            score['total'], score['scarcity'], score['impact'],
            score['tech_depth'], score['timeliness'], score['preference'],
            score['credibility'], score['total']/10.0, now, new_id))
    cleaned += 1
    results.append({'id': new_id, 'title': title[:50], 'source': item.get('source',''), 'score': score['total']})

conn.commit()
conn.close()

print(f"Total: {len(rows)} | Cleaned: {cleaned} | Noise: {noise} | Dup: {dup} | WL-filtered: {whitelisted}")
for r in results:
    print(f"  + {r['source']:8s} score={r['score']:3.0f} | {r['title']}")
```

## 2026-05-30 实测数据

| 指标 | 值 |
|------|-----|
| 未清洗总候选 | 814条（765 CSDN + 49 其他） |
| 跳过源 | CSDN（全部无内容入门教程标题，正确过滤） |
| 噪声过滤 | 30条（douyin热度标题/zhihu零内容/关键词搜索项） |
| 白名单过滤 | 2条（1条散文、1条游记） |
| 重复 | 3条（标题已存在于cleaned） |
| **新清洗+评分** | **14条**（36kr×6, cnblogs×4, ithome×2, toutiao×2） |
| 评分范围 | 23-48分（均值36.4） |
| 总耗时 | ~0.05秒 |

## 关键教训

1. **不要降低噪声阈值来清积压** — CSDN空标题是正确过滤对象，不是bug
2. **遇到单一源阻塞队列时，跳过该源做定向清洗** — 比跑 `engine/cleaning_engine.py`（会引入海量噪声）更干净
3. **定向清洗后必须立即评分** — 这些尾数据是实时采集的，时效性窗口有限
4. `c.lastrowid` 在INSERT后可能返回0 — 用 `last_insert_rowid()` 替代
5. 该模式适合 cron 定时任务：每次检查队列头部的源分布，如果单一噪声源占比>80%则自动跳过
