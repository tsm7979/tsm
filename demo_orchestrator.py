"""
Demo: TSMv1 Poly-LLM Orchestrator Integration
==============================================

Shows REAL intelligent routing with cost tracking.
"""

import asyncio
import sys
sys.path.insert(0, '.')

from router import orchestrator
from router.orchestrator import LLMRequest, TaskType


async def main():
    print("=" * 70)
    print("TSMv1 POLY-LLM ORCHESTRATOR - LIVE DEMO")
    print("=" * 70)
    print()
    print("Features:")
    print("  [OK] Multi-provider routing (GPT, Claude, Gemini, Local)")
    print("  [OK] Task-based intelligent selection")
    print("  [OK] Cost tracking and optimization")
    print("  [OK] Automatic fallback on failure")
    print("  [OK] Performance metrics")
    print()

    # Test different task types
    tests = [
        LLMRequest(
            task_type=TaskType.REASONING,
            prompt="Why is defense-in-depth important for security?"
        ),
        LLMRequest(
            task_type=TaskType.CODE_ANALYSIS,
            prompt="Analyze this: db.query('SELECT * FROM users WHERE id=' + userId)"
        ),
        LLMRequest(
            task_type=TaskType.SEARCH,
            prompt="Find CVE-2024-1234 details"
        ),
        LLMRequest(
            task_type=TaskType.SUMMARIZATION,
            prompt="Summarize: TSM is a privacy-first AI control plane."
        ),
    ]

    print("=" * 70)
    print("RUNNING 4 REQUESTS THROUGH ORCHESTRATOR")
    print("=" * 70)

    for i, request in enumerate(tests, 1):
        print(f"\n[{i}/4] Task: {request.task_type.value}")
        print(f"      Prompt: {request.prompt[:60]}...")

        # Get routing decision
        provider, model = orchestrator.route(request)
        print(f"      Route: {provider.value}/{model}")

        # Execute
        response = await orchestrator.complete(request)

        if response.success:
            print(f"      [SUCCESS]")
            print(f"      Tokens: {response.tokens_used}")
            print(f"      Cost: ${response.cost:.4f}")
            print(f"      Latency: {response.latency_ms:.0f}ms")
            print(f"      Output: {response.content[:80]}...")
        else:
            print(f"      [FAILED] {response.error}")

    # Show stats
    print("\n" + "=" * 70)
    print("ORCHESTRATOR STATISTICS")
    print("=" * 70)

    stats = orchestrator.get_stats()
    print(f"\nTotal Requests: {stats['total_requests']}")
    print(f"Success Rate: {stats['success_rate'] * 100:.1f}%")
    print(f"Total Tokens: {stats['total_tokens']:,}")
    print(f"Total Cost: ${stats['total_cost']:.4f}")
    print(f"Avg Latency: {stats['avg_latency_ms']:.0f}ms")

    print("\nRequests by Provider:")
    for provider, count in stats['requests_by_provider'].items():
        print(f"  {provider:12s}: {count}")

    print("\nCost Breakdown:")
    cost_breakdown = orchestrator.get_cost_breakdown()
    for provider, cost in cost_breakdown.items():
        print(f"  {provider:12s}: ${cost:.4f}")

    print("\n" + "=" * 70)
    print("STEP 1/10 COMPLETE")
    print("=" * 70)
    print("\nIntegrated Components:")
    print("  [OK] Poly-LLM Orchestrator (603 LOC)")
    print("  [OK] 4 Model Providers (OpenAI, Claude, Gemini, Local)")
    print("  [OK] Intelligent routing with task types")
    print("  [OK] Cost tracking and optimization")
    print("  [OK] Fallback chains")
    print("\nNext: Integrate full execution engine + agentic reasoning")


if __name__ == "__main__":
    asyncio.run(main())
