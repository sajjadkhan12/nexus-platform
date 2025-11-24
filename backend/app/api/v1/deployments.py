from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.deployment import Deployment
from app.schemas.deployment import DeploymentCreate, DeploymentUpdate, DeploymentResponse
from app.core.rbac import Permission, has_permission, require_permission

router = APIRouter(prefix="/deployments", tags=["deployments"])


@router.get("/", response_model=List[DeploymentResponse])
async def list_deployments(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List deployments - admin sees all, engineer sees only their own"""
    if has_permission(current_user.role, Permission.DEPLOYMENT_READ_ALL):
        deployments = db.query(Deployment).all()
    else:
        deployments = db.query(Deployment).filter(
            Deployment.owner_id == current_user.id
        ).all()
    
    return deployments


@router.get("/{deployment_id}", response_model=DeploymentResponse)
async def get_deployment(
    deployment_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get deployment by ID"""
    deployment = db.query(Deployment).filter(Deployment.id == deployment_id).first()
    
    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")
    
    # Check ownership or admin permission
    if deployment.owner_id != current_user.id:
        require_permission(current_user.role, Permission.DEPLOYMENT_READ_ALL)
    
    return deployment


@router.post("/", response_model=DeploymentResponse, status_code=status.HTTP_201_CREATED)
async def create_deployment(
    deployment: DeploymentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new deployment"""
    require_permission(current_user.role, Permission.DEPLOYMENT_CREATE)
    
    new_deployment = Deployment(
        **deployment.dict(),
        owner_id=current_user.id
    )
    db.add(new_deployment)
    db.commit()
    db.refresh(new_deployment)
    
    return new_deployment


@router.put("/{deployment_id}", response_model=DeploymentResponse)
async def update_deployment(
    deployment_id: str,
    deployment_update: DeploymentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a deployment"""
    deployment = db.query(Deployment).filter(Deployment.id == deployment_id).first()
    
    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")
    
    # Check ownership or admin permission
    if deployment.owner_id != current_user.id:
        require_permission(current_user.role, Permission.DEPLOYMENT_UPDATE_ALL)
    else:
        require_permission(current_user.role, Permission.DEPLOYMENT_UPDATE_OWN)
    
    update_data = deployment_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(deployment, field, value)
    
    db.commit()
    db.refresh(deployment)
    
    return deployment


@router.delete("/{deployment_id}")
async def delete_deployment(
    deployment_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a deployment"""
    deployment = db.query(Deployment).filter(Deployment.id == deployment_id).first()
    
    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")
    
    # Check ownership or admin permission
    if deployment.owner_id != current_user.id:
        require_permission(current_user.role, Permission.DEPLOYMENT_DELETE_ALL)
    else:
        require_permission(current_user.role, Permission.DEPLOYMENT_DELETE_OWN)
    
    db.delete(deployment)
    db.commit()
    
    return {"message": "Deployment deleted successfully"}
