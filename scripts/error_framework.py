"""
error_framework.py — Unified Error Handling Framework

对标 Scale AI Error Response 标准 + RFC 7807 Problem Details
===============================================================

Provides:
  - HermesError base class with full RFC 7807 compliance
  - Specialized subclasses for common error domains
  - @hermes_error_handler decorator for automatic error wrapping
  - to_dict() producing standard {success: false, error: {...}} format

Scale AI standard format:
  {
    "success": false,
    "error": {
      "code": "CONFIG_ERROR",
      "message": "human-readable summary",
      "detail": "detailed explanation / RFC 7807 detail",
      "trace_id": "uuid-v4",
      "timestamp": "2025-06-14T12:34:56.789Z"
    }
  }

RFC 7807 / Problem Details (RFC 9457):
  type, title, status, detail, instance — partially mapped into our error dict.
  'type'     -> 'urn:hermes:error:{error_code_lower}'
  'title'    -> message
  'status'   -> status_code
  'detail'   -> detail
  'instance' -> trace_id (as a pseudo-URN or URI)
"""

from __future__ import annotations

import functools
import logging
import traceback
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any, TypeVar

logger = logging.getLogger(__name__)

# Type variable for the decorator
F = TypeVar("F", bound=Callable[..., Any])

# ──────────────────────────────────────────────────────────────
# Error Codes (aligned with common Scale AI categories)
# ──────────────────────────────────────────────────────────────

class ErrorCode:
    """Canonical error code constants — matches Scale AI conventions."""
    CONFIG_ERROR = "CONFIG_ERROR"
    EXECUTION_ERROR = "EXECUTION_ERROR"
    SECURITY_ERROR = "SECURITY_ERROR"
    RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"
    RATE_LIMIT_ERROR = "RATE_LIMIT_ERROR"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    TIMEOUT_ERROR = "TIMEOUT_ERROR"
    AUTHENTICATION_ERROR = "AUTHENTICATION_ERROR"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"

    # Maps exception class names -> error codes for auto-detection
    _CLASS_MAP: dict[str, str] = {
        "ConfigError": CONFIG_ERROR,
        "ExecutionError": EXECUTION_ERROR,
        "SecurityError": SECURITY_ERROR,
        "ResourceNotFoundError": RESOURCE_NOT_FOUND,
        "RateLimitError": RATE_LIMIT_ERROR,
        "ValidationError": VALIDATION_ERROR,
    }

    @classmethod
    def from_exception_name(cls, name: str) -> str:
        """Infer error code from exception class name."""
        return cls._CLASS_MAP.get(name, cls.INTERNAL_ERROR)


# ──────────────────────────────────────────────────────────────
# Base Exception
# ──────────────────────────────────────────────────────────────

class HermesError(Exception):
    """
    Base exception for all Hermes errors.

    Implements RFC 7807 (Problem Details) semantics and Scale AI error format.

    Attributes:
        code (str): Machine-readable error code (e.g., "CONFIG_ERROR").
        message (str): Human-readable summary / RFC 7807 'title'.
        detail (str): Detailed explanation / RFC 7807 'detail'.
        status_code (int): HTTP-style status code (e.g., 400, 404, 500).
        timestamp (str): ISO 8601 UTC timestamp with millisecond precision.
        trace_id (str): UUID v4 trace identifier for request correlation.
        _cause (Optional[Exception]): Original exception that caused this error (if any).
        _stack (Optional[str]): Captured stack trace string.
    """

    def __init__(
        self,
        message: str,
        *,
        code: str = ErrorCode.INTERNAL_ERROR,
        detail: str = "",
        status_code: int = 500,
        trace_id: str | None = None,
        cause: Exception | None = None,
    ) -> None:
        self.code = code
        self.message = message
        self.detail = detail
        self.status_code = status_code
        self.timestamp = _now_iso()
        self.trace_id = trace_id or uuid.uuid4().hex
        self._cause = cause
        self._stack = "".join(traceback.format_exception(type(self), self, self.__traceback__)) if self.__traceback__ else None

        # If a cause was provided, chain it via Python's native exception chaining
        if cause is not None:
            super().__init__(message, cause)
        else:
            super().__init__(message)

    def to_dict(self) -> dict[str, Any]:
        """
        Convert to Scale AI / RFC 7807 compliant dictionary.

        Returns:
            {
                "success": false,
                "error": {
                    "code": str,
                    "message": str,
                    "detail": str,
                    "trace_id": str,
                    "timestamp": str
                }
            }
        """
        return {
            "success": False,
            "error": {
                "code": self.code,
                "message": self.message,
                "detail": self.detail,
                "trace_id": self.trace_id,
                "timestamp": self.timestamp,
            },
        }

    def to_problem_detail(self) -> dict[str, Any]:
        """
        Return a pure RFC 9457 (Problem Details) dictionary.

        https://www.rfc-editor.org/rfc/rfc9457.html
        """
        return {
            "type": f"urn:hermes:error:{self.code.lower()}",
            "title": self.message,
            "status": self.status_code,
            "detail": self.detail,
            "instance": f"urn:hermes:trace:{self.trace_id}",
        }

    def __str__(self) -> str:
        return f"[{self.code}] {self.message}"

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"message={self.message!r}, "
            f"code={self.code!r}, "
            f"status_code={self.status_code!r}, "
            f"trace_id={self.trace_id!r})"
        )


# ──────────────────────────────────────────────────────────────
# Specialized Subclasses
# ──────────────────────────────────────────────────────────────

class ConfigError(HermesError):
    """Configuration-related errors (missing env vars, invalid config files, etc.)."""

    def __init__(
        self,
        message: str,
        *,
        detail: str = "",
        status_code: int = 500,
        trace_id: str | None = None,
        cause: Exception | None = None,
        config_key: str | None = None,
    ) -> None:
        self.config_key = config_key
        enriched_detail = detail
        if config_key:
            enriched_detail = f"Config key '{config_key}': {detail}" if detail else f"Missing or invalid config key: '{config_key}'"
        super().__init__(
            message=message,
            code=ErrorCode.CONFIG_ERROR,
            detail=enriched_detail,
            status_code=status_code,
            trace_id=trace_id,
            cause=cause,
        )


class ExecutionError(HermesError):
    """Runtime execution errors (task failures, pipeline errors, etc.)."""

    def __init__(
        self,
        message: str,
        *,
        detail: str = "",
        status_code: int = 500,
        trace_id: str | None = None,
        cause: Exception | None = None,
        task_name: str | None = None,
    ) -> None:
        self.task_name = task_name
        enriched_detail = detail
        if task_name:
            enriched_detail = f"Task '{task_name}': {detail}" if detail else f"Execution failed for task: '{task_name}'"
        super().__init__(
            message=message,
            code=ErrorCode.EXECUTION_ERROR,
            detail=enriched_detail,
            status_code=status_code,
            trace_id=trace_id,
            cause=cause,
        )


class SecurityError(HermesError):
    """Security / authentication / authorization errors."""

    def __init__(
        self,
        message: str,
        *,
        detail: str = "",
        status_code: int = 403,
        trace_id: str | None = None,
        cause: Exception | None = None,
        required_permission: str | None = None,
    ) -> None:
        self.required_permission = required_permission
        enriched_detail = detail
        if required_permission:
            enriched_detail = f"Requires permission '{required_permission}': {detail}" if detail else f"Missing required permission: '{required_permission}'"
        super().__init__(
            message=message,
            code=ErrorCode.SECURITY_ERROR,
            detail=enriched_detail,
            status_code=status_code,
            trace_id=trace_id,
            cause=cause,
        )


class ResourceNotFoundError(HermesError):
    """Resource not found errors (file, API endpoint, database record, etc.)."""

    def __init__(
        self,
        message: str,
        *,
        detail: str = "",
        status_code: int = 404,
        trace_id: str | None = None,
        cause: Exception | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
    ) -> None:
        self.resource_type = resource_type
        self.resource_id = resource_id
        enriched_detail = detail
        if resource_type and resource_id:
            enriched_detail = f"{resource_type} '{resource_id}' not found: {detail}" if detail else f"{resource_type} '{resource_id}' not found"
        elif resource_type:
            enriched_detail = f"{resource_type} not found: {detail}" if detail else f"{resource_type} not found"
        super().__init__(
            message=message,
            code=ErrorCode.RESOURCE_NOT_FOUND,
            detail=enriched_detail,
            status_code=status_code,
            trace_id=trace_id,
            cause=cause,
        )


class RateLimitError(HermesError):
    """Rate limiting / throttling errors."""

    def __init__(
        self,
        message: str,
        *,
        detail: str = "",
        status_code: int = 429,
        trace_id: str | None = None,
        cause: Exception | None = None,
        retry_after_seconds: float | None = None,
        limit: int | None = None,
        remaining: int | None = None,
    ) -> None:
        self.retry_after_seconds = retry_after_seconds
        self.limit = limit
        self.remaining = remaining
        enriched_detail = detail
        parts = []
        if limit is not None:
            parts.append(f"limit={limit}")
        if remaining is not None:
            parts.append(f"remaining={remaining}")
        if retry_after_seconds is not None:
            parts.append(f"retry_after={retry_after_seconds}s")
        if parts:
            enriched_detail = f"{' | '.join(parts)}: {detail}" if detail else " | ".join(parts)
        super().__init__(
            message=message,
            code=ErrorCode.RATE_LIMIT_ERROR,
            detail=enriched_detail,
            status_code=status_code,
            trace_id=trace_id,
            cause=cause,
        )


class ValidationError(HermesError):
    """Input/data validation errors."""

    def __init__(
        self,
        message: str,
        *,
        detail: str = "",
        status_code: int = 400,
        trace_id: str | None = None,
        cause: Exception | None = None,
        field: str | None = None,
        expected: Any | None = None,
        actual: Any | None = None,
    ) -> None:
        self.field = field
        self.expected = expected
        self.actual = actual
        enriched_detail = detail
        if field:
            parts = [f"field='{field}'"]
            if expected is not None:
                parts.append(f"expected={expected!r}")
            if actual is not None:
                parts.append(f"got={actual!r}")
            enriched_detail = f"{' | '.join(parts)}: {detail}" if detail else " | ".join(parts)
        super().__init__(
            message=message,
            code=ErrorCode.VALIDATION_ERROR,
            detail=enriched_detail,
            status_code=status_code,
            trace_id=trace_id,
            cause=cause,
        )


# ──────────────────────────────────────────────────────────────
# Decorator
# ──────────────────────────────────────────────────────────────

def hermes_error_handler(
    func: F | None = None,
    *,
    default_code: str = ErrorCode.INTERNAL_ERROR,
    default_status: int = 500,
    re_raise: bool = False,
    log_exceptions: bool = True,
) -> Callable[..., Any]:
    """
    Decorator that wraps any exception into a standard HermesError response.

    Usage:
        @hermes_error_handler
        def my_function(...):
            ...

        @hermes_error_handler(default_status=400, re_raise=False)
        def validated_function(...):
            ...

    How it works:
        1. If the raised exception is already a HermesError, it's passed through.
        2. If it's a standard Exception, it's wrapped into a HermesError with
           the appropriate code inferred from the exception class name, or
           the provided default_code / default_status.
        3. The decorator returns the to_dict() result (a dict) by default.
        4. If re_raise=True, the HermesError is raised instead of returning a dict.

    Args:
        func: The function to decorate (used without parentheses).
        default_code: Fallback error code if inference fails.
        default_status: Fallback HTTP status code.
        re_raise: If True, raise the HermesError instead of returning a dict.
        log_exceptions: If True (default), log the exception at error level.

    Returns:
        Decorated function that returns a dict (Scale AI format) or raises.
    """

    def decorator(fn: F) -> F:
        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return fn(*args, **kwargs)
            except HermesError:
                # Already a HermesError — pass through or re-raise
                if log_exceptions:
                    logger.exception("HermesError caught by decorator")
                if re_raise:
                    raise
                # Return the dict representation of the already-structured error
                import sys
                exc_info = sys.exc_info()
                hermes_err = exc_info[1]  # type: ignore[assignment]
                if log_exceptions:
                    logger.error(
                        "HermesError [%s]: %s | trace=%s",
                        hermes_err.code,
                        hermes_err.message,
                        hermes_err.trace_id,
                    )
                return hermes_err.to_dict()
            except Exception as exc:
                # Generic exception — wrap into HermesError
                if log_exceptions:
                    logger.exception("Unhandled exception caught by hermes_error_handler")
                # Infer error code from exception class name, falling back to default
                exc_name = exc.__class__.__name__
                inferred_code = ErrorCode.from_exception_name(exc_name)
                # If the inferred code is a generic fallback (INTERNAL_ERROR),
                # allow the user-provided default_code to take precedence
                if inferred_code == "INTERNAL_ERROR":
                    inferred_code = default_code
                # Map well-known Python exceptions to status codes
                status = default_status
                if isinstance(exc, FileNotFoundError):
                    status = 404
                    inferred_code = ErrorCode.RESOURCE_NOT_FOUND
                elif isinstance(exc, PermissionError):
                    status = 403
                    inferred_code = ErrorCode.PERMISSION_DENIED
                elif isinstance(exc, ValueError) or isinstance(exc, TypeError):
                    status = 400
                    inferred_code = ErrorCode.VALIDATION_ERROR
                elif isinstance(exc, TimeoutError):
                    status = 504
                    inferred_code = ErrorCode.TIMEOUT_ERROR
                elif isinstance(exc, KeyError):
                    status = 400
                    inferred_code = ErrorCode.VALIDATION_ERROR
                # Build the wrapped error
                hermes_err = HermesError(
                    message=str(exc) or f"Unhandled {exc_name}",
                    code=inferred_code,
                    detail=f"{exc_name}: {exc}",
                    status_code=status,
                    cause=exc,
                )
                if re_raise:
                    raise hermes_err from exc
                return hermes_err.to_dict()

        return wrapper  # type: ignore[return-value]

    # Handle bare @hermes_error_handler (no parentheses) case
    if func is not None:
        return decorator(func)

    return decorator


# ──────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────

def _now_iso() -> str:
    """Return ISO 8601 UTC timestamp with millisecond precision."""
    now = datetime.now(UTC)
    # Truncate microseconds to milliseconds for cleaner output
    timestamp = now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z"
    return timestamp


def wrap_exception(
    exc: Exception,
    *,
    message: str | None = None,
    code: str = ErrorCode.INTERNAL_ERROR,
    status_code: int = 500,
) -> dict[str, Any]:
    """
    Convenience function: wrap any exception into the standard error dict format.

    Args:
        exc: The exception to wrap.
        message: Override the human-readable message (default: str(exc)).
        code: Error code (default: INTERNAL_ERROR).
        status_code: HTTP-style status (default: 500).

    Returns:
        Standard error dict: {success: false, error: {...}}
    """
    if isinstance(exc, HermesError):
        return exc.to_dict()
    return HermesError(
        message=message or str(exc) or "Unknown error",
        code=code,
        detail=str(exc),
        status_code=status_code,
        cause=exc,
    ).to_dict()


# ──────────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────────

__all__ = [
    # Base
    "HermesError",
    "ErrorCode",
    # Subclasses
    "ConfigError",
    "ExecutionError",
    "SecurityError",
    "ResourceNotFoundError",
    "RateLimitError",
    "ValidationError",
    # Decorator
    "hermes_error_handler",
    # Utilities
    "wrap_exception",
]
