"""Unit tests for logging utilities

Tests for services/common/logging.py
"""

import json
import logging
from datetime import datetime

import pytest

from services.common.logging import (
    JsonFormatter,
    LogHelper,
    PlainTextFormatter,
    get_logger,
    get_service_logger,
    json_serial,
    log_context,
    log_duration,
    setup_logging,
)


class TestJsonSerial:
    """测试 JSON 序列化"""

    def test_json_serial_datetime(self):
        """测试日期时间序列化"""
        dt = datetime(2024, 1, 1, 12, 0, 0)
        result = json_serial(dt)

        assert result == "2024-01-01T12:00:00"

    def test_json_serial_unsupported_type(self):
        """测试不支持的类型"""
        with pytest.raises(TypeError, match="not serializable"):
            json_serial(object())


class TestJsonFormatter:
    """测试 JSON 格式化器"""

    def test_init_default(self):
        """测试默认初始化"""
        formatter = JsonFormatter(service="test-service")

        assert formatter.service == "test-service"
        assert formatter.environment == "production"
        assert formatter.include_extra is True

    def test_init_custom(self):
        """测试自定义初始化"""
        formatter = JsonFormatter(
            service="test-service",
            environment="development",
            include_extra=False
        )

        assert formatter.environment == "development"
        assert formatter.include_extra is False

    def test_format_basic(self):
        """测试基本格式化"""
        formatter = JsonFormatter(service="test-service")
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None
        )

        result = formatter.format(record)

        assert isinstance(result, str)
        data = json.loads(result)

        assert data["level"] == "INFO"
        assert data["service"] == "test-service"
        assert data["message"] == "Test message"

    def test_format_with_exception(self):
        """测试带异常信息的格式化"""
        formatter = JsonFormatter(service="test-service")

        # Create a record with exception info
        try:
            raise ValueError("Test error")
        except ValueError:
            import sys
            exc_info = sys.exc_info()
            record = logging.LogRecord(
                name="test",
                level=logging.ERROR,
                pathname="test.py",
                lineno=1,
                msg="Error occurred",
                args=(),
                exc_info=exc_info,
            )

        result = formatter.format(record)
        data = json.loads(result)

        assert data["level"] == "ERROR"
        assert "exception" in data

    def test_format_with_custom_attributes(self):
        """测试带自定义属性的格式化"""
        formatter = JsonFormatter(service="test-service")
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None
        )
        # Add custom attributes
        record.duration_ms = 123.45
        record.trace_id = "abc123"
        record.user_id = "user456"

        result = formatter.format(record)
        data = json.loads(result)

        assert data["duration_ms"] == 123.45
        assert data["trace_id"] == "abc123"
        assert data["user_id"] == "user456"


class TestPlainTextFormatter:
    """测试纯文本格式化器"""

    def test_init_default(self):
        """测试默认初始化"""
        formatter = PlainTextFormatter(service="test-service")

        assert formatter.service == "test-service"
        assert formatter.include_colors is False

    def test_init_with_colors(self):
        """测试带颜色初始化"""
        formatter = PlainTextFormatter(service="test-service", include_colors=True)

        assert formatter.include_colors is True
        assert "DEBUG" in formatter.colors
        assert "INFO" in formatter.colors

    def test_format_basic(self):
        """测试基本格式化"""
        formatter = PlainTextFormatter(service="test-service")
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None
        )

        result = formatter.format(record)

        assert "test-service" in result
        assert "INFO" in result
        assert "Test message" in result

    def test_format_with_duration(self):
        """测试带持续时间的格式化"""
        formatter = PlainTextFormatter(service="test-service")
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None
        )
        record.duration_ms = 123

        result = formatter.format(record)

        assert "duration=123ms" in result


class TestSetupLogging:
    """测试日志设置"""

    def test_setup_logging_default(self):
        """测试默认日志设置"""
        logger = setup_logging(service="test-service")

        assert logger is not None
        assert logger.level == logging.INFO

    def test_setup_logging_debug_level(self):
        """测试 DEBUG 级别日志设置"""
        logger = setup_logging(service="test-service", level="DEBUG")

        assert logger.level == logging.DEBUG

    def test_setup_logging_plain_text(self):
        """测试纯文本格式日志设置"""
        logger = setup_logging(service="test-service", json_format=False)

        assert logger is not None


class TestGetLogger:
    """测试获取日志器"""

    def test_get_logger(self):
        """测试获取命名日志器"""
        logger = get_logger("test.module")

        assert logger is not None
        assert logger.name == "test.module"


class TestLogContext:
    """测试日志上下文管理器"""

    def test_log_context_basic(self):
        """测试基本日志上下文"""
        logger = get_logger("test")

        with log_context(logger, user_id="123", request_id="abc") as adapter:
            assert adapter is not None
            assert adapter.extra["user_id"] == "123"
            assert adapter.extra["request_id"] == "abc"


class TestLogDuration:
    """测试日志计时管理器"""

    def test_log_duration(self):
        """测试操作计时"""
        logger = get_logger("test")

        with log_duration(logger, "Test operation"):
            pass  # No-op

        # Should complete without error


class TestLogHelper:
    """测试日志辅助类"""

    def test_init_default(self):
        """测试默认初始化"""
        helper = LogHelper(service="test-service")

        assert helper.service == "test-service"
        assert helper.logger is not None

    def test_init_custom_logger(self):
        """测试自定义日志器"""
        custom_logger = get_logger("custom")
        helper = LogHelper(service="test-service", logger=custom_logger)

        assert helper.logger == custom_logger

    def test_debug(self):
        """测试 DEBUG 日志"""
        helper = LogHelper(service="test-service")

        # Should not raise exception
        helper.debug("Debug message")

    def test_info(self):
        """测试 INFO 日志"""
        helper = LogHelper(service="test-service")

        # Should not raise exception
        helper.info("Info message")

    def test_warning(self):
        """测试 WARNING 日志"""
        helper = LogHelper(service="test-service")

        # Should not raise exception
        helper.warning("Warning message")

    def test_error(self):
        """测试 ERROR 日志"""
        helper = LogHelper(service="test-service")

        # Should not raise exception
        helper.error("Error message")

    def test_critical(self):
        """测试 CRITICAL 日志"""
        helper = LogHelper(service="test-service")

        # Should not raise exception
        helper.critical("Critical message")

    def test_log_with_context(self):
        """测试带上下文的日志"""
        helper = LogHelper(service="test-service")

        # Should not raise exception
        helper.info("Message with context", user_id="123", path="/api/test")


class TestGetServiceLogger:
    """测试获取服务日志器"""

    def test_get_service_logger(self):
        """测试获取服务日志器"""
        helper = get_service_logger("test-service")

        assert helper is not None
        assert helper.service == "test-service"
        assert isinstance(helper, LogHelper)
