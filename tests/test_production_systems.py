"""
Comprehensive Tests for Production Systems
===========================================

Tests for all enterprise production features:
- Resilience (circuit breakers, retry, fallback)
- Configuration management
- Multi-tenancy
- RBAC
- Load balancing
- GraphQL API
- Message queuing
- Metrics export
- SDK client
"""

import pytest
import asyncio
from datetime import datetime, timedelta


# Resilience Tests
class TestCircuitBreaker:
    """Test circuit breaker functionality."""

    @pytest.mark.asyncio
    async def test_circuit_breaker_closed_state(self):
        """Test circuit breaker in closed state allows requests."""
        from resilience import CircuitBreaker, CircuitBreakerConfig

        breaker = CircuitBreaker(name="test", config=CircuitBreakerConfig(failure_threshold=3))

        # Should allow request in closed state
        async with breaker:
            result = "success"

        assert result == "success"
        assert breaker.stats.total_calls == 1
        assert breaker.stats.total_successes == 1

    @pytest.mark.asyncio
    async def test_circuit_breaker_opens_on_failures(self):
        """Test circuit breaker opens after threshold failures."""
        from resilience import CircuitBreaker, CircuitBreakerConfig, CircuitBreakerOpen, CircuitState

        breaker = CircuitBreaker(name="test", config=CircuitBreakerConfig(
            failure_threshold=3,
            tracked_exceptions=[ValueError]
        ))

        # Cause failures
        for i in range(3):
            try:
                async with breaker:
                    raise ValueError("Test error")
            except ValueError:
                pass

        # Circuit should be open now
        assert breaker.stats.state == CircuitState.OPEN

        # Next request should be rejected immediately
        with pytest.raises(CircuitBreakerOpen):
            async with breaker:
                pass

    @pytest.mark.asyncio
    async def test_retry_with_exponential_backoff(self):
        """Test retry with exponential backoff."""
        from resilience import Retry, ExponentialBackoff

        attempts = []

        @Retry(strategy=ExponentialBackoff(max_retries=3, base_delay=0.01))
        async def flaky_function():
            attempts.append(len(attempts))
            if len(attempts) < 3:
                raise ValueError("Not yet")
            return "success"

        result = await flaky_function()

        assert result == "success"
        assert len(attempts) == 3  # Failed twice, succeeded on third

    @pytest.mark.asyncio
    async def test_fallback_on_error(self):
        """Test fallback triggers on error."""
        from resilience import Fallback, FallbackConfig

        @Fallback(config=FallbackConfig(fallback_value="fallback_result"))
        async def failing_function():
            raise RuntimeError("Always fails")

        result = await failing_function()
        assert result == "fallback_result"


# Configuration Tests
class TestConfiguration:
    """Test configuration management."""

    def test_config_manager_default_values(self):
        """Test configuration with default values."""
        from config import ConfigManager, Environment

        manager = ConfigManager()
        config = manager.build()

        assert config.environment == Environment.DEVELOPMENT
        assert config.debug == True
        assert config.server.port == 8000

    def test_config_manager_from_dict(self):
        """Test configuration from dictionary."""
        from config import ConfigManager

        test_config = {
            "environment": "production",
            "debug": False,
            "server": {
                "host": "0.0.0.0",
                "port": 9000,
                "workers": 8
            }
        }

        manager = ConfigManager()
        manager.load_from_dict(test_config)
        config = manager.build()

        assert config.environment.value == "production"
        assert config.debug == False
        assert config.server.port == 9000
        assert config.server.workers == 8

    def test_config_validation_production(self):
        """Test production configuration validation."""
        from config import ConfigManager, Environment

        manager = ConfigManager()
        manager.load_from_dict({
            "environment": "production",
            "debug": True,  # Should fail validation
            "security": {"jwt_secret": ""}  # Should fail validation
        })
        config = manager.build()

        errors = config.validate()
        assert len(errors) > 0
        assert any("debug" in err.lower() for err in errors)
        assert any("jwt" in err.lower() for err in errors)


# Multi-Tenancy Tests
class TestMultiTenancy:
    """Test multi-tenancy functionality."""

    @pytest.mark.asyncio
    async def test_create_tenant(self):
        """Test tenant creation."""
        from tenancy import TenantManager, TenantTier

        manager = TenantManager()
        tenant = await manager.create_tenant(
            name="Test Corp",
            email="test@example.com",
            tier=TenantTier.PRO
        )

        assert tenant.name == "Test Corp"
        assert tenant.email == "test@example.com"
        assert tenant.tier == TenantTier.PRO
        assert len(tenant.api_keys) == 1

    @pytest.mark.asyncio
    async def test_tenant_quota_enforcement(self):
        """Test tenant quota enforcement."""
        from tenancy import TenantManager, TenantTier

        manager = TenantManager()
        tenant = await manager.create_tenant(
            name="Test Corp",
            email="test@example.com",
            tier=TenantTier.FREE
        )

        # Simulate reaching quota
        if tenant.usage:
            tenant.usage.requests_hour = tenant.quota.max_requests_per_hour

        can_request, reason = tenant.can_make_request()
        assert not can_request
        assert "hourly" in reason.lower()

    @pytest.mark.asyncio
    async def test_tenant_tier_upgrade(self):
        """Test tenant tier upgrade."""
        from tenancy import TenantManager, TenantTier, TIER_QUOTAS

        manager = TenantManager()
        tenant = await manager.create_tenant(
            name="Test Corp",
            email="test@example.com",
            tier=TenantTier.FREE
        )

        # Upgrade to PRO
        await manager.upgrade_tier(tenant.tenant_id, TenantTier.PRO)

        # Get updated tenant
        updated = await manager.get_tenant(tenant.tenant_id)
        assert updated.tier == TenantTier.PRO
        assert updated.quota.max_requests_per_day == TIER_QUOTAS[TenantTier.PRO].max_requests_per_day


# RBAC Tests
class TestRBAC:
    """Test role-based access control."""

    @pytest.mark.asyncio
    async def test_user_with_role_has_permissions(self):
        """Test user with role has appropriate permissions."""
        from rbac import AccessControl, User, Permission, Resource, ResourceType

        access_control = AccessControl()

        # Create user with developer role
        user = User(user_id="user1", username="dev", roles=["developer"])
        await access_control.store.create_user(user)

        # Check permission
        resource = Resource(ResourceType.MODEL, "gpt-4")
        has_permission = await access_control.check_permission(
            "user1",
            Permission.MODEL_EXECUTE,
            resource
        )

        assert has_permission == True

    @pytest.mark.asyncio
    async def test_user_without_role_denied(self):
        """Test user without appropriate role is denied."""
        from rbac import AccessControl, User, Permission, Resource, ResourceType

        access_control = AccessControl()

        # Create user with readonly role
        user = User(user_id="user2", username="readonly_user", roles=["readonly"])
        await access_control.store.create_user(user)

        # Try to execute (should be denied)
        resource = Resource(ResourceType.MODEL, "gpt-4")
        has_permission = await access_control.check_permission(
            "user2",
            Permission.MODEL_EXECUTE,
            resource
        )

        assert has_permission == False

    @pytest.mark.asyncio
    async def test_admin_has_all_permissions(self):
        """Test admin role has all permissions."""
        from rbac import AccessControl, User, Permission, Resource, ResourceType

        access_control = AccessControl()

        # Create admin user
        user = User(user_id="admin1", username="admin", roles=["admin"])
        await access_control.store.create_user(user)

        # Admin should have any permission
        resource = Resource(ResourceType.SYSTEM, "config")
        has_permission = await access_control.check_permission(
            "admin1",
            Permission.SYSTEM_ADMIN,
            resource
        )

        assert has_permission == True


# Load Balancer Tests
class TestLoadBalancer:
    """Test load balancing functionality."""

    @pytest.mark.asyncio
    async def test_round_robin_selection(self):
        """Test round-robin backend selection."""
        from loadbalancer import LoadBalancer, Backend, LoadBalancingAlgorithm

        lb = LoadBalancer(algorithm=LoadBalancingAlgorithm.ROUND_ROBIN)

        # Add backends
        lb.add_backend(Backend(backend_id="b1", name="Backend 1", endpoint="http://b1"))
        lb.add_backend(Backend(backend_id="b2", name="Backend 2", endpoint="http://b2"))
        lb.add_backend(Backend(backend_id="b3", name="Backend 3", endpoint="http://b3"))

        # Select backends
        selections = []
        for _ in range(6):
            backend = await lb.select_backend()
            selections.append(backend.backend_id)

        # Should rotate through backends
        assert selections == ["b1", "b2", "b3", "b1", "b2", "b3"]

    @pytest.mark.asyncio
    async def test_least_connections_selection(self):
        """Test least connections backend selection."""
        from loadbalancer import LoadBalancer, Backend, LoadBalancingAlgorithm

        lb = LoadBalancer(algorithm=LoadBalancingAlgorithm.LEAST_CONNECTIONS)

        # Add backends with different connection counts
        b1 = Backend(backend_id="b1", name="Backend 1", endpoint="http://b1")
        b1.metrics.active_connections = 5
        lb.add_backend(b1)

        b2 = Backend(backend_id="b2", name="Backend 2", endpoint="http://b2")
        b2.metrics.active_connections = 2
        lb.add_backend(b2)

        # Should select b2 (fewer connections)
        backend = await lb.select_backend()
        assert backend.backend_id == "b2"

    @pytest.mark.asyncio
    async def test_unhealthy_backend_excluded(self):
        """Test unhealthy backends are not selected."""
        from loadbalancer import LoadBalancer, Backend, LoadBalancingAlgorithm, BackendStatus

        lb = LoadBalancer(algorithm=LoadBalancingAlgorithm.ROUND_ROBIN)

        # Add healthy backend
        b1 = Backend(backend_id="b1", name="Backend 1", endpoint="http://b1")
        lb.add_backend(b1)

        # Add unhealthy backend
        b2 = Backend(backend_id="b2", name="Backend 2", endpoint="http://b2")
        b2.status = BackendStatus.UNHEALTHY
        lb.add_backend(b2)

        # Should only select healthy backend
        for _ in range(3):
            backend = await lb.select_backend()
            assert backend.backend_id == "b1"


# GraphQL Tests
class TestGraphQL:
    """Test GraphQL API functionality."""

    def test_schema_generation(self):
        """Test GraphQL schema generation."""
        from graphql_api import TSMSchema

        schema_builder = TSMSchema()
        sdl = schema_builder.get_sdl()

        # Check for key types
        assert "type Query" in sdl
        assert "type Mutation" in sdl
        assert "type Model" in sdl
        assert "type Request" in sdl
        assert "type Tenant" in sdl

    def test_data_loader_batching(self):
        """Test DataLoader batches requests."""
        from graphql_api import DataLoader

        batch_calls = []

        async def batch_load(keys):
            batch_calls.append(len(keys))
            return [f"result_{k}" for k in keys]

        loader = DataLoader(batch_load)

        async def test():
            # Request multiple items
            results = await asyncio.gather(
                loader.load("a"),
                loader.load("b"),
                loader.load("c"),
            )

            assert results == ["result_a", "result_b", "result_c"]
            assert len(batch_calls) == 1  # Should batch into single call
            assert batch_calls[0] == 3  # Should load all 3 keys

        asyncio.run(test())


# Message Queue Tests
class TestMessageQueue:
    """Test message queue functionality."""

    @pytest.mark.asyncio
    async def test_publish_and_consume(self):
        """Test message publishing and consuming."""
        from messaging import InMemoryBroker, Queue, Message, MessagePriority

        broker = InMemoryBroker()
        await broker.connect()

        # Declare queue
        queue = Queue(name="test_queue")
        await broker.declare_queue(queue)

        # Publish message
        message = Message(
            message_id="msg1",
            queue_name="test_queue",
            payload={"test": "data"},
            priority=MessagePriority.NORMAL
        )
        await broker.publish(message)

        # Consume message
        received_messages = []

        async def callback(msg):
            received_messages.append(msg)

        await broker.consume("test_queue", callback, auto_ack=True)

        # Wait for processing
        await asyncio.sleep(0.2)

        assert len(received_messages) == 1
        assert received_messages[0].payload["test"] == "data"

        await broker.disconnect()

    @pytest.mark.asyncio
    async def test_priority_queue(self):
        """Test priority-based message ordering."""
        from messaging import InMemoryBroker, Queue, Message, MessagePriority

        broker = InMemoryBroker()
        await broker.connect()

        queue = Queue(name="priority_queue")
        await broker.declare_queue(queue)

        # Publish messages with different priorities
        await broker.publish(Message(
            message_id="low",
            queue_name="priority_queue",
            payload={"priority": "low"},
            priority=MessagePriority.LOW
        ))

        await broker.publish(Message(
            message_id="high",
            queue_name="priority_queue",
            payload={"priority": "high"},
            priority=MessagePriority.HIGH
        ))

        await broker.publish(Message(
            message_id="critical",
            queue_name="priority_queue",
            payload={"priority": "critical"},
            priority=MessagePriority.CRITICAL
        ))

        # Consume and check order
        received = []

        async def callback(msg):
            received.append(msg.payload["priority"])

        await broker.consume("priority_queue", callback, auto_ack=True)
        await asyncio.sleep(0.3)

        # Should receive in priority order
        assert received == ["critical", "high", "low"]

        await broker.disconnect()


# Metrics Export Tests
class TestMetricsExport:
    """Test metrics export functionality."""

    @pytest.mark.asyncio
    async def test_counter_metric(self):
        """Test counter metric."""
        from metrics_export import Metric, MetricType

        counter = Metric(name="test_counter", type=MetricType.COUNTER)
        counter.increment(5)

        assert counter.value == 5

        counter.increment(3)
        assert counter.value == 8

    @pytest.mark.asyncio
    async def test_histogram_metric(self):
        """Test histogram metric."""
        from metrics_export import Metric, MetricType

        histogram = Metric(name="test_histogram", type=MetricType.HISTOGRAM)

        # Observe values
        histogram.observe(0.1)
        histogram.observe(0.5)
        histogram.observe(1.2)

        assert len(histogram.values) == 3
        assert sum(histogram.values) == pytest.approx(1.8)

    @pytest.mark.asyncio
    async def test_prometheus_exporter(self):
        """Test Prometheus format export."""
        from metrics_export import PrometheusExporter, Metric, MetricType

        exporter = PrometheusExporter()

        metrics = [
            Metric(name="requests_total", type=MetricType.COUNTER, value=100),
            Metric(name="cpu_usage", type=MetricType.GAUGE, value=75.5),
        ]

        await exporter.export(metrics)
        output = exporter.get_metrics_text()

        assert "requests_total 100" in output
        assert "cpu_usage 75.5" in output
        assert "# TYPE requests_total counter" in output
        assert "# TYPE cpu_usage gauge" in output


# SDK Tests
class TestSDK:
    """Test Python SDK client."""

    def test_execute_options_creation(self):
        """Test ExecuteOptions creation."""
        from sdk.python.client import ExecuteOptions, ModelProvider

        options = ExecuteOptions(
            model="gpt-4",
            provider=ModelProvider.OPENAI,
            temperature=0.8,
            max_tokens=1000
        )

        assert options.model == "gpt-4"
        assert options.provider == ModelProvider.OPENAI
        assert options.temperature == 0.8
        assert options.max_tokens == 1000

    def test_response_from_dict(self):
        """Test Response deserialization."""
        from sdk.python.client import Response

        data = {
            "request_id": "req123",
            "output": "Test output",
            "model": "gpt-4",
            "provider": "openai",
            "tokens": 50,
            "cost": 0.001,
            "latency_ms": 500.0,
        }

        response = Response.from_dict(data)

        assert response.request_id == "req123"
        assert response.output == "Test output"
        assert response.model == "gpt-4"
        assert response.tokens == 50


# Integration Tests
class TestIntegration:
    """Integration tests for complete workflows."""

    @pytest.mark.asyncio
    async def test_full_request_flow_with_resilience(self):
        """Test complete request flow with resilience features."""
        from resilience import CircuitBreaker, Retry, ExponentialBackoff

        attempts = []

        @Retry(strategy=ExponentialBackoff(max_retries=2, base_delay=0.01))
        async def execute_with_retry():
            attempts.append(1)
            if len(attempts) < 2:
                raise ValueError("Temporary error")
            return "success"

        breaker = CircuitBreaker(name="test")

        async with breaker:
            result = await execute_with_retry()

        assert result == "success"
        assert len(attempts) == 2
        assert breaker.stats.total_successes == 1

    @pytest.mark.asyncio
    async def test_tenant_with_rbac(self):
        """Test tenant isolation with RBAC."""
        from tenancy import TenantManager, TenantTier
        from rbac import AccessControl, User, Permission, Resource, ResourceType

        # Create tenant
        tenant_mgr = TenantManager()
        tenant = await tenant_mgr.create_tenant(
            name="Enterprise Corp",
            email="admin@enterprise.com",
            tier=TenantTier.ENTERPRISE
        )

        # Create user in tenant
        access_control = AccessControl()
        user = User(
            user_id="user1",
            username="developer",
            tenant_id=tenant.tenant_id,
            roles=["developer"]
        )
        await access_control.store.create_user(user)

        # Check quota
        can_request, _ = tenant.can_make_request()
        assert can_request == True

        # Check permission
        resource = Resource(ResourceType.MODEL, "gpt-4")
        has_permission = await access_control.check_permission(
            "user1",
            Permission.MODEL_EXECUTE,
            resource
        )
        assert has_permission == True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
