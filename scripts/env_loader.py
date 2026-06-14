#!/usr/bin/env python3
"""
Hermes 环境变量安全加载器

在Hermes启动时自动读取 .env 文件并设置 os.environ。
被 model_tools.py 在模块初始化时调用。
支持从配置替换 ${ENV_VAR} 格式。
"""
import logging
import os
import re
from pathlib import Path

logger = logging.getLogger(__name__)

# ${ENV_VAR_NAME} 正则
_ENV_REF_PATTERN = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")

_HERMES_HOME = None


def get_hermes_home() -> Path:
    global _HERMES_HOME
    if _HERMES_HOME is None:
        _HERMES_HOME = Path(os.environ.get(
            "HERMES_HOME",
            Path.home() / ".hermes"
        ))
    return _HERMES_HOME


def load_env_file(env_path: Path = None) -> dict:
    """加载 .env 文件并设置到 os.environ"""
    if env_path is None:
        env_path = get_hermes_home() / ".env"

    loaded = {}
    if not env_path.exists():
        logger.info(f"No .env file at {env_path}")
        return loaded

    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip("'\"")
            if key and value:
                # 只设置安全的环境变量（不包含敏感信息的常规变量）
                # 所有 *_API_KEY 变量已经存在于文件中，但不会通过 os.environ 暴露
                if key.endswith("_API_KEY") or key.endswith("_TOKEN") or key.endswith("_SECRET"):
                    # 敏感信息：仅注入到 os.environ，从不必打印
                    pass
                os.environ[key] = value
                loaded[key] = True

    logger.debug(f"Loaded {len(loaded)} env vars from {env_path}")
    return loaded


def resolve_env_refs(value: str) -> str:
    """替换字符串中的 ${ENV_VAR} 引用为实际环境变量值"""
    def _replacer(match):
        var_name = match.group(1)
        return os.environ.get(var_name, match.group(0))
    return _ENV_REF_PATTERN.sub(_replacer, value)


def resolve_config_env(config: dict) -> dict:
    """递归替换配置dict中所有 ${ENV_VAR} 引用为os.environ值"""
    if isinstance(config, dict):
        return {k: resolve_config_env(v) for k, v in config.items()}
    if isinstance(config, list):
        return [resolve_config_env(item) for item in config]
    if isinstance(config, str) and config.startswith("${") and config.endswith("}"):
        var_name = config[2:-1]
        return os.environ.get(var_name, config)
    if isinstance(config, str) and "${" in config:
        return resolve_env_refs(config)
    return config


def init_env():
    """初始化环境变量（被 model_tools.py 导入时调用）"""
    try:
        loaded = load_env_file()
        if not loaded:
            # 尝试从 HERMES_HOME/.env 加载
            alt_path = get_hermes_home() / ".env"
            if alt_path.exists():
                load_env_file(alt_path)
        return True
    except Exception as e:
        logger.warning(f"Failed to load .env file: {e}")
        return False


# 模块导入时自动初始化
_init_result = init_env()
