#!/usr/bin/env python3
"""
今日头条增强采集器 - 多API端点+多关键词
解决头条采集量少问题(7→50+)
"""

import hashlib
import json
import random
import re
import sqlite3
import time
from datetime import datetime

HERMES_DIR = str(Path.home() / ".hermes")
DB_PATH = f"{HERMES_DIR}/intelligence.db"

KEYWORDS = [
    # AI/科技 (20个)
    "AI大模型", "ChatGPT", "AIGC", "LLM", "GPT-4", "Claude", "Gemini",
    "AI训练", "AI应用", "AI行业", "人工智能", "大模型", "深度学习", "神经网络",
    "OpenAI", "DeepSeek", "百度AI", "阿里通义", "字节AI", "腾讯混元", "华为盘古",
    # IT/手机 (15个)
    "iPhone", "华为手机", "小米手机", "OPPO", "vivo", "三星手机", "荣耀手机",
    "手机评测", "旗舰手机", "折叠屏", "骁龙8", "天玑9300", "麒麟芯片", "鸿蒙系统", "iOS",
    # 汽车 (15个)
    "特斯拉", "比亚迪", "小米汽车", "问界", "蔚来", "小鹏汽车", "理想汽车",
    "智驾", "自动驾驶", "新能源汽车", "电动车", "极氪", "腾势", "汽车评测", "车型对比",
    # 体育/格斗 (10个)
    "NBA", "CBA", "足球", "欧冠", "拳击", "UFC", "MMA", "格斗", "马拉松", "电竞",
    # 军事/国际 (10个)
    "军事", "战斗机", "航母", "俄乌", "中美", "国际局势", "台海", "南海", "防空", "军事装备",
    # 娱乐/社会 (10个)
    "电影", "热播剧", "明星", "网红", "旅游", "美食", "社会", "热点", "热搜", "民生",
    # 摄影/游戏 (10个)
    "摄影", "相机", "拍照", "游戏", "主机", "Steam", "Switch", "PlayStation", "Xbox", "手游",
    # 科技/其他 (10个)
    "量子计算", "芯片", "光刻机", "机器人", "无人机", "智能穿戴", "电脑", "笔记本", "显示器", "数码",
]

def fetch(url, headers=None, timeout=15, post_data=None):
    import urllib.request
    try:
        req = urllib.request.Request(url)
        req.add_header("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        if headers:
            for k, v in headers.items():
                req.add_header(k, v)
        if post_data:
            req.data = post_data.encode()
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="ignore")
    except:
        return None

def url_hash(url):
    return hashlib.sha256(url.encode()).hexdigest()[:32]

def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def detect_lang(title, content=""):
    cn = len(re.findall(r"[\u4e00-\u9fff]", (title or "") + (content or "")))
    en = len(re.findall(r"[a-zA-Z]", (title or "") + (content or "")))
    return "zh" if cn > en else ("en" if en > cn else "mixed")

def extract_tags(title, content=""):
    text = ((title or "") + " " + (content or "")).lower()
    tags = []
    if any(k in text for k in ["llm","gpt","chatgpt","aigc","ai","大模型","模型","训练"]): tags.append("AI")
    if any(k in text for k in ["手机","iphone","android","小米","华为"]): tags.append("Mobile")
    if any(k in text for k in ["新能源","电动","特斯拉","比亚迪","智驾"]): tags.append("EV")
    if any(k in text for k in ["ufc","拳击","格斗","mma","NBA","篮球","足球"]): tags.append("Sports")
    if any(k in text for k in ["军事","战争","装备","战斗机"]): tags.append("Military")
    if any(k in text for k in ["摄影","相机","绘画","艺术"]): tags.append("Art")
    if any(k in text for k in ["github","开源","程序员","python","rust"]): tags.append("Dev")
    return "|".join(tags) if tags else "General"

def get_db():
    return sqlite3.connect(DB_PATH, timeout=30)

def insert_batch(items: list[dict]) -> int:
    if not items: return 0
    db = get_db()
    new_count = 0
    now = now_str()
    for item in items:
        url = item.get("url", "")
        h = url_hash(url)
        try:
            db.execute("""
                INSERT OR IGNORE INTO raw_intelligence 
                (platform, title, content, url, url_hash, author, author_id, 
                 published_at, collected_at, hot_score, source_type, language, category_tags)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                item.get("platform", "toutiao"),
                item.get("title","")[:500],
                item.get("content","")[:2000],
                url[:1000], h,
                item.get("author",""), item.get("author_id",""),
                item.get("published_at", now), now,
                item.get("hot_score", 0), item.get("source_type", "toutiao_api"),
                detect_lang(item.get("title",""), item.get("content","")),
                extract_tags(item.get("title",""), item.get("content",""))
            ))
            if db.total_changes > 0: new_count += 1
        except: pass
    db.commit()
    db.close()
    return new_count

def collect_toutiao_multi_keyword() -> list[dict]:
    """多关键词搜索API采集"""
    items = []

    # 头条搜索API - 支持关键词搜索
    search_url = "https://www.toutiao.com/api/search/content/?keyword={kw}&pd=article&source=input&offset=0&count=20&as=A1D5BB7E4A8B6B4&cp=62F7E3E5E8E6D1&"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://www.toutiao.com/",
        "Accept": "application/json, text/plain",
    }

    for kw in KEYWORDS:
        try:
            url = search_url.format(kw=kw)
            out = fetch(url, headers=headers, timeout=8)
            if out:
                d = json.loads(out)
                for item in d.get("data", []):
                    title = item.get("title", "")
                    if len(title) < 5:
                        continue

                    article_url = item.get("article_url", "") or item.get("share_url", "") or item.get("url", "")
                    if not article_url:
                        continue

                    # 过滤非头条链接
                    if "toutiao.com" not in article_url and "bytedance" not in article_url:
                        continue

                    items.append({
                        "platform": "toutiao",
                        "title": title,
                        "content": item.get("abstract", "")[:500] if item.get("abstract") else f"Toutiao KW:{kw}",
                        "url": article_url[:300],
                        "author": item.get("user_info", {}).get("name", "") if isinstance(item.get("user_info"), dict) else "",
                        "author_id": str(item.get("user_info", {}).get("user_id", "")) if isinstance(item.get("user_info"), dict) else "",
                        "published_at": item.get("publish_time", now_str()) if item.get("publish_time") else now_str(),
                        "hot_score": item.get("go_detail_count", 0),
                        "source_type": "toutiao_search",
                        "category_tags": extract_tags(title, kw)
                    })
        except Exception:
            pass

        time.sleep(random.uniform(0.3, 0.8))

    return items

def collect_toutiao_hot_api() -> list[dict]:
    """头条热榜API"""
    items = []

    # 热榜API端点
    hot_urls = [
        "https://www.toutiao.com/api/pc/feed/?category=hot_board&count=30",
        "https://www.toutiao.com/api/pc/feed/?category=news_tech&count=30",
        "https://www.toutiao.com/api/pc/feed/?category=news_game&count=30",
        "https://www.toutiao.com/api/pc/feed/?category=news_sports&count=30",
        "https://www.toutiao.com/api/pc/feed/?category=news_finance&count=30",
        "https://www.toutiao.com/api/pc/feed/?category=news_car&count=30",
        "https://www.toutiao.com/api/pc/feed/?category=news_entertainment&count=30",
        "https://www.toutiao.com/api/pc/feed/?category=news_military&count=30",
        "https://www.toutiao.com/api/pc/feed/?category=news_world&count=30",
        "https://www.toutiao.com/api/pc/feed/?category=news_life&count=30",
    ]

    for url in hot_urls:
        try:
            out = fetch(url, timeout=8)
            if not out:
                continue

            d = json.loads(out)
            for item in d.get("data", []):
                title = item.get("title", "")
                if len(title) < 5:
                    continue

                article_url = item.get("article_url", "") or item.get("url", "")
                if not article_url or "toutiao.com" not in article_url:
                    continue

                items.append({
                    "platform": "toutiao",
                    "title": title,
                    "content": item.get("abstract", "")[:500] if item.get("abstract") else "",
                    "url": article_url[:300],
                    "author": item.get("user_info", {}).get("name", "") if isinstance(item.get("user_info"), dict) else "",
                    "author_id": str(item.get("user_info", {}).get("user_id", "")) if isinstance(item.get("user_info"), dict) else "",
                    "published_at": item.get("publish_time", now_str()) if item.get("publish_time") else now_str(),
                    "hot_score": item.get("go_detail_count", 0),
                    "source_type": "toutiao_hot",
                    "category_tags": extract_tags(title, "")
                })
        except Exception:
            pass

        time.sleep(random.uniform(0.2, 0.5))

    return items

def run():
    print("="*60)
    print("今日头条增强采集器")
    print("="*60)

    all_items = []

    print("\n[1/2] 热榜API...")
    hot_items = collect_toutiao_hot_api()
    print(f"热榜: {len(hot_items)} items")
    all_items.extend(hot_items)

    print("\n[2/2] 关键词搜索...")
    search_items = collect_toutiao_multi_keyword()
    print(f"搜索: {len(search_items)} items")
    all_items.extend(search_items)

    print(f"\n总计: {len(all_items)} items")

    if all_items:
        # 去重
        seen = set()
        unique = []
        for item in all_items:
            h = url_hash(item["url"])
            if h not in seen:
                seen.add(h)
                unique.append(item)

        count = insert_batch(unique)
        print(f"去重后: {len(unique)}, 写入DB: {count} new records")

        for item in unique[:5]:
            print(f"  {item['title'][:60]}")
    else:
        print("WARNING: No items!")

if __name__ == "__main__":
    run()
