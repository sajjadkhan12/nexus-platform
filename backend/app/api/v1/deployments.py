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
    # Ideally we use has_permission(current_user, Permission.DEPLOYMENTS_LIST)
    
    # Check if user has admin permission
    if has_permission(current_user, Permission.DEPLOYMENTS_LIST):
        result = await db.execute(select(Deployment))
        deployments = result.scalars().all()
    elif has_permission(current_user, Permission.DEPLOYMENTS_LIST_OWN):
        result = await db.execute(select(Deployment).where(Deployment.user_id == current_user.id))
        deployments = result.scalars().all()
    else:
        raise HTTPException(status_code=403, detail="Permission denied")
    
    return deployments

@router.post("/", response_model=DeploymentResponse)
async def create_deployment(
    deployment: DeploymentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Check permission
    if not has_permission(current_user, Permission.DEPLOYMENTS_CREATE):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    new_deployment = Deployment(
        **deployment.dict(),
        user_id=current_user.id
    )
    db.add(new_deployment)
    await db.commit()
    await db.refresh(new_deployment)
    
    return new_deployment

@router.get("/{deployment_id}", response_model=DeploymentResponse)
async def get_deployment(
    deployment_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(Deployment).where(Deployment.id == deployment_id))
    deployment = result.scalars().first()
    
    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")
    
    # Check if user has permission to view this deployment
    if not (has_permission(current_user, Permission.DEPLOYMENTS_LIST) or 
            (has_permission(current_user, Permission.DEPLOYMENTS_LIST_OWN) and deployment.user_id == current_user.id)):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    return deployment


@router.delete("/{deployment_id}")
async def destroy_deployment(
    deployment_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(Deployment).where(Deployment.id == deployment_id))
    deployment = result.scalars().first()
    
    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")
    
    # Check ownership or admin permission
    if not (has_permission(current_user, Permission.DEPLOYMENTS_DELETE) or 
            (has_permission(current_user, Permission.DEPLOYMENTS_DELETE_OWN) and deployment.user_id == current_user.id)):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    # Trigger Celery task to destroy infrastructure
    from app.worker import destroy_infrastructure
    task = destroy_infrastructure.delay(str(deployment_id))
    
    return {
        "message": "Infrastructure destruction initiated",
        "task_id": task.id,
        "deployment_id": str(deployment_id)
    }

