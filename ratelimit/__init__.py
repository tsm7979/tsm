"""
Rate Limiting & Quota Management
=================================

Token bucket rate limiting and usage quota enforcement.
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, deque
import time
import logging

logger = logging.getLogger(__name__)


@dataclass
class QuotaLimit:
    """Resource quota limit."""
    max_requests: int
    max_tokens: int
    max_cost_usd: float
    window_seconds: int

    def __str__(self) -> str:
        """String representation."""
        window_desc = f"{self.window_seconds}s"
        if self.window_seconds >= 3600:
            window_desc = f"{self.window_seconds // 3600}h"
        elif self.window_seconds >= 60:
            window_desc = f"{self.window_seconds // 60}m"

        return (
            f"{self.max_requests} req/{window_desc}, "
            f"{self.max_tokens} tokens/{window_desc}, "
            f"${self.max_cost_usd}/{window_desc}"
        )


@dataclass
class UsageStats:
    """Current usage statistics."""
    requests: int = 0
    tokens: int = 0
    cost_usd: float = 0.0
    window_start: datetime = field(default_factory=datetime.utcnow)

    def reset(self):
        """Reset usage stats."""
        self.requests = 0
        self.tokens = 0
        self.cost_usd = 0.0
        self.window_start = datetime.utcnow()


class TokenBucket:
    """
    Token bucket rate limiter.

    Classic token bucket algorithm for smooth rate limiting.
    """

    def __init__(
        self,
        rate: float,
        capacity: float,
        initial_tokens: Optional[float] = None
    ):
        """
        Initialize token bucket.

        Args:
            rate: Token refill rate (tokens per second)
            capacity: Maximum bucket capacity
            initial_tokens: Initial token count (default: capacity)
        """
        self.rate = rate
        self.capacity = capacity
        self.tokens = initial_tokens if initial_tokens is not None else capacity
        self.last_update = time.time()

        logger.debug(
            f"TokenBucket initialized (rate={rate}/s, capacity={capacity})"
        )

    def consume(self, tokens: float = 1.0) -> bool:
        """
        Try to consume tokens.

        Args:
            tokens: Number of tokens to consume

        Returns:
            True if tokens consumed, False if insufficient
        """
        self._refill()

        if self.tokens >= tokens:
            self.tokens -= tokens
            return True

        return False

    def _refill(self):
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self.last_update

        # Add tokens based on elapsed time
        self.tokens = min(
            self.capacity,
            self.tokens + (self.rate * elapsed)
        )

        self.last_update = now

    def available(self) -> float:
        """Get available tokens."""
        self._refill()
        return self.tokens

    def wait_time(self, tokens: float = 1.0) -> float:
        """
        Calculate wait time for tokens to be available.

        Args:
            tokens: Number of tokens needed

        Returns:
            Wait time in seconds (0 if available now)
        """
        self._refill()

        if self.tokens >= tokens:
            return 0.0

        tokens_needed = tokens - self.tokens
        return tokens_needed / self.rate


class QuotaManager:
    """
    Quota manager for enforcing usage limits.

    Tracks requests, tokens, and costs per user/tenant.
    """

    def __init__(self):
        """Initialize quota manager."""
        # User quotas
        self.quotas: Dict[str, QuotaLimit] = {}

        # Current usage per user
        self.usage: Dict[str, UsageStats] = defaultdict(UsageStats)

        # Request history (for sliding window)
        self.request_history: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=10000)
        )

        # Default quotas by tier
        self.tier_quotas = {
            "free": QuotaLimit(
                max_requests=100,
                max_tokens=100_000,
                max_cost_usd=0.10,
                window_seconds=3600  # 1 hour
            ),
            "pro": QuotaLimit(
                max_requests=1000,
                max_tokens=1_000_000,
                max_cost_usd=10.0,
                window_seconds=3600  # 1 hour
            ),
            "enterprise": QuotaLimit(
                max_requests=10_000,
                max_tokens=10_000_000,
                max_cost_usd=1000.0,
                window_seconds=3600  # 1 hour
            ),
        }

        logger.info("QuotaManager initialized")

    def set_user_quota(
        self,
        user_id: str,
        quota: QuotaLimit
    ):
        """
        Set quota for a user.

        Args:
            user_id: User identifier
            quota: Quota limits
        """
        self.quotas[user_id] = quota
        logger.info(f"Set quota for {user_id}: {quota}")

    def set_user_tier(self, user_id: str, tier: str):
        """
        Set user tier (free/pro/enterprise).

        Args:
            user_id: User identifier
            tier: Tier name
        """
        if tier not in self.tier_quotas:
            raise ValueError(f"Invalid tier: {tier}")

        self.quotas[user_id] = self.tier_quotas[tier]
        logger.info(f"Set {user_id} to {tier} tier")

    def check_quota(
        self,
        user_id: str,
        estimated_tokens: int = 0,
        estimated_cost: float = 0.0
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if request is within quota.

        Args:
            user_id: User identifier
            estimated_tokens: Estimated tokens for request
            estimated_cost: Estimated cost for request

        Returns:
            Tuple of (allowed, reason_if_denied)
        """
        # Get quota
        quota = self.quotas.get(user_id)
        if quota is None:
            # No quota set - allow
            return True, None

        # Get current usage
        usage = self.usage[user_id]

        # Check if window expired
        now = datetime.utcnow()
        window_age = (now - usage.window_start).total_seconds()
        if window_age >= quota.window_seconds:
            # Reset window
            usage.reset()

        # Check request limit
        if usage.requests >= quota.max_requests:
            return False, f"Request limit exceeded ({quota.max_requests} req/{quota.window_seconds}s)"

        # Check token limit
        if usage.tokens + estimated_tokens > quota.max_tokens:
            return False, f"Token limit exceeded ({quota.max_tokens} tokens/{quota.window_seconds}s)"

        # Check cost limit
        if usage.cost_usd + estimated_cost > quota.max_cost_usd:
            return False, f"Cost limit exceeded (${quota.max_cost_usd}/{quota.window_seconds}s)"

        return True, None

    def record_usage(
        self,
        user_id: str,
        tokens: int,
        cost: float
    ):
        """
        Record usage for a user.

        Args:
            user_id: User identifier
            tokens: Tokens used
            cost: Cost incurred
        """
        usage = self.usage[user_id]
        usage.requests += 1
        usage.tokens += tokens
        usage.cost_usd += cost

        # Record timestamp for sliding window
        self.request_history[user_id].append({
            "timestamp": datetime.utcnow(),
            "tokens": tokens,
            "cost": cost
        })

        logger.debug(
            f"Recorded usage for {user_id}: "
            f"{tokens} tokens, ${cost:.6f}"
        )

    def get_usage(self, user_id: str) -> Dict[str, Any]:
        """
        Get current usage for a user.

        Args:
            user_id: User identifier

        Returns:
            Usage statistics
        """
        quota = self.quotas.get(user_id)
        usage = self.usage[user_id]

        result = {
            "requests": usage.requests,
            "tokens": usage.tokens,
            "cost_usd": usage.cost_usd,
            "window_start": usage.window_start.isoformat(),
        }

        if quota:
            result["limits"] = {
                "max_requests": quota.max_requests,
                "max_tokens": quota.max_tokens,
                "max_cost_usd": quota.max_cost_usd,
                "window_seconds": quota.window_seconds,
            }
            result["remaining"] = {
                "requests": max(0, quota.max_requests - usage.requests),
                "tokens": max(0, quota.max_tokens - usage.tokens),
                "cost_usd": max(0, quota.max_cost_usd - usage.cost_usd),
            }
            result["utilization"] = {
                "requests": usage.requests / quota.max_requests,
                "tokens": usage.tokens / quota.max_tokens,
                "cost": usage.cost_usd / quota.max_cost_usd,
            }

        return result

    def reset_user_usage(self, user_id: str):
        """Reset usage for a user."""
        if user_id in self.usage:
            self.usage[user_id].reset()
        if user_id in self.request_history:
            self.request_history[user_id].clear()
        logger.info(f"Reset usage for {user_id}")


class RateLimiter:
    """
    Combined rate limiter with token bucket and quota management.
    """

    def __init__(
        self,
        requests_per_second: float = 10.0,
        burst_size: int = 20,
        enable_quotas: bool = True
    ):
        """
        Initialize rate limiter.

        Args:
            requests_per_second: Request rate limit
            burst_size: Burst capacity
            enable_quotas: Enable quota management
        """
        self.requests_per_second = requests_per_second
        self.burst_size = burst_size
        self.enable_quotas = enable_quotas

        # Token buckets per user
        self.buckets: Dict[str, TokenBucket] = {}

        # Quota manager
        self.quota_manager = QuotaManager() if enable_quotas else None

        logger.info(
            f"RateLimiter initialized "
            f"(rate={requests_per_second}/s, burst={burst_size})"
        )

    def _get_bucket(self, user_id: str) -> TokenBucket:
        """Get or create token bucket for user."""
        if user_id not in self.buckets:
            self.buckets[user_id] = TokenBucket(
                rate=self.requests_per_second,
                capacity=self.burst_size
            )
        return self.buckets[user_id]

    def check_rate_limit(
        self,
        user_id: str,
        estimated_tokens: int = 0,
        estimated_cost: float = 0.0
    ) -> Tuple[bool, Optional[str], Optional[float]]:
        """
        Check if request is allowed.

        Args:
            user_id: User identifier
            estimated_tokens: Estimated tokens
            estimated_cost: Estimated cost

        Returns:
            Tuple of (allowed, reason_if_denied, retry_after_seconds)
        """
        # Check token bucket
        bucket = self._get_bucket(user_id)
        if not bucket.consume(1.0):
            wait_time = bucket.wait_time(1.0)
            return False, "Rate limit exceeded", wait_time

        # Check quota
        if self.enable_quotas:
            allowed, reason = self.quota_manager.check_quota(
                user_id,
                estimated_tokens,
                estimated_cost
            )
            if not allowed:
                return False, reason, None

        return True, None, None

    def record_request(
        self,
        user_id: str,
        tokens: int,
        cost: float
    ):
        """Record completed request."""
        if self.enable_quotas:
            self.quota_manager.record_usage(user_id, tokens, cost)

    def get_limits(self, user_id: str) -> Dict[str, Any]:
        """Get current limits and usage."""
        bucket = self._get_bucket(user_id)

        result = {
            "rate_limit": {
                "requests_per_second": self.requests_per_second,
                "burst_size": self.burst_size,
                "available_tokens": bucket.available(),
            }
        }

        if self.enable_quotas:
            result["quota"] = self.quota_manager.get_usage(user_id)

        return result


# Global rate limiter
rate_limiter = RateLimiter(
    requests_per_second=10.0,
    burst_size=20,
    enable_quotas=True
)

# Configure default quotas
rate_limiter.quota_manager.set_user_tier("default", "free")
