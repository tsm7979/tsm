"""
TSM RBAC (Role-Based Access Control)
=====================================

Fine-grained access control system with:
- Role-based permissions
- Resource-level access control
- Permission inheritance
- Dynamic permission checking
- Audit trail
"""

from enum import Enum
from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass, field
from datetime import datetime
from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)


class Permission(str, Enum):
    """System permissions."""

    # Model operations
    MODEL_EXECUTE = "model:execute"
    MODEL_LIST = "model:list"
    MODEL_CONFIGURE = "model:configure"

    # Document operations
    DOCUMENT_READ = "document:read"
    DOCUMENT_WRITE = "document:write"
    DOCUMENT_DELETE = "document:delete"
    DOCUMENT_LIST = "document:list"

    # Plugin operations
    PLUGIN_INSTALL = "plugin:install"
    PLUGIN_UNINSTALL = "plugin:uninstall"
    PLUGIN_EXECUTE = "plugin:execute"
    PLUGIN_CONFIGURE = "plugin:configure"
    PLUGIN_LIST = "plugin:list"

    # Webhook operations
    WEBHOOK_CREATE = "webhook:create"
    WEBHOOK_DELETE = "webhook:delete"
    WEBHOOK_UPDATE = "webhook:update"
    WEBHOOK_LIST = "webhook:list"

    # Cache operations
    CACHE_READ = "cache:read"
    CACHE_WRITE = "cache:write"
    CACHE_DELETE = "cache:delete"
    CACHE_CLEAR = "cache:clear"

    # Analytics operations
    ANALYTICS_VIEW = "analytics:view"
    ANALYTICS_EXPORT = "analytics:export"

    # Configuration operations
    CONFIG_READ = "config:read"
    CONFIG_WRITE = "config:write"

    # User management
    USER_CREATE = "user:create"
    USER_READ = "user:read"
    USER_UPDATE = "user:update"
    USER_DELETE = "user:delete"
    USER_LIST = "user:list"

    # Role management
    ROLE_CREATE = "role:create"
    ROLE_READ = "role:read"
    ROLE_UPDATE = "role:update"
    ROLE_DELETE = "role:delete"
    ROLE_ASSIGN = "role:assign"

    # Tenant management
    TENANT_CREATE = "tenant:create"
    TENANT_READ = "tenant:read"
    TENANT_UPDATE = "tenant:update"
    TENANT_DELETE = "tenant:delete"
    TENANT_MANAGE = "tenant:manage"

    # System operations
    SYSTEM_ADMIN = "system:admin"
    SYSTEM_MONITOR = "system:monitor"
    SYSTEM_DEBUG = "system:debug"


class ResourceType(str, Enum):
    """Resource types for access control."""

    MODEL = "model"
    DOCUMENT = "document"
    PLUGIN = "plugin"
    WEBHOOK = "webhook"
    CACHE = "cache"
    CONFIG = "config"
    USER = "user"
    ROLE = "role"
    TENANT = "tenant"
    SYSTEM = "system"


@dataclass
class Resource:
    """
    A resource that can be protected by access control.

    Resources have a type and ID, and can have metadata for fine-grained control.
    """

    resource_type: ResourceType
    resource_id: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        return f"{self.resource_type.value}:{self.resource_id}"

    def matches(self, pattern: "ResourcePattern") -> bool:
        """Check if this resource matches a pattern."""
        if pattern.resource_type != self.resource_type:
            return False

        if pattern.resource_id == "*":
            return True

        return pattern.resource_id == self.resource_id


@dataclass
class ResourcePattern:
    """
    Pattern for matching resources.

    Supports wildcards for resource_id (e.g., "model:*" matches all models).
    """

    resource_type: ResourceType
    resource_id: str = "*"

    def __str__(self) -> str:
        return f"{self.resource_type.value}:{self.resource_id}"

    @classmethod
    def from_string(cls, pattern_str: str) -> "ResourcePattern":
        """Parse pattern from string (e.g., 'model:gpt-4' or 'document:*')."""
        parts = pattern_str.split(":", 1)
        if len(parts) != 2:
            raise ValueError(f"Invalid resource pattern: {pattern_str}")

        return cls(
            resource_type=ResourceType(parts[0]),
            resource_id=parts[1]
        )


@dataclass
class PermissionGrant:
    """
    A permission grant on a resource pattern.

    Combines a permission with a resource pattern.
    """

    permission: Permission
    resource_pattern: ResourcePattern

    def allows(self, permission: Permission, resource: Resource) -> bool:
        """Check if this grant allows the permission on the resource."""
        if self.permission != permission:
            return False

        return resource.matches(self.resource_pattern)

    def __str__(self) -> str:
        return f"{self.permission.value} on {self.resource_pattern}"


@dataclass
class Role:
    """
    A role with a set of permission grants.

    Roles can inherit from other roles.
    """

    role_id: str
    name: str
    description: str = ""

    # Permission grants
    grants: List[PermissionGrant] = field(default_factory=list)

    # Role inheritance
    parent_roles: List[str] = field(default_factory=list)

    # Metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_permission(self, permission: Permission, resource_pattern: ResourcePattern):
        """Add a permission grant to this role."""
        grant = PermissionGrant(permission, resource_pattern)
        self.grants.append(grant)
        self.updated_at = datetime.utcnow()

    def remove_permission(self, permission: Permission, resource_pattern: ResourcePattern) -> bool:
        """Remove a permission grant from this role."""
        for i, grant in enumerate(self.grants):
            if grant.permission == permission and str(grant.resource_pattern) == str(resource_pattern):
                self.grants.pop(i)
                self.updated_at = datetime.utcnow()
                return True
        return False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "role_id": self.role_id,
            "name": self.name,
            "description": self.description,
            "grants": [
                {
                    "permission": grant.permission.value,
                    "resource": str(grant.resource_pattern)
                }
                for grant in self.grants
            ],
            "parent_roles": self.parent_roles,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "metadata": self.metadata,
        }


# Predefined roles
PREDEFINED_ROLES = {
    "admin": Role(
        role_id="admin",
        name="Administrator",
        description="Full system access",
        grants=[
            PermissionGrant(Permission.SYSTEM_ADMIN, ResourcePattern(ResourceType.SYSTEM, "*")),
        ]
    ),
    "developer": Role(
        role_id="developer",
        name="Developer",
        description="Development and testing access",
        grants=[
            PermissionGrant(Permission.MODEL_EXECUTE, ResourcePattern(ResourceType.MODEL, "*")),
            PermissionGrant(Permission.MODEL_LIST, ResourcePattern(ResourceType.MODEL, "*")),
            PermissionGrant(Permission.DOCUMENT_READ, ResourcePattern(ResourceType.DOCUMENT, "*")),
            PermissionGrant(Permission.DOCUMENT_WRITE, ResourcePattern(ResourceType.DOCUMENT, "*")),
            PermissionGrant(Permission.PLUGIN_EXECUTE, ResourcePattern(ResourceType.PLUGIN, "*")),
            PermissionGrant(Permission.PLUGIN_LIST, ResourcePattern(ResourceType.PLUGIN, "*")),
            PermissionGrant(Permission.CACHE_READ, ResourcePattern(ResourceType.CACHE, "*")),
            PermissionGrant(Permission.CACHE_WRITE, ResourcePattern(ResourceType.CACHE, "*")),
            PermissionGrant(Permission.ANALYTICS_VIEW, ResourcePattern(ResourceType.SYSTEM, "*")),
            PermissionGrant(Permission.CONFIG_READ, ResourcePattern(ResourceType.CONFIG, "*")),
        ]
    ),
    "analyst": Role(
        role_id="analyst",
        name="Analyst",
        description="Analytics and monitoring access",
        grants=[
            PermissionGrant(Permission.MODEL_EXECUTE, ResourcePattern(ResourceType.MODEL, "*")),
            PermissionGrant(Permission.MODEL_LIST, ResourcePattern(ResourceType.MODEL, "*")),
            PermissionGrant(Permission.DOCUMENT_READ, ResourcePattern(ResourceType.DOCUMENT, "*")),
            PermissionGrant(Permission.ANALYTICS_VIEW, ResourcePattern(ResourceType.SYSTEM, "*")),
            PermissionGrant(Permission.ANALYTICS_EXPORT, ResourcePattern(ResourceType.SYSTEM, "*")),
            PermissionGrant(Permission.CACHE_READ, ResourcePattern(ResourceType.CACHE, "*")),
        ]
    ),
    "user": Role(
        role_id="user",
        name="User",
        description="Basic user access",
        grants=[
            PermissionGrant(Permission.MODEL_EXECUTE, ResourcePattern(ResourceType.MODEL, "*")),
            PermissionGrant(Permission.MODEL_LIST, ResourcePattern(ResourceType.MODEL, "*")),
            PermissionGrant(Permission.DOCUMENT_READ, ResourcePattern(ResourceType.DOCUMENT, "*")),
            PermissionGrant(Permission.CACHE_READ, ResourcePattern(ResourceType.CACHE, "*")),
        ]
    ),
    "readonly": Role(
        role_id="readonly",
        name="Read-Only",
        description="Read-only access",
        grants=[
            PermissionGrant(Permission.MODEL_LIST, ResourcePattern(ResourceType.MODEL, "*")),
            PermissionGrant(Permission.DOCUMENT_READ, ResourcePattern(ResourceType.DOCUMENT, "*")),
            PermissionGrant(Permission.PLUGIN_LIST, ResourcePattern(ResourceType.PLUGIN, "*")),
            PermissionGrant(Permission.WEBHOOK_LIST, ResourcePattern(ResourceType.WEBHOOK, "*")),
            PermissionGrant(Permission.CACHE_READ, ResourcePattern(ResourceType.CACHE, "*")),
            PermissionGrant(Permission.CONFIG_READ, ResourcePattern(ResourceType.CONFIG, "*")),
        ]
    ),
}


@dataclass
class User:
    """
    A user with assigned roles.

    Users inherit permissions from all their roles.
    """

    user_id: str
    username: str
    email: str = ""

    # Roles assigned to this user
    roles: List[str] = field(default_factory=list)

    # Direct permission grants (override role permissions)
    direct_grants: List[PermissionGrant] = field(default_factory=list)

    # Tenant association
    tenant_id: Optional[str] = None

    # Metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_role(self, role_id: str):
        """Assign a role to this user."""
        if role_id not in self.roles:
            self.roles.append(role_id)

    def remove_role(self, role_id: str) -> bool:
        """Remove a role from this user."""
        if role_id in self.roles:
            self.roles.remove(role_id)
            return True
        return False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "username": self.username,
            "email": self.email,
            "roles": self.roles,
            "tenant_id": self.tenant_id,
            "created_at": self.created_at.isoformat(),
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "metadata": self.metadata,
        }


class RBACStore(ABC):
    """Abstract storage interface for RBAC entities."""

    @abstractmethod
    async def get_role(self, role_id: str) -> Optional[Role]:
        """Get role by ID."""
        pass

    @abstractmethod
    async def create_role(self, role: Role) -> Role:
        """Create a new role."""
        pass

    @abstractmethod
    async def update_role(self, role: Role) -> Role:
        """Update existing role."""
        pass

    @abstractmethod
    async def delete_role(self, role_id: str) -> bool:
        """Delete role."""
        pass

    @abstractmethod
    async def get_user(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        pass

    @abstractmethod
    async def create_user(self, user: User) -> User:
        """Create a new user."""
        pass

    @abstractmethod
    async def update_user(self, user: User) -> User:
        """Update existing user."""
        pass

    @abstractmethod
    async def delete_user(self, user_id: str) -> bool:
        """Delete user."""
        pass


class InMemoryRBACStore(RBACStore):
    """In-memory RBAC storage (for development)."""

    def __init__(self):
        # Initialize with predefined roles
        self._roles: Dict[str, Role] = PREDEFINED_ROLES.copy()
        self._users: Dict[str, User] = {}

    async def get_role(self, role_id: str) -> Optional[Role]:
        return self._roles.get(role_id)

    async def create_role(self, role: Role) -> Role:
        self._roles[role.role_id] = role
        logger.info(f"Created role: {role.role_id} ({role.name})")
        return role

    async def update_role(self, role: Role) -> Role:
        role.updated_at = datetime.utcnow()
        self._roles[role.role_id] = role
        return role

    async def delete_role(self, role_id: str) -> bool:
        if role_id in self._roles:
            del self._roles[role_id]
            logger.info(f"Deleted role: {role_id}")
            return True
        return False

    async def get_user(self, user_id: str) -> Optional[User]:
        return self._users.get(user_id)

    async def create_user(self, user: User) -> User:
        self._users[user.user_id] = user
        logger.info(f"Created user: {user.user_id} ({user.username})")
        return user

    async def update_user(self, user: User) -> User:
        self._users[user.user_id] = user
        return user

    async def delete_user(self, user_id: str) -> bool:
        if user_id in self._users:
            del self._users[user_id]
            logger.info(f"Deleted user: {user_id}")
            return True
        return False


class AccessControl:
    """
    Access control enforcement.

    Checks if a user has permission to perform an action on a resource.
    """

    def __init__(self, store: Optional[RBACStore] = None):
        self.store = store or InMemoryRBACStore()

    async def check_permission(
        self,
        user_id: str,
        permission: Permission,
        resource: Resource,
    ) -> bool:
        """
        Check if user has permission on resource.

        Returns:
            True if allowed, False otherwise
        """
        user = await self.store.get_user(user_id)
        if not user:
            return False

        # Check direct grants first
        for grant in user.direct_grants:
            if grant.allows(permission, resource):
                logger.debug(f"Access granted via direct grant: {user_id} -> {permission.value} on {resource}")
                return True

        # Check role grants
        for role_id in user.roles:
            role = await self.store.get_role(role_id)
            if not role:
                continue

            # Check role's grants
            if await self._check_role_permission(role, permission, resource):
                logger.debug(f"Access granted via role '{role_id}': {user_id} -> {permission.value} on {resource}")
                return True

        logger.debug(f"Access denied: {user_id} -> {permission.value} on {resource}")
        return False

    async def _check_role_permission(
        self,
        role: Role,
        permission: Permission,
        resource: Resource,
    ) -> bool:
        """Check if role has permission (including inherited roles)."""
        # Check this role's grants
        for grant in role.grants:
            if grant.allows(permission, resource):
                return True

            # Check for admin permission (grants all)
            if grant.permission == Permission.SYSTEM_ADMIN:
                return True

        # Check parent roles
        for parent_id in role.parent_roles:
            parent = await self.store.get_role(parent_id)
            if parent and await self._check_role_permission(parent, permission, resource):
                return True

        return False

    async def require_permission(
        self,
        user_id: str,
        permission: Permission,
        resource: Resource,
    ):
        """
        Require permission (raise exception if denied).

        Raises:
            PermissionDenied if user lacks permission
        """
        if not await self.check_permission(user_id, permission, resource):
            raise PermissionDenied(
                f"User '{user_id}' lacks permission '{permission.value}' on resource '{resource}'"
            )

    async def get_user_permissions(self, user_id: str) -> List[PermissionGrant]:
        """Get all effective permissions for a user."""
        user = await self.store.get_user(user_id)
        if not user:
            return []

        permissions = []

        # Add direct grants
        permissions.extend(user.direct_grants)

        # Add role grants
        for role_id in user.roles:
            role = await self.store.get_role(role_id)
            if role:
                permissions.extend(await self._get_role_permissions(role))

        return permissions

    async def _get_role_permissions(self, role: Role) -> List[PermissionGrant]:
        """Get all permissions from role (including inherited)."""
        permissions = list(role.grants)

        # Add parent role permissions
        for parent_id in role.parent_roles:
            parent = await self.store.get_role(parent_id)
            if parent:
                permissions.extend(await self._get_role_permissions(parent))

        return permissions


class PermissionDenied(Exception):
    """Exception raised when permission is denied."""
    pass


# Global access control instance
_access_control: Optional[AccessControl] = None


def get_access_control() -> AccessControl:
    """Get global access control instance."""
    global _access_control
    if _access_control is None:
        _access_control = AccessControl()
    return _access_control


__all__ = [
    "Permission",
    "ResourceType",
    "Resource",
    "ResourcePattern",
    "PermissionGrant",
    "Role",
    "User",
    "RBACStore",
    "InMemoryRBACStore",
    "AccessControl",
    "PermissionDenied",
    "PREDEFINED_ROLES",
    "get_access_control",
]
