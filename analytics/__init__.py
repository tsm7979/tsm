"""
Analytics & Reporting
======================

Advanced analytics, aggregations, and reporting for TSM platform.
"""

from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict
from enum import Enum
import statistics
import logging

logger = logging.getLogger(__name__)


class TimeRange(str, Enum):
    """Predefined time ranges."""
    LAST_HOUR = "last_hour"
    LAST_24_HOURS = "last_24_hours"
    LAST_7_DAYS = "last_7_days"
    LAST_30_DAYS = "last_30_days"
    LAST_90_DAYS = "last_90_days"


class AggregationType(str, Enum):
    """Aggregation types."""
    SUM = "sum"
    AVG = "avg"
    MIN = "min"
    MAX = "max"
    COUNT = "count"
    P50 = "p50"
    P95 = "p95"
    P99 = "p99"


@dataclass
class MetricPoint:
    """A single metric data point."""
    timestamp: datetime
    value: float
    labels: Dict[str, str] = field(default_factory=dict)


@dataclass
class TimeSeriesData:
    """Time series data."""
    metric_name: str
    data_points: List[MetricPoint]
    aggregation: Optional[AggregationType] = None

    def get_values(self) -> List[float]:
        """Get all values."""
        return [p.value for p in self.data_points]

    def get_timestamps(self) -> List[datetime]:
        """Get all timestamps."""
        return [p.timestamp for p in self.data_points]

    def aggregate(self, agg_type: AggregationType) -> float:
        """Aggregate values."""
        values = self.get_values()
        if not values:
            return 0.0

        if agg_type == AggregationType.SUM:
            return sum(values)
        elif agg_type == AggregationType.AVG:
            return statistics.mean(values)
        elif agg_type == AggregationType.MIN:
            return min(values)
        elif agg_type == AggregationType.MAX:
            return max(values)
        elif agg_type == AggregationType.COUNT:
            return len(values)
        elif agg_type == AggregationType.P50:
            return statistics.median(values)
        elif agg_type == AggregationType.P95:
            sorted_vals = sorted(values)
            idx = int(len(sorted_vals) * 0.95)
            return sorted_vals[idx]
        elif agg_type == AggregationType.P99:
            sorted_vals = sorted(values)
            idx = int(len(sorted_vals) * 0.99)
            return sorted_vals[idx]

        return 0.0


@dataclass
class UsageReport:
    """Usage analytics report."""
    time_range: Tuple[datetime, datetime]
    total_requests: int
    successful_requests: int
    failed_requests: int
    total_tokens: int
    total_cost: float
    avg_latency_ms: float
    p95_latency_ms: float
    models_used: Dict[str, int]
    top_users: List[Tuple[str, int]]
    cost_by_model: Dict[str, float]
    requests_by_hour: List[Tuple[datetime, int]]


class AnalyticsEngine:
    """
    Analytics engine for aggregations and reporting.

    Provides advanced metrics, aggregations, and insights.
    """

    def __init__(self):
        """Initialize analytics engine."""
        self.metrics: Dict[str, List[MetricPoint]] = defaultdict(list)
        self.events: List[Dict[str, Any]] = []

        logger.info("AnalyticsEngine initialized")

    def record_metric(
        self,
        metric_name: str,
        value: float,
        labels: Optional[Dict[str, str]] = None
    ):
        """
        Record a metric.

        Args:
            metric_name: Metric name
            value: Metric value
            labels: Optional labels
        """
        point = MetricPoint(
            timestamp=datetime.utcnow(),
            value=value,
            labels=labels or {}
        )

        self.metrics[metric_name].append(point)

    def record_event(
        self,
        event_type: str,
        data: Dict[str, Any]
    ):
        """
        Record an event.

        Args:
            event_type: Event type
            data: Event data
        """
        event = {
            "type": event_type,
            "timestamp": datetime.utcnow(),
            "data": data
        }

        self.events.append(event)

    def get_time_series(
        self,
        metric_name: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        labels: Optional[Dict[str, str]] = None
    ) -> TimeSeriesData:
        """
        Get time series data.

        Args:
            metric_name: Metric name
            start_time: Start time
            end_time: End time
            labels: Filter by labels

        Returns:
            Time series data
        """
        if metric_name not in self.metrics:
            return TimeSeriesData(metric_name=metric_name, data_points=[])

        points = self.metrics[metric_name]

        # Filter by time
        if start_time:
            points = [p for p in points if p.timestamp >= start_time]

        if end_time:
            points = [p for p in points if p.timestamp <= end_time]

        # Filter by labels
        if labels:
            points = [
                p for p in points
                if all(p.labels.get(k) == v for k, v in labels.items())
            ]

        return TimeSeriesData(
            metric_name=metric_name,
            data_points=points
        )

    def aggregate_metric(
        self,
        metric_name: str,
        agg_type: AggregationType,
        time_range: Optional[TimeRange] = None,
        labels: Optional[Dict[str, str]] = None
    ) -> float:
        """
        Aggregate a metric.

        Args:
            metric_name: Metric name
            agg_type: Aggregation type
            time_range: Time range
            labels: Filter by labels

        Returns:
            Aggregated value
        """
        # Calculate time window
        start_time = None
        if time_range:
            end_time = datetime.utcnow()

            if time_range == TimeRange.LAST_HOUR:
                start_time = end_time - timedelta(hours=1)
            elif time_range == TimeRange.LAST_24_HOURS:
                start_time = end_time - timedelta(hours=24)
            elif time_range == TimeRange.LAST_7_DAYS:
                start_time = end_time - timedelta(days=7)
            elif time_range == TimeRange.LAST_30_DAYS:
                start_time = end_time - timedelta(days=30)
            elif time_range == TimeRange.LAST_90_DAYS:
                start_time = end_time - timedelta(days=90)

        # Get time series
        ts = self.get_time_series(
            metric_name,
            start_time=start_time,
            labels=labels
        )

        # Aggregate
        return ts.aggregate(agg_type)

    def group_by(
        self,
        metric_name: str,
        group_by_label: str,
        agg_type: AggregationType,
        time_range: Optional[TimeRange] = None
    ) -> Dict[str, float]:
        """
        Group metric by label and aggregate.

        Args:
            metric_name: Metric name
            group_by_label: Label to group by
            agg_type: Aggregation type
            time_range: Time range

        Returns:
            Dict of label value to aggregated metric
        """
        # Get time series
        ts = self.get_time_series(metric_name)

        # Group by label
        groups: Dict[str, List[float]] = defaultdict(list)

        for point in ts.data_points:
            label_value = point.labels.get(group_by_label, "unknown")
            groups[label_value].append(point.value)

        # Aggregate each group
        result = {}
        for label_value, values in groups.items():
            if agg_type == AggregationType.SUM:
                result[label_value] = sum(values)
            elif agg_type == AggregationType.AVG:
                result[label_value] = statistics.mean(values)
            elif agg_type == AggregationType.COUNT:
                result[label_value] = len(values)
            elif agg_type == AggregationType.MAX:
                result[label_value] = max(values)
            elif agg_type == AggregationType.MIN:
                result[label_value] = min(values)

        return result

    def get_top_n(
        self,
        metric_name: str,
        group_by_label: str,
        n: int = 10,
        time_range: Optional[TimeRange] = None
    ) -> List[Tuple[str, float]]:
        """
        Get top N by metric.

        Args:
            metric_name: Metric name
            group_by_label: Label to group by
            n: Number of results
            time_range: Time range

        Returns:
            List of (label_value, metric_value) tuples
        """
        groups = self.group_by(
            metric_name,
            group_by_label,
            AggregationType.SUM,
            time_range
        )

        # Sort by value descending
        sorted_items = sorted(
            groups.items(),
            key=lambda x: x[1],
            reverse=True
        )

        return sorted_items[:n]

    def get_usage_report(
        self,
        start_time: datetime,
        end_time: datetime
    ) -> UsageReport:
        """
        Generate comprehensive usage report.

        Args:
            start_time: Report start time
            end_time: Report end time

        Returns:
            Usage report
        """
        # Get request metrics
        request_ts = self.get_time_series(
            "requests",
            start_time=start_time,
            end_time=end_time
        )

        total_requests = len(request_ts.data_points)

        # Get success/failure counts
        success_ts = self.get_time_series(
            "requests",
            start_time=start_time,
            end_time=end_time,
            labels={"status": "success"}
        )

        successful_requests = len(success_ts.data_points)
        failed_requests = total_requests - successful_requests

        # Get token usage
        tokens_ts = self.get_time_series(
            "tokens",
            start_time=start_time,
            end_time=end_time
        )
        total_tokens = int(tokens_ts.aggregate(AggregationType.SUM))

        # Get cost
        cost_ts = self.get_time_series(
            "cost",
            start_time=start_time,
            end_time=end_time
        )
        total_cost = cost_ts.aggregate(AggregationType.SUM)

        # Get latency stats
        latency_ts = self.get_time_series(
            "latency_ms",
            start_time=start_time,
            end_time=end_time
        )

        avg_latency_ms = latency_ts.aggregate(AggregationType.AVG)
        p95_latency_ms = latency_ts.aggregate(AggregationType.P95)

        # Get model usage
        models_used = self.group_by(
            "requests",
            "model",
            AggregationType.COUNT,
            None
        )

        # Get top users
        top_users = self.get_top_n(
            "requests",
            "user_id",
            n=10
        )

        # Get cost by model
        cost_by_model = self.group_by(
            "cost",
            "model",
            AggregationType.SUM
        )

        # Get requests by hour
        requests_by_hour = self._group_by_hour(
            request_ts,
            start_time,
            end_time
        )

        return UsageReport(
            time_range=(start_time, end_time),
            total_requests=total_requests,
            successful_requests=successful_requests,
            failed_requests=failed_requests,
            total_tokens=total_tokens,
            total_cost=total_cost,
            avg_latency_ms=avg_latency_ms,
            p95_latency_ms=p95_latency_ms,
            models_used=models_used,
            top_users=top_users,
            cost_by_model=cost_by_model,
            requests_by_hour=requests_by_hour
        )

    def _group_by_hour(
        self,
        ts: TimeSeriesData,
        start_time: datetime,
        end_time: datetime
    ) -> List[Tuple[datetime, int]]:
        """Group time series by hour."""
        # Create hourly buckets
        buckets: Dict[datetime, int] = {}

        current = start_time.replace(minute=0, second=0, microsecond=0)
        while current <= end_time:
            buckets[current] = 0
            current += timedelta(hours=1)

        # Count points in each bucket
        for point in ts.data_points:
            hour = point.timestamp.replace(minute=0, second=0, microsecond=0)
            if hour in buckets:
                buckets[hour] += 1

        # Convert to sorted list
        return sorted(buckets.items())

    def export_report(
        self,
        report: UsageReport,
        format: str = "text"
    ) -> str:
        """
        Export report to string.

        Args:
            report: Usage report
            format: Output format (text, json, markdown)

        Returns:
            Formatted report
        """
        if format == "text":
            return self._export_text(report)
        elif format == "json":
            import json
            return json.dumps(self._report_to_dict(report), indent=2)
        elif format == "markdown":
            return self._export_markdown(report)

        return ""

    def _export_text(self, report: UsageReport) -> str:
        """Export report as text."""
        lines = []

        lines.append("=" * 60)
        lines.append("USAGE REPORT")
        lines.append("=" * 60)

        # Time range
        start, end = report.time_range
        lines.append(f"\nTime Range: {start} to {end}")

        # Request stats
        lines.append("\nRequest Statistics:")
        lines.append(f"  Total Requests:      {report.total_requests:,}")
        lines.append(f"  Successful:          {report.successful_requests:,}")
        lines.append(f"  Failed:              {report.failed_requests:,}")

        success_rate = (
            (report.successful_requests / report.total_requests * 100)
            if report.total_requests > 0 else 0
        )
        lines.append(f"  Success Rate:        {success_rate:.1f}%")

        # Performance stats
        lines.append("\nPerformance:")
        lines.append(f"  Avg Latency:         {report.avg_latency_ms:.1f}ms")
        lines.append(f"  P95 Latency:         {report.p95_latency_ms:.1f}ms")

        # Resource usage
        lines.append("\nResource Usage:")
        lines.append(f"  Total Tokens:        {report.total_tokens:,}")
        lines.append(f"  Total Cost:          ${report.total_cost:.4f}")

        avg_cost_per_req = (
            report.total_cost / report.total_requests
            if report.total_requests > 0 else 0
        )
        lines.append(f"  Avg Cost/Request:    ${avg_cost_per_req:.6f}")

        # Models used
        lines.append("\nModels Used:")
        for model, count in sorted(
            report.models_used.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]:
            lines.append(f"  {model:20s} {count:,} requests")

        # Top users
        if report.top_users:
            lines.append("\nTop Users:")
            for user_id, count in report.top_users[:5]:
                lines.append(f"  {user_id:20s} {count:,} requests")

        lines.append("\n" + "=" * 60)

        return "\n".join(lines)

    def _export_markdown(self, report: UsageReport) -> str:
        """Export report as markdown."""
        lines = []

        lines.append("# Usage Report")
        lines.append("")

        # Time range
        start, end = report.time_range
        lines.append(f"**Time Range**: {start} to {end}")
        lines.append("")

        # Request stats
        lines.append("## Request Statistics")
        lines.append("")
        lines.append(f"- Total Requests: **{report.total_requests:,}**")
        lines.append(f"- Successful: **{report.successful_requests:,}**")
        lines.append(f"- Failed: **{report.failed_requests:,}**")

        success_rate = (
            (report.successful_requests / report.total_requests * 100)
            if report.total_requests > 0 else 0
        )
        lines.append(f"- Success Rate: **{success_rate:.1f}%**")
        lines.append("")

        # Performance
        lines.append("## Performance")
        lines.append("")
        lines.append(f"- Avg Latency: **{report.avg_latency_ms:.1f}ms**")
        lines.append(f"- P95 Latency: **{report.p95_latency_ms:.1f}ms**")
        lines.append("")

        # Cost
        lines.append("## Cost")
        lines.append("")
        lines.append(f"- Total Tokens: **{report.total_tokens:,}**")
        lines.append(f"- Total Cost: **${report.total_cost:.4f}**")
        lines.append("")

        # Models table
        lines.append("## Models Used")
        lines.append("")
        lines.append("| Model | Requests | Cost |")
        lines.append("|-------|----------|------|")

        for model in sorted(
            report.models_used.keys(),
            key=lambda m: report.models_used[m],
            reverse=True
        )[:10]:
            count = report.models_used[model]
            cost = report.cost_by_model.get(model, 0.0)
            lines.append(f"| {model} | {count:,} | ${cost:.4f} |")

        return "\n".join(lines)

    def _report_to_dict(self, report: UsageReport) -> Dict[str, Any]:
        """Convert report to dictionary."""
        start, end = report.time_range

        return {
            "time_range": {
                "start": start.isoformat(),
                "end": end.isoformat()
            },
            "requests": {
                "total": report.total_requests,
                "successful": report.successful_requests,
                "failed": report.failed_requests
            },
            "performance": {
                "avg_latency_ms": report.avg_latency_ms,
                "p95_latency_ms": report.p95_latency_ms
            },
            "resources": {
                "total_tokens": report.total_tokens,
                "total_cost": report.total_cost
            },
            "models_used": report.models_used,
            "top_users": [
                {"user_id": uid, "requests": count}
                for uid, count in report.top_users
            ],
            "cost_by_model": report.cost_by_model
        }


# Global analytics engine
analytics = AnalyticsEngine()
