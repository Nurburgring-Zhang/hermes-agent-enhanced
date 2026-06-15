#!/usr/bin/env python3
"""
🔮 V3进化守护进程启动器 — 接入Hermes cron/eternal_loop
=====================================================
通过cron每小时触发，或作为eternal_loop子任务集成。
调用 evolution_v3.v3_daemon.run_full_daemon_cycle() 执行完整6阶段巡检。

用法:
  python3 scripts/evo_daemon_launcher.py          # 独立运行
  python3 scripts/evo_daemon_launcher.py --quiet  # 静默模式(仅错误输出)

格林主人最高指令: 永不降级，全量真实执行。
"""

import json
import os
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

HERMES = Path.home() / ".hermes"
LOG_DIR = HERMES / "logs" / "evo_daemon"
REPORT_DIR = HERMES / "reports"

# 本地时区
TZ = timezone(timedelta(hours=8))


def log(msg: str, level: str = "INFO"):
    """结构化日志"""
    ts = datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] [{level}] {msg}"
    print(line)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOG_DIR / f"evo_daemon_{datetime.now(TZ).strftime('%Y%m%d')}.log"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def run_evo_daemon_cycle(quiet: bool = False) -> dict:
    """
    执行V3全自动守护循环。
    返回执行结果dict。
    """
    # 确保evolution_v3在路径中
    hermes_root = str(HERMES)
    if hermes_root not in sys.path:
        sys.path.insert(0, hermes_root)

    if not quiet:
        log("⚙️ V3进化守护进程启动器 — 开始执行")

    result = {"status": "error", "error": None, "phases": {}, "duration_s": 0}
    t0 = time.time()

    try:
        # 动态导入v3_daemon模块
        from evolution_v3.v3_daemon import run_full_daemon_cycle

        if not quiet:
            log("  → 已加载 evolution_v3.v3_daemon")

        # 执行完整守护循环
        daemon_result = run_full_daemon_cycle()
        result["status"] = daemon_result.get("status", "unknown")
        result["phases"] = {
            k: v for k, v in daemon_result.get("phases", {}).items()
            if isinstance(v, dict)
        }

        # 汇总阶段结果
        phase_count = len(result["phases"])
        ok_count = sum(1 for p in result["phases"].values() if p.get("ok", False))

        if not quiet:
            log(f"  阶段完成: {ok_count}/{phase_count} 通过")
            for phase_name, phase_data in result["phases"].items():
                ok = phase_data.get("ok", False)
                status_icon = "✅" if ok else "⚠️"
                error = phase_data.get("error", "")
                err_str = f" — {error}" if error else ""
                log(f"    {status_icon} {phase_name}{err_str}")

    except Exception as e:
        result["error"] = str(e)[:200]
        log(f"  ❌ 守护循环异常: {e}", "ERROR")

    result["duration_s"] = round(time.time() - t0, 1)

    # 持久化结果摘要
    try:
        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        summary_path = REPORT_DIR / "evo_daemon_last.json"
        summary_path.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    except Exception as e:
        log(f"  ⚠️ 无法写入摘要: {e}", "WARN")

    if not quiet:
        log(f"  ⏱️ 耗时: {result['duration_s']}s | 状态: {result['status']}")

    return result


def main():
    quiet = "--quiet" in sys.argv or "-q" in sys.argv

    log("======== V3进化守护进程 ========")
    result = run_evo_daemon_cycle(quiet=quiet)

    # 退出码
    if result["status"] == "ok":
        log("✅ V3守护完成: 全部通过")
        return 0
    elif result["status"] == "degraded":
        log("⚠️ V3守护完成: 部分异常(非致命)")
        return 0  # 降级不阻塞后续流程
    else:
        log(f"❌ V3守护失败: {result.get('error', '未知错误')}", "ERROR")
        return 1


if __name__ == "__main__":
    sys.exit(main())
