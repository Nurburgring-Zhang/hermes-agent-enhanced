#!/usr/bin/env python3
"""
lowscore_cleaner.py — Hermes 低分数据清理脚本
用法:
  python3 scripts/lowscore_cleaner.py [--dry-run] [--fast]

功能:
  1. 扫描 cleaned_intelligence 中 ai_score_total < 20（或=0）的数据
  2. 归档到 archive_cleaned 表（保留评分明细）
  3. 从 cleaned_intelligence 删除
  4. 清理 raw_intelligence 中3天以上未清洗的孤立数据
  5. VACUUM 回收空间
  6. 修补有分无时间戳的记录

--dry-run: 预览清理计划，不实际执行
--fast:    不执行 VACUUM
"""

import json
import os
import sqlite3
import sys
from datetime import datetime

DRY_RUN = "--dry-run" in sys.argv
FAST = "--fast" in sys.argv

# 阈值处理: --threshold 参数（默认20）
THRESHOLD = 20
if "--threshold" in sys.argv:
    idx = sys.argv.index("--threshold")
    if idx + 1 < len(sys.argv):
        try:
            THRESHOLD = int(sys.argv[idx + 1])
        except ValueError:
            print(f"[WARN] 无法解析阈值: {sys.argv[idx+1]}, 使用默认20")
# 兼容旧版: 如果传了--zero-only则只清理得分为0的
if "--zero-only" in sys.argv:
    THRESHOLD = 0


def main():
    db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "intelligence.db")
    if not os.path.exists(db_path):
        print(f"[ERROR] 数据库不存在: {db_path}")
        sys.exit(1)

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    print("低分数据清理 v1.0")
    print(f"数据库: {db_path}")
    print(f'模式: {"DRY RUN (预览)" if DRY_RUN else "实际执行"}')
    print("---")

    # ---- 1. 诊断 ----
    null_scores = cur.execute("SELECT COUNT(*) FROM cleaned_intelligence WHERE ai_score_total IS NULL").fetchone()[0]
    zero_scores = cur.execute("SELECT COUNT(*) FROM cleaned_intelligence WHERE ai_score_total <= ?", (THRESHOLD,)).fetchone()[0]
    partial_ts = cur.execute("SELECT COUNT(*) FROM cleaned_intelligence WHERE ai_score_total > 0 AND ai_scored_at IS NULL").fetchone()[0]
    total = cur.execute("SELECT COUNT(*) FROM cleaned_intelligence").fetchone()[0]

    print(f"cleaned_intelligence 总行数: {total}")
    print(f"  真正未评分 (total IS NULL):    {null_scores}")
    print(f"  低分 (total <= {THRESHOLD}):     {zero_scores}")
    print(f"  有分无时间戳:                  {partial_ts}")

    # 低分来源分布
    sources = cur.execute("""
        SELECT source, COUNT(*) as cnt FROM cleaned_intelligence 
        WHERE ai_score_total <= ? 
        GROUP BY source ORDER BY cnt DESC LIMIT 10
    """, (THRESHOLD,)).fetchall()
    if sources:
        print("\n低分来源TOP10:")
        for s, c in sources:
            print(f"  {s}: {c}条")

    # ---- 2. 清理低分数据 ----
    if zero_scores > 0:
        # 检查archive_cleaned表有哪些列
        archive_cols = [col[1] for col in cur.execute("PRAGMA table_info('archive_cleaned')").fetchall()]
        has_compressed = "compressed_data" in archive_cols

        items = cur.execute("""
            SELECT id, title, platform, source, url, collected_at, ai_score_total, ai_score_reasoning, ai_scored_at
            FROM cleaned_intelligence WHERE ai_score_total <= ? ORDER BY id
        """, (THRESHOLD,)).fetchall()
        print(f"\n[操作1] 归档+删除 {len(items)} 条低分数据")
        print(f'  archive_cleaned列: {len(archive_cols)}列, compressed_data列: {"存在" if has_compressed else "⚠️ 不存在，跳过压缩字段"}')

        if not DRY_RUN:
            archived_ok = 0
            archived_fail = 0
            for item in items:
                try:
                    if has_compressed:
                        compressed = json.dumps({
                            "title": item[1],
                            "platform": item[2],
                            "source": item[3],
                            "collected_at": item[5],
                            "score_total": item[6]
                        }, ensure_ascii=False)
                        cur.execute("""
                            INSERT INTO archive_cleaned 
                            (title, platform, source, archived_at, compressed_data, ai_score_total, ai_score_reasoning, ai_scored_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """, (item[1], item[2] or "", item[3] or "", now, compressed,
                              item[6] or 0, str(item[7] or "")[:500], str(item[8] or now)))
                    else:
                        # 无compressed_data列: 用完整字段插入
                        cur.execute("""
                            INSERT OR IGNORE INTO archive_cleaned 
                            (id, title, source, platform, url, ai_score_total, ai_score_reasoning, ai_scored_at, archived_at, archive_reason)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (item[0], item[1], item[3] or "", item[2] or "",
                              item[4] or "", item[6] or 0, str(item[7] or "")[:500],
                              str(item[8] or now), now, f"auto: ai_score_total<={THRESHOLD}"))
                    archived_ok += 1
                except Exception as e:
                    print(f"    ❌ 归档失败 id={item[0]}: {e}")
                    archived_fail += 1

            # 删除
            ids = [item[0] for item in items]
            for i in range(0, len(ids), 200):
                batch = ids[i:i+200]
                placeholders = ",".join(["?"] * len(batch))
                cur.execute(f"DELETE FROM cleaned_intelligence WHERE id IN ({placeholders})", batch)

            conn.commit()
            print(f"  ✅ 归档+删除完成 (成功{archived_ok}, 失败{archived_fail})")
    else:
        print("\n[操作1] 无需清理低分数据")

    # ---- 3. 修补时间戳 ----
    if partial_ts > 0:
        print(f"\n[操作2] 修补 {partial_ts} 条有分无时间戳记录")
        if not DRY_RUN:
            cur.execute("""
                UPDATE cleaned_intelligence 
                SET ai_scored_at = collected_at || ' 23:59:59'
                WHERE ai_score_total > 0 AND ai_scored_at IS NULL
            """)
            conn.commit()
            print("  ✅ 修补完成")
    else:
        print("\n[操作2] 无需修补时间戳")

    # ---- 4. VACUUM ----
    if not DRY_RUN and not FAST:
        print("\n[操作3] VACUUM 回收空间...")
        cur.execute("VACUUM")
        print("  ✅ VACUUM完成")

    # ---- 5. 清理孤立raw数据 ----
    print("\n[操作4] 扫描孤立raw数据...")
    orphaned = cur.execute("""
        SELECT COUNT(*) FROM raw_intelligence r 
        LEFT JOIN cleaned_intelligence c ON r.id = c.raw_id 
        WHERE c.raw_id IS NULL AND r.collected_at < datetime('now', '-3 day')
    """).fetchone()[0]
    print(f"  3天以上孤立raw数据: {orphaned}条")
    if orphaned > 0 and not DRY_RUN:
        cur.execute("""
            INSERT OR IGNORE INTO archive_raw (archived_at, compressed_summary)
            VALUES (?, 'auto-cleaned during lowscore cleanup')
        """, (now,))
        cur.execute("""
            DELETE FROM raw_intelligence WHERE id IN (
                SELECT r.id FROM raw_intelligence r 
                LEFT JOIN cleaned_intelligence c ON r.id = c.raw_id 
                WHERE c.raw_id IS NULL AND r.collected_at < datetime('now', '-3 day')
            )
        """)
        conn.commit()
        deleted = cur.rowcount
        print(f"  ✅ 删除了 {deleted} 条孤立raw数据")

    # ---- 6. 验证 ----
    if not DRY_RUN:
        conn.commit()
        print("\n=== 验证结果 ===")
        for check, sql in [
            ("真正未评分 (total IS NULL)", "SELECT COUNT(*) FROM cleaned_intelligence WHERE ai_score_total IS NULL"),
            ("低分残留 (total <= 0)", f"SELECT COUNT(*) FROM cleaned_intelligence WHERE ai_score_total <= {THRESHOLD}"),
            ("有分无时间戳", "SELECT COUNT(*) FROM cleaned_intelligence WHERE ai_score_total > 0 AND ai_scored_at IS NULL"),
            ("cleaned_intelligence 总行数", "SELECT COUNT(*) FROM cleaned_intelligence"),
            ("archive_cleaned 总行数", "SELECT COUNT(*) FROM archive_cleaned"),
        ]:
            r = cur.execute(sql).fetchone()[0]
            print(f"  {check}: {r}")

        old_size = os.path.getsize(db_path) // (1024 * 1024)
        print(f"  数据库大小: {old_size} MB")

    conn.close()
    print(f"\n[完成] {now}")


if __name__ == "__main__":
    main()
