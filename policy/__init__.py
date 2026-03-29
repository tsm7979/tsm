"""
TSM Layer Policy Engine
=======================

Governance, compliance, and policy enforcement.
"""

from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


class PolicyEngine:
    """
    Policy decision engine.

    Determines what actions are allowed based on:
    - User/org context
    - Risk classification
    - Compliance requirements
    - Custom rules
    """

    async def check(
        self,
        input_data: Any,
        risk: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Check if action is allowed.

        Args:
            input_data: The request data
            risk: Risk classification
            context: User/org context

        Returns:
            Policy decision with allowed/denied and reason
        """
        # TODO: Implement real policy logic
        # For now, simple allow/deny based on risk

        risk_tier = risk.tier.value if hasattr(risk, "tier") else risk.get("tier", "low")

        # Block critical without approval
        if risk_tier == "critical" and not context.get("has_approval"):
            return {
                "allowed": False,
                "reason": "Critical risk requires approval",
                "requires_approval": True
            }

        # All others allowed
        return {
            "allowed": True,
            "reason": "Policy check passed",
            "requires_approval": False
        }


# Global instance
engine = PolicyEngine()
