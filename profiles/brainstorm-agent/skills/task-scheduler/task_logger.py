"""
Task Logger Module
Dedicated logging for task execution with structured output.
"""

import sys
import threading
from datetime import datetime
from enum import Enum
from typing import Any


class LogLevel(Enum):
    """Log levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class TaskLogger:
    """
    Task-specific logger that writes to both console and persistent storage.
    """

    def __init__(self, storage: "TaskStorage", run_id: str | None = None):
        """Initialize logger."""
        self.storage = storage
        self.run_id = run_id
        self._lock = threading.RLock()
        self._local = threading.local()

    def _get_buffer(self) -> list[dict[str, Any]]:
        """Get thread-local buffer."""
        if not hasattr(self._local, "buffer"):
            self._local.buffer = []
        return self._local.buffer

    def log(
        self,
        level: LogLevel,
        message: str,
        structured_data: dict[str, Any] | None = None,
        flush: bool = False
    ):
        """
        Log a message.

        Args:
            level: Log level
            message: Log message
            structured_data: Optional structured data
            flush: Immediately write to storage
        """
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": level.value,
            "message": message,
            "structured_data": structured_data
        }

        with self._lock:
            buffer = self._get_buffer()
            buffer.append(entry)

            # Console output
            if level in [LogLevel.ERROR, LogLevel.CRITICAL] or getattr(self._local, "verbose", False):
                self._print_entry(entry)

            # Flush to storage if requested
            if flush:
                self.flush()

    def debug(self, message: str, **kwargs):
        """Log debug message."""
        self.log(LogLevel.DEBUG, message, structured_data=kwargs or None)

    def info(self, message: str, **kwargs):
        """Log info message."""
        self.log(LogLevel.INFO, message, structured_data=kwargs or None)

    def warning(self, message: str, **kwargs):
        """Log warning message."""
        self.log(LogLevel.WARNING, message, structured_data=kwargs or None)

    def error(self, message: str, **kwargs):
        """Log error message."""
        self.log(LogLevel.ERROR, message, structured_data=kwargs or None)

    def critical(self, message: str, **kwargs):
        """Log critical message."""
        self.log(LogLevel.CRITICAL, message, structured_data=kwargs or None)

    def exception(self, message: str, exc_info=True, **kwargs):
        """Log exception with traceback."""
        import traceback
        tb = traceback.format_exc() if exc_info else None
        self.error(f"{message}\n{tb}" if tb else message, **kwargs)

    def _print_entry(self, entry: dict[str, Any]):
        """Print log entry to console."""
        timestamp = entry["timestamp"][:19]
        level = entry["level"]
        message = entry["message"]

        # Color codes
        colors = {
            "DEBUG": "\033[90m",
            "INFO": "\033[0m",
            "WARNING": "\033[93m",
            "ERROR": "\033[91m",
            "CRITICAL": "\033[91;1m"
        }
        reset = "\033[0m"

        color = colors.get(level, "")
        print(f"{color}[{timestamp}] [{level:8}] {message}{reset}")

    def flush(self):
        """Flush buffered logs to storage."""
        with self._lock:
            buffer = self._get_buffer()
            if not buffer:
                return

            try:
                for entry in buffer:
                    if self.run_id:
                        self.storage.append_log(
                            run_id=self.run_id,
                            level=entry["level"],
                            message=entry["message"],
                            structured_data=entry["structured_data"]
                        )
                buffer.clear()
            except Exception as e:
                print(f"Logger flush error: {e}", file=sys.stderr)

    def set_verbose(self, verbose: bool):
        """Set verbose mode."""
        self._local.verbose = verbose


# Global log buffer (for non-task-specific logging)
_global_storage = None
_global_buffer: list[dict[str, Any]] = []
_global_lock = threading.RLock()


def init_global_logger(storage: "TaskStorage"):
    """Initialize global logger for non-task messages."""
    global _global_storage
    _global_storage = storage


def log(level: LogLevel, message: str, **kwargs):
    """Log a global message (no run_id)."""
    entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "level": level.value,
        "message": message,
        "structured_data": kwargs or None
    }

    with _global_lock:
        _global_buffer.append(entry)

        # Print to console for warnings/errors
        if level in [LogLevel.ERROR, LogLevel.CRITICAL]:
            _print_entry(entry)

        # Flush to storage if available
        if _global_storage:
            try:
                _global_storage.append_log(
                    run_id="monitor",
                    level=entry["level"],
                    message=entry["message"],
                    structured_data=entry["structured_data"]
                )
            except Exception:
                pass


def _print_entry(entry: dict[str, Any]):
    """Print entry to console."""
    timestamp = entry["timestamp"][:19]
    level = entry["level"]
    message = entry["message"]
    print(f"[{timestamp}] [{level:8}] {message}")


def debug(msg, **kwargs): log(LogLevel.DEBUG, msg, **kwargs)
def info(msg, **kwargs): log(LogLevel.INFO, msg, **kwargs)
def warning(msg, **kwargs): log(LogLevel.WARNING, msg, **kwargs)
def error(msg, **kwargs): log(LogLevel.ERROR, msg, **kwargs)
def critical(msg, **kwargs): log(LogLevel.CRITICAL, msg, **kwargs)
