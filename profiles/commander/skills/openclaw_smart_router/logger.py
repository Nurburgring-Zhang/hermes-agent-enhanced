"""
OpenClaw AI Smart Router - Logger
日志系统 - 支持多级别日志、文件输出、颜色标记
"""

import logging
import sys
from pathlib import Path


class ColoredFormatter(logging.Formatter):
    """彩色日志格式化器"""

    # ANSI 颜色代码
    COLORS = {
        "DEBUG": "\033[36m",      # 青色
        "INFO": "\033[32m",       # 绿色
        "WARNING": "\033[33m",    # 黄色
        "ERROR": "\033[31m",      # 红色
        "CRITICAL": "\033[35m",   # 紫色
        "RESET": "\033[0m",       # 重置
        "BOLD": "\033[1m"         # 粗体
    }

    def __init__(self, use_colors: bool = True, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.use_colors = use_colors and sys.stderr.isatty()

    def format(self, record: logging.LogRecord) -> str:
        levelname = record.levelname

        if self.use_colors and levelname in self.COLORS:
            # 添加颜色
            colored_levelname = f"{self.COLORS[levelname]}{levelname}{self.COLORS['RESET']}"
            record.levelname = colored_levelname

            # 如果是错误或严重错误，加粗整行
            if record.levelno >= logging.ERROR:
                record.msg = f"{self.COLORS['BOLD']}{record.msg}{self.COLORS['RESET']}"

        return super().format(record)


class SmartRouterLogger:
    """智能路由日志器"""

    def __init__(
        self,
        name: str = "SmartRouter",
        log_level: str = "info",
        log_file: str | None = None,
        use_colors: bool = True
    ):
        self.name = name
        self.logger = logging.getLogger(name)
        self.logger.handlers = []  # 清除现有处理器

        # 设置日志级别
        level_map = {
            "debug": logging.DEBUG,
            "info": logging.INFO,
            "warn": logging.WARNING,
            "warning": logging.WARNING,
            "error": logging.ERROR,
            "critical": logging.CRITICAL
        }
        self.logger.setLevel(level_map.get(log_level.lower(), logging.INFO))

        # 控制台处理器
        console_handler = logging.StreamHandler(sys.stderr)
        console_formatter = ColoredFormatter(
            use_colors=use_colors,
            fmt="[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)

        # 文件处理器（如果指定）
        if log_file:
            self._setup_file_handler(log_file)

        self.logger.propagate = False

    def _setup_file_handler(self, log_file: str):
        """设置文件处理器"""
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_formatter = logging.Formatter(
            fmt="[%(asctime)s] [%(levelname)s] [%(name)s] [%(process)d] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        file_handler.setFormatter(file_formatter)
        self.logger.addHandler(file_handler)

    def debug(self, message: str, *args, **kwargs):
        """调试日志"""
        self.logger.debug(message, *args, **kwargs)

    def info(self, message: str, *args, **kwargs):
        """信息日志"""
        self.logger.info(message, *args, **kwargs)

    def warning(self, message: str, *args, **kwargs):
        """警告日志"""
        self.logger.warning(message, *args, **kwargs)

    def warn(self, message: str, *args, **kwargs):
        """警告日志（别名）"""
        self.warning(message, *args, **kwargs)

    def error(self, message: str, *args, **kwargs):
        """错误日志"""
        self.logger.error(message, *args, **kwargs)

    def critical(self, message: str, *args, **kwargs):
        """严重错误日志"""
        self.logger.critical(message, *args, **kwargs)

    def exception(self, message: str, *args, exc_info=True, **kwargs):
        """异常日志"""
        self.logger.exception(message, *args, exc_info=exc_info, **kwargs)

    def set_level(self, level: str):
        """设置日志级别"""
        level_map = {
            "debug": logging.DEBUG,
            "info": logging.INFO,
            "warn": logging.WARNING,
            "warning": logging.WARNING,
            "error": logging.ERROR,
            "critical": logging.CRITICAL
        }
        self.logger.setLevel(level_map.get(level.lower(), logging.INFO))


# 全局单例
_default_logger: SmartRouterLogger | None = None


def get_logger(
    name: str = "SmartRouter",
    log_level: str = "info",
    log_file: str | None = None,
    use_colors: bool = True
) -> SmartRouterLogger:
    """获取日志器实例（单例模式）"""
    global _default_logger

    if _default_logger is None or _default_logger.name != name:
        _default_logger = SmartRouterLogger(name, log_level, log_file, use_colors)

    return _default_logger


def set_global_logger(logger: SmartRouterLogger):
    """设置全局日志器"""
    global _default_logger
    _default_logger = logger


def setup_logging_from_config(config):
    """从配置设置日志"""
    logger = get_logger(
        log_level=config.get("log_level", "info"),
        log_file=config.get("log_file")
    )
    return logger
