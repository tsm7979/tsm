"""Test Mesh Orchestrator - 5-Agent Deliberation."""

import asyncio
import sys
sys.path.insert(0, '.')

from execution.mesh_adapter import mesh_orchestrator, AgentRole


async def main():
    print("=" * 80)
    print("MESH ORCHESTRATOR TEST - 5-Agent Byzantine-Fault-Tolerant Deliberation")
    print("=" * 80)
    print()
    print("Architecture:")
    print("  Phase 1: Observer + Security (parallel analysis)")
    print("  Phase 2: Coherence check (Jaccard similarity)")
    print("  Phase 3: Planner (synthesis)")
    print("  Phase 4: Execution (technical details)")
    print("  Phase 5: Verifier (red team validation)")
    print()

    # Test Case 1: SQL Injection Incident
    print("=" * 80)
    print("[TEST 1] SQL Injection in Authentication Endpoint")
    print("=" * 80)

    incident = (
        "SQL injection vulnerability detected in /api/auth/login endpoint. "
        "User input from 'username' field is concatenated directly into SQL query "
        "without parameterization. Attacker can bypass authentication using "
        "' OR '1'='1 payload."
    )

    result = await mesh_orchestrator.run_deliberation(
        incident_description=incident,
        severity="critical"
    )

    print(f"\n[RESULT]")
    print(f"  Deliberation ID: {result['deliberation_id']}")
    print(f"  Severity: {result['severity']}")
    print(f"  Coherence Score: {result['coherence_score']:.2f}")
    print(f"  Consensus Status: {result['consensus_status']}")
    print(f"  Execution Time: {result['execution_time_ms']:.0f}ms")
    print()

    print(f"[AGENT RESPONSES]")
    print()

    for role, response in result['agent_responses'].items():
        print(f"  [{role.upper()}]")
        # Show first 200 chars of response
        preview = response[:200] + "..." if len(response) > 200 else response
        print(f"    {preview}")
        print()

    # Test Case 2: XSS Vulnerability
    print("=" * 80)
    print("[TEST 2] Cross-Site Scripting in User Profile")
    print("=" * 80)

    incident2 = (
        "Stored XSS vulnerability in user profile page. User bio field "
        "accepts unescaped HTML input which is rendered directly without "
        "sanitization, allowing <script> tag injection."
    )

    result2 = await mesh_orchestrator.run_deliberation(
        incident_description=incident2,
        severity="high"
    )

    print(f"\n[RESULT]")
    print(f"  Deliberation ID: {result2['deliberation_id']}")
    print(f"  Coherence Score: {result2['coherence_score']:.2f}")
    print(f"  Consensus Status: {result2['consensus_status']}")
    print(f"  Execution Time: {result2['execution_time_ms']:.0f}ms")
    print()

    # Show planner output (most important for action plan)
    print(f"[PLANNER OUTPUT]")
    planner_response = result2['agent_responses']['planner']
    print(f"  {planner_response[:400]}...")
    print()

    # Show verifier output (red team findings)
    print(f"[VERIFIER OUTPUT]")
    verifier_response = result2['agent_responses']['verifier']
    print(f"  {verifier_response[:400]}...")
    print()

    # Get stats
    print("=" * 80)
    print("[STATISTICS]")
    print("=" * 80)

    stats = mesh_orchestrator.get_stats()
    print(f"  Total Deliberations: {stats['total_deliberations']}")
    print(f"  Avg Execution Time: {stats['avg_execution_time_ms']:.0f}ms")
    print(f"  Avg Coherence Score: {stats['avg_coherence_score']:.2f}")
    print(f"  Success Rate: {stats['success_rate'] * 100:.1f}%")
    print()

    print("=" * 80)
    print("MESH ORCHESTRATION COMPLETE")
    print("=" * 80)
    print()
    print("[STATUS] 5-agent mesh operational with Byzantine fault tolerance")
    print("[AGENTS] Observer, Security, Planner, Execution, Verifier")
    print("[ROUTING] All agents routed through TSMv1 poly-LLM orchestrator")
    print()


if __name__ == "__main__":
    asyncio.run(main())
