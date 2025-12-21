"""
Helper functions to make multi-tenant enforcement easier
"""
from typing import Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.rbac import User
from app.core.organization import get_user_organization, get_organization_domain
from casbin import Enforcer


async def get_enforcement_context(
    current_user: User,
    db: AsyncSession
) -> Tuple[str, str]:
    """
    Get user_id and org_domain for enforcement checks.
    
    Returns:
        Tuple of (user_id, org_domain)
        
    Example:
        user_id, org_domain = await get_enforcement_context(current_user, db)
        if not enforcer.enforce(user_id, org_domain, "resource", "action"):
            raise HTTPException(403)
    """
    user_id = str(current_user.id)
    organization = await get_user_organization(current_user, db)
    org_domain = get_organization_domain(organization)
    return user_id, org_domain


async def check_permission(
    current_user: User,
    db: AsyncSession,
    enforcer: Enforcer,
    resource: str,
    action: str
) -> bool:
    """
    Check if user has permission for a resource and action.
    Automatically handles organization context.
    
    Args:
        current_user: Current authenticated user
        db: Database session
        enforcer: Casbin enforcer
        resource: Resource name (e.g., "plugins", "deployments")
        action: Action name (e.g., "read", "create", "delete")
        
    Returns:
        True if user has permission, False otherwise
    """
    user_id, org_domain = await get_enforcement_context(current_user, db)
    return enforcer.enforce(user_id, org_domain, resource, action)


async def require_permission(
    current_user: User,
    db: AsyncSession,
    enforcer: Enforcer,
    resource: str,
    action: str,
    error_message: str = None
):
    """
    Require user to have permission or raise HTTPException.
    Automatically handles organization context.
    
    Args:
        current_user: Current authenticated user
        db: Database session
        enforcer: Casbin enforcer
        resource: Resource name (e.g., "plugins", "deployments")
        action: Action name (e.g., "read", "create", "delete")
        error_message: Custom error message (optional)
        
    Raises:
        HTTPException: If user doesn't have permission
    """
    from fastapi import HTTPException, status
    
    if not await check_permission(current_user, db, enforcer, resource, action):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=error_message or f"Permission denied: {resource}:{action} required"
        )
