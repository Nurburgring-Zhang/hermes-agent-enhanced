# Parallel Sub-Batch Delegate-Task Scoring Recipe

> Proven in production 2026-05-29: 342+ items scanned and scored in ~37 min

## Step 0: Diagnose the True Backlog

```sql
-- Run this in intelligence.db, NOT cleaned_intelligence.db
SELECT 
  CASE 
    WHEN ai_score_reasoning IS NULL OR ai_score_reasoning = '' THEN 'truly_unscored'
    WHEN ai_score_reasoning LIKE '%AI评分%' THEN 'ai_scored'
    WHEN ai_score_reasoning LIKE '%规则%' THEN 'rule_only'
    WHEN ai_score_reasoning LIKE '%summary%' THEN 'with_summary'
    WHEN ai_score_reasoning LIKE '{%' THEN 'json_format'
    ELSE 'other_text'
  END as fmt,
  COUNT(*) as cnt
FROM cleaned_intelligence
GROUP BY fmt ORDER BY cnt DESC;
```

## Step 1: Export & Split Target Items

```python
# Query the format that needs upgrading
c.execute("""
  SELECT id, title, substr(COALESCE(content,''), 1, 250) as content,
         source, ai_score_total, platform
  FROM cleaned_intelligence
  WHERE <target_format_condition>  -- e.g. ai_score_reasoning LIKE '%规则%'
    AND LENGTH(COALESCE(content,'')) > 100
  ORDER BY ai_score_total DESC
""")

# Split into 20-item sub-batches
batches = [items[i:i+20] for i in range(0, len(items), 20)]
os.makedirs('scoring_batches/sub', exist_ok=True)
for i, batch in enumerate(batches):
    path = f'scoring_batches/sub/batch_{i+1}_of_{len(batches)}.json'
    json.dump(batch, open(path, 'w'), ensure_ascii=False, indent=2)
```

## Step 2: Launch Parallel Scoring (3 concurrent)

Each delegate_task receives:
- Scale table (see SKILL.md)
- User interest keywords
- File path to read
- Result save path
- DB write one-liner

## Step 3: DB Write After Each Batch

```python
python3 -c "
import sqlite3,json
conn=sqlite3.connect('/home/administrator/.hermes/data/intelligence.db')
scores=json.load(open('RESULT_FILE.json'))
from datetime import datetime
now=datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
saved=0
for s in scores:
    total=s['scarcity']+s['impact']+s['tech_depth']+s['timeliness']+s['preference']+s['credibility']
    total=min(total,100)
    reasoning=json.dumps({k:s.get(k,'') for k in ['scarcity_reason','impact_reason','tech_depth_reason','timeliness_reason','preference_reason','credibility_reason','summary']},ensure_ascii=False)
    conn.execute('UPDATE cleaned_intelligence SET ai_score_scarcity=?,ai_score_impact=?,ai_score_tech_depth=?,ai_score_timeliness=?,ai_score_preference=?,ai_score_credibility=?,ai_score_total=?,importance_score=?,ai_score_reasoning=?,ai_scored_at=? WHERE id=?',(s['scarcity'],s['impact'],s['tech_depth'],s['timeliness'],s['preference'],s['credibility'],total,round(total/10,2),reasoning,now,s['id']))
    saved+=1
conn.commit();conn.close()
print(f'DONE:{saved}')
"
```

## Step 4: Verify

```sql
SELECT 
  CASE 
    WHEN ai_score_reasoning LIKE '%summary%' THEN 'with_summary'
    WHEN ai_score_reasoning LIKE '%AI评分%' THEN 'ai_scored' 
    ELSE 'still_other'
  END as fmt,
  COUNT(*) as cnt
FROM cleaned_intelligence
GROUP BY fmt ORDER BY cnt DESC;
```

## Expected Throughput

- 3×20 parallel batches: ~55s for 60 items (1.09 items/s)
- Full 200-item pass: ~335s
- Remaining 162 low-value items: ~280s
