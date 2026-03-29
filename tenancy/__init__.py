"""
TSM Multi-Tenancy Layer
========================

Complete multi-tenancy support with:
- Tenant isolation
- Per-tenant quotas and limits
- Data segregation
- Tenant-specific configuration
- Tenant management
"""

import uuid
from typing import Dict, Optional, List, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import logging
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class TenantStatus(str, Enum):
    """Tenant account status."""

    ACTIVE = "active"
    SUSPENDED = "suspended"
    TRIAL = "trial"
    DELETED = "deleted"


class TenantTier(str, Enum):
    """Tenant subscription tiers."""

    FREE = "free"
    STARTER = "starter"
    PRO = "pro"
    ENTERPRISE = "enterprise"


@dataclass
class TenantQuota:
    """Per-tenant quota limits."""

    # Request limits
    max_requests_per_hour: int = 100
    max_requests_per_day: int = 1000
    max_requests_per_month: int = 10000

    # Token limits
    max_tokens_per_request: int = 4096
    max_tokens_per_day: int = 100000
    max_tokens_per_month: int = 1000000

    # Cost limits
    max_cost_per_request_usd: float = 0.10
    max_cost_per_day_usd: float = 5.0
    max_cost_per_month_usd: float = 100.0

    # Feature limits
    max_documents: int = 100
    max_plugins: int = 5
    max_webhooks: int = 10
    max_cache_entries: int = 1000

    # Performance limits
    max_concurrent_requests: int = 5
    rate_limit_per_second: float = 2.0
    timeout_seconds: float = 30.0

    # Storage limits
    max_storage_mb: int = 100
    max_file_size_mb: int = 10


# Tier-based default quotas
TIER_QUOTAS = {
    TenantTier.FREE: TenantQuota(
        max_requests_per_hour=100,
        max_requests_per_day=1000,
        max_requests_per_month=10000,
        max_tokens_per_request=4096,
        max_tokens_per_day=100000,
        max_tokens_per_month=1000000,
        max_cost_per_request_usd=0.01,
        max_cost_per_day_usd=1.0,
        max_cost_per_month_usd=10.0,
        max_documents=100,
        max_plugins=2,
        max_webhooks=5,
        max_concurrent_requests=2,
        rate_limit_per_second=1.0,
        max_storage_mb=50,
    ),
    TenantTier.STARTER: TenantQuota(
        max_requests_per_hour=500,
        max_requests_per_day=10000,
        max_requests_per_month=100000,
        max_tokens_per_request=8192,
        max_tokens_per_day=500000,
        max_tokens_per_month=10000000,
        max_cost_per_request_usd=0.05,
        max_cost_per_day_usd=10.0,
        max_cost_per_month_usd=100.0,
        max_documents=1000,
        max_plugins=10,
        max_webhooks=20,
        max_concurrent_requests=10,
        rate_limit_per_second=5.0,
        max_storage_mb=500,
    ),
    TenantTier.PRO: TenantQuota(
        max_requests_per_hour=2000,
        max_requests_per_day=50000,
        max_requests_per_month=1000000,
        max_tokens_per_request=32768,
        max_tokens_per_day=2000000,
        max_tokens_per_month=50000000,
        max_cost_per_request_usd=0.50,
        max_cost_per_day_usd=100.0,
        max_cost_per_month_usd=1000.0,
        max_documents=10000,
        max_plugins=50,
        max_webhooks=100,
        max_concurrent_requests=50,
        rate_limit_per_second=20.0,
        max_storage_mb=5000,
    ),
    TenantTier.ENTERPRISE: TenantQuota(
        max_requests_per_hour=10000,
        max_requests_per_day=500000,
        max_requests_per_month=10000000,
        max_tokens_per_request=128000,
        max_tokens_per_day=10000000,
        max_tokens_per_month=100000000,
        max_cost_per_request_usd=5.0,
        max_cost_per_day_usd=1000.0,
        max_cost_per_month_usd=10000.0,
        max_documents=100000,
        max_plugins=1000,
        max_webhooks=1000,
        max_concurrent_requests=200,
        rate_limit_per_second=100.0,
        max_storage_mb=50000,
    ),
}


@dataclass
class TenantUsage:
    """Current tenant usage tracking."""

    tenant_id: str

    # Request counters
    requests_hour: int = 0
    requests_day: int = 0
    requests_month: int = 0

    # Token counters
    tokens_day: int = 0
    tokens_month: int = 0

    # Cost counters
    cost_day_usd: float = 0.0
    cost_month_usd: float = 0.0

    # Resource counters
    documents: int = 0
    plugins: int = 0
    webhooks: int = 0
    cache_entries: int = 0
    storage_mb: float = 0.0

    # Current state
    concurrent_requests: int = 0

    # Timestamps
    last_request: Optional[datetime] = None
    hour_reset_at: datetime = field(default_factory=datetime.utcnow)
    day_reset_at: datetime = field(default_factory=datetime.utcnow)
    month_reset_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tenant_id": self.tenant_id,
            "requests": {
                "hour": self.requests_hour,
                "day": self.requests_day,
                "month": self.requests_month,
            },
            "tokens": {
                "day": self.tokens_day,
                "month": self.tokens_month,
            },
            "cost_usd": {
                "day": self.cost_day_usd,
                "month": self.cost_month_usd,
            },
            "resources": {
                "documents": self.documents,
                "plugins": self.plugins,
                "webhooks": self.webhooks,
                "cache_entries": self.cache_entries,
                "storage_mb": self.storage_mb,
            },
            "concurrent_requests": self.concurrent_requests,
            "last_request": self.last_request.isoformat() if self.last_request else None,
        }


@dataclass
class TenantConfig:
    """Tenant-specific configuration."""

    # Model preferences
    default_provider: Optional[str] = None
    default_model: Optional[str] = None
    allowed_providers: Optional[List[str]] = None
    allowed_models: Optional[List[str]] = None

    # Feature toggles
    enable_caching: bool = True
    enable_webhooks: bool = True
    enable_plugins: bool = True
    enable_analytics: bool = True
    enable_tracing: bool = True

    # Security settings
    require_api_key: bool = True
    allowed_ip_ranges: Optional[List[str]] = None
    enable_audit_log: bool = True

    # Custom settings
    custom: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Tenant:
    """
    Tenant entity.

    Represents a single tenant in the multi-tenant system.
    """

    tenant_id: str
    name: str
    status: TenantStatus = TenantStatus.ACTIVE
    tier: TenantTier = TenantTier.FREE

    # Contact info
    email: str = ""
    company: Optional[str] = None

    # Authentication
    api_keys: List[str] = field(default_factory=list)

    # Quotas and usage
    quota: TenantQuota = field(default_factory=lambda: TIER_QUOTAS[TenantTier.FREE])
    usage: Optional[TenantUsage] = None

    # Configuration
    config: TenantConfig = field(default_factory=TenantConfig)

    # Metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.usage is None:
            self.usage = TenantUsage(tenant_id=self.tenant_id)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tenant_id": self.tenant_id,
            "name": self.name,
            "status": self.status.value,
            "tier": self.tier.value,
            "email": self.email,
            "company": self.company,
            "quota": self.quota.__dict__,
            "usage": self.usage.to_dict() if self.usage else None,
            "config": self.config.__dict__,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "metadata": self.metadata,
        }

    def is_active(self) -> bool:
        """Check if tenant is active."""
        return self.status == TenantStatus.ACTIVE

    def can_make_request(self) -> tuple[bool, Optional[str]]:
        """
        Check if tenant can make a request.

        Returns:
            (allowed, reason) tuple
        """
        if not self.is_active():
            return False, f"Tenant status is {self.status.value}"

        if not self.usage:
            return True, None

        # Check hourly limit
        if self.usage.requests_hour >= self.quota.max_requests_per_hour:
            return False, "Hourly request limit exceeded"

        # Check daily limit
        if self.usage.requests_day >= self.quota.max_requests_per_day:
            return False, "Daily request limit exceeded"

        # Check monthly limit
        if self.usage.requests_month >= self.quota.max_requests_per_month:
            return False, "Monthly request limit exceeded"

        # Check concurrent requests
        if self.usage.concurrent_requests >= self.quota.max_concurrent_requests:
            return False, "Concurrent request limit exceeded"

        # Check daily cost limit
        if self.usage.cost_day_usd >= self.quota.max_cost_per_day_usd:
            return False, "Daily cost limit exceeded"

        # Check monthly cost limit
        if self.usage.cost_month_usd >= self.quota.max_cost_per_month_usd:
            return False, "Monthly cost limit exceeded"

        return True, None


class TenantStore(ABC):
    """Abstract tenant storage interface."""

    @abstractmethod
    async def create(self, tenant: Tenant) -> Tenant:
        """Create a new tenant."""
        pass

    @abstractmethod
    async def get(self, tenant_id: str) -> Optional[Tenant]:
        """Get tenant by ID."""
        pass

    @abstractmethod
    async def get_by_api_key(self, api_key: str) -> Optional[Tenant]:
        """Get tenant by API key."""
        pass

    @abstractmethod
    async def update(self, tenant: Tenant) -> Tenant:
        """Update existing tenant."""
        pass

    @abstractmethod
    async def delete(self, tenant_id: str) -> bool:
        """Delete tenant."""
        pass

    @abstractmethod
    async def list(self, limit: int = 100, offset: int = 0) -> List[Tenant]:
        """List all tenants."""
        pass


class InMemoryTenantStore(TenantStore):
    """In-memory tenant storage (for development)."""

    def __init__(self):
        self._tenants: Dict[str, Tenant] = {}
        self._api_key_index: Dict[str, str] = {}  # api_key -> tenant_id

    async def create(self, tenant: Tenant) -> Tenant:
        """Create a new tenant."""
        self._tenants[tenant.tenant_id] = tenant

        # Index API keys
        for api_key in tenant.api_keys:
            self._api_key_index[api_key] = tenant.tenant_id

        logger.info(f"Created tenant: {tenant.tenant_id} ({tenant.name})")
        return tenant

    async def get(self, tenant_id: str) -> Optional[Tenant]:
        """Get tenant by ID."""
        return self._tenants.get(tenant_id)

    async def get_by_api_key(self, api_key: str) -> Optional[Tenant]:
        """Get tenant by API key."""
        tenant_id = self._api_key_index.get(api_key)
        if tenant_id:
            return self._tenants.get(tenant_id)
        return None

    async def update(self, tenant: Tenant) -> Tenant:
        """Update existing tenant."""
        tenant.updated_at = datetime.utcnow()
        self._tenants[tenant.tenant_id] = tenant

        # Re-index API keys
        for api_key in tenant.api_keys:
            self._api_key_index[api_key] = tenant.tenant_id

        return tenant

    async def delete(self, tenant_id: str) -> bool:
        """Delete tenant."""
        tenant = self._tenants.pop(tenant_id, None)
        if tenant:
            # Remove from API key index
            for api_key in tenant.api_keys:
                self._api_key_index.pop(api_key, None)
            logger.info(f"Deleted tenant: {tenant_id}")
            return True
        return False

    async def list(self, limit: int = 100, offset: int = 0) -> List[Tenant]:
        """List all tenants."""
        tenants = list(self._tenants.values())
        return tenants[offset:offset + limit]


class TenantManager:
    """
    Tenant management service.

    Handles tenant lifecycle, quota tracking, and usage monitoring.
    """

    def __init__(self, store: Optional[TenantStore] = None):
        self.store = store or InMemoryTenantStore()

    async def create_tenant(
        self,
        name: str,
        email: str,
        tier: TenantTier = TenantTier.FREE,
        company: Optional[str] = None,
    ) -> Tenant:
        """Create a new tenant."""
        tenant_id = str(uuid.uuid4())
        api_key = f"tsm_{uuid.uuid4().hex}"

        tenant = Tenant(
            tenant_id=tenant_id,
            name=name,
            email=email,
            tier=tier,
            company=company,
            api_keys=[api_key],
            quota=TIER_QUOTAS[tier],
        )

        return await self.store.create(tenant)

    async def get_tenant(self, tenant_id: str) -> Optional[Tenant]:
        """Get tenant by ID."""
        return await self.store.get(tenant_id)

    async def get_tenant_by_api_key(self, api_key: str) -> Optional[Tenant]:
        """Get tenant by API key."""
        return await self.store.get_by_api_key(api_key)

    async def update_tenant(self, tenant: Tenant) -> Tenant:
        """Update tenant."""
        return await self.store.update(tenant)

    async def delete_tenant(self, tenant_id: str) -> bool:
        """Delete tenant (soft delete)."""
        tenant = await self.store.get(tenant_id)
        if tenant:
            tenant.status = TenantStatus.DELETED
            await self.store.update(tenant)
            return True
        return False

    async def suspend_tenant(self, tenant_id: str) -> bool:
        """Suspend tenant."""
        tenant = await self.store.get(tenant_id)
        if tenant:
            tenant.status = TenantStatus.SUSPENDED
            await self.store.update(tenant)
            logger.warning(f"Suspended tenant: {tenant_id}")
            return True
        return False

    async def activate_tenant(self, tenant_id: str) -> bool:
        """Activate tenant."""
        tenant = await self.store.get(tenant_id)
        if tenant:
            tenant.status = TenantStatus.ACTIVE
            await self.store.update(tenant)
            logger.info(f"Activated tenant: {tenant_id}")
            return True
        return False

    async def upgrade_tier(self, tenant_id: str, new_tier: TenantTier) -> bool:
        """Upgrade tenant tier."""
        tenant = await self.store.get(tenant_id)
        if tenant:
            tenant.tier = new_tier
            tenant.quota = TIER_QUOTAS[new_tier]
            await self.store.update(tenant)
            logger.info(f"Upgraded tenant {tenant_id} to {new_tier.value}")
            return True
        return False

    async def record_usage(
        self,
        tenant_id: str,
        tokens: int = 0,
        cost_usd: float = 0.0,
    ) -> TenantUsage:
        """Record usage for a tenant."""
        tenant = await self.store.get(tenant_id)
        if not tenant or not tenant.usage:
            raise ValueError(f"Tenant not found: {tenant_id}")

        usage = tenant.usage

        # Update counters
        usage.requests_hour += 1
        usage.requests_day += 1
        usage.requests_month += 1
        usage.tokens_day += tokens
        usage.tokens_month += tokens
        usage.cost_day_usd += cost_usd
        usage.cost_month_usd += cost_usd
        usage.last_request = datetime.utcnow()

        await self.store.update(tenant)
        return usage

    async def increment_concurrent(self, tenant_id: str) -> int:
        """Increment concurrent request counter."""
        tenant = await self.store.get(tenant_id)
        if not tenant or not tenant.usage:
            raise ValueError(f"Tenant not found: {tenant_id}")

        tenant.usage.concurrent_requests += 1
        await self.store.update(tenant)
        return tenant.usage.concurrent_requests

    async def decrement_concurrent(self, tenant_id: str) -> int:
        """Decrement concurrent request counter."""
        tenant = await self.store.get(tenant_id)
        if not tenant or not tenant.usage:
            raise ValueError(f"Tenant not found: {tenant_id}")

        tenant.usage.concurrent_requests = max(0, tenant.usage.concurrent_requests - 1)
        await self.store.update(tenant)
        return tenant.usage.concurrent_requests

    async def reset_usage(self, tenant_id: str, period: str = "hour"):
        """Reset usage counters for a period."""
        tenant = await self.store.get(tenant_id)
        if not tenant or not tenant.usage:
            return

        usage = tenant.usage
        now = datetime.utcnow()

        if period == "hour":
            usage.requests_hour = 0
            usage.hour_reset_at = now
        elif period == "day":
            usage.requests_day = 0
            usage.tokens_day = 0
            usage.cost_day_usd = 0.0
            usage.day_reset_at = now
        elif period == "month":
            usage.requests_month = 0
            usage.tokens_month = 0
            usage.cost_month_usd = 0.0
            usage.month_reset_at = now

        await self.store.update(tenant)

    async def list_tenants(self, limit: int = 100, offset: int = 0) -> List[Tenant]:
        """List all tenants."""
        return await self.store.list(limit, offset)


# Global tenant manager instance
_tenant_manager: Optional[TenantManager] = None


def get_tenant_manager() -> TenantManager:
    """Get global tenant manager instance."""
    global _tenant_manager
    if _tenant_manager is None:
        _tenant_manager = TenantManager()
    return _tenant_manager


__all__ = [
    "Tenant",
    "TenantStatus",
    "TenantTier",
    "TenantQuota",
    "TenantUsage",
    "TenantConfig",
    "TenantStore",
    "InMemoryTenantStore",
    "TenantManager",
    "TIER_QUOTAS",
    "get_tenant_manager",
]
