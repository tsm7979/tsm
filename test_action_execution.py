"""Test ActionExecutor integration with ExecutionEngine."""

import asyncio
import sys
sys.path.insert(0, '.')

from execution.action_executor import Action, ActionType
from execution import ExecutionEngine


async def test_action_executor():
    """Test ActionExecutor via ExecutionEngine."""

    print("=" * 70)
    print("TESTING ACTION EXECUTOR INTEGRATION")
    print("=" * 70)

    # Initialize engine
    engine = ExecutionEngine()

    # Test 1: Security Scan Action
    print("\n[TEST 1] Security Scan Action")
    print("-" * 70)

    routing_decision = {
        "type": "tool",
        "target": "scan",
        "model": None
    }

    result = await engine.execute(
        routing_decision=routing_decision,
        input_data="Scan current directory for vulnerabilities",
        context={"target": ".", "user_id": "test_user"},
        options={"scan_type": "security"}
    )

    print(f"Result: {result['output']['success']}")
    print(f"Message: {result['output']['message']}")
    if result['output']['data']:
        data = result['output']['data']
        if 'findings' in data:
            findings = data['findings']
            print(f"Files Scanned: {findings.get('files_scanned', 0)}")
            print(f"Vulnerabilities: {len(findings.get('vulnerabilities', []))}")
            print(f"Secrets Detected: {findings.get('secrets_detected', 0)}")

    # Test 2: Analyze Action
    print("\n[TEST 2] Analyze Action")
    print("-" * 70)

    routing_decision2 = {
        "type": "tool",
        "target": "analyze",
        "model": None
    }

    result2 = await engine.execute(
        routing_decision=routing_decision2,
        input_data="Analyze security posture of application",
        context={"target": "application", "user_id": "test_user"},
        options={"analysis_type": "security"}
    )

    print(f"Result: {result2['output']['success']}")
    print(f"Message: {result2['output']['message']}")
    if result2['output']['data']:
        data = result2['output']['data']
        print(f"Risk Score: {data.get('risk_score', 'N/A')}")
        print(f"Confidence: {data.get('confidence', 'N/A')}")

    # Test 3: Direct ActionExecutor Usage
    print("\n[TEST 3] Direct ActionExecutor - Vulnerability Scan")
    print("-" * 70)

    action = Action(
        action_type=ActionType.SCAN.value,
        description="Run vulnerability scan on TSMv1",
        target=".",
        parameters={"scan_type": "vulnerability"},
        risk_level="low"
    )

    direct_result = await engine.action_executor.execute(action)

    print(f"Success: {direct_result.success}")
    print(f"Execution Time: {direct_result.execution_time_ms:.2f}ms")
    if direct_result.data and 'findings' in direct_result.data:
        vuln_data = direct_result.data['findings']
        print(f"Critical: {vuln_data.get('critical', 0)}")
        print(f"High: {vuln_data.get('high', 0)}")
        print(f"Medium: {vuln_data.get('medium', 0)}")
        print(f"Low: {vuln_data.get('low', 0)}")

    # Test 4: Get Executor Stats
    print("\n[TEST 4] Executor Statistics")
    print("-" * 70)

    stats = engine.action_executor.get_stats()
    print(f"Total Executions: {stats['total_executions']}")
    print(f"Successful: {stats['successful']}")
    print(f"Failed: {stats['failed']}")
    print(f"Success Rate: {stats['success_rate'] * 100:.1f}%")

    print("\n" + "=" * 70)
    print("ALL TESTS COMPLETE")
    print("=" * 70)

    return True


if __name__ == "__main__":
    asyncio.run(test_action_executor())
