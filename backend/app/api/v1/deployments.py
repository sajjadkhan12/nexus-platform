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
from app.logger import logger
from casbin import Enforcer

router = APIRouter(prefix="/deployments", tags=["deployments"])

@router.get("/{deployment_id}/ci-cd-status")
async def get_cicd_status(
    deployment_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get CI/CD status for a microservice deployment.
    Returns current GitHub Actions workflow status.
    """
    from uuid import UUID
    from app.services.github_actions_service import github_actions_service
    from app.config import settings
    
    try:
        deployment_uuid = UUID(deployment_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid deployment ID format")
    
    result = await db.execute(select(Deployment).where(Deployment.id == deployment_uuid))
    deployment = result.scalar_one_or_none()
    
    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")
    
    # Check permissions - user must own the deployment or be admin
    if deployment.user_id != current_user.id:
        from app.core.casbin import get_enforcer
        enforcer = get_enforcer()
        user_id = str(current_user.id)
        if not enforcer.enforce(user_id, "deployments", "read"):
            raise HTTPException(status_code=403, detail="Permission denied")
    
    # Only microservices have CI/CD status
    if deployment.deployment_type != "microservice":
        raise HTTPException(
            status_code=400,
            detail="CI/CD status is only available for microservice deployments"
        )
    
    if not deployment.github_repo_name:
        return {
            "ci_cd_status": None,
            "ci_cd_run_id": None,
            "ci_cd_run_url": None,
            "message": "Repository not yet created"
        }
    
    # Get GitHub token (use platform token for now)
    github_token = settings.GITHUB_TOKEN if hasattr(settings, 'GITHUB_TOKEN') else ""
    if not github_token:
        return {
            "ci_cd_status": deployment.ci_cd_status,
            "ci_cd_run_id": deployment.ci_cd_run_id,
            "ci_cd_run_url": deployment.ci_cd_run_url,
            "message": "GitHub token not configured"
        }
    
    # Get latest workflow status
    try:
        ci_cd_status = github_actions_service.get_latest_workflow_status(
            repo_full_name=deployment.github_repo_name,
            user_github_token=github_token,
            branch="main"  # Default branch
        )
        
        if ci_cd_status:
            # Update deployment record with latest status
            deployment.ci_cd_status = ci_cd_status.get("ci_cd_status")
            deployment.ci_cd_run_id = ci_cd_status.get("ci_cd_run_id")
            deployment.ci_cd_run_url = ci_cd_status.get("ci_cd_run_url")
            from datetime import datetime
            deployment.ci_cd_updated_at = datetime.utcnow()
            db.add(deployment)
            await db.commit()
            
            return ci_cd_status
        else:
            return {
                "ci_cd_status": deployment.ci_cd_status or "pending",
                "ci_cd_run_id": deployment.ci_cd_run_id,
                "ci_cd_run_url": deployment.ci_cd_run_url,
                "message": "No workflow runs found"
            }
    except Exception as e:
        logger.error(f"Error fetching CI/CD status: {e}")
        return {
            "ci_cd_status": deployment.ci_cd_status,
            "ci_cd_run_id": deployment.ci_cd_run_id,
            "ci_cd_run_url": deployment.ci_cd_run_url,
            "error": str(e)
        }

@router.get("/{deployment_id}/repository")
async def get_repository_info(
    deployment_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get repository information for a microservice deployment.
    """
    from uuid import UUID
    from app.services.microservice_service import microservice_service
    from app.config import settings
    
    try:
        deployment_uuid = UUID(deployment_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid deployment ID format")
    
    result = await db.execute(select(Deployment).where(Deployment.id == deployment_uuid))
    deployment = result.scalar_one_or_none()
    
    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")
    
    # Check permissions
    if deployment.user_id != current_user.id:
        from app.core.casbin import get_enforcer
        enforcer = get_enforcer()
        user_id = str(current_user.id)
        if not enforcer.enforce(user_id, "deployments", "read"):
            raise HTTPException(status_code=403, detail="Permission denied")
    
    if deployment.deployment_type != "microservice":
        raise HTTPException(
            status_code=400,
            detail="Repository info is only available for microservice deployments"
        )
    
    if not deployment.github_repo_name:
        raise HTTPException(
            status_code=404,
            detail="Repository not yet created for this deployment"
        )
    
    # Get repository info from GitHub
    github_token = settings.GITHUB_TOKEN if hasattr(settings, 'GITHUB_TOKEN') else ""
    if not github_token:
        raise HTTPException(
            status_code=500,
            detail="GitHub token not configured"
        )
    
    try:
        repo_info = microservice_service.get_repository_info(
            repo_full_name=deployment.github_repo_name,
            user_github_token=github_token
        )
        
        return {
            "full_name": repo_info.get("full_name"),
            "name": repo_info.get("name"),
            "clone_url": repo_info.get("clone_url"),
            "ssh_url": repo_info.get("ssh_url"),
            "html_url": repo_info.get("html_url"),
            "default_branch": repo_info.get("default_branch"),
            "private": repo_info.get("private"),
            "description": repo_info.get("description"),
            "created_at": repo_info.get("created_at"),
            "updated_at": repo_info.get("updated_at"),
        }
    except Exception as e:
        logger.error(f"Error fetching repository info: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch repository information: {str(e)}"
        )

@router.post("/{deployment_id}/sync-ci-cd")
async def sync_cicd_status(
    deployment_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Manually sync CI/CD status from GitHub Actions.
    """
    from uuid import UUID
    from app.services.github_actions_service import github_actions_service
    from app.config import settings
    from datetime import datetime
    
    try:
        deployment_uuid = UUID(deployment_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid deployment ID format")
    
    result = await db.execute(select(Deployment).where(Deployment.id == deployment_uuid))
    deployment = result.scalar_one_or_none()
    
    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")
    
    # Check permissions
    if deployment.user_id != current_user.id:
        from app.core.casbin import get_enforcer
        enforcer = get_enforcer()
        user_id = str(current_user.id)
        if not enforcer.enforce(user_id, "deployments", "update"):
            raise HTTPException(status_code=403, detail="Permission denied")
    
    if deployment.deployment_type != "microservice" or not deployment.github_repo_name:
        raise HTTPException(
            status_code=400,
            detail="CI/CD sync is only available for microservice deployments with repositories"
        )
    
    github_token = settings.GITHUB_TOKEN if hasattr(settings, 'GITHUB_TOKEN') else ""
    if not github_token:
        raise HTTPException(status_code=500, detail="GitHub token not configured")
    
    try:
        ci_cd_status = github_actions_service.get_latest_workflow_status(
            repo_full_name=deployment.github_repo_name,
            user_github_token=github_token,
            branch="main"
        )
        
        if ci_cd_status:
            deployment.ci_cd_status = ci_cd_status.get("ci_cd_status")
            deployment.ci_cd_run_id = ci_cd_status.get("ci_cd_run_id")
            deployment.ci_cd_run_url = ci_cd_status.get("ci_cd_run_url")
            deployment.ci_cd_updated_at = datetime.utcnow()
            db.add(deployment)
            await db.commit()
            
            return {
                "message": "CI/CD status synced successfully",
                "ci_cd_status": deployment.ci_cd_status,
                "ci_cd_run_id": deployment.ci_cd_run_id,
                "ci_cd_run_url": deployment.ci_cd_run_url
            }
        else:
            return {
                "message": "No workflow runs found",
                "ci_cd_status": deployment.ci_cd_status
            }
    except Exception as e:
        logger.error(f"Error syncing CI/CD status: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to sync CI/CD status: {str(e)}"
        )

@router.get("/")
async def list_deployments(
    search: str = None,
    status: str = None,
    cloud_provider: str = None,
    plugin_id: str = None,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    enforcer: Enforcer = Depends(get_enforcer)
):
    """
    List deployments with optional search, filtering, and pagination.
    
    - search: Search across name, plugin_id, stack_name (case-insensitive)
    - status: Filter by deployment status (active, provisioning, failed, deleted)
    - cloud_provider: Filter by cloud provider (aws, gcp, azure)
    - plugin_id: Filter by specific plugin ID
    - skip: Number of records to skip (for pagination)
    - limit: Maximum number of deployments to return per page
    """
    from sqlalchemy import or_, func
    
    # Admin sees all, engineer sees only their own
    user_id = str(current_user.id)
    
    # Base query based on permissions
    base_filter = None
    if enforcer.enforce(user_id, "deployments", "list"):
        base_query = select(Deployment)
        base_count_query = select(func.count(Deployment.id))
    elif enforcer.enforce(user_id, "deployments", "list:own"):
        base_filter = Deployment.user_id == current_user.id
        base_query = select(Deployment).where(base_filter)
        base_count_query = select(func.count(Deployment.id)).where(base_filter)
    else:
        raise HTTPException(status_code=403, detail="Permission denied")
    
    # Apply search filter
    if search:
        search_pattern = f"%{search}%"
        search_filter = or_(
            Deployment.name.ilike(search_pattern),
            Deployment.plugin_id.ilike(search_pattern),
            Deployment.stack_name.ilike(search_pattern),
            Deployment.region.ilike(search_pattern)
        )
        base_query = base_query.where(search_filter)
        base_count_query = base_count_query.where(search_filter)
    
    # Apply status filter
    if status:
        base_query = base_query.where(Deployment.status == status)
        base_count_query = base_count_query.where(Deployment.status == status)
    
    # Apply cloud provider filter
    if cloud_provider:
        base_query = base_query.where(Deployment.cloud_provider.ilike(f"%{cloud_provider}%"))
        base_count_query = base_count_query.where(Deployment.cloud_provider.ilike(f"%{cloud_provider}%"))
    
    # Apply plugin_id filter
    if plugin_id:
        base_query = base_query.where(Deployment.plugin_id == plugin_id)
        base_count_query = base_count_query.where(Deployment.plugin_id == plugin_id)
    
    # Order by created_at descending (newest first)
    base_query = base_query.order_by(Deployment.created_at.desc())
    
    # Get total count
    total_result = await db.execute(base_count_query)
    total = total_result.scalar() or 0
    
    # Apply pagination
    query = base_query.offset(skip).limit(limit)
    
    result = await db.execute(query)
    deployments = result.scalars().all()
    
    # Serialize deployments using the response model
    deployment_items = [DeploymentResponse.model_validate(d) for d in deployments]
    
    return {
        "items": deployment_items,
        "total": total,
        "skip": skip,
        "limit": limit
    }

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
    response = DeploymentResponse.model_validate(deployment)
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
    from app.models import Job, JobStatus, PluginVersion
    from sqlalchemy import select
    import uuid
    
    deployment = await get_or_404(db, Deployment, deployment_id, resource_name="Deployment")
    
    # Check ownership or admin permission
    user_id = str(current_user.id)
    if not (enforcer.enforce(user_id, "deployments", "delete") or 
            (enforcer.enforce(user_id, "deployments", "delete:own") and deployment.user_id == current_user.id)):
        raise_permission_denied("delete this deployment")
    
    # Get plugin version to create a deletion job
    plugin_version_result = await db.execute(
        select(PluginVersion).where(
            PluginVersion.plugin_id == deployment.plugin_id,
            PluginVersion.version == deployment.version
        )
    )
    plugin_version = plugin_version_result.scalar_one_or_none()
    
    # Create a job for deletion tracking (similar to provisioning)
    if plugin_version:
        deletion_job = Job(
            id=str(uuid.uuid4()),
            plugin_version_id=plugin_version.id,
            deployment_id=deployment.id,
            status=JobStatus.PENDING,
            triggered_by=current_user.email,
            inputs={"action": "destroy", "deployment_id": str(deployment_id), "deployment_name": deployment.name}
        )
        db.add(deletion_job)
        await db.commit()
        job_id = deletion_job.id
    else:
        job_id = None
    
    # Route to appropriate destroy task based on deployment type
    deployment_type = deployment.deployment_type or "infrastructure"
    
    if deployment_type == "microservice":
        # Microservice deletion - simpler, just delete the deployment record
        # Optionally could delete GitHub repo, but for now just mark as deleted
        from app.worker import destroy_microservice
        try:
            task = destroy_microservice.delay(str(deployment_id))
            
            return {
                "message": "Microservice deletion initiated",
                "task_id": task.id,
                "job_id": job_id,
                "deployment_id": str(deployment_id),
                "status": "accepted"
            }
        except Exception as e:
            from app.logger import logger
            logger.error(f"Error queuing destroy task for microservice {deployment_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to initiate microservice deletion: {str(e)}"
            )
    else:
        # Infrastructure deletion - use Pulumi to destroy resources
        from app.worker import destroy_infrastructure
        try:
            task = destroy_infrastructure.delay(str(deployment_id))
            
            return {
                "message": "Infrastructure destruction initiated",
                "task_id": task.id,
                "job_id": job_id,
                "deployment_id": str(deployment_id),
                "status": "accepted"
            }
        except Exception as e:
            from app.logger import logger
            logger.error(f"Error queuing destroy task for deployment {deployment_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to initiate infrastructure destruction: {str(e)}"
            )

