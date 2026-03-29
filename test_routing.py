"""Test routing decisions across different task types."""

import asyncio
import sys
sys.path.insert(0, '.')

from gateway.pipeline import RequestPipeline


async def test():
    pipeline = RequestPipeline()

    tests = [
        ('What is 2+2?', 'REASONING'),
        ('Search for CVE-2024-1234', 'SEARCH'),
        ('Analyze this code: function foo() {}', 'CODE_ANALYSIS'),
        ('Generate a fix for SQL injection', 'CODE_GENERATION'),
        ('Summarize this report', 'SUMMARIZATION'),
    ]

    print("=" * 70)
    print("ROUTING DECISION TEST")
    print("=" * 70)

    for test_input, expected in tests:
        print(f'\n[TEST] {test_input[:50]}...')
        try:
            result = await pipeline.execute(test_input, {}, {})

            meta = result['metadata']
            print(f'  Task Type    : {meta.get("task_type")}')
            print(f'  Provider     : {meta.get("model_used")}')
            print(f'  Model        : {meta.get("model_name")}')
            print(f'  Routing      : {meta.get("routing_reason")}')
            print(f'  Cost Estimate: ${meta.get("estimated_cost", 0):.4f}')
            print(f'  Risk Tier    : {meta.get("risk_tier")}')
        except Exception as e:
            print(f'  [ERROR] {e}')

if __name__ == "__main__":
    asyncio.run(test())
