"""
R12: 质量门禁 — post_tool_call hook
========================================
方法论依据: 四.2 质量门禁 (Quality Gates)
五道强制门禁:
1. Lint门: 代码通过Ruff/ESLint检查
2. Type门: Python mypy严格模式
3. Security门: SAST扫描 + 依赖漏洞检查
4. Test门: 单元测试覆盖率≥80%
5. Performance门: 关键操作延迟≤110%基线
"""

import json
import logging
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

GATE_LOG = Path("~/.hermes/logs/quality_gates.jsonl").expanduser()

# ── 门禁配置 ──
GATE_CONFIG = {
    "lint": {
        "enabled": True,
        "command": "ruff check --select=E,F,W",
        "block_on_failure": True,
    },
    "type": {
        "enabled": True,
        "command": "mypy --strict",
        "block_on_failure": True,
    },
    "security": {
        "enabled": True,
        "command": "bandit -r .",
        "block_on_failure": False,  # 警告但不阻塞
    },
    "test": {
        "enabled": True,
        "coverage_threshold": 80.0,
        "block_on_failure": True,
    },
    "performance": {
        "enabled": True,
        "latency_threshold_ratio": 1.10,  # 110%
        "block_on_failure": False,
    },
}

GATE_NAMES = ["lint", "type", "security", "test", "performance"]


def _log_gate_result(gate_name: str, passed: bool, details: str):
    """记录门禁结果"""
    GATE_LOG.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "gate": gate_name,
        "passed": passed,
        "details": details,
    }
    with open(GATE_LOG, "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _check_lint_gate(ctx) -> tuple[bool, str]:
    """Lint门: 静态代码检查"""
    # 获取最近修改的Python文件
    modified_files = getattr(ctx, "_recently_modified_files", [])
    if not modified_files:
        return True, "无最近修改的代码文件，跳过Lint检查"

    py_files = [f for f in modified_files if f.endswith(".py")]
    if not py_files:
        return True, "无Python文件变更"

    try:
        cmd = ["ruff", "check", "--select=E,F,W"] + py_files
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        passed = result.returncode == 0
        details = result.stdout[:500] if result.stdout else "Lint通过"
        if not passed:
            details = result.stderr[:500] or result.stdout[:500]
        return passed, details
    except FileNotFoundError:
        return True, "ruff未安装，跳过Lint门"
    except subprocess.TimeoutExpired:
        return False, "Lint检查超时(30s)"


def _check_type_gate(ctx) -> tuple[bool, str]:
    """Type门: 类型检查"""
    modified_files = getattr(ctx, "_recently_modified_files", [])
    py_files = [f for f in modified_files if f.endswith(".py")]
    if not py_files:
        return True, "无Python文件变更"

    try:
        cmd = ["mypy", "--strict"] + py_files
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        return result.returncode == 0, result.stdout[:500] or "类型检查通过"
    except FileNotFoundError:
        return True, "mypy未安装，跳过Type门"
    except subprocess.TimeoutExpired:
        return False, "类型检查超时(60s)"


def _check_security_gate(ctx) -> tuple[bool, str]:
    """Security门: SAST扫描"""
    try:
        cmd = ["bandit", "-r", ".", "-f", "json"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode == 0:
            return True, "安全扫描通过"
        # 解析结果
        data = json.loads(result.stdout)
        high_sev = [r for r in data.get("results", [])
                    if r.get("issue_severity") in ("HIGH", "MEDIUM")]
        if high_sev:
            return False, f"发现{len(high_sev)}个中高危安全问题"
        return True, f"仅发现低危问题({len(data.get('results',[]))}个)"
    except FileNotFoundError:
        return True, "bandit未安装，跳过Security门"
    except (subprocess.TimeoutExpired, json.JSONDecodeError) as e:
        return False, f"安全扫描失败: {e}"


def _check_test_gate(ctx) -> tuple[bool, str]:
    """Test门: 测试覆盖率"""
    try:
        cmd = ["python", "-m", "pytest", "--cov", "--cov-report=json", "-q"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        # 尝试读取覆盖率
        cov_path = Path("coverage.json")
        if cov_path.exists():
            cov_data = json.loads(cov_path.read_text())
            pct = cov_data.get("totals", {}).get("percent_covered", 0)
            threshold = GATE_CONFIG["test"]["coverage_threshold"]
            passed = pct >= threshold
            return passed, f"覆盖率 {pct:.1f}% (阈值 {threshold}%)"
        return result.returncode == 0, "测试执行完成（无法读取覆盖率）"
    except FileNotFoundError:
        return True, "pytest未安装，跳过Test门"
    except subprocess.TimeoutExpired:
        return False, "测试执行超时(120s)"


def _check_performance_gate(ctx) -> tuple[bool, str]:
    """Performance门: 性能回归检查"""
    # 抽样检查最近工具调用延迟
    recent_latencies = getattr(ctx, "_recent_tool_latencies", [])
    if not recent_latencies or len(recent_latencies) < 3:
        return True, "性能数据不足，跳过检查"

    avg_latency = sum(recent_latencies) / len(recent_latencies)
    baseline = getattr(ctx, "_performance_baseline", avg_latency)
    ratio = avg_latency / baseline if baseline > 0 else 1.0
    threshold = GATE_CONFIG["performance"]["latency_threshold_ratio"]
    passed = ratio <= threshold

    return passed, f"平均延迟 {avg_latency:.2f}s, 基线 {baseline:.2f}s (比值 {ratio:.2f})"


GATE_CHECKERS = {
    "lint": _check_lint_gate,
    "type": _check_type_gate,
    "security": _check_security_gate,
    "test": _check_test_gate,
    "performance": _check_performance_gate,
}


def check_gates(ctx, tool_name: str, result):
    """
    post_tool_call hook: 每次tool调用后检查是否需要运行质量门禁。
    对于"write_file"/"patch"等修改代码的操作，触发质量门禁检查。
    """
    # 只在代码修改类操作后触发
    CODE_MUTATING_TOOLS = {"write_file", "patch"}
    if tool_name not in CODE_MUTATING_TOOLS:
        return None

    # 获取修改的文件
    kwargs = getattr(ctx, "_last_tool_kwargs", {})
    file_path = kwargs.get("path", "")
    modified = getattr(ctx, "_recently_modified_files", [])
    if file_path and file_path.endswith(".py"):
        if file_path not in modified:
            modified.append(file_path)
            ctx._recently_modified_files = modified

    # 累计5次代码修改后运行门禁
    if len(modified) < 5:
        return None

    logger.info(f"[R12-质量门禁] 触发检查 ({len(modified)}个文件修改)")

    results = {}
    all_passed = True
    blocking_failures = []

    for gate_name in GATE_NAMES:
        config = GATE_CONFIG.get(gate_name, {})
        if not config.get("enabled", True):
            continue

        checker = GATE_CHECKERS.get(gate_name)
        if not checker:
            continue

        try:
            passed, details = checker(ctx)
            results[gate_name] = {"passed": passed, "details": details}
            _log_gate_result(gate_name, passed, details)

            if not passed:
                all_passed = False
                if config.get("block_on_failure", True):
                    blocking_failures.append(gate_name)
                logger.warning(f"[R12-质量门禁] {gate_name} 未通过: {details}")
            else:
                logger.info(f"[R12-质量门禁] {gate_name} 通过")
        except Exception as e:
            logger.error(f"[R12-质量门禁] {gate_name} 检查异常: {e}")
            results[gate_name] = {"passed": False, "details": str(e)}

    # 存储结果到上下文
    ctx._last_gate_results = results

    if blocking_failures:
        return {
            "block": True,
            "reason": f"质量门禁未通过: {', '.join(blocking_failures)}",
            "gate_results": results,
        }

    return None  # 放行
