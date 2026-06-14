#!/usr/bin/env python3
"""
Hermes 情报清洗管道 (Intelligence Cleaning Pipeline)
=====================================================
将原始情报转化为结构化、可推送的高价值情报

功能：
1. 去重 (URL Hash / Title Similarity)
2. 语言检测 + 中文比例计算
3. 重要性评分 (hot_score * platform_weight * freshness)
4. 个人偏好匹配 (Rust/TS/函数式/AI)
5. 价值评估 (技术深度/创新性/实用性)
6. AI相关性标记
7. 热点趋势检测
8. 70/30分层标记
"""

import json
import logging
import re
import sqlite3
from datetime import datetime
from pathlib import Path

HERMES = Path.home() / ".hermes"
DB_PATH = HERMES / "intelligence.db"
LOG_PATH = HERMES / "logs" / f"cleaning_{datetime.now().strftime('%Y%m%d')}.log"
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler(LOG_PATH, encoding="utf-8"), logging.StreamHandler()]
)
log = logging.getLogger("cleaning_pipeline")

# ── 平台权重 ────────────────────────────────────────────────────────────────
PLATFORM_WEIGHTS = {
    "github": 2.0,
    "bilibili": 1.5,
    "36kr": 1.5,
    "zhihu": 1.2,
    "reddit": 1.3,
    "oschina": 1.5,
    "huxiu": 1.3,
    "sspai": 1.4,
    "ithome": 1.2,
    "weibo": 0.8,
    "twitter": 1.0,
    "youtube": 1.0,
    "solidot": 1.6,
    "liangziwei": 1.4,
    "infoq": 1.5,
    "default": 1.0,
}

# ── 个人偏好关键词 ─────────────────────────────────────────────────────────
PERSONAL_KEYWORDS = {
    "rust": 3.0,
    "typescript": 2.5,
    "javascript": 1.5,
    "python": 1.5,
    "golang": 1.8,
    "llm": 3.0,
    "gpt": 2.5,
    "claude": 2.5,
    "openai": 2.5,
    "agent": 2.5,
    "mcp": 3.0,
    "aigc": 2.5,
    "生成式": 2.0,
    "fine-tuning": 2.5,
    "微调": 2.0,
    "推理": 2.0,
    "函数式": 2.0,
    "functional": 2.0,
    "架构": 1.5,
    "开源": 1.5,
    "github": 1.5,
    "模型": 2.0,
    "transformer": 2.5,
    "rag": 2.5,
    "rag": 2.5,
    "向量数据库": 2.5,
    "embedding": 2.5,
}

# ── 噪音关键词 ─────────────────────────────────────────────────────────────
NOISE_PATTERNS = [
    "广告", "推广", "抽奖", "中奖", "红包", "优惠券", "秒杀",
    "震惊", "惊人", "必看", "转疯了", "删前必看",
    "性感", "诱惑", "走光", "透视",
    "抖音带货", "快手带货", "直播带货",
]

# ── B站频道白名单 ─────────────────────────────────────────────────────────
# 只有这些B站分类/频道才会被清洗进推送管线
BILIBILI_CHANNEL_WHITELIST = [
    "科技", "数码", "知识", "编程", "AI", "人工智能",
    "开发者", "开源", "软件", "互联网", "产品",
]
# B站source前缀（采集器中source字段以这些开头才保留）
BILIBILI_SOURCE_WHITELIST_PREFIXES = [
    "B站-科技", "B站-数码", "B站-知识",
    "bilibili_科技", "bilibili_数码",
]
# 明确排除的B站source
BILIBILI_SOURCE_BLOCKLIST = [
    "B站-生活", "B站-游戏", "B站-动画", "B站-美食",
    "B站-影视", "B站-娱乐", "B站-音乐", "B站-舞蹈",
    "B站-时尚", "B站-穿搭", "B站-汽车", "B站-全站",
    "bilibili_电影", "bilibili_电视剧", "bilibili_动画",
    "bilibili_游戏", "bilibili_运动", "bilibili_美食",
    "bilibili_娱乐", "bilibili_穿搭", "bilibili_音乐",
    "bilibili_汽车", "bilibili_全站",
]

# ── AI相关关键词 ──────────────────────────────────────────────────────────
AI_KEYWORDS = [
    "ai", "llm", "gpt", "大模型", "人工智能", "chatgpt", "claude",
    "openai", "gemini", "anthropic", "aigc", "生成式", "扩散模型",
    "stable diffusion", "midjourney", "sora", "文生视频",
    "langchain", "autogen", "crewai", "crewai", "agent",
    "transformer", "attention", "rlhf", "dpo", "grpo",
    "fine-tune", "微调", "rag", "embedding", "向量",
    "llama", "mistral", "gemma", "qwen", "yi", "deepseek",
    "机器学习", "深度学习", "神经网络", "计算机视觉", "cv",
    "nlp", "自然语言", "语音识别", "asr",
]


def detect_language(text: str) -> tuple[str, float]:
    """检测语言和中文比例"""
    if not text:
        return "mixed", 0.5

    # 统计中文字符
    chinese_chars = len(re.findall(r"[\u4e00-\u9fff]", text))
    total_chars = len(re.findall(r"[\w\u00ff-\uffff]", text))

    if total_chars == 0:
        return "mixed", 0.5

    ratio = chinese_chars / total_chars

    if ratio > 0.7:
        return "zh", ratio
    if ratio < 0.2:
        return "en", 1 - ratio
    return "mixed", ratio


def is_noise(item: dict) -> bool:
    """判断是否为噪音内容"""
    title = item.get("title", "")
    content = (item.get("content", "") or "") + title

    for pattern in NOISE_PATTERNS:
        if pattern in content:
            return True

    # 标题太短
    if len(title) < 8:
        return True

    return False


def calc_personal_match(item: dict) -> float:
    """计算个人偏好匹配度"""
    text = (item.get("title", "") + " " + (item.get("content", "") or "") + " " + (item.get("tags", "") or "")).lower()

    score = 0.0
    matched = []
    for keyword, weight in PERSONAL_KEYWORDS.items():
        if keyword.lower() in text:
            score += weight
            matched.append(keyword)

    # AI相关额外加权
    if calc_ai_related(item) > 0:
        score += 2.0

    item["_matched_keywords"] = matched
    item["_personal_score"] = score
    return min(score, 10.0)  # 上限10分


def calc_ai_related(item: dict) -> int:
    """判断AI相关性"""
    if item.get("ai_related"):
        return 1

    text = (item.get("title", "") + " " + (item.get("content", "") or "") + " " + (item.get("tags", "") or "")).lower()

    count = 0
    for kw in AI_KEYWORDS:
        count += text.count(kw.lower())

    if count >= 2:
        return 2  # 强相关
    if count == 1:
        return 1  # 弱相关
    return 0


def calc_importance_score(item: dict) -> float:
    """计算综合重要性评分"""
    hot = item.get("hot_score", 0)
    view = item.get("view_count", 0)
    like = item.get("like_count", 0)
    comment = item.get("comment_count", 0)
    collect = item.get("collect_count", 0)
    platform = item.get("platform", "default")
    pweight = PLATFORM_WEIGHTS.get(platform, PLATFORM_WEIGHTS["default"])

    # 基础分数 = 互动综合
    base_score = (hot * 0.3 + view * 0.01 + like * 0.2 + comment * 0.3 + collect * 0.2) / 100

    # 平台加权
    base_score *= pweight

    # 偏好匹配加权
    personal = item.get("_personal_score", 0)
    base_score *= (1 + personal * 0.1)

    # AI相关性
    ai_rel = item.get("_ai_related", 0)
    if ai_rel >= 2:
        base_score *= 1.5
    elif ai_rel == 1:
        base_score *= 1.2

    # 发布时间衰减
    published = item.get("published_at", "") or item.get("collected_at", "")
    if published:
        try:
            if "T" in str(published):
                pub_dt = datetime.strptime(str(published)[:19], "%Y-%m-%dT%H:%M:%S")
            else:
                pub_dt = datetime.strptime(str(published)[:10], "%Y-%m-%d")
            hours_old = (datetime.now() - pub_dt).total_seconds() / 3600
            if hours_old < 6:
                base_score *= 1.5  # 6小时内加权
            elif hours_old > 48:
                base_score *= 0.5  # 48小时衰减
        except:
            pass

    return round(base_score, 2)


def title_similarity(t1: str, t2: str) -> float:
    """计算标题相似度 (0-1)"""
    if not t1 or not t2:
        return 0
    # 简单基于字符集合的Jaccard相似度
    s1 = set(t1.lower())
    s2 = set(t2.lower())
    if not s1 or not s2:
        return 0
    return len(s1 & s2) / len(s1 | s2)


def calc_value_level(score: float) -> int:
    """评分转等级 1-5"""
    if score >= 1000:
        return 5
    if score >= 500:
        return 4
    if score >= 100:
        return 3
    if score >= 20:
        return 2
    return 1


def get_value_reasons(item: dict) -> str:
    """生成价值描述"""
    reasons = []

    if item.get("_ai_related", 0) >= 2:
        reasons.append("AI/大模型相关")
    if item.get("_personal_score", 0) >= 3:
        reasons.append("高度匹配个人偏好")
    if item.get("hot_score", 0) >= 1000:
        reasons.append("高热度的内容")
    if item.get("platform") in ["github", "reddit"]:
        reasons.append("技术社区热门")
    if item.get("_matched_keywords"):
        reasons.append(f"命中关键词: {', '.join(item['_matched_keywords'][:3])}")

    return "; ".join(reasons) if reasons else "一般资讯"


# ── 主清洗函数 ─────────────────────────────────────────────────────────────
def clean_batch(batch_size: int = 200, max_batches: int = 100, order_by_id: bool = True) -> dict:
    """批量清洗原始情报（改进版）
    
    修复了以下问题：
    1. 【Bug: 批次被B站噪音填满】B站黑名单内容高热度占据排序前列，非B站内容无法进入批次
       → 解决: SQL层预过滤已知B站噪音
    2. 【Bug: 单批次限制】每次只处理2000条，需多次人工运行
       → 解决: 循环处理多个批次直到清完
    3. 【Bug: 旧数据得不到清洗】ORDER BY hot_score DESC意味着低热度数据永不处理
       → 解决: 默认按id升序（时间序）处理，从最早的数据开始
    """
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")

    stats = {
        "total_processed": 0,
        "new_cleaned": 0,
        "duplicates": 0,
        "noise_filtered": 0,
        "error": 0,
        "batches_run": 0,
        "remaining": 0,
    }

    # 构建B站黑名单SQL条件 — 在SQL层过滤掉已知噪音，避免它们抢占批次名额
    bilibili_source_block_conditions = " OR ".join(
        [f"(r.source LIKE '{blk}%' OR r.platform LIKE '{blk}%')" for blk in BILIBILI_SOURCE_BLOCKLIST]
    )
    # 白名单前缀 — 这些是允许的B站内容
    bilibili_source_allow_conditions = " OR ".join(
        [f"(r.source LIKE '{wl}%' OR r.platform LIKE '{wl}%')" for wl in BILIBILI_SOURCE_WHITELIST_PREFIXES]
    )
    # SQL层过滤：排除明确进入blocklist的B站记录
    # 逻辑：如果source/platform包含B站/bilibili，并且进入blocklist，则排除
    # 这样非B站内容就能正常进入批次
    bilibili_skip_sql = f"""
        AND NOT (
            (r.source LIKE '%B站%' OR r.source LIKE '%bilibili%' OR r.platform LIKE '%bilibili%')
            AND NOT ({bilibili_source_allow_conditions})
            AND ({bilibili_source_block_conditions})
        )
    """

    order_clause = "ORDER BY r.id ASC" if order_by_id else "ORDER BY r.hot_score DESC, r.collected_at DESC"

    for batch_num in range(1, max_batches + 1):
        # 获取未处理的原始记录 — SQL层预过滤已知B站噪音
        query = f"""
            SELECT r.id, r.title, r.content, r.url, r.source, r.platform, 
                   r.author, r.author_id,
                   r.category, r.tags, r.hot_score, r.view_count, r.like_count, 
                   r.collect_count,
                   r.comment_count, r.share_count, r.published_at, r.collected_at, r.raw_data
            FROM raw_intelligence r
            WHERE r.id NOT IN (
                SELECT COALESCE(c.raw_id, 0) FROM cleaned_intelligence c WHERE c.raw_id IS NOT NULL
            )
            {bilibili_skip_sql}
            {order_clause}
            LIMIT ?
        """
        cur = conn.execute(query, (batch_size,))

        cols = [d[0] for d in cur.description]
        rows = cur.fetchall()

        if not rows:
            log.info(f"批次{batch_num}: 无待清洗数据，全部处理完毕")
            break

        log.info(f"批次{batch_num}: 开始清洗 {len(rows)} 条记录")

        # 用于去重 - 存储(平台, 标题相似度key)
        seen_titles = {}  # key -> first_id

        batch_new = 0
        batch_dup = 0
        batch_noise = 0
        batch_err = 0

        for row in rows:
            try:
                item = dict(zip(cols, row))
                item_id = item["id"]

                # 去重检查
                title_key = re.sub(r"[^\w]", "", item.get("title", "")[:30].lower())
                if not title_key:
                    continue

                dup_found = False
                for seen_key, seen_id in seen_titles.items():
                    if title_similarity(title_key, seen_key) > 0.8:
                        dup_found = True
                        break

                if dup_found:
                    batch_dup += 1
                    continue

                seen_titles[title_key] = item_id

                # 噪音过滤
                if is_noise(item):
                    batch_noise += 1
                    continue

                # ── B站白名单过滤（仅处理SQL层未完全过滤的边界情况）──
                source_val = (item.get("source", "") or "").strip()
                platform_val = (item.get("platform", "") or "").strip()
                is_bilibili = ("bilibili" in source_val.lower() or "bilibili" in platform_val.lower()
                               or source_val.startswith("B站") or platform_val.startswith("B站"))

                if is_bilibili:
                    blocked = False
                    # 检查黑名单前缀 — 命中的直接过滤
                    for blk in BILIBILI_SOURCE_BLOCKLIST:
                        if source_val.startswith(blk) or platform_val.startswith(blk):
                            blocked = True
                            break
                    if blocked:
                        batch_noise += 1
                        continue
                    # 不在黑名单，检查白名单
                    allowed = False
                    for wl in BILIBILI_SOURCE_WHITELIST_PREFIXES:
                        if source_val.startswith(wl) or platform_val.startswith(wl):
                            allowed = True
                            break
                    if not allowed:
                        # 检查title/category/tags是否有科技相关关键词
                        title = (item.get("title", "") or "").lower()
                        content = (item.get("content", "") or "").lower()
                        category = (item.get("category", "") or "").lower()
                        tags = (item.get("tags", "") or "").lower()
                        combined = f"{title} {content} {category} {tags}"
                        for kw in BILIBILI_CHANNEL_WHITELIST:
                            if kw.lower() in combined:
                                allowed = True
                                break
                    if not allowed:
                        batch_noise += 1
                        continue

                # 语言检测
                lang, chinese_ratio = detect_language(
                    item.get("title", "") + " " + (item.get("content", "") or "")
                )

                # AI相关性
                ai_related = calc_ai_related(item)

                # 个人偏好匹配
                personal_match = calc_personal_match(item)

                # 重要性评分
                item["_ai_related"] = ai_related
                importance_score = calc_importance_score(item)

                # 价值等级
                value_level = calc_value_level(importance_score)

                # 价值描述
                value_reasons = get_value_reasons(item)

                # 判断来源类型
                source_type = item.get("platform", "unknown")

                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                conn.execute("""
                    INSERT INTO cleaned_intelligence
                    (raw_id, title, content, url, source, platform, author, author_id,
                     category, tags, importance_score, value_level, value_reasons,
                     is_ai_related, language, chinese_ratio, is_processed,
                     published_at, collected_at, cleaned_at, agent,
                     personal_match_score, source_type)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    item_id,
                    item.get("title", "")[:500],
                    item.get("content", "")[:2000],
                    item.get("url", ""),
                    item.get("source", ""),
                    item.get("platform", ""),
                    item.get("author", ""),
                    item.get("author_id", ""),
                    item.get("category", ""),
                    item.get("tags", ""),
                    importance_score,
                    value_level,
                    value_reasons,
                    ai_related,
                    lang,
                    chinese_ratio,
                    1,
                    item.get("published_at", ""),
                    item.get("collected_at", ""),
                    now,
                    "unified_cleaning_pipeline",
                    personal_match,
                    source_type,
                ))

                batch_new += 1

            except Exception as e:
                log.error(f"清洗失败 id={item.get('id', '?')}: {e}")
                batch_err += 1

        conn.commit()

        stats["total_processed"] += len(rows)
        stats["new_cleaned"] += batch_new
        stats["duplicates"] += batch_dup
        stats["noise_filtered"] += batch_noise
        stats["error"] += batch_err
        stats["batches_run"] = batch_num

        log.info(f"批次{batch_num}完成: +{batch_new} cleaned, {batch_dup} dup, {batch_noise} noise, {batch_err} err")

        # 如果这一批实际清洗量很少(全是噪音/重复)，或者达到最大批次，可以提前退出
        if batch_new == 0 and batch_num >= 3:
            log.warning("连续批次无新数据，提前结束")
            break

    # 更新趋势追踪
    _update_trends(conn)

    # 统计剩余未处理
    cur = conn.execute("""
        SELECT COUNT(*) FROM raw_intelligence r
        WHERE r.id NOT IN (
            SELECT COALESCE(c.raw_id, 0) FROM cleaned_intelligence c WHERE c.raw_id IS NOT NULL
        )
    """)
    stats["remaining"] = cur.fetchone()[0]

    conn.close()

    log.info(f"清洗完成: {stats}")
    return stats


def _update_trends(conn):
    """更新热点趋势"""
    # 提取近期高热词
    cur = conn.execute("""
        SELECT title, platform, importance_score, url
        FROM cleaned_intelligence
        WHERE datetime(cleaned_at) >= datetime('now', '-3 days')
          AND importance_score >= 50
        ORDER BY importance_score DESC
        LIMIT 50
    """)

    keywords_count = {}
    for row in cur.fetchall():
        title = row[0] or ""
        score = row[2]
        url = row[3]

        # 简单关键词提取
        for kw in ["AI", "LLM", "GPT", "Claude", "GitHub", "开源", "模型", "Agent", "MCP"]:
            if kw.lower() in title.lower():
                if kw not in keywords_count:
                    keywords_count[kw] = {"count": 0, "total_score": 0, "url": url}
                keywords_count[kw]["count"] += 1
                keywords_count[kw]["total_score"] += score

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for kw, data in keywords_count.items():
        if data["count"] >= 3:
            cur = conn.execute("SELECT id FROM trend_tracking WHERE keyword=?", (kw,))
            existing = cur.fetchone()

            if existing:
                conn.execute("""
                    UPDATE trend_tracking
                    SET hit_count=hit_count+1, hit_days=hit_days+1,
                        importance_score=?, last_seen=?, updated_at=?,
                        is_hot=CASE WHEN hit_count > 10 THEN 1 ELSE is_hot END
                    WHERE keyword=?
                """, (data["total_score"], now, now, kw))
            else:
                conn.execute("""
                    INSERT INTO trend_tracking
                    (keyword, title, source, platform, importance_score,
                     first_seen, last_seen, hit_days, hit_count, is_hot, status, url)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (kw, f"热点话题: {kw}", "cleaned_intelligence", "mixed",
                      data["total_score"], now, now, 1, data["count"], 1, "active", data["url"]))


# ── CLI ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Hermes 情报清洗管道")
    parser.add_argument("--batch", type=int, default=2000, help="每批大小 (默认2000)")
    parser.add_argument("--max-batches", type=int, default=100, help="最大批次数 (默认100)")
    parser.add_argument("--order-by-hot", action="store_true", help="按热度排序而非id顺序")
    args = parser.parse_args()

    result = clean_batch(batch_size=args.batch, max_batches=args.max_batches, order_by_id=not args.order_by_hot)
    print(f"清洗结果: {json.dumps(result, ensure_ascii=False, indent=2)}")
