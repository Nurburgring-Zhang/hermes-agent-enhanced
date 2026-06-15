#!/usr/bin/env python3
"""
Hermes Secret Manager v1.0
===========================
密钥安全管理 — 无密钥进入 LLM 上下文。

核心原则: API 密钥不应出现在 LLM 提示/上下文中。
通过占位符机制，密钥在 LLM 上下文外管理，仅在实际执行 API 调用时注入。

对标:
  - OWASP LLM Top 10: LLM06 (敏感信息泄露), LLM02 (不安全输出处理)
  - NIST SP 800-57: 密钥管理最佳实践
  - HashiCorp Vault / AWS Secrets Manager 设计理念

核心功能:
  1. 占位符解析: {{SECRET:name}} → 执行时注入
  2. API 密钥不进入 LLM 上下文
  3. 密钥加密存储 (Fernet AES-128-CBC)

使用:
  from scripts.secret_manager import SecretManager
  sm = SecretManager()
  sm.set("OPENAI_API_KEY", "sk-abc123...")
  resolved = sm.resolve_placeholders("export KEY={{SECRET:OPENAI_API_KEY}}")
  # → "export KEY=sk-abc123..."
"""

import hashlib
import json
import logging
import os
import re
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ── 常量 ──
HERMES = Path(os.path.expanduser("~/.hermes"))
DEFAULT_VAULT_PATH = HERMES / "vault" / "secrets.enc"
DEFAULT_KEY_PATH = HERMES / "vault" / ".encryption_key"
DEFAULT_METADATA_PATH = HERMES / "vault" / "secrets_meta.json"

# 占位符模式: {{SECRET:name}} 或 {{SECRET:name:field}}
PLACEHOLDER_PATTERN = re.compile(r'\{\{SECRET:([a-zA-Z_][a-zA-Z0-9_]*)(?::([a-zA-Z_][a-zA-Z0-9_]*))?\}\}')

# 密钥值模式 (用于扫描，防止硬编码密钥)
HARDCODED_SECRET_PATTERNS = [
    re.compile(r'(?i)(api[_-]?key|apikey|secret[_-]?key|access[_-]?key|token)\s*[:=]\s*[\'"]?([A-Za-z0-9\-_+/=]{20,200})[\'"]?'),
    re.compile(r'(?i)(password|passwd|pwd)\s*[:=]\s*[\'"]([^\'"]+)[\'"]'),
    re.compile(r'(?i)export\s+([A-Z_]+)\s*=\s*[\'"]([A-Za-z0-9\-_+/=]{20,200})[\'"]'),
]


# ═══════════════════════════════════════════════════════════════
# 加密层
# ═══════════════════════════════════════════════════════════════


class EncryptionLayer:
    """Fernet AES-128-CBC 加密层。

    存放密钥到磁盘，提供 encrypt/decrypt 接口。
    """

    def __init__(self, key_path: Path = DEFAULT_KEY_PATH):
        self._key_path = key_path
        self._fernet: Any = None

    def _get_or_create_key(self) -> bytes:
        """获取或创建加密密钥"""
        if self._key_path.exists():
            return self._key_path.read_bytes()

        # 生成新密钥
        from cryptography.fernet import Fernet
        key = Fernet.generate_key()
        self._key_path.parent.mkdir(parents=True, exist_ok=True)
        # 设置仅 owner 可读写
        self._key_path.write_bytes(key)
        os.chmod(self._key_path, 0o600)
        logger.info("Generated new encryption key at %s", self._key_path)
        return key

    def _ensure_fernet(self) -> Any:
        """确保 Fernet 实例已初始化"""
        if self._fernet is None:
            from cryptography.fernet import Fernet
            key = self._get_or_create_key()
            self._fernet = Fernet(key)
        return self._fernet

    def encrypt(self, plaintext: str) -> str:
        """加密字符串 → base64 密文"""
        fernet = self._ensure_fernet()
        return fernet.encrypt(plaintext.encode("utf-8")).decode("utf-8")

    def decrypt(self, ciphertext: str) -> str:
        """解密 base64 密文 → 明文"""
        fernet = self._ensure_fernet()
        return fernet.decrypt(ciphertext.encode("utf-8")).decode("utf-8")


# ═══════════════════════════════════════════════════════════════
# Secret Manager
# ═══════════════════════════════════════════════════════════════


class SecretManager:
    """密钥管理器 — 占位符解析 + 加密存储。

    核心设计:
      - LLM 上下文中的密钥以 {{SECRET:name}} 占位符呈现
      - 实际密钥值仅在 resolve_placeholders() 时注入
      - 密钥存储加密 (Fernet)
      - 内存中仅保留运行时必需密钥

    Usage:
        sm = SecretManager()

        # 存储密钥
        sm.set("OPENAI_API_KEY", "sk-abc123...")
        sm.set("DATABASE_URL", "postgresql://user:pass@host/db")

        # 在 LLM 上下文中使用占位符
        prompt = "请设置环境变量: export OPENAI_API_KEY={{SECRET:OPENAI_API_KEY}}"
        # prompt 被发送到 LLM — 密钥不在其中！

        # 执行时解析
        actual = sm.resolve_placeholders(prompt)
        # → "请设置环境变量: export OPENAI_API_KEY=sk-abc123..."
    """

    def __init__(
        self,
        vault_path: Path | str = DEFAULT_VAULT_PATH,
        key_path: Path | str = DEFAULT_KEY_PATH,
        metadata_path: Path | str = DEFAULT_METADATA_PATH,
    ):
        self._vault_path = Path(vault_path)
        self._metadata_path = Path(metadata_path)
        self._crypto = EncryptionLayer(Path(key_path))
        self._cache: dict[str, str] = {}
        self._metadata: dict[str, dict] = {}
        self._lock = threading.Lock()
        self._secrets: dict[str, str] = {}  # 内存中的解密密钥

        # 创建目录
        self._vault_path.parent.mkdir(parents=True, exist_ok=True)
        os.chmod(self._vault_path.parent, 0o700)

        # 加载持久化的密钥
        self._load_vault()
        self._load_metadata()

    # ── 密钥存取 ──

    def set(
        self,
        name: str,
        value: str,
        metadata: dict[str, Any] | None = None,
        persist: bool = True,
    ) -> None:
        """存储一个密钥。

        Args:
            name: 密钥名称 (用于占位符 {{SECRET:name}})
            value: 密钥值 (明文)
            metadata: 可选的元数据 (如 description, expires_at)
            persist: 是否持久化到磁盘
        """
        with self._lock:
            cleaned_name = name.strip().upper().replace(" ", "_")
            self._cache[cleaned_name] = value
            self._secrets[cleaned_name] = value

            # 更新元数据
            self._metadata[cleaned_name] = {
                "created_at": datetime.now(UTC).isoformat(),
                "updated_at": datetime.now(UTC).isoformat(),
                "value_hash": hashlib.sha256(value.encode()).hexdigest()[:16],
                **(metadata or {}),
            }

            if persist:
                self._save_vault()
                self._save_metadata()

            logger.info("Secret '%s' stored (len=%d)", cleaned_name, len(value))

    def get(self, name: str, default: str | None = None) -> str | None:
        """获取密钥明文。

        从内存缓存获取，若不存在则返回 default。
        密钥值永远不会直接出现在 LLM 上下文中。
        """
        cleaned_name = name.strip().upper().replace(" ", "_")
        with self._lock:
            if cleaned_name in self._cache:
                return self._cache[cleaned_name]
        return default

    def delete(self, name: str) -> bool:
        """删除密钥"""
        cleaned_name = name.strip().upper().replace(" ", "_")
        with self._lock:
            if cleaned_name in self._cache:
                del self._cache[cleaned_name]
            if cleaned_name in self._secrets:
                del self._secrets[cleaned_name]
            if cleaned_name in self._metadata:
                del self._metadata[cleaned_name]
            self._save_vault()
            self._save_metadata()
            logger.info("Secret '%s' deleted", cleaned_name)
            return True
        return False

    def list_names(self) -> list[str]:
        """列出所有已存储的密钥名称 (仅名称，不包含值)"""
        with self._lock:
            return sorted(self._metadata.keys())

    def list_metadata(self) -> dict[str, dict]:
        """列出所有密钥的元数据 (不含密钥值)"""
        with self._lock:
            return dict(self._metadata)

    # ── 占位符解析 ──

    def resolve_placeholders(self, text: str) -> str:
        """解析文本中的所有 {{SECRET:name}} 占位符。

        这是核心操作：将 LLM 上下文中的占位符替换为实际密钥值。
        仅在执行实际操作时调用，不在准备 LLM 提示时调用。

        Args:
            text: 可能包含占位符的文本

        Returns:
            占位符被替换为实际值的文本

        Example:
            >>> sm = SecretManager()
            >>> sm.set("DB_PASS", "s3cret!")
            >>> sm.resolve_placeholders("mysql -p{{SECRET:DB_PASS}}")
            'mysql -ps3cret!'
        """
        def _replacer(match: re.Match) -> str:
            name = match.group(1)
            field = match.group(2)  # 可选: 未来 JSON 字段提取
            value = self.get(name)
            if value is None:
                logger.warning("Secret placeholder '%s' not found — keeping placeholder", name)
                return match.group(0)  # 保留原占位符
            if field:
                # 如果密钥值是 JSON，尝试提取字段
                try:
                    data = json.loads(value)
                    if isinstance(data, dict) and field in data:
                        return str(data[field])
                except (json.JSONDecodeError, TypeError):
                    logger.warning("Cannot extract field '%s' from non-JSON secret '%s'", field, name)
                    return match.group(0)
            return value

        return PLACEHOLDER_PATTERN.sub(_replacer, text)

    def has_placeholders(self, text: str) -> bool:
        """检查文本是否包含密钥占位符"""
        return bool(PLACEHOLDER_PATTERN.search(text))

    def list_placeholders(self, text: str) -> list[str]:
        """列出文本中所有占位符引用的密钥名"""
        matches = PLACEHOLDER_PATTERN.findall(text)
        return [m[0] for m in matches]

    # ── 防止密钥进入 LLM 上下文 ──

    def mask_for_llm(self, text: str) -> str:
        """将文本中的实际密钥替换为占位符 (反向操作)。

        用于确保发送给 LLM 的上下文中不包含明文密钥。

        Args:
            text: 可能包含明文密钥的文本

        Returns:
            密钥被替换为占位符的文本
        """
        result = text
        with self._lock:
            for name, value in self._secrets.items():
                if value and len(value) > 4:
                    result = result.replace(value, f"{{{{SECRET:{name}}}}}")
        return result

    def scan_for_hardcoded_secrets(self, text: str) -> list[dict[str, str]]:
        """扫描文本中的硬编码密钥。

        返回发现的潜在密钥信息。
        这是防御性检查，应该在工具输出进入 LLM 上下文前运行。

        Returns:
            [{"type": "api_key", "name": "...", "value_preview": "sk-...xxx"}]
        """
        findings: list[dict[str, str]] = []
        for pattern in HARDCODED_SECRET_PATTERNS:
            for match in pattern.finditer(text):
                groups = match.groups()
                findings.append({
                    "type": "potential_secret",
                    "name": groups[0] if len(groups) > 0 else "unknown",
                    "value_preview": groups[-1][:10] + "..." if len(groups[-1]) > 10 else groups[-1],
                })
        return findings

    # ── 持久化 ──

    def _save_vault(self) -> None:
        """加密所有密钥并持久化到磁盘"""
        try:
            vault_data = {}
            for name, value in self._secrets.items():
                vault_data[name] = self._crypto.encrypt(value)
            with open(self._vault_path, "w", encoding="utf-8") as f:
                json.dump(vault_data, f, indent=2)
            os.chmod(self._vault_path, 0o600)
        except Exception as e:
            logger.error("Failed to save vault: %s", e)

    def _load_vault(self) -> None:
        """从磁盘加载加密的密钥"""
        if not self._vault_path.exists():
            return
        try:
            with open(self._vault_path, "r", encoding="utf-8") as f:
                vault_data = json.load(f)
            for name, ciphertext in vault_data.items():
                try:
                    self._secrets[name] = self._crypto.decrypt(ciphertext)
                    self._cache[name] = self._secrets[name]
                except Exception as e:
                    logger.warning("Failed to decrypt secret '%s': %s", name, e)
            logger.info("Loaded %d secrets from vault", len(self._secrets))
        except Exception as e:
            logger.error("Failed to load vault: %s", e)

    def _save_metadata(self) -> None:
        """保存密钥元数据 (不包含密钥值)"""
        try:
            with open(self._metadata_path, "w", encoding="utf-8") as f:
                json.dump(self._metadata, f, indent=2, default=str)
        except Exception as e:
            logger.error("Failed to save metadata: %s", e)

    def _load_metadata(self) -> None:
        """加载密钥元数据"""
        if not self._metadata_path.exists():
            return
        try:
            with open(self._metadata_path, "r", encoding="utf-8") as f:
                self._metadata = json.load(f)
        except Exception as e:
            logger.warning("Failed to load metadata: %s", e)

    # ── 生命周期 ──

    def flush(self) -> None:
        """强制刷新密钥缓存到磁盘"""
        with self._lock:
            self._save_vault()
            self._save_metadata()

    def clear_cache(self) -> None:
        """清空内存密钥缓存 (不删除持久化数据)"""
        with self._lock:
            self._cache.clear()
            self._secrets.clear()

    def import_from_env(self, var_names: list[str]) -> int:
        """从环境变量导入密钥。

        Returns:
            成功导入的密钥数量

        Example:
            sm.import_from_env(["OPENAI_API_KEY", "ANTHROPIC_API_KEY"])
        """
        count = 0
        for var in var_names:
            value = os.environ.get(var)
            if value:
                self.set(var, value, metadata={"source": "environment"})
                count += 1
        return count

    def export_env_vars(self) -> dict[str, str]:
        """导出所有密钥为环境变量字典 (用于 subprocess)"""
        with self._lock:
            return dict(self._secrets)


# ═══════════════════════════════════════════════════════════════
# 便捷函数
# ═══════════════════════════════════════════════════════════════

_default_manager: SecretManager | None = None
_default_lock = threading.Lock()


def get_secret_manager() -> SecretManager:
    """获取全局单例 SecretManager"""
    global _default_manager
    if _default_manager is None:
        with _default_lock:
            if _default_manager is None:
                _default_manager = SecretManager()
    return _default_manager


def resolve(text: str) -> str:
    """快速解析占位符"""
    return get_secret_manager().resolve_placeholders(text)


def mask(text: str) -> str:
    """快速掩码密钥 (用于 LLM 上下文)"""
    return get_secret_manager().mask_for_llm(text)


# ═══════════════════════════════════════════════════════════════
# 自检
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("Hermes Secret Manager v1.0 — 自检")
    print("=" * 60)

    sm = SecretManager()

    # 1. 基础存储与获取
    sm.set("TEST_KEY", "secret-value-12345")
    value = sm.get("TEST_KEY")
    assert value == "secret-value-12345", f"Expected 'secret-value-12345', got {value}"
    print("[1] ✅ 密钥存储/获取成功")

    # 2. 占位符解析
    text = "export API_KEY={{SECRET:TEST_KEY}} and use {{SECRET:TEST_KEY}} again"
    resolved = sm.resolve_placeholders(text)
    assert "secret-value-12345" in resolved
    assert "{{SECRET" not in resolved
    print(f"[2] ✅ 占位符解析: {resolved}")

    # 3. 掩码 (反向 — 密钥 → 占位符)
    dirty = "my password is secret-value-12345, don't tell anyone"
    masked = sm.mask_for_llm(dirty)
    assert "{{SECRET:TEST_KEY}}" in masked
    assert "secret-value-12345" not in masked
    print(f"[3] ✅ LLM 掩码: {masked}")

    # 4. 占位符存在检查
    assert sm.has_placeholders("use {{SECRET:TEST_KEY}} here")
    assert not sm.has_placeholders("no secrets here")
    print("[4] ✅ 占位符检测")

    # 5. 列出占位符
    placeholders = sm.list_placeholders("{{SECRET:A}} and {{SECRET:B}}")
    assert "A" in placeholders and "B" in placeholders
    print(f"[5] ✅ 占位符列表: {placeholders}")

    # 6. 扫描硬编码密钥
    findings = sm.scan_for_hardcoded_secrets("api_key=sk-test-1234567890abcdefghijklmnopqrstuvwxyz")
    assert len(findings) >= 1
    print(f"[6] ✅ 硬编码密钥扫描: {findings[0]['name']}")

    # 7. 密钥列表 (仅元数据，无值)
    sm.set("DB_PASSWORD", "db-secret-999", metadata={"description": "Database password"})
    names = sm.list_names()
    assert "TEST_KEY" in names and "DB_PASSWORD" in names
    print(f"[7] ✅ 密钥列表: {names}")

    meta = sm.list_metadata()
    assert "DB_PASSWORD" in meta
    assert "description" in meta["DB_PASSWORD"]
    assert "db-secret-999" not in str(meta["DB_PASSWORD"]), "Metadata should not contain the secret value"
    print("[8] ✅ 元数据不含密钥值")

    # 8. 不存在的占位符 (保留原样)
    result = sm.resolve_placeholders("{{SECRET:NONEXISTENT}}")
    assert "{{SECRET:NONEXISTENT}}" in result
    print("[9] ✅ 不存在密钥保留占位符")

    # 9. 密钥删除
    sm.set("TEMP_KEY", "temp-value")
    assert sm.get("TEMP_KEY") == "temp-value"
    sm.delete("TEMP_KEY")
    assert sm.get("TEMP_KEY") is None
    print("[10] ✅ 密钥删除成功")

    # 10. 持久化验证
    sm.flush()  # 确保写入磁盘
    sm2 = SecretManager()  # 新实例从磁盘加载
    value2 = sm2.get("TEST_KEY")
    assert value2 == "secret-value-12345", f"Persisted value mismatch: {value2}"
    print("[11] ✅ 持久化恢复成功")

    # 清理
    sm.delete("TEST_KEY")
    sm.delete("DB_PASSWORD")
    sm.flush()

    print("\n" + "=" * 60)
    print("所有测试通过 ✅")
    print("=" * 60)
