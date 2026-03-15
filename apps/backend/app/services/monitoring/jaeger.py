"""
Jaeger Trace Exporter Service

Integrates with Jaeger for distributed tracing.
"""

import logging
import time
from contextlib import contextmanager
from datetime import datetime
from typing import Optional, Dict, Any, List, Generator
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class TraceExporter:
    """
    Jaeger distributed tracing exporter

    Handles span creation, context propagation, and trace export to Jaeger.
    """

    def __init__(
        self,
        jaeger_agent_host: str = "localhost",
        jaeger_agent_port: int = 6831,
        service_name: str = "one-data-studio",
    ):
        """
        Initialize trace exporter

        Args:
            jaeger_agent_host: Jaeger agent host
            jaeger_agent_port: Jaeger agent port
            service_name: Service name for traces
        """
        self.jaeger_agent_host = jaeger_agent_host
        self.jaeger_agent_port = jaeger_agent_port
        self.service_name = service_name
        self._tracer = None

    @property
    def tracer(self):
        """Lazy load Jaeger tracer"""
        if self._tracer is None:
            try:
                from jaeger_client import ThriftClient
                from jaeger_client import Config

                config = Config(
                    host=self.jaeger_agent_host,
                    port=self.jaeger_agent_port,
                    reporter_type="jaeger",
                    sampler_type="const",
                    sampler_param=1,  # Sample 100% of traces
                )

                self._tracer = config.initialize_tracer()
            except ImportError:
                logger.warning("jaeger_client not installed")
                self._tracer = None

        return self._tracer

    @contextmanager
    def trace(
        self,
        operation_name: str,
        tags: Optional[Dict[str, Any]] = None,
    ) -> Generator["Span", None, None]:
        """
        Context manager for tracing an operation

        Args:
            operation_name: Name of the operation
            tags: Tags to add to the span

        Yields:
            Span object
        """
        if not self.tracer:
            yield None
            return

        with self.tracer.start_span(
            operation_name=operation_name,
            tags=tags or {},
        ) as span:
            yield span

    async def export_span(
        self,
        operation_name: str,
        parent_span: Optional[Any] = None,
        tags: Optional[Dict[str, Any]] = None,
        logs: Optional[List[Dict[str, Any]]] = None,
    ) -> Optional[str]:
        """
        Export a span to Jaeger

        Args:
            operation_name: Name of the operation
            parent_span: Parent span context
            tags: Span tags
            logs: Span logs

        Returns:
            Span ID or None
        """
        if not self.tracer:
            return None

        try:
            with self.tracer.start_span(
                operation_name=operation_name,
                child_of=parent_span,
                tags=tags or {},
            ) as span:
                # Add logs
                if logs:
                    for log in logs:
                        span.log_kv(**log)

                return span.span_id

        except Exception as e:
            logger.error(f"Failed to export span: {e}")
            return None

    def inject_context(
        self,
        span: Any,
    ) -> Dict[str, str]:
        """
        Inject span context into headers

        Args:
            span: Span object

        Returns:
            Headers with trace context
        """
        if not span:
            return {}

        try:
            from jaeger_client.code import TraceCode
            from opentracing import Format

            headers = {}
            span_context = span.context

            # Inject context into headers
            tracer = self.tracer
            tracer.inject(span_context, Format.TEXT_MAP, headers)

            return headers

        except Exception as e:
            logger.error(f"Failed to inject context: {e}")
            return {}

    def extract_context(
        self,
        headers: Dict[str, str],
    ) -> Optional[Any]:
        """
        Extract span context from headers

        Args:
            headers: HTTP headers

        Returns:
            Span context or None
        """
        if not self.tracer:
            return None

        try:
            from opentracing import Format

            span_context = self.tracer.extract(
                Format.TEXT_MAP,
                headers,
            )

            return span_context

        except Exception as e:
            logger.error(f"Failed to extract context: {e}")
            return None

    async def create_span(
        self,
        operation_name: str,
        headers: Optional[Dict[str, str]] = None,
        tags: Optional[Dict[str, Any]] = None,
    ) -> Optional["ActiveSpan"]:
        """
        Create and start a new span

        Args:
            operation_name: Name of the operation
            headers: Incoming headers with trace context
            tags: Span tags

        Returns:
            ActiveSpan context
        """
        if not self.tracer:
            return None

        try:
            # Extract parent context if available
            parent_span = None
            if headers:
                parent_span = self.extract_context(headers)

            # Create span
            span = self.tracer.start_span(
                operation_name=operation_name,
                child_of=parent_span,
                tags=tags or {},
            )

            return ActiveSpan(span, self.tracer)

        except Exception as e:
            logger.error(f"Failed to create span: {e}")
            return None

    async def get_trace(
        self,
        trace_id: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Get trace from Jaeger

        Args:
            trace_id: Trace ID

        Returns:
            Trace data or None
        """
        try:
            import requests

            url = f"http://{self.jaeger_agent_host}:16686/api/traces/{trace_id}"
            response = requests.get(url, timeout=10)

            if response.status_code == 200:
                return response.json()

            return None

        except Exception as e:
            logger.error(f"Failed to get trace: {e}")
            return None

    async def query_traces(
        self,
        service: str,
        operation: Optional[str] = None,
        limit: int = 100,
        lookback: str = "1h",
    ) -> List[Dict[str, Any]]:
        """
        Query traces from Jaeger

        Args:
            service: Service name
            operation: Operation name filter
            limit: Maximum number of traces
            lookback: Time range (e.g., "1h", "1d")

        Returns:
            List of traces
        """
        try:
            import requests

            url = f"http://{self.jaeger_agent_host}:16686/api/traces"
            params = {
                "service": service,
                "limit": limit,
                "lookback": lookback,
            }

            if operation:
                params["operation"] = operation

            response = requests.get(url, params=params, timeout=30)

            if response.status_code == 200:
                return response.json().get("data", [])

            return []

        except Exception as e:
            logger.error(f"Failed to query traces: {e}")
            return []

    async def get_services(self) -> List[str]:
        """
        Get list of services from Jaeger

        Returns:
            List of service names
        """
        try:
            import requests

            url = f"http://{self.jaeger_agent_host}:16686/api/services"
            response = requests.get(url, timeout=10)

            if response.status_code == 200:
                data = response.json()
                return data.get("data", [])

            return []

        except Exception as e:
            logger.error(f"Failed to get services: {e}")
            return []


class ActiveSpan:
    """Context manager for active span"""

    def __init__(self, span: Any, tracer: Any):
        """
        Initialize active span

        Args:
            span: Jaeger span
            tracer: Jaeger tracer
        """
        self.span = span
        self.tracer = tracer

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            # Record exception
            self.span.set_tag("error", True)
            self.span.set_tag("error.message", str(exc_val))

        self.span.finish()
        return False

    def add_tag(self, key: str, value: Any) -> None:
        """Add tag to span"""
        self.span.set_tag(key, value)

    def log(self, level: str, message: str, payload: Optional[Dict] = None) -> None:
        """Add log to span"""
        log_data = {
            "level": level,
            "message": message,
        }
        if payload:
            log_data["payload"] = payload

        self.span.log_kv(**log_data)

    def finish(self) -> None:
        """Finish the span"""
        self.span.finish()


def get_trace_exporter(
    jaeger_agent_host: str = "localhost",
    jaeger_agent_port: int = 6831,
    service_name: str = "one-data-studio",
) -> TraceExporter:
    """Get or create trace exporter instance"""
    return TraceExporter(
        jaeger_agent_host=jaeger_agent_host,
        jaeger_agent_port=jaeger_agent_port,
        service_name=service_name,
    )
