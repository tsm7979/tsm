"""
Distributed Tracing
===================

OpenTelemetry-compatible distributed tracing for observability.
"""

from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import time
import uuid
import logging
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class SpanKind(str, Enum):
    """Span kind types."""
    INTERNAL = "internal"
    SERVER = "server"
    CLIENT = "client"
    PRODUCER = "producer"
    CONSUMER = "consumer"


class SpanStatus(str, Enum):
    """Span status."""
    UNSET = "unset"
    OK = "ok"
    ERROR = "error"


@dataclass
class SpanContext:
    """Span context for trace propagation."""
    trace_id: str
    span_id: str
    parent_span_id: Optional[str] = None
    trace_flags: int = 1  # Sampled
    trace_state: str = ""

    def to_traceparent(self) -> str:
        """Convert to W3C traceparent header."""
        return f"00-{self.trace_id}-{self.span_id}-{self.trace_flags:02x}"

    @classmethod
    def from_traceparent(cls, traceparent: str) -> Optional['SpanContext']:
        """Parse W3C traceparent header."""
        try:
            parts = traceparent.split('-')
            if len(parts) != 4 or parts[0] != '00':
                return None

            return cls(
                trace_id=parts[1],
                span_id=parts[2],
                trace_flags=int(parts[3], 16)
            )
        except Exception:
            return None


@dataclass
class Span:
    """A single span in a trace."""
    span_id: str
    trace_id: str
    parent_span_id: Optional[str]
    name: str
    kind: SpanKind
    start_time: datetime
    end_time: Optional[datetime] = None
    status: SpanStatus = SpanStatus.UNSET
    status_message: Optional[str] = None
    attributes: Dict[str, Any] = field(default_factory=dict)
    events: List[Dict[str, Any]] = field(default_factory=list)
    links: List[SpanContext] = field(default_factory=list)

    def set_attribute(self, key: str, value: Any):
        """Set span attribute."""
        self.attributes[key] = value

    def add_event(self, name: str, attributes: Optional[Dict[str, Any]] = None):
        """Add span event."""
        self.events.append({
            "name": name,
            "timestamp": datetime.utcnow(),
            "attributes": attributes or {}
        })

    def set_status(self, status: SpanStatus, message: Optional[str] = None):
        """Set span status."""
        self.status = status
        self.status_message = message

    def end(self):
        """End the span."""
        if self.end_time is None:
            self.end_time = datetime.utcnow()

    def duration_ms(self) -> float:
        """Get span duration in milliseconds."""
        if self.end_time is None:
            return 0.0

        delta = self.end_time - self.start_time
        return delta.total_seconds() * 1000

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "span_id": self.span_id,
            "trace_id": self.trace_id,
            "parent_span_id": self.parent_span_id,
            "name": self.name,
            "kind": self.kind.value,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_ms": self.duration_ms(),
            "status": self.status.value,
            "status_message": self.status_message,
            "attributes": self.attributes,
            "events": self.events,
            "links": [link.to_traceparent() for link in self.links]
        }


class Tracer:
    """
    Tracer for creating and managing spans.

    Compatible with OpenTelemetry semantics.
    """

    def __init__(self, name: str = "tsm"):
        """
        Initialize tracer.

        Args:
            name: Tracer name
        """
        self.name = name
        self.active_spans: Dict[str, Span] = {}
        self.completed_spans: List[Span] = []
        self.current_context: Optional[SpanContext] = None

        logger.info(f"Tracer initialized: {name}")

    def start_span(
        self,
        name: str,
        kind: SpanKind = SpanKind.INTERNAL,
        attributes: Optional[Dict[str, Any]] = None,
        parent_context: Optional[SpanContext] = None
    ) -> Span:
        """
        Start a new span.

        Args:
            name: Span name
            kind: Span kind
            attributes: Initial attributes
            parent_context: Parent span context

        Returns:
            New span
        """
        # Generate IDs
        span_id = uuid.uuid4().hex[:16]

        if parent_context:
            trace_id = parent_context.trace_id
            parent_span_id = parent_context.span_id
        elif self.current_context:
            trace_id = self.current_context.trace_id
            parent_span_id = self.current_context.span_id
        else:
            trace_id = uuid.uuid4().hex
            parent_span_id = None

        # Create span
        span = Span(
            span_id=span_id,
            trace_id=trace_id,
            parent_span_id=parent_span_id,
            name=name,
            kind=kind,
            start_time=datetime.utcnow(),
            attributes=attributes or {}
        )

        # Store active span
        self.active_spans[span_id] = span

        logger.debug(f"Started span: {name} (trace_id={trace_id[:8]})")

        return span

    def end_span(self, span: Span):
        """
        End a span.

        Args:
            span: Span to end
        """
        span.end()

        # Move to completed
        if span.span_id in self.active_spans:
            del self.active_spans[span.span_id]

        self.completed_spans.append(span)

        logger.debug(
            f"Ended span: {span.name} ({span.duration_ms():.1f}ms)"
        )

    @contextmanager
    def trace(
        self,
        name: str,
        kind: SpanKind = SpanKind.INTERNAL,
        attributes: Optional[Dict[str, Any]] = None
    ):
        """
        Context manager for tracing.

        Args:
            name: Span name
            kind: Span kind
            attributes: Initial attributes

        Yields:
            Span
        """
        span = self.start_span(name, kind, attributes)

        # Set current context
        old_context = self.current_context
        self.current_context = SpanContext(
            trace_id=span.trace_id,
            span_id=span.span_id,
            parent_span_id=span.parent_span_id
        )

        try:
            yield span
            span.set_status(SpanStatus.OK)
        except Exception as e:
            span.set_status(SpanStatus.ERROR, str(e))
            span.add_event("exception", {
                "exception.type": type(e).__name__,
                "exception.message": str(e)
            })
            raise
        finally:
            self.end_span(span)
            self.current_context = old_context

    def get_current_context(self) -> Optional[SpanContext]:
        """Get current span context."""
        return self.current_context

    def set_current_context(self, context: Optional[SpanContext]):
        """Set current span context."""
        self.current_context = context

    def get_completed_spans(
        self,
        trace_id: Optional[str] = None
    ) -> List[Span]:
        """
        Get completed spans.

        Args:
            trace_id: Filter by trace ID

        Returns:
            List of spans
        """
        if trace_id:
            return [
                s for s in self.completed_spans
                if s.trace_id == trace_id
            ]
        return self.completed_spans.copy()

    def clear_completed_spans(self):
        """Clear completed spans."""
        count = len(self.completed_spans)
        self.completed_spans.clear()
        logger.info(f"Cleared {count} completed spans")


class TraceExporter:
    """
    Base class for trace exporters.

    Export spans to external systems (Jaeger, Zipkin, etc.)
    """

    def export(self, spans: List[Span]) -> bool:
        """
        Export spans.

        Args:
            spans: Spans to export

        Returns:
            True if successful
        """
        raise NotImplementedError


class ConsoleExporter(TraceExporter):
    """Export traces to console/logs."""

    def export(self, spans: List[Span]) -> bool:
        """Export spans to console."""
        for span in spans:
            logger.info(f"Trace span: {span.to_dict()}")
        return True


class InMemoryExporter(TraceExporter):
    """Store traces in memory for testing."""

    def __init__(self):
        """Initialize in-memory exporter."""
        self.spans: List[Span] = []

    def export(self, spans: List[Span]) -> bool:
        """Store spans in memory."""
        self.spans.extend(spans)
        return True

    def get_spans(self, trace_id: Optional[str] = None) -> List[Span]:
        """Get exported spans."""
        if trace_id:
            return [s for s in self.spans if s.trace_id == trace_id]
        return self.spans.copy()

    def clear(self):
        """Clear stored spans."""
        self.spans.clear()


class TraceProcessor:
    """
    Process and export spans.

    Batches spans and exports them periodically.
    """

    def __init__(
        self,
        exporter: TraceExporter,
        batch_size: int = 10,
        max_queue_size: int = 1000
    ):
        """
        Initialize trace processor.

        Args:
            exporter: Trace exporter
            batch_size: Batch size for export
            max_queue_size: Maximum queue size
        """
        self.exporter = exporter
        self.batch_size = batch_size
        self.max_queue_size = max_queue_size
        self.queue: List[Span] = []

        logger.info(
            f"TraceProcessor initialized "
            f"(batch_size={batch_size}, max_queue_size={max_queue_size})"
        )

    def process(self, span: Span):
        """
        Process a span.

        Args:
            span: Span to process
        """
        self.queue.append(span)

        # Check if should flush
        if len(self.queue) >= self.batch_size:
            self.flush()

    def flush(self) -> bool:
        """
        Flush queued spans.

        Returns:
            True if successful
        """
        if not self.queue:
            return True

        spans_to_export = self.queue[:self.batch_size]
        success = self.exporter.export(spans_to_export)

        if success:
            # Remove exported spans
            self.queue = self.queue[self.batch_size:]
            logger.debug(f"Exported {len(spans_to_export)} spans")
        else:
            logger.error("Failed to export spans")

        return success

    def get_queue_size(self) -> int:
        """Get current queue size."""
        return len(self.queue)


class TracingMiddleware:
    """
    HTTP middleware for automatic request tracing.

    Extracts trace context from headers and creates spans.
    """

    def __init__(self, tracer: Tracer):
        """
        Initialize middleware.

        Args:
            tracer: Tracer instance
        """
        self.tracer = tracer

    async def __call__(self, request: Dict[str, Any], call_next: Callable):
        """
        Process request with tracing.

        Args:
            request: Request dict
            call_next: Next handler

        Returns:
            Response
        """
        # Extract trace context from headers
        headers = request.get("headers", {})
        traceparent = headers.get("traceparent")

        parent_context = None
        if traceparent:
            parent_context = SpanContext.from_traceparent(traceparent)

        # Start span
        with self.tracer.trace(
            name=f"{request.get('method', 'GET')} {request.get('path', '/')}",
            kind=SpanKind.SERVER,
            attributes={
                "http.method": request.get("method"),
                "http.path": request.get("path"),
                "http.user_agent": headers.get("user-agent"),
            }
        ) as span:
            # Set parent if available
            if parent_context:
                span.parent_span_id = parent_context.span_id

            # Process request
            start_time = time.time()
            response = await call_next(request)
            duration_ms = (time.time() - start_time) * 1000

            # Add response attributes
            span.set_attribute("http.status_code", response.get("status_code", 200))
            span.set_attribute("http.response_time_ms", duration_ms)

            # Set status based on response
            status_code = response.get("status_code", 200)
            if status_code >= 500:
                span.set_status(SpanStatus.ERROR, f"HTTP {status_code}")
            elif status_code >= 400:
                span.set_status(SpanStatus.ERROR, f"HTTP {status_code}")
            else:
                span.set_status(SpanStatus.OK)

            return response


# Semantic conventions for common attributes
class SemanticAttributes:
    """Common attribute keys following OpenTelemetry conventions."""

    # HTTP
    HTTP_METHOD = "http.method"
    HTTP_URL = "http.url"
    HTTP_STATUS_CODE = "http.status_code"
    HTTP_USER_AGENT = "http.user_agent"

    # Database
    DB_SYSTEM = "db.system"
    DB_STATEMENT = "db.statement"
    DB_NAME = "db.name"

    # Messaging
    MESSAGING_SYSTEM = "messaging.system"
    MESSAGING_DESTINATION = "messaging.destination"

    # Model
    MODEL_NAME = "model.name"
    MODEL_PROVIDER = "model.provider"
    MODEL_TOKENS = "model.tokens"
    MODEL_COST = "model.cost"

    # Cache
    CACHE_HIT = "cache.hit"
    CACHE_KEY = "cache.key"

    # Error
    ERROR_TYPE = "error.type"
    ERROR_MESSAGE = "error.message"
    ERROR_STACK = "error.stack"


# Global tracer instance
tracer = Tracer("tsm")

# Global exporter
exporter = InMemoryExporter()

# Global processor
processor = TraceProcessor(exporter, batch_size=10)
