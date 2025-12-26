"""Deployment history and rollback endpoints"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import datetime, timezone
import uuid as uuid_lib

from app.database import get_db
from app.api.deps import get_current_user, OrgAwareEnforcer, get_org_aware_enforcer
from app.models.rbac import User
from app.models.deployment import Deployment, DeploymentStatus, DeploymentHistory
from app.models.plugins import Job, JobStatus, JobLog, PluginVersion
from app.core.utils import get_or_404, raise_permission_denied
from app.logger import logger

router = APIRouter()

@router.get("/{deployment_id}/history")
async def get_deployment_history(
    deployment_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    enforcer: OrgAwareEnforcer = Depends(get_org_aware_enforcer)
):
    """
    Get deployment history - all versions/changes for a deployment.
    Returns list of history entries ordered by version number (newest first).
    """
    from app.schemas.deployment import DeploymentHistoryResponse
    
    deployment = await get_or_404(db, Deployment, deployment_id, resource_name="Deployment")
    
    # Check permissions - use same permission check as get_deployment endpoint
    # If user can view the deployment, they can view its history
    from app.core.authorization import check_permission
    from app.models.business_unit import BusinessUnitMember
    from sqlalchemy.orm import selectinload
    
    # Get user's active business unit
    business_unit_id = None
    if current_user.active_business_unit_id:
        business_unit_id = current_user.active_business_unit_id
    
    # Check if user has list permission
    has_list_permission = await check_permission(
        current_user,
        "business_unit:deployments:list",
        business_unit_id,
        db,
        enforcer.enforcer if hasattr(enforcer, 'enforcer') else enforcer
    )
    
    # Check if user has own deployments list permission
    has_list_own = await check_permission(
        current_user,
        "user:deployments:list:own",
        None,
        db,
        enforcer.enforcer if hasattr(enforcer, 'enforcer') else enforcer
    )
    
    if not has_list_permission and not (has_list_own and deployment.user_id == current_user.id):
        raise_permission_denied("view deployment history")
    
    # Get history entries
    history_result = await db.execute(
        select(DeploymentHistory)
        .where(DeploymentHistory.deployment_id == deployment.id)
        .order_by(DeploymentHistory.version_number.desc())
    )
    history_entries = history_result.scalars().all()
    
    # Convert to response format
    history_list = []
    for entry in history_entries:
        history_list.append({
            "id": str(entry.id),
            "version_number": entry.version_number,
            "inputs": entry.inputs,
            "outputs": entry.outputs,
            "status": entry.status,
            "job_id": entry.job_id,
            "created_at": entry.created_at.isoformat() if entry.created_at else None,
            "created_by": entry.created_by,
            "description": entry.description
        })
    
    return {"history": history_list}

@router.post("/{deployment_id}/rollback/{version_number}", status_code=status.HTTP_202_ACCEPTED)
async def rollback_deployment(
    deployment_id: str,
    version_number: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    enforcer: OrgAwareEnforcer = Depends(get_org_aware_enforcer)
):
    """
    Rollback a deployment to a previous version.
    Creates a new update job with the inputs from the specified version.
    """
    deployment = await get_or_404(db, Deployment, deployment_id, resource_name="Deployment")
    
    # Check if deployment is deleted or being deleted - locked and cannot be rolled back
    if deployment.status == DeploymentStatus.DELETED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot rollback a deleted deployment. Deleted deployments are locked and read-only."
        )
    if deployment.status == DeploymentStatus.DELETING:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot rollback a deployment that is being deleted. Please wait for the deletion to complete."
        )
    
    # Check permissions
    from app.core.authorization import check_permission
    
    has_update_permission = False
    if deployment.business_unit_id:
        has_update_permission = await check_permission(
            current_user,
            "business_unit:deployments:update",
            deployment.business_unit_id,
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
        raise_permission_denied("rollback this deployment")
    
    # Only allow rollback for active deployments
    if deployment.status != DeploymentStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot rollback deployment with status '{deployment.status}'. Only active deployments can be rolled back."
        )
    
    # Check if an update is already in progress
    if deployment.update_status == "updating":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An update is already in progress for this deployment. Please wait for it to complete."
        )
    
    # Get the history entry for the specified version
    history_result = await db.execute(
        select(DeploymentHistory)
        .where(
            DeploymentHistory.deployment_id == deployment.id,
            DeploymentHistory.version_number == version_number
        )
    )
    history_entry = history_result.scalar_one_or_none()
    
    if not history_entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Version {version_number} not found in deployment history"
        )
    
    # Get plugin version
    plugin_version_result = await db.execute(
        select(PluginVersion).where(
            PluginVersion.plugin_id == deployment.plugin_id,
            PluginVersion.version == deployment.version
        )
    )
    plugin_version = plugin_version_result.scalar_one_or_none()
    
    if not plugin_version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plugin version not found"
        )
    
    # Only infrastructure deployments can be rolled back via this endpoint
    if deployment.deployment_type != "infrastructure":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only infrastructure deployments can be rolled back via this endpoint"
        )
    
    # Create a new job for the rollback
    rollback_job = Job(
        id=str(uuid_lib.uuid4()),
        plugin_version_id=plugin_version.id,
        deployment_id=deployment.id,
        status=JobStatus.PENDING,
        triggered_by=current_user.email,
        inputs=history_entry.inputs.copy(),  # Use inputs from the history version
        retry_count=0
    )
    db.add(rollback_job)
    
    # Update deployment tracking fields
    deployment.update_status = "updating"
    deployment.last_update_job_id = rollback_job.id
    deployment.last_update_error = None
    deployment.last_update_attempted_at = datetime.now(timezone.utc)
    
    # Add log entry
    rollback_log = JobLog(
        job_id=rollback_job.id,
        level="INFO",
        message=f"Deployment rollback to version {version_number} initiated by {current_user.email}"
    )
    db.add(rollback_log)
    
    await db.commit()
    await db.refresh(rollback_job)
    await db.refresh(deployment)
    
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
    
    # Queue rollback job to Celery worker
    from app.workers import celery_app
    try:
        celery_app.send_task(
            "provision_infrastructure",
            args=[rollback_job.id, deployment.plugin_id, deployment.version,
                  history_entry.inputs, credential_name, str(deployment.id)]
        )
        
        return {
            "message": f"Deployment rollback to version {version_number} initiated",
            "job_id": rollback_job.id,
            "deployment_id": str(deployment_id),
            "version_number": version_number,
            "status": "accepted"
        }
    except Exception as e:
        logger.error(f"Error queuing rollback task for deployment {deployment_id}: {str(e)}")
        # Reset update status on error
        deployment.update_status = None
        deployment.last_update_job_id = None
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initiate deployment rollback: {str(e)}"
        )

