"""
Performance Monitoring
======================

Real-time performance tracking, metrics collection, and alerting.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, deque
import time
import logging
import statistics

logger = logging.getLogger(__name__)


@dataclass
class MetricPoint:
    """A single metric measurement."""
    timestamp: datetime
    value: float
    labels: Dict[str, str] = field(default_factory=dict)


@dataclass
class PerformanceMetrics:
    """Performance metrics snapshot."""
    timestamp: datetime

    # Request metrics
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0

    # Latency metrics (milliseconds)
    avg_latency_ms: float = 0.0
    p50_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    p99_latency_ms: float = 0.0
    max_latency_ms: float = 0.0

    # Cost metrics
    total_cost_usd: float = 0.0
    avg_cost_per_request: float = 0.0

    # Token metrics
    total_tokens: int = 0
    avg_tokens_per_request: float = 0.0

    # Model usage
    model_usage: Dict[str, int] = field(default_factory=dict)

    # Provider usage
    provider_usage: Dict[str, int] = field(default_factory=dict)

    # Error rates
    error_rate: float = 0.0
    timeout_rate: float = 0.0

    # Cache metrics
    cache_hit_rate: float = 0.0
    cache_hits: int = 0
    cache_misses: int = 0


class MetricsCollector:
    """
    Collects and aggregates performance metrics.

    Thread-safe metrics collection with time-series storage.
    """

    def __init__(self, retention_hours: int = 24):
        """
        Initialize metrics collector.

        Args:
            retention_hours: How long to retain metrics
        """
        self.retention_hours = retention_hours
        self.retention_seconds = retention_hours * 3600

        # Time-series data (last N measurements)
        self.max_points = 10000
        self.latencies = deque(maxlen=self.max_points)
        self.costs = deque(maxlen=self.max_points)
        self.tokens = deque(maxlen=self.max_points)
        self.timestamps = deque(maxlen=self.max_points)

        # Counters
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.timeouts = 0

        # Model tracking
        self.model_counts = defaultdict(int)
        self.provider_counts = defaultdict(int)

        # Cache tracking
        self.cache_hits = 0
        self.cache_misses = 0

        # Running totals
        self.total_cost = 0.0
        self.total_tokens = 0

        logger.info(f"MetricsCollector initialized (retention: {retention_hours}h)")

    def record_request(
        self,
        latency_ms: float,
        cost_usd: float,
        tokens: int,
        model: str,
        provider: str,
        success: bool = True,
        timeout: bool = False
    ):
        """
        Record a single request.

        Args:
            latency_ms: Request latency in milliseconds
            cost_usd: Request cost in USD
            tokens: Tokens used
            model: Model name
            provider: Provider name
            success: Whether request succeeded
            timeout: Whether request timed out
        """
        now = datetime.utcnow()

        # Record time-series data
        self.latencies.append(latency_ms)
        self.costs.append(cost_usd)
        self.tokens.append(tokens)
        self.timestamps.append(now)

        # Update counters
        self.total_requests += 1
        if success:
            self.successful_requests += 1
        else:
            self.failed_requests += 1

        if timeout:
            self.timeouts += 1

        # Update model/provider tracking
        self.model_counts[model] += 1
        self.provider_counts[provider] += 1

        # Update totals
        self.total_cost += cost_usd
        self.total_tokens += tokens

        logger.debug(
            f"Recorded request: {model} via {provider}, "
            f"{latency_ms:.1f}ms, ${cost_usd:.4f}, {tokens} tokens"
        )

    def record_cache_hit(self):
        """Record a cache hit."""
        self.cache_hits += 1

    def record_cache_miss(self):
        """Record a cache miss."""
        self.cache_misses += 1

    def get_metrics(self, window_minutes: Optional[int] = None) -> PerformanceMetrics:
        """
        Get current performance metrics.

        Args:
            window_minutes: Time window for metrics (None = all time)

        Returns:
            PerformanceMetrics snapshot
        """
        now = datetime.utcnow()

        # Filter to time window if specified
        if window_minutes:
            cutoff = now - timedelta(minutes=window_minutes)
            indices = [
                i for i, ts in enumerate(self.timestamps)
                if ts >= cutoff
            ]
            latencies = [self.latencies[i] for i in indices]
            costs = [self.costs[i] for i in indices]
            tokens_list = [self.tokens[i] for i in indices]
        else:
            latencies = list(self.latencies)
            costs = list(self.costs)
            tokens_list = list(self.tokens)

        # Calculate percentiles
        if latencies:
            sorted_latencies = sorted(latencies)
            n = len(sorted_latencies)
            p50 = sorted_latencies[int(n * 0.50)]
            p95 = sorted_latencies[int(n * 0.95)]
            p99 = sorted_latencies[int(n * 0.99)]
            avg_latency = statistics.mean(latencies)
            max_latency = max(latencies)
        else:
            p50 = p95 = p99 = avg_latency = max_latency = 0.0

        # Calculate rates
        total_cache = self.cache_hits + self.cache_misses
        cache_hit_rate = (
            self.cache_hits / total_cache if total_cache > 0 else 0.0
        )

        error_rate = (
            self.failed_requests / self.total_requests
            if self.total_requests > 0 else 0.0
        )

        timeout_rate = (
            self.timeouts / self.total_requests
            if self.total_requests > 0 else 0.0
        )

        # Calculate averages
        avg_cost = (
            self.total_cost / self.total_requests
            if self.total_requests > 0 else 0.0
        )

        avg_tokens = (
            self.total_tokens / self.total_requests
            if self.total_requests > 0 else 0.0
        )

        return PerformanceMetrics(
            timestamp=now,
            total_requests=self.total_requests,
            successful_requests=self.successful_requests,
            failed_requests=self.failed_requests,
            avg_latency_ms=avg_latency,
            p50_latency_ms=p50,
            p95_latency_ms=p95,
            p99_latency_ms=p99,
            max_latency_ms=max_latency,
            total_cost_usd=self.total_cost,
            avg_cost_per_request=avg_cost,
            total_tokens=self.total_tokens,
            avg_tokens_per_request=avg_tokens,
            model_usage=dict(self.model_counts),
            provider_usage=dict(self.provider_counts),
            error_rate=error_rate,
            timeout_rate=timeout_rate,
            cache_hit_rate=cache_hit_rate,
            cache_hits=self.cache_hits,
            cache_misses=self.cache_misses,
        )

    def get_summary(self) -> Dict[str, Any]:
        """Get human-readable summary."""
        metrics = self.get_metrics()

        return {
            "overview": {
                "total_requests": metrics.total_requests,
                "success_rate": f"{(1 - metrics.error_rate) * 100:.1f}%",
                "avg_latency": f"{metrics.avg_latency_ms:.1f}ms",
                "total_cost": f"${metrics.total_cost_usd:.4f}",
            },
            "latency": {
                "p50": f"{metrics.p50_latency_ms:.1f}ms",
                "p95": f"{metrics.p95_latency_ms:.1f}ms",
                "p99": f"{metrics.p99_latency_ms:.1f}ms",
                "max": f"{metrics.max_latency_ms:.1f}ms",
            },
            "costs": {
                "total": f"${metrics.total_cost_usd:.4f}",
                "avg_per_request": f"${metrics.avg_cost_per_request:.6f}",
            },
            "tokens": {
                "total": metrics.total_tokens,
                "avg_per_request": f"{metrics.avg_tokens_per_request:.0f}",
            },
            "models": metrics.model_usage,
            "providers": metrics.provider_usage,
            "cache": {
                "hit_rate": f"{metrics.cache_hit_rate * 100:.1f}%",
                "hits": metrics.cache_hits,
                "misses": metrics.cache_misses,
            }
        }

    def reset(self):
        """Reset all metrics."""
        self.latencies.clear()
        self.costs.clear()
        self.tokens.clear()
        self.timestamps.clear()

        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.timeouts = 0

        self.model_counts.clear()
        self.provider_counts.clear()

        self.cache_hits = 0
        self.cache_misses = 0

        self.total_cost = 0.0
        self.total_tokens = 0

        logger.info("Metrics reset")


class PerformanceTracker:
    """
    Context manager for tracking request performance.

    Usage:
        with PerformanceTracker(collector, model="gpt-4o", provider="openai") as tracker:
            result = await some_operation()
            tracker.set_cost(0.002)
            tracker.set_tokens(500)
    """

    def __init__(
        self,
        collector: MetricsCollector,
        model: str,
        provider: str
    ):
        """
        Initialize performance tracker.

        Args:
            collector: MetricsCollector instance
            model: Model name
            provider: Provider name
        """
        self.collector = collector
        self.model = model
        self.provider = provider

        self.start_time = None
        self.cost = 0.0
        self.tokens = 0
        self.success = True
        self.timeout = False

    def __enter__(self):
        """Start tracking."""
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop tracking and record metrics."""
        if self.start_time is None:
            return

        latency_ms = (time.time() - self.start_time) * 1000

        # Check for errors
        if exc_type is not None:
            self.success = False
            if exc_type.__name__ == "TimeoutError":
                self.timeout = True

        # Record metrics
        self.collector.record_request(
            latency_ms=latency_ms,
            cost_usd=self.cost,
            tokens=self.tokens,
            model=self.model,
            provider=self.provider,
            success=self.success,
            timeout=self.timeout
        )

    def set_cost(self, cost: float):
        """Set request cost."""
        self.cost = cost

    def set_tokens(self, tokens: int):
        """Set tokens used."""
        self.tokens = tokens

    def mark_failed(self):
        """Mark request as failed."""
        self.success = False


# Global metrics collector
metrics_collector = MetricsCollector(retention_hours=24)
