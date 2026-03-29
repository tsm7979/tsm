"""
TSM Load Balancer
==================

Intelligent load balancing for distributing requests across:
- Multiple model provider instances
- Multiple workers
- Multiple regions

Features:
- Round-robin, least-connections, weighted, latency-based algorithms
- Health checking
- Sticky sessions
- Request routing based on metrics
"""

from enum import Enum
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import asyncio
import time
import logging
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class BackendStatus(str, Enum):
    """Backend health status."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class LoadBalancingAlgorithm(str, Enum):
    """Load balancing algorithms."""

    ROUND_ROBIN = "round_robin"
    LEAST_CONNECTIONS = "least_connections"
    WEIGHTED_ROUND_ROBIN = "weighted_round_robin"
    LATENCY_BASED = "latency_based"
    RANDOM = "random"
    IP_HASH = "ip_hash"


@dataclass
class BackendMetrics:
    """Performance metrics for a backend."""

    # Connection metrics
    active_connections: int = 0
    total_requests: int = 0
    total_failures: int = 0

    # Performance metrics
    avg_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    p99_latency_ms: float = 0.0

    # Recent performance (sliding window)
    recent_latencies: List[float] = field(default_factory=list)
    window_size: int = 100

    # Health metrics
    last_health_check: Optional[datetime] = None
    consecutive_failures: int = 0
    consecutive_successes: int = 0

    def record_request(self, latency_ms: float, success: bool):
        """Record a request."""
        self.total_requests += 1

        if success:
            self.consecutive_successes += 1
            self.consecutive_failures = 0

            # Update latency metrics
            self.recent_latencies.append(latency_ms)
            if len(self.recent_latencies) > self.window_size:
                self.recent_latencies.pop(0)

            # Recalculate averages
            if self.recent_latencies:
                self.avg_latency_ms = sum(self.recent_latencies) / len(self.recent_latencies)
                sorted_latencies = sorted(self.recent_latencies)
                p95_idx = int(len(sorted_latencies) * 0.95)
                p99_idx = int(len(sorted_latencies) * 0.99)
                self.p95_latency_ms = sorted_latencies[p95_idx] if p95_idx < len(sorted_latencies) else sorted_latencies[-1]
                self.p99_latency_ms = sorted_latencies[p99_idx] if p99_idx < len(sorted_latencies) else sorted_latencies[-1]
        else:
            self.total_failures += 1
            self.consecutive_failures += 1
            self.consecutive_successes = 0

    def get_success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_requests == 0:
            return 1.0
        return 1.0 - (self.total_failures / self.total_requests)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "active_connections": self.active_connections,
            "total_requests": self.total_requests,
            "total_failures": self.total_failures,
            "success_rate": self.get_success_rate(),
            "avg_latency_ms": self.avg_latency_ms,
            "p95_latency_ms": self.p95_latency_ms,
            "p99_latency_ms": self.p99_latency_ms,
            "consecutive_failures": self.consecutive_failures,
            "consecutive_successes": self.consecutive_successes,
        }


@dataclass
class HealthCheckConfig:
    """Configuration for health checks."""

    interval_seconds: float = 30.0
    timeout_seconds: float = 5.0
    unhealthy_threshold: int = 3  # Consecutive failures before marking unhealthy
    healthy_threshold: int = 2  # Consecutive successes before marking healthy


@dataclass
class Backend:
    """
    A backend server/instance that can handle requests.

    Could be:
    - A model provider instance
    - A worker process
    - A remote API endpoint
    """

    backend_id: str
    name: str
    endpoint: str  # URL or identifier
    weight: int = 1  # For weighted algorithms

    # Status
    status: BackendStatus = BackendStatus.UNKNOWN
    enabled: bool = True

    # Metrics
    metrics: BackendMetrics = field(default_factory=BackendMetrics)

    # Health check
    health_check_config: HealthCheckConfig = field(default_factory=HealthCheckConfig)
    health_check_function: Optional[Callable] = None

    # Metadata
    region: Optional[str] = None
    tags: Dict[str, str] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)

    def is_available(self) -> bool:
        """Check if backend is available for requests."""
        return self.enabled and self.status in [BackendStatus.HEALTHY, BackendStatus.DEGRADED]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "backend_id": self.backend_id,
            "name": self.name,
            "endpoint": self.endpoint,
            "weight": self.weight,
            "status": self.status.value,
            "enabled": self.enabled,
            "metrics": self.metrics.to_dict(),
            "region": self.region,
            "tags": self.tags,
        }


class LoadBalancingStrategy(ABC):
    """Base class for load balancing strategies."""

    @abstractmethod
    async def select_backend(
        self,
        backends: List[Backend],
        context: Optional[Dict[str, Any]] = None,
    ) -> Optional[Backend]:
        """Select a backend from the available pool."""
        pass


class RoundRobinStrategy(LoadBalancingStrategy):
    """Round-robin load balancing."""

    def __init__(self):
        self._index = 0
        self._lock = asyncio.Lock()

    async def select_backend(
        self,
        backends: List[Backend],
        context: Optional[Dict[str, Any]] = None,
    ) -> Optional[Backend]:
        """Select next backend in round-robin fashion."""
        available = [b for b in backends if b.is_available()]
        if not available:
            return None

        async with self._lock:
            backend = available[self._index % len(available)]
            self._index += 1
            return backend


class LeastConnectionsStrategy(LoadBalancingStrategy):
    """Least connections load balancing."""

    async def select_backend(
        self,
        backends: List[Backend],
        context: Optional[Dict[str, Any]] = None,
    ) -> Optional[Backend]:
        """Select backend with fewest active connections."""
        available = [b for b in backends if b.is_available()]
        if not available:
            return None

        return min(available, key=lambda b: b.metrics.active_connections)


class WeightedRoundRobinStrategy(LoadBalancingStrategy):
    """Weighted round-robin load balancing."""

    def __init__(self):
        self._current_weight = 0
        self._index = 0
        self._lock = asyncio.Lock()

    async def select_backend(
        self,
        backends: List[Backend],
        context: Optional[Dict[str, Any]] = None,
    ) -> Optional[Backend]:
        """Select backend based on weights."""
        available = [b for b in backends if b.is_available()]
        if not available:
            return None

        async with self._lock:
            max_weight = max(b.weight for b in available)

            while True:
                self._index = (self._index + 1) % len(available)
                if self._index == 0:
                    self._current_weight = self._current_weight - 1
                    if self._current_weight <= 0:
                        self._current_weight = max_weight

                backend = available[self._index]
                if backend.weight >= self._current_weight:
                    return backend


class LatencyBasedStrategy(LoadBalancingStrategy):
    """Latency-based load balancing (select backend with lowest latency)."""

    async def select_backend(
        self,
        backends: List[Backend],
        context: Optional[Dict[str, Any]] = None,
    ) -> Optional[Backend]:
        """Select backend with lowest average latency."""
        available = [b for b in backends if b.is_available()]
        if not available:
            return None

        # Filter backends with recent data
        with_data = [b for b in available if b.metrics.recent_latencies]
        if not with_data:
            # Fall back to round-robin if no latency data
            return available[0]

        return min(with_data, key=lambda b: b.metrics.avg_latency_ms)


class RandomStrategy(LoadBalancingStrategy):
    """Random load balancing."""

    async def select_backend(
        self,
        backends: List[Backend],
        context: Optional[Dict[str, Any]] = None,
    ) -> Optional[Backend]:
        """Select random available backend."""
        import random

        available = [b for b in backends if b.is_available()]
        if not available:
            return None

        return random.choice(available)


class IPHashStrategy(LoadBalancingStrategy):
    """IP hash load balancing (sticky sessions based on client IP)."""

    async def select_backend(
        self,
        backends: List[Backend],
        context: Optional[Dict[str, Any]] = None,
    ) -> Optional[Backend]:
        """Select backend based on client IP hash."""
        available = [b for b in backends if b.is_available()]
        if not available:
            return None

        # Get client IP from context
        client_ip = context.get("client_ip", "") if context else ""
        if not client_ip:
            # Fall back to first available
            return available[0]

        # Hash IP to backend index
        import hashlib
        hash_value = int(hashlib.md5(client_ip.encode()).hexdigest(), 16)
        index = hash_value % len(available)

        return available[index]


class LoadBalancer:
    """
    Load balancer for distributing requests across backends.

    Features:
    - Multiple load balancing algorithms
    - Health checking
    - Automatic failover
    - Metrics tracking
    """

    def __init__(
        self,
        algorithm: LoadBalancingAlgorithm = LoadBalancingAlgorithm.ROUND_ROBIN,
        enable_health_checks: bool = True,
    ):
        self.backends: Dict[str, Backend] = {}
        self.algorithm = algorithm
        self.enable_health_checks = enable_health_checks

        # Create strategy
        self.strategy = self._create_strategy(algorithm)

        # Health check task
        self._health_check_task: Optional[asyncio.Task] = None

    def _create_strategy(self, algorithm: LoadBalancingAlgorithm) -> LoadBalancingStrategy:
        """Create load balancing strategy."""
        strategies = {
            LoadBalancingAlgorithm.ROUND_ROBIN: RoundRobinStrategy(),
            LoadBalancingAlgorithm.LEAST_CONNECTIONS: LeastConnectionsStrategy(),
            LoadBalancingAlgorithm.WEIGHTED_ROUND_ROBIN: WeightedRoundRobinStrategy(),
            LoadBalancingAlgorithm.LATENCY_BASED: LatencyBasedStrategy(),
            LoadBalancingAlgorithm.RANDOM: RandomStrategy(),
            LoadBalancingAlgorithm.IP_HASH: IPHashStrategy(),
        }
        return strategies[algorithm]

    def add_backend(self, backend: Backend):
        """Add a backend to the pool."""
        self.backends[backend.backend_id] = backend
        logger.info(f"Added backend: {backend.backend_id} ({backend.name})")

    def remove_backend(self, backend_id: str) -> bool:
        """Remove a backend from the pool."""
        if backend_id in self.backends:
            del self.backends[backend_id]
            logger.info(f"Removed backend: {backend_id}")
            return True
        return False

    async def select_backend(
        self,
        context: Optional[Dict[str, Any]] = None,
    ) -> Optional[Backend]:
        """Select a backend using the configured strategy."""
        backends_list = list(self.backends.values())
        return await self.strategy.select_backend(backends_list, context)

    async def execute_request(
        self,
        func: Callable,
        *args,
        context: Optional[Dict[str, Any]] = None,
        max_retries: int = 2,
        **kwargs,
    ) -> Any:
        """
        Execute a request on a selected backend with automatic retry.

        Args:
            func: Function to execute on backend
            context: Request context (e.g., client IP)
            max_retries: Maximum retry attempts on failure

        Returns:
            Result from backend
        """
        last_error = None

        for attempt in range(max_retries + 1):
            backend = await self.select_backend(context)
            if not backend:
                raise RuntimeError("No available backends")

            # Track active connection
            backend.metrics.active_connections += 1

            try:
                start_time = time.time()

                # Execute request
                result = await func(backend, *args, **kwargs)

                # Record success
                latency_ms = (time.time() - start_time) * 1000
                backend.metrics.record_request(latency_ms, success=True)

                return result

            except Exception as e:
                # Record failure
                latency_ms = (time.time() - start_time) * 1000
                backend.metrics.record_request(latency_ms, success=False)

                last_error = e
                logger.warning(f"Request failed on backend {backend.backend_id}: {str(e)}")

                # Mark backend as degraded if too many failures
                if backend.metrics.consecutive_failures >= 3:
                    backend.status = BackendStatus.DEGRADED
                    logger.warning(f"Backend {backend.backend_id} marked as degraded")

            finally:
                backend.metrics.active_connections -= 1

        # All retries failed
        if last_error:
            raise last_error
        raise RuntimeError("Request failed after all retries")

    async def start_health_checks(self):
        """Start background health checking."""
        if not self.enable_health_checks:
            return

        if self._health_check_task is not None:
            return  # Already running

        self._health_check_task = asyncio.create_task(self._health_check_loop())
        logger.info("Started health check loop")

    async def stop_health_checks(self):
        """Stop background health checking."""
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
            self._health_check_task = None
            logger.info("Stopped health check loop")

    async def _health_check_loop(self):
        """Background loop for health checks."""
        while True:
            try:
                await self._run_health_checks()
            except Exception as e:
                logger.error(f"Health check error: {str(e)}")

            # Wait before next check
            if self.backends:
                interval = next(iter(self.backends.values())).health_check_config.interval_seconds
            else:
                interval = 30.0

            await asyncio.sleep(interval)

    async def _run_health_checks(self):
        """Run health checks on all backends."""
        for backend in self.backends.values():
            await self._check_backend_health(backend)

    async def _check_backend_health(self, backend: Backend):
        """Check health of a single backend."""
        if not backend.health_check_function:
            # No health check configured, assume healthy
            backend.status = BackendStatus.HEALTHY
            return

        config = backend.health_check_config

        try:
            # Run health check with timeout
            await asyncio.wait_for(
                backend.health_check_function(backend),
                timeout=config.timeout_seconds
            )

            # Health check passed
            backend.metrics.consecutive_successes += 1
            backend.metrics.consecutive_failures = 0

            # Mark as healthy if threshold reached
            if backend.metrics.consecutive_successes >= config.healthy_threshold:
                if backend.status != BackendStatus.HEALTHY:
                    backend.status = BackendStatus.HEALTHY
                    logger.info(f"Backend {backend.backend_id} is now healthy")

        except Exception as e:
            # Health check failed
            backend.metrics.consecutive_failures += 1
            backend.metrics.consecutive_successes = 0

            logger.warning(f"Health check failed for {backend.backend_id}: {str(e)}")

            # Mark as unhealthy if threshold reached
            if backend.metrics.consecutive_failures >= config.unhealthy_threshold:
                if backend.status != BackendStatus.UNHEALTHY:
                    backend.status = BackendStatus.UNHEALTHY
                    logger.error(f"Backend {backend.backend_id} is now unhealthy")

        backend.metrics.last_health_check = datetime.utcnow()

    def get_stats(self) -> Dict[str, Any]:
        """Get load balancer statistics."""
        return {
            "algorithm": self.algorithm.value,
            "total_backends": len(self.backends),
            "healthy_backends": sum(1 for b in self.backends.values() if b.status == BackendStatus.HEALTHY),
            "degraded_backends": sum(1 for b in self.backends.values() if b.status == BackendStatus.DEGRADED),
            "unhealthy_backends": sum(1 for b in self.backends.values() if b.status == BackendStatus.UNHEALTHY),
            "backends": {
                backend_id: backend.to_dict()
                for backend_id, backend in self.backends.items()
            }
        }


__all__ = [
    "Backend",
    "BackendStatus",
    "BackendMetrics",
    "HealthCheckConfig",
    "LoadBalancer",
    "LoadBalancingAlgorithm",
    "LoadBalancingStrategy",
    "RoundRobinStrategy",
    "LeastConnectionsStrategy",
    "WeightedRoundRobinStrategy",
    "LatencyBasedStrategy",
    "RandomStrategy",
    "IPHashStrategy",
]
