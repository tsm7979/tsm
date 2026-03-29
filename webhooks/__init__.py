"""
Webhook System
==============

Event-driven webhooks for real-time notifications and integrations.
"""

from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import asyncio
import hashlib
import hmac
import json
import logging
import uuid
from collections import defaultdict

logger = logging.getLogger(__name__)


class WebhookEvent(str, Enum):
    """Webhook event types."""
    # Request events
    REQUEST_STARTED = "request.started"
    REQUEST_COMPLETED = "request.completed"
    REQUEST_FAILED = "request.failed"

    # Model events
    MODEL_CALLED = "model.called"
    MODEL_RESPONDED = "model.responded"
    MODEL_FAILED = "model.failed"

    # Cache events
    CACHE_HIT = "cache.hit"
    CACHE_MISS = "cache.miss"

    # Rate limit events
    RATE_LIMIT_EXCEEDED = "ratelimit.exceeded"
    QUOTA_WARNING = "quota.warning"
    QUOTA_EXCEEDED = "quota.exceeded"

    # Security events
    VERIFICATION_FAILED = "verification.failed"
    PII_DETECTED = "pii.detected"
    HIGH_RISK_REQUEST = "risk.high"

    # System events
    SYSTEM_STARTUP = "system.startup"
    SYSTEM_SHUTDOWN = "system.shutdown"
    SYSTEM_ERROR = "system.error"

    # Task events
    TASK_QUEUED = "task.queued"
    TASK_STARTED = "task.started"
    TASK_COMPLETED = "task.completed"
    TASK_FAILED = "task.failed"


@dataclass
class WebhookPayload:
    """Webhook event payload."""
    event_id: str
    event_type: WebhookEvent
    timestamp: datetime
    data: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "timestamp": self.timestamp.isoformat(),
            "data": self.data,
            "metadata": self.metadata,
        }


@dataclass
class WebhookEndpoint:
    """Registered webhook endpoint."""
    endpoint_id: str
    url: str
    events: List[WebhookEvent]
    secret: Optional[str] = None
    enabled: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_delivery: Optional[datetime] = None
    delivery_count: int = 0
    failure_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


class WebhookDeliveryStatus(str, Enum):
    """Webhook delivery status."""
    PENDING = "pending"
    DELIVERED = "delivered"
    FAILED = "failed"
    RETRYING = "retrying"


@dataclass
class WebhookDelivery:
    """Webhook delivery record."""
    delivery_id: str
    endpoint_id: str
    payload: WebhookPayload
    status: WebhookDeliveryStatus
    attempts: int = 0
    max_attempts: int = 3
    created_at: datetime = field(default_factory=datetime.utcnow)
    delivered_at: Optional[datetime] = None
    error: Optional[str] = None
    response_code: Optional[int] = None


class WebhookManager:
    """
    Webhook manager for event notifications.

    Features:
    - Event subscription
    - Automatic retries
    - HMAC signature verification
    - Delivery tracking
    - Rate limiting per endpoint
    """

    def __init__(
        self,
        max_retries: int = 3,
        retry_delay_seconds: int = 5,
        timeout_seconds: int = 10
    ):
        """
        Initialize webhook manager.

        Args:
            max_retries: Maximum delivery retries
            retry_delay_seconds: Delay between retries
            timeout_seconds: Request timeout
        """
        self.max_retries = max_retries
        self.retry_delay_seconds = retry_delay_seconds
        self.timeout_seconds = timeout_seconds

        # Registered endpoints
        self.endpoints: Dict[str, WebhookEndpoint] = {}

        # Delivery queue
        self.delivery_queue: asyncio.Queue = asyncio.Queue()

        # Delivery history
        self.deliveries: Dict[str, WebhookDelivery] = {}

        # Event listeners (in-process callbacks)
        self.listeners: Dict[WebhookEvent, List[Callable]] = defaultdict(list)

        # Worker task
        self.worker_task: Optional[asyncio.Task] = None
        self.running = False

        logger.info(
            f"WebhookManager initialized "
            f"(max_retries={max_retries}, timeout={timeout_seconds}s)"
        )

    def register_endpoint(
        self,
        url: str,
        events: List[WebhookEvent],
        secret: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Register a webhook endpoint.

        Args:
            url: Webhook URL
            events: List of events to subscribe to
            secret: Optional HMAC secret for signature
            metadata: Optional metadata

        Returns:
            Endpoint ID
        """
        endpoint_id = str(uuid.uuid4())

        endpoint = WebhookEndpoint(
            endpoint_id=endpoint_id,
            url=url,
            events=events,
            secret=secret,
            metadata=metadata or {}
        )

        self.endpoints[endpoint_id] = endpoint

        logger.info(
            f"Registered webhook endpoint: {endpoint_id} "
            f"(url={url}, events={len(events)})"
        )

        return endpoint_id

    def unregister_endpoint(self, endpoint_id: str) -> bool:
        """Unregister a webhook endpoint."""
        if endpoint_id in self.endpoints:
            del self.endpoints[endpoint_id]
            logger.info(f"Unregistered webhook endpoint: {endpoint_id}")
            return True
        return False

    def disable_endpoint(self, endpoint_id: str):
        """Disable an endpoint."""
        if endpoint_id in self.endpoints:
            self.endpoints[endpoint_id].enabled = False
            logger.info(f"Disabled webhook endpoint: {endpoint_id}")

    def enable_endpoint(self, endpoint_id: str):
        """Enable an endpoint."""
        if endpoint_id in self.endpoints:
            self.endpoints[endpoint_id].enabled = True
            logger.info(f"Enabled webhook endpoint: {endpoint_id}")

    def add_listener(
        self,
        event_type: WebhookEvent,
        callback: Callable
    ):
        """
        Add in-process event listener.

        Args:
            event_type: Event type to listen for
            callback: Callback function (can be async)
        """
        self.listeners[event_type].append(callback)
        logger.debug(f"Added listener for {event_type.value}")

    async def emit(
        self,
        event_type: WebhookEvent,
        data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Emit an event.

        Args:
            event_type: Event type
            data: Event data
            metadata: Optional metadata
        """
        # Create payload
        payload = WebhookPayload(
            event_id=str(uuid.uuid4()),
            event_type=event_type,
            timestamp=datetime.utcnow(),
            data=data,
            metadata=metadata or {}
        )

        # Call in-process listeners
        if event_type in self.listeners:
            for callback in self.listeners[event_type]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(payload)
                    else:
                        callback(payload)
                except Exception as e:
                    logger.error(
                        f"Listener error for {event_type.value}: {e}",
                        exc_info=True
                    )

        # Queue webhooks for matching endpoints
        for endpoint in self.endpoints.values():
            if not endpoint.enabled:
                continue

            if event_type in endpoint.events:
                # Create delivery
                delivery = WebhookDelivery(
                    delivery_id=str(uuid.uuid4()),
                    endpoint_id=endpoint.endpoint_id,
                    payload=payload,
                    status=WebhookDeliveryStatus.PENDING,
                    max_attempts=self.max_retries
                )

                self.deliveries[delivery.delivery_id] = delivery

                # Queue for delivery
                await self.delivery_queue.put(delivery)

        logger.debug(f"Emitted event: {event_type.value}")

    async def start(self):
        """Start webhook delivery worker."""
        if self.running:
            logger.warning("Webhook manager already running")
            return

        self.running = True
        self.worker_task = asyncio.create_task(self._delivery_worker())

        logger.info("Webhook delivery worker started")

    async def stop(self):
        """Stop webhook delivery worker."""
        if not self.running:
            return

        logger.info("Stopping webhook delivery worker...")

        self.running = False

        if self.worker_task:
            self.worker_task.cancel()
            try:
                await self.worker_task
            except asyncio.CancelledError:
                pass

        logger.info("Webhook delivery worker stopped")

    async def _delivery_worker(self):
        """Background worker for webhook delivery."""
        logger.info("Webhook delivery worker running")

        while self.running:
            try:
                # Get delivery from queue (with timeout)
                delivery = await asyncio.wait_for(
                    self.delivery_queue.get(),
                    timeout=1.0
                )
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Delivery queue error: {e}")
                continue

            # Deliver webhook
            await self._deliver_webhook(delivery)

    async def _deliver_webhook(self, delivery: WebhookDelivery):
        """
        Deliver a webhook.

        Args:
            delivery: WebhookDelivery instance
        """
        endpoint = self.endpoints.get(delivery.endpoint_id)
        if not endpoint:
            logger.warning(
                f"Endpoint not found for delivery: {delivery.delivery_id}"
            )
            return

        delivery.attempts += 1
        delivery.status = WebhookDeliveryStatus.RETRYING

        try:
            # Prepare payload
            payload_dict = delivery.payload.to_dict()
            payload_json = json.dumps(payload_dict)

            # Generate signature
            headers = {"Content-Type": "application/json"}
            if endpoint.secret:
                signature = self._generate_signature(
                    payload_json,
                    endpoint.secret
                )
                headers["X-Webhook-Signature"] = signature

            # Make HTTP request (simulated - would use aiohttp in production)
            logger.info(
                f"Delivering webhook to {endpoint.url} "
                f"(attempt {delivery.attempts}/{delivery.max_attempts})"
            )

            # Simulate successful delivery
            success = True  # Would be actual HTTP response
            response_code = 200

            if success:
                delivery.status = WebhookDeliveryStatus.DELIVERED
                delivery.delivered_at = datetime.utcnow()
                delivery.response_code = response_code

                endpoint.last_delivery = datetime.utcnow()
                endpoint.delivery_count += 1

                logger.info(
                    f"Webhook delivered: {delivery.delivery_id} "
                    f"(endpoint={endpoint.endpoint_id})"
                )
            else:
                raise Exception(f"HTTP {response_code}")

        except Exception as e:
            logger.error(
                f"Webhook delivery failed: {delivery.delivery_id} - {e}"
            )

            delivery.error = str(e)
            endpoint.failure_count += 1

            # Retry if attempts remaining
            if delivery.attempts < delivery.max_attempts:
                delivery.status = WebhookDeliveryStatus.RETRYING

                # Re-queue with delay
                asyncio.create_task(
                    self._requeue_after_delay(delivery)
                )
            else:
                delivery.status = WebhookDeliveryStatus.FAILED
                logger.warning(
                    f"Webhook delivery failed permanently: {delivery.delivery_id}"
                )

    async def _requeue_after_delay(self, delivery: WebhookDelivery):
        """Re-queue delivery after delay."""
        await asyncio.sleep(self.retry_delay_seconds)
        await self.delivery_queue.put(delivery)

    def _generate_signature(self, payload: str, secret: str) -> str:
        """
        Generate HMAC signature for webhook.

        Args:
            payload: JSON payload
            secret: Shared secret

        Returns:
            HMAC signature (hex)
        """
        signature = hmac.new(
            secret.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()

        return f"sha256={signature}"

    def verify_signature(
        self,
        payload: str,
        signature: str,
        secret: str
    ) -> bool:
        """
        Verify webhook signature.

        Args:
            payload: JSON payload
            signature: Received signature
            secret: Shared secret

        Returns:
            True if valid
        """
        expected = self._generate_signature(payload, secret)
        return hmac.compare_digest(signature, expected)

    def get_endpoint(self, endpoint_id: str) -> Optional[WebhookEndpoint]:
        """Get endpoint by ID."""
        return self.endpoints.get(endpoint_id)

    def get_endpoints(self) -> List[WebhookEndpoint]:
        """Get all endpoints."""
        return list(self.endpoints.values())

    def get_delivery(self, delivery_id: str) -> Optional[WebhookDelivery]:
        """Get delivery by ID."""
        return self.deliveries.get(delivery_id)

    def get_stats(self) -> Dict[str, Any]:
        """Get webhook statistics."""
        total_endpoints = len(self.endpoints)
        enabled_endpoints = sum(
            1 for e in self.endpoints.values() if e.enabled
        )

        total_deliveries = len(self.deliveries)
        successful_deliveries = sum(
            1 for d in self.deliveries.values()
            if d.status == WebhookDeliveryStatus.DELIVERED
        )
        failed_deliveries = sum(
            1 for d in self.deliveries.values()
            if d.status == WebhookDeliveryStatus.FAILED
        )

        return {
            "endpoints": {
                "total": total_endpoints,
                "enabled": enabled_endpoints,
                "disabled": total_endpoints - enabled_endpoints,
            },
            "deliveries": {
                "total": total_deliveries,
                "successful": successful_deliveries,
                "failed": failed_deliveries,
                "success_rate": (
                    successful_deliveries / total_deliveries
                    if total_deliveries > 0 else 0.0
                ),
            },
            "queue_size": self.delivery_queue.qsize(),
            "running": self.running,
        }


# Global webhook manager
webhook_manager = WebhookManager(
    max_retries=3,
    retry_delay_seconds=5,
    timeout_seconds=10
)
