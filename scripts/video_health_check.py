#!/usr/bin/env python3
"""视频引擎健康检查日志"""
from pathlib import Path

import sys

sys.path.insert(0, str(Path.home() / ".hermes" / "scripts"))
from hermes_video_engine import get_status

s = get_status()
print(f'[{__import__("datetime").datetime.now()}] video_health: ffmpeg={s["ffmpeg"]["available"]} comfyui_exists={s["comfyui"]["exists"]} video_nodes={s["comfyui"].get("video_nodes",0)} html_video={s.get("html_video","?")} flipbook={s.get("flipbook","?")}')
