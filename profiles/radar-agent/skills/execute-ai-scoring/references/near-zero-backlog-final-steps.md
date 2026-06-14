# Near-Zero Backlog Final Steps — Tail-End Scoring Pattern

**適用場景**: cron要求「處理cleaned_intelligence未評分積壓」，但常規診斷顯示只有個位數條目待處理。

## 核心原則

當積壓已接近0但仍有最後幾條時，不要用批量腳本——逐條手動處理更快、更準確。

## 三步流程（2026-05-30實測，15270→15268條，100%覆蓋）

### Step 1: 全格式診斷

不要只查 `ai_score_total IS NULL`，舊格式/零分/幻影零分都會被漏掉：

```sql
-- 一次看全貌
SELECT 
  CASE 
    WHEN ai_score_total IS NULL OR ai_score_total = 0 THEN 'needs_scoring_or_zero'
    ELSE 'scored'
  END as bucket,
  CASE 
    WHEN ai_score_reasoning IS NULL OR ai_score_reasoning = '' THEN 'truly_unscored'
    WHEN ai_score_reasoning LIKE '%summary%' THEN 'new_json_format' 
    WHEN ai_score_reasoning LIKE '%規則評分%' OR (ai_score_reasoning LIKE '%規則%' AND ai_score_reasoning NOT LIKE '%summary%') THEN 'rule_only'
    ELSE 'other'
  END as fmt,
  COUNT(*) as cnt
FROM cleaned_intelligence
GROUP BY bucket, fmt ORDER BY cnt DESC;
```

如果 `needs_scoring_or_zero` > 0，繼續。

### Step 2: 逐條檢查未評分條目

```sql
SELECT id, ai_score_total, substr(ai_score_reasoning,1,80) as reasoning_preview,
       substr(title,1,80) as title, source, 
       LENGTH(COALESCE(content,'')) as content_len
FROM cleaned_intelligence
WHERE (ai_score_total IS NULL OR ai_score_total = 0)
ORDER BY cleaned_at DESC;
```

分類決策樹：

| 條件 | 判斷 | 操作 |
|------|------|------|
| content_len > 100 AND reasoning是規則評分 | 有內容的規則評分 | delegate_task做AI理解評分 |
| content_len > 100 AND reasoning IS NULL | 完全未評分 | delegate_task做AI理解評分 |
| content_len < 50 AND reasoning是規則評分 | 短內容但非垃圾 | 直接賦低分（基於title+source） |
| content_len < 50 AND content是純標籤（Label:* Score:*） | **微博熱點/空採集** | **存檔到archive_cleaned+刪除** |
| ai_score_total = 0 AND reasoning NOT NULL且含summary | **幻影零分** | 檢查六維分數列是否為空→補算total |
| ai_score_total = 0 AND reasoning NOT NULL且不含summary | 有推理但無總分 | 用reasoning中的分數重新計算total |

### Step 3: 處理每種類型

**A) 有內容的規則評分條目 → delegate_task**

```python
# 單條直接delegate_task評分（比real_ai_scorer.py更快）
# context中包含：標題、內容[:500]、來源、六維評分標準表
# 子代理輸出JSON → 直接UPDATE到資料庫
```

**B) 無內容微博熱點/空採集（content純標籤） → 存檔清理**

```sql
-- 先複製到archive_cleaned
INSERT INTO archive_cleaned SELECT *, 
  datetime('now') as archived_at,
  'low_quality_zero_score_no_content' as archive_reason,
  '' as compressed_data
FROM cleaned_intelligence WHERE id IN (814985, 814989);

-- 再從cleaned_intelligence刪除
DELETE FROM cleaned_intelligence WHERE id IN (814985, 814989);
```

**C) 幻影零分（有reasoning JSON但total=0） → 補算**

```python
# 解析reasoning JSON中的分數，重新計算total
import json
reasoning = json.loads(item['ai_score_reasoning'])
# 或者從六維分數列重建
total = sum([item['scarcity'], item['impact'], ...])
UPDATE cleaned_intelligence SET ai_score_total=? WHERE id=?
```

## 驗證完成

```sql
-- 最終完整性檢查
SELECT 
  SUM(CASE WHEN ai_score_total IS NULL OR ai_score_total = 0 THEN 1 ELSE 0 END) as zero_or_null,
  SUM(CASE WHEN ai_score_reasoning IS NULL OR ai_score_reasoning = '' THEN 1 ELSE 0 END) as no_reasoning,
  MAX(ai_scored_at) as last_scored_at,
  COUNT(*) as total
FROM cleaned_intelligence;
```

如果 `zero_or_null = 0` 且 `no_reasoning = 0`，積壓真正清零。

## 2026-05-30 實測數據

| 步驟 | 操作 | 條數 | 耗時 |
|------|------|:----:|:----:|
| 診斷 | 發現6條「未評分」 | - | <1s |
| 分類 | 3條真正AI評分（reasoning誤含「規則」但已有summary）→跳過 | 3 | - |
| delegate_task | 1條規則評分→真正AI評分（#806433 61→59分） | 1 | ~61s |
| 存檔清理 | 2條微博0分空內容→archive_cleaned+刪除 | 2 | <1s |
| 驗證 | 零積壓，15268條100%已評分 | ✓ | <1s |

## 陷阱

- **LIKE '%規則%' 偽陽性**: reasoning正文中的「規則更新」「規則指南」「規則說明」會被錯誤匹配。交叉驗證：`AND reasoning NOT LIKE '%summary%'`
- **ai_score_total=0 ≠ 未評分**: 可能是reasoning有值但total未填（幻影零分），需檢查 `reasoning NOT NULL AND total=0`
- **不要用批量腳本處理個位數**: `score_backlog_200.py` 查詢條件可能不覆蓋零分+有reasoning的條目，手動更可控
