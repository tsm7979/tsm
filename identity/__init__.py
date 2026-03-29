"""
TSM Layer Identity
==================

Authentication, authorization, and context management.
"""

from typing import Dict, Any, Optional
from fastapi import Request, HTTPException
import logging

logger = logging.getLogger(__name__)


class UserContext:
    """User/org context for requests"""

    def __init__(
        self,
        user_id: Optional[str] = None,
        org_id: Optional[str] = None,
        role: str = "user",
        trust_level: float = 0.5,
        **kwargs
    ):
        self.user_id = user_id or "anonymous"
        self.org_id = org_id
        self.role = role
        self.trust_level = trust_level
        self.metadata = kwargs

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "org_id": self.org_id,
            "role": self.role,
            "trust_level": self.trust_level,
            **self.metadata
        }


async def get_current_context(request: Request = None) -> UserContext:
    """
    Extract user context from request.

    This is a dependency for FastAPI endpoints.
    """
    # TODO: Implement proper auth
    # For now, return default context
    return UserContext(
        user_id="default_user",
        org_id="default_org",
        role="user",
        trust_level=0.7
    )


async def extract_context(request: Dict[str, Any]) -> UserContext:
    """Extract context from request dict"""
    return UserContext(
        user_id=request.get("user_id"),
        org_id=request.get("org_id"),
        role=request.get("role", "user"),
        trust_level=request.get("trust_level", 0.5)
    )
