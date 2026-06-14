#!/usr/bin/env python3
"""
hv_analysis.py — 横纵分析法 (Horizontal-Vertical Analysis) 执行引擎
基于数字生命卡兹克 (KKKKhazik) 开源方法论

集成到 Hermes 情报管线：采集 → hv-analysis → 六维评分 → 推送

用法：
  python3 hv_analysis.py --topic "大模型" --days 180
  python3 hv_analysis.py --topic "自动驾驶" --days 365 --push
  python3 hv_analysis.py --topic "AI芯片" --db-only
"""
import argparse
import json
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

DB_PATH = str(Path.home() / ".hermes" / "intelligence.db")
SCRIPT_DIR = Path(__file__).parent
TEMPLATE_DIR = SCRIPT_DIR.parent / "templates"


def delegate_task(prompt: str) -> str:
    """委托分析任务给内部 DeepSeek 模型

    通过 stdin/stdout 与主进程通信，由主进程的 delegate_task 机制实际执行。
    此函数为接口占位，实际执行依赖 Hermes 框架的异步任务调度。
    """
    # 实际调用由外部 Hermes 框架注入
    print(f"[delegate_task] Prompt length: {len(prompt)} chars", file=sys.stderr)
    return ""


def fetch_intelligence(topic: str, days: int = 90, limit: int = 50) -> list:
    """从 intelligence.db 获取主题相关情报

    Args:
        topic: 搜索主题关键词
        days: 回溯天数
        limit: 最大返回条数

    Returns:
        list of dict: [{"id", "title", "content", "source", "created_at", "summary"}, ...]
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        cursor = conn.execute("""
            SELECT id, title, content, source, created_at, summary
            FROM cleaned_intelligence
            WHERE (title LIKE ? OR content LIKE ?)
              AND created_at >= datetime('now', ?)
            ORDER BY created_at DESC
            LIMIT ?
        """, (f"%{topic}%", f"%{topic}%", f"-{days} days", limit))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def fetch_high_score_intelligence(min_score: int = 70, hours: int = 24, limit: int = 20) -> list:
    """获取高分情报数据

    Args:
        min_score: 最低六维评分
        hours: 回溯小时数
        limit: 最大返回条数
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        cursor = conn.execute("""
            SELECT c.id, c.title, c.content, c.source, c.created_at, c.summary,
                   s.total_score, s.scores_detail
            FROM cleaned_intelligence c
            JOIN intelligence_scores s ON c.id = s.item_id
            WHERE s.total_score >= ?
              AND c.created_at >= datetime('now', ?)
            ORDER BY s.total_score DESC
            LIMIT ?
        """, (min_score, f"-{hours} hours", limit))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def build_analysis_prompt(topic: str, data: list) -> str:
    """构建 hv-analysis 的 prompt

    包含：
    - hv-analysis 核心框架说明
    - 情报数据
    - 输出格式要求
    """
    data_json = json.dumps(data, ensure_ascii=False, indent=2, default=str)

    prompt = f"""你是一个顶级战略分析师，负责对主题进行横纵分析（Horizontal-Vertical Analysis）。

## 分析主题
{topic}

## 核心框架

### 第一维：纵向分析（时间维度）
回顾3-5年历史，识别关键转折点（政策/技术/事件），判断趋势外推vs结构性变化。
- 构建时间线：标注重要事件和时间节点
- 识别三类转折点：🔴政策转折 / 🔵技术转折 / 🟡事件转折
- 趋势判断：区分趋势外推（延续性）和结构性变化（范式转移）
- 多情景推演：乐观/中性/悲观三种可能

### 第二维：横向分析（空间维度）
同行业内不同玩家/不同区域/不同用户群体差异，标杆研究，产业链生态地图。
- 玩家地图：头部/腰部/长尾三层，各自定位、份额、优势
- 区域/市场对比（如适用）
- 用户/群体分层（如适用）
- 标杆案例：成功案例+失败案例，可迁移经验
- 产业链：上中下游全景，价值分布，关键瓶颈

### 第三维：竞争战略叠加
- 波特五力模型评估（供应商/买家/新进入者/替代品/同业竞争）
- SWOT分析
- 战略定位（成本领先/差异化/聚焦）
- 可持续护城河分析

## 可用情报数据
{data_json}

## 输出要求
请输出结构化的完整分析报告，包含以下四个部分：
1. 纵向分析（时间维度）
2. 横向分析（空间维度）
3. 竞争战略叠加
4. 结论与行动建议

使用清晰的Markdown格式，每个部分使用二级标题(##)，重要发现加粗或使用emoji标记。
每部分至少2-3个具体发现，避免泛泛而谈，基于情报数据给出有依据的分析。
"""
    return prompt


def store_report(topic: str, report: str, score: int = 0, data_sources: list = None):
    """存储分析报告到 hv_analysis_reports 表

    Args:
        topic: 分析主题
        report: 完整分析报告（markdown格式）
        score: 报告六维评分
        data_sources: 数据源ID列表
    """
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS hv_analysis_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic TEXT NOT NULL,
                report TEXT NOT NULL,
                score INTEGER DEFAULT 0,
                data_sources TEXT,
                related_reports TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            INSERT INTO hv_analysis_reports (topic, report, score, data_sources)
            VALUES (?, ?, ?, ?)
        """, (topic, report, score, json.dumps(data_sources or [], ensure_ascii=False)))
        conn.commit()
        print(f"[store] hv-analysis report stored: topic='{topic}', score={score}", file=sys.stderr)
    finally:
        conn.close()


def load_report_template(name: str) -> str:
    """加载报告模板

    Args:
        name: 模板文件名（不含路径）
    Returns:
        模板内容字符串，模板不存在时返回空字符串
    """
    template_path = TEMPLATE_DIR / name
    if template_path.exists():
        return template_path.read_text(encoding="utf-8")
    return ""


def push_summary_report(topic: str, report: str, score: int):
    """推送轻量版 hv-analysis 摘要到微信

    从完整报告中提取前500字作为摘要推送。
    完整报告存储在数据库中。
    """
    # 提取摘要：前500字
    summary = report[:500].strip()
    if len(report) > 500:
        summary += "..."

    lines = [
        f"📊 hv横纵分析 | {topic}",
        "────────────────",
        summary,
        "────────────────",
        f"评分: {score}/100 | 查看全文: hv_analysis_reports"
    ]
    msg = "\n".join(lines)

    try:
        # 尝试调用 PushPlus 推送
        from pushplus_wechat import push_to_wechat
        push_to_wechat(msg, title=f"hv横纵分析 | {topic}")
        print(f"[push] Sent to WeChat: topic='{topic}'", file=sys.stderr)
    except ImportError:
        print("[push] pushplus_wechat not available, printing to stdout:", file=sys.stderr)
        print(msg)
    except Exception as e:
        print(f"[push] Error: {e}", file=sys.stderr)
        print(msg)


def print_db_only(topic: str, days: int, limit: int):
    """仅从数据库检索情报，不执行分析

    用于预览可用的数据量，辅助判断是否值得执行完整分析。
    """
    data = fetch_intelligence(topic, days, limit)
    print("╔══════════════════════════════════════╗")
    print("║  hv-analysis 数据预览                 ║")
    print(f"║  主题: {topic}")
    print(f"║  回溯: {days}天")
    print(f"║  条数: {len(data)}")
    print("╚══════════════════════════════════════╝")
    print()
    for item in data:
        print(f"[{item.get('created_at', '?')[:10]}] {item['source']:>12s} | {item['title'][:60]}")
    print(f"\n共 {len(data)} 条数据")


def main():
    parser = argparse.ArgumentParser(
        description="hv-analysis 横纵分析引擎",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python3 hv_analysis.py --topic "大模型价格战" --days 180 --push
  python3 hv_analysis.py --topic "自动驾驶" --db-only
  python3 hv_analysis.py --topic "新能源电池" --days 365
        """
    )
    parser.add_argument("--topic", required=True, help="分析主题（关键词）")
    parser.add_argument("--days", type=int, default=90, help="回溯天数（默认90天）")
    parser.add_argument("--limit", type=int, default=50, help="最大数据条数（默认50）")
    parser.add_argument("--push", action="store_true", help="推送微信摘要")
    parser.add_argument("--db-only", action="store_true", help="仅检索数据库预览，不执行分析")
    parser.add_argument("--score", type=int, default=0, help="人工指定六维评分（可选）")
    args = parser.parse_args()

    # 仅数据预览模式
    if args.db_only:
        print_db_only(args.topic, args.days, args.limit)
        return

    # 获取情报数据
    print(f"[hv-analysis] 开始分析: topic='{args.topic}', days={args.days}", file=sys.stderr)
    data = fetch_intelligence(args.topic, args.days, args.limit)
    if not data:
        print(f"[hv-analysis] ⚠️  主题 '{args.topic}' 没有找到情报数据", file=sys.stderr)
        print("[hv-analysis] 建议: 扩大回溯天数(--days)或先执行采集", file=sys.stderr)
        sys.exit(1)

    print(f"[hv-analysis] 获取到 {len(data)} 条情报数据", file=sys.stderr)

    # 构建提示
    prompt = build_analysis_prompt(args.topic, data)
    print(f"[hv-analysis] Prompt 长度: {len(prompt)} 字符", file=sys.stderr)

    # 执行分析（通过 delegate_task）
    report = delegate_task(prompt)

    # 如果 delegate_task 返回空（占位实现），生成基本报告结构
    if not report:
        report = generate_basic_report(args.topic, data)
        print("[hv-analysis] 使用本地生成的基本报告（delegate_task不可用）", file=sys.stderr)

    # 评分
    score = args.score if args.score > 0 else estimate_report_quality(data)

    # 存储
    store_report(args.topic, report, score, [d.get("id") for d in data])

    # 推送
    if args.push:
        push_summary_report(args.topic, report, score)

    # 输出报告
    print(report)


def generate_basic_report(topic: str, data: list) -> str:
    """当 delegate_task 不可用时，生成本地基本报告框架

    这是一个 fallback 实现，仅提供报告模板框架，
    delegate_task 正常时应优先使用 AI 驱动的分析。
    """
    sources = set(d.get("source", "?") for d in data)
    dates = [d.get("created_at", "?")[:10] for d in data if d.get("created_at")]

    lines = []
    lines.append("# hv-analysis 横纵分析报告")
    lines.append("")
    lines.append(f"**主题**: {topic}")
    lines.append(f"**日期**: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"**数据源**: {', '.join(sorted(sources))}")
    lines.append(f"**数据量**: {len(data)} 条")
    if dates:
        lines.append(f"**时间范围**: {min(dates)} ~ {max(dates)}")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 一、纵向分析（时间维度）")
    lines.append("")
    lines.append("### 历史时间线")
    for item in data:
        lines.append(f"- {item.get('created_at', '?')[:10]} | {item['title'][:60]}")
    lines.append("")
    lines.append("### 关键转折点识别")
    lines.append("> ⚠️ 需要 delegate_task(AI) 实际执行分析才能识别转折点")
    lines.append("")
    lines.append("### 趋势判断")
    lines.append("> ⚠️ 需要 delegate_task(AI) 实际执行趋势分析")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 二、横向分析（空间维度）")
    lines.append("")
    lines.append("### 玩家地图")
    for item in data[:10]:
        lines.append(f"- [{item.get('source', '?')}] {item['title'][:60]}")
    lines.append("")
    lines.append("### 产业链生态")
    lines.append("> ⚠️ 需要 delegate_task(AI) 实际执行产业链分析")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 三、竞争战略叠加")
    lines.append("> ⚠️ 需要 delegate_task(AI) 实际执行波特五力/SWOT分析")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 四、结论与行动建议")
    lines.append("> ⚠️ 需要 delegate_task(AI) 实际执行洞察提取和建议生成")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(f"*分析完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
    lines.append("*⚠️ 本报告为本地 fallback 版本，请使用 delegate_task 获取AI深度分析版本*")

    return "\n".join(lines)


def estimate_report_quality(data: list) -> int:
    """基于数据量和多样性估算分析质量评分（0-100）

    这是一个替代六维评分的简易版本。
    完整六维评分应走 ai-six-dimension-scoring-pipeline。
    """
    score = 50  # 基础分
    # 数据量加分
    if len(data) >= 30:
        score += 20
    elif len(data) >= 15:
        score += 10
    elif len(data) >= 5:
        score += 5
    # 来源多样性加分
    sources = set(d.get("source", "") for d in data)
    if len(sources) >= 5:
        score += 15
    elif len(sources) >= 3:
        score += 8
    # 时间跨度加分
    dates = [d.get("created_at", "")[:10] for d in data if d.get("created_at")]
    if dates:
        span = (datetime.strptime(max(dates), "%Y-%m-%d") -
                datetime.strptime(min(dates), "%Y-%m-%d")).days
        if span >= 180:
            score += 15
        elif span >= 90:
            score += 10
        elif span >= 30:
            score += 5
    return min(score, 100)


if __name__ == "__main__":
    main()
