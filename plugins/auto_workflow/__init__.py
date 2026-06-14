"""
Hermes Workflow 自动触发插件
=============================
通过 post_llm_call hook，在每次用户消息处理后自动将用户消息写入 workflow 待处理队列。

写入的 workflow 由 daemon 后台消费执行（不阻塞主Agent）。
"""

import json
import os
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERMES_HOME = Path(os.environ.get("HERMES_HOME", os.path.expanduser("~/.hermes")))

def register(ctx):
    """插件注册 — Hermes 主Agent启动时自动调用"""
    ctx.register_hook("post_llm_call", auto_workflow_hook)

    # 初始化数据库表
    _init_db()

    # 写入激活日志
    log_dir = HERMES_HOME / "logs" / "auto_workflow"
    log_dir.mkdir(parents=True, exist_ok=True)
    with open(log_dir / "plugin_activated.log", "a") as f:
        f.write(f"[{_now_ts()}] Workflow自动触发插件已激活\n")


def auto_workflow_hook(session_id="", user_message="", assistant_response="",
                       conversation_history=None, model="", platform="", **kwargs):
    """
    post_llm_call hook — 每次用户消息处理后自动调用
    
    把用户消息写入 workflow 待处理队列。
    不阻塞主Agent，写入后立即返回。
    """
    if not user_message or len(user_message.strip()) < 10:
        return  # 太短的消息跳过

    try:
        _init_db()

        conn = sqlite3.connect(str(HERMES_HOME / "workflow.db"))
        conn.execute("""
            CREATE TABLE IF NOT EXISTS auto_workflow_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                user_message TEXT,
                assistant_summary TEXT,
                model TEXT,
                platform TEXT,
                status TEXT DEFAULT 'pending',
                created_at TEXT,
                processed_at TEXT,
                workflow_id TEXT,
                error TEXT
            )
        """)

        # 提取 assistant 响应的摘要（前200字）
        assistant_summary = ""
        if assistant_response:
            assistant_summary = assistant_response.strip()[:200]

        conn.execute(
            """INSERT INTO auto_workflow_queue 
               (session_id, user_message, assistant_summary, model, platform, status, created_at)
               VALUES (?, ?, ?, ?, ?, 'pending', ?)""",
            (session_id[:20], user_message[:500], assistant_summary,
             str(model)[:30], str(platform)[:20], _now_ts())
        )
        conn.commit()
        conn.close()

        # 写入日志
        log_dir = HERMES_HOME / "logs" / "auto_workflow"
        log_dir.mkdir(parents=True, exist_ok=True)
        with open(log_dir / "queue.log", "a") as f:
            f.write(f"[{_now_ts()}] 入队: {user_message[:60]}... | session={session_id[:16]}\n")

    except Exception as e:
        log_dir = HERMES_HOME / "logs" / "auto_workflow"
        log_dir.mkdir(parents=True, exist_ok=True)
        with open(log_dir / "error.log", "a") as f:
            f.write(f"[{_now_ts()}] 错误: {e}\n")


def _init_db():
    """初始化数据库"""
    conn = sqlite3.connect(str(HERMES_HOME / "workflow.db"))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS auto_workflow_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            user_message TEXT,
            assistant_summary TEXT,
            model TEXT,
            platform TEXT,
            status TEXT DEFAULT 'pending',
            created_at TEXT,
            processed_at TEXT,
            workflow_id TEXT,
            error TEXT
        )
    """)
    conn.commit()
    conn.close()


def _now_ts():
    return datetime.now(timezone(timedelta(hours=8))).isoformat()
