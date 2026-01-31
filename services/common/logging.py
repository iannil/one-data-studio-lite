# ONE-DATA-STUDIO-LITE - 统一日志配置
# 位置: services/common/logging.py

"""
统一日志配置模块

提供统一的日志格式、配置和工具函数，确保所有服务日志格式一致，
便于 Loki 聚合分析和 Grafana 可视化。
"""

import logging
import sys
import json
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Optional, Dict
from contextlib import contextmanager
import time

# JSON 日期编码器
def json_serial(obj: Any) -> str:
    """JSON 序列化辅助函数，处理特殊类型"""
    if isinstance(obj, (datetime,)):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")


class JsonFormatter(logging.Formatter):
    """
    JSON 格式化器

    输出 JSON 格式日志，包含结构化字段，便于 Loki 解析和查询。
    输出格式示例：
    {
        "timestamp": "2024-01-30T10:30:00.123Z",
        "level": "INFO",
        "service": "portal",
        "message": "Request processed",
        "context": {
            "path": "/api/v1/users",
            "method": "GET",
            "status": 200,
            "duration_ms": 123
        },
        "trace_id": "abc123",
        "span_id": "def456"
    }
    """

    def __init__(
        self,
        service: str,
        environment: str = "production",
        include_extra: bool = True
    ):
        super().__init__()
        self.service = service
        self.environment = environment
        self.include_extra = include_extra

    def format(self, record: logging.LogRecord) -> str:
        # 基础日志数据
        log_data: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "service": self.service,
            "environment": self.environment,
            "message": record.getMessage(),
            "logger": record.name,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # 添加异常信息
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": self.formatException(record.exc_info) if record.exc_info else None
            }

        # 添加上下文字段
        if hasattr(record, "duration_ms"):
            log_data["duration_ms"] = record.duration_ms
        if hasattr(record, "trace_id"):
            log_data["trace_id"] = record.trace_id
        if hasattr(record, "span_id"):
            log_data["span_id"] = record.span_id
        if hasattr(record, "user_id"):
            log_data["user_id"] = record.user_id
        if hasattr(record, "path"):
            log_data["path"] = record.path
        if hasattr(record, "method"):
            log_data["method"] = record.method
        if hasattr(record, "status"):
            log_data["status"] = record.status

        # 添加额外字段
        if self.include_extra and hasattr(record, "context"):
            log_data["context"] = record.context

        return json.dumps(log_data, default=json_serial, ensure_ascii=False)


class PlainTextFormatter(logging.Formatter):
    """
    纯文本格式化器

    输出人类可读的纯文本日志格式，适合开发环境。
    格式: [TIMESTAMP] LEVEL SERVICE MESSAGE
    """

    def __init__(
        self,
        service: str,
        include_colors: bool = False
    ):
        super().__init__()
        self.service = service
        self.include_colors = include_colors

        # ANSI 颜色代码
        if include_colors:
            self.colors = {
                "DEBUG": "\033[36m",    # 青色
                "INFO": "\033[32m",     # 绿色
                "WARNING": "\033[33m",  # 黄色
                "ERROR": "\033[31m",    # 红色
                "CRITICAL": "\033[35m", # 紫色
                "RESET": "\033[0m"
            }
        else:
            self.colors = {}

    def format(self, record: logging.LogRecord) -> str:
        level = record.levelname
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

        # 添加颜色
        if self.include_colors and level in self.colors:
            level_colored = f"{self.colors[level]}{level}{self.colors['RESET']}"
        else:
            level_colored = level

        # 基础格式
        message = f"[{timestamp}] {level_colored:8} {self.service:15} {record.getMessage()}"

        # 添加额外上下文
        extra_parts = []
        if hasattr(record, "duration_ms"):
            extra_parts.append(f"duration={record.duration_ms}ms")
        if hasattr(record, "trace_id"):
            extra_parts.append(f"trace={record.trace_id}")
        if hasattr(record, "path"):
            extra_parts.append(f"path={record.path}")

        if extra_parts:
            message += f" [{' '.join(extra_parts)}]"

        # 添加异常信息
        if record.exc_info:
            message += "\n" + self.formatException(record.exc_info)

        return message


def setup_logging(
    service: str,
    level: str = "INFO",
    environment: str = "production",
    log_file: Optional[str] = None,
    json_format: bool = True
) -> logging.Logger:
    """
    配置统一日志

    Args:
        service: 服务名称（如 portal, nl2sql）
        level: 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        environment: 环境名称 (development, production)
        log_file: 日志文件路径（可选）
        json_format: 是否使用 JSON 格式（生产环境推荐）

    Returns:
        配置好的 logger 实例
    """
    # 获取根日志器
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # 清除现有处理器
    logger.handlers.clear()

    # 选择格式化器
    if json_format:
        formatter = JsonFormatter(service=service, environment=environment)
    else:
        include_colors = environment == "development"
        formatter = PlainTextFormatter(service=service, include_colors=include_colors)

    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(getattr(logging, level.upper(), logging.INFO))
    logger.addHandler(console_handler)

    # 文件处理器（如果指定）
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.DEBUG)  # 文件记录所有级别
        logger.addHandler(file_handler)

    return logger


def get_logger(name: str) -> logging.Logger:
    """获取命名日志器"""
    return logging.getLogger(name)


@contextmanager
def log_context(
    logger: logging.Logger,
    **context
):
    """
    日志上下文管理器

    在 with 块中自动添加上下文信息到所有日志。

    Example:
        with log_context(logger, user_id="123", request_id="abc"):
            logger.info("Processing request")  # 自动包含 user_id 和 request_id
    """
    # 创建日志适配器
    class ContextAdapter(logging.LoggerAdapter):
        def process(self, msg, kwargs):
            # 将上下文添加到 extra
            extra = kwargs.get("extra", {})
            for key, value in self.extra.items():
                extra[key] = value
            kwargs["extra"] = extra
            return msg, kwargs

    adapter = ContextAdapter(logger, context)
    yield adapter


@contextmanager
def log_duration(
    logger: logging.Logger,
    operation: str,
    level: str = "INFO"
):
    """
    计时上下文管理器

    自动记录操作耗时。

    Example:
        with log_duration(logger, "Database query"):
            result = db.query(...)
    """
    start_time = time.time()
    try:
        yield
    finally:
        duration_ms = (time.time() - start_time) * 1000
        log_func = getattr(logger, level.lower(), logger.info)
        log_func(
            f"{operation} completed",
            extra={"duration_ms": duration_ms, "operation": operation}
        )


class LogHelper:
    """
    日志辅助类

    提供便捷的日志方法，自动添加常用字段。
    """

    def __init__(self, service: str, logger: Optional[logging.Logger] = None):
        self.service = service
        self.logger = logger or logging.getLogger(service)

    def _log_with_context(self, level: str, message: str, **context):
        """带上下文的日志记录"""
        log_func = getattr(self.logger, level.lower(), self.logger.info)
        extra = {"service": self.service, **context}
        log_func(message, extra=extra)

    def debug(self, message: str, **context):
        self._log_with_context("DEBUG", message, **context)

    def info(self, message: str, **context):
        self._log_with_context("INFO", message, **context)

    def warning(self, message: str, **context):
        self._log_with_context("WARNING", message, **context)

    def error(self, message: str, **context):
        self._log_with_context("ERROR", message, **context)

    def critical(self, message: str, **context):
        self._log_with_context("CRITICAL", message, **context)

    def log_request(
        self,
        method: str,
        path: str,
        status: int,
        duration_ms: float,
        **context
    ):
        """记录 API 请求"""
        self.info(
            f"{method} {path} - {status}",
            method=method,
            path=path,
            status=status,
            duration_ms=duration_ms,
            **context
        )

    def log_error(
        self,
        error: Exception,
        message: str = "Error occurred",
        **context
    ):
        """记录异常"""
        self.error(
            f"{message}: {type(error).__name__}: {str(error)}",
            error_type=type(error).__name__,
            error_message=str(error),
            **context
        )

    def log_external_call(
        self,
        service: str,
        endpoint: str,
        status: str,
        duration_ms: float,
        **context
    ):
        """记录外部服务调用"""
        level = "INFO" if status == "success" else "ERROR"
        self._log_with_context(
            level,
            f"External call to {service} - {endpoint}",
            external_service=service,
            endpoint=endpoint,
            call_status=status,
            duration_ms=duration_ms,
            **context
        )


# 创建服务日志器的工厂函数
_service_loggers: Dict[str, LogHelper] = {}


def get_service_logger(service: str) -> LogHelper:
    """
    获取服务日志辅助类

    Args:
        service: 服务名称

    Returns:
        LogHelper 实例
    """
    if service not in _service_loggers:
        _service_loggers[service] = LogHelper(service)
    return _service_loggers[service]
