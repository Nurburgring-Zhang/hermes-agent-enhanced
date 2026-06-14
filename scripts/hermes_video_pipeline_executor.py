#!/usr/bin/env python3
"""
Hermes 视频生产组合管线执行器 v1.0
=================================
将ComfyUI + ffmpeg + 短剧引擎 + 网页视频组合成一条完整的视频生产链路。

集成点：
  - comfyui skill的 run_workflow.py → ComfyUI视频生成
  - hermes_video_engine.py → 统一引擎
  - hermes_short_drama_engine.py → 短剧管线
  - garden-web-video-production skill → 网页视频

执行模式：
  1. 单引擎模式：直接调用某一引擎
  2. 组合模式：链式组合多个引擎
  3. 并行模式：Goal Hive拆解并行
  4. 自动化模式：根据任务描述自动选择引擎
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

HERMES_HOME = Path(os.environ.get("HERMES_HOME", os.path.expanduser("~/.hermes")))
SCRIPT_DIR = HERMES_HOME / "scripts"
SKILLS_DIR = HERMES_HOME / "skills"
OUTPUT_VIDEO = HERMES_HOME / "outputs" / "video"
OUTPUT_DRAMA = HERMES_HOME / "outputs" / "short_drama"
COMFYUI_DIR = Path("/mnt/d/ComfyUI")
COMFYUI_SCRIPTS = SKILLS_DIR / "creative" / "comfyui" / "scripts"
COMFYUI_WORKFLOWS = SKILLS_DIR / "creative" / "comfyui" / "workflows"

# ===== 自动引擎选择 =====
class AutoPipelineSelector:
    """根据任务描述自动选择最优视频生产引擎"""

    VIDEO_TYPES = {
        "文生视频": {
            "keywords": ["文生视频", "文本到视频", "text-to-video", "t2v", "文字生成视频"],
            "engines": ["comfyui_wan", "comfyui_hunyuan"],
            "fallback": "html-video"
        },
        "图生视频": {
            "keywords": ["图生视频", "图片转视频", "image-to-video", "img2video", "i2v"],
            "engines": ["comfyui_wan_i2v", "comfyui_animatediff", "comfyui_cogvideo"],
            "fallback": "flipbook"
        },
        "短剧": {
            "keywords": ["短剧", "drama", "剧本", "小说转视频", "故事片", "剧情片"],
            "engines": ["short_drama"],
            "fallback": "html-video"
        },
        "演示视频": {
            "keywords": ["演示视频", "产品展示", "宣传片", "展示视频", "presentation", "产品视频"],
            "engines": ["html-video"],
            "fallback": "manim"
        },
        "数学动画": {
            "keywords": ["数学动画", "算法可视化", "manim", "3b1b", "教学动画", "科普动画"],
            "engines": ["manim"],
            "fallback": "html-video"
        },
        "视频处理": {
            "keywords": ["拼接", "合并", "加音频", "转场", "裁剪", "缩放", "格式转换"],
            "engines": ["ffmpeg"],
            "fallback": None
        },
        "视频编辑": {
            "keywords": ["剪辑", "编辑", "加字幕", "调速", "裁切", "添加文字"],
            "engines": ["ffmpeg"],
            "fallback": None
        }
    }

    @staticmethod
    def select(task_description: str) -> dict[str, Any]:
        """根据任务描述选择最佳引擎"""
        desc_lower = task_description.lower()

        for video_type, config in AutoPipelineSelector.VIDEO_TYPES.items():
            if any(kw in desc_lower for kw in config["keywords"]):
                return {
                    "type": video_type,
                    "engines": config["engines"],
                    "fallback": config["fallback"],
                    "confidence": "high"
                }

        # 默认：包含"视频"关键字
        if "视频" in desc_lower or "video" in desc_lower:
            return {
                "type": "通用视频",
                "engines": ["comfyui_wan", "html-video"],
                "fallback": "html-video",
                "confidence": "medium"
            }

        return {
            "type": "unknown",
            "engines": ["html-video"],
            "fallback": "html-video",
            "confidence": "low",
            "message": "未能明确匹配视频类型，默认使用html-video"
        }

# ===== ComfyUI直接调用 =====
class ComfyUIDirect:
    """直接调用ComfyUI工作流"""

    @staticmethod
    def run_workflow(workflow_name: str, params: dict, output_dir: str | None = None) -> dict:
        """运行一个ComfyUI工作流"""
        workflow_path = COMFYUI_WORKFLOWS / workflow_name
        if not workflow_path.exists():
            workflow_path = workflow_path.with_suffix(".json")
        if not workflow_path.exists():
            return {"status": "error", "message": f"Workflow not found: {workflow_name}"}

        output_dir = output_dir or str(OUTPUT_VIDEO)
        script = COMFYUI_SCRIPTS / "run_workflow.py"

        cmd = [
            sys.executable, str(script),
            "--workflow", str(workflow_path),
            "--args", json.dumps(params),
            "--output-dir", output_dir
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            return {
                "status": "success" if result.returncode == 0 else "error",
                "stdout": result.stdout[-500:],
                "stderr": result.stderr[-500:],
                "returncode": result.returncode
            }
        except subprocess.TimeoutExpired:
            return {"status": "timeout", "message": "Workflow execution timed out (600s)"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    @staticmethod
    def generate_video(
        prompt: str,
        engine: str = "wan",
        width: int = 1280,
        height: int = 720,
        frames: int = 81,
        negative_prompt: str = ""
    ) -> dict:
        """便捷的文生视频接口"""
        workflow_map = {
            "wan": "wan_video_t2v.json",
            "hunyuan": None,  # 需要创建工作流
            "animatediff": "animatediff_video.json",
            "cogvideo": None,
        }

        workflow_name = workflow_map.get(engine)
        if not workflow_name:
            return {"status": "error", "message": f"No workflow configured for engine: {engine}"}

        params = {
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "width": width,
            "height": height,
            "frames": frames,
            "seed": int(time.time() * 1000) % 9999999999
        }

        return ComfyUIDirect.run_workflow(workflow_name, params)

# ===== 短剧生产组合 =====
class DramaComposer:
    """短剧全流程组合执行器"""

    @staticmethod
    def full_production(
        script_path: str,
        title: str = "",
        max_scenes: int = 10,
        use_comfyui_for_video: bool = False
    ) -> dict:
        """从剧本到成片的全流程"""
        script_engine = SCRIPT_DIR / "hermes_short_drama_engine.py"

        cmd = [
            sys.executable, str(script_engine),
            "--produce", script_path,
            "--title", title or "未命名短剧",
            "--scenes", str(max_scenes)
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            output = result.stdout
            try:
                return json.loads(output)
            except json.JSONDecodeError:
                return {
                    "status": "partial",
                    "raw_output": output[-1000:],
                    "stderr": result.stderr[-500:]
                }
        except Exception as e:
            return {"status": "error", "message": str(e)}

# ===== 网页视频组合 =====
class HTMLVideoComposer:
    """网页视频组合执行"""

    @staticmethod
    def produce(content: str, theme: str = "default", use_tts: bool = True) -> dict:
        """
        生成网页视频。

        theme 可选:
          bold-signal / terminal-green / newsroom / electric-studio
          bauhaus-bold / creative-voltage / neon-cyber / vintage-editorial
          split-canvas / dark-botanical / forest-ink
        """
        # 默认由garden-web-video-production skill处理
        return {
            "status": "delegated",
            "skill": "garden-web-video-production",
            "theme": theme,
            "content_length": len(content),
            "message": "网页视频生成由garden-web-video-production skill负责"
        }

# ===== 统一执行器 =====
class UnifiedVideoExecutor:
    """统一入口——任意视频/短剧任务都从这里进入"""

    @staticmethod
    def execute(task: dict) -> dict:
        """
        执行任意视频/短剧任务。

        输入task格式:
        {
            "type": "text-to-video" | "short-drama" | "html-video" | "video-edit" | "auto",
            "prompt": "描述",
            "params": {...}
        }
        """
        task_type = task.get("type", "auto")
        prompt = task.get("prompt", task.get("description", ""))
        params = task.get("params", {})

        if task_type == "auto":
            selection = AutoPipelineSelector.select(prompt)
            task_type = selection["type"]

        result = {"task_type": task_type, "prompt": prompt[:200], "status": "pending"}

        if task_type in ["文生视频", "text-to-video", "通用视频"]:
            engine = params.get("engine", "wan")
            result = ComfyUIDirect.generate_video(prompt, engine=engine, **params)
            # 如果ComfyUI失败，尝试默认引擎
            if result.get("status") in ["error", "timeout", "needs_launch"]:
                fallback_result = HTMLVideoComposer.produce(prompt)
                result["fallback"] = fallback_result

        elif task_type in ["短剧", "short-drama", "drama"]:
            script_path = params.get("script_path")
            if script_path:
                result = DramaComposer.full_production(script_path, **params)
            else:
                result = {"status": "error", "message": "短剧生产需要script_path参数"}

        elif task_type in ["演示视频", "演示", "html-video", "presentation"]:
            result = HTMLVideoComposer.produce(prompt, **params)

        elif task_type in ["视频处理", "video-edit", "ffmpeg"]:
            action = params.get("action", "concat")
            if action == "concat":
                from hermes_video_engine import FFmpegProcessor
                result = FFmpegProcessor.concat_videos(
                    params.get("inputs", []),
                    params.get("output", "")
                )
            else:
                result = {"status": "error", "message": f"Unknown action: {action}"}

        else:
            result = {"status": "unknown", "message": f"Unknown task type: {task_type}"}

        return result

# ===== CLI入口 =====
def main():
    import argparse
    parser = argparse.ArgumentParser(description="Hermes 视频生产组合管线")
    parser.add_argument("--task", type=str, help="视频任务JSON文件路径")
    parser.add_argument("--prompt", type=str, help="视频描述prompt")
    parser.add_argument("--type", type=str, default="auto",
                        choices=["text-to-video", "short-drama", "html-video", "video-edit", "auto"],
                        help="任务类型")
    parser.add_argument("--engine", type=str, default="wan",
                        help="视频引擎 (wan/hunyuan/animatediff)")
    parser.add_argument("--select", type=str, help="根据prompt自动选择引擎")
    parser.add_argument("--list-workflows", action="store_true", help="列出可用工作流")

    args = parser.parse_args()

    if args.list_workflows:
        wfs = list(COMFYUI_WORKFLOWS.glob("*.json"))
        print(f"Available ComfyUI workflows ({len(wfs)}):")
        for wf in sorted(wfs):
            print(f"  {wf.name}")

    elif args.select:
        selection = AutoPipelineSelector.select(args.select)
        print(json.dumps(selection, indent=2, ensure_ascii=False))

    elif args.task:
        with open(args.task) as f:
            task = json.load(f)
        result = UnifiedVideoExecutor.execute(task)
        print(json.dumps(result, indent=2, ensure_ascii=False))

    elif args.prompt:
        task = {"type": args.type, "prompt": args.prompt, "params": {"engine": args.engine}}
        result = UnifiedVideoExecutor.execute(task)
        print(json.dumps(result, indent=2, ensure_ascii=False))

    else:
        parser.print_help()

if __name__ == "__main__":
    main()
