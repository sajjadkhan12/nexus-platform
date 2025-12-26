"""Deployment tag management endpoints"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete as sql_delete
from typing import Dict, List

from app.database import get_db
from app.api.deps import get_current_user, OrgAwareEnforcer, get_org_aware_enforcer
from app.models.rbac import User
from app.models.deployment import Deployment, DeploymentTag
from app.services.tag_validator import validate_tag_key, validate_tag_value

router = APIRouter()

@router.get("/tags/keys")
async def list_tag_keys(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get list of unique tag keys used across all deployments (for autocomplete)"""
    result = await db.execute(
        select(DeploymentTag.key).distinct().order_by(DeploymentTag.key)
    )
    
    keys = [row[0] for row in result]
    return {"keys": keys}

@router.get("/tags/values/{tag_key}")
async def list_tag_values(
    tag_key: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get list of unique values for a specific tag key (for autocomplete)"""
    result = await db.execute(
        select(DeploymentTag.value)
        .where(DeploymentTag.key == tag_key)
        .distinct()
        .order_by(DeploymentTag.value)
    )
    
    values = [row[0] for row in result]
    return {"key": tag_key, "values": values}

@router.post("/{deployment_id}/tags")
async def add_deployment_tags(
    deployment_id: str,
    tags: Dict[str, str],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    enforcer: OrgAwareEnforcer = Depends(get_org_aware_enforcer)
):
    """Add or update tags for a deployment"""
    from uuid import UUID
    
    try:
        deployment_uuid = UUID(deployment_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid deployment ID format")
    
    # Get deployment
    result = await db.execute(select(Deployment).where(Deployment.id == deployment_uuid))
    deployment = result.scalar_one_or_none()
    
    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")
    
    # Check permissions
    from app.core.authorization import check_permission
    
    # Get user's active business unit
    business_unit_id = None
    if current_user.active_business_unit_id:
        business_unit_id = current_user.active_business_unit_id
    
    has_update_permission = False
    if business_unit_id:
        has_update_permission = await check_permission(
            current_user,
            "business_unit:deployments:update",
            business_unit_id,
            db,
            enforcer.enforcer if hasattr(enforcer, 'enforcer') else enforcer
        )
    
    has_update_own = await check_permission(
        current_user,
        "user:deployments:update:own",
        None,
        db,
        enforcer.enforcer if hasattr(enforcer, 'enforcer') else enforcer
    )
    
    if not has_update_permission and not (has_update_own and deployment.user_id == current_user.id):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    # Validate each tag
    for key, value in tags.items():
        is_valid_key, key_error = validate_tag_key(key)
        if not is_valid_key:
            raise HTTPException(status_code=400, detail=f"Invalid tag key '{key}': {key_error}")
        
        is_valid_value, value_error = validate_tag_value(value)
        if not is_valid_value:
            raise HTTPException(status_code=400, detail=f"Invalid tag value for '{key}': {value_error}")
    
    # Add or update tags
    tags_added = []
    for key, value in tags.items():
        # Check if tag already exists
        existing_tag_result = await db.execute(
            select(DeploymentTag).where(
                DeploymentTag.deployment_id == deployment.id,
                DeploymentTag.key == key
            )
        )
        existing_tag = existing_tag_result.scalar_one_or_none()
        
        if existing_tag:
            # Update existing tag
            existing_tag.value = value
            tags_added.append({"key": key, "value": value, "action": "updated"})
        else:
            # Create new tag
            new_tag = DeploymentTag(
                deployment_id=deployment.id,
                key=key,
                value=value
            )
            db.add(new_tag)
            tags_added.append({"key": key, "value": value, "action": "created"})
    
    await db.commit()
    
    # Refresh deployment to get updated tags
    await db.refresh(deployment)
    
    return {
        "message": "Tags updated successfully",
        "tags_modified": tags_added,
        "total_tags": len(deployment.tags)
    }

@router.delete("/{deployment_id}/tags/{tag_key}")
async def remove_deployment_tag(
    deployment_id: str,
    tag_key: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    enforcer: OrgAwareEnforcer = Depends(get_org_aware_enforcer)
):
    """Remove a specific tag from deployment"""
    from uuid import UUID
    
    try:
        deployment_uuid = UUID(deployment_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid deployment ID format")
    
    # Get deployment
    result = await db.execute(select(Deployment).where(Deployment.id == deployment_uuid))
    deployment = result.scalar_one_or_none()
    
    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")
    
    # Check permissions
    from app.core.authorization import check_permission
    
    # Get user's active business unit
    business_unit_id = None
    if current_user.active_business_unit_id:
        business_unit_id = current_user.active_business_unit_id
    
    has_update_permission = False
    if business_unit_id:
        has_update_permission = await check_permission(
            current_user,
            "business_unit:deployments:update",
            business_unit_id,
            db,
            enforcer.enforcer if hasattr(enforcer, 'enforcer') else enforcer
        )
    
    has_update_own = await check_permission(
        current_user,
        "user:deployments:update:own",
        None,
        db,
        enforcer.enforcer if hasattr(enforcer, 'enforcer') else enforcer
    )
    
    if not has_update_permission and not (has_update_own and deployment.user_id == current_user.id):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    # Delete the tag
    delete_result = await db.execute(
        sql_delete(DeploymentTag).where(
            DeploymentTag.deployment_id == deployment_uuid,
            DeploymentTag.key == tag_key
        )
    )
    
    if delete_result.rowcount == 0:
        raise HTTPException(status_code=404, detail=f"Tag '{tag_key}' not found on this deployment")
    
    await db.commit()
    
    return {"message": f"Tag '{tag_key}' removed successfully"}

