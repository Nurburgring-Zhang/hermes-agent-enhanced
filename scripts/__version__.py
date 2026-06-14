"""
Hermes Agent Enhanced — 版本信息与变更记录
============================================

本项目版本遵循语义化版本 2.0 (SemVer) 规范：
https://semver.org/lang/zh-CN/
"""

__version__ = "0.16.0-enhanced"
__version_info__ = (0, 16, 0, "enhanced")

__title__ = "hermes-agent-enhanced"
__description__ = "Hermes Agent 增强版 — 商用级AI Agent平台"
__author__ = "Nous Research"
__email__ = "info@nousresearch.com"
__license__ = "MIT"
__copyright__ = "Copyright (c) 2024-2026 Nous Research"

# ─────────────────────────────────────────────
#  变更记录 (Changelog)
# ─────────────────────────────────────────────

CHANGELOG = {
    "0.16.0-enhanced": {
        "date": "2026-06-13",
        "type": "major",
        "summary": "Hermes Agent 增强版首发发布",
        "features": [
            "集成规则执行引擎 (rule_enforcer)，支持动态规则加载与热更新",
            "环境变量加载器 (env_loader)，支持 .env 多环境管理与秘钥脱敏",
            "六部模块架构：采集 → 解析 → 存储 → 分析 → 决策 → 执行",
            "统一采集框架 (unified_collector_v5)，支持多平台内容采集",
            "Gear 任务执行系统，支持任务编排与自动恢复",
            "上下文关联引擎 (context_auto_assoc)，智能知识图谱构建",
            "上下文安全模块 (context_failsafe)，异常检测与自动熔断",
            "故障恢复包 (recovery_pack)，支持自动修复与自我增强",
            "跨会话缓存 (cross_session_cache)，多会话知识共享",
            "工作流编排引擎 (workflow_daemon)，支持定时与事件驱动",
            "生产环境监控仪表盘 (production_monitor)，实时运行状态",
            "元认知思考器 (meta_thinker)，支持深度反思与策略优化",
        ],
        "improvements": [],
        "fixes": [],
        "deprecations": [],
        "breaking_changes": [],
    },
}


def get_version() -> str:
    """返回当前版本号字符串。"""
    return __version__


def get_changelog_since(since_version: str = "") -> str:
    """返回指定版本之后的变更摘要。

    Args:
        since_version: 起始版本号，为空时返回全部变更。

    Returns:
        格式化的变更记录文本。
    """
    lines = []
    for ver, info in sorted(CHANGELOG.items(), reverse=True):
        if since_version and ver <= since_version:
            continue
        lines.append(f"v{ver} ({info['date']}) — {info['summary']}")
        if info["features"]:
            lines.append("  新增:")
            for f in info["features"]:
                lines.append(f"    • {f}")
        if info["improvements"]:
            lines.append("  改进:")
            for i in info["improvements"]:
                lines.append(f"    • {i}")
        if info["fixes"]:
            lines.append("  修复:")
            for fx in info["fixes"]:
                lines.append(f"    • {fx}")
        if info["breaking_changes"]:
            lines.append("  不兼容变更:")
            for bc in info["breaking_changes"]:
                lines.append(f"    • {bc}")
        lines.append("")
    return "\n".join(lines)
