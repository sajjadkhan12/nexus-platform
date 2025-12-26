"""Deployment statistics endpoints"""
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional
import uuid

from app.database import get_db
from app.api.deps import get_current_user, OrgAwareEnforcer, get_org_aware_enforcer, get_active_business_unit
from app.models.rbac import User
from app.models.deployment import Deployment, DeploymentTag

router = APIRouter()

@router.get("/environments")
async def list_environments():
    """Get list of available environments"""
    from app.models.deployment import Environment
    
    return [
        {
            "name": env.value,
            "display": env.value.title(),
            "description": f"{env.value.title()} environment"
        }
        for env in Environment
    ]

@router.get("/stats/by-environment")
async def deployment_stats_by_environment(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    enforcer: OrgAwareEnforcer = Depends(get_org_aware_enforcer),
    business_unit_id: Optional[uuid.UUID] = Depends(get_active_business_unit)
):
    """Get deployment counts grouped by environment"""
    # Check permissions
    from app.core.authorization import check_permission
    
    has_list_permission = False
    if business_unit_id:
        has_list_permission = await check_permission(
            current_user,
            "business_unit:deployments:list",
            business_unit_id,
            db,
            enforcer.enforcer if hasattr(enforcer, 'enforcer') else enforcer
        )
    
    has_list_own = await check_permission(
        current_user,
        "user:deployments:list:own",
        None,
        db,
        enforcer.enforcer if hasattr(enforcer, 'enforcer') else enforcer
    )
    
    query = select(
        Deployment.environment,
        func.count(Deployment.id).label('count')
    )
    
    is_admin = has_list_permission
    
    if is_admin:
        # Can see all deployments in organization
        pass
    elif has_list_own:
        # Can only see own deployments
        query = query.where(Deployment.user_id == current_user.id)
    else:
        raise HTTPException(status_code=403, detail="Permission denied")
    
    # Apply business unit filter if provided
    # Admins can work without business unit (see all), regular users need business unit
    if business_unit_id:
        query = query.where(Deployment.business_unit_id == business_unit_id)
    elif not is_admin:
        # Regular users without business unit - show only unassigned deployments
        query = query.where(Deployment.business_unit_id.is_(None))
    
    query = query.group_by(Deployment.environment)
    result = await db.execute(query)
    
    stats = []
    for row in result:
        stats.append({
            "environment": row[0],
            "count": row[1]
        })
    
    return stats

@router.get("/stats/tags")
async def tag_usage_stats(
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    enforcer: OrgAwareEnforcer = Depends(get_org_aware_enforcer),
    business_unit_id: Optional[uuid.UUID] = Depends(get_active_business_unit)
):
    """Get most commonly used tags across all deployments"""
    # Check permissions
    user_id = str(current_user.id)
    
    # Base query
    query = select(
        DeploymentTag.key,
        DeploymentTag.value,
        func.count(DeploymentTag.id).label('usage_count')
    )
    
    from app.core.authorization import check_permission
    
    has_list_permission = False
    if business_unit_id:
        has_list_permission = await check_permission(
            current_user,
            "business_unit:deployments:list",
            business_unit_id,
            db,
            enforcer.enforcer if hasattr(enforcer, 'enforcer') else enforcer
        )
    
    is_admin = has_list_permission
    
    # Filter by user if not admin
    if not is_admin:
        # Only show tags from user's own deployments
        query = query.join(Deployment).where(Deployment.user_id == current_user.id)
    else:
        query = query.join(Deployment)
    
    # Apply business unit filter if provided
    # Admins can work without business unit (see all), regular users need business unit
    if business_unit_id:
        query = query.where(Deployment.business_unit_id == business_unit_id)
    elif not is_admin:
        # Regular users without business unit - show only unassigned deployments
        query = query.where(Deployment.business_unit_id.is_(None))
    
    query = (query
             .group_by(DeploymentTag.key, DeploymentTag.value)
             .order_by(func.count(DeploymentTag.id).desc())
             .limit(limit))
    
    result = await db.execute(query)
    
    stats = []
    for row in result:
        stats.append({
            "key": row[0],
            "value": row[1],
            "count": row[2]
        })
    
    return stats

