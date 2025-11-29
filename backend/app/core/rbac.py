from typing import List
from fastapi import HTTPException, status
from app.models.rbac import User

class Permission:
    """Permission constants for RBAC"""
    
    # User permissions
    USERS_LIST = "users:list"
    USERS_CREATE = "users:create"
    USERS_READ = "users:read"
    USERS_UPDATE = "users:update"
    USERS_DELETE = "users:delete"
    USERS_MANAGE_ROLES = "users:manage-roles"
    PROFILE_READ = "profile:read"
    PROFILE_UPDATE = "profile:update"
    PROFILE_DELETE = "profile:delete"

    # Role permissions
    ROLES_LIST = "roles:list"
    ROLES_CREATE = "roles:create"
    ROLES_READ = "roles:read"
    ROLES_UPDATE = "roles:update"
    ROLES_DELETE = "roles:delete"

    # Group permissions
    GROUPS_LIST = "groups:list"
    GROUPS_CREATE = "groups:create"
    GROUPS_READ = "groups:read"
    GROUPS_UPDATE = "groups:update"
    GROUPS_DELETE = "groups:delete"
    GROUPS_MANAGE_MEMBERS = "groups:manage-members"
    GROUPS_MANAGE_ROLES = "groups:manage-roles"

    # Deployment permissions
    DEPLOYMENTS_LIST = "deployments:list"
    DEPLOYMENTS_CREATE = "deployments:create"
    DEPLOYMENTS_READ = "deployments:read"
    DEPLOYMENTS_UPDATE = "deployments:update"
    DEPLOYMENTS_DELETE = "deployments:delete"
    DEPLOYMENTS_LIST_OWN = "deployments:list:own"
    DEPLOYMENTS_READ_OWN = "deployments:read:own"
    DEPLOYMENTS_UPDATE_OWN = "deployments:update:own"
    DEPLOYMENTS_DELETE_OWN = "deployments:delete:own"

    # Permission permissions
    PERMISSIONS_LIST = "permissions:list"

    # Audit log permissions
    AUDIT_LIST = "audit:list"
    AUDIT_READ = "audit:read"

    # Plugin permissions
    PLUGINS_LIST = "plugins:list"
    PLUGINS_UPLOAD = "plugins:upload"
    PLUGINS_DELETE = "plugins:delete"




def has_permission(user: User, permission_slug: str) -> bool:
    """Check if a user has a specific permission via their roles"""
    for role in user.roles:
        for permission in role.permissions:
            if permission.slug == permission_slug:
                return True
    return False


def require_permission(user: User, permission_slug: str) -> None:
    """Raise exception if user doesn't have required permission"""
    if not has_permission(user, permission_slug):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permission denied: {permission_slug} required"
        )
