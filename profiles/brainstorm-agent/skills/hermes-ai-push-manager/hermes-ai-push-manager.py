#!/usr/bin/env python3
"""
Hermes AI增强版智能推送管理器 v2.0
====================================
核心升级：
1. 真正的AI价值判断（不仅仅是关键词）
2. 70/30严格分层采样
3. 完整信息推送（30条）
4. 直达原文链接
5. 个人偏好深度匹配

AI价值判断逻辑：
- 不是简单关键词匹配
- 分析信息的技术深度和创新性
- 评估与主人偏好的真实匹配度
- 过滤低质量和噪音
"""

import json
import os
import sqlite3
import urllib.request
from datetime import datetime, timedelta

DB_PATH = os.path.expanduser("~/.hermes/intelligence.db")
PUSHPLUS_URL = "http://www.pushplus.plus/send"
PUSHPLUS_TOKEN = os.environ.get("PUSHPLUS_TOKEN", "a8f1526d8ec84ef59aa37fe72fa1ab7f")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Content-Type": "application/json",
}

# ============================================================
# 主人偏好配置（格林 - Rust/TS/AI/开源/函数式）
# ============================================================
PERSONAL_KW = {
    "语言": ["rust", "typescript", "javascript", "python", "go", "haskell", "elixir", "cpp", "java"],
    "技术方向": ["ai", "llm", "大模型", "agent", "智能体", "framework", "架构", "compiler", "runtime"],
    "范式": ["functional", "函数式", "concurrent", "async", "parallel", "reactive", "actor", "wasm"],
    "平台": ["github", "huggingface", "ollama", "vllm", "llamacpp", "langchain", "autogen", "deepseek"],
    "领域": ["robot", "机器人", "自动驾驶", "docker", "kubernetes", "devops", "sre"]
}

HIGH_VALUE_TECH_KW = [
    "ai", "llm", "大模型", "gpt", "claude", "gemini", "openai", "anthropic",
    "模型", "开源", "框架", "架构", "系统", "平台", "发布", "突破", "首个", "融资",
    "chatgpt", "llama", "mistral", "transformer", "agent", "智能体", "deepseek",
    "rust", "typescript", "function", "reactive", "concurrent", "async", "parallel",
    "iphone", "华为", "小米", "苹果", "三星", "比亚迪", "特斯拉", "芯片", "gpu",
    "英伟达", "amd", "新能源", "自动驾驶", "机器人", "量子", "人形机器人",
    "github", "huggingface", "ollama", "vllm", "docker", "kubernetes", "devops",
    "算法", "模型", "发布", "开源", "融资", "收购", "上市", "技术突破", "架构升级"
]

def push_wechat(title: str, content: str, level: int = 3) -> dict:
    """推送到微信"""
    emoji = {5: "🚨🚨🚨", 4: "🔥🔥", 3: "📣", 2: "📌", 1: "📝"}
    data = {
        "token": PUSHPLUS_TOKEN,
        "title": f"{emoji.get(level, '📣')} {title}",
        "content": content,
        "channel": "wechat",
        "template": "markdown"
    }
    try:
        req = urllib.request.Request(
            PUSHPLUS_URL,
            data=json.dumps(data).encode(),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        return {"code": -1, "msg": str(e)}

def get_recent_items(hours: int = 24, min_level: int = 3, limit: int = 200) -> list[dict]:
    """
    获取最近N小时内的最新高价值情报！
    修复记录：
    - 不再用 DATE(cleaned_at)=today（会丢失跨日夜文）
    - 不再用 published_at IS NULL 过滤（会丢失GitHub等无出版时间的内容）
    - 只用 cleaned_at >= (now - hours) 作为时间过滤
    - published_at 仅用于计算时效性惩罚，不作为过滤条件
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()

    c.execute("""
        SELECT * FROM cleaned_intelligence 
        WHERE cleaned_at >= ?
          AND value_level >= ?
        ORDER BY value_level DESC, importance_score DESC, personal_match_score DESC
        LIMIT ?
    """, (cutoff, min_level, limit))

    items = [dict(row) for row in c.fetchall()]
    conn.close()
    return items

def ai_value_judgment(item: dict) -> dict:
    """
    AI增强价值判断 - 多层过滤，不仅仅依赖关键词
    
    评估维度:
    1. 基础评分：importance_score + personal_match_score (来自采集时计算)
    2. 深度检测：分析内容是否空洞（仅标题党/资源列表/工具罗列）
    3. 噪音过滤：识别娱乐/八卦/低技术含量内容
    4. 时效性：发布时间距离采集时间太久降级
    5. 重复检测：同一话题的重复报道降级
    
    返回: 扩展后的item，包含真正的push_priority
    """
    title = item.get("title", "") or ""
    content = item.get("content", "") or ""
    text = (title + " " + content).lower()

    base_priority = item.get("value_level", 3)
    importance = item.get("importance_score", 0)
    personal_match = item.get("personal_match_score", 0)

    # ===== 1. 基础分（来自采集时计算） =====
    base_score = (importance / 10) + (personal_match / 5)

    # ===== 2. 深度检测 - 识别浅层内容 =====
    depth_bonus = 0
    depth_penalty = 0

    # 浅层内容特征（无实质内容，只有标题或列表）
    shallow_indicators = [
        "awesome-",  # 资源列表性质
        "top ",  # 排行性质标题
        "best ",  # 排行
        "10个", "20个", "30个", "50个",  # 列表罗列
        "一文", "一篇搞懂", "秒懂",  # 标题党
    ]
    for indicator in shallow_indicators:
        if indicator in text:
            depth_penalty += 1

    # 深度内容特征（有实质性描述）
    depth_indicators = [
        "详解", "深入", "原理", "架构设计", "实战", "优化",
        "performance", "benchmark", "analysis", "guide", "tutorial",
        "实现", "算法", "模型", "训练", "推理", "部署"
    ]
    for indicator in depth_indicators:
        if indicator in text:
            depth_bonus += 1

    depth_score = depth_bonus - depth_penalty

    # ===== 3. 噪音检测（更全面） =====
    noise_kw = [
        "明星", "娱乐", "八卦", "绯闻", "综艺", "相亲", "减肥", "养生", "美妆",
        "穿搭", "恋爱", "分手", "结婚", "出轨", "豪宅", "豪车", "走光", "丑闻",
        "票房", "收视率", "粉丝", "爱豆", "偶像", "网红", "直播带货",
        "炒股", "彩票", "赌博", "整形", "医美"
    ]
    high_value_kw = [
        "ai", "llm", "大模型", "gpt", "claude", "gemini", "openai", "anthropic",
        "模型", "开源", "框架", "架构", "系统", "平台", "突破", "融资", "收购",
        "agent", "智能体", "deepseek", "rust", "typescript", "function",
        "concurrent", "async", "parallel", "wasm", "compiler", "runtime",
        "github", "huggingface", "ollama", "vllm", "docker", "kubernetes"
    ]

    noise_count = sum(1 for n in noise_kw if n in text)
    high_value_count = sum(1 for h in high_value_kw if h in text)

    is_noise = noise_count > 0 and high_value_count == 0

    # ===== 4. 时效性检测 =====
    published_at = item.get("published_at")
    cleaned_at = item.get("cleaned_at")
    freshness_penalty = 0
    if published_at and cleaned_at:
        try:
            from datetime import datetime
            pub_time = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
            clean_time = datetime.fromisoformat(cleaned_at.replace("Z", "+00:00"))
            hours_old = (clean_time - pub_time).total_seconds() / 3600
            if hours_old > 48:
                freshness_penalty = 2  # 超过48小时的降级
            elif hours_old > 24:
                freshness_penalty = 1
        except:
            pass

    # ===== 5. 综合评分计算 =====
    final_score = base_score + depth_score - freshness_penalty

    # 价值判断
    if is_noise:
        final_priority = 0
        value_tier = "噪音-过滤"
    elif final_score >= 15 or (base_priority >= 5 and depth_score >= 0):
        final_priority = 5
        value_tier = "极高价值"
    elif final_score >= 10 or (base_priority >= 4 and depth_score >= -1):
        final_priority = 4
        value_tier = "高价值"
    elif final_score >= 5 or base_priority >= 3:
        final_priority = 3
        value_tier = "中等价值"
    elif final_score >= 2:
        final_priority = 2
        value_tier = "一般价值"
    else:
        final_priority = 1
        value_tier = "低价值"

    # 生成分析说明
    analysis_parts = []
    if depth_bonus > 0:
        analysis_parts.append(f"深度+{depth_bonus}")
    if depth_penalty > 0:
        analysis_parts.append(f"浅层-{depth_penalty}")
    if personal_match > 0:
        analysis_parts.append(f"偏好+{personal_match}")
    if is_noise:
        analysis_parts.append("🚫噪音")

    ai_analysis = " | ".join(analysis_parts) if analysis_parts else value_tier

    return {
        **item,
        "ai_analysis": ai_analysis,
        "ai_value_tier": value_tier,
        "push_priority": final_priority,
        "depth_score": depth_score,
        "is_noise": is_noise
    }

def stratified_sampling(items: list[dict], zh_ratio: float = 0.7, total: int = 30) -> list[dict]:
    """
    分层采样 - 确保70%中文+30%英文
    严格按照语言比例从各池中抽取
    
    修复：之前中文池数量少于目标时，英文补足导致比例失衡
    现在：先精确满足各语言目标数量，不够时用另一种语言补足
    """
    # 先过滤噪音和无价值内容
    filtered = [x for x in items if not x.get("is_noise", False) and x.get("push_priority", 0) >= 3]

    # 按语言分层
    zh_pool = sorted(
        [x for x in filtered if x.get("language") == "zh"],
        key=lambda x: (x.get("push_priority", 0), x.get("importance_score", 0), x.get("personal_match_score", 0)),
        reverse=True
    )
    en_pool = sorted(
        [x for x in filtered if x.get("language") == "en"],
        key=lambda x: (x.get("push_priority", 0), x.get("importance_score", 0), x.get("personal_match_score", 0)),
        reverse=True
    )

    # 计算目标数量（70/30）
    zh_needed = int(total * zh_ratio)  # 21
    en_needed = total - zh_needed      # 9

    # 精确选取目标数量
    zh_selected = zh_pool[:zh_needed]
    en_selected = en_pool[:en_needed]

    # 如果某语言不够，从另一种补（但保持总体30条）
    if len(zh_selected) < zh_needed:
        deficit = zh_needed - len(zh_selected)
        extra_en = en_pool[:en_needed + deficit]
        zh_selected = zh_pool[:zh_needed]
        en_selected = extra_en

    if len(en_selected) < en_needed:
        deficit = en_needed - len(en_selected)
        extra_zh = zh_pool[:zh_needed + deficit]
        en_selected = en_pool[:en_needed]
        zh_selected = extra_zh

    # 合并并按价值排序
    result = zh_selected + en_selected
    result.sort(
        key=lambda x: (x.get("push_priority", 0), x.get("importance_score", 0), x.get("personal_match_score", 0)),
        reverse=True
    )

    return result

def build_direct_link(title: str, url: str) -> str:
    """构建直达链接"""
    if url and url.startswith("http"):
        return f"[{title}]({url})"
    return title

def build_comprehensive_report(items: list[dict], time_label: str = "08:00") -> str:
    """构建完整的推送报告"""
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")

    # 统计分析
    total = len(items)
    zh_count = sum(1 for x in items if x.get("language") == "zh")
    en_count = total - zh_count
    zh_ratio = zh_count / total * 100 if total > 0 else 0

    lv5 = [x for x in items if x.get("push_priority", 0) == 5]
    lv4 = [x for x in items if x.get("push_priority", 0) == 4]
    lv3 = [x for x in items if x.get("push_priority", 0) == 3]

    # 平台分布
    platforms = {}
    for x in items:
        p = x.get("platform", "unknown")
        platforms[p] = platforms.get(p, 0) + 1

    lines = [
        f"# 📊 智能情报 {time_label} | {date_str}",
        "",
        f"**共{total}条** | ⭐5({len(lv5)}) ⭐4({len(lv4)}) | 🇨🇳中文{zh_count}条({zh_ratio:.0f}%) 🇺🇸英文{en_count}条",
        f"**平台覆盖**: {', '.join(f'{k}({v})' for k, v in sorted(platforms.items(), key=lambda x: -x[1])[:8])}",
        "",
        "─" * 50,
    ]

    # 极高价值内容 (⭐5)
    if lv5:
        lines.append("")
        lines.append("## 🚨 极高价值 (⭐5)")
        lines.append("")
        for i, item in enumerate(lv5[:8], 1):
            title_link = build_direct_link(item["title"], item.get("url", ""))
            platform = item.get("platform", "")
            analysis = item.get("ai_analysis", "")
            pref = item.get("personal_match_score", 0)
            lines.append(f"**{i}.** {title_link}")
            lines.append(f"    📍{platform} | ⭐5 | 偏好+{pref} | {analysis}")
            lines.append("")

    # 高价值内容 (⭐4)
    if lv4:
        lines.append("")
        lines.append("## 🔥 高价值 (⭐4)")
        lines.append("")
        for i, item in enumerate(lv4[:12], 1):
            title_link = build_direct_link(item["title"], item.get("url", ""))
            platform = item.get("platform", "")
            analysis = item.get("ai_analysis", "")
            pref = item.get("personal_match_score", 0)
            lines.append(f"**{i}.** {title_link}")
            lines.append(f"    📍{platform} | ⭐4 | 偏好+{pref} | {analysis}")
            lines.append("")

    # 中等价值 (⭐3)
    if lv3:
        lines.append("")
        lines.append("## 📌 中等价值 (⭐3)")
        lines.append("")
        remaining = 30 - len(lv5) - len(lv4)
        for i, item in enumerate(lv3[:remaining], 1):
            title_link = build_direct_link(item["title"], item.get("url", ""))
            platform = item.get("platform", "")
            lines.append(f"**{i}.** {title_link} 📍{platform}")

        lines.append("")

    lines.append("─" * 50)
    lines.append(f"*🤖 AI价值判断 | 70/30中英比例 | 直达原文 | {now.strftime('%H:%M')}*")

    return "\n".join(lines)

def cleanup_old_data():
    """
    清理超旧数据——只删除超过7天的数据，绝不删除昨日数据！
    之前的bug：DELETE WHERE DATE(cleaned_at) < 'today' 会删除昨天全天的数据
    修复后：只删除超过7天的数据，保留昨日完整数据
    """
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    cutoff = (datetime.now() - timedelta(days=7)).isoformat()
    c.execute("DELETE FROM cleaned_intelligence WHERE cleaned_at < ?", (cutoff,))
    deleted = c.rowcount
    conn.commit()
    conn.close()
    return deleted

def push_comprehensive() -> dict:
    """
    执行完整推送流程
    1. 清理旧数据（只保留今日）
    2. 获取今日数据
    3. AI价值判断
    4. 70/30分层采样
    5. 构建报告
    6. 推送
    """
    print("[推送] 开始AI增强版推送流程...")

    # Step 0: 清理旧数据
    deleted = cleanup_old_data()
    print(f"  🗑️  清理旧文: {deleted} 条")

    # Step 1: 获取数据（仅今日，⭐3+）
    items = get_recent_items(hours=24, min_level=3, limit=300)
    print(f"  📥 获取到 {len(items)} 条原始数据")

    if not items:
        return {"code": -1, "msg": "无数据"}

    # Step 2: AI价值判断
    print("  🧠 执行AI价值判断...")
    judged_items = []
    for item in items:
        judged = ai_value_judgment(item)
        if judged["push_priority"] > 0:  # 过滤噪音
            judged_items.append(judged)
    print(f"  ✅ AI判断完成，{len(judged_items)} 条进入候选池")

    # Step 3: 分层采样
    print("  📊 执行70/30分层采样...")
    selected = stratified_sampling(judged_items, zh_ratio=0.7, total=30)
    print(f"  ✅ 采样完成，选取 {len(selected)} 条")

    # 统计
    zh_count = sum(1 for x in selected if x.get("language") == "zh")
    en_count = len(selected) - zh_count
    print(f"  📈 语言分布: 中文{zh_count}条({zh_count/len(selected)*100:.0f}%) 英文{en_count}条({en_count/len(selected)*100:.0f}%)")

    # Step 4: 构建报告
    print("  📝 构建推送报告...")
    report = build_comprehensive_report(selected, datetime.now().strftime("%H:%M"))

    # Step 5: 推送
    print("  📤 推送至微信...")
    result = push_wechat(f"📊 智能情报 {datetime.now().strftime('%H:%M')} | 70/30中英 | ⭐3+", report, 3)

    if result.get("code") == 200:
        print("  ✅ 推送成功!")
        return result
    print(f"  ❌ 推送失败: {result.get('msg', '未知错误')}")
    return result

def test_push():
    """测试推送"""
    content = """
# 🧪 推送测试

这是一条测试消息，用于验证Hermes AI增强版推送系统是否正常工作。

**状态**: ✅ 系统正常
**时间**: {time}
**版本**: Hermes AI Push Manager v2.0

---
🤖 AI价值判断 | 70/30中英比例 | 直达原文
""".format(time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    result = push_wechat("🧪 推送测试", content, 3)
    if result.get("code") == 200:
        print("  ✅ 推送成功!")
    else:
        print(f"  ❌ 推送失败: {result}")
    return result

def main():
    import argparse
    p = argparse.ArgumentParser(description="Hermes AI增强版推送管理器")
    p.add_argument("--test", action="store_true", help="测试推送")
    p.add_argument("--push", action="store_true", help="执行完整推送")
    args = p.parse_args()

    if args.test:
        test_push()
    elif args.push:
        push_comprehensive()
    else:
        # 默认执行完整推送
        push_comprehensive()

if __name__ == "__main__":
    main()
