#!/usr/bin/env python3
"""Tests for error_framework.py — Unified Error Handling Framework"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path.home() / ".hermes"))


class TestErrorCode:
    """ErrorCode — 规范错误码常量"""

    def test_has_all_codes(self):
        """具有所有标准错误码"""
        from scripts.error_framework import ErrorCode
        assert ErrorCode.CONFIG_ERROR == "CONFIG_ERROR"
        assert ErrorCode.EXECUTION_ERROR == "EXECUTION_ERROR"
        assert ErrorCode.SECURITY_ERROR == "SECURITY_ERROR"
        assert ErrorCode.RESOURCE_NOT_FOUND == "RESOURCE_NOT_FOUND"
        assert ErrorCode.RATE_LIMIT_ERROR == "RATE_LIMIT_ERROR"
        assert ErrorCode.VALIDATION_ERROR == "VALIDATION_ERROR"
        assert ErrorCode.INTERNAL_ERROR == "INTERNAL_ERROR"
        assert ErrorCode.TIMEOUT_ERROR == "TIMEOUT_ERROR"
        assert ErrorCode.AUTHENTICATION_ERROR == "AUTHENTICATION_ERROR"
        assert ErrorCode.PERMISSION_DENIED == "PERMISSION_DENIED"
        assert ErrorCode.UNKNOWN_ERROR == "UNKNOWN_ERROR"

    def test_from_exception_name_known(self):
        """已知异常类名 → 映射到对应错误码"""
        from scripts.error_framework import ErrorCode
        assert ErrorCode.from_exception_name("ConfigError") == "CONFIG_ERROR"
        assert ErrorCode.from_exception_name("ExecutionError") == "EXECUTION_ERROR"
        assert ErrorCode.from_exception_name("ValidationError") == "VALIDATION_ERROR"
        assert ErrorCode.from_exception_name("SecurityError") == "SECURITY_ERROR"

    def test_from_exception_name_unknown(self):
        """未知异常类名 → 返回 INTERNAL_ERROR"""
        from scripts.error_framework import ErrorCode
        assert ErrorCode.from_exception_name("WeirdError") == "INTERNAL_ERROR"
        assert ErrorCode.from_exception_name("") == "INTERNAL_ERROR"


class TestHermesError:
    """HermesError — 基础异常类"""

    def test_basic_creation(self):
        """创建基础异常"""
        from scripts.error_framework import HermesError
        err = HermesError("test error")
        assert str(err) == "[INTERNAL_ERROR] test error"
        assert err.code == "INTERNAL_ERROR"
        assert err.status_code == 500

    def test_custom_code_and_status(self):
        """自定义错误码和状态码"""
        from scripts.error_framework import HermesError
        err = HermesError("not found", code="RESOURCE_NOT_FOUND", status_code=404)
        assert err.code == "RESOURCE_NOT_FOUND"
        assert err.status_code == 404
        assert err.message == "not found"

    def test_to_dict_scale_ai_format(self):
        """to_dict() 返回 Scale AI 标准格式"""
        from scripts.error_framework import HermesError
        err = HermesError("test msg", code="VAL_ERROR", detail="some detail")
        d = err.to_dict()
        assert d["success"] is False
        assert d["error"]["code"] == "VAL_ERROR"
        assert d["error"]["message"] == "test msg"
        assert d["error"]["detail"] == "some detail"
        assert "trace_id" in d["error"]
        assert "timestamp" in d["error"]

    def test_to_problem_detail_rfc_9457(self):
        """to_problem_detail() 返回 RFC 9457 格式"""
        from scripts.error_framework import HermesError
        err = HermesError("test", code="CONFIG_ERROR", status_code=400, detail="detail")
        pd = err.to_problem_detail()
        assert pd["type"] == "urn:hermes:error:config_error"
        assert pd["title"] == "test"
        assert pd["status"] == 400
        assert pd["detail"] == "detail"
        assert pd["instance"].startswith("urn:hermes:trace:")

    def test_trace_id_auto_generated(self):
        """trace_id 自动生成"""
        from scripts.error_framework import HermesError
        err = HermesError("test")
        assert err.trace_id is not None
        assert len(err.trace_id) > 0

    def test_trace_id_custom(self):
        """trace_id 可自定义传入"""
        from scripts.error_framework import HermesError
        err = HermesError("test", trace_id="my_custom_id")
        assert err.trace_id == "my_custom_id"

    def test_repr(self):
        """__repr__ 包含关键信息"""
        from scripts.error_framework import HermesError
        err = HermesError("msg", code="CONFIG_ERROR", status_code=400)
        r = repr(err)
        assert "HermesError" in r
        assert "CONFIG_ERROR" in r
        assert "msg" in r

    def test_cause_chaining(self):
        """cause 记录原始异常"""
        from scripts.error_framework import HermesError
        original = ValueError("original error")
        err = HermesError("wrapped", cause=original)
        assert err._cause is original
        # The cause is not chained via __cause__ when passed as kwarg
        # (HermesError.__init__ doesn't use super().__init__(message, cause))



class TestConfigError:
    """ConfigError — 配置错误"""

    def test_creation(self):
        from scripts.error_framework import ConfigError
        err = ConfigError("config broken", config_key="MY_KEY")
        assert err.code == "CONFIG_ERROR"
        assert err.config_key == "MY_KEY"
        assert "MY_KEY" in err.detail

    def test_default_status(self):
        from scripts.error_framework import ConfigError
        err = ConfigError("test")
        assert err.status_code == 500


class TestExecutionError:
    """ExecutionError — 执行错误"""

    def test_creation(self):
        from scripts.error_framework import ExecutionError
        err = ExecutionError("task failed", task_name="my_task")
        assert err.code == "EXECUTION_ERROR"
        assert err.task_name == "my_task"
        assert "my_task" in err.detail


class TestSecurityError:
    """SecurityError — 安全错误"""

    def test_creation(self):
        from scripts.error_framework import SecurityError
        err = SecurityError("access denied", required_permission="admin")
        assert err.code == "SECURITY_ERROR"
        assert err.status_code == 403
        assert "admin" in err.detail


class TestResourceNotFoundError:
    """ResourceNotFoundError — 资源未找到"""

    def test_creation_with_type_and_id(self):
        from scripts.error_framework import ResourceNotFoundError
        err = ResourceNotFoundError("file missing", resource_type="file", resource_id="config.yaml")
        assert err.code == "RESOURCE_NOT_FOUND"
        assert err.status_code == 404
        assert "config.yaml" in err.detail

    def test_creation_with_type_only(self):
        from scripts.error_framework import ResourceNotFoundError
        err = ResourceNotFoundError("not found", resource_type="database")
        assert "database" in err.detail


class TestRateLimitError:
    """RateLimitError — 速率限制"""

    def test_creation(self):
        from scripts.error_framework import RateLimitError
        err = RateLimitError("too fast", limit=100, remaining=0, retry_after_seconds=30)
        assert err.code == "RATE_LIMIT_ERROR"
        assert err.status_code == 429
        assert "limit=100" in err.detail
        assert "retry_after=30" in err.detail

    def test_no_optional_params(self):
        from scripts.error_framework import RateLimitError
        err = RateLimitError("rate limited")
        assert err.status_code == 429


class TestValidationError:
    """ValidationError — 验证错误"""

    def test_creation_with_field(self):
        from scripts.error_framework import ValidationError
        err = ValidationError("invalid input", field="email", expected="valid email", actual="bad")
        assert err.code == "VALIDATION_ERROR"
        assert err.status_code == 400
        assert "email" in err.detail

    def test_field_only(self):
        from scripts.error_framework import ValidationError
        err = ValidationError("missing", field="name")
        assert "name" in err.detail


class TestHermesErrorHandler:
    """@hermes_error_handler — 装饰器"""

    def test_wraps_generic_exception(self):
        """包装普通异常为错误 dict"""
        from scripts.error_framework import hermes_error_handler
        @hermes_error_handler
        def failing():
            raise ValueError("bad value")
        result = failing()
        assert result["success"] is False
        assert "VALIDATION_ERROR" in result["error"]["code"]

    def test_passes_hermes_error_through(self):
        """HermesError 直接通过"""
        from scripts.error_framework import HermesError, hermes_error_handler
        @hermes_error_handler
        def failing():
            raise HermesError("my error", code="CONFIG_ERROR")
        result = failing()
        assert result["error"]["code"] == "CONFIG_ERROR"

    def test_re_raise_raises_exception(self):
        """re_raise=True 时重新抛出异常"""
        from scripts.error_framework import HermesError, hermes_error_handler
        @hermes_error_handler(re_raise=True)
        def failing():
            raise ValueError("boom")
        with pytest.raises(HermesError):
            failing()

    def test_successful_function_returns_value(self):
        """正常函数返回原值"""
        from scripts.error_framework import hermes_error_handler
        @hermes_error_handler
        def ok_func():
            return {"success": True, "data": 42}
        result = ok_func()
        assert result["data"] == 42

    def test_file_not_found_mapped(self):
        """FileNotFoundError 映射为 RESOURCE_NOT_FOUND + 404"""
        from scripts.error_framework import hermes_error_handler
        @hermes_error_handler
        def failing():
            raise FileNotFoundError("no file")
        result = failing()
        assert result["error"]["code"] == "RESOURCE_NOT_FOUND"
        # status_code is an attribute on the HermesError, not in the error dict
        # Only 'code','message','detail','trace_id','timestamp' appear in the dict


    def test_permission_error_mapped(self):
        """PermissionError 映射为 PERMISSION_DENIED + 403"""
        from scripts.error_framework import hermes_error_handler
        @hermes_error_handler
        def failing():
            raise PermissionError("no permission")
        result = failing()
        assert result["error"]["code"] == "PERMISSION_DENIED"

    def test_custom_default_code(self):
        """自定义默认错误码"""
        from scripts.error_framework import hermes_error_handler
        @hermes_error_handler(default_code="CUSTOM_CODE", default_status=418)
        def failing():
            raise RuntimeError("custom fail")
        result = failing()
        assert result["error"]["code"] == "CUSTOM_CODE"


class TestWrapException:
    """wrap_exception() — 便利函数"""

    def test_wraps_plain_exception(self):
        from scripts.error_framework import wrap_exception
        exc = ValueError("oops")
        result = wrap_exception(exc)
        assert result["success"] is False
        assert "oops" in result["error"]["message"]

    def test_wraps_hermes_error_directly(self):
        from scripts.error_framework import HermesError, wrap_exception
        exc = HermesError("structured", code="CONFIG_ERROR")
        result = wrap_exception(exc)
        assert result["error"]["code"] == "CONFIG_ERROR"

    def test_custom_message_and_code(self):
        from scripts.error_framework import wrap_exception
        exc = RuntimeError("raw")
        result = wrap_exception(exc, message="custom msg", code="CUSTOM", status_code=418)
        assert result["error"]["message"] == "custom msg"
        assert result["error"]["code"] == "CUSTOM"


class TestNowIso:
    """_now_iso() — 时间戳生成"""

    def test_returns_string(self):
        from scripts.error_framework import _now_iso
        ts = _now_iso()
        assert isinstance(ts, str)
        assert ts.endswith("Z")
        assert "T" in ts
