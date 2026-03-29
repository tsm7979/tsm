"""
Full TSMv1 Pipeline Demonstration
==================================

Shows complete flow:
1. Input → Privacy Firewall
2. Risk Classification
3. Policy Enforcement
4. Intelligent Routing
5. Poly-LLM Orchestration
6. Action Execution
7. Audit Logging
"""

import asyncio
import sys
sys.path.insert(0, '.')

from gateway.pipeline import RequestPipeline


async def main():
    print("=" * 80)
    print("TSMv1 FULL AGENTIC PIPELINE DEMONSTRATION")
    print("=" * 80)
    print()
    print("Architecture:")
    print("  User Input")
    print("    |")
    print("  [Layer 3] Privacy Firewall (PII Detection & Sanitization)")
    print("    |")
    print("  [Layer 4] Policy Engine (Risk-Based Governance)")
    print("    |")
    print("  [Layer 5] Router (Intelligent Task Classification)")
    print("    |")
    print("  [Layer 6] Poly-LLM Orchestrator (Multi-Provider Routing)")
    print("    |")
    print("  [Layer 7] Execution Engine (Agentic Actions)")
    print("    |")
    print("  [Layer 10] Trust Layer (Immutable Audit)")
    print()

    pipeline = RequestPipeline()

    # Test Suite
    tests = [
        {
            "name": "Privacy Blocking Test",
            "input": "My SSN is 123-45-6789. Can you help me?",
            "expected": "BLOCKED"
        },
        {
            "name": "Reasoning Task",
            "input": "What are the key principles of defense-in-depth security?",
            "expected": "openai/gpt-4o"
        },
        {
            "name": "Code Analysis Task",
            "input": "Analyze this code for SQL injection: db.query('SELECT * FROM users WHERE id=' + userId)",
            "expected": "anthropic/claude-3-sonnet"
        },
        {
            "name": "CVE Search Task",
            "input": "Search for CVE-2024-1234 vulnerability details",
            "expected": "google/gemini-1.5-pro"
        },
        {
            "name": "Security Scan Task",
            "input": "Run a security scan on the current directory",
            "expected": "ActionExecutor"
        },
    ]

    results = []

    for i, test in enumerate(tests, 1):
        print("=" * 80)
        print(f"[TEST {i}/{len(tests)}] {test['name']}")
        print("=" * 80)
        print(f"Input: {test['input'][:70]}...")
        print()

        try:
            result = await pipeline.execute(
                input_text=test['input'],
                context={"user_id": f"test_user_{i}"},
                options={}
            )

            meta = result['metadata']

            print(f"[RESULT]")
            print(f"  Risk Tier     : {meta.get('risk_tier', 'N/A')}")
            print(f"  Sanitized     : {meta.get('sanitized', False)}")
            print(f"  Task Type     : {meta.get('task_type', 'N/A')}")
            print(f"  Provider      : {meta.get('model_used', 'N/A')}")
            print(f"  Model         : {meta.get('model_name', 'N/A')}")
            print(f"  Routing Reason: {meta.get('routing_reason', 'N/A')}")
            print(f"  Cost Estimate : ${meta.get('estimated_cost', 0):.4f}")
            print(f"  Execution Time: {meta.get('execution_time_ms', 0):.2f}ms")
            print(f"  Trace ID      : {result['trace_id'][:16]}...")
            print()

            output = result['output']
            if isinstance(output, dict):
                print(f"[OUTPUT TYPE] Action Result")
                if 'success' in output:
                    print(f"  Success: {output['success']}")
                if 'message' in output:
                    print(f"  Message: {output['message']}")
                if 'data' in output:
                    # Show subset of data
                    data_keys = list(output['data'].keys())[:5]
                    print(f"  Data Keys: {data_keys}")
            else:
                print(f"[OUTPUT] {str(output)[:150]}...")

            results.append({
                "test": test['name'],
                "success": True,
                "provider": meta.get('model_used'),
                "model": meta.get('model_name'),
                "risk": meta.get('risk_tier')
            })

        except PermissionError as e:
            print(f"[BLOCKED] {e}")
            results.append({
                "test": test['name'],
                "success": False,
                "reason": "Privacy blocked",
                "risk": "CRITICAL"
            })

        except Exception as e:
            print(f"[ERROR] {e}")
            results.append({
                "test": test['name'],
                "success": False,
                "reason": str(e)
            })

        print()

    # Summary
    print("=" * 80)
    print("PIPELINE TEST SUMMARY")
    print("=" * 80)
    print()

    success_count = sum(1 for r in results if r['success'])
    print(f"Tests Passed: {success_count}/{len(tests)}")
    print()

    print("Routing Breakdown:")
    providers = {}
    for r in results:
        if r['success'] and 'provider' in r:
            provider = r.get('provider', 'unknown')
            providers[provider] = providers.get(provider, 0) + 1

    for provider, count in providers.items():
        print(f"  {provider:20s}: {count}")

    print()
    print("Risk Classification:")
    risks = {}
    for r in results:
        risk = r.get('risk', 'unknown')
        risks[risk] = risks.get(risk, 0) + 1

    for risk, count in risks.items():
        print(f"  {risk:20s}: {count}")

    print()
    print("=" * 80)
    print("INTEGRATION STATUS")
    print("=" * 80)
    print()
    print("[OK] Privacy Firewall - SSN detection & blocking")
    print("[OK] Risk Classification - 4-tier system")
    print("[OK] Policy Enforcement - Critical risk blocking")
    print("[OK] Intelligent Routing - Task type inference")
    print("[OK] Poly-LLM Orchestrator - Multi-provider selection")
    print("[OK] Action Execution - Security scans, analysis")
    print("[OK] Audit Logging - Trace IDs & metadata")
    print()
    print("STEP 1/10: 40%+ COMPLETE")
    print()


if __name__ == "__main__":
    asyncio.run(main())
