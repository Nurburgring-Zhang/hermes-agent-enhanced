#!/usr/bin/env python3
"""
Hermes 视频/短剧生产 cron 调度器
=================================
维护视频引擎的自动运行状态。

被 crontab 调度：
  - 每30分钟检测ComfyUI是否存活
  - 每天03:00清理过期视频缓存
  - 每15分钟检查待处理的视频队列
"""

import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

HERMES_HOME = Path(os.environ.get("HERMES_HOME", os.path.expanduser("~/.hermes")))
SCRIPT_DIR = HERMES_HOME / "scripts"
OUTPUT_VIDEO = HERMES_HOME / "outputs" / "video"
OUTPUT_DRAMA = HERMES_HOME / "outputs" / "short_drama"
REPORT_DIR = HERMES_HOME / "reports"
QUEUE_PATH = REPORT_DIR / "video_queue.json"


def healthcheck():
    """检查视频引擎健康状态"""
    sys.path.insert(0, str(SCRIPT_DIR))
    try:
        from hermes_video_engine import get_status
        status = get_status()
        report = {
            "timestamp": datetime.now().isoformat(),
            "comfyui_exists": status["comfyui"]["exists"],
            "comfyui_video_nodes": status["comfyui"]["video_nodes"],
            "ffmpeg_available": status["ffmpeg"]["available"],
            "video_free_gb": round(status["output_dir"]["video_free_gb"], 1)
        }
        # 写报告
        report_path = REPORT_DIR / "video_engine_health.json"
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)
        print(f"HEALTH: {json.dumps(report)}")
        return report
    except Exception as e:
        print(f"HEALTH_ERROR: {e}")
        return {"error": str(e)}


def clean_old_outputs(max_age_days: int = 7, dry_run: bool = True):
    """清理过期视频输出"""
    now = time.time()
    removed = {"video": 0, "drama": 0, "freed_mb": 0}

    for base_dir, key in [(OUTPUT_VIDEO, "video"), (OUTPUT_DRAMA, "drama")]:
        if not base_dir.exists():
            continue
        for f in base_dir.iterdir():
            if f.is_file() and f.suffix in [".mp4", ".webm", ".wav", ".json"]:
                age_seconds = now - f.stat().st_mtime
                if age_seconds > max_age_days * 86400:
                    removed[key] += 1
                    removed["freed_mb"] += f.stat().st_size / (1024 * 1024)
                    if not dry_run:
                        f.unlink()

    print(f"CLEAN: removed={removed} dry_run={dry_run}")
    return removed


def check_queue():
    """检查视频生产队列是否有待处理任务"""
    if not QUEUE_PATH.exists():
        print("QUEUE: empty (no queue file)")
        return {"pending": 0, "items": []}

    with open(QUEUE_PATH) as f:
        queue = json.load(f)

    pending = [q for q in queue if q.get("status") == "pending"]
    print(f"QUEUE: {len(pending)} pending items")
    return {"pending": len(pending), "items": pending}


# ===== CLI =====
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Video system cron")
    parser.add_argument("action", choices=["healthcheck", "clean", "queue"])
    parser.add_argument("--dry-run", action="store_true", default=True)
    parser.add_argument("--max-age", type=int, default=7)
    args = parser.parse_args()

    if args.action == "healthcheck":
        healthcheck()
    elif args.action == "clean":
        clean_old_outputs(args.max_age, args.dry_run)
    elif args.action == "queue":
        check_queue()
