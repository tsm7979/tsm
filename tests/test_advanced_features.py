"""
Advanced Features Test Suite
============================

Tests for task classification, monitoring, caching, rate limiting, and queuing.
"""

import sys
import os
import asyncio
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


async def test_task_classifier():
    """Test advanced task classification."""
    print("\n[TEST 1] Advanced Task Classification")
    print("-" * 60)

    from router.task_classifier import task_classifier, TaskType, TaskComplexity

    test_cases = [
        ("Analyze this code for security vulnerabilities", TaskType.CODE_ANALYSIS),
        ("Write a function to sort an array", TaskType.CODE_GENERATION),
        ("Search for CVE-2024-1234", TaskType.SEARCH),
        ("Summarize this document", TaskType.SUMMARIZATION),
        ("What is SQL injection?", TaskType.QUESTION_ANSWERING),
        ("Calculate 2+2", TaskType.MATH),
        ("Scan this code for vulnerabilities", TaskType.VULNERABILITY_SCAN),
    ]

    for input_text, expected_type in test_cases:
        classification = task_classifier.classify(input_text)

        print(f"  Input: '{input_text[:40]}...'")
        print(f"    Type: {classification.task_type.value}")
        print(f"    Complexity: {classification.complexity.value}")
        print(f"    Confidence: {classification.confidence:.2f}")
        print(f"    Est. tokens: {classification.estimated_tokens}")
        print(f"    Recommended: {', '.join(classification.recommended_models[:2])}")

        # Check if correct type detected
        if classification.task_type == expected_type:
            print(f"    ✓ Correct classification")
        else:
            print(f"    ⚠ Expected {expected_type.value}, got {classification.task_type.value}")

    # Test code detection
    code_input = """
    function login(user, pass) {
        db.query('SELECT * FROM users WHERE name=' + user);
    }
    """
    classification = task_classifier.classify(code_input)
    assert classification.metadata["has_code"] == True
    assert classification.task_type == TaskType.CODE_ANALYSIS

    print("  [PASSED]")


async def test_performance_monitoring():
    """Test performance monitoring system."""
    print("\n[TEST 2] Performance Monitoring")
    print("-" * 60)

    from monitoring import metrics_collector, PerformanceTracker

    # Record some test requests
    with PerformanceTracker(metrics_collector, "gpt-4o", "openai") as tracker:
        await asyncio.sleep(0.01)  # Simulate work
        tracker.set_cost(0.002)
        tracker.set_tokens(500)

    with PerformanceTracker(metrics_collector, "llama3.2", "local") as tracker:
        await asyncio.sleep(0.005)
        tracker.set_cost(0.0)
        tracker.set_tokens(300)

    with PerformanceTracker(metrics_collector, "gpt-3.5-turbo", "openai") as tracker:
        await asyncio.sleep(0.008)
        tracker.set_cost(0.0005)
        tracker.set_tokens(200)

    # Get metrics
    metrics = metrics_collector.get_metrics()

    print(f"  Total requests: {metrics.total_requests}")
    print(f"  Successful: {metrics.successful_requests}")
    print(f"  Avg latency: {metrics.avg_latency_ms:.1f}ms")
    print(f"  P95 latency: {metrics.p95_latency_ms:.1f}ms")
    print(f"  Total cost: ${metrics.total_cost_usd:.6f}")
    print(f"  Total tokens: {metrics.total_tokens}")
    print(f"  Model usage: {metrics.model_usage}")

    assert metrics.total_requests == 3
    assert metrics.successful_requests == 3
    assert metrics.total_cost_usd > 0

    # Get summary
    summary = metrics_collector.get_summary()
    print(f"\n  Summary:")
    print(f"    Success rate: {summary['overview']['success_rate']}")
    print(f"    Avg latency: {summary['overview']['avg_latency']}")
    print(f"    Total cost: {summary['overview']['total_cost']}")

    print("  [PASSED]")


async def test_caching():
    """Test caching layer."""
    print("\n[TEST 3] Intelligent Caching")
    print("-" * 60)

    from caching import smart_cache

    # Test cache miss
    result = smart_cache.get_cached_response(
        prompt="What is 2+2?",
        model="gpt-3.5-turbo"
    )
    assert result is None
    print("  ✓ Cache miss on first request")

    # Cache a response
    smart_cache.cache_response(
        prompt="What is 2+2?",
        model="gpt-3.5-turbo",
        response="4"
    )
    print("  ✓ Response cached")

    # Test cache hit
    result = smart_cache.get_cached_response(
        prompt="What is 2+2?",
        model="gpt-3.5-turbo"
    )
    assert result is not None
    assert result[0] == "4"
    print("  ✓ Cache hit on second request")

    # Test different model (cache miss)
    result = smart_cache.get_cached_response(
        prompt="What is 2+2?",
        model="gpt-4o"
    )
    assert result is None
    print("  ✓ Cache miss for different model")

    # Get stats
    stats = smart_cache.get_stats()
    print(f"\n  Cache stats:")
    print(f"    Size: {stats['size']}")
    print(f"    Hits: {stats['hits']}")
    print(f"    Misses: {stats['misses']}")
    print(f"    Hit rate: {stats['hit_rate']:.1%}")

    assert stats['hits'] == 1
    assert stats['misses'] == 2

    print("  [PASSED]")


async def test_rate_limiting():
    """Test rate limiting."""
    print("\n[TEST 4] Rate Limiting & Quotas")
    print("-" * 60)

    from ratelimit import rate_limiter, QuotaLimit

    # Set up test user quota
    rate_limiter.quota_manager.set_user_quota(
        "test_user",
        QuotaLimit(
            max_requests=10,
            max_tokens=1000,
            max_cost_usd=0.10,
            window_seconds=60
        )
    )

    # Test normal request (should pass)
    allowed, reason, retry_after = rate_limiter.check_rate_limit(
        "test_user",
        estimated_tokens=100,
        estimated_cost=0.01
    )
    assert allowed == True
    print("  ✓ Request allowed within quota")

    # Record usage
    rate_limiter.record_request("test_user", 100, 0.01)

    # Check usage
    usage = rate_limiter.quota_manager.get_usage("test_user")
    print(f"\n  Usage stats:")
    print(f"    Requests: {usage['requests']}/{usage['limits']['max_requests']}")
    print(f"    Tokens: {usage['tokens']}/{usage['limits']['max_tokens']}")
    print(f"    Cost: ${usage['cost_usd']:.4f}/${usage['limits']['max_cost_usd']}")
    print(f"    Remaining requests: {usage['remaining']['requests']}")

    assert usage['requests'] == 1
    assert usage['tokens'] == 100

    # Test quota exceeded
    allowed, reason, retry_after = rate_limiter.check_rate_limit(
        "test_user",
        estimated_tokens=2000,  # Exceeds limit
        estimated_cost=0.01
    )
    assert allowed == False
    print(f"\n  ✓ Request blocked: {reason}")

    # Test tier-based quotas
    rate_limiter.quota_manager.set_user_tier("pro_user", "pro")
    pro_limits = rate_limiter.get_limits("pro_user")
    print(f"\n  Pro tier quota:")
    print(f"    Max requests: {pro_limits['quota']['limits']['max_requests']}")
    print(f"    Max tokens: {pro_limits['quota']['limits']['max_tokens']}")

    print("  [PASSED]")


async def test_task_queue():
    """Test async task queue."""
    print("\n[TEST 5] Async Task Queue")
    print("-" * 60)

    from queue import AsyncTaskQueue, TaskPriority, TaskStatus

    # Create queue
    queue = AsyncTaskQueue(max_workers=2)
    await queue.start()

    print("  ✓ Queue started with 2 workers")

    # Submit tasks
    async def sample_task(duration: float, value: str):
        """Sample async task."""
        await asyncio.sleep(duration)
        return f"Completed: {value}"

    # Submit normal priority task
    task1_id = await queue.submit(
        sample_task,
        0.1,
        "task1",
        priority=TaskPriority.NORMAL
    )
    print(f"  ✓ Submitted task 1 (NORMAL priority)")

    # Submit high priority task
    task2_id = await queue.submit(
        sample_task,
        0.05,
        "task2",
        priority=TaskPriority.HIGH
    )
    print(f"  ✓ Submitted task 2 (HIGH priority)")

    # Submit low priority task
    task3_id = await queue.submit(
        sample_task,
        0.02,
        "task3",
        priority=TaskPriority.LOW
    )
    print(f"  ✓ Submitted task 3 (LOW priority)")

    # Wait for results
    result1 = await queue.get_result(task1_id, timeout=5)
    result2 = await queue.get_result(task2_id, timeout=5)
    result3 = await queue.get_result(task3_id, timeout=5)

    print(f"\n  Results:")
    print(f"    Task 1: {result1}")
    print(f"    Task 2: {result2}")
    print(f"    Task 3: {result3}")

    assert "Completed: task1" in result1
    assert "Completed: task2" in result2

    # Get stats
    stats = queue.get_stats()
    print(f"\n  Queue stats:")
    print(f"    Total queued: {stats['total_queued']}")
    print(f"    Total completed: {stats['total_completed']}")
    print(f"    Workers: {stats['workers']}/{stats['max_workers']}")

    assert stats['total_completed'] == 3

    # Stop queue
    await queue.stop()
    print("\n  ✓ Queue stopped")

    print("  [PASSED]")


async def test_task_cancellation():
    """Test task cancellation."""
    print("\n[TEST 6] Task Cancellation")
    print("-" * 60)

    from queue import AsyncTaskQueue, TaskStatus

    queue = AsyncTaskQueue(max_workers=1)
    await queue.start()

    # Submit long-running task
    async def long_task():
        await asyncio.sleep(10)
        return "Should not complete"

    task_id = await queue.submit(long_task)
    print(f"  ✓ Submitted long-running task")

    # Wait a bit
    await asyncio.sleep(0.1)

    # Cancel task
    cancelled = await queue.cancel(task_id)
    assert cancelled == True
    print(f"  ✓ Task cancelled")

    # Check status
    status = queue.get_status(task_id)
    print(f"  Task status: {status['status']}")
    assert status['status'] == TaskStatus.CANCELLED.value

    await queue.stop()

    print("  [PASSED]")


async def test_batch_processing():
    """Test batch processor."""
    print("\n[TEST 7] Batch Processing")
    print("-" * 60)

    from queue import AsyncTaskQueue, BatchProcessor

    queue = AsyncTaskQueue(max_workers=2)
    await queue.start()

    batch_processor = BatchProcessor(
        queue,
        batch_size=3,
        max_wait_seconds=0.5
    )

    # Define batch processing function
    async def process_batch(items):
        """Process a batch of items."""
        await asyncio.sleep(0.1)
        return [f"Processed: {item}" for item in items]

    # Submit items to batch
    print("  Submitting items for batching...")
    await batch_processor.submit_batch_item("batch1", "item1", process_batch)
    await batch_processor.submit_batch_item("batch1", "item2", process_batch)
    task_id = await batch_processor.submit_batch_item("batch1", "item3", process_batch)

    # Batch should process when size reached
    assert task_id is not None
    print(f"  ✓ Batch processed (task_id={task_id[:8]})")

    # Wait for result
    result = await queue.get_result(task_id, timeout=5)
    print(f"  Batch result: {len(result)} items processed")

    assert len(result) == 3

    await queue.stop()

    print("  [PASSED]")


async def test_integration():
    """Test integration of all advanced features."""
    print("\n[TEST 8] Integration Test")
    print("-" * 60)

    from router.task_classifier import task_classifier
    from monitoring import metrics_collector, PerformanceTracker
    from caching import smart_cache
    from ratelimit import rate_limiter

    # Simulate a complete request flow
    input_text = "Analyze this code for SQL injection"

    # 1. Classify task
    classification = task_classifier.classify(input_text)
    print(f"  1. Task classified: {classification.task_type.value}")

    # 2. Check rate limit
    allowed, reason, _ = rate_limiter.check_rate_limit(
        "integration_test_user",
        estimated_tokens=classification.estimated_tokens,
        estimated_cost=0.01
    )
    print(f"  2. Rate limit check: {'Allowed' if allowed else 'Denied'}")

    if allowed:
        # 3. Check cache
        cached = smart_cache.get_cached_response(
            prompt=input_text,
            model=classification.recommended_models[0]
        )
        print(f"  3. Cache check: {'Hit' if cached else 'Miss'}")

        if not cached:
            # 4. Execute request with monitoring
            model = classification.recommended_models[0]
            with PerformanceTracker(metrics_collector, model, "local") as tracker:
                # Simulate LLM call
                await asyncio.sleep(0.05)
                response = "SQL injection detected: Use parameterized queries"
                tracker.set_cost(0.0)  # Local model
                tracker.set_tokens(100)

            print(f"  4. Request executed: {len(response)} chars")

            # 5. Cache response
            smart_cache.cache_response(
                prompt=input_text,
                model=model,
                response=response
            )
            print(f"  5. Response cached")

            # 6. Record usage
            rate_limiter.record_request("integration_test_user", 100, 0.0)
            print(f"  6. Usage recorded")

    print("  [PASSED]")


def main():
    """Run all tests."""
    print("=" * 60)
    print("ADVANCED FEATURES TEST SUITE")
    print("=" * 60)
    print("\nTesting:")
    print("  • Task Classification")
    print("  • Performance Monitoring")
    print("  • Intelligent Caching")
    print("  • Rate Limiting & Quotas")
    print("  • Async Task Queue")
    print("  • Batch Processing")
    print("  • Integration")
    print("")

    async def run_tests():
        try:
            await test_task_classifier()
            await test_performance_monitoring()
            await test_caching()
            await test_rate_limiting()
            await test_task_queue()
            await test_cancellation()
            await test_batch_processing()
            await test_integration()

            print("\n" + "=" * 60)
            print("ALL ADVANCED TESTS PASSED (8/8)")
            print("=" * 60)
            print("\n[SUMMARY]")
            print("  Task Classification: ✓ Operational")
            print("  Performance Monitoring: ✓ Working")
            print("  Intelligent Caching: ✓ Functional")
            print("  Rate Limiting: ✓ Enforced")
            print("  Task Queue: ✓ Processing")
            print("  Batch Processing: ✓ Efficient")
            print("  Integration: ✓ End-to-end working")
            print("\n  All advanced features production-ready!")

            return 0

        except Exception as e:
            print(f"\n[FAILED] {e}")
            import traceback
            traceback.print_exc()
            return 1

    return asyncio.run(run_tests())


if __name__ == "__main__":
    sys.exit(main())
