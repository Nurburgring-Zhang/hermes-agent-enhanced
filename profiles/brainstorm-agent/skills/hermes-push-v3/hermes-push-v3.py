#!/usr/bin/env python3
"""
Hermes 智能推送系统 v3.0
=======================
仅基于真正的AI六维评分做推送。拒绝播放量×系数伪评分。

核心原则：
1. 推送候选必须来自AI评分结果(ai_score_total>0且ai_score_reasoning!='')
2. 如果AI评分不足→调用AI评分引擎先评分再推送
3. 禁止降级到v2伪评分（播放量×系数）
4. 按平台均衡取TOP15（每个平台最多取15条）
5. 推送结果记录到push_history

使用方式：
  python3 hermes_push_v3.py              # 正常推送
  python3 hermes_push_v3.py --dry-run    # 只看不推
  python3 hermes_push_v3.py --status     # 查看推送状态
"""

import json
import logging
import sqlite3
import subprocess
import sys
import time
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path

HERMES = Path.home() / ".hermes"
DB_PATH = HERMES / "intelligence.db"
LOG_DIR = HERMES / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / f"push_v3_{date.today().strftime('%Y%m%d')}.log"
OUTPUT_DIR = HERMES / "cron" / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler(LOG_FILE, encoding="utf-8"), logging.StreamHandler()]
)
log = logging.getLogger("push_v3")

# ── PushPlus配置 ───────────────────────────────────
PUSHPLUS_URL = "https://www.pushplus.plus/send"

def get_pushplus_token() -> str:
    """从config.yaml读取PushPlus token"""
    try:
        import yaml
        cfg_path = HERMES / "config.yaml"
        if cfg_path.exists():
            with open(cfg_path) as f:
                cfg = yaml.safe_load(f)
            token = cfg.get("pushplus", {}).get("token", "")
            if token:
                return token
    except Exception as e:
        log.warning(f"从config.yaml读token失败: {e}")
    # 回退：从state.db读
    try:
        conn = sqlite3.connect(str(HERMES / "state.db"))
        row = conn.execute("SELECT value FROM config WHERE key='pushplus_token'").fetchone()
        conn.close()
        if row:
            return row[0]
    except Exception as e:
        log.warning(f"从state.db读token失败: {e}")
    # 终极回退：从config.json读
    try:
        import json as _json
        with open(HERMES / "config.json") as f:
            cfg = _json.load(f)
        return cfg.get("pushplus", {}).get("token", "")
    except:
        pass
    return ""


def push_to_wechat(title: str, content: str, token: str = None) -> bool:
    """通过PushPlus推送消息到微信"""
    if token is None:
        token = get_pushplus_token()
    if not token:
        log.error("❌ PushPlus token未配置")
        return False

    import urllib.request
    data = json.dumps({
        "token": token,
        "title": title[:64],
        "content": content,
        "template": "markdown",
        "topic": "Hermes情报",
    }).encode("utf-8")

    req = urllib.request.Request(
        PUSHPLUS_URL,
        data=data,
        headers={"Content-Type": "application/json"}
    )

    try:
        resp = urllib.request.urlopen(req, timeout=15)
        body = resp.read().decode()
        result = json.loads(body)
        if result.get("code") == 200:
            log.info(f"✅ PushPlus推送成功: {title[:40]}")
            return True
        log.error(f"❌ PushPlus推送失败: {result.get('msg', body)}")
        return False
    except Exception as e:
        log.error(f"❌ PushPlus请求异常: {e}")
        return False


def get_ai_scored_items(min_score: int = 30, max_days: int = 2, limit_per_platform: int = 15,
                         total_limit: int = 200) -> list[dict]:
    """
    获取真正AI评分过的条目（禁止降级！必须有reasoning）
    """
    conn = sqlite3.connect(str(DB_PATH))
    cutoff = (datetime.now() - timedelta(days=max_days)).strftime("%Y-%m-%d %H:%M:%S")

    # 关键过滤条件：必须有真正的AI评分 (ai_score_reasoning != '')
    rows = conn.execute("""
        SELECT id, title, content, url, source, platform,
               ai_score_total, ai_score_scarcity, ai_score_impact,
               ai_score_tech_depth, ai_score_timeliness, ai_score_preference, ai_score_credibility,
               ai_score_reasoning, ai_scored_at
        FROM cleaned_intelligence
        WHERE ai_score_total >= ?
          AND (published_at IS NULL OR published_at >= ?)
          AND ai_score_reasoning != ''
          AND ai_score_reasoning IS NOT NULL
        ORDER BY ai_score_total DESC
    """, (min_score, cutoff)).fetchall()

    cols = ["id", "title", "content", "url", "source", "platform",
            "ai_score_total", "scarcity", "impact", "tech_depth",
            "timeliness", "preference", "credibility", "reasoning", "scored_at"]

    items = []
    for row in rows:
        d = dict(zip(cols, row))
        d["ai_score_total"] = d["ai_score_total"] or 0
        items.append(d)

    conn.close()

    # 按平台均衡：每个平台最多取limit_per_platform条
    platform_count = Counter()
    balanced = []
    for item in items:
        p = item.get("platform", "unknown")
        if platform_count[p] < limit_per_platform:
            balanced.append(item)
            platform_count[p] += 1
        if len(balanced) >= total_limit:
            break

    log.info(f"AI评分候选: {len(items)}条 → 平台均衡后: {len(balanced)}条")
    return balanced


def get_push_history(max_days: int = 1) -> set:
    """获取最近已推送的标题（去重）"""
    conn = sqlite3.connect(str(DB_PATH))
    cutoff = (datetime.now() - timedelta(days=max_days)).strftime("%Y-%m-%d %H:%M:%S")
    rows = conn.execute(
        "SELECT title FROM push_history WHERE pushed_at >= ?",
        (cutoff,)
    ).fetchall()
    conn.close()
    return {r[0].strip().lower() for r in rows if r[0]}


def record_push(items: list[dict]):
    """记录推送历史"""
    conn = sqlite3.connect(str(DB_PATH))
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for item in items:
        title = (item.get("title") or "")[:200]
        item_id = item.get("id", 0)
        try:
            conn.execute(
                "INSERT OR IGNORE INTO push_history (item_id, title, pushed_at, push_type) VALUES (?, ?, ?, ?)",
                (item_id, title, now, "ai_v3")
            )
        except:
            pass
    conn.commit()
    conn.close()
    log.info(f"✅ 已记录 {len(items)} 条推送历史")


def format_push_content(items: list[dict], title: str = "Hermes AI情报精选") -> str:
    """格式化推送内容为Markdown"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        f"# {title}",
        f"📅 {now} | 真正AI六维评分驱动",
        "",
    ]

    for i, item in enumerate(items[:20], 1):
        total = item.get("ai_score_total", 0)
        scarcity = item.get("scarcity", 0)
        impact = item.get("impact", 0)
        tech_depth = item.get("tech_depth", 0)
        timeliness = item.get("timeliness", 0)
        preference = item.get("preference", 0)
        credibility = item.get("credibility", 0)
        platform = item.get("platform", "unknown")
        title_text = (item.get("title") or "")[:80]
        summary = ""

        # 从reasoning中提取summary
        reasoning = item.get("reasoning") or ""
        if reasoning:
            try:
                r = json.loads(reasoning) if isinstance(reasoning, str) else reasoning
                summary = r.get("summary", "")[:80]
            except:
                pass

        score_str = f"稀缺{scarcity:.0f}+影响{impact:.0f}+技术{tech_depth:.0f}+时效{timeliness:.0f}+偏好{preference:.0f}+可信{credibility:.0f}"
        lines.append(f"**{i}. [{total:.0f}分] 『{platform}』{title_text}**")
        if summary:
            lines.append(f"> {summary}")
        lines.append(f"`{score_str}`")
        lines.append("")

    lines.append("---")
    lines.append("Powered by Hermes AI 六维评分引擎 v3.0")
    return "\n".join(lines)


def run_ai_scoring():
    """触发AI评分引擎评分（如果没有足够已评分条目）"""
    log.info("触发AI评分引擎...")
    try:
        r = subprocess.run(
            ["python3", str(HERMES / "scripts" / "hermes_ai_scorer_v2.py")],
            capture_output=True, text=True, timeout=60, cwd=str(HERMES)
        )
        log.info(f"评分引擎输出: {r.stdout[-500:]}")
        if r.returncode != 0:
            log.warning(f"评分引擎异常: {r.stderr[-200:]}")
    except Exception as e:
        log.error(f"触发评分引擎失败: {e}")


def run_collection():
    """触发采集（确保有足够数据）"""
    log.info("触发快速采集...")
    try:
        r = subprocess.run(
            ["python3", str(HERMES / "scripts" / "hermes_fast_pipeline.py"), "--collect", "--parallel", "6"],
            capture_output=True, text=True, timeout=300, cwd=str(HERMES)
        )
        log.info(f"采集输出: {r.stdout[-300:]}")
    except Exception as e:
        log.error(f"采集失败: {e}")


def run_cleaning():
    """触发清洗"""
    log.info("触发清洗管道...")
    try:
        r = subprocess.run(
            ["python3", str(HERMES / "scripts" / "unified_cleaning_pipeline.py"),
             "--newest-first", "--max-batches", "5"],
            capture_output=True, text=True, timeout=300, cwd=str(HERMES)
        )
        log.info(f"清洗输出: {r.stdout[-300:]}")
    except Exception as e:
        log.error(f"清洗失败: {e}")


def status() -> dict:
    """查看推送系统状态"""
    conn = sqlite3.connect(str(DB_PATH))

    # AI评分统计
    scored = conn.execute("SELECT COUNT(*) FROM cleaned_intelligence WHERE ai_score_total > 0 AND ai_score_reasoning != ''").fetchone()[0]
    pending = conn.execute("SELECT COUNT(*) FROM cleaned_intelligence WHERE ai_score_total IS NULL OR ai_score_total = 0 OR ai_score_reasoning = ''").fetchone()[0]

    # 今日推送统计
    today = date.today().strftime("%Y-%m-%d")
    pushed_today = conn.execute("SELECT COUNT(*) FROM push_history WHERE pushed_at >= ?", (today,)).fetchone()[0]

    # 今日可推送
    cutoff = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S")
    pushable = conn.execute("""
        SELECT COUNT(*) FROM cleaned_intelligence
        WHERE ai_score_total >= 30
          AND (published_at IS NULL OR published_at >= ?)
          AND ai_score_reasoning != ''
    """, (cutoff,)).fetchone()[0]

    # 高分分布
    high = conn.execute("SELECT COUNT(*) FROM cleaned_intelligence WHERE ai_score_total >= 70").fetchone()[0]
    med = conn.execute("SELECT COUNT(*) FROM cleaned_intelligence WHERE ai_score_total >= 40 AND ai_score_total < 70").fetchone()[0]

    # TOP5
    top5 = conn.execute("""
        SELECT id, title, ai_score_total, platform FROM cleaned_intelligence
        WHERE ai_score_total > 0 AND ai_score_reasoning != ''
        ORDER BY ai_score_total DESC LIMIT 5
    """).fetchall()

    conn.close()

    return {
        "scored_true_ai": scored,
        "pending": pending,
        "pushed_today": pushed_today,
        "pushable_now": pushable,
        "high_score": high,
        "medium_score": med,
        "top5": [{"id": r[0], "title": r[1][:40], "score": r[2], "platform": r[3]} for r in top5],
    }


def main():
    if "--status" in sys.argv:
        s = status()
        print("📊 推送系统状态:")
        print(f"  真正AI已评分: {s['scored_true_ai']}")
        print(f"  待评分: {s['pending']}")
        print(f"  今日已推送: {s['pushed_today']}")
        print(f"  当前可推送: {s['pushable_now']}")
        print(f"  High(70+): {s['high_score']} | Medium(40-69): {s['medium_score']}")
        print("\n  TOP5:")
        for t in s["top5"]:
            print(f"    #{t['id']} [{t['platform']}] → {t['score']:.0f}分 {t['title']}")
        return

    dry_run = "--dry-run" in sys.argv
    log.info("=" * 60)
    log.info("🚀 Hermes AI推送系统 v3.0 启动")
    log.info(f"  模式: {'🔄 DRY RUN (仅预览)' if dry_run else '▶️ 正常推送'}")

    # 步骤1: 检查AI评分覆盖情况
    scored = status()
    log.info("\n📊 步骤1: AI评分覆盖检查")
    log.info(f"  真正AI评分条目: {scored['scored_true_ai']} | 可推送: {scored['pushable_now']}")

    # 步骤2: 如果可推送条目不足，触发采集+清洗+评分
    if scored["pushable_now"] < 10:
        log.info("\n🔔 步骤2: AI评分条目不足，触发全链路")

        # 2a: 采集
        log.info("  2a: 采集最新数据...")
        run_collection()

        # 2b: 清洗
        log.info("  2b: 清洗数据...")
        run_cleaning()

        # 2c: AI评分
        log.info("  2c: 执行AI评分...")
        run_ai_scoring()

        # 给delegate_task一些时间
        log.info("  等待5秒...")
        time.sleep(5)

        # 重新检查
        scored = status()
        log.info(f"  重新检查: 真正AI评分={scored['scored_true_ai']} | 可推送={scored['pushable_now']}")

    # 步骤3: 获取可推送条目
    log.info("\n🎯 步骤3: 获取AI评分候选")
    items = get_ai_scored_items(min_score=30, max_days=2, limit_per_platform=15)

    if not items and scored["pushable_now"] >= 10:
        # 可能是过滤太严，放宽条件
        items = get_ai_scored_items(min_score=20, max_days=3, limit_per_platform=20)
        log.info(f"  放宽条件后: {len(items)} 条")

    if not items:
        log.warning("⚠️ 没有可推送条目")
        print("NO_PUSHABLE_ITEMS")
        return

    # 步骤4: 去重（排除已推送的）
    log.info("\n🔄 步骤4: 去重")
    already_pushed = get_push_history(max_days=1)
    deduped = []
    for item in items:
        title = (item.get("title") or "").strip().lower()
        if title and title not in already_pushed:
            deduped.append(item)
        else:
            log.info(f"  去重排除(已推送): {item.get('title','')[:40]}")

    log.info(f"  去重后: {len(deduped)} 条 (排除 {len(items)-len(deduped)} 条)")

    if not deduped:
        log.warning("⚠️ 去重后无可用条目")
        print("ALL_DEDUPED")
        return

    # 步骤5: 格式化推送内容
    log.info("\n📝 步骤5: 格式化推送内容")
    items_to_push = deduped[:20]

    # 生成推送内容（带六维评分详情）
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        "# 🤖 Hermes AI情报精选",
        f"📅 {now} | 真正AI六维评分驱动 | 共{len(items_to_push)}条",
        "",
    ]

    for i, item in enumerate(items_to_push, 1):
        total = item.get("ai_score_total", 0)
        title_text = (item.get("title") or "")[:80]
        platform = item.get("platform", "unknown")
        scarcity = item.get("scarcity", 0)
        impact = item.get("impact", 0)
        tech = item.get("tech_depth", 0)
        time_v = item.get("timeliness", 0)
        pref = item.get("preference", 0)
        cred = item.get("credibility", 0)

        summary = ""
        reasoning = item.get("reasoning") or ""
        if reasoning:
            try:
                r = json.loads(reasoning) if isinstance(reasoning, str) else reasoning
                summary = r.get("summary", "")[:80]
            except:
                pass

        star = "⭐" if total >= 70 else "🔥" if total >= 50 else "📌"
        lines.append(f"**{i}. {star}[{total:.0f}分]『{platform}』{title_text}**")
        if summary:
            lines.append(f"> {summary}")
        lines.append(f"`稀缺{scarcity:.0f} 影响{impact:.0f} 技术{tech:.0f} 时效{time_v:.0f} 偏好{pref:.0f} 可信{cred:.0f}`")
        lines.append("")

    lines.append("---")
    lines.append("*💡 评分标准：稀缺性0-30 + 影响力0-30 + 技术深度0-20 + 时效性0-10 + 偏好匹配0-10 + 来源可信度0-10*")
    lines.append("*Powered by Hermes AI 六维评分引擎 v3.0*")

    content = "\n".join(lines)

    # 也生成简洁版（只包含标题和评分）
    simple_lines = [
        "# 🤖 Hermes AI情报精选",
        f"📅 {now} | 共{len(items_to_push)}条",
        "",
    ]
    for i, item in enumerate(items_to_push, 1):
        total = item.get("ai_score_total", 0)
        title_text = (item.get("title") or "")[:80]
        platform = item.get("platform", "unknown")
        star = "⭐" if total >= 70 else "🔥" if total >= 50 else ""
        simple_lines.append(f"{i}. {star}[{total:.0f}分/{platform}] {title_text}")
    simple_lines.append("")
    simple_lines.append("---")
    simple_lines.append("*Powered by Hermes AI 六维评分引擎 v3.0*")
    simple_content = "\n".join(simple_lines)

    # 保存到文件
    output_path = OUTPUT_DIR / f"push_v3_{date.today().strftime('%Y%m%d_%H%M')}.md"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)
    log.info(f"  推送内容已保存: {output_path}")

    if dry_run:
        log.info("\n🔍 DRY RUN模式 — 不推送")
        print(content)
        return

    # 步骤6: 推送
    log.info("\n📤 步骤6: 推送微信")
    success = push_to_wechat(
        f"Hermes AI情报精选 ({now.split()[0]})",
        simple_content  # 推送简洁版到微信
    )

    if success:
        # 记录推送历史
        record_push(items_to_push)
        log.info(f"✅ 推送成功! 共{len(items_to_push)}条")
    else:
        log.error("❌ 推送失败")

    print(f"PUSH_RESULT:{'SUCCESS' if success else 'FAILED'}")
    print(f"ITEMS:{len(items_to_push)}")


if __name__ == "__main__":
    main()
