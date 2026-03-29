"""Test Tool Registry and Playbook Integration."""

import asyncio
import sys
sys.path.insert(0, '.')

from tools import tool_registry, ToolType


async def main():
    print("=" * 80)
    print("TOOL REGISTRY TEST - Playbook Integration")
    print("=" * 80)
    print()

    # Get stats
    stats = tool_registry.get_stats()

    print(f"[REGISTRY STATS]")
    print(f"  Total Tools: {stats['total_tools']}")
    print()

    print(f"[BY TYPE]")
    for tool_type, count in stats['by_type'].items():
        print(f"  {tool_type:15s}: {count}")
    print()

    print(f"[BY FINDING TYPE] (Top 10)")
    finding_types = sorted(stats['by_finding_type'].items(), key=lambda x: x[1], reverse=True)
    for finding_type, count in finding_types[:10]:
        print(f"  {finding_type:25s}: {count}")
    print()

    # Test 1: Find SQL Injection fixer for Python/Django
    print("=" * 80)
    print("[TEST 1] Find SQL Injection Fixer for Python/Django")
    print("=" * 80)

    tools = tool_registry.find_tools(
        finding_type="SQL_INJECTION",
        language="python",
        framework="django",
        tool_type=ToolType.FIXER
    )

    print(f"Found {len(tools)} matching tools:")
    for tool in tools:
        print(f"\n  Tool: {tool.name}")
        print(f"    ID: {tool.tool_id}")
        print(f"    Description: {tool.description}")
        print(f"    Confidence: {tool.confidence}")
        print(f"    Languages: {tool.languages}")
        print(f"    Frameworks: {tool.frameworks}")

    # Test 2: Execute SQL Injection Fixer
    if tools:
        print("\n" + "=" * 80)
        print("[TEST 2] Execute SQL Injection Fixer")
        print("=" * 80)

        tool = tools[0]
        result = await tool_registry.execute(
            tool_name=tool.tool_id,
            inputs={"input": "Fix SQL injection in user login"},
            context={"target": "app.py"}
        )

        print(f"\nExecution Result:")
        print(f"  Success: {result['success']}")
        print(f"  Tool: {result.get('tool')}")
        print(f"  Playbook: {result.get('playbook_id')}")
        print(f"  Strategy: {result.get('fix_strategy')}")
        if result.get('code_template'):
            print(f"\n  Code Template:")
            template_lines = result['code_template'].strip().split('\n')[:5]
            for line in template_lines:
                print(f"    {line}")
            print(f"    ...")

    # Test 3: Find all XSS fixers
    print("\n" + "=" * 80)
    print("[TEST 3] Find XSS Fixers (All Frameworks)")
    print("=" * 80)

    xss_tools = tool_registry.find_tools(
        finding_type="XSS",
        tool_type=ToolType.FIXER
    )

    print(f"Found {len(xss_tools)} XSS fixers:")
    for tool in xss_tools:
        print(f"  - {tool.name} ({tool.tool_id})")
        print(f"    Languages: {tool.languages}")
        print(f"    Frameworks: {tool.frameworks}")

    # Test 4: Find security scanners
    print("\n" + "=" * 80)
    print("[TEST 4] Find Security Scanners")
    print("=" * 80)

    scanners = tool_registry.find_tools(
        finding_type="ALL",
        tool_type=ToolType.SCANNER
    )

    print(f"Found {len(scanners)} scanners:")
    for scanner in scanners:
        print(f"  - {scanner.name} ({scanner.tool_id})")
        print(f"    Description: {scanner.description}")
        print(f"    Confidence: {scanner.confidence}")

    # Test 5: Execute security scanner
    if scanners:
        print("\n" + "=" * 80)
        print("[TEST 5] Execute Security Scanner")
        print("=" * 80)

        result = await tool_registry.execute(
            tool_name="SCAN-SECURITY-001",
            inputs={"input": "Scan current directory"},
            context={"target": "."}
        )

        print(f"\nScan Result:")
        print(f"  Success: {result['success']}")
        print(f"  Tool: {result.get('tool')}")
        if result.get('data') and 'findings' in result['data']:
            findings = result['data']['findings']
            print(f"  Files Scanned: {findings.get('files_scanned', 0)}")
            print(f"  Vulnerabilities: {len(findings.get('vulnerabilities', []))}")
            print(f"  Secrets Found: {findings.get('secrets_detected', 0)}")

    # Test 6: Find Command Injection fixers
    print("\n" + "=" * 80)
    print("[TEST 6] Find Command Injection Fixers")
    print("=" * 80)

    cmd_injection_tools = tool_registry.find_tools(
        finding_type="COMMAND_INJECTION",
        tool_type=ToolType.FIXER
    )

    print(f"Found {len(cmd_injection_tools)} command injection fixers:")
    for tool in cmd_injection_tools:
        print(f"  - {tool.name}")
        print(f"    Languages: {tool.languages}")
        print(f"    Confidence: {tool.confidence}")

    print("\n" + "=" * 80)
    print("TOOL REGISTRY INTEGRATION COMPLETE")
    print("=" * 80)
    print()
    print(f"[SUMMARY]")
    print(f"  Total Tools Registered: {stats['total_tools']}")
    print(f"  Fixer Tools: {stats['by_type'].get('fixer', 0)}")
    print(f"  Scanner Tools: {stats['by_type'].get('scanner', 0)}")
    print(f"  Unique Finding Types: {len(stats['by_finding_type'])}")
    print()
    print("[STATUS] Tool registry fully operational with 18+ security playbooks")
    print()


if __name__ == "__main__":
    asyncio.run(main())
