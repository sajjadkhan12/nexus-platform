from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List
from app.database import get_db
from app.api.deps import get_current_user
from app.models.rbac import User
from app.models.deployment import Deployment
from app.schemas.deployment import DeploymentCreate, DeploymentResponse
from app.core.rbac import has_permission, Permission

router = APIRouter(prefix="/deployments", tags=["deployments"])

@router.get("/", response_model=List[DeploymentResponse])
async def list_deployments(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Admin sees all, engineer sees only their own
    # We need to check permissions. For now, let's assume 'admin' role has all access
    # and 'engineer' has own access.
    # Ideally we use has_permission(current_user, Permission.DEPLOYMENT_READ_ALL)
    
    # Check if user has admin permission
    is_admin = has_permission(current_user, Permission.DEPLOYMENT_READ_ALL)
    
    if is_admin:
        result = await db.execute(select(Deployment))
        deployments = result.scalars().all()
    else:
        result = await db.execute(select(Deployment).where(Deployment.owner_id == current_user.id))
        deployments = result.scalars().all()
    
    return deployments

@router.post("/", response_model=DeploymentResponse)
async def create_deployment(
    deployment: DeploymentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Check permission
    if not has_permission(current_user, Permission.DEPLOYMENT_CREATE):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    new_deployment = Deployment(
        **deployment.dict(),
        owner_id=current_user.id
    )
    db.add(new_deployment)
    await db.commit()
    await db.refresh(new_deployment)
    
    return new_deployment

@router.delete("/{deployment_id}")
async def delete_deployment(
    deployment_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(Deployment).where(Deployment.id == deployment_id))
    deployment = result.scalars().first()
    
    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")
    
    # Check ownership or admin permission
    is_admin = has_permission(current_user, Permission.DEPLOYMENT_DELETE_ALL)
    
    if deployment.owner_id != current_user.id and not is_admin:
        raise HTTPException(status_code=403, detail="Permission denied")
    
    await db.delete(deployment)
    await db.commit()
    
    return {"message": "Deployment deleted successfully"}
