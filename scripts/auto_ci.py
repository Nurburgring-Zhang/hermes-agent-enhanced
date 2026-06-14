#!/usr/bin/env python3
"""
auto_ci.py — Hermes 本地自动CI循环
替代GitHub Actions，在本地每30分钟自动运行完整检查链
对标：GitHub Actions CI + GitLab CI Runner
"""
import json
import logging
import os
import subprocess
import time
from datetime import datetime
from pathlib import Path

HERMES = Path(os.path.expanduser("~/.hermes"))
LOG_DIR = HERMES / "logs" / "auto_ci"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / f"ci_{datetime.now():%Y%m%d}.log"),
        logging.StreamHandler(),
    ]
)
logger = logging.getLogger("auto_ci")

RESULTS_FILE = LOG_DIR / "ci_results.jsonl"

def run_step(name, cmd, cwd=None):
    """运行一个CI步骤，返回(success, output)"""
    logger.info(f"[{name}] 开始...")
    start = time.time()
    try:
        r = subprocess.run(
            cmd.split(), capture_output=True, text=True, timeout=300,
            cwd=cwd or str(HERMES)
        )
        duration = time.time() - start
        success = r.returncode == 0
        output = r.stdout[-500:] + r.stderr[-500:]

        status = "✅" if success else "❌"
        logger.info(f"[{name}] {status} ({duration:.1f}s)")
        if not success:
            logger.warning(f"[{name}] 失败输出: {r.stderr[-300:]}")

        return success, {
            "step": name, "success": success, "duration_s": round(duration, 2),
            "timestamp": datetime.now().isoformat(),
        }
    except subprocess.TimeoutExpired:
        logger.error(f"[{name}] ❌ 超时(300s)")
        return False, {"step": name, "success": False, "error": "timeout",
                       "timestamp": datetime.now().isoformat()}
    except Exception as e:
        logger.error(f"[{name}] ❌ 异常: {e}")
        return False, {"step": name, "success": False, "error": str(e),
                       "timestamp": datetime.now().isoformat()}


def run_full_ci():
    """执行完整CI链"""
    logger.info("=" * 60)
    logger.info("HERMES AUTO CI 开始")
    logger.info("  版本: 0.16.0-enhanced")
    logger.info(f"  时间: {datetime.now().isoformat()}")
    logger.info("=" * 60)

    results = []
    all_pass = True

    # Step 1: Lint
    ok, r = run_step("lint", "ruff check . --exit-zero", cwd=str(HERMES))
    results.append(r)
    if not ok: all_pass = False

    # Step 2: Test (核心模块) — 使用 cwd=scripts 替代 cd scripts
    test_cmd = (
        "python3 -m pytest "
        "test_rule_enforcer.py test_audit_system.py test_ministry.py "
        "test_resilience_patterns.py test_env_loader.py test_error_framework.py "
        "test_wake_guide.py test_gear_system.py test_gongbu_impl.py "
        "test_unified_collector.py test_cleaning_pipeline.py test_scoring.py "
        "test_push.py test_hy_memory.py test_context.py "
        "test_guardian.py test_auto_ci.py test_gear_enforcer.py "
        "test_gear_full.py test_rule_enforcer_extended.py test_memory_full.py "
        "-q --tb=short"
    )
    ok, r = run_step("test_core", test_cmd, cwd=str(HERMES / "scripts"))
    results.append(r)
    if not ok: all_pass = False

    # Step 3: Coverage (核心模块) — 使用 cwd=scripts
    cov_cmd = (
        "python3 -m pytest "
        "test_rule_enforcer.py test_audit_system.py "
        "test_ministry.py test_resilience_patterns.py test_env_loader.py "
        "test_error_framework.py test_wake_guide.py test_gear_system.py "
        "test_gongbu_impl.py "
        "test_guardian.py test_auto_ci.py test_gear_enforcer.py "
        "test_gear_full.py test_rule_enforcer_extended.py test_memory_full.py "
        "--cov --cov-report=term --cov-fail-under=30 -q --tb=short"
    )
    ok, r = run_step("coverage", cov_cmd, cwd=str(HERMES / "scripts"))
    results.append(r)
    if not ok: all_pass = False

    # Step 4: Security
    ok, r = run_step("security", "bandit -r scripts/ --exit-zero", cwd=str(HERMES))
    results.append(r)

    # 保存结果
    with open(RESULTS_FILE, "a") as f:
        f.write(json.dumps({
            "timestamp": datetime.now().isoformat(),
            "all_pass": all_pass,
            "steps": results,
            "total_duration_s": sum(s.get("duration_s", 0) for s in results),
        }) + "\n")

    # 报告
    logger.info("=" * 60)
    logger.info(f"CI 结果: {'✅ 全部通过' if all_pass else '❌ 有失败'}")
    for r in results:
        status = "✅" if r.get("success") else "❌"
        logger.info(f"  {status} {r['step']} ({r.get('duration_s',0):.1f}s)")
    logger.info("=" * 60)

    return all_pass


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Hermes Auto CI")
    parser.add_argument("--loop", type=int, default=0, help="循环间隔(分钟), 0=执行一次")
    parser.add_argument("--max-loops", type=int, default=10, help="最大循环次数")
    args = parser.parse_args()

    if args.loop > 0:
        logger.info(f"循环模式已启动: 每{args.loop}分钟一次, 最多{args.max_loops}次")
        for i in range(args.max_loops):
            logger.info(f"\n--- 第{i+1}次CI循环 ---")
            run_full_ci()
            if i < args.max_loops - 1:
                logger.info(f"等待{args.loop}分钟...")
                time.sleep(args.loop * 60)
    else:
        run_full_ci()
