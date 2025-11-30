from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List
from app.database import get_db
from app.api.deps import get_current_user
from app.models.rbac import User
from app.models.deployment import Deployment
from app.schemas.deployment import DeploymentCreate, DeploymentResponse
from app.core.casbin import get_enforcer
from casbin import Enforcer

router = APIRouter(prefix="/deployments", tags=["deployments"])

@router.get("/", response_model=List[DeploymentResponse])
async def list_deployments(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    enforcer: Enforcer = Depends(get_enforcer)
):
    # Admin sees all, engineer sees only their own
    user_id = str(current_user.id)
    
    # Check if user has admin permission
    if enforcer.enforce(user_id, "deployments", "list"):
        result = await db.execute(select(Deployment))
        deployments = result.scalars().all()
    elif enforcer.enforce(user_id, "deployments", "list:own"):
        result = await db.execute(select(Deployment).where(Deployment.user_id == current_user.id))
        deployments = result.scalars().all()
    else:
        raise HTTPException(status_code=403, detail="Permission denied")
    
    return deployments

@router.post("/", response_model=DeploymentResponse)
async def create_deployment(
    deployment: DeploymentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    enforcer: Enforcer = Depends(get_enforcer)
):
    # Check permission
    user_id = str(current_user.id)
    if not enforcer.enforce(user_id, "deployments", "create"):
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
    current_user: User = Depends(get_current_user),
    enforcer: Enforcer = Depends(get_enforcer)
):
    result = await db.execute(select(Deployment).where(Deployment.id == deployment_id))
    deployment = result.scalars().first()
    
    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")
    
    # Check if user has permission to view this deployment
    user_id = str(current_user.id)
    if not (enforcer.enforce(user_id, "deployments", "list") or 
            (enforcer.enforce(user_id, "deployments", "list:own") and deployment.user_id == current_user.id)):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    # Get latest job for this deployment
    from app.models.plugins import Job
    job_result = await db.execute(
        select(Job).where(Job.deployment_id == deployment.id).order_by(Job.created_at.desc())
    )
    latest_job = job_result.scalars().first()
    
    # Convert to response model and add job_id
    response = DeploymentResponse.from_orm(deployment)
    if latest_job:
        response.job_id = latest_job.id
        
    return response


@router.delete("/{deployment_id}")
async def destroy_deployment(
    deployment_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    enforcer: Enforcer = Depends(get_enforcer)
):
    result = await db.execute(select(Deployment).where(Deployment.id == deployment_id))
    deployment = result.scalars().first()
    
    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")
    
    # Check ownership or admin permission
    user_id = str(current_user.id)
    if not (enforcer.enforce(user_id, "deployments", "delete") or 
            (enforcer.enforce(user_id, "deployments", "delete:own") and deployment.user_id == current_user.id)):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    # Trigger Celery task to destroy infrastructure
    from app.worker import destroy_infrastructure
    task = destroy_infrastructure.delay(str(deployment_id))
    
    return {
        "message": "Infrastructure destruction initiated",
        "task_id": task.id,
        "deployment_id": str(deployment_id)
    }

