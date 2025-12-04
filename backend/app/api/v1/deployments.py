from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List
from app.database import get_db
from app.api.deps import get_current_user
from app.models.rbac import User
from app.models.deployment import Deployment, DeploymentStatus
from app.schemas.deployment import DeploymentCreate, DeploymentResponse
from app.core.casbin import get_enforcer
from casbin import Enforcer

router = APIRouter(prefix="/deployments", tags=["deployments"])

@router.get("/", response_model=List[DeploymentResponse])
async def list_deployments(
    search: str = None,
    status: str = None,
    cloud_provider: str = None,
    plugin_id: str = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    enforcer: Enforcer = Depends(get_enforcer)
):
    """
    List deployments with optional search and filtering.
    
    - search: Search across name, plugin_id, stack_name (case-insensitive)
    - status: Filter by deployment status (active, provisioning, failed, deleted)
    - cloud_provider: Filter by cloud provider (aws, gcp, azure)
    - plugin_id: Filter by specific plugin ID
    """
    from sqlalchemy import or_
    
    # Admin sees all, engineer sees only their own
    user_id = str(current_user.id)
    
    # Base query based on permissions
    if enforcer.enforce(user_id, "deployments", "list"):
        query = select(Deployment)
    elif enforcer.enforce(user_id, "deployments", "list:own"):
        query = select(Deployment).where(Deployment.user_id == current_user.id)
    else:
        raise HTTPException(status_code=403, detail="Permission denied")
    
    # Apply search filter
    if search:
        search_pattern = f"%{search}%"
        query = query.where(
            or_(
                Deployment.name.ilike(search_pattern),
                Deployment.plugin_id.ilike(search_pattern),
                Deployment.stack_name.ilike(search_pattern),
                Deployment.region.ilike(search_pattern)
            )
        )
    
    # Apply status filter
    if status:
        query = query.where(Deployment.status == status)
    
    # Apply cloud provider filter
    if cloud_provider:
        query = query.where(Deployment.cloud_provider.ilike(f"%{cloud_provider}%"))
    
    # Apply plugin_id filter
    if plugin_id:
        query = query.where(Deployment.plugin_id == plugin_id)
    
    # Order by created_at descending (newest first)
    query = query.order_by(Deployment.created_at.desc())
    
    result = await db.execute(query)
    deployments = result.scalars().all()
    
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
    from app.core.utils import get_or_404, raise_permission_denied
    deployment = await get_or_404(db, Deployment, deployment_id, resource_name="Deployment")
    
    # Check if user has permission to view this deployment
    user_id = str(current_user.id)
    if not (enforcer.enforce(user_id, "deployments", "list") or 
            (enforcer.enforce(user_id, "deployments", "list:own") and deployment.user_id == current_user.id)):
        raise_permission_denied("view this deployment")
    
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


@router.post("/{deployment_id}/retry", status_code=status.HTTP_202_ACCEPTED)
async def retry_deployment(
    deployment_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    enforcer: Enforcer = Depends(get_enforcer)
):
    """Retry a failed deployment by re-queuing the same job"""
    from app.core.utils import get_or_404, raise_permission_denied
    from app.models.plugins import Job, JobStatus, JobLog
    from app.models import PluginVersion
    
    deployment = await get_or_404(db, Deployment, deployment_id, resource_name="Deployment")
    
    # Check ownership or admin permission
    user_id = str(current_user.id)
    if not (enforcer.enforce(user_id, "deployments", "update") or 
            (enforcer.enforce(user_id, "deployments", "update:own") and deployment.user_id == current_user.id)):
        raise_permission_denied("retry this deployment")
    
    # Only allow retry for failed deployments
    if deployment.status != DeploymentStatus.FAILED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot retry deployment with status '{deployment.status}'. Only failed deployments can be retried."
        )
    
    # Find the latest failed job for this deployment
    job_result = await db.execute(
        select(Job).where(Job.deployment_id == deployment.id).order_by(Job.created_at.desc())
    )
    latest_job = job_result.scalars().first()
    
    if not latest_job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No job found for this deployment"
        )
    
    # Get plugin version info
    plugin_version = await db.get(PluginVersion, latest_job.plugin_version_id)
    if not plugin_version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plugin version not found"
        )
    
    # Reset job status
    latest_job.status = JobStatus.PENDING
    latest_job.finished_at = None
    latest_job.outputs = None
    
    # Reset deployment status
    deployment.status = DeploymentStatus.PROVISIONING
    
    # Add retry log entry
    retry_log = JobLog(
        job_id=latest_job.id,
        level="INFO",
        message=f"Job retry initiated by {current_user.email}"
    )
    db.add(retry_log)
    
    await db.commit()
    await db.refresh(latest_job)
    
    # Auto-select credentials based on plugin's cloud provider
    credential_name = None
    cloud_provider = plugin_version.manifest.get("cloud_provider")
    
    if cloud_provider and cloud_provider != "unknown":
        from app.models import CloudProvider, CloudCredential
        try:
            provider_enum = CloudProvider(cloud_provider)
            cred_result = await db.execute(
                select(CloudCredential).where(CloudCredential.provider == provider_enum)
            )
            credential = cred_result.scalar_one_or_none()
            if credential:
                credential_name = credential.name
        except ValueError:
            pass
    
    # Re-queue the same job
    from app.worker import provision_infrastructure
    try:
        provision_infrastructure.delay(
            job_id=latest_job.id,
            plugin_id=deployment.plugin_id,
            version=deployment.version,
            inputs=latest_job.inputs,
            credential_name=credential_name,
            deployment_id=str(deployment.id)
        )
        
        return {
            "message": "Deployment retry initiated",
            "job_id": latest_job.id,
            "deployment_id": str(deployment_id),
            "status": "accepted"
        }
    except Exception as e:
        from app.logger import logger
        logger.error(f"Error queuing retry task for deployment {deployment_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initiate deployment retry: {str(e)}"
        )


@router.delete("/{deployment_id}", status_code=status.HTTP_202_ACCEPTED)
async def destroy_deployment(
    deployment_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    enforcer: Enforcer = Depends(get_enforcer)
):
    from app.core.utils import get_or_404, raise_permission_denied
    deployment = await get_or_404(db, Deployment, deployment_id, resource_name="Deployment")
    
    # Check ownership or admin permission
    user_id = str(current_user.id)
    if not (enforcer.enforce(user_id, "deployments", "delete") or 
            (enforcer.enforce(user_id, "deployments", "delete:own") and deployment.user_id == current_user.id)):
        raise_permission_denied("delete this deployment")
    
    # Trigger Celery task to destroy infrastructure
    from app.worker import destroy_infrastructure
    try:
        task = destroy_infrastructure.delay(str(deployment_id))
        
        return {
            "message": "Infrastructure destruction initiated",
            "task_id": task.id,
            "deployment_id": str(deployment_id),
            "status": "accepted"
        }
    except Exception as e:
        # Log error but still return success - the task might have been queued
        from app.logger import logger
        logger.error(f"Error queuing destroy task for deployment {deployment_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initiate infrastructure destruction: {str(e)}"
        )

