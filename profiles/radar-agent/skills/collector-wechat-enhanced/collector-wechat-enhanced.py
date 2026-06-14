#!/usr/bin/env python3
"""
微信公众号增强采集器 - 搜狗微信搜索API

功能:
  1. 使用80+用户偏好词作为搜索关键词
  2. 每个关键词取前5条
# 3. 写入 $HOME/.hermes/intelligence.db 的 raw_intelligence 表
  4. 平台标记为 sogou_wechat

字段映射:
  title, content, url, source, platform='sogou_wechat',
  author, category, tags, hot_score, collected_at, url_hash, source_type

参考: hermes_collector_v6.py 的 collect_weixin_sogou() 实现
"""

import hashlib
import html as html_module
import re
import ssl
import time
from datetime import datetime
from pathlib import Path
from urllib.request import Request, urlopen

# ============================================================
# 配置
# ============================================================
HERMES = Path.home() / ".hermes"
DB_PATH = HERMES / "intelligence.db"

UA_POOL = [
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
]

# 80+ 用户偏好搜索关键词 - 覆盖AI/大模型/科技/汽车/军事/财经/体育/摄影/游戏/美食/旅行/时尚/教育等
USER_PREFERENCE_KEYWORDS = [
    # ---- AI / 大模型 (15) ----
    "AI大模型", "ChatGPT", "人工智能", "大模型应用", "AIGC",
    "深度学习", "机器学习", "GPT-4", "Claude", "Gemini",
    "AI编程", "AI Agent", "AI绘画", "AI视频生成", "开源大模型",
    # ---- 科技/数码 (12) ----
    "华为", "华为手机", "华为鸿蒙", "华为芯片",
    "比亚迪", "比亚迪汽车", "小米", "小米汽车", "小米手机",
    "iPhone", "苹果新品", "折叠屏",
    # ---- 军事/国际 (12) ----
    "军事新闻", "俄乌冲突", "中美关系", "台海局势", "南海",
    "国防建设", "国际局势", "地缘政治", "无人机", "航母",
    "武器装备", "军事科技",
    # ---- 汽车 (8) ----
    "新能源汽车", "特斯拉", "蔚来汽车", "小鹏汽车",
    "理想汽车", "智能驾驶", "自动驾驶", "电动车",
    # ---- 财经/商业 (8) ----
    "股市行情", "投资理财", "创业", "IPO", "融资",
    "宏观经济", "A股", "财经新闻",
    # ---- 体育 (6) ----
    "NBA", "CBA", "足球", "UFC", "格斗", "拳击",
    # ---- 摄影 (5) ----
    "摄影技巧", "相机", "人像摄影", "风光摄影", "后期修图",
    # ---- 游戏 (5) ----
    "游戏资讯", "Steam", "PS5", "Switch", "电竞",
    # ---- 美食/生活 (6) ----
    "美食探店", "美食推荐", "咖啡", "烘焙", "料理", "健康饮食",
    # ---- 旅行 (5) ----
    "旅行攻略", "自驾游", "户外", "酒店", "旅游",
    # ---- 时尚/美妆 (4) ----
    "时尚穿搭", "美妆", "护肤", "潮流",
    # ---- 教育/职场 (5) ----
    "学习方法", "职场", "考研", "留学", "编程学习",
    # ---- 美女/娱乐 (6) ----
    "美女", "美女写真", "明星八卦", "娱乐圈", "综艺", "动漫",
]
# Total: 15+12+12+8+8+6+5+5+6+5+4+5+6 = 97 keywords


# ============================================================
# 工具函数
# ============================================================

def _fetch(url: str, headers: dict = None, timeout: int = 15, post_data: str = None) -> str:
    """简化的HTTP请求函数"""
    ua = UA_POOL[int(time.time()) % len(UA_POOL)]
    h = {"User-Agent": ua}
    if headers:
        h.update(headers)
    try:
        req = Request(url, data=post_data.encode() if post_data else None, headers=h)
        ctx = ssl.create_default_context()
        with urlopen(req, timeout=timeout, context=ctx) as resp:
            ct = resp.headers.get("content-type", "")
            charset = "utf-8"
            if "charset=" in ct:
                charset = ct.split("charset=")[-1].split(";")[0].strip()
            return resp.read().decode(charset, errors="replace")
    except Exception:
        return ""


def _normalize_date(date_str: str) -> str:
    """标准化搜狗日期格式 -> ISO格式"""
    if not date_str or date_str == "None":
        return ""
    date_str = date_str.strip()
    now = datetime.now()
    if "分钟前" in date_str:
        m = re.search(r"(\d+)", date_str)
        mins = int(m.group(1)) if m else 0
        dt = datetime.fromtimestamp(time.time() - mins * 60)
        return dt.strftime("%Y-%m-%dT%H:%M:%S")
    if "小时前" in date_str:
        m = re.search(r"(\d+)", date_str)
        hours = int(m.group(1)) if m else 0
        dt = datetime.fromtimestamp(time.time() - hours * 3600)
        return dt.strftime("%Y-%m-%dT%H:%M:%S")
    if "昨天" in date_str:
        dt = datetime.fromtimestamp(time.time() - 86400)
        return dt.strftime("%Y-%m-%dT00:00:00")
    if "前天" in date_str:
        dt = datetime.fromtimestamp(time.time() - 172800)
        return dt.strftime("%Y-%m-%dT00:00:00")
    # 常见格式: 2023-12-25 或 2023/12/25
    m = re.search(r"(\d{4}[-/]\d{1,2}[-/]\d{1,2})", date_str)
    if m:
        return m.group(1).replace("/", "-") + "T00:00:00"
    return date_str


def _url_hash(url: str) -> str:
    """生成URL的SHA256哈希（前32字符）"""
    return hashlib.sha256(url.encode()).hexdigest()[:32]


def _extract_category(title: str, content: str = "") -> str:
    """从标题和内容提取分类"""
    text = (title + " " + (content or "")).lower()

    # 优先级顺序：越靠前优先级越高
    ai_kw = ["llm", "gpt", "chatgpt", "aigc", "ai", "artificial intelligence",
             "大模型", "模型", "人工智能", "深度学习", "机器学习", "agent", "rag",
             "embedding", "diffusion", "stable diffusion", "midjourney", "claude",
             "gemini", "openai", "anthropic", "deepseek", "qwen", "kimi",
             "copilot", "cursor", "sora", "llama", "mistral", "AI编程", "AI绘画",
             "AI视频", "AI Agent", "AI助手", "AI搜索"]

    tech_kw = ["华为", "鸿蒙", "芯片", "gpu", "cuda", "nvidia", "amd", "intel",
               "骁龙", "天玑", "麒麟", "手机", "iphone", "android", "折叠屏",
               "ios", "系统", "操作系统", "数据库", "云计算", "云服务", "服务器",
               "arm", "risc-v", "算力", "处理器"]

    military_kw = ["军事", "战争", "武器", "俄乌", "中美", "台海", "南海",
                   "国防", "军队", "航母", "无人机", "军演", "地缘政治",
                   "国际局势", "冲突", "制裁", "中东", "北约", "伊朗", "以色列",
                   "乌克兰", "俄罗斯", "朝鲜", "胡塞"]

    auto_kw = ["新能源汽车", "电动汽车", "特斯拉", "比亚迪", "蔚来", "小鹏",
               "理想", "小米汽车", "问界", "智能驾驶", "自动驾驶", "电动车",
               "充电", "电池", "混动"]

    finance_kw = ["股市", "投资", "理财", "IPO", "融资", "创业", "A股",
                  "基金", "股票", "债券", "加密货币", "比特币", "区块链",
                  "宏观经济", "央行", "降息", "加息", "通货膨胀"]

    sports_kw = ["NBA", "CBA", "足球", "UFC", "格斗", "拳击", "MMA", "篮球",
                 "足球", "世界杯", "奥运", "冠军", "体育"]

    photo_kw = ["摄影", "相机", "镜头", "拍照", "人像", "风光", "调色",
                "后期", "修图", "摄像", "索尼", "佳能", "尼康", "富士"]

    game_kw = ["游戏", "Steam", "PS5", "Xbox", "Switch", "电竞", "手游",
               "主机", "3A", "独立游戏", "原神", "王者荣耀"]

    food_kw = ["美食", "探店", "咖啡", "烘焙", "料理", "菜谱", "餐厅",
               "食材", "烹饪", "好吃", "美味"]

    travel_kw = ["旅行", "旅游", "自驾", "酒店", "民宿", "攻略", "户外",
                 "露营", "徒步", "机票"]

    fashion_kw = ["时尚", "穿搭", "美妆", "护肤", "潮流", "服装", "设计",
                  "奢侈品", "包包", "发型", "美女", "写真"]

    edu_kw = ["学习", "教育", "考研", "留学", "职场", "编程", "培训",
              "课程", "考试", "大学", "高考", "英语"]

    # 按优先级匹配分类
    if any(k in text for k in ai_kw):
        return "AI_Tech"
    if any(k in text for k in military_kw):
        return "Military_Intl"
    if any(k in text for k in auto_kw):
        return "Auto_EV"
    if any(k in text for k in tech_kw):
        return "Tech_Digital"
    if any(k in text for k in finance_kw):
        return "Finance"
    if any(k in text for k in sports_kw):
        return "Sports"
    if any(k in text for k in photo_kw):
        return "Photography"
    if any(k in text for k in game_kw):
        return "Game"
    if any(k in text for k in food_kw):
        return "Food"
    if any(k in text for k in travel_kw):
        return "Travel"
    if any(k in text for k in fashion_kw):
        return "Fashion_Beauty"
    if any(k in text for k in edu_kw):
        return "Education"

    return "General"


def _extract_tags(title: str, content: str = "") -> str:
    """从标题和内容提取标签（以|分隔）"""
    text = (title + " " + (content or "")).lower()
    tags = []

    # AI
    if any(k in text for k in ["llm", "gpt", "chatgpt", "aigc", "大模型", "人工智能",
                                "deepseek", "claude", "gemini", "openai", "anthropic",
                                "agent", "rag", "diffusion", "ai编程", "ai绘画"]):
        tags.append("AI")

    # Tech
    if any(k in text for k in ["华为", "鸿蒙", "芯片", "手机", "iphone", "小米",
                                "折叠屏", "gpu", "nvidia", "amd", "intel", "骁龙"]):
        tags.append("Tech")

    # Military
    if any(k in text for k in ["军事", "战争", "武器", "俄乌", "中美", "台海",
                                "国防", "地缘", "冲突", "制裁"]):
        tags.append("Military")

    # Auto/EV
    if any(k in text for k in ["新能源", "电动汽车", "特斯拉", "比亚迪", "蔚来",
                                "智能驾驶", "自动驾驶", "电动车"]):
        tags.append("EV")

    # Auto general
    if any(k in text for k in ["汽车", "车型", "发动机", "本田", "丰田", "宝马",
                                "奔驰", "赛车"]):
        tags.append("Auto")

    # Finance
    if any(k in text for k in ["股市", "投资", "理财", "ipo", "融资", "创业",
                                "股票", "基金", "比特币", "加密货币"]):
        tags.append("Finance")

    # Sports
    if any(k in text for k in ["nba", "cba", "ufc", "格斗", "拳击", "mma",
                                "足球", "篮球", "世界杯"]):
        tags.append("Sports")

    # Photography
    if any(k in text for k in ["摄影", "相机", "镜头", "拍照", "人像", "风光",
                                "调色", "后期", "修图"]):
        tags.append("Photography")

    # Game
    if any(k in text for k in ["游戏", "steam", "ps5", "switch", "电竞", "手游"]):
        tags.append("Game")

    # Food
    if any(k in text for k in ["美食", "探店", "咖啡", "烘焙", "料理", "菜谱"]):
        tags.append("Food")

    # Travel
    if any(k in text for k in ["旅行", "旅游", "自驾", "酒店", "民宿", "攻略", "户外"]):
        tags.append("Travel")

    # Fashion
    if any(k in text for k in ["时尚", "穿搭", "美妆", "护肤", "潮流", "美女"]):
        tags.append("Fashion")

    # Education
    if any(k in text for k in ["学习", "教育", "考研", "留学", "职场", "编程"]):
        tags.append("Education")

    return "|".join(tags) if tags else "WeChat|General"


# ============================================================
# 搜狗微信公众号搜索采集
# ============================================================

def collect_sogou_wechat(keywords: list[str] = None, max_per_kw: int = 5) -> list[dict]:
    """
    搜狗微信搜索采集
    
    从搜狗微信搜API获取公众号文章，使用用户偏好词搜索
    
    Args:
        keywords: 搜索关键词列表，默认使用 USER_PREFERENCE_KEYWORDS (97个)
        max_per_kw: 每个关键词最多取多少条
        
    Returns:
        List[dict]: 符合 raw_intelligence 表结构的记录列表
    """
    if keywords is None:
        keywords = USER_PREFERENCE_KEYWORDS

    items = []
    seen_urls = set()
    seen_titles = set()
    total_kw = len(keywords)
    now_iso = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    print(f"  [SogouWeChat] Starting collection: {total_kw} keywords, max {max_per_kw}/kw")

    for idx, kw in enumerate(keywords):
        if not kw or not kw.strip():
            continue

        # 打印进度
        if (idx + 1) % 10 == 0 or idx == 0:
            print(f'  [SogouWeChat] Keyword {idx+1}/{total_kw}: "{kw}" (items so far: {len(items)})')

        try:
            # === 参考 hermes_collector_v6.py 的 collect_weixin_sogou() 实现 ===
            # 搜狗微信搜索页面：type=2 搜索文章
            search_url = f"https://weixin.sogou.com/weixin?type=2&query={kw}&ie=utf8"

            headers = {
                "User-Agent": UA_POOL[idx % len(UA_POOL)],
                "Referer": "https://weixin.sogou.com/",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            }

            out = _fetch(search_url, headers, timeout=12)

            # 检查是否被反爬
            if not out or len(out) < 200:
                continue

            if "antispider" in out[:500] or "请输入验证码" in out or "验证" in out[:1000]:
                if (idx + 1) % 10 == 0:
                    print(f'  [SogouWeChat] WARNING: Anti-spider detected for kw="{kw}", skipping batch')
                continue

            # 解析搜索结果
            # 提取标题（在<h3>标签内的<a>链接文本）
            titles = re.findall(r"<h3[^>]*>.*?<a[^>]*>(.*?)</a>", out, re.DOTALL)

            # 提取链接 - 优先匹配搜索结果块中的链接
            # 方法1: 从 <h3><a> 中提取href
            link_blocks = re.findall(r'<h3[^>]*>.*?<a[^>]*href="([^"]+)"', out, re.DOTALL)
            links = []
            for lb in link_blocks:
                if lb.startswith("//"):
                    lb = "https:" + lb
                elif lb.startswith("/"):
                    lb = "https://weixin.sogou.com" + lb
                if any(skip in lb for skip in ["sogou.com/images", "sogou.com/index", ".ico", ".png", ".gif", ".svg"]):
                    continue
                links.append(lb)

            if not links:
                # 方法2: 匹配 mp.weixin.qq.com 链接
                links = re.findall(r'href="(https?://mp\.weixin\.qq\.com[^"]*)"', out)

            if not links:
                # 方法3: 匹配搜狗跳转链接
                links = re.findall(r'href="(/link\?[^"]*)"', out)
                links = [f"https://weixin.sogou.com{l}" for l in links]

            # 提取日期
            dates = re.findall(r'<span[^>]*class="s2"[^>]*>(.*?)</span>', out, re.DOTALL)
            if not dates:
                dates = re.findall(r'<span[^>]*class="[^"]*time[^"]*"[^>]*>(.*?)</span>', out, re.DOTALL)

            # 提取公众号名称（作者）
            authors = re.findall(r'<span[^>]*class="s3"[^>]*>(.*?)</span>', out, re.DOTALL)
            if not authors:
                # 尝试从链接中提取
                authors = re.findall(r'account_name_([^"]+)', out)

            # 提取摘要/简介作为content
            summaries = re.findall(r'<p[^>]*class="txt-info"[^>]*>(.*?)</p>', out, re.DOTALL)

            # 逐条处理
            count = 0
            for i in range(min(len(titles), len(links) if links else 0)):
                if count >= max_per_kw:
                    break

                # 清理标题
                title = re.sub(r"<[^>]+>", "", titles[i]).strip()
                title = html_module.unescape(title)
                if len(title) < 4:
                    continue
                if title in seen_titles:
                    continue
                seen_titles.add(title)

                # 链接
                link = links[i] if i < len(links) else ""
                if not link:
                    continue
                # 补全相对路径
                if link.startswith("//"):
                    link = "https:" + link
                elif link.startswith("/"):
                    link = "https://weixin.sogou.com" + link
                if link in seen_urls:
                    continue
                seen_urls.add(link)

                # 日期
                date = dates[i].strip() if i < len(dates) else ""
                pub_at = _normalize_date(date)

                # 作者（公众号名称）
                author = authors[i].strip() if i < len(authors) else ""
                author = re.sub(r"<[^>]+>", "", author).strip()
                author = html_module.unescape(author)

                # 内容摘要
                summary = summaries[i].strip() if i < len(summaries) else ""
                summary = re.sub(r"<[^>]+>", "", summary).strip()
                summary = html_module.unescape(summary)

                content = summary or f"Article from WeChat search for keyword: {kw}"

                # 生成分类和标签
                category = _extract_category(title, content)
                tags = _extract_tags(title, content)

                # 构建记录 - 严格匹配 raw_intelligence 表结构
                item = {
                    "title": title[:500],
                    "content": content[:2000],
                    "url": link,
                    "source": "sogou_wechat",          # source 字段
                    "platform": "sogou_wechat",         # platform 字段
                    "author": author[:100],
                    "category": category,                # category 字段
                    "tags": tags,                        # tags 字段
                    "hot_score": 0.0,                    # hot_score 浮点
                    "collected_at": now_iso,             # collected_at
                    "url_hash": _url_hash(link),         # url_hash
                    "source_type": "api",                # source_type
                }

                items.append(item)
                count += 1

            # 节流 -避免触发反爬
            time.sleep(0.5 + (idx % 3) * 0.2)

        except Exception as e:
            if (idx + 1) % 10 == 0:
                print(f'  [SogouWeChat] Error at keyword "{kw}": {e}')
            continue

    print(f"  [SogouWeChat] Collection complete: {len(items)} unique items from {total_kw} keywords")
    return items


# ============================================================
# 数据库写入
# ============================================================

def _insert_batch(items: list[dict]) -> int:
    """
    批量写入 raw_intelligence 表
    
    Args:
        items: 采集到的记录列表
        
    Returns:
        int: 新写入的记录数
    """
    import sqlite3

    if not items:
        return 0

    new_count = 0
    now_iso = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        db = sqlite3.connect(str(DB_PATH), timeout=30)

        for item in items:
            try:
                url_h = item.get("url_hash") or _url_hash(item.get("url", ""))

                # 先检查是否已存在（通过url_hash）
                existing = db.execute(
                    "SELECT id FROM raw_intelligence WHERE url_hash = ?", (url_h,)
                ).fetchone()

                if existing:
                    continue

                db.execute("""
                    INSERT INTO raw_intelligence 
                    (title, content, url, source, platform, author, 
                     category, tags, hot_score, collected_at, url_hash, source_type)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    item.get("title", "")[:500],
                    item.get("content", "")[:2000],
                    item.get("url", ""),
                    item.get("source", "sogou_wechat"),
                    item.get("platform", "sogou_wechat"),
                    item.get("author", "")[:100],
                    item.get("category", "General"),
                    item.get("tags", "WeChat|General"),
                    float(item.get("hot_score", 0.0)),
                    item.get("collected_at", now_iso),
                    url_h,
                    item.get("source_type", "api"),
                ))
                db.commit()
                new_count += 1

            except Exception:
                continue

        db.close()

    except Exception as e:
        print(f"  [SogouWeChat] DB Error: {e}")

    return new_count


# ============================================================
# 主入口
# ============================================================

def collect_wechat_enhanced() -> list[dict]:
    """
    微信公众号增强采集主函数
    
    从搜狗微信搜索API获取公众号文章，使用97个用户偏好词搜索，
    每个关键词取前5条，去重后返回
    
    Returns:
        List[dict]: 符合 raw_intelligence 表结构的记录列表
    """
    # 使用全部97个用户偏好关键词，每词取5条
    items = collect_sogou_wechat(
        keywords=USER_PREFERENCE_KEYWORDS,
        max_per_kw=5
    )
    return items


def main():
    """主入口：采集并写入数据库"""
    print("=" * 60)
    print("  微信公众号增强采集器 (Sogou WeChat Enhanced)")
    print(f"  时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  关键词数: {len(USER_PREFERENCE_KEYWORDS)}")
    print("=" * 60)

    items = collect_wechat_enhanced()

    if items:
        new_count = _insert_batch(items)
        print(f"\n  结果: 共采集 {len(items)} 条, 新写入 {new_count} 条")
    else:
        print("\n  结果: 未采集到任何内容")

    print("=" * 60)
    return len(items)


if __name__ == "__main__":
    main()
