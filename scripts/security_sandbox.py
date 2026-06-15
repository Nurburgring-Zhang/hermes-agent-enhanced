#!/usr/bin/env python3
"""
Hermes Security Sandbox v1.0
============================
工具授权中间件 + 危险操作拦截 + 网络白名单 + 操作日志。

对标:
  - OWASP LLM Top 10: LLM04 (过度代理), LLM06 (敏感信息泄露)
  - NIST SP 800-53: AC-3 (访问控制), AU-2 (审计事件), CM-7 (最小功能)

核心功能:
  1. 工具授权中间件: 在执行工具前检查权限规则
  2. 危险操作拦截: 文件写入 /etc/、~/.ssh/、*.pem → 自动拒绝
  3. 网络白名单: 可选域名/IP 限制
  4. 操作日志: 每次工具调用记录到 JSONL
  5. 权限配置: 从 ~/.hermes/config/sandbox.yaml 加载规则

使用:
  from scripts.security_sandbox import SecuritySandbox
  sandbox = SecuritySandbox()
  ok, reason = sandbox.check("write_file", target="/etc/hosts")
  if ok:
      res = sandbox.wrap(tool_call)  # 记录到审计日志
"""

import fnmatch
import json
import logging
import os
import re
import threading
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

# ── 常量 ──
HERMES = Path(os.path.expanduser("~/.hermes"))
DEFAULT_CONFIG_PATH = HERMES / "config" / "sandbox.yaml"
DEFAULT_LOG_PATH = HERMES / "logs" / "sandbox_audit.jsonl"

# ── 默认规则 (启动时加载，若 YAML 不存在则使用此硬编码后备) ──
FALLBACK_BLOCKED_WRITE = [
    "/etc/**", "/boot/**", "/sys/**", "/proc/**",
    "~/.ssh/**", "~/.gnupg/**", "/root/.ssh/**",
    "**/*.pem", "**/*-key.pem", "**/id_rsa*",
    "**/id_ed25519*", "**/id_ecdsa*", "**/authorized_keys",
    "**/.env", "**/credentials.json", "**/service-account.json",
]

FALLBACK_BLOCKED_DELETE = [
    "/etc/**", "/home/**", "/root/**",
    "~/.hermes/config/**", "~/.hermes/scripts/**",
]

FALLBACK_BLOCKED_COMMANDS = [
    "rm -rf /", "dd if=", "mkfs.", ":(){ :|:& };:",
    "chmod 777 /", "chown -R", "> /dev/sda",
    "shutdown", "reboot", "halt", "poweroff",
    "systemctl stop", "systemctl disable", "iptables -F", "ufw disable",
    "crontab -r",
]

FALLBACK_BLOCKED_SUBSTRINGS = [
    "wget http://", "curl http://", "nc -l", "eval ",
]


def _expand_path(pattern: str) -> str:
    """将 ~ 展开为绝对路径，并标准化"""
    if pattern.startswith("~/"):
        expanded = os.path.expanduser(pattern)
        return os.path.normpath(expanded)
    return os.path.normpath(pattern)


def _path_matches(filepath: str, patterns: list[str]) -> bool:
    """检查 filepath 是否匹配任一 glob 模式。

    自动处理 ~ 展开。支持 ** 递归匹配。
    """
    normalized = _expand_path(filepath)
    for pattern in patterns:
        expanded_pattern = _expand_path(pattern)
        if fnmatch.fnmatch(normalized, expanded_pattern):
            return True
        # 也尝试不区分大小写匹配
        if fnmatch.fnmatch(normalized.lower(), expanded_pattern.lower()):
            return True
    return False


def _path_matches_any(filepath: str, pattern_list: list[str]) -> bool:
    """filepath 匹配列表中任一模式则返回 True"""
    if not pattern_list:
        return False
    return _path_matches(filepath, pattern_list)


# ═══════════════════════════════════════════════════════════════
# 速率限制器
# ═══════════════════════════════════════════════════════════════


class RateLimiter:
    """滑动窗口速率限制器（线程安全）"""

    def __init__(self, max_per_minute: int = 60):
        self.max_per_minute = max_per_minute
        self._window: list[float] = []
        self._lock = threading.Lock()

    def allow(self) -> bool:
        """返回 True 表示允许本次调用"""
        now = time.time()
        with self._lock:
            # 清理过期条目
            cutoff = now - 60.0
            self._window = [t for t in self._window if t > cutoff]
            if len(self._window) >= self.max_per_minute:
                return False
            self._window.append(now)
            return True

    def remaining(self) -> int:
        """返回剩余配额"""
        with self._lock:
            cutoff = time.time() - 60.0
            self._window = [t for t in self._window if t > cutoff]
            return max(0, self.max_per_minute - len(self._window))


# ═══════════════════════════════════════════════════════════════
# 沙箱核心
# ═══════════════════════════════════════════════════════════════


class SecuritySandbox:
    """安全沙箱 — 工具调用的守门人。

    流程:
      check() → 权限检查 (文件/网络/命令)
      wrap()  → 记录审计日志
    """

    def __init__(
        self,
        config_path: Path | str = DEFAULT_CONFIG_PATH,
        log_path: Path | str = DEFAULT_LOG_PATH,
    ):
        self.config_path = Path(config_path)
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

        # 加载配置
        self._config: dict[str, Any] = {}
        self._load_config()

        # 从配置中提取规则
        self._enabled: bool = self._config.get("sandbox", {}).get("enabled", True)
        self._deny_by_default: bool = self._config.get("sandbox", {}).get("deny_by_default", False)

        fs_cfg = self._config.get("filesystem", {})
        self._blocked_write: list[str] = fs_cfg.get("blocked_write_patterns", FALLBACK_BLOCKED_WRITE)
        self._blocked_delete: list[str] = fs_cfg.get("blocked_delete_patterns", FALLBACK_BLOCKED_DELETE)
        self._allowed_write: list[str] = fs_cfg.get("allowed_write_paths", [])

        cmd_cfg = self._config.get("command", {})
        self._blocked_commands: list[str] = cmd_cfg.get("blocked_commands", FALLBACK_BLOCKED_COMMANDS)
        self._blocked_substrings: list[str] = cmd_cfg.get("blocked_substrings", FALLBACK_BLOCKED_SUBSTRINGS)
        self._allowed_prefixes: list[str] = cmd_cfg.get("allowed_prefixes", [])

        net_cfg = self._config.get("network", {}).get("egress_filter", {})
        self._net_filter_enabled: bool = net_cfg.get("enabled", False)
        self._net_mode: str = net_cfg.get("mode", "whitelist")
        self._whitelist_domains: list[str] = net_cfg.get("whitelist_domains", [])
        self._blacklist_domains: list[str] = net_cfg.get("blacklist_domains", [])
        self._whitelist_ips: list[str] = net_cfg.get("whitelist_ips", [])
        self._blacklist_ips: list[str] = net_cfg.get("blacklist_ips", [])

        py_cfg = self._config.get("python", {})
        self._blocked_imports: list[str] = py_cfg.get("blocked_imports", [])
        self._block_dynamic_execution: bool = py_cfg.get("block_dynamic_execution", True)

        rl_cfg = self._config.get("rate_limit", {})
        self._rate_limit_enabled: bool = rl_cfg.get("enabled", True)
        rl_max = rl_cfg.get("max_tool_calls_per_minute", 60)
        self._tool_rate_limiter = RateLimiter(max_per_minute=rl_max)
        self._file_write_limiter = RateLimiter(
            max_per_minute=rl_cfg.get("max_file_writes_per_minute", 20)
        )

        notif_cfg = self._config.get("notifications", {})
        self._notify_on_block: bool = notif_cfg.get("on_block", True)
        self._notify_on_warn: bool = notif_cfg.get("on_warn", True)
        self._alert_threshold: int = notif_cfg.get("alert_threshold", 5)

        # 阻断计数器
        self._block_count: int = 0
        self._block_lock = threading.Lock()
        self._log_lock = threading.Lock()

        logger.info(
            "SecuritySandbox initialized: enabled=%s deny_by_default=%s blocked_write=%d patterns",
            self._enabled,
            self._deny_by_default,
            len(self._blocked_write),
        )

    # ── 配置加载 ──

    def _load_config(self) -> None:
        """从 YAML 文件加载配置，不存在则使用后备规则"""
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    self._config = yaml.safe_load(f) or {}
                logger.info("Loaded sandbox config from %s", self.config_path)
            except Exception as e:
                logger.error("Failed to load sandbox config: %s", e)
                self._config = {}
        else:
            logger.warning(
                "Sandbox config not found at %s, using fallback rules", self.config_path
            )
            self._config = {}

    def reload(self) -> None:
        """热重载配置"""
        self._load_config()
        # 重新提取规则 (re-init pattern lists)
        fs_cfg = self._config.get("filesystem", {})
        self._blocked_write = fs_cfg.get("blocked_write_patterns", FALLBACK_BLOCKED_WRITE)
        self._blocked_delete = fs_cfg.get("blocked_delete_patterns", FALLBACK_BLOCKED_DELETE)
        self._allowed_write = fs_cfg.get("allowed_write_paths", [])
        cmd_cfg = self._config.get("command", {})
        self._blocked_commands = cmd_cfg.get("blocked_commands", FALLBACK_BLOCKED_COMMANDS)
        self._blocked_substrings = cmd_cfg.get("blocked_substrings", FALLBACK_BLOCKED_SUBSTRINGS)
        self._enabled = self._config.get("sandbox", {}).get("enabled", True)
        logger.info("Sandbox config reloaded")

    # ── 安全检查核心 ──

    def check(
        self,
        tool_name: str,
        target: str | None = None,
        command: str | None = None,
        url: str | None = None,
    ) -> tuple[bool, str]:
        """检查工具调用是否被允许。

        Args:
            tool_name: 工具名称 (如 'write_file', 'terminal')
            target:   目标文件路径 (如 '/etc/hosts')
            command:  执行的命令 (如 'rm -rf /tmp/test')
            url:      网络请求 URL

        Returns:
            (allowed: bool, reason: str)
        """
        if not self._enabled:
            return True, "Sandbox disabled"

        # ── 速率限制检查 ──
        if self._rate_limit_enabled and not self._tool_rate_limiter.allow():
            self._increment_block()
            return False, "Rate limit exceeded"

        # ── 文件写入拦截 ──
        if target and tool_name in ("write_file", "patch", "move_file", "copy_file"):
            allowed, reason = self._check_file_write(target)
            if not allowed:
                self._increment_block()
                return False, reason

        # ── 文件删除拦截 ──
        if target and tool_name in ("delete_file", "rm", "unlink"):
            allowed, reason = self._check_file_delete(target)
            if not allowed:
                self._increment_block()
                return False, reason

        # ── 命令执行拦截 ──
        if command and tool_name in ("terminal", "execute", "shell"):
            allowed, reason = self._check_command(command)
            if not allowed:
                self._increment_block()
                return False, reason

        # ── 网络访问检查 ──
        if url and tool_name in ("http_request", "fetch", "download"):
            allowed, reason = self._check_network(url)
            if not allowed:
                self._increment_block()
                return False, reason

        # ── 默认拒绝模式 ──
        if self._deny_by_default:
            return False, f"deny_by_default: tool '{tool_name}' not in allowlist"

        return True, "ok"

    def _check_file_write(self, target: str) -> tuple[bool, str]:
        """检查文件写入是否允许"""
        # 先检查白名单
        if self._allowed_write and _path_matches_any(target, self._allowed_write):
            return True, "allowed_write_path"

        # 检查黑名单
        if _path_matches_any(target, self._blocked_write):
            return False, f"BLOCKED: write to protected path '{target}'"

        return True, "ok"

    def _check_file_delete(self, target: str) -> tuple[bool, str]:
        """检查文件删除是否允许"""
        if _path_matches_any(target, self._blocked_delete):
            return False, f"BLOCKED: delete of protected path '{target}'"
        return True, "ok"

    def _check_command(self, command: str) -> tuple[bool, str]:
        """检查命令是否允许执行"""
        # 检查危险子串
        for sub in self._blocked_substrings:
            if sub in command:
                return False, f"BLOCKED: command contains dangerous substring '{sub}'"

        # 检查完全匹配的危险命令
        for blocked in self._blocked_commands:
            if blocked in command:
                return False, f"BLOCKED: dangerous command pattern '{blocked}'"

        # 如果有前缀白名单，检查
        if self._allowed_prefixes:
            for prefix in self._allowed_prefixes:
                if command.strip().startswith(prefix):
                    return True, "ok"
            return False, "BLOCKED: command prefix not in allowlist"

        return True, "ok"

    def _check_network(self, url: str) -> tuple[bool, str]:
        """检查网络请求是否允许"""
        if not self._net_filter_enabled:
            return True, "network filter disabled"

        # 提取域名
        hostname = _extract_hostname(url)
        if not hostname:
            return True, "no hostname extracted"

        if self._net_mode == "whitelist":
            if _hostname_matches(hostname, self._whitelist_domains):
                return True, "domain in whitelist"
            return False, f"BLOCKED: domain '{hostname}' not in whitelist"

        elif self._net_mode == "blacklist":
            if _hostname_matches(hostname, self._blacklist_domains):
                return False, f"BLOCKED: domain '{hostname}' in blacklist"
            return True, "ok"

        return True, "ok"

    def _increment_block(self) -> None:
        """递增阻断计数器，超过阈值时发出告警"""
        with self._block_lock:
            self._block_count += 1
            if self._block_count >= self._alert_threshold:
                logger.warning(
                    "ALERT: %d consecutive blocks detected!", self._block_count
                )

    # ── 操作日志 ──

    def log(
        self,
        tool_name: str,
        result: str,
        target: str | None = None,
        command: str | None = None,
        url: str | None = None,
        reason: str | None = None,
        duration_ms: float | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """记录一次工具调用到 JSONL 审计日志。

        Returns:
            event_id
        """
        event_id = str(uuid.uuid4())
        event = {
            "event_id": event_id,
            "timestamp": datetime.now(UTC).isoformat(),
            "actor": "hermes_agent",
            "action": "tool_call",
            "tool_name": tool_name,
            "result": result,
            "target": target,
            "command": command,
            "url": url,
            "reason": reason,
            "duration_ms": duration_ms,
            "metadata": metadata or {},
        }

        # 去除 None 值
        event = {k: v for k, v in event.items() if v is not None}

        with self._log_lock:
            try:
                with open(self.log_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(event, ensure_ascii=False) + "\n")
            except Exception as e:
                logger.error("Failed to write sandbox audit log: %s", e)

        return event_id

    def wrap(
        self,
        tool_name: str,
        target: str | None = None,
        command: str | None = None,
        url: str | None = None,
    ) -> tuple[bool, str, str]:
        """一站式工具调用包装：检查 + 记录。

        返回 (allowed, reason, event_id)。
        先调用 check()，然后调用 log() 记录结果。

        Usage:
            sandbox = SecuritySandbox()
            allowed, reason, event_id = sandbox.wrap("write_file", target="/tmp/test.py")
            if not allowed:
                raise PermissionError(reason)
            # ... 执行工具调用 ...
        """
        allowed, reason = self.check(tool_name, target=target, command=command, url=url)
        event_id = self.log(
            tool_name=tool_name,
            result="blocked" if not allowed else "allowed",
            target=target,
            command=command,
            url=url,
            reason=reason,
        )
        return allowed, reason, event_id

    # ── 审计日志查询 ──

    def query_logs(
        self,
        tool_name: str | None = None,
        result: str | None = None,
        limit: int = 100,
    ) -> list[dict]:
        """查询审计日志"""
        results = []
        try:
            if not self.log_path.exists():
                return results
            with open(self.log_path, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        event = json.loads(line)
                        if tool_name and event.get("tool_name") != tool_name:
                            continue
                        if result and event.get("result") != result:
                            continue
                        results.append(event)
                        if len(results) >= limit:
                            break
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            logger.error("Failed to query sandbox logs: %s", e)
        return results

    def stats(self) -> dict[str, Any]:
        """返回沙箱统计信息"""
        total = 0
        blocked = 0
        try:
            if self.log_path.exists():
                with open(self.log_path, "r", encoding="utf-8") as f:
                    for line in f:
                        try:
                            event = json.loads(line)
                            total += 1
                            if event.get("result") == "blocked":
                                blocked += 1
                        except json.JSONDecodeError:
                            continue
        except Exception:
            pass
        return {
            "enabled": self._enabled,
            "total_events": total,
            "blocked": blocked,
            "allowed": total - blocked,
            "block_ratio": round(blocked / max(total, 1), 4),
            "rate_limit_remaining": self._tool_rate_limiter.remaining(),
        }


# ═══════════════════════════════════════════════════════════════
# 工具函数
# ═══════════════════════════════════════════════════════════════


def _extract_hostname(url: str) -> str | None:
    """从 URL 中提取主机名"""
    # 尝试标准 URL 解析
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        if parsed.hostname:
            return parsed.hostname
    except Exception:
        pass
    # 回退: 正则提取
    m = re.search(r"(?:https?://)?([^/:\s]+)", url)
    if m:
        return m.group(1).lower()
    return None


def _hostname_matches(hostname: str, patterns: list[str]) -> bool:
    """检查 hostname 是否匹配 glob 模式列表"""
    hostname = hostname.lower()
    for pattern in patterns:
        plower = pattern.lower()
        if fnmatch.fnmatch(hostname, plower):
            return True
    return False


# ═══════════════════════════════════════════════════════════════
# 便捷函数 (用于快速集成)
# ═══════════════════════════════════════════════════════════════

_default_sandbox: SecuritySandbox | None = None
_default_lock = threading.Lock()


def get_sandbox() -> SecuritySandbox:
    """获取全局单例沙箱实例"""
    global _default_sandbox
    if _default_sandbox is None:
        with _default_lock:
            if _default_sandbox is None:
                _default_sandbox = SecuritySandbox()
    return _default_sandbox


def check_tool(
    tool_name: str,
    target: str | None = None,
    command: str | None = None,
    url: str | None = None,
) -> tuple[bool, str]:
    """快速检查工具调用是否允许 (使用全局单例)"""
    return get_sandbox().check(tool_name, target=target, command=command, url=url)


def log_tool(
    tool_name: str,
    result: str,
    target: str | None = None,
    command: str | None = None,
    url: str | None = None,
    reason: str | None = None,
    duration_ms: float | None = None,
) -> str:
    """快速记录工具调用到审计日志"""
    return get_sandbox().log(
        tool_name=tool_name,
        result=result,
        target=target,
        command=command,
        url=url,
        reason=reason,
        duration_ms=duration_ms,
    )


# ═══════════════════════════════════════════════════════════════
# 自检
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("Hermes Security Sandbox v1.0 — 自检")
    print("=" * 60)

    sandbox = SecuritySandbox()

    # 1. 文件写入拦截
    ok, reason = sandbox.check("write_file", target="/etc/hosts")
    assert not ok, f"Expected blocked, got {reason}"
    print(f"[1] ✅ /etc/hosts 写入已拦截: {reason}")

    ok, reason = sandbox.check("write_file", target="/home/user/.ssh/id_rsa")
    assert not ok
    print(f"[2] ✅ ~/.ssh/id_rsa 写入已拦截: {reason}")

    ok, reason = sandbox.check("write_file", target="/app/staging-key.pem")
    assert not ok
    print(f"[3] ✅ *.pem 写入已拦截: {reason}")

    # 2. 正常写入允许
    ok, reason = sandbox.check("write_file", target="/tmp/hermes_test/test.py")
    assert ok, f"Expected ok, got {reason}"
    print("[4] ✅ /tmp/ 正常写入通过")

    ok, reason = sandbox.check("write_file", target="/home/user/.hermes/config/test.yaml")
    assert ok
    print("[5] ✅ ~/.hermes/ 正常写入通过")

    # 3. 命令拦截
    ok, reason = sandbox.check("terminal", command="rm -rf /")
    assert not ok
    print(f"[6] ✅ rm -rf / 已拦截: {reason}")

    ok, reason = sandbox.check("terminal", command="python test.py")
    assert ok, f"Expected ok, got {reason}"
    print("[7] ✅ python 正常命令通过")

    # 4. 审计日志
    event_id = sandbox.log("write_file", "blocked", target="/etc/hosts", reason="protected path")
    print(f"[8] ✅ 审计日志已写入: {event_id[:8]}...")

    event_id = sandbox.log("terminal", "allowed", command="python test.py", duration_ms=123.4)
    print(f"[9] ✅ 审计日志已写入: {event_id[:8]}...")

    # 5. wrap 一站式
    allowed, reason, eid = sandbox.wrap("write_file", target="/etc/shadow")
    assert not allowed
    print(f"[10] ✅ wrap 拦截: {reason}")

    allowed, reason, eid = sandbox.wrap("terminal", command="git status")
    assert allowed
    print(f"[11] ✅ wrap 放行: {reason}")

    # 6. 查询与统计
    logs = sandbox.query_logs(limit=10)
    print(f"[12] ✅ 查询审计日志: {len(logs)} 条")

    stats = sandbox.stats()
    print(f"[13] ✅ 沙箱统计: {stats}")

    # 7. 网络检查
    ok, reason = sandbox.check("http_request", url="https://api.openai.com/v1/chat")
    print(f"[14] ✅ 网络检查 (filter off): {reason}")

    print("\n" + "=" * 60)
    print("所有测试通过 ✅")
    print("=" * 60)
