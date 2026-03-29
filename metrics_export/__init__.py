"""
TSM Metrics Export
==================

Export metrics to external monitoring systems:
- Prometheus (pull-based)
- StatsD (push-based)
- CloudWatch (AWS)
- Datadog
- Custom HTTP endpoints

Features:
- Multiple export formats
- Configurable intervals
- Metric aggregation
- Label/tag support
"""

from enum import Enum
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from datetime import datetime
import asyncio
import time
import logging
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class MetricType(str, Enum):
    """Metric types."""

    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


class ExportFormat(str, Enum):
    """Export formats."""

    PROMETHEUS = "prometheus"
    STATSD = "statsd"
    JSON = "json"
    INFLUXDB = "influxdb"
    CLOUDWATCH = "cloudwatch"


@dataclass
class MetricValue:
    """A metric value with timestamp."""

    value: float
    timestamp: datetime = field(default_factory=datetime.utcnow)
    labels: Dict[str, str] = field(default_factory=dict)


@dataclass
class Metric:
    """
    A metric to be exported.

    Supports counters, gauges, histograms, and summaries.
    """

    name: str
    type: MetricType
    description: str = ""
    unit: str = ""

    # Current value(s)
    value: float = 0.0
    values: List[float] = field(default_factory=list)  # For histograms/summaries

    # Labels (tags)
    labels: Dict[str, str] = field(default_factory=dict)

    # Timestamp
    timestamp: datetime = field(default_factory=datetime.utcnow)

    # Histogram buckets
    buckets: List[float] = field(default_factory=lambda: [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0])
    bucket_counts: Dict[float, int] = field(default_factory=dict)

    # Summary quantiles
    quantiles: List[float] = field(default_factory=lambda: [0.5, 0.9, 0.95, 0.99])

    def __post_init__(self):
        if self.type == MetricType.HISTOGRAM and not self.bucket_counts:
            self.bucket_counts = {bucket: 0 for bucket in self.buckets}

    def increment(self, amount: float = 1.0, labels: Optional[Dict[str, str]] = None):
        """Increment counter."""
        if self.type != MetricType.COUNTER:
            raise ValueError(f"Cannot increment {self.type} metric")

        self.value += amount
        self.timestamp = datetime.utcnow()

        if labels:
            self.labels.update(labels)

    def set(self, value: float, labels: Optional[Dict[str, str]] = None):
        """Set gauge value."""
        if self.type != MetricType.GAUGE:
            raise ValueError(f"Cannot set {self.type} metric")

        self.value = value
        self.timestamp = datetime.utcnow()

        if labels:
            self.labels.update(labels)

    def observe(self, value: float, labels: Optional[Dict[str, str]] = None):
        """Observe value for histogram/summary."""
        if self.type not in [MetricType.HISTOGRAM, MetricType.SUMMARY]:
            raise ValueError(f"Cannot observe {self.type} metric")

        self.values.append(value)
        self.timestamp = datetime.utcnow()

        if labels:
            self.labels.update(labels)

        # Update histogram buckets
        if self.type == MetricType.HISTOGRAM:
            for bucket in self.buckets:
                if value <= bucket:
                    self.bucket_counts[bucket] += 1

    def get_quantile(self, quantile: float) -> float:
        """Calculate quantile from observed values."""
        if not self.values:
            return 0.0

        sorted_values = sorted(self.values)
        index = int(len(sorted_values) * quantile)
        return sorted_values[min(index, len(sorted_values) - 1)]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = {
            "name": self.name,
            "type": self.type.value,
            "description": self.description,
            "unit": self.unit,
            "value": self.value,
            "labels": self.labels,
            "timestamp": self.timestamp.isoformat(),
        }

        if self.type == MetricType.HISTOGRAM:
            data["buckets"] = {str(k): v for k, v in self.bucket_counts.items()}
            data["count"] = len(self.values)
            data["sum"] = sum(self.values)

        elif self.type == MetricType.SUMMARY:
            data["quantiles"] = {str(q): self.get_quantile(q) for q in self.quantiles}
            data["count"] = len(self.values)
            data["sum"] = sum(self.values)

        return data


class MetricExporter(ABC):
    """Base class for metric exporters."""

    @abstractmethod
    async def export(self, metrics: List[Metric]):
        """Export metrics."""
        pass


class PrometheusExporter(MetricExporter):
    """
    Export metrics in Prometheus format.

    Prometheus exposition format:
    # HELP metric_name Description
    # TYPE metric_name counter
    metric_name{label="value"} 42.0 1234567890000
    """

    def __init__(self):
        self._metrics_text = ""

    async def export(self, metrics: List[Metric]):
        """Export to Prometheus format."""
        lines = []

        for metric in metrics:
            # HELP line
            if metric.description:
                lines.append(f"# HELP {metric.name} {metric.description}")

            # TYPE line
            lines.append(f"# TYPE {metric.name} {metric.type.value}")

            # Metric lines
            if metric.type == MetricType.HISTOGRAM:
                # Histogram buckets
                for bucket, count in sorted(metric.bucket_counts.items()):
                    labels = self._format_labels({**metric.labels, "le": str(bucket)})
                    lines.append(f"{metric.name}_bucket{labels} {count}")

                # Count and sum
                labels = self._format_labels(metric.labels)
                lines.append(f"{metric.name}_count{labels} {len(metric.values)}")
                lines.append(f"{metric.name}_sum{labels} {sum(metric.values)}")

            elif metric.type == MetricType.SUMMARY:
                # Quantiles
                for quantile in metric.quantiles:
                    value = metric.get_quantile(quantile)
                    labels = self._format_labels({**metric.labels, "quantile": str(quantile)})
                    lines.append(f"{metric.name}{labels} {value}")

                # Count and sum
                labels = self._format_labels(metric.labels)
                lines.append(f"{metric.name}_count{labels} {len(metric.values)}")
                lines.append(f"{metric.name}_sum{labels} {sum(metric.values)}")

            else:
                # Counter or Gauge
                labels = self._format_labels(metric.labels)
                timestamp_ms = int(metric.timestamp.timestamp() * 1000)
                lines.append(f"{metric.name}{labels} {metric.value} {timestamp_ms}")

        self._metrics_text = "\n".join(lines) + "\n"

    def _format_labels(self, labels: Dict[str, str]) -> str:
        """Format labels for Prometheus."""
        if not labels:
            return ""

        label_parts = [f'{k}="{v}"' for k, v in labels.items()]
        return "{" + ",".join(label_parts) + "}"

    def get_metrics_text(self) -> str:
        """Get the formatted metrics text."""
        return self._metrics_text


class StatsDExporter(MetricExporter):
    """
    Export metrics in StatsD format.

    StatsD format:
    metric.name:value|type|@sample_rate|#tag1:value1,tag2:value2
    """

    def __init__(self, host: str = "localhost", port: int = 8125):
        self.host = host
        self.port = port
        self._messages: List[str] = []

    async def export(self, metrics: List[Metric]):
        """Export to StatsD format."""
        self._messages = []

        for metric in metrics:
            tags = self._format_tags(metric.labels)

            if metric.type == MetricType.COUNTER:
                self._messages.append(f"{metric.name}:{metric.value}|c{tags}")

            elif metric.type == MetricType.GAUGE:
                self._messages.append(f"{metric.name}:{metric.value}|g{tags}")

            elif metric.type == MetricType.HISTOGRAM:
                # Send each observation
                for value in metric.values:
                    self._messages.append(f"{metric.name}:{value}|h{tags}")

            elif metric.type == MetricType.SUMMARY:
                # Send as timer (similar to histogram)
                for value in metric.values:
                    self._messages.append(f"{metric.name}:{value}|ms{tags}")

    def _format_tags(self, labels: Dict[str, str]) -> str:
        """Format tags for StatsD."""
        if not labels:
            return ""

        tag_parts = [f"{k}:{v}" for k, v in labels.items()]
        return "|#" + ",".join(tag_parts)

    def get_messages(self) -> List[str]:
        """Get the formatted messages."""
        return self._messages


class JSONExporter(MetricExporter):
    """Export metrics as JSON."""

    def __init__(self):
        self._data: List[Dict[str, Any]] = []

    async def export(self, metrics: List[Metric]):
        """Export to JSON format."""
        self._data = [metric.to_dict() for metric in metrics]

    def get_data(self) -> List[Dict[str, Any]]:
        """Get the JSON data."""
        return self._data


class InfluxDBExporter(MetricExporter):
    """
    Export metrics in InfluxDB line protocol.

    Format:
    measurement,tag1=value1,tag2=value2 field1=value1,field2=value2 timestamp
    """

    def __init__(self, database: str = "tsm"):
        self.database = database
        self._lines: List[str] = []

    async def export(self, metrics: List[Metric]):
        """Export to InfluxDB format."""
        self._lines = []

        for metric in metrics:
            tags = self._format_tags(metric.labels)
            timestamp_ns = int(metric.timestamp.timestamp() * 1_000_000_000)

            if metric.type in [MetricType.COUNTER, MetricType.GAUGE]:
                self._lines.append(f"{metric.name}{tags} value={metric.value} {timestamp_ns}")

            elif metric.type == MetricType.HISTOGRAM:
                # Export bucket counts
                for bucket, count in metric.bucket_counts.items():
                    bucket_tags = tags + f",le={bucket}"
                    self._lines.append(f"{metric.name}_bucket{bucket_tags} count={count} {timestamp_ns}")

                # Export count and sum
                self._lines.append(f"{metric.name}{tags} count={len(metric.values)},sum={sum(metric.values)} {timestamp_ns}")

            elif metric.type == MetricType.SUMMARY:
                # Export quantiles
                for quantile in metric.quantiles:
                    value = metric.get_quantile(quantile)
                    quantile_tags = tags + f",quantile={quantile}"
                    self._lines.append(f"{metric.name}{quantile_tags} value={value} {timestamp_ns}")

                # Export count and sum
                self._lines.append(f"{metric.name}{tags} count={len(metric.values)},sum={sum(metric.values)} {timestamp_ns}")

    def _format_tags(self, labels: Dict[str, str]) -> str:
        """Format tags for InfluxDB."""
        if not labels:
            return ""

        tag_parts = [f"{k}={v}" for k, v in labels.items()]
        return "," + ",".join(tag_parts)

    def get_lines(self) -> List[str]:
        """Get the formatted lines."""
        return self._lines


class MetricRegistry:
    """
    Registry for all metrics.

    Central repository for metric collection and export.
    """

    def __init__(self):
        self._metrics: Dict[str, Metric] = {}
        self._lock = asyncio.Lock()

    def register(self, metric: Metric):
        """Register a metric."""
        key = self._get_key(metric.name, metric.labels)
        self._metrics[key] = metric

    def get_metric(self, name: str, labels: Optional[Dict[str, str]] = None) -> Optional[Metric]:
        """Get a metric by name and labels."""
        key = self._get_key(name, labels or {})
        return self._metrics.get(key)

    def get_or_create(
        self,
        name: str,
        type: MetricType,
        description: str = "",
        unit: str = "",
        labels: Optional[Dict[str, str]] = None,
    ) -> Metric:
        """Get existing metric or create new one."""
        metric = self.get_metric(name, labels)
        if metric:
            return metric

        metric = Metric(
            name=name,
            type=type,
            description=description,
            unit=unit,
            labels=labels or {}
        )
        self.register(metric)
        return metric

    def get_all_metrics(self) -> List[Metric]:
        """Get all registered metrics."""
        return list(self._metrics.values())

    def clear(self):
        """Clear all metrics."""
        self._metrics.clear()

    def _get_key(self, name: str, labels: Dict[str, str]) -> str:
        """Generate unique key for metric."""
        label_parts = [f"{k}={v}" for k, v in sorted(labels.items())]
        return f"{name}:{':'.join(label_parts)}" if label_parts else name


class MetricExportService:
    """
    Service for exporting metrics to multiple backends.

    Periodically exports metrics from registry.
    """

    def __init__(
        self,
        registry: MetricRegistry,
        exporters: Optional[List[MetricExporter]] = None,
        interval_seconds: float = 60.0,
    ):
        self.registry = registry
        self.exporters = exporters or []
        self.interval_seconds = interval_seconds
        self._task: Optional[asyncio.Task] = None
        self._running = False

    def add_exporter(self, exporter: MetricExporter):
        """Add an exporter."""
        self.exporters.append(exporter)

    async def start(self):
        """Start export loop."""
        if self._running:
            return

        self._running = True
        self._task = asyncio.create_task(self._export_loop())
        logger.info(f"Started metric export service (interval={self.interval_seconds}s)")

    async def stop(self):
        """Stop export loop."""
        self._running = False

        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        logger.info("Stopped metric export service")

    async def _export_loop(self):
        """Background export loop."""
        while self._running:
            try:
                await self.export_now()
            except Exception as e:
                logger.error(f"Error exporting metrics: {str(e)}")

            await asyncio.sleep(self.interval_seconds)

    async def export_now(self):
        """Export metrics immediately."""
        metrics = self.registry.get_all_metrics()

        if not metrics:
            return

        # Export to all exporters
        for exporter in self.exporters:
            try:
                await exporter.export(metrics)
                logger.debug(f"Exported {len(metrics)} metrics to {exporter.__class__.__name__}")
            except Exception as e:
                logger.error(f"Error in {exporter.__class__.__name__}: {str(e)}")


# Global registry
_registry: Optional[MetricRegistry] = None


def get_registry() -> MetricRegistry:
    """Get global metric registry."""
    global _registry
    if _registry is None:
        _registry = MetricRegistry()
    return _registry


# Convenience functions
def counter(name: str, description: str = "", labels: Optional[Dict[str, str]] = None) -> Metric:
    """Create or get a counter metric."""
    return get_registry().get_or_create(name, MetricType.COUNTER, description, labels=labels)


def gauge(name: str, description: str = "", unit: str = "", labels: Optional[Dict[str, str]] = None) -> Metric:
    """Create or get a gauge metric."""
    return get_registry().get_or_create(name, MetricType.GAUGE, description, unit, labels=labels)


def histogram(name: str, description: str = "", unit: str = "", labels: Optional[Dict[str, str]] = None) -> Metric:
    """Create or get a histogram metric."""
    return get_registry().get_or_create(name, MetricType.HISTOGRAM, description, unit, labels=labels)


def summary(name: str, description: str = "", unit: str = "", labels: Optional[Dict[str, str]] = None) -> Metric:
    """Create or get a summary metric."""
    return get_registry().get_or_create(name, MetricType.SUMMARY, description, unit, labels=labels)


__all__ = [
    "Metric",
    "MetricType",
    "MetricValue",
    "MetricExporter",
    "PrometheusExporter",
    "StatsDExporter",
    "JSONExporter",
    "InfluxDBExporter",
    "MetricRegistry",
    "MetricExportService",
    "ExportFormat",
    "get_registry",
    "counter",
    "gauge",
    "histogram",
    "summary",
]
