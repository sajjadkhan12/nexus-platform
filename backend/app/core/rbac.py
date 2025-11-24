from typing import List
from fastapi import HTTPException, status


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


# Role-based permission mapping
ROLE_PERMISSIONS = {
    "admin": [
        Permission.DEPLOYMENT_CREATE,
        Permission.DEPLOYMENT_READ_ALL,
        Permission.DEPLOYMENT_UPDATE_ALL,
        Permission.DEPLOYMENT_DELETE_ALL,
        Permission.PLUGIN_READ,
        Permission.PLUGIN_MANAGE,
        Permission.USER_READ_ALL,
        Permission.USER_MANAGE,
        Permission.ROLE_MANAGE,
        Permission.COST_READ_ALL,
        Permission.SETTINGS_READ,
        Permission.SETTINGS_MANAGE,
    ],
    "engineer": [
        Permission.DEPLOYMENT_CREATE,
        Permission.DEPLOYMENT_READ_OWN,
        Permission.DEPLOYMENT_UPDATE_OWN,
        Permission.DEPLOYMENT_DELETE_OWN,
        Permission.PLUGIN_READ,
        Permission.USER_READ_OWN,
        Permission.COST_READ_OWN,
        Permission.SETTINGS_READ,
    ]
}


def has_permission(user_role: str, permission: str) -> bool:
    """Check if a role has a specific permission"""
    return permission in ROLE_PERMISSIONS.get(user_role, [])


def get_user_permissions(user_role: str) -> List[str]:
    """Get all permissions for a user role"""
    return ROLE_PERMISSIONS.get(user_role, [])


def require_permission(user_role: str, permission: str) -> None:
    """Raise exception if user doesn't have required permission"""
    if not has_permission(user_role, permission):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permission denied: {permission} required"
        )
