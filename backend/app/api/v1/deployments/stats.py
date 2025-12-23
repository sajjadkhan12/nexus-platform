"""Deployment statistics endpoints"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List

from app.database import get_db
from app.api.deps import get_current_user, OrgAwareEnforcer, get_org_aware_enforcer
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
    enforcer: OrgAwareEnforcer = Depends(get_org_aware_enforcer)
):
    """Get deployment counts grouped by environment"""
    # Check permissions
    user_id = str(current_user.id)
    query = select(
        Deployment.environment,
        func.count(Deployment.id).label('count')
    )
    
    if enforcer.enforce(user_id, "deployments", "list"):
        # Can see all deployments in organization
        pass
    elif enforcer.enforce(user_id, "deployments", "list:own"):
        # Can only see own deployments
        query = query.where(Deployment.user_id == current_user.id)
    else:
        raise HTTPException(status_code=403, detail="Permission denied")
    
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
    enforcer: OrgAwareEnforcer = Depends(get_org_aware_enforcer)
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
    
    # Filter by user if not admin
    if not enforcer.enforce(user_id, "deployments", "list"):
        # Only show tags from user's own deployments
        query = query.join(Deployment).where(Deployment.user_id == current_user.id)
    
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

