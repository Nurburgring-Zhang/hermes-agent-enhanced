"""
Hermes Agent Enhanced — Scripts Module
========================================

脚本模块初始化文件，提供版本信息导入和包级实用功能。
"""

from .__version__ import (
    CHANGELOG,
    __description__,
    __title__,
    __version__,
    __version_info__,
    get_version,
)
from .error_framework import (
    ConfigError,
    ErrorCode,
    ExecutionError,
    HermesError,
    RateLimitError,
    ResourceNotFoundError,
    SecurityError,
    ValidationError,
    hermes_error_handler,
    wrap_exception,
)

__all__ = [
    "__version__",
    "__version_info__",
    "__title__",
    "__description__",
    "get_version",
    "CHANGELOG",
    # Error framework
    "HermesError",
    "ConfigError",
    "ExecutionError",
    "SecurityError",
    "ResourceNotFoundError",
    "RateLimitError",
    "ValidationError",
    "ErrorCode",
    "hermes_error_handler",
    "wrap_exception",
]
