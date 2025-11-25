from typing import List
from fastapi import HTTPException, status
from app.models.rbac import User

class Permission:
    """Permission constants for RBAC"""
    
    # Deployment permissions
    DEPLOYMENT_CREATE = "deployment:create"
    DEPLOYMENT_READ_OWN = "deployment:read:own"
    DEPLOYMENT_READ_ALL = "deployment:read:all"
    DEPLOYMENT_UPDATE_OWN = "deployment:update:own"
    DEPLOYMENT_UPDATE_ALL = "deployment:update:all"
    DEPLOYMENT_DELETE_OWN = "deployment:delete:own"
    DEPLOYMENT_DELETE_ALL = "deployment:delete:all"
    
    # Plugin permissions
    PLUGIN_READ = "plugin:read"
    PLUGIN_MANAGE = "plugin:manage"
    
    # User permissions
    USER_READ_OWN = "user:read:own"
    USER_READ_ALL = "user:read:all"
    USER_MANAGE = "user:manage"
    
    # Role permissions
    ROLE_MANAGE = "role:manage"
    
    # Cost permissions
    COST_READ_OWN = "cost:read:own"
    COST_READ_ALL = "cost:read:all"
    
    # Settings permissions
    SETTINGS_READ = "settings:read"
    SETTINGS_MANAGE = "settings:manage"


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
