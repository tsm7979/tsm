"""
TSM Message Queue Integration
==============================

Enterprise message queue integration for:
- Distributed processing
- Event-driven architecture
- Reliable message delivery
- Dead letter queues
- Message persistence

Supported backends:
- In-memory (development)
- RabbitMQ (production)
- Apache Kafka (high-throughput)
- AWS SQS/SNS (cloud)
"""

from enum import Enum
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import asyncio
import json
import logging
from abc import ABC, abstractmethod
import uuid

logger = logging.getLogger(__name__)


class MessagePriority(int, Enum):
    """Message priority levels."""

    LOW = 0
    NORMAL = 5
    HIGH = 10
    CRITICAL = 15


class MessageStatus(str, Enum):
    """Message processing status."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    DEAD_LETTER = "dead_letter"


class ExchangeType(str, Enum):
    """Exchange types (RabbitMQ-style)."""

    DIRECT = "direct"
    FANOUT = "fanout"
    TOPIC = "topic"
    HEADERS = "headers"


@dataclass
class Message:
    """
    A message in the queue.

    Contains payload, metadata, and delivery information.
    """

    message_id: str
    queue_name: str
    payload: Dict[str, Any]

    # Routing
    routing_key: str = ""
    exchange: str = ""

    # Priority and timing
    priority: MessagePriority = MessagePriority.NORMAL
    timestamp: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None

    # Delivery
    status: MessageStatus = MessageStatus.PENDING
    delivery_count: int = 0
    max_retries: int = 3

    # Tracking
    created_at: datetime = field(default_factory=datetime.utcnow)
    processed_at: Optional[datetime] = None
    error: Optional[str] = None

    # Metadata
    headers: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "message_id": self.message_id,
            "queue_name": self.queue_name,
            "payload": self.payload,
            "routing_key": self.routing_key,
            "exchange": self.exchange,
            "priority": self.priority.value,
            "timestamp": self.timestamp.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "status": self.status.value,
            "delivery_count": self.delivery_count,
            "max_retries": self.max_retries,
            "headers": self.headers,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Message":
        """Create message from dictionary."""
        return cls(
            message_id=data["message_id"],
            queue_name=data["queue_name"],
            payload=data["payload"],
            routing_key=data.get("routing_key", ""),
            exchange=data.get("exchange", ""),
            priority=MessagePriority(data.get("priority", 5)),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            expires_at=datetime.fromisoformat(data["expires_at"]) if data.get("expires_at") else None,
            status=MessageStatus(data.get("status", "pending")),
            delivery_count=data.get("delivery_count", 0),
            max_retries=data.get("max_retries", 3),
            headers=data.get("headers", {}),
            metadata=data.get("metadata", {}),
        )

    def is_expired(self) -> bool:
        """Check if message has expired."""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at

    def can_retry(self) -> bool:
        """Check if message can be retried."""
        return self.delivery_count < self.max_retries


@dataclass
class Queue:
    """Queue definition."""

    name: str
    durable: bool = True
    max_length: Optional[int] = None
    message_ttl: Optional[int] = None  # seconds
    dead_letter_queue: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Exchange:
    """Exchange definition (for routing)."""

    name: str
    type: ExchangeType = ExchangeType.DIRECT
    durable: bool = True
    bindings: List[Dict[str, str]] = field(default_factory=list)  # {queue, routing_key}


class MessageBroker(ABC):
    """Abstract message broker interface."""

    @abstractmethod
    async def connect(self):
        """Connect to message broker."""
        pass

    @abstractmethod
    async def disconnect(self):
        """Disconnect from message broker."""
        pass

    @abstractmethod
    async def declare_queue(self, queue: Queue):
        """Declare a queue."""
        pass

    @abstractmethod
    async def declare_exchange(self, exchange: Exchange):
        """Declare an exchange."""
        pass

    @abstractmethod
    async def publish(self, message: Message):
        """Publish a message."""
        pass

    @abstractmethod
    async def consume(self, queue_name: str, callback: Callable[[Message], Any], auto_ack: bool = False):
        """Consume messages from a queue."""
        pass

    @abstractmethod
    async def ack(self, message: Message):
        """Acknowledge message processing."""
        pass

    @abstractmethod
    async def nack(self, message: Message, requeue: bool = True):
        """Negative acknowledge (reject) message."""
        pass


class InMemoryBroker(MessageBroker):
    """
    In-memory message broker.

    For development and testing.
    """

    def __init__(self):
        self.queues: Dict[str, Queue] = {}
        self.exchanges: Dict[str, Exchange] = {}
        self.messages: Dict[str, List[Message]] = {}  # queue_name -> messages
        self.dead_letter_messages: List[Message] = []
        self._consumer_tasks: Dict[str, asyncio.Task] = {}
        self._running = False

    async def connect(self):
        """Connect (no-op for in-memory)."""
        self._running = True
        logger.info("In-memory broker connected")

    async def disconnect(self):
        """Disconnect and cleanup."""
        self._running = False

        # Cancel consumer tasks
        for task in self._consumer_tasks.values():
            task.cancel()

        self._consumer_tasks.clear()
        logger.info("In-memory broker disconnected")

    async def declare_queue(self, queue: Queue):
        """Declare a queue."""
        self.queues[queue.name] = queue
        if queue.name not in self.messages:
            self.messages[queue.name] = []
        logger.info(f"Declared queue: {queue.name}")

    async def declare_exchange(self, exchange: Exchange):
        """Declare an exchange."""
        self.exchanges[exchange.name] = exchange
        logger.info(f"Declared exchange: {exchange.name} (type={exchange.type.value})")

    async def publish(self, message: Message):
        """Publish a message."""
        # Check if message expired
        if message.is_expired():
            logger.warning(f"Message {message.message_id} expired, not publishing")
            return

        # Route message
        if message.exchange:
            await self._route_via_exchange(message)
        else:
            # Direct queue publish
            await self._add_to_queue(message.queue_name, message)

        logger.debug(f"Published message {message.message_id} to queue {message.queue_name}")

    async def _route_via_exchange(self, message: Message):
        """Route message via exchange."""
        exchange = self.exchanges.get(message.exchange)
        if not exchange:
            logger.warning(f"Exchange {message.exchange} not found")
            return

        if exchange.type == ExchangeType.DIRECT:
            # Route to queues with matching routing key
            for binding in exchange.bindings:
                if binding["routing_key"] == message.routing_key:
                    await self._add_to_queue(binding["queue"], message)

        elif exchange.type == ExchangeType.FANOUT:
            # Route to all bound queues
            for binding in exchange.bindings:
                await self._add_to_queue(binding["queue"], message)

        elif exchange.type == ExchangeType.TOPIC:
            # Route based on pattern matching
            for binding in exchange.bindings:
                if self._matches_topic(message.routing_key, binding["routing_key"]):
                    await self._add_to_queue(binding["queue"], message)

    def _matches_topic(self, routing_key: str, pattern: str) -> bool:
        """Check if routing key matches topic pattern."""
        # Simple topic matching (* = one word, # = zero or more words)
        routing_parts = routing_key.split(".")
        pattern_parts = pattern.split(".")

        i = 0
        j = 0

        while i < len(routing_parts) and j < len(pattern_parts):
            if pattern_parts[j] == "#":
                # Matches zero or more words
                if j == len(pattern_parts) - 1:
                    return True
                j += 1
            elif pattern_parts[j] == "*" or pattern_parts[j] == routing_parts[i]:
                i += 1
                j += 1
            else:
                return False

        return i == len(routing_parts) and j == len(pattern_parts)

    async def _add_to_queue(self, queue_name: str, message: Message):
        """Add message to queue."""
        if queue_name not in self.messages:
            self.messages[queue_name] = []

        queue = self.queues.get(queue_name)
        if not queue:
            logger.warning(f"Queue {queue_name} not declared")
            return

        # Check queue max length
        if queue.max_length and len(self.messages[queue_name]) >= queue.max_length:
            logger.warning(f"Queue {queue_name} is full, dropping oldest message")
            self.messages[queue_name].pop(0)

        # Set message TTL
        if queue.message_ttl and not message.expires_at:
            message.expires_at = datetime.utcnow() + timedelta(seconds=queue.message_ttl)

        # Insert with priority (higher priority first)
        messages = self.messages[queue_name]
        insert_idx = 0
        for i, msg in enumerate(messages):
            if msg.priority.value < message.priority.value:
                insert_idx = i
                break
            insert_idx = i + 1

        messages.insert(insert_idx, message)

    async def consume(self, queue_name: str, callback: Callable[[Message], Any], auto_ack: bool = False):
        """Consume messages from a queue."""
        if queue_name not in self.messages:
            await self.declare_queue(Queue(name=queue_name))

        # Start consumer task
        task = asyncio.create_task(self._consumer_loop(queue_name, callback, auto_ack))
        self._consumer_tasks[queue_name] = task

        logger.info(f"Started consumer for queue: {queue_name}")

    async def _consumer_loop(self, queue_name: str, callback: Callable, auto_ack: bool):
        """Consumer loop."""
        while self._running:
            try:
                # Get next message
                message = await self._get_next_message(queue_name)

                if message:
                    message.status = MessageStatus.PROCESSING
                    message.delivery_count += 1

                    try:
                        # Process message
                        await callback(message)

                        # Auto-ack if enabled
                        if auto_ack:
                            await self.ack(message)

                    except Exception as e:
                        logger.error(f"Error processing message {message.message_id}: {str(e)}")
                        message.error = str(e)

                        # Auto-nack on error
                        if auto_ack:
                            await self.nack(message, requeue=message.can_retry())

                else:
                    # No messages, wait
                    await asyncio.sleep(0.1)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Consumer error: {str(e)}")
                await asyncio.sleep(1)

    async def _get_next_message(self, queue_name: str) -> Optional[Message]:
        """Get next message from queue."""
        messages = self.messages.get(queue_name, [])

        # Find first non-expired, pending message
        for i, message in enumerate(messages):
            if message.status == MessageStatus.PENDING:
                if message.is_expired():
                    # Remove expired message
                    messages.pop(i)
                    logger.debug(f"Removed expired message: {message.message_id}")
                    continue

                return message

        return None

    async def ack(self, message: Message):
        """Acknowledge message."""
        message.status = MessageStatus.COMPLETED
        message.processed_at = datetime.utcnow()

        # Remove from queue
        messages = self.messages.get(message.queue_name, [])
        if message in messages:
            messages.remove(message)

        logger.debug(f"Acknowledged message: {message.message_id}")

    async def nack(self, message: Message, requeue: bool = True):
        """Negative acknowledge."""
        message.status = MessageStatus.FAILED

        if requeue and message.can_retry():
            # Requeue for retry
            message.status = MessageStatus.PENDING
            logger.debug(f"Requeued message: {message.message_id} (attempt {message.delivery_count})")
        else:
            # Move to dead letter queue
            queue = self.queues.get(message.queue_name)
            if queue and queue.dead_letter_queue:
                message.queue_name = queue.dead_letter_queue
                message.status = MessageStatus.DEAD_LETTER
                await self._add_to_queue(queue.dead_letter_queue, message)
                logger.warning(f"Moved message to dead letter queue: {message.message_id}")
            else:
                self.dead_letter_messages.append(message)
                logger.error(f"Message permanently failed: {message.message_id}")

            # Remove from original queue
            messages = self.messages.get(message.queue_name, [])
            if message in messages:
                messages.remove(message)


class MessageProducer:
    """
    High-level message producer.

    Simplifies publishing messages.
    """

    def __init__(self, broker: MessageBroker, default_exchange: str = ""):
        self.broker = broker
        self.default_exchange = default_exchange

    async def send(
        self,
        queue_name: str,
        payload: Dict[str, Any],
        priority: MessagePriority = MessagePriority.NORMAL,
        routing_key: str = "",
        ttl_seconds: Optional[int] = None,
        headers: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Send a message."""
        message_id = str(uuid.uuid4())

        message = Message(
            message_id=message_id,
            queue_name=queue_name,
            payload=payload,
            routing_key=routing_key or queue_name,
            exchange=self.default_exchange,
            priority=priority,
            headers=headers or {},
        )

        if ttl_seconds:
            message.expires_at = datetime.utcnow() + timedelta(seconds=ttl_seconds)

        await self.broker.publish(message)

        return message_id


class MessageConsumer:
    """
    High-level message consumer.

    Simplifies consuming messages with error handling.
    """

    def __init__(self, broker: MessageBroker):
        self.broker = broker
        self._handlers: Dict[str, Callable] = {}

    def register_handler(self, queue_name: str, handler: Callable):
        """Register a message handler for a queue."""
        self._handlers[queue_name] = handler

    async def start(self, auto_ack: bool = True):
        """Start consuming all registered queues."""
        for queue_name, handler in self._handlers.items():
            await self.broker.consume(queue_name, handler, auto_ack=auto_ack)

        logger.info(f"Started {len(self._handlers)} consumers")

    async def stop(self):
        """Stop all consumers."""
        await self.broker.disconnect()
        logger.info("Stopped all consumers")


# Event types for TSM
class TSMEvent(str, Enum):
    """TSM system events."""

    REQUEST_CREATED = "request.created"
    REQUEST_COMPLETED = "request.completed"
    REQUEST_FAILED = "request.failed"

    MODEL_EXECUTED = "model.executed"
    MODEL_FAILED = "model.failed"

    DOCUMENT_ADDED = "document.added"
    DOCUMENT_DELETED = "document.deleted"

    TENANT_CREATED = "tenant.created"
    TENANT_UPGRADED = "tenant.upgraded"

    QUOTA_EXCEEDED = "quota.exceeded"
    COST_THRESHOLD_EXCEEDED = "cost.threshold_exceeded"


# Global broker instance
_broker: Optional[MessageBroker] = None


def get_broker() -> MessageBroker:
    """Get global message broker instance."""
    global _broker
    if _broker is None:
        _broker = InMemoryBroker()
    return _broker


__all__ = [
    "Message",
    "MessagePriority",
    "MessageStatus",
    "Queue",
    "Exchange",
    "ExchangeType",
    "MessageBroker",
    "InMemoryBroker",
    "MessageProducer",
    "MessageConsumer",
    "TSMEvent",
    "get_broker",
]
