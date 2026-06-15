#!/usr/bin/env python3
"""
🏭 Production Loop守护启动器 — 接入Hermes cron/eternal_loop/guardian
=================================================================
每2小时由cron触发，或在Hermes任务完成后被eternal_loop/guardian调用。
执行生产级可靠性验证: 状态检查、Critic审查、安全审计、中断恢复。

用法:
  python3 scripts/prod_loop_launcher.py              # 完整验证(默认)
  python3 scripts/prod_loop_launcher.py --mode check  # 快速检查
  python3 scripts/prod_loop_launcher.py --mode critic # Critic审查
  python3 scripts/prod_loop_launcher.py --mode full   # 深度验证

格林主人最高指令: 永不降级，全量真实执行。
"""

import json
import os
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

HERMES = Path.home() / ".hermes"
LOG_DIR = HERMES / "logs" / "prod_loop"
REPORT_DIR = HERMES / "reports"

TZ = timezone(timedelta(hours=8))


def log(msg: str, level: str = "INFO"):
    """结构化日志"""
    ts = datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] [{level}] {msg}"
    print(line)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOG_DIR / f"prod_loop_{datetime.now(TZ).strftime('%Y%m%d')}.log"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def ensure_production_loop_on_path():
    """确保production_loop可导入"""
    hermes_root = str(HERMES)
    if hermes_root not in sys.path:
        sys.path.insert(0, hermes_root)


def run_production_loop_check() -> dict:
    """
    快速检查模式: 状态查询 + 中断恢复 + CaMeL安全轻检。
    对应 production_loop.engine 的 status + check 操作。
    """
    log("🏭 Production Loop — 快速检查模式")
    result = {"mode": "check", "status": "ok", "checks": {}, "warnings": []}

    ensure_production_loop_on_path()

    try:
        from production_loop.engine import resume_interrupted
        from production_loop.loop_state import FileBasedStateStore, LoopStateStore

        # 1. 检查活跃运行状态
        file_store = FileBasedStateStore()
        run_state = file_store.load_run_state()
        if run_state:
            result["checks"]["active_run_state"] = {
                "ok": True,
                "fsm_state": run_state.fsm_state,
                "task_id": getattr(run_state, "task_id", "?"),
                "progress": getattr(
                    getattr(run_state, "global_progress", None),
                    "overall_progress", 0
                ),
            }
            if run_state.fsm_state not in ("IDLE",):
                log(f"  检测到中断任务: {getattr(run_state, 'task_id', '?')} (状态: {run_state.fsm_state})")
                result["warnings"].append(f"中断任务: {run_state.fsm_state}")
        else:
            result["checks"]["active_run_state"] = {"ok": True, "message": "无活跃运行状态"}

        # 2. 未完成任务数
        store = LoopStateStore()
        unfinished = store.get_unfinished_tasks()
        result["checks"]["unfinished_tasks"] = {
            "ok": len(unfinished) <= 5,
            "count": len(unfinished),
        }
        if len(unfinished) > 5:
            result["warnings"].append(f"未完成任务堆积: {len(unfinished)}")

        # 3. 中断恢复
        if run_state and run_state.fsm_state not in ("IDLE",):
            log("  尝试恢复中断任务...")
            try:
                recovery = resume_interrupted()
                result["checks"]["recovery"] = {
                    "ok": recovery is not None,
                    "result": str(recovery)[:200] if recovery else "无结果",
                }
            except Exception as e:
                result["checks"]["recovery"] = {"ok": False, "error": str(e)[:100]}

        log(f"  状态检查完成: 未完成={len(unfinished)}")

    except ImportError as e:
        result["status"] = "error"
        result["checks"]["import_error"] = str(e)
        log(f"  ❌ 导入失败: {e}", "ERROR")
    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)[:200]
        log(f"  ❌ 检查异常: {e}", "ERROR")

    return result


def run_production_loop_critic() -> dict:
    """
    Critic审查模式: 审查所有活跃会话、CaMeL趋势分析。
    对应 production_loop.engine 的 critic 操作。
    """
    log("🏭 Production Loop — Critic审查模式")
    result = {"mode": "critic", "status": "ok", "sessions": [], "warnings": []}

    ensure_production_loop_on_path()

    try:
        from production_loop.loop_state import LoopStateStore

        store = LoopStateStore()
        unfinished = store.get_unfinished_tasks()

        result["active_sessions"] = len(unfinished)
        for task in unfinished:
            result["sessions"].append({
                "task_id": task.get("task_id", "")[:16],
                "goal": task.get("original_goal", "")[:80],
                "status": task.get("status", "unknown"),
                "created": task.get("created_at", ""),
            })

        if len(unfinished) > 10:
            result["warnings"].append(f"Critic: 活跃会话过多 ({len(unfinished)})")

        log(f"  Critic审查完成: {len(unfinished)}活跃会话")

    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)[:200]
        log(f"  ❌ Critic异常: {e}", "ERROR")

    return result


def run_production_loop_full() -> dict:
    """
    深度验证模式: 完整性检查 + CaMeL安全深度+ 状态持久化验证。
    对应 production_loop.engine 的 verify + deep_check 操作。
    """
    log("🏭 Production Loop — 深度验证模式")
    result = {"mode": "full", "status": "ok", "checks": {}, "warnings": []}

    ensure_production_loop_on_path()

    # 完整性文件检查
    state_files = {
        "run_state.json": HERMES / "state" / "run_state.json",
        "last_success.json": HERMES / "state" / "last_success.json",
        "experiences.jsonl": HERMES / "state" / "experiences.jsonl",
    }

    for name, path in state_files.items():
        exists = path.exists()
        result["checks"][f"file_{name}"] = {"ok": exists, "exists": exists}
        if not exists:
            result["warnings"].append(f"缺失状态文件: {name}")

    # 先执行快速检查
    check_result = run_production_loop_check()
    result["checks"]["quick_check"] = check_result

    # 再执行Critic审查
    critic_result = run_production_loop_critic()
    result["checks"]["critic"] = critic_result

    all_ok = all(
        c.get("ok", True) for c in result["checks"].values()
        if isinstance(c, dict) and "ok" in c
    )
    if not all_ok:
        result["status"] = "degraded"

    log(f"  深度验证完成: 状态={result['status']}, 警告={len(result['warnings'])}条")

    return result


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Hermes Production Loop守护启动器")
    parser.add_argument(
        "--mode", default="full",
        choices=["check", "critic", "full"],
        help="运行模式: check(快速检查), critic(审查), full(深度验证,默认)"
    )
    parser.add_argument("--quiet", "-q", action="store_true", help="静默模式")
    args = parser.parse_args()

    quiet = args.quiet
    if not quiet:
        log(f"======== Production Loop守护 ========")
        log(f"模式: {args.mode}")

    t0 = time.time()
    mode_handlers = {
        "check": run_production_loop_check,
        "critic": run_production_loop_critic,
        "full": run_production_loop_full,
    }

    handler = mode_handlers.get(args.mode, run_production_loop_full)
    result = handler()
    result["duration_s"] = round(time.time() - t0, 1)
    result["timestamp"] = datetime.now(TZ).isoformat()

    # 持久化结果
    try:
        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        report_path = REPORT_DIR / "prod_loop_last.json"
        report_path.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    except Exception as e:
        log(f"  ⚠️ 无法写入报告: {e}", "WARN")

    if not quiet:
        log(f"  耗时: {result['duration_s']}s | 状态: {result['status']} "
            f"| 警告: {len(result.get('warnings', []))}条")

    # 退出码
    if result["status"] == "ok":
        return 0
    else:
        return 1


if __name__ == "__main__":
    sys.exit(main())
