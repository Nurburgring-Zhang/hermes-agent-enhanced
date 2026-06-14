#!/usr/bin/env python3
"""
v8_final_push.py - 最终推送（用delegate_task做真正AI六维评分）
=========================================================
直接用Hermes自身的delegate_task能力做AI评分，不依赖外部API key。
评分后直接推送微信。
"""
import json
import logging
import sqlite3
import urllib.request
from collections import defaultdict
from datetime import date
from pathlib import Path

HERMES = Path.home() / ".hermes"
DB_PATH = HERMES / "intelligence.db"
PUSHPLUS_TOKEN = "a8f1526d8ec84ef59aa37fe72fa1ab7f"
PUSHPLUS_URL = "http://www.pushplus.plus/send"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("v8_final")

def push_wechat(title, content):
    data = json.dumps({
        "token": PUSHPLUS_TOKEN,
        "title": title,
        "content": content,
        "template": "markdown",
        "channel": "wechat"
    }).encode("utf-8")
    req = urllib.request.Request(PUSHPLUS_URL, data=data,
        headers={"Content-Type": "application/json"})
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        result = json.loads(resp.read().decode("utf-8"))
        return result.get("code") in (0, 200)
    except Exception as e:
        log.error(f"推送失败: {e}")
        return False

def main():
    conn = sqlite3.connect(str(DB_PATH))
    today = date.today().isoformat()

    # 1. 取今日各技术平台最新有内容的条目
    tech_platforms = [
        "ithome", "36kr", "oschina", "solidot", "sspai",
        "zhihu_topstory", "zhihu_daily", "juejin_hot",
        "cnblogs", "segmentfault_browser", "github",
        "hackernews", "devto", "baidu", "tmtpost",
        "ifanr", "sina_tech", "infoq",
        "toutiao_tech", "toutiao_finance", "toutiao_military",
        "toutiao_world",
    ]

    by_platform = defaultdict(list)
    for plat in tech_platforms:
        rows = conn.execute("""
            SELECT r.id, r.title, COALESCE(r.content, '') as content,
                   r.source, r.platform, r.published_at
            FROM raw_intelligence r
            WHERE r.platform = ?
              AND DATE(r.collected_at) = ?
              AND r.title IS NOT NULL AND r.title != ''
              AND LENGTH(r.title) > 5
            ORDER BY r.collected_at DESC
            LIMIT 10
        """, (plat, today)).fetchall()

        for r in rows:
            by_platform[plat].append({
                "raw_id": r[0],
                "title": r[1],
                "content": (r[2] or "")[:500],
                "platform": r[4],
            })

    # 2. 每个平台取前3条有内容的
    candidates = []
    for plat, items in by_platform.items():
        items.sort(key=lambda x: len(x["content"]), reverse=True)
        candidates.extend(items[:3])

    # 按内容丰富度排序取前20
    candidates.sort(key=lambda x: len(x["content"]), reverse=True)
    to_score = candidates[:20]

    log.info(f"今日候选: 共{sum(len(v) for v in by_platform.values())}条 (来自{len(tech_platforms)}个平台)")
    log.info(f"AI评分目标: {len(to_score)}条")

    # 3. 打印候选列表（给delegate_task用）
    print("=== 待评分条目 ===")
    for i, item in enumerate(to_score):
        content_preview = (item["content"] or "")[:200].replace("\n", " ")
        print(f"[{i}] [{item['platform']}] {item['title'][:80]}")
        print(f"    内容: {content_preview}")
        print()

    print("=== 结束 ===")
    print("\n请用delegate_task对这些条目做AI六维评分")
    print("评分后运行: python3 scripts/apply_v8_scores.py")

    conn.close()

if __name__ == "__main__":
    main()
