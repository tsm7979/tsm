"""
TSM Resilience Layer
====================

Circuit breakers, retries, timeouts, and fault tolerance patterns.

Key features:
- Circuit breaker pattern
- Automatic retry with exponential backoff
- Timeout management
- Fallback strategies
- Health checks
"""

from enum import Enum
from typing import Optional, Callable, Any, Dict, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import asyncio
import time
import logging
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class CircuitState(str, Enum):
    """Circuit breaker states."""

    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered


class FailureType(str, Enum):
    """Types of failures to track."""

    TIMEOUT = "timeout"
    ERROR = "error"
    RATE_LIMIT = "rate_limit"
    UNAVAILABLE = "unavailable"
    INVALID_RESPONSE = "invalid_response"


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""

    failure_threshold: int = 5  # Failures before opening
    success_threshold: int = 2  # Successes to close from half-open
    timeout_seconds: float = 30.0  # Request timeout
    reset_timeout_seconds: float = 60.0  # Time before trying half-open
    half_open_max_calls: int = 3  # Max calls in half-open state

    # Tracked failure types
    tracked_exceptions: List[type] = field(default_factory=lambda: [
        Exception, TimeoutError, ConnectionError, RuntimeError
    ])


@dataclass
class CircuitBreakerStats:
    """Statistics for circuit breaker."""

    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: Optional[datetime] = None
    last_state_change: datetime = field(default_factory=datetime.utcnow)
    total_calls: int = 0
    total_failures: int = 0
    total_successes: int = 0
    total_timeouts: int = 0
    total_rejected: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "last_failure": self.last_failure_time.isoformat() if self.last_failure_time else None,
            "last_state_change": self.last_state_change.isoformat(),
            "total_calls": self.total_calls,
            "total_failures": self.total_failures,
            "total_successes": self.total_successes,
            "total_timeouts": self.total_timeouts,
            "total_rejected": self.total_rejected,
            "success_rate": self.total_successes / self.total_calls if self.total_calls > 0 else 0.0,
        }


class CircuitBreakerOpen(Exception):
    """Exception raised when circuit breaker is open."""

    def __init__(self, message: str, stats: CircuitBreakerStats):
        super().__init__(message)
        self.stats = stats


class CircuitBreaker:
    """
    Circuit breaker implementation.

    Prevents cascading failures by stopping requests to failing services.

    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Service failing, reject all requests immediately
    - HALF_OPEN: Testing if service recovered, allow limited requests

    Usage:
        breaker = CircuitBreaker(name="openai_api")

        async with breaker:
            result = await call_external_api()
    """

    def __init__(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None,
        on_state_change: Optional[Callable[[CircuitState, CircuitState], None]] = None,
    ):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.stats = CircuitBreakerStats()
        self.on_state_change = on_state_change
        self._lock = asyncio.Lock()
        self._half_open_calls = 0

    async def __aenter__(self):
        """Enter context - check if call is allowed."""
        await self._before_call()
        self._call_start = time.time()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit context - record success or failure."""
        duration = time.time() - self._call_start

        if exc_type is None:
            # Success
            await self._on_success()
            return False

        # Check if this is a tracked exception
        if any(isinstance(exc_val, exc_class) for exc_class in self.config.tracked_exceptions):
            failure_type = FailureType.TIMEOUT if isinstance(exc_val, TimeoutError) else FailureType.ERROR
            await self._on_failure(failure_type)

        # Don't suppress exception
        return False

    async def _before_call(self):
        """Check if call should be allowed based on current state."""
        async with self._lock:
            self.stats.total_calls += 1

            if self.stats.state == CircuitState.OPEN:
                # Check if we should try half-open
                if self._should_attempt_reset():
                    await self._transition_to(CircuitState.HALF_OPEN)
                else:
                    self.stats.total_rejected += 1
                    raise CircuitBreakerOpen(
                        f"Circuit breaker '{self.name}' is OPEN",
                        self.stats
                    )

            elif self.stats.state == CircuitState.HALF_OPEN:
                # Limit concurrent calls in half-open
                if self._half_open_calls >= self.config.half_open_max_calls:
                    self.stats.total_rejected += 1
                    raise CircuitBreakerOpen(
                        f"Circuit breaker '{self.name}' is HALF_OPEN (max calls reached)",
                        self.stats
                    )
                self._half_open_calls += 1

    async def _on_success(self):
        """Record successful call."""
        async with self._lock:
            self.stats.total_successes += 1
            self.stats.success_count += 1
            self.stats.failure_count = 0  # Reset failure count

            if self.stats.state == CircuitState.HALF_OPEN:
                self._half_open_calls -= 1

                # Check if we should close
                if self.stats.success_count >= self.config.success_threshold:
                    await self._transition_to(CircuitState.CLOSED)

    async def _on_failure(self, failure_type: FailureType):
        """Record failed call."""
        async with self._lock:
            self.stats.total_failures += 1
            self.stats.failure_count += 1
            self.stats.success_count = 0  # Reset success count
            self.stats.last_failure_time = datetime.utcnow()

            if failure_type == FailureType.TIMEOUT:
                self.stats.total_timeouts += 1

            if self.stats.state == CircuitState.HALF_OPEN:
                self._half_open_calls -= 1
                # Any failure in half-open -> back to open
                await self._transition_to(CircuitState.OPEN)

            elif self.stats.state == CircuitState.CLOSED:
                # Check if we should open
                if self.stats.failure_count >= self.config.failure_threshold:
                    await self._transition_to(CircuitState.OPEN)

    async def _transition_to(self, new_state: CircuitState):
        """Transition to a new state."""
        old_state = self.stats.state

        if old_state == new_state:
            return

        self.stats.state = new_state
        self.stats.last_state_change = datetime.utcnow()
        self.stats.failure_count = 0
        self.stats.success_count = 0
        self._half_open_calls = 0

        logger.info(
            f"Circuit breaker '{self.name}' transitioned: {old_state.value} -> {new_state.value}"
        )

        if self.on_state_change:
            self.on_state_change(old_state, new_state)

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to try half-open."""
        if self.stats.last_state_change is None:
            return True

        time_since_open = datetime.utcnow() - self.stats.last_state_change
        return time_since_open.total_seconds() >= self.config.reset_timeout_seconds

    def get_stats(self) -> CircuitBreakerStats:
        """Get current statistics."""
        return self.stats

    async def reset(self):
        """Manually reset circuit breaker to closed state."""
        async with self._lock:
            await self._transition_to(CircuitState.CLOSED)


class RetryStrategy(ABC):
    """Base class for retry strategies."""

    @abstractmethod
    def get_delay(self, attempt: int) -> float:
        """Get delay before next retry attempt."""
        pass

    @abstractmethod
    def should_retry(self, attempt: int, exception: Exception) -> bool:
        """Check if should retry after this attempt."""
        pass


class ExponentialBackoff(RetryStrategy):
    """Exponential backoff retry strategy."""

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter

    def get_delay(self, attempt: int) -> float:
        """Calculate delay with exponential backoff."""
        delay = min(
            self.base_delay * (self.exponential_base ** attempt),
            self.max_delay
        )

        if self.jitter:
            # Add random jitter (0-50% of delay)
            import random
            delay = delay * (0.5 + random.random() * 0.5)

        return delay

    def should_retry(self, attempt: int, exception: Exception) -> bool:
        """Check if should retry."""
        # Don't retry on certain exceptions
        if isinstance(exception, (KeyboardInterrupt, SystemExit)):
            return False

        return attempt < self.max_retries


class Retry:
    """
    Retry decorator with configurable strategy.

    Usage:
        retry = Retry(strategy=ExponentialBackoff(max_retries=3))

        @retry
        async def call_api():
            return await api.request()
    """

    def __init__(
        self,
        strategy: Optional[RetryStrategy] = None,
        on_retry: Optional[Callable[[int, Exception], None]] = None,
    ):
        self.strategy = strategy or ExponentialBackoff()
        self.on_retry = on_retry

    def __call__(self, func: Callable):
        """Decorator wrapper."""
        async def wrapper(*args, **kwargs):
            attempt = 0
            last_exception = None

            while True:
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e

                    if not self.strategy.should_retry(attempt, e):
                        raise

                    delay = self.strategy.get_delay(attempt)

                    if self.on_retry:
                        self.on_retry(attempt, e)

                    logger.warning(
                        f"Retry attempt {attempt + 1} after {delay:.2f}s due to: {str(e)}"
                    )

                    await asyncio.sleep(delay)
                    attempt += 1

            # Should never reach here, but just in case
            if last_exception:
                raise last_exception

        return wrapper


@dataclass
class FallbackConfig:
    """Configuration for fallback strategy."""

    fallback_value: Any = None
    fallback_function: Optional[Callable] = None
    log_fallback: bool = True


class Fallback:
    """
    Fallback decorator for graceful degradation.

    Usage:
        fallback = Fallback(fallback_value="Service unavailable")

        @fallback
        async def get_data():
            return await external_service.get()
    """

    def __init__(self, config: Optional[FallbackConfig] = None):
        self.config = config or FallbackConfig()

    def __call__(self, func: Callable):
        """Decorator wrapper."""
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                if self.config.log_fallback:
                    logger.warning(f"Fallback triggered for {func.__name__}: {str(e)}")

                if self.config.fallback_function:
                    return await self.config.fallback_function(*args, **kwargs)

                return self.config.fallback_value

        return wrapper


class CircuitBreakerRegistry:
    """
    Global registry for circuit breakers.

    Manages circuit breakers across the application.
    """

    def __init__(self):
        self._breakers: Dict[str, CircuitBreaker] = {}
        self._lock = asyncio.Lock()

    async def get_or_create(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None,
    ) -> CircuitBreaker:
        """Get existing or create new circuit breaker."""
        async with self._lock:
            if name not in self._breakers:
                self._breakers[name] = CircuitBreaker(name=name, config=config)
            return self._breakers[name]

    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all circuit breakers."""
        return {
            name: breaker.get_stats().to_dict()
            for name, breaker in self._breakers.items()
        }

    async def reset_all(self):
        """Reset all circuit breakers."""
        async with self._lock:
            for breaker in self._breakers.values():
                await breaker.reset()


# Global registry instance
registry = CircuitBreakerRegistry()


# Convenience functions
async def with_circuit_breaker(
    name: str,
    func: Callable,
    *args,
    config: Optional[CircuitBreakerConfig] = None,
    **kwargs
) -> Any:
    """
    Execute function with circuit breaker protection.

    Usage:
        result = await with_circuit_breaker(
            "openai_api",
            call_openai,
            prompt="Hello"
        )
    """
    breaker = await registry.get_or_create(name, config)

    async with breaker:
        return await func(*args, **kwargs)


__all__ = [
    "CircuitBreaker",
    "CircuitBreakerConfig",
    "CircuitBreakerStats",
    "CircuitState",
    "CircuitBreakerOpen",
    "CircuitBreakerRegistry",
    "Retry",
    "RetryStrategy",
    "ExponentialBackoff",
    "Fallback",
    "FallbackConfig",
    "FailureType",
    "registry",
    "with_circuit_breaker",
]
