# Observability module for full-lifecycle tracking

from __future__ import annotations

import contextvars
import json
import logging
import time
import traceback
import uuid
from collections import deque
from contextlib import asynccontextmanager, contextmanager
from functools import wraps
from datetime import datetime, timezone
from typing import Any, Callable, TypeVar
from typing_extensions import ParamSpec

import structlog

# Context variables for trace propagation across async calls
_trace_id: contextvars.ContextVar[str] = contextvars.ContextVar("trace_id", default="")
_span_id: contextvars.ContextVar[str] = contextvars.ContextVar("span_id", default="")
_parent_span_id: contextvars.ContextVar[str] = contextvars.ContextVar("parent_span_id", default="")
_execution_trace: contextvars.ContextVar[deque] = contextvars.ContextVar(
    "execution_trace", default=deque(maxlen=1000)
)

# Type variables for generic decorators
P = ParamSpec("P")
R = TypeVar("R")

# Configure structured logging
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer()
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)


def generate_trace_id() -> str:
    """Generate a new trace ID."""
    return str(uuid.uuid4())


def generate_span_id() -> str:
    """Generate a new span ID."""
    return str(uuid.uuid4())[:8]


def get_trace_id() -> str:
    """Get the current trace ID."""
    return _trace_id.get() or ""


def get_span_id() -> str:
    """Get the current span ID."""
    return _span_id.get() or ""


def set_trace_context(trace_id: str | None = None, span_id: str | None = None) -> None:
    """Set the trace context for the current execution."""
    if trace_id:
        _trace_id.set(trace_id)
    if span_id:
        _span_id.set(span_id)


class TraceContext:
    """Context manager for managing trace context."""

    def __init__(
        self,
        trace_id: str | None = None,
        span_id: str | None = None,
        parent_span_id: str | None = None,
    ):
        self.trace_id = trace_id or generate_trace_id()
        self.span_id = span_id or generate_span_id()
        self.parent_span_id = parent_span_id
        self.token_trace: contextvars.Token[str] | None = None
        self.token_span: contextvars.Token[str] | None = None
        self.token_parent: contextvars.Token[str] | None = None

    def __enter__(self) -> TraceContext:
        self.token_trace = _trace_id.set(self.trace_id)
        self.token_span = _span_id.set(self.span_id)
        if self.parent_span_id:
            self.token_parent = _parent_span_id.set(self.parent_span_id)
        return self

    def __exit__(self, *args: Any) -> None:
        if self.token_trace:
            _trace_id.reset(self.token_trace)
        if self.token_span:
            _span_id.reset(self.token_span)
        if self.token_parent:
            _parent_span_id.reset(self.token_parent)


def _log_event(
    event_type: str,
    payload: dict[str, Any] | None = None,
    level: str = "info",
) -> None:
    """Log an event with structured context."""
    log_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "trace_id": get_trace_id(),
        "span_id": get_span_id(),
        "event_type": event_type,
        "payload": payload or {},
    }

    # Add to execution trace
    trace = _execution_trace.get()
    trace.append(log_entry)

    # Log via structlog
    log_fn = getattr(logger, level, logger.info)
    log_fn(event_type, **log_entry)


class LifecycleTracker:
    """Decorator and context manager for tracking function lifecycle."""

    def __init__(
        self,
        name: str | None = None,
        log_args: bool = True,
        log_result: bool = True,
        log_exceptions: bool = True,
        enable_trace: bool = True,
    ):
        """
        Initialize the lifecycle tracker.

        Args:
            name: Name for the tracked operation (defaults to function name)
            log_args: Whether to log input arguments
            log_result: Whether to log return values
            log_exceptions: Whether to log exception details
            enable_trace: Whether to add to execution trace
        """
        self.name = name
        self.log_args = log_args
        self.log_result = log_result
        self.log_exceptions = log_exceptions
        self.enable_trace = enable_trace

    def __call__(self, func: Callable[P, R]) -> Callable[P, R]:
        """Decorator usage."""

        @wraps(func)
        def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            return self._sync_track(func, args, kwargs)

        @wraps(func)
        async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            return await self._async_track(func, args, kwargs)

        # Check if function is async
        if hasattr(func, "__wrapped__"):
            return async_wrapper
        import inspect
        if inspect.iscoroutinefunction(func):
            return async_wrapper  # type: ignore[return-value]
        return sync_wrapper  # type: ignore[return-value]

    def _sync_track(
        self,
        func: Callable[P, R],
        args: P.args,
        kwargs: P.kwargs,
    ) -> R:
        """Track synchronous function execution."""
        operation_name = self.name or f"{func.__module__}.{func.__qualname__}"
        span_id = generate_span_id()
        parent_span_id = get_span_id()

        with TraceContext(span_id=span_id, parent_span_id=parent_span_id):
            start_time = time.perf_counter()

            # Log function start
            payload = {"function": func.__name__}
            if self.log_args:
                payload["args"] = self._sanitize_args(args, kwargs)

            _log_event("Function_Start", payload, level="debug")

            try:
                result = func(*args, **kwargs)

                # Log function success
                duration_ms = (time.perf_counter() - start_time) * 1000
                return_payload = {
                    "function": func.__name__,
                    "duration_ms": round(duration_ms, 2),
                }
                if self.log_result:
                    return_payload["return_value"] = self._sanitize_result(result)

                _log_event("Function_End", return_payload, level="debug")

                return result

            except Exception as e:
                # Log exception
                duration_ms = (time.perf_counter() - start_time) * 1000
                error_payload = {
                    "function": func.__name__,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "duration_ms": round(duration_ms, 2),
                }
                if self.log_exceptions:
                    error_payload["stack_trace"] = traceback.format_exc()

                _log_event("Function_Error", error_payload, level="error")
                raise

    async def _async_track(
        self,
        func: Callable[P, R],
        args: P.args,
        kwargs: P.kwargs,
    ) -> R:
        """Track async function execution."""
        operation_name = self.name or f"{func.__module__}.{func.__qualname__}"
        span_id = generate_span_id()
        parent_span_id = get_span_id()

        with TraceContext(span_id=span_id, parent_span_id=parent_span_id):
            start_time = time.perf_counter()

            # Log function start
            payload = {"function": func.__name__}
            if self.log_args:
                payload["args"] = self._sanitize_args(args, kwargs)

            _log_event("Function_Start", payload, level="debug")

            try:
                result = await func(*args, **kwargs)

                # Log function success
                duration_ms = (time.perf_counter() - start_time) * 1000
                return_payload = {
                    "function": func.__name__,
                    "duration_ms": round(duration_ms, 2),
                }
                if self.log_result:
                    return_payload["return_value"] = self._sanitize_result(result)

                _log_event("Function_End", return_payload, level="debug")

                return result

            except Exception as e:
                # Log exception
                duration_ms = (time.perf_counter() - start_time) * 1000
                error_payload = {
                    "function": func.__name__,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "duration_ms": round(duration_ms, 2),
                }
                if self.log_exceptions:
                    error_payload["stack_trace"] = traceback.format_exc()

                _log_event("Function_Error", error_payload, level="error")
                raise

    @staticmethod
    def _sanitize_args(args: tuple, kwargs: dict) -> dict:
        """Sanitize function arguments for logging."""
        result = {"args_count": len(args)}
        # Only log non-sensitive keyword arguments
        sensitive_keys = {"password", "secret", "token", "api_key", "key"}
        sanitized_kwargs = {}
        for k, v in kwargs.items():
            if k.lower() in sensitive_keys:
                sanitized_kwargs[k] = "***REDACTED***"
            elif hasattr(v, "__dict__"):
                sanitized_kwargs[k] = f"<{type(v).__name__} object>"
            else:
                sanitized_kwargs[k] = str(v)[:100]
        result["kwargs"] = sanitized_kwargs
        return result

    @staticmethod
    def _sanitize_result(result: Any) -> Any:
        """Sanitize result for logging."""
        if isinstance(result, (list, dict)):
            return f"<{type(result).__name__} with {len(result)} items>"
        if hasattr(result, "__dict__"):
            return f"<{type(result).__name__} object>"
        return str(result)[:100]


@contextmanager
def track_operation(
    operation_name: str,
    **metadata: Any,
):
    """Context manager for tracking an operation.

    Usage:
        with track_operation("data_processing", table="users", rows=1000):
            # Do work
            pass
    """
    span_id = generate_span_id()
    parent_span_id = get_span_id()
    start_time = time.perf_counter()

    with TraceContext(span_id=span_id, parent_span_id=parent_span_id):
        _log_event("Operation_Start", {"operation": operation_name, **metadata})

        try:
            yield

            duration_ms = (time.perf_counter() - start_time) * 1000
            _log_event(
                "Operation_End",
                {
                    "operation": operation_name,
                    "duration_ms": round(duration_ms, 2),
                    **metadata,
                },
            )

        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            _log_event(
                "Operation_Error",
                {
                    "operation": operation_name,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "duration_ms": round(duration_ms, 2),
                    **metadata,
                },
                level="error",
            )
            raise


@asynccontextmanager
async def track_operation_async(
    operation_name: str,
    **metadata: Any,
):
    """Async context manager for tracking an operation."""
    span_id = generate_span_id()
    parent_span_id = get_span_id()
    start_time = time.perf_counter()

    with TraceContext(span_id=span_id, parent_span_id=parent_span_id):
        _log_event("Operation_Start", {"operation": operation_name, **metadata})

        try:
            yield

            duration_ms = (time.perf_counter() - start_time) * 1000
            _log_event(
                "Operation_End",
                {
                    "operation": operation_name,
                    "duration_ms": round(duration_ms, 2),
                    **metadata,
                },
            )

        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            _log_event(
                "Operation_Error",
                {
                    "operation": operation_name,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "duration_ms": round(duration_ms, 2),
                    **metadata,
                },
                level="error",
            )
            raise


def log_branch(
    condition: str,
    result: bool,
    **metadata: Any,
) -> None:
    """Log a branch/decision point in code."""
    _log_event(
        "Branch",
        {"condition": condition, "result": result, **metadata},
        level="debug",
    )


def log_loop_iteration(
    loop_name: str,
    iteration: int,
    total: int | None = None,
    **metadata: Any,
) -> None:
    """Log a loop iteration (use sparingly for performance)."""
    _log_event(
        "Loop_Iteration",
        {
            "loop": loop_name,
            "iteration": iteration,
            "total": total,
            **metadata,
        },
        level="debug",
    )


def get_execution_trace() -> list[dict[str, Any]]:
    """Get the current execution trace for this request."""
    return list(_execution_trace.get())


def generate_execution_report() -> dict[str, Any]:
    """Generate an execution trace report for the current trace."""
    trace = get_execution_trace()

    if not trace:
        return {"trace_id": get_trace_id(), "events": []}

    # Calculate statistics
    function_starts = [e for e in trace if e["event_type"] == "Function_Start"]
    function_ends = [e for e in trace if e["event_type"] == "Function_End"]
    errors = [e for e in trace if "Error" in e["event_type"]]

    # Calculate total duration
    if trace:
        start_time = trace[0]["timestamp"]
        end_time = trace[-1]["timestamp"]
    else:
        start_time = end_time = None

    return {
        "trace_id": get_trace_id(),
        "event_count": len(trace),
        "function_calls": len(function_starts),
        "error_count": len(errors),
        "start_time": start_time,
        "end_time": end_time,
        "events": trace,
        "errors": [
            {"event_type": e["event_type"], "payload": e["payload"]}
            for e in errors
        ],
    }


# Export commonly used items
__all__ = [
    "LifecycleTracker",
    "track_operation",
    "track_operation_async",
    "log_branch",
    "log_loop_iteration",
    "get_trace_id",
    "get_span_id",
    "set_trace_context",
    "TraceContext",
    "get_execution_trace",
    "generate_execution_report",
    "generate_trace_id",
    "generate_span_id",
]
