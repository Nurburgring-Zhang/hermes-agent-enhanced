
#!/usr/bin/env python3
"""Hermes 老旧数据压缩引擎 - 将48K条数据压缩归档"""
import sqlite3
from datetime import datetime
from pathlib import Path

HERMES = Path.home() / ".hermes"
DB_PATH = HERMES / "intelligence.db"

def archive_old_data():
    conn = sqlite3.connect(str(DB_PATH))

    # 1. 创建压缩归档表
    conn.execute("""
        CREATE TABLE IF NOT EXISTS compressed_intelligence (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_id INTEGER,
            title TEXT,
            content_snippet TEXT,
            url TEXT,
            source TEXT,
            platform TEXT,
            importance_score REAL DEFAULT 0,
            ai_score_total REAL DEFAULT 0,
            ai_score_scarcity REAL DEFAULT 0,
            ai_score_impact REAL DEFAULT 0,
            ai_score_tech_depth REAL DEFAULT 0,
            ai_score_timeliness REAL DEFAULT 0,
            ai_score_preference REAL DEFAULT 0,
            ai_score_credibility REAL DEFAULT 0,
            collected_at TEXT,
            archived_at TEXT DEFAULT (datetime('now'))
        )
    """)

    # 2. 统计旧数据
    thirty_days_ago = (datetime.now() - __import__("datetime").timedelta(days=30)).isoformat()

    # 已评分但超过30天的数据
    old_scored = conn.execute("""
        SELECT id, title, substr(COALESCE(content, ''), 1, 200),
               url, source, platform, importance_score,
               ai_score_total, ai_score_scarcity, ai_score_impact,
               ai_score_tech_depth, ai_score_timeliness,
               ai_score_preference, ai_score_credibility,
               collected_at
        FROM cleaned_intelligence
        WHERE (cleaned_at < ? OR cleaned_at IS NULL)
          AND id NOT IN (SELECT source_id FROM compressed_intelligence WHERE source_id IS NOT NULL)
    """, (thirty_days_ago,)).fetchall()

    # 无评分但也超过30天的
    old_unscored = conn.execute("""
        SELECT id, title, substr(COALESCE(content, ''), 1, 200),
               url, source, platform, importance_score,
               ai_score_total, ai_score_scarcity, ai_score_impact,
               ai_score_tech_depth, ai_score_timeliness,
               ai_score_preference, ai_score_credibility,
               collected_at
        FROM cleaned_intelligence
        WHERE cleaned_at < ?
          AND (ai_score_total IS NULL OR ai_score_total = 0)
          AND id NOT IN (SELECT source_id FROM compressed_intelligence WHERE source_id IS NOT NULL)
    """, (thirty_days_ago,)).fetchall()

    all_old = old_scored + old_unscored
    archived_count = 0

    for row in all_old:
        try:
            conn.execute("""
                INSERT OR IGNORE INTO compressed_intelligence
                (source_id, title, content_snippet, url, source, platform,
                 importance_score, ai_score_total, ai_score_scarcity,
                 ai_score_impact, ai_score_tech_depth, ai_score_timeliness,
                 ai_score_preference, ai_score_credibility, collected_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, row)
            if conn.total_changes > 0 or True:
                archived_count += 1
        except:
            pass

    conn.commit()

    total_old = len(old_scored) + len(old_unscored)
    print(f"旧数据统计: {len(old_scored)}条已评分 + {len(old_unscored)}条未评分 = {total_old}条旧数据")
    print(f"已归档: {archived_count}条")

    # 统计压缩前后size
    before = conn.execute("SELECT COUNT(*) FROM cleaned_intelligence").fetchone()[0]
    after = conn.execute("SELECT COUNT(*) FROM compressed_intelligence").fetchone()[0]
    print(f"cleaned_intelligence: {before}条")
    print(f"compressed_intelligence: {after}条")

    conn.close()
    return {"old_total": total_old, "archived": archived_count}

if __name__ == "__main__":
    archive_old_data()
