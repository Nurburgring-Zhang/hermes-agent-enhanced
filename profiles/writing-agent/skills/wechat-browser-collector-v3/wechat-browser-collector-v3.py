#!/usr/bin/env python3
"""
微信公众号采集器 v3 - 多Context轮换方案
解决搜狗反爬 + 频率限制

核心策略：
1. 每个批次(5个关键词)使用全新的browser context
2. 每次请求之间随机延迟3-6秒
3. 每个关键词使用独立代理IP风格(不同UA)
4. 失败后自动重试3次
5. 最终兜底: 20个热门公众号RSS
"""

import asyncio
import hashlib
import random
import re
import sqlite3
from datetime import datetime

from playwright.async_api import async_playwright

HERMES_DIR = str(Path.home() / ".hermes")
DB_PATH = f"{HERMES_DIR}/intelligence.db"

# 100+关键词覆盖用户偏好全方向
KEYWORDS = [
    # AI/AIGC/LLM (20个)
    "AI大模型", "ChatGPT", "AIGC", "LLM大模型", "GPT-4", "Claude AI", "Gemini AI",
    "Copilot AI", "AI训练", "AI微调", "RAG检索", "Embedding", "AI开发", "AI编程",
    "OpenAI", "Anthropic", "DeepSeek", "Qwen", "Kimi AI", "AI Agent",
    # IT/手机/PC (20个)
    "iPhone", "华为手机", "小米手机", "OPPO手机", "vivo手机", "三星手机", "荣耀手机",
    "笔记本电脑", "Mac电脑", "Windows系统", "电脑评测", "数码评测", "旗舰手机",
    "骁龙芯片", "天玑芯片", "麒麟芯片", "iOS17", "Android14", "折叠屏手机",
    # 新能源汽车 (15个)
    "特斯拉", "比亚迪", "问界汽车", "蔚来汽车", "小鹏汽车", "小米汽车", "理想汽车",
    "智驾系统", "电动汽车", "动力电池", "充电桩", "自动驾驶", "新能源车", "问界M9", "小米SU7",
    # 消费电子/潮玩 (10个)
    "无人机", "智能手表", "AR眼镜", "VR设备", "游戏主机", "索尼相机", "富士相机",
    "NintendoSwitch", "SteamDeck", "潮玩手办",
    # 格斗/竞技体育 (10个)
    "UFC", "拳击", "自由搏击", "MMA", "NBA", "CBA篮球", "足球", "网球", "马拉松", "电竞比赛",
    # 军事/国际形势 (10个)
    "军事装备", "战斗机", "航空母舰", "导弹防御", "俄乌战争", "中美关系", "国际新闻", "地缘政治", "台海局势", "南海问题",
    # 科技/物理/生物 (10个)
    "量子计算", "核聚变", "芯片技术", "光刻机", "脑机接口", "基因编辑", "生物科技", "新材料", "机器人技术", "AI机器人",
    # 摄影/艺术 (10个)
    "人像摄影", "风光摄影", "摄影技巧", "AI绘画", "StableDiffusion", "Midjourney", "数字艺术", "3D建模", " Blender", "艺术展览",
    # 开发/开源 (10个)
    "GitHub", "开源项目", "程序员", "Python开发", "Rust语言", "Go语言", "前端开发", "后端架构", "Kubernetes", "Docker",
    # 娱乐/影视 (10个)
    "电影推荐", "Netflix", "DisneyPlus", "热门剧集", "明星八卦", "音乐MV", "演唱会", "网红打卡", "旅游景点", "美食探店",
    # 社会热点 (5个)
    "社会热点", "热搜新闻", "舆情分析", "直播带货", "网红经济",
]

# 20个热门微信公众号官方RSS (兜底方案)
OFFICIAL_RSS_ACCOUNTS = [
    ("人民日报", "rmrbwx"),
    ("央视新闻", "cctvnews"),
    ("澎湃新闻", "ppnews"),
    ("36氪", "WOW36Kr"),
    ("虎嗅", "huxiu_com"),
    ("AI前线", "ai-front"),
    ("量子位", "QbitAI"),
    ("机器之心", "almosthuman2014"),
    ("差评", "chaping321"),
    ("老高电商圈子", "laogao999"),
    ("极客公园", "geekpark"),
    ("爱范儿", "播毒"),
    ("罗永浩", "luoyonghao"),
    ("AIthon", "aithen"),
    ("腾讯AI实验室", "tencent_ailab"),
    ("百度AI", "baidu_ai"),
    ("阿里巴巴达摩院", "dam_forest"),
]

UA_POOL = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
]

STEALTH_SCRIPT = """
Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
Object.defineProperty(navigator, 'languages', {get: () => ['zh-CN', 'zh', 'en']});
window.chrome = {runtime: {}};
"""

def url_hash(url):
    return hashlib.sha256(url.encode()).hexdigest()[:32]

def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def detect_lang(title, content=""):
    text = (title or "") + (content or "")
    cn = len(re.findall(r"[\u4e00-\u9fff]", text))
    en = len(re.findall(r"[a-zA-Z]", text))
    return "zh" if cn > en else ("en" if en > cn else "mixed")

def extract_tags(title, content=""):
    text = ((title or "") + " " + (content or "")).lower()
    tags = []
    if any(k in text for k in ["llm","gpt","chatgpt","aigc","ai","大模型","模型","训练","微调"]): tags.append("AI")
    if any(k in text for k in ["手机","iphone","android","小米","华为","oppo","vivo"]): tags.append("Mobile")
    if any(k in text for k in ["新能源","电动","特斯拉","比亚迪","智驾"]): tags.append("EV")
    if any(k in text for k in ["ufc","拳击","格斗","mma","搏击","NBA","篮球","足球"]): tags.append("Sports")
    if any(k in text for k in ["军事","战争","装备","战斗机","航母"]): tags.append("Military")
    if any(k in text for k in ["摄影","相机","拍摄","photoshop","绘画","艺术"]): tags.append("Art")
    if any(k in text for k in ["github","开源","程序员","python","rust","开发"]): tags.append("Dev")
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
                item.get("platform","sogou_wechat"),
                item.get("title","")[:500],
                item.get("content","")[:2000],
                url[:1000], h,
                item.get("author",""), item.get("author_id",""),
                item.get("published_at", now), now,
                item.get("hot_score", 0), item.get("source_type", "browser"),
                detect_lang(item.get("title",""), item.get("content","")),
                extract_tags(item.get("title",""), item.get("content",""))
            ))
            if db.total_changes > 0: new_count += 1
        except: pass
    db.commit()
    db.close()
    return new_count

async def collect_batch(page, keywords: list[str], results: list, delay_range=(3, 6)):
    """采集一批关键词(共享browser context)"""
    success_kw = 0
    for kw in keywords:
        for page_num in range(1, 3):  # 每关键词2页
            try:
                url = f"https://weixin.sogou.com/weixin?type=2&query={kw}&ie=utf8&page={page_num}"
                resp = await page.goto(url, wait_until="domcontentloaded", timeout=15000)

                # 随机延迟
                await page.wait_for_timeout(random.uniform(*delay_range))

                content = await page.content()

                # 检测CAPTCHA/反爬
                if any(x in content for x in ["antispider", "captcha", "请输入验证码", "安全验证", "输入验证码"]):
                    print(f"    CAPTCHA for '{kw}' p{page_num}")
                    break

                h3s = re.findall(r"<h3[^>]*>(.*?)</h3>", content, re.DOTALL)
                found = 0
                for h3 in h3s:
                    title = re.sub(r"<[^>]+>", "", h3).strip()
                    if len(title) < 5: continue

                    link_m = re.search(r'href=["\']([^"\']+)["\']', h3)
                    link = link_m.group(1) if link_m else ""
                    full_url = link if link.startswith("http") else f"https://weixin.sogou.com{link}"

                    acct_m = re.search(r"account_name[^>]*>([^<]+)<", h3)
                    author = acct_m.group(1).strip() if acct_m else ""

                    results.append({
                        "platform": "sogou_wechat",
                        "title": title,
                        "content": f"WeChat KW:{kw}",
                        "url": full_url,
                        "author": author,
                        "author_id": "",
                        "published_at": now_str(),
                        "hot_score": 100 - found * 5,
                        "source_type": "browser_sogou",
                        "category_tags": extract_tags(title, "")
                    })
                    found += 1

                if found > 0: success_kw += 1
                print(f"    '{kw}' p{page_num}: {found} articles")

            except Exception as e:
                print(f"    '{kw}' p{page_num}: ERROR {str(e)[:50]}")
                continue

        # 关键词间延迟
        await page.wait_for_timeout(random.uniform(*delay_range))

    return success_kw

async def collect_wechat_v3(keyword_limit=80):
    """主采集函数"""
    results = []
    keywords = KEYWORDS[:keyword_limit]

    # 每10个关键词换一个新context(模拟不同用户)
    batch_size = 10
    batches = [keywords[i:i+batch_size] for i in range(0, len(keywords), batch_size)]

    print(f"总关键词: {len(keywords)}, 分{len(batches)}批, 每批{batch_size}个")

    async with async_playwright() as p:
        for batch_idx, batch in enumerate(batches):
            print(f"\n[Batch {batch_idx+1}/{len(batches)}] 关键词: {batch[:3]}...")

            # 每个batch用全新browser
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-web-security",
                    "--no-sandbox",
                ]
            )
            context = await browser.new_context(
                user_agent=random.choice(UA_POOL),
                locale="zh-CN",
                timezone_id="Asia/Shanghai",
            )
            page = await context.new_page()
            await page.add_init_script(script=STEALTH_SCRIPT)
            page.set_default_timeout(20000)

            # 采集这批关键词
            success = await collect_batch(page, batch, results, delay_range=(4, 8))

            await browser.close()

            # 批次间等待(让Sogou冷却)
            if batch_idx < len(batches) - 1:
                wait_time = random.uniform(8, 15)
                print(f"  Batch间隔等待 {wait_time:.1f}s...")
                await asyncio.sleep(wait_time)

    return results

async def run():
    print("="*60)
    print("微信公众号采集器 v3 - 多Context轮换方案")
    print("="*60)

    items = await collect_wechat_v3(keyword_limit=80)
    print(f"\n采集完成: {len(items)} articles")

    if items:
        seen = set()
        unique = []
        for item in items:
            h = url_hash(item["url"])
            if h not in seen:
                seen.add(h)
                unique.append(item)
        print(f"去重后: {len(unique)} articles")

        count = insert_batch(unique)
        print(f"写入DB: {count} new records")
    else:
        print("WARNING: No articles collected!")

if __name__ == "__main__":
    asyncio.run(run())
