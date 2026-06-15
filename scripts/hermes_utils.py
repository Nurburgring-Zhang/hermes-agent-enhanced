#!/usr/bin/env python3
"""
Hermes Utils -- 公共工具函数库
==============================
从各模块中提取的重复代码块和通用工具函数。

提取来源：
  - to_dict() 重复模式（actor_base, loop_engine, synapse_bus, etc.）
  - _init_db() 重复数据库初始化（8+ 处）
  - threading.RLock() 线程安全样板（10+ 处）
  - 日志配置重复模式
  - JSON 序列化/反序列化

所有函数保持向后兼容，原有模块可通过 import 渐进迁移。
"""

import hashlib
import json
import logging
import os
import sqlite3
import threading
import time
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union


class ErrorMessages:
    """统一错误消息，提供可操作的修复建议。"""

    CONFIG_NOT_FOUND = (
        "配置文件未找到。请确保 ~/.hermes/config.yaml 存在。"
        "\n  Action: cp config.yaml.example ~/.hermes/config.yaml"
    )
    CONFIG_INVALID_YAML = (
        "配置文件包含无效的 YAML 语法。"
        "\n  Action: yamllint ~/.hermes/config.yaml"
    )
    DB_INIT_FAILED = (
        "数据库初始化失败。请检查磁盘空间和写权限。"
        "\n  Action: df -h ~/.hermes/ && ls -la ~/.hermes/state.db"
    )
    ACTOR_NOT_REGISTERED = (
        "Actor 未注册到总线。"
        "\n  Action: bus.register_actor(my_actor, ['topic.name'])"
    )
    LOOP_NOT_REGISTERED = (
        "Loop 未注册。"
        "\n  Action: engine.register_loop(loop_def) 或 list_loops()"
    )
    SKILL_NOT_FOUND = (
        "Skill 未找到。"
        "\n  Action: ls ~/.hermes/skills/<category>/<skill>/SKILL.md"
    )
    MODEL_ROUTE_FAILED = (
        "模型路由失败，所有 Provider 不可用。"
        "\n  Action: 检查 API Key 和网络连接。"
    )
    API_TIMEOUT = (
        "API 请求超时。"
        "\n  Action: 检查网络连接，增加超时参数。"
    )
    API_RATE_LIMITED = (
        "API 触发限流。"
        "\n  Action: 等待 60s 后重试。"
    )
    API_AUTH_FAILED = (
        "API 认证失败。"
        "\n  Action: 检查环境变量 env | grep API_KEY"
    )
    FILE_NOT_FOUND = (
        "文件不存在。"
        "\n  Action: ls -la <path>"
    )
    FILE_PERMISSION_DENIED = (
        "文件权限不足。"
        "\n  Action: chmod +r <file>"
    )
    BACKUP_FAILED = (
        "文件备份失败。"
        "\n  Action: df -h; 清理旧备份。"
    )
    INVALID_JSON = (
        "JSON 解析失败。"
        "\n  Action: python -m json.tool 验证"
    )
    SCHEMA_MISMATCH = (
        "数据 Schema 不匹配。"
        "\n  Action: 检查 API 是否有更新。"
    )
    MEMORY_LIMIT = (
        "内存使用接近上限。"
        "\n  Action: hermes memory compress"
    )
    TOKEN_BUDGET_EXCEEDED = (
        "Token 预算耗尽。"
        "\n  Action: 等待预算重置或增加 budget_cap。"
    )


# ============================================================
# 日志工具
# ============================================================

_HERMES_HOME = os.path.expanduser("~/.hermes")
_logger_registry: Dict[str, logging.Logger] = {}


def get_hermes_logger(name: str, log_dir: str = None) -> logging.Logger:
    """获取或创建 Hermes 日志记录器（带缓存）。

    Args:
        name: Logger 名称（如 'hermes.actor'）。
        log_dir: 日志目录，默认 ~/.hermes/logs/。

    Returns:
        配置好的 logging.Logger 实例。
    """
    if name in _logger_registry:
        return _logger_registry[name]

    logger = logging.getLogger(name)
    if not logger.handlers:
        log_dir = log_dir or os.path.join(_HERMES_HOME, "logs")
        os.makedirs(log_dir, exist_ok=True)
        handler = logging.FileHandler(
            os.path.join(log_dir, f"{name.split('.')[-1]}.log")
        )
        handler.setFormatter(logging.Formatter(
            "[%(asctime)s] %(levelname)s %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        ))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

    _logger_registry[name] = logger
    return logger


# ============================================================
# 数据类序列化工具
# ============================================================

def safe_to_dict(obj: Any, recursive: bool = True) -> Any:
    """安全地将对象转换为字典，处理 dataclass、Enum、datetime 等。

    统一替代各处散落的 to_dict() 样板方法。
    """
    if obj is None:
        return None
    if isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, (list, tuple)):
        return [safe_to_dict(item, recursive) for item in obj] if recursive else list(obj)
    if isinstance(obj, dict):
        return {k: safe_to_dict(v, recursive) for k, v in obj.items()} if recursive else dict(obj)
    if isinstance(obj, datetime):
        return obj.isoformat()
    if is_dataclass(obj):
        result = {}
        for f in obj.__dataclass_fields__.values():
            value = getattr(obj, f.name)
            result[f.name] = safe_to_dict(value, recursive) if recursive else value
        return result
    if hasattr(obj, "value") and hasattr(obj, "name"):
        # Enum-like
        return obj.value
    if hasattr(obj, "to_dict"):
        return obj.to_dict()
    return str(obj)


T = TypeVar("T")


def populate_dataclass(cls: type[T], data: Dict[str, Any]) -> T:
    """从字典填充 dataclass 实例，忽略多余字段。

    统一替代各处散落的 from_dict() 类方法。
    """
    import dataclasses
    field_names = {f.name for f in dataclasses.fields(cls)}
    filtered = {k: v for k, v in data.items() if k in field_names}
    return cls(**filtered)


# ============================================================
# 数据库工具
# ============================================================

def init_sqlite_db(
    db_path: str,
    schema_sql: Union[str, List[str]],
    logger: logging.Logger = None,
) -> bool:
    """统一 SQLite 数据库初始化 -- 替代 8 处重复的 _init_db()。"""
    log = logger or logging.getLogger(__name__)
    try:
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        conn = sqlite3.connect(db_path)
        statements = [schema_sql] if isinstance(schema_sql, str) else schema_sql
        for stmt in statements:
            try:
                conn.execute(stmt)
            except sqlite3.Error as e:
                log.debug(f"SQL skip (may already exist): {e}")
        conn.commit()
        conn.close()
        return True
    except (sqlite3.Error, OSError) as e:
        log.error(f"DB init failed for {db_path}: {e}")
        return False


def safe_sqlite_execute(
    db_path: str,
    sql: str,
    params: tuple = (),
    fetch: str = "none",
    write: bool = False,
) -> Any:
    """安全执行 SQLite 操作。"""
    try:
        conn = sqlite3.connect(db_path, timeout=10)
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(sql, params)
        if write:
            conn.commit()
        result = None
        if fetch == "one":
            row = cursor.fetchone()
            result = dict(row) if row else None
        elif fetch == "all":
            result = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return result
    except sqlite3.Error:
        raise


# ============================================================
# 文件/IO 工具
# ============================================================

def safe_json_read(path: str, default: Any = None) -> Any:
    """安全读取 JSON 文件。"""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError, OSError):
        return default


def safe_json_write(path: str, data: Any, indent: int = 2) -> bool:
    """安全写入 JSON 文件（原子写入）。"""
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp_path = path + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=indent, default=str)
        os.replace(tmp_path, path)
        return True
    except (OSError, TypeError) as e:
        logging.getLogger(__name__).warning(f"JSON write failed for {path}: {e}")
        return False


def ensure_dir(path: str) -> str:
    """确保目录存在。"""
    os.makedirs(path, exist_ok=True)
    return os.path.abspath(path)


def hash_content(content: str, algorithm: str = "sha256") -> str:
    """计算内容哈希。"""
    h = hashlib.new(algorithm)
    h.update(content.encode("utf-8"))
    return h.hexdigest()


# ============================================================
# 重试/弹性工具
# ============================================================

def retry_call(
    func: Callable,
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    exponential: bool = True,
    exceptions: tuple = (Exception,),
    logger: logging.Logger = None,
) -> Any:
    """通用重试调用。"""
    log = logger or logging.getLogger(__name__)
    last_error = None
    for attempt in range(max_attempts):
        try:
            return func()
        except exceptions as e:
            last_error = e
            if attempt < max_attempts - 1:
                delay = min(
                    base_delay * (2 ** attempt) if exponential else base_delay,
                    max_delay,
                )
                log.warning(
                    "Retry %d/%d: %s, waiting %.1fs",
                    attempt + 1, max_attempts, e, delay
                )
                time.sleep(delay)
    raise last_error


# ============================================================
# 时间工具
# ============================================================

def utc_now() -> datetime:
    """返回当前的 UTC datetime。"""
    return datetime.now(timezone.utc)


def utc_now_iso() -> str:
    """返回当前的 UTC ISO 时间字符串。"""
    return utc_now().isoformat()


def timestamp_ms() -> int:
    """返回当前 Unix 时间戳（毫秒）。"""
    return int(time.time() * 1000)


# ============================================================
# 模块导入工具
# ============================================================

def safe_import(module_name: str, fallback: Any = None, logger: logging.Logger = None):
    """安全导入模块。"""
    import importlib
    log = logger or logging.getLogger(__name__)
    try:
        return importlib.import_module(module_name)
    except ImportError as e:
        log.debug(f"Optional module '{module_name}' not available: {e}")
        return fallback


# ============================================================
# 字符串工具
# ============================================================

def truncate(s: str, max_len: int = 200, suffix: str = "...") -> str:
    """截断字符串。"""
    if len(s) <= max_len:
        return s
    return s[: max_len - len(suffix)] + suffix


def format_duration(seconds: float) -> str:
    """格式化持续时间。"""
    if seconds < 1:
        return f"{seconds * 1000:.0f}ms"
    if seconds < 60:
        return f"{seconds:.1f}s"
    mins, secs = divmod(seconds, 60)
    if mins < 60:
        return f"{int(mins)}m {secs:.0f}s"
    hours, mins = divmod(mins, 60)
    return f"{int(hours)}h {int(mins)}m {secs:.0f}s"


# ============================================================
# 自检
# ============================================================

if __name__ == "__main__":
    print("=== Hermes Utils Self-Check ===")
    from dataclasses import dataclass
    from enum import Enum

    class TestEnum(Enum):
        A = "a"

    @dataclass
    class TestData:
        name: str
        value: int

    d = TestData("hello", 42)
    assert safe_to_dict(d) == {"name": "hello", "value": 42}
    print("  safe_to_dict: OK")

    d2 = populate_dataclass(TestData, {"name": "x", "value": 99, "extra": "ignored"})
    assert d2.name == "x" and d2.value == 99
    print("  populate_dataclass: OK")

    assert truncate("hello world", 8) == "hello..."
    print("  truncate: OK")

    assert "s" in format_duration(30)
    print("  format_duration: OK")

    h = hash_content("hermes")
    assert len(h) == 64
    print("  hash_content: OK")

    assert "配置" in ErrorMessages.CONFIG_NOT_FOUND
    print("  ErrorMessages: OK")

    log = get_hermes_logger("hermes.test_utils")
    log.info("Logger test OK")

    print("\nOK All checks passed -- hermes_utils.py")
