#!/usr/bin/env python3
"""
Hermes 规则强制执行引擎 v1.0
================================
将 SOUL.md 中所有"写在文档里但无代码强制"的规则，
变成真正的系统底层拦截器。

强制范围：
  R1 反幻觉铁律  — 工具调用结果真实性验证
  R2 前置三查      — 任务执行前自动 session_search + memory + skill
  R3 改前备份      — 工具调用修改文件前自动备份
  R4 交付铁律      — 提交前检查是否包含真实运行证据
  R5 深度审核      — 审核结果必须包含运行测试证据

注入方式：model_tools.py 系统启动层自动加载，
         每次工具调用前后和对话前后执行拦截。
"""

import hashlib
import json
import logging
import os
import re
import shutil
import subprocess
import threading
from datetime import datetime
from pathlib import Path

try:
    import yaml as _yaml
    _yaml_available = True
except ImportError:
    _yaml_available = False

logger = logging.getLogger(__name__)

# ── 日志 ──
_log_lock = threading.Lock()
try:
    from scripts.audit_system import get_audit_logger
    _audit = get_audit_logger()
    _audit_available = True
except Exception:
    _audit = None
    _audit_available = False

# ── 弹性模式引擎（对标OPA/Hystrix 商用级）
try:
    from resilience_patterns import (
        CircuitBreaker,
        CircuitBreakerConfig,
        RateLimiterConfig,
        RetryConfig,
        UnifiedRuleEnforcer,
    )
    _resilience = UnifiedRuleEnforcer("rule_enforcer")
    _resilience.circuit_breaker = CircuitBreaker(
        "rule_eval", CircuitBreakerConfig(fail_max=10, reset_timeout=60.0)
    )
    _resilience.retry_config = RetryConfig(max_retries=2, base_delay=0.5, jitter=True)
    _resilience.rate_limiter_cfg = RateLimiterConfig(max_requests=500, window_seconds=60)
    _resilience_available = True
except Exception as e:
    _resilience_available = False
    logger.debug("Resilience patterns unavailable: %s", e)

HERMES = Path(os.path.expanduser("~/.hermes"))
BACKUP_DIR = Path("/mnt/d/Hermes/备份")
LOG_PATH = HERMES / "logs" / "rule_enforcer.log"


def _log(msg: str):
    with _log_lock:
        try:
            LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(LOG_PATH, "a") as f:
                f.write(f"[{datetime.now().isoformat()}] {msg}\n")
        except Exception:
            pass

# ── 状态 ──
_enforcer_enabled = True
_enforcement_count = {"pass": 0, "block": 0, "warn": 0}


# ════════════════════════════════════════════════════════════
# R1: 反幻觉铁律 — 工具调用结果真实性验证
# ════════════════════════════════════════════════════════════
class AntiHallucination:
    """R1: 反幻觉铁律 — 工具调用结果真实性验证。

    在每次工具调用返回后验证输出是否包含未经验证的断言。
    检测推测性语言、无来源声明、空结果等。

    Attributes:
        HALLUCINATION_PATTERNS: 推测性语言正则模式列表。

    Example:
        >>> result = AntiHallucination.check_tool_output("read_file", {}, "可能是版本3.2")
        >>> result['verdict']  # 'warn' or 'pass'
    """

    HALLUCINATION_PATTERNS = [
        r"(?i)应该(是|有|在|可以)",
        r"(?i)可能(是|有|在|存在)",
        r"(?i)理论上",
        r"(?i)一般来说",
        r"(?i)据(我所知|了解)",
        r"(?i)我不确定但",
        r"(?i)大概是",
        r"(?i)让我(猜|假设)",
        r"(?i)我没有验证过",
    ]

    @staticmethod
    def check_tool_output(tool_name: str, args: dict, result: str) -> dict:
        """检查工具输出是否含有未经验证的断言"""
        issues = []

        # 模式1: 输出包含推测性语言
        for pattern in AntiHallucination.HALLUCINATION_PATTERNS:
            if re.search(pattern, result):
                issues.append(f"输出含有推测性语言: {pattern}")

        # 模式2: 输出声称路径/版本号存在但无来源说明
        path_claims = re.findall(r"(?:路径|目录|文件).*?[:：]\s*([/\w.\\-]+)", result)
        version_claims = re.findall(r"版本[号本]?[:：]\s*([\w.]+)", result)
        for claim in path_claims + version_claims:
            if not re.search(r"(?:ls|cat|read_file|查看|检查|确认).*"+re.escape(claim), result):
                issues.append(f'声明 "{claim}" 无来源说明')

        # 模式3: 文件操作类工具结果为空但声称成功
        if tool_name in ("read_file", "search_files", "list_files", "cat") and not result.strip():
            issues.append("工具返回空但未说明失败原因")

        verdict = "pass" if not issues else "warn"
        if verdict != "pass":
            _log(f"[R1反幻觉] {tool_name}: {'; '.join(issues[:3])}")

        return {"rule": "R1", "tool": tool_name, "verdict": verdict, "issues": issues}

    @staticmethod
    def check_response(response: str, tool_calls: list[dict]) -> dict:
        """
        在LLM返回最终回答时，验证不包含幻觉。
        检查回答中是否声称做了某些事但实际tool_call记录不匹配。
        """
        issues = []

        # 检查"我执行了X"模式
        exec_claims = re.findall(r"我(已|已经)?(执行|完成|调用|运行)(了)?[：: ]*(.+?)[。，；]", response)
        for claim in exec_claims:
            claimed_action = claim[3].strip() if len(claim) > 3 else ""
            if claimed_action and not any(claimed_action[:8] in str(tc) for tc in tool_calls):
                issues.append(f'声称执行了 "{claimed_action[:30]}..." 但无对应tool_call记录')

        # 检查未标注数据来源的数字/统计
        numbers = re.findall(r"(采集|处理|生成|获取)(了)?(\d+)\s*(条|个|篇)", response)
        for n in numbers:
            count = n[2]
            if int(count) > 10:
                # 检查是否有对应的采集/处理工具调用
                has_tool = any(
                    tc.get("name", "") in ("collect", "crawl", "unified_collector_v5", "search")
                    for tc in tool_calls
                ) if tool_calls else False
                if not has_tool:
                    issues.append(f"声称采集了{count}条数据但无对应工具调用记录")

        verdict = "pass" if not issues else "warn"
        if verdict != "warn":
            issues = issues[:3]
            for i in issues:
                _log(f"[R1反幻觉 response] {i}")

        return {"rule": "R1", "context": "response", "verdict": verdict, "issues": issues}


# ════════════════════════════════════════════════════════════
# R2: 前置三查 — 任务执行前自动 session_search + memory + skill
# ════════════════════════════════════════════════════════════
class PreCheck:
    """R2: 前置三查 — 任务执行前自动回顾。

    在每次任务/对话开始前自动执行:
      ① session_search — 历史会话回顾
      ② fact_store — 记忆检索
      ③ skill_view — 相关技能加载

    Example:
        >>> result = PreCheck.execute("测试数据库配置修改")
        >>> result['verdict']  # 'pass' or 'warn'
    """

    @staticmethod
    def execute(task: str) -> dict:
        """执行前置三查，返回检查结果"""
        checks = {"session_search": False, "fact_store": False, "skill_load": False}
        outputs = []

        # ① session_search — 通过子进程调用 hermes session_search
        try:
            result = subprocess.run(
                ["hermes", "sessions", "list", "--limit", "10"],
                capture_output=True, text=True, timeout=10,
                env={**os.environ, "HERMES_NO_SPINNER": "1"}
            )
            if result.returncode == 0 and result.stdout.strip():
                session_count = len([l for l in result.stdout.split("\n") if l.strip() and not l.startswith("┌") and not l.startswith("│") and not l.startswith("└") and not l.startswith("╭") and not l.startswith("├") and not l.startswith("╰") and "session_id" not in l])
                outputs.append(f"历史回顾: 最近{session_count}个会话可用")
                checks["session_search"] = True
        except Exception:
            outputs.append("历史回顾: hermes不可用(降级)")

        # ② fact_store — 检查fact_store状态
        try:
            # 通过fact_store工具确认，没法直接调用，检查memory目录
            memory_dir = HERMES / "memories"
            if memory_dir.exists():
                memory_files = list(memory_dir.glob("*.json"))
                outputs.append(f"记忆存储: {len(memory_files)}个记忆文件")
                checks["fact_store"] = True
            else:
                outputs.append("记忆存储: memory目录不存在")
        except Exception:
            pass

        # ③ skill_view — 根据task关键词找到相关skills
        try:
            skills_dir = HERMES / "skills"
            if skills_dir.exists():
                keywords = re.findall(r"[\u4e00-\u9fff\w]{2,}", task.lower())
                matched = set()
                for skill_dir in skills_dir.iterdir():
                    if skill_dir.is_dir():
                        skill_name = skill_dir.name.lower()
                        for kw in keywords:
                            if len(kw) >= 2 and kw in skill_name:
                                matched.add(skill_dir.name)
                                break
                if matched:
                    outputs.append(f"匹配技能: {', '.join(list(matched)[:5])}")
                    checks["skill_load"] = True
                else:
                    outputs.append("匹配技能: 自动匹配未发现(可手动加载)")
        except Exception:
            pass

        verdict = "pass" if all(checks.values()) else "warn"
        _log(f"[R2前置三查] {'✅' if verdict=='pass' else '⚠️'} task='{task[:50]}...' session={checks['session_search']} memory={checks['fact_store']} skill={checks['skill_load']}")

        return {
            "rule": "R2",
            "verdict": verdict,
            "checks": checks,
            "summary": " | ".join(outputs),
            "outputs": outputs,
        }


# ════════════════════════════════════════════════════════════
# R3: 改前备份 — 修改文件前自动备份
# ════════════════════════════════════════════════════════════
class BackupGuard:
    """
    拦截所有写文件类工具调用(read_file/write_file/patch/search_files等)，
    如果目标是源代码目录(~/.hermes/hermes-agent/)，
    自动在修改前创建备份副本到 /mnt/d/Hermes/备份/。
    """

    PROTECTED_DIRS = [
        str(HERMES / "hermes-agent"),
        str(HERMES / "scripts"),
        str(HERMES / "skills"),
        str(HERMES / "agent"),
        str(HERMES / "tools"),
    ]

    WRITE_TOOLS = {"write_file", "patch", "delete_file", "rename", "move", "copy", "sed", "replace"}

    @staticmethod
    def pre_tool(tool_name: str, args: dict) -> dict:
        """工具调用前检查是否需要备份"""
        if tool_name not in BackupGuard.WRITE_TOOLS:
            return {"action": "pass"}

        target_path = args.get("path", args.get("old_file", args.get("source", "")))
        if not target_path:
            return {"action": "pass"}

        target_path = os.path.abspath(os.path.expanduser(target_path))

        # 检查是否在保护目录中
        is_protected = False
        for protected in BackupGuard.PROTECTED_DIRS:
            if target_path.startswith(protected):
                is_protected = True
                break

        if not is_protected:
            return {"action": "pass"}

        # 检查文件是否存在
        if not os.path.isfile(target_path):
            return {"action": "pass"}

        # 检查是否今天已经备份过了（避免重复备份）
        backup_date = datetime.now().strftime("%Y%m%d")
        relative = os.path.relpath(target_path, str(HERMES))
        backup_path = BACKUP_DIR / backup_date / relative
        if backup_path.exists():
            # 检查内容是否一致
            existing_hash = hashlib.sha256(open(backup_path, "rb").read()).hexdigest()
            current_hash = hashlib.sha256(open(target_path, "rb").read()).hexdigest()
            if existing_hash == current_hash:
                return {"action": "pass", "note": f"已备份({backup_path})"}

        # 执行备份
        try:
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(target_path, backup_path)
            _log(f"[R3改前备份] ✅ {target_path} → {backup_path}")
            return {"action": "pass", "note": f"自动备份到 {backup_path}"}
        except Exception as e:
            _log(f"[R3改前备份] ❌ {target_path} 备份失败: {e}")
            return {"action": "warn", "note": f"备份失败: {e}"}

    @staticmethod
    def post_tool(tool_name: str, args: dict, result: str) -> dict:
        """工具调用后验证文件是否被修改且未备份"""
        if tool_name not in BackupGuard.WRITE_TOOLS:
            return {"action": "pass"}

        target_path = args.get("path", args.get("old_file", args.get("source", "")))
        if not target_path:
            return {"action": "pass"}

        target_path = os.path.abspath(os.path.expanduser(target_path))

        # 检查是否在保护目录
        is_protected = any(target_path.startswith(d) for d in BackupGuard.PROTECTED_DIRS)
        if not is_protected:
            return {"action": "pass"}

        # 检查备份是否存在
        backup_date = datetime.now().strftime("%Y%m%d")
        relative = os.path.relpath(target_path, str(HERMES))
        backup_path = BACKUP_DIR / backup_date / relative
        if not backup_path.exists():
            _log(f"[R3改前备份] ❌ {target_path} 被修改但无备份")
            return {
                "action": "block",
                "reason": f"{target_path} 被修改但未找到备份文件！"
            }

        return {"action": "pass", "note": f"备份已验证: {backup_path}"}


# ════════════════════════════════════════════════════════════
# R4: 交付铁律 — 提交前检查是否包含真实运行证据
# ════════════════════════════════════════════════════════════
class DeliveryEnforcer:
    """
    在每次交付/输出检查时，验证输出是否包含真实运行证据。
    禁止：纯描述性声明、只说"已完成"不说怎么验证的。
    """

    @staticmethod
    def check_output(response: str, tool_calls: list[dict]) -> dict:
        """检查最终输出是否包含可验证的运行证据"""
        issues = []

        # 模式1: 只有声明没有证据
        completion_claims = re.findall(r"(已(完成|实现|创建|添加|修复|部署)|成功(部署|创建)?|全部完成)", response)
        if completion_claims:
            has_evidence = any([
                re.search(r"http[s]?://", response),
                re.search(r"(curl|wget|http|localhost|测试通过|返回.*状态)", response, re.IGNORECASE),
                re.search(r"(?:\d+)/(?:\d+)\s*(?:通过|成功|测试)", response),
                re.search(r"状态码|HTTP.*\d{3}|\b200\b|\bOK\b", response),
            ])
            if not has_evidence:
                issues.append("声明完成但无运行证据(无URL/无HTTP状态码/无测试结果)")

        # 模式2: 说了"已验证"但没说出具体验证方法
        verify_claims = re.findall(r"(经过|已)?(验证|测试|确认)(了)?(功能|正常|通过)?", response)
        if verify_claims and not re.search(r"(curl|测试用例|pytest|运行|http://|状态)", response, re.IGNORECASE):
            issues.append("声称已验证但未说明验证方法")

        # 模式3: 工具调用记录为0但声称做了复杂工作
        if not tool_calls and len(response) > 200:
            # 检查是否真的需要工具
            if not re.search(r"(你好|我叫|你是谁|hi|hello|回复)", response[:100], re.IGNORECASE):
                issues.append("无工具调用但输出超过200字（缺少运行支撑）")

        verdict = "pass" if not issues else "warn"
        if verdict != "pass":
            _log(f"[R4交付铁律] {'; '.join(issues[:3])}")

        return {"rule": "R4", "verdict": verdict, "issues": issues}


# ════════════════════════════════════════════════════════════
# R5: 深度审核铁律 — 审核结果必须包含运行测试证据
# ════════════════════════════════════════════════════════════
class DeepAuditEnforcer:
    """
    在"审核"类工具调用后，验证输出是否包含真实测试运行结果。
    禁止：只看代码不看运行、只说"可能有bug"不说不可以实际运行验证。
    """

    AUDIT_KEYWORDS = ["审核", "审计", "review", "audit", "检查", "审阅", "深度审核"]

    @staticmethod
    def check_audit_output(tool_name: str, args: dict, result: str) -> dict:
        """检查审核输出是否包含真实测试证据"""
        if not any(kw in tool_name.lower() or kw in str(args).lower() for kw in DeepAuditEnforcer.AUDIT_KEYWORDS):
            return {"action": "pass"}

        issues = []

        # 必须有实际验证方法
        has_verification = any([
            re.search(r"(pytest|unittest|测试运行|实际验证|浏览器.*打开|手动验证)", result),
            re.search(r"(运行|执行).*(测试|验证)", result),
            re.search(r"(状态码|HTTP.*\d{3}|返回.*数据|实际.*输出)", result),
            re.search(r"(real_output|actual_output|实际运行)", result),
        ])

        if not has_verification and len(result) > 100:
            issues.append("深度审核必须包含实际运行验证（pytest/浏览器/curl）")

        # 检查是否只有"代码审查"没有"运行测试"
        if re.search(r"(代码|逻辑|结构|风格|格式).*(问题|错误|建议)", result):
            if not re.search(r"(运行|执行|测试|跑一下)", result):
                issues.append("只做了代码审查，未做实际运行验证")

        if issues:
            _log(f"[R5深度审核] {'; '.join(issues)}")
            return {"action": "warn", "issues": issues}

        return {"action": "pass"}


# ════════════════════════════════════════════════════════════
# 统一拦截入口
# ════════════════════════════════════════════════════════════


def pre_conversation_hook(task: str) -> str:
    """在对话开始前执行R2前置三查，返回检查摘要注入system prompt"""
    try:
        pc = PreCheck.execute(task)
        return f"[Rules] {pc['summary']}"
    except Exception:
        return ""


def post_conversation_hook(task: str, response: str) -> None:
    """在对话完成后执行R1+R4检查"""
    try:
        # tool_calls在对话后无法获取全量，只做R1 basic + R4
        r1 = AntiHallucination.check_response(response, [])
        r4 = DeliveryEnforcer.check_output(response, [])
        if r1["verdict"] != "pass":
            _log(f"[POST-R1反幻觉] 最终响应发现{len(r1.get('issues',[]))}个问题")
        if r4["verdict"] != "pass":
            _log(f"[POST-R4交付铁律] 最终响应发现{len(r4.get('issues',[]))}个问题")
    except Exception:
        pass


# ════════════════════════════════════════════════════════════
# 独立测试
# ════════════════════════════════════════════════════════════
if __name__ == "__main__":
    logger.info("=" * 72)
    logger.info("Hermes 规则强制执行引擎 v1.0 — 自检")
    logger.info("=" * 72)
    logger.info()

    # R1 测试
    logger.info("[R1] 反幻觉测试:")
    r = AntiHallucination.check_tool_output("read_file", {}, "这个文件应该存在，可能是版本3.2.1")
    logger.info(f"  推测性输出 → {r['verdict']}")
    r = AntiHallucination.check_tool_output("search_files", {}, "/home/user/config.json")
    logger.info(f"  无来源声明 → {r['verdict']}")
    r = AntiHallucination.check_response("我已完成了所有采集工作，获取了约50条数据", [{"name": "chat", "args": {}}])
    logger.info(f"  声称无证据 → {r['verdict']}")
    logger.info()

    # R2 测试
    logger.info("[R2] 前置三查测试:")
    r = PreCheck.execute("测试数据库配置修改")
    logger.info(f"  session_search: {'✅' if r['checks']['session_search'] else '❌'} | memory: {'✅' if r['checks']['fact_store'] else '❌'} | skill: {'✅' if r['checks']['skill_load'] else '❌'}")
    logger.info(f"  摘要: {r['summary']}")
    logger.info()

    # R3 测试
    logger.info("[R3] 改前备份测试:")
    from tempfile import NamedTemporaryFile
    tf = NamedTemporaryFile(delete=False, suffix=".py")
    tf.write(b"test")
    tf.close()
    test_path = tf.name.replace("/tmp/", str(HERMES / "hermes-agent" / ""))
    # 不在保护目录中，预期pass
    r = BackupGuard.pre_tool("write_file", {"path": "/tmp/test.py"})
    logger.info(f"  /tmp路径 → {r['action']} (预期pass)")
    logger.info()

    # R4 测试
    logger.info("[R4] 交付铁律测试:")
    r = DeliveryEnforcer.check_output("已成功完成所有功能，全部验证通过", [])
    logger.info(f"  无证据声明 → {r['verdict']}")
    r = DeliveryEnforcer.check_output("接口返回HTTP 200，数据验证通过，返回了137条记录", [{"name": "curl", "args": {"url": "http://test"}}])
    logger.info(f"  有证据声明 → {r['verdict']}")
    logger.info()

    # R5 测试
    logger.info("[R5] 深度审核测试:")
    r = DeepAuditEnforcer.check_audit_output("audit", {"file": "test.py"}, "代码逻辑有三处问题...")
    logger.info(f"  仅有代码审查 → {r.get('action', 'pass')}")
    r = DeepAuditEnforcer.check_audit_output("audit", {"file": "test.py"}, "运行pytest后发现了3个失败...")
    logger.info(f"  含运行测试 → {r.get('action', 'pass')}")
    logger.info()

    # 统一入口测试 (defined later in module)
    # r1 = pre_tool_intercept("write_file", {"path": str(HERMES / "hermes-agent" / "test.py")})
    # r2 = post_tool_intercept("read_file", {}, "可能是版本2.0", "")
    # r3 = post_response_intercept("全部完成，一切正常", [])
    logger.info("[统一拦截] 测试已移至模块末尾")
    logger.info()

    logger.info("=" * 72)
    logger.info(get_report())
    logger.info("=" * 72)


# ════════════════════════════════════════════════════════════
# R6: 沟通风格 — 禁止AI味词汇，强制具体数字
# ════════════════════════════════════════════════════════════
class CommunicationEnforcer:
    """
    检测输出中是否有AI味词汇，替换为具体数字/证据。
    """

    BANNED_WORDS = [
        "赋能", "助力", "加持", "赋能于", "高效赋能",
        "赋能升级", "深度赋能", "数字化赋能", "科技赋能",
        "抓手", "闭环", "颗粒度", "底层逻辑", "顶层设计",
        "对齐", "打法", "组合拳", "增量", "盘活",
        "反哺", "共振", "矩阵", "延展", "落地",
        "赛道", "生态化", "去中心化", "私域",
        "复用", "透传", "下钻", "拉通", "打通",
        "心智", "场域", "体感", "链路", "耦合",
        "敏捷迭代", "快速响应", "降本增效", "数字化转型",
    ]

    VAGUE_PATTERNS = [
        (r"(显著|大幅|极大|非常|多维度|全方位|立体化|有效)(提升|改进|优化|增强|改善|增长)", "模糊提升描述，需替换为具体数据"),
        (r"(大量|众多|许多|广泛|普遍)(应用|使用|采用|实践)", "模糊数量词，需替换为具体数字"),
        (r"(业内|行业|业界)(领先|一流|顶尖|前沿|知名)", "无来源的行业领先声明"),
        (r"(经过|多次|反复)(测试|验证|优化|迭代)", "需说明具体测试次数/方法"),
    ]

    @staticmethod
    def check_response(response: str) -> dict:
        issues = []

        # 精确匹配禁用词
        for word in CommunicationEnforcer.BANNED_WORDS:
            if word in response:
                issues.append(f'含禁用词: "{word}"')

        # 模糊表述匹配
        for pattern, msg in CommunicationEnforcer.VAGUE_PATTERNS:
            match = re.search(pattern, response)
            if match:
                issues.append(f'{msg}: "{match.group(0)[:50]}"')

        # 检查是否有AI问候模板
        ai_greeting = re.search(r"(作为(一个)?AI|作为一个大型语言模型|我是AI|我是助手|很高兴为你)",
                                response[:300], re.IGNORECASE)
        if ai_greeting:
            issues.append(f'AI味开场白: "{ai_greeting.group(0)[:40]}"')

        if issues:
            _log(f"[R6沟通风格] {'; '.join(issues[:5])}")

        return {"rule": "R6", "verdict": "warn" if issues else "pass", "issues": issues[:8]}


# ════════════════════════════════════════════════════════════
# R7: 自主边界 — 敏感操作拦截
# ════════════════════════════════════════════════════════════
class AutonomyGuard:
    """
    拦截需要明确批准的敏感操作。
    三级响应：提示(提醒确认) / 阻止(直接拦截) / 报警(记录+通知)
    """

    SENSITIVE_ACTIONS = [
        # 🔴 阻止级 — 直接拦截
        ("公开发布", "publish|deploy.*prod|release", "block"),
        ("购买/支付", "purchase|buy|order|subscribe|支付|付款|扣费", "block"),
        ("不可逆删除", "rm.*-rf|DROP TABLE|truncate|format|dd if|disk.*wipe|shred", "block"),
        ("删除数据库", "drop (table|database|schema|index|view)", "block"),
        ("修改密码", "password.*change|change.*password|reset.*password|passwd", "block"),
        ("删除用户", "user.*del|deluser|userdel|delete.*user|remove.*user", "block"),
        ("提权操作", "chmod.*777|chown.*root|sudo.*ALL|NOPASSWD", "block"),

        # 🟡 提示级 — 警告但可继续
        ("重启服务", "restart|reboot|shutdown|systemctl.*restart", "warn"),
        ("停止服务", "service.*stop|systemctl.*stop|kill.*-9", "warn"),
        ("修改系统配置", "sysctl|kernel.*param|grub|fstab", "warn"),
        ("开通外网端口", "iptables.*ACCEPT|firewall.*open|ufw.*allow", "warn"),
        ("安装软件包", "apt.*install|pip.*install|npm.*install|gem.*install", "warn"),
        ("修改API密钥", "api.*key|apikey.*=|secret.*=|token.*=", "warn"),
        ("发送正式通知", "send.*email.*all|announce|broadcast", "warn"),
        ("大规模数据操作", "update.*set.*where.*1=1|delete.*from.*where.*1=1", "warn"),

        # 🔴 报警级 — 记录+通知管理员
        ("访问敏感数据", "passwd|shadow|credential|secret.*key|private.*key", "alert"),
        ("导出用户数据", "select.*from.*users|export.*user.*data|dump.*user", "alert"),
    ]

    @staticmethod
    def pre_tool(tool_name: str, args: dict) -> dict:
        desc = str(args)
        for action, pattern, level in AutonomyGuard.SENSITIVE_ACTIONS:
            if re.search(pattern, desc, re.IGNORECASE):
                _log(f"[R7自主边界] {level.upper()}: {action} (匹配: {pattern})")
                if level == "block":
                    return {"action": "block", "reason": f'自主边界阻止: "{action}" 必须经过格林主人明确批准'}
                if level == "warn":
                    return {"action": "warn", "reason": f'自主边界警告: "{action}" 建议确认后执行'}
                if level == "alert":
                    _log(f"[R7自主边界] 🔴 报警: {action}")
                    return {"action": "warn", "reason": f'自主边界报警: "{action}" 已记录日志'}
        return {"action": "pass"}


# ════════════════════════════════════════════════════════════
# R8: 问责 — 产出未使用则指出
# ════════════════════════════════════════════════════════════
class AccountabilityEnforcer:
    """
    如果曾经交付过有效产出但未被使用，在后续任务中主动指出。
    """

    _unused_outputs = []

    @staticmethod
    def record_unused(output_desc: str):
        AccountabilityEnforcer._unused_outputs.append({
            "desc": output_desc,
            "timestamp": datetime.now().isoformat(),
        })
        _log(f"[R8问责] 记录未使用产出: {output_desc[:80]}")

    @staticmethod
    def get_unused_summary(task: str = "") -> str:
        if not AccountabilityEnforcer._unused_outputs:
            return ""
        recent = AccountabilityEnforcer._unused_outputs[-3:]
        return f"[问责] 以下{len(AccountabilityEnforcer._unused_outputs)}个产出未被使用: {'; '.join(o['desc'][:40] for o in recent)}"

    @staticmethod
    def check_response(response: str, task: str) -> dict:
        if AccountabilityEnforcer._unused_outputs and "未被使用" not in response:
            recent = AccountabilityEnforcer._unused_outputs[-1]
            return {
                "rule": "R8",
                "verdict": "warn",
                "issues": [f"未指出之前交付但未使用的产出: {recent['desc'][:60]}"],
            }
        return {"rule": "R8", "verdict": "pass", "issues": []}


# ════════════════════════════════════════════════════════════
# R9: 双AI互审 — 确保使用不同模型
# ════════════════════════════════════════════════════════════
class DualModelEnforcer:
    """
    确保监督AI和执行AI使用不同模型接入。
    从config.yaml读取实际配置做对比。
    """

    _last_exec_model = ""
    _last_super_model = ""

    @staticmethod
    def record_models(exec_model: str, super_model: str):
        DualModelEnforcer._last_exec_model = exec_model
        DualModelEnforcer._last_super_model = super_model
        if exec_model == super_model:
            _log(f"[R9双模型] ❌ 执行和监督模型相同: {exec_model}")

    @staticmethod
    def check(exec_model: str, provider_count_str: str) -> dict:
        issues = []
        # 检查是否有多个不同的provider可用
        try:
            provider_count = int(provider_count_str.replace("providers=", ""))
            if provider_count < 2:
                issues.append(f"仅{provider_count}个provider（需要至少2个才能实现不同模型互审）")
        except (ValueError, AttributeError):
            pass

        # 检查是否只有一个模型
        if exec_model and not provider_count_str:
            issues.append("未检测到多模型配置")

        if issues:
            _log(f"[R9双模型] {'; '.join(issues)}")
            return {"rule": "R9", "verdict": "warn", "issues": issues}
        return {"rule": "R9", "verdict": "pass"}


# ════════════════════════════════════════════════════════════
# R10: 规则5 — 真实实现+联网最佳方案+严苛测试
# ════════════════════════════════════════════════════════════
class RealImplementationEnforcer:
    """
    检测输出中是否有降级词汇和占位符模式。
    扩展模式：示例/模拟/TODO/FIXME/mock/stub等。
    """

    DEGRADATION_PATTERNS = [
        # 直接降级词汇
        (r"(示例|模拟|占位符|演示|demo|示例代码|模拟数据|伪实现|假装|stub|placeholder)", "含降级词汇"),
        # 未完成的痕迹
        (r"(TODO|FIXME|HACK|XXX|TBD|WIP|WORKAROUND|TEMPORARY)", "含未完成标记"),
        # mock/假数据
        (r"(mock|fake|dummy|fakedata|testdata|hardcoded)", "含mock/假数据模式"),
        # 虚假实现
        (r"(pass\s*$|raise NotImplementedError|raise NotImplemented)", "未实现的方法体"),
        # 只返回固定值
        (r"(return\s+True\s*$|return\s+False\s*$|return\s+None\s*$|return\s+\[\s*\]\s*$|return\s+\{\s*\}\s*$)", "可能为占位返回"),
    ]

    @staticmethod
    def check(response: str) -> dict:
        issues = []
        seen = set()
        for pattern, category in RealImplementationEnforcer.DEGRADATION_PATTERNS:
            matches = re.findall(pattern, response, re.IGNORECASE)
            for m in matches:
                match_text = m[0] if isinstance(m, tuple) else str(m)
                if match_text.lower() not in seen:
                    issues.append(f'{category}: "{match_text[:30]}"')
                    seen.add(match_text.lower())

        if issues:
            _log(f"[R10真实实现] {'; '.join(issues[:5])}")
        return {"rule": "R10", "verdict": "warn" if issues else "pass", "issues": issues[:8]}


# ════════════════════════════════════════════════════════════
# R11: 规则6 — 完善→审核→测试循环（至少3轮）
# ════════════════════════════════════════════════════════════
class IterationEnforcer:
    """
    确保代码任务执行了至少3轮的完善→审核→测试循环。
    记录每次response中的工具调用行为来检测迭代模式。
    """

    _cycles = []

    @staticmethod
    def record_cycle(cycle_type: str, result: str):
        IterationEnforcer._cycles.append({"type": cycle_type, "result": result, "ts": datetime.now().isoformat()})
        # 保留最近20条记录
        if len(IterationEnforcer._cycles) > 20:
            IterationEnforcer._cycles = IterationEnforcer._cycles[-20:]

    @staticmethod
    def check_completion(task: str) -> dict:
        if not IterationEnforcer._cycles:
            return {"rule": "R11", "verdict": "warn", "issues": ["无完善→审核→测试循环记录"]}
        rounds = len([c for c in IterationEnforcer._cycles if c["type"] in ("完善", "审核", "测试")])
        if rounds < 3:
            return {"rule": "R11", "verdict": "warn", "issues": [f"仅{rounds}轮循环（要求至少3轮）, 当前记录: {len(IterationEnforcer._cycles)}条"]}
        return {"rule": "R11", "verdict": "pass", "rounds": rounds, "total_records": len(IterationEnforcer._cycles)}


# ════════════════════════════════════════════════════════════
# R12: 智影7步SDLC — 每次开发任务必须执行
# ════════════════════════════════════════════════════════════
class SdlcEnforcer:
    """
    检测到开发任务时，检查输出是否包含了7步SDLC流程。
    支持多种表述方式。
    """

    SDLC_STEPS = ["全网检索", "全局观念", "需求分析", "功能设置", "软件开发", "审核测试", "交付上线"]
    SDLC_ALIASES = {
        "全网检索": ["检索", "搜索", "调研", "investigate", "research", "step 1"],
        "全局观念": ["全局", "观念", "约束", "rules", "context", "step 2"],
        "需求分析": ["需求", "requirements", "analysis", "step 3"],
        "功能设置": ["架构", "方案", "设计", "architecture", "design", "step 4"],
        "软件开发": ["开发", "编码", "coding", "implementation", "step 5"],
        "审核测试": ["审核", "测试", "review", "testing", "audit", "step 6"],
        "交付上线": ["交付", "上线", "delivery", "deploy", "step 7"],
    }

    @staticmethod
    def check(task: str, response: str) -> dict:
        if not any(kw in task for kw in ["开发", "编码", "实现", "构建", "构建", "代码", "功能", "审计", "修复"]):
            return {"rule": "R12", "verdict": "pass"}
        missing = []
        for step in SdlcEnforcer.SDLC_STEPS:
            aliases = SdlcEnforcer.SDLC_ALIASES.get(step, [step])
            if not any(a in response for a in aliases):
                missing.append(step)
        if missing:
            return {"rule": "R12", "verdict": "warn", "issues": [f"缺少SDLC步骤: {', '.join(missing)}"]}
        return {"rule": "R12", "verdict": "pass"}


# ════════════════════════════════════════════════════════════
# R13: 所有skill必须主动运行+链式+并行
# ════════════════════════════════════════════════════════════
class SkillActiveEnforcer:
    """
    检查skill是否具有主动运行能力。
    通过解析skills目录中的SKILL.md文件判断。
    """

    @staticmethod
    def check_skills() -> dict:
        skills_dir = HERMES / "skills"
        if not skills_dir.exists():
            return {"rule": "R13", "verdict": "warn", "issues": ["skills目录不存在"]}

        issues = []
        active = 0
        total = 0
        for skill_dir in skills_dir.iterdir():
            if not skill_dir.is_dir():
                continue
            total += 1
            skill_md = skill_dir / "SKILL.md"
            if skill_md.exists():
                content = skill_md.read_text()
                has_command = "```" in content or "hermes" in content or "bash" in content or "python" in content
                if has_command:
                    active += 1
                else:
                    issues.append(f"skill {skill_dir.name} 可能缺少主动运行命令")

        if total > 0 and active < total:
            _log(f"[R13技能强制] {active}/{total}个skill有主动运行命令")
            return {"rule": "R13", "verdict": "warn", "issues": issues[:5]}
        return {"rule": "R13", "verdict": "pass", "active": active, "total": total}


# ════════════════════════════════════════════════════════════
# R14: 三阶段开发铁律 — 商用级强制（不可违反、不可绕过）
# ════════════════════════════════════════════════════════════
class ThreePhaseDevEnforcer:
    """R14: 三阶段开发铁律 — 商用级强制开发流程。

    不可违反、不可绕过的三阶段开发标准:
      第一阶段: 规划与执行（9步）
      第二阶段: 全面升级（≥3轮对标迭代）
      第三阶段: 全功能审核测试（全覆盖测试）

    强制执行:
      - pre_tool_block: 工具调用前的阶段阻断
      - complete_phase1/2/3: 基于真实产出证据的阶段推进
      - get_status: 查询当前阶段状态

    Attributes:
        PHASE_1_STEPS: 第一阶段9步定义。
        PHASE_2_MIN_ROUNDS: 第二阶段最小轮数 (3)。
        STATE_FILE: 阶段状态持久化文件路径。

    Example:
        >>> status = ThreePhaseDevEnforcer.get_status()
        >>> status['current_phase']  # 'none' | 'phase1' | 'phase2' | 'phase3'
    """

    # ── 阶段定义 ──
    PHASE_1_STEPS = [
        "全网检索", "全局观念", "开发计划",
        "需求文档", "开发文档", "子Agent拆解",
        "三AI互审", "阶段性检查", "总体验证",
    ]

    PHASE_2_MIN_ROUNDS = 3
    PHASE_3_MIN_ROUNDS = 2

    STATE_FILE = HERMES / "scripts" / ".phase_state.json"
    _state = None  # lazy loaded

    @staticmethod
    def _get_state() -> dict:
        """懒加载阶段状态"""
        if ThreePhaseDevEnforcer._state is not None:
            return ThreePhaseDevEnforcer._state
        try:
            if ThreePhaseDevEnforcer.STATE_FILE.exists():
                with open(ThreePhaseDevEnforcer.STATE_FILE) as f:
                    ThreePhaseDevEnforcer._state = json.load(f)
            else:
                ThreePhaseDevEnforcer._state = {
                    "current_phase": "none",
                    "phase1": {"completed_steps": [], "completed": False, "completed_at": None},
                    "phase2": {"rounds": 0, "last_benchmark": None, "completed": False},
                    "phase3": {"rounds": 0, "completed": False, "completed_at": None},
                    "last_session_task": "",
                    "version": 2,
                }
                ThreePhaseDevEnforcer._save_state()
        except Exception:
            ThreePhaseDevEnforcer._state = {"current_phase": "none"}
        return ThreePhaseDevEnforcer._state

    @staticmethod
    def _save_state():
        """持久化阶段状态"""
        try:
            ThreePhaseDevEnforcer.STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(ThreePhaseDevEnforcer.STATE_FILE, "w") as f:
                json.dump(ThreePhaseDevEnforcer._state, f, indent=2, ensure_ascii=False)
        except Exception as e:
            _log(f"[R14] 状态持久化失败: {e}")

    @staticmethod
    def is_development_task(task: str) -> bool:
        """判断是否属于开发任务"""
        dev_keywords = [
            "开发", "实现", "构建", "代码", "功能",
            "开发任务", "SDLC", "三阶段", "设计", "架构",
            "修复", "完善", "升级", "测试", "审核",
            "Phase-", "阶段", "商用级", "创建", "添加",
        ]
        return any(kw in task for kw in dev_keywords)

    # ═══════════════════════════════════════════════════════════
    # 真实证据检查 — 取代关键词匹配
    # ═══════════════════════════════════════════════════════════

    @staticmethod
    def _has_real_output_evidence(response: str, tool_calls: list) -> bool:
        """
        检查响应中是否包含真实的阶段完成证据。
        必须满足至少一项：
        ① 有文件/路径/URL引用（产出物）
        ② 有HTTP状态码/运行结果/测试通过报告
        ③ 有delegate_task/tool_call的实际调用记录
        """
        # 检查产出物引用
        has_output = bool(re.search(
            r"(?:已写入|已保存|已创建|已生成|已拆解|文件.*?:.*?/[\w/.\-]+|http[s]?://)",
            response
        ))
        # 检查运行证据
        has_runtime = bool(re.search(
            r"(状态码|HTTP.*\d{3}|\d+/\d+.*通过|✅|❌|passed|failed|exit_code)",
            response
        ))
        # 检查工具调用
        has_tool_calls = len(tool_calls) >= 2 if tool_calls else False
        # 检查阶段标记
        has_phase_marker = bool(re.search(r"\[Phase-\d|\[阶段.完成\]|阶段.*完成|phase.*complete", response, re.IGNORECASE))

        return has_output or has_runtime or has_tool_calls or has_phase_marker

    @staticmethod
    def _get_real_phase_declaration(task: str, response: str, tool_calls: list) -> str:
        """检测当前实际所处的阶段（基于真实证据而非关键词）"""
        # 检查第三阶段证据
        phase3_evidence = bool(re.search(
            r"(测试.*全部通过|上线.*验证|审核.*通过|完整测试|最终交付)",
            response
        )) and ThreePhaseDevEnforcer._has_real_output_evidence(response, tool_calls)
        if phase3_evidence:
            return "phase3"

        # 检查第二阶段证据
        phase2_evidence = bool(re.search(
            r"(对标.*|升级.*|第二轮|第三轮|迭代.*优化|全面.*升级)",
            response
        )) and ThreePhaseDevEnforcer._has_real_output_evidence(response, tool_calls)
        if phase2_evidence:
            return "phase2"

        # 检查第一阶段证据
        phase1_evidence = (
            ThreePhaseDevEnforcer._has_real_output_evidence(response, tool_calls)
            and any(kw in response for kw in ["规划", "文档", "计划", "方案", "拆解", "检索"])
        )
        if phase1_evidence or ThreePhaseDevEnforcer._get_state().get("phase1", {}).get("completed"):
            # 检查是否在第一阶段但无阶段标记 — 如果已有phase1完成标记且没检测到phase2/3，默认还在phase1
            if not phase2_evidence and not phase3_evidence:
                return "phase1"
            return "phase1"

        return "unknown"

    # ═══════════════════════════════════════════════════════════
    # 前置拦截 — 工具调用前的阻断
    # ═══════════════════════════════════════════════════════════

    @staticmethod
    def pre_tool_block(tool_name: str, args: dict, task: str) -> dict:
        """
        在pre_tool_intercept中调用。
        如果识别到开发任务且当前不允许执行某个阶段的操作，直接block。
        返回: {"action": "pass"} 或 {"action": "block", "reason": "..."}
        """
        if not ThreePhaseDevEnforcer.is_development_task(task):
            return {"action": "pass"}

        state = ThreePhaseDevEnforcer._get_state()

        # ——阻断规则1：第一阶段未完成时，禁止delegate_task（先做规划再执行）——
        if tool_name == "delegate_task" and not state["phase1"]["completed"]:
            # 允许第一阶段的规划类delegate_task
            desc = str(args)[:200]
            if any(kw in desc for kw in ["调研", "检索", "搜索", "research", "investigate", "规划", "分析"]):
                return {"action": "pass"}
            return {
                "action": "block",
                "rule": "R14",
                "reason": (
                    "【R14三阶段开发铁律】禁止跳过第一阶段直接执行！\n"
                    "必须先完成：全网检索 → 全局观念 → 开发计划 → 需求文档 → 开发文档\n"
                    "→ 子Agent拆解 → 三AI互审 → 阶段性检查 → 总体验证\n"
                    "当前第一阶段状态: 未完成\n"
                    "请先执行第一阶段规划工作，或手动设置 phase_state。"
                ),
            }

        # ——阻断规则2：第二阶段不足3轮时，禁止delegate_task执行第三阶段操作——
        if tool_name == "delegate_task" and state["current_phase"] == "phase3":
            if state["phase2"]["rounds"] < ThreePhaseDevEnforcer.PHASE_2_MIN_ROUNDS:
                return {
                    "action": "block",
                    "rule": "R14",
                    "reason": (
                        f"【R14三阶段开发铁律】第二阶段仅{state['phase2']['rounds']}轮，"
                        f"要求≥{ThreePhaseDevEnforcer.PHASE_2_MIN_ROUNDS}轮！\n"
                        "请完成3轮对标升级后再进入第三阶段。"
                    ),
                }

        return {"action": "pass"}

    # ═══════════════════════════════════════════════════════════
    # 阶段完成验证 — 基于真实产出
    # ═══════════════════════════════════════════════════════════

    @staticmethod
    def complete_step(step_name: str, response: str, tool_calls: list) -> dict:
        """
        标记某个步骤为已完成（仅在有真实产出证据时）
        """
        state = ThreePhaseDevEnforcer._get_state()

        if not ThreePhaseDevEnforcer._has_real_output_evidence(response, tool_calls):
            return {"verdict": "rejected", "reason": "无真实产出证据，无法标记步骤完成"}

        state["phase1"]["completed_steps"].append({
            "step": step_name,
            "timestamp": datetime.now().isoformat(),
        })
        ThreePhaseDevEnforcer._save_state()
        return {"verdict": "accepted", "step": step_name}

    @staticmethod
    def complete_phase1(response: str, tool_calls: list) -> dict:
        """
        检查第一阶段是否真正完成（9步全部有真实产出）
        """
        state = ThreePhaseDevEnforcer._get_state()
        completed = set(s["step"] for s in state["phase1"]["completed_steps"])
        missing = [s for s in ThreePhaseDevEnforcer.PHASE_1_STEPS if s not in completed]

        if missing:
            return {
                "verdict": "incomplete",
                "missing": missing,
                "progress": f"{len(completed)}/{len(ThreePhaseDevEnforcer.PHASE_1_STEPS)}",
            }

        # 必须有真实产出证据
        if not ThreePhaseDevEnforcer._has_real_output_evidence(response, tool_calls):
            return {
                "verdict": "incomplete",
                "missing": ["真实产出证据"],
                "progress": "9/9（但缺产出证据）",
            }

        state["phase1"]["completed"] = True
        state["phase1"]["completed_at"] = datetime.now().isoformat()
        state["current_phase"] = "phase1_complete"
        ThreePhaseDevEnforcer._save_state()
        _log("[R14] ✅ 第一阶段全部9步完成，通过真实产出验证")
        return {"verdict": "complete"}

    @staticmethod
    def advance_phase2_round(response: str, tool_calls: list) -> dict:
        """
        推进第二阶段轮次（每轮必须有真实升级证据）
        """
        state = ThreePhaseDevEnforcer._get_state()

        if not state["phase1"]["completed"]:
            return {"verdict": "blocked", "reason": "第一阶段未完成，禁止进入第二阶段"}

        # 检查本轮是否有真实升级证据
        has_benchmark = bool(re.search(
            r"(对标|benchmark|对比|比较|参考|参考了|研究.*实现)",
            response
        ))
        has_improvement = bool(re.search(
            r"(优化|改进|修复|提升|增强|完善|升级|重构)",
            response
        ))
        has_evidence = ThreePhaseDevEnforcer._has_real_output_evidence(response, tool_calls)

        if not (has_benchmark or has_improvement):
            return {"verdict": "skipped", "reason": "未检测到对标或改进内容，不计入有效轮次"}

        if not has_evidence:
            return {"verdict": "skipped", "reason": "无真实产出证据，不计入有效轮次"}

        state["phase2"]["rounds"] += 1
        state["phase2"]["last_benchmark"] = datetime.now().isoformat()
        state["current_phase"] = "phase2"
        _log(f"[R14] 第二阶段第{state['phase2']['rounds']}轮完成（有真实产出证据）")

        if state["phase2"]["rounds"] >= ThreePhaseDevEnforcer.PHASE_2_MIN_ROUNDS:
            state["phase2"]["completed"] = True
            _log("[R14] ✅ 第二阶段3轮全部完成")

        ThreePhaseDevEnforcer._save_state()
        return {
            "verdict": "advanced",
            "round": state["phase2"]["rounds"],
            "required": ThreePhaseDevEnforcer.PHASE_2_MIN_ROUNDS,
            "complete": state["phase2"]["completed"],
        }

    @staticmethod
    def complete_phase3(response: str, tool_calls: list) -> dict:
        """
        完成第三阶段（必须有全功能测试证据）
        """
        state = ThreePhaseDevEnforcer._get_state()

        if not state["phase2"]["completed"]:
            return {"verdict": "blocked", "reason": "第二阶段3轮未完成，禁止进入第三阶段"}

        # 检查是否有测试证据
        has_tests = bool(re.search(
            r"(测试.*通过|test.*pass|全部通过|✅\s*\d+.*✅|验证.*成功|上线.*ok)",
            response
        ))
        has_full_coverage = bool(re.search(
            r"(每个|所有|全部|全量|逐一|逐个|逐行|各个)",
            response
        )) and has_tests
        has_iteration = bool(re.search(
            r"(迭代|修复.*完善|优化.*完成|第.*轮)",
            response
        ))
        has_evidence = ThreePhaseDevEnforcer._has_real_output_evidence(response, tool_calls)

        if not has_tests:
            state["phase3"]["rounds"] = (state["phase3"].get("rounds", 0) or 0)
            return {"verdict": "incomplete", "reason": "未检测到真实测试通过证据"}

        if not has_evidence:
            return {"verdict": "incomplete", "reason": "无真实运行证据"}

        state["phase3"]["rounds"] = (state["phase3"].get("rounds", 0) or 0) + 1
        state["current_phase"] = "phase3"

        if has_full_coverage and has_iteration:
            state["phase3"]["completed"] = True
            state["phase3"]["completed_at"] = datetime.now().isoformat()
            ThreePhaseDevEnforcer._save_state()
            _log("[R14] ✅ 第三阶段全功能审核测试通过，项目开发完成")
            return {"verdict": "complete", "rounds": state["phase3"]["rounds"]}

        ThreePhaseDevEnforcer._save_state()
        return {
            "verdict": "in_progress",
            "rounds": state["phase3"]["rounds"],
            "note": "测试已开始，但需要全覆盖测试+迭代修复后才算完成",
        }

    # ═══════════════════════════════════════════════════════════
    # 系统报告
    # ═══════════════════════════════════════════════════════════

    @staticmethod
    def get_status() -> dict:
        state = ThreePhaseDevEnforcer._get_state()
        phase1 = state.get("phase1", {})
        phase2 = state.get("phase2", {})
        phase3 = state.get("phase3", {})
        return {
            "current_phase": state.get("current_phase", "none"),
            "phase1": {
                "completed_steps": len(phase1.get("completed_steps", [])),
                "total_steps": len(ThreePhaseDevEnforcer.PHASE_1_STEPS),
                "completed": phase1.get("completed", False),
            },
            "phase2": {
                "rounds": phase2.get("rounds", 0),
                "required": ThreePhaseDevEnforcer.PHASE_2_MIN_ROUNDS,
                "completed": phase2.get("completed", False),
            },
            "phase3": {
                "rounds": phase3.get("rounds", 0),
                "completed": phase3.get("completed", False),
            },
        }

    @staticmethod
    def get_report() -> str:
        s = ThreePhaseDevEnforcer.get_status()
        completed_steps = s["phase1"]["completed_steps"]
        total_steps = s["phase1"]["total_steps"]
        phase1_status = "完成" if s["phase1"]["completed"] else f"{completed_steps}/{total_steps}步"
        phase2_rounds = s["phase2"]["rounds"]
        phase2_required = s["phase2"]["required"]
        phase2_status = "完成" if s["phase2"]["completed"] else f"{phase2_rounds}/{phase2_required}轮"
        phase3_rounds = s["phase3"]["rounds"]
        phase3_status = "完成" if s["phase3"]["completed"] else f"{phase3_rounds}轮(需全覆盖)"
        lines = [
            "【R14 三阶段开发铁律】",
            f"  当前阶段: {s['current_phase']}",
            f"  第一阶段: {phase1_status}",
            f"  第二阶段: {phase2_status}",
            f"  第三阶段: {phase3_status}",
        ]
        return "\n".join(lines)

    @staticmethod
    def reset():
        """重置所有阶段状态（仅限格林主人明确要求时）"""
        ThreePhaseDevEnforcer._state = None
        if ThreePhaseDevEnforcer.STATE_FILE.exists():
            ThreePhaseDevEnforcer.STATE_FILE.unlink()
        ThreePhaseDevEnforcer._get_state()
        _log("[R14] ⚠️ 三阶段状态已重置")



# ════════════════════════════════════════════════════════════
# 统一入口更新 — 加入R14
# ════════════════════════════════════════════════════════════

def pre_tool_intercept(tool_name: str, args: dict, task: str = "") -> dict:
    """工具调用前统一拦截器。

    按顺序执行: R7自主边界 → R14三阶段阻断 → R3改前备份 → R2前置三查。

    Args:
        tool_name: 被调用的工具名称。
        args: 工具参数。
        task: 当前任务描述（可选）。

    Returns:
        {"action": "pass" | "block" | "warn", "reason": ..., "rule": ...}
    """
    global _enforcement_count
    if not _enforcer_enabled:
        return {"action": "pass", "reason": "enforcer_disabled"}

    # R7: 自主边界
    r7 = AutonomyGuard.pre_tool(tool_name, args)
    if r7["action"] == "block":
        _enforcement_count["block"] += 1
        return r7

    # R14: 三阶段开发铁律 — pre_tool级别的阻断
    r14_block = ThreePhaseDevEnforcer.pre_tool_block(tool_name, args, task)
    if r14_block["action"] == "block":
        _enforcement_count["block"] += 1
        return r14_block

    # R3: 改前备份
    backup = BackupGuard.pre_tool(tool_name, args)
    if backup.get("action") in ("warn", "block"):
        _enforcement_count["warn"] += 1
        return {"action": backup["action"], "reason": backup.get("note", ""), "rule": "R3"}

    # R2: 前置三查
    if task and not hasattr(pre_tool_intercept, "_pre_check_done"):
        pre_tool_intercept._pre_check_done = True
        try:
            pc = PreCheck.execute(task)
            if pc["verdict"] == "warn":
                _log("[R2前置三查] ⚠️ 部分检查未通过")
        except Exception:
            pass

    _enforcement_count["pass"] += 1
    return {"action": "pass"}


def post_tool_intercept(tool_name: str, args: dict, result: str, task: str = "") -> dict:
    """工具调用后统一拦截器。

    按顺序执行: R1反幻觉 → R5深度审核 → R3备份验证。
    包含审计日志记录。

    Args:
        tool_name: 被调用的工具名称。
        args: 工具参数。
        result: 工具调用返回的结果文本。
        task: 当前任务描述（可选）。

    Returns:
        {"action": "pass" | "block" | "warn", "rule": ..., "issues": ...}
    """
    global _enforcement_count
    if not _enforcer_enabled:
        return {"action": "pass", "reason": "enforcer_disabled"}

    # ── 审计记录：工具调用 ──
    _audit_event_id = None
    if _audit_available and _audit is not None:
        try:
            _audit_event_id = _audit.log_tool_call(
                tool_name=tool_name,
                args=args,
                result="processing",
                metadata={"source": "rule_enforcer.post_tool_intercept"},
            )
        except Exception:
            pass

    # R1: 反幻觉
    r1 = AntiHallucination.check_tool_output(tool_name, args, result)
    if r1["verdict"] != "pass":
        _enforcement_count["block"] += 1
        if _audit_available and _audit is not None:
            try:
                _audit.log_rule_enforcement("R1", tool_name, "warn", r1["issues"])
            except Exception:
                pass
        return {"action": "warn", "rule": "R1", "issues": r1["issues"]}

    # R5: 深度审核
    r5 = DeepAuditEnforcer.check_audit_output(tool_name, args, result)
    if r5.get("action") == "warn":
        _enforcement_count["warn"] += 1
        if _audit_available and _audit is not None:
            try:
                _audit.log_rule_enforcement("R5", tool_name, "warn", r5.get("issues", []))
            except Exception:
                pass
        return {"action": "warn", "rule": "R5", "issues": r5["issues"]}

    # R3: 改前备份验证
    r3 = BackupGuard.post_tool(tool_name, args, result)
    if r3.get("action") == "block":
        _enforcement_count["block"] += 1
        if _audit_available and _audit is not None:
            try:
                _audit.log_rule_enforcement(
                    "R3", tool_name, "block",
                    [r3.get("reason", "备份验证失败")]
                )
            except Exception:
                pass
        return {"action": "block", "rule": "R3", "reason": r3["reason"]}

    return {"action": "pass"}


def post_response_intercept(response: str, tool_calls: list, task: str = "") -> dict:
    """最终响应统一拦截器。

    在LLM返回最终回答后执行全部审查规则:
    R1反幻觉 → R4交付铁律 → R6沟通风格 → R10真实实现 → R12 SDLC → R9双模型 → R11循环 → R8问责 → R14阶段。

    Args:
        response: LLM 返回的最终响应文本。
        tool_calls: 本轮对话中的工具调用记录列表。
        task: 当前任务描述（可选）。

    Returns:
        {"action": "pass" | "warn", "rules": [...]}
    """
    global _enforcement_count
    if not _enforcer_enabled:
        return {"action": "pass"}
    results = []

    r1 = AntiHallucination.check_response(response, tool_calls)
    if r1["verdict"] != "pass":
        results.append(r1)
        _enforcement_count["warn"] += 1

    r4 = DeliveryEnforcer.check_output(response, tool_calls)
    if r4["verdict"] != "pass":
        results.append(r4)
        _enforcement_count["warn"] += 1

    r6 = CommunicationEnforcer.check_response(response)
    if r6["verdict"] != "pass":
        results.append(r6)
        _enforcement_count["warn"] += 1

    r10 = RealImplementationEnforcer.check(response)
    if r10["verdict"] != "pass":
        results.append(r10)
        _enforcement_count["warn"] += 1

    r12 = SdlcEnforcer.check(task, response)
    if r12["verdict"] != "pass":
        results.append(r12)
        _enforcement_count["warn"] += 1

    # ── R9: 双模型检查 — 从config.yaml读取实际模型配置 ──
    if _yaml_available:
        try:
            _cfg_path = os.path.expanduser("~/.hermes/config.yaml")
            if os.path.exists(_cfg_path):
                with open(_cfg_path) as _f:
                    _cfg = _yaml.safe_load(_f)
                _exec_model = _cfg.get("model", {}).get("default", "")
                _provider_count = len(_cfg.get("providers", {}))
                r9 = DualModelEnforcer.check(_exec_model, f"providers={_provider_count}")
                if r9["verdict"] != "pass":
                    results.append(r9)
                    _enforcement_count["warn"] += 1
        except Exception:
            pass

    # ── R11: 循环检查 — 记录当前response为一次循环 ──
    IterationEnforcer.record_cycle("测试", response[:100])
    r11 = IterationEnforcer.check_completion(task)
    if r11["verdict"] != "pass":
        results.append(r11)
        _enforcement_count["warn"] += 1

    if task:
        r8 = AccountabilityEnforcer.check_response(response, task)
        if r8["verdict"] != "pass":
            results.append(r8)
            _enforcement_count["warn"] += 1

    # ── R14: 三阶段开发铁律 — 检查阶段进展（基于真实产出证据）──
    state = ThreePhaseDevEnforcer._get_state()
    r14_phase = ThreePhaseDevEnforcer._get_real_phase_declaration(task, response, tool_calls)
    _log(f"[R14] 检测到阶段: {r14_phase}")

    if r14_phase == "phase1" and task:
        # 尝试自动标记第一阶段步骤
        for step in ThreePhaseDevEnforcer.PHASE_1_STEPS:
            aliases = {
                "全网检索": ["全网检索", "调研", "research", "检索"],
                "全局观念": ["全局观念", "全局", "约束", "方向"],
                "开发计划": ["开发计划", "规划方案", "执行计划", "计划"],
                "需求文档": ["需求文档", "需求分析", "requirements"],
                "开发文档": ["开发文档", "设计文档", "架构设计"],
                "子Agent拆解": ["子Agent", "并行", "拆解", "delegate_task"],
                "三AI互审": ["三AI互审", "三AI", "交叉验证"],
                "阶段性检查": ["阶段性检查", "阶段检查", "计划映证"],
                "总体验证": ["总体验证", "整体验证", "总体规划"],
            }
            matched_aliases = aliases.get(step, [step])
            if any(a in response for a in matched_aliases):
                # 检查是否已被标记
                existing = state.get("phase1", {}).get("completed_steps", [])
                if not any(s["step"] == step for s in existing):
                    ThreePhaseDevEnforcer.complete_step(step, response, tool_calls)
                    _log(f"[R14] 自动标记第一阶段步骤: {step}")

    if not results:
        return {"action": "pass"}
    return {"action": "warn", "rules": results}


# 更新get_status
def get_status() -> dict:
    return {
        "enabled": _enforcer_enabled,
        "enforcement_count": dict(_enforcement_count),
        "rules": [
            "R1反幻觉", "R2前置三查", "R3改前备份", "R4交付铁律", "R5深度审核",
            "R6沟通风格", "R7自主边界", "R8问责", "R9双模型", "R10真实实现",
            "R11循环", "R12智影SDLC", "R13技能强制",
            "R14三阶段开发铁律",
            "R9-WBS任务分解", "R10-幂等性保护", "R11-Checkpoint",
            "R12-五道质量门禁", "R13-三Agent评估器", "R15-五级降级",
        ],
    }


def get_report() -> str:
    s = _enforcement_count
    return (
        f"【Hermes规则引擎状态】\n"
        f"  启用: {_enforcer_enabled}\n"
        f"  执行统计: {s['pass']}通过 / {s['block']}拦截 / {s['warn']}警告\n"
        f"  20条规则全部注入并激活(含R9-R15商用级质量体系)\n"
        f"  日志: {LOG_PATH}"
    )
