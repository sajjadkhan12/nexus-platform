"""Deployment CRUD operations"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import or_, func, and_
from sqlalchemy.orm import selectinload
from typing import Dict, Optional
from datetime import datetime, timezone
import uuid as uuid_lib

from app.database import get_db
from app.api.deps import get_current_user, OrgAwareEnforcer, get_org_aware_enforcer
from app.models.rbac import User
from app.models.deployment import Deployment, DeploymentStatus, DeploymentHistory, DeploymentTag
from app.models.plugins import Job, JobStatus, JobLog, PluginVersion
from app.schemas.deployment import DeploymentCreate, DeploymentResponse, DeploymentUpdateRequest
from app.core.utils import get_or_404, raise_permission_denied
from app.logger import logger

router = APIRouter()

@router.get("/")
async def list_deployments(
    search: str = None,
    status: str = None,
    cloud_provider: str = None,
    plugin_id: str = None,
    environment: str = None,
    tags: str = None,
    user_id: str = Query(None, description="Filter by user ID (admin only)", include_in_schema=True),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of records to return"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    enforcer: OrgAwareEnforcer = Depends(get_org_aware_enforcer)
):
    """
    List deployments with optional search, filtering, and pagination.
    
    - search: Search across name, plugin_id, stack_name (case-insensitive)
    - status: Filter by deployment status (active, provisioning, failed, deleted)
    - cloud_provider: Filter by cloud provider (aws, gcp, azure)
    - plugin_id: Filter by specific plugin ID
    - environment: Filter by environment (development, staging, production)
    - tags: Filter by tags (format: "key1:value1,key2:value2")
    - skip: Number of records to skip (for pagination)
    - limit: Maximum number of deployments to return per page
    """
    # Admin sees all, engineer sees only their own
    # NOTE: user_id parameter is the query param for filtering by user (admin only)
    # current_user_id_str is the current logged-in user's ID for permission checks
    current_user_id_str = str(current_user.id)
    
    # Base query based on permissions - eager load tags
    # Check if user has "list" permission (admins) or "list:own" permission (regular users)
    has_list_all = enforcer.enforce(current_user_id_str, "deployments", "list")
    has_list_own = enforcer.enforce(current_user_id_str, "deployments", "list:own")
    
    if has_list_all:
        # Admin: can see all deployments
        base_query = select(Deployment).options(selectinload(Deployment.tags))
        base_count_query = select(func.count(Deployment.id))
    elif has_list_own:
        # Regular user: can only see their own deployments
        base_filter = Deployment.user_id == current_user.id
        base_query = select(Deployment).options(selectinload(Deployment.tags)).where(base_filter)
        base_count_query = select(func.count(Deployment.id)).where(base_filter)
    else:
        raise HTTPException(status_code=403, detail="Permission denied")
    
    # Apply search filter with input validation
    if search:
        # Validate search input length to prevent DoS
        if len(search) > 100:
            raise HTTPException(
                status_code=400,
                detail="Search query too long. Maximum 100 characters allowed."
            )
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
    
    # Apply environment filter
    if environment:
        base_query = base_query.where(Deployment.environment == environment)
        base_count_query = base_count_query.where(Deployment.environment == environment)
    
    # Apply user_id filter (admin only) - this is the query parameter, not the current user's ID
    # Only process if user_id query parameter is provided, not None, not empty, and not just whitespace
    if user_id is not None and str(user_id).strip():
        filter_user_id_str = str(user_id).strip()
        # Only allow admins to filter by user_id query parameter
        if not has_list_all:
            raise HTTPException(status_code=403, detail="Only administrators can filter by user_id")
        
        try:
            from uuid import UUID
            filter_user_uuid = UUID(filter_user_id_str)
            base_query = base_query.where(Deployment.user_id == filter_user_uuid)
            base_count_query = base_count_query.where(Deployment.user_id == filter_user_uuid)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid user_id format")
    
    # Apply tags filter - Optimized with JOIN instead of multiple IN subqueries
    if tags:
        # Parse tags: "team:backend,purpose:api"
        tag_filters = {}
        for tag_pair in tags.split(','):
            if ':' in tag_pair:
                key, value = tag_pair.split(':', 1)
                tag_filters[key.strip()] = value.strip()
        
        if tag_filters:
            # Optimized: Use JOIN-based approach for better performance
            # Create filter conditions for all tags
            tag_conditions = [
                and_(DeploymentTag.key == key, DeploymentTag.value == value)
                for key, value in tag_filters.items()
            ]
            
            # For multiple tags, we need deployments that have ALL tags
            # Use a subquery that groups by deployment_id and counts matching tags
            tag_match_subquery = (
                select(DeploymentTag.deployment_id)
                .where(or_(*tag_conditions))  # Deployment has at least one matching tag
                .group_by(DeploymentTag.deployment_id)
                .having(func.count(DeploymentTag.deployment_id) == len(tag_filters))  # Has all tags
            )
            
            # Apply to both queries
            base_query = base_query.where(Deployment.id.in_(tag_match_subquery))
            base_count_query = base_count_query.where(Deployment.id.in_(tag_match_subquery))
    
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
    enforcer: OrgAwareEnforcer = Depends(get_org_aware_enforcer)
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
    enforcer: OrgAwareEnforcer = Depends(get_org_aware_enforcer)
):
    from uuid import UUID
    
    # Eagerly load tags to avoid lazy loading issues
    try:
        deployment_uuid = UUID(deployment_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid deployment ID format")
    
    result = await db.execute(
        select(Deployment)
        .options(selectinload(Deployment.tags))
        .where(Deployment.id == deployment_uuid)
    )
    deployment = result.scalar_one_or_none()
    
    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")
    
    # Check if user has permission to view this deployment
    user_id = str(current_user.id)
    if not (enforcer.enforce(user_id, "deployments", "list") or
            (enforcer.enforce(user_id, "deployments", "list:own") and deployment.user_id == current_user.id)):
        raise_permission_denied("view this deployment")
    
    # Get latest job for this deployment
    job_result = await db.execute(
        select(Job).where(Job.deployment_id == deployment.id).order_by(Job.created_at.desc())
    )
    latest_job = job_result.scalars().first()
    
    # Convert to response model and add job_id
    response = DeploymentResponse.model_validate(deployment)
    if latest_job:
        response.job_id = latest_job.id
        
    return response

@router.put("/{deployment_id}", status_code=status.HTTP_202_ACCEPTED)
async def update_deployment(
    deployment_id: str,
    update_request: DeploymentUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    enforcer: OrgAwareEnforcer = Depends(get_org_aware_enforcer)
):
    """
    Update an existing active deployment by modifying its inputs.
    Creates a new job to update the Pulumi stack with new configuration.
    """
    deployment = await get_or_404(db, Deployment, deployment_id, resource_name="Deployment")
    
    # Check ownership or admin permission
    user_id = str(current_user.id)
    if not (enforcer.enforce(user_id, "deployments", "update") or
            (enforcer.enforce(user_id, "deployments", "update:own") and deployment.user_id == current_user.id)):
        raise_permission_denied("update this deployment")
    
    # Only allow updates for active deployments
    if deployment.status != DeploymentStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot update deployment with status '{deployment.status}'. Only active deployments can be updated."
        )
    
    # Check if an update is already in progress
    if deployment.update_status == "updating":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An update is already in progress for this deployment. Please wait for it to complete."
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
    
    # Only infrastructure deployments can be updated via this endpoint
    if deployment.deployment_type != "infrastructure":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only infrastructure deployments can be updated via this endpoint"
        )
    
    # Create a new job for the update
    update_job = Job(
        id=str(uuid_lib.uuid4()),
        plugin_version_id=plugin_version.id,
        deployment_id=deployment.id,
        status=JobStatus.PENDING,
        triggered_by=current_user.email,
        inputs=update_request.inputs,
        retry_count=0
    )
    db.add(update_job)
    
    # Update deployment tracking fields
    deployment.update_status = "updating"
    deployment.last_update_job_id = update_job.id
    deployment.last_update_error = None
    deployment.last_update_attempted_at = datetime.now(timezone.utc)
    
    # Update optional fields if provided
    if update_request.cost_center is not None:
        deployment.cost_center = update_request.cost_center
    if update_request.project_code is not None:
        deployment.project_code = update_request.project_code
    
    # Update tags if provided
    if update_request.tags is not None:
        # Delete existing tags
        existing_tags = await db.execute(
            select(DeploymentTag).where(DeploymentTag.deployment_id == deployment.id)
        )
        for tag in existing_tags.scalars().all():
            await db.delete(tag)
        
        # Add new tags
        for key, value in update_request.tags.items():
            tag = DeploymentTag(
                deployment_id=deployment.id,
                key=key,
                value=value
            )
            db.add(tag)
    
    # Add log entry
    update_log = JobLog(
        job_id=update_job.id,
        level="INFO",
        message=f"Deployment update initiated by {current_user.email}"
    )
    db.add(update_log)
    
    await db.commit()
    await db.refresh(update_job)
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
    
    # Queue update job to Celery worker
    from app.workers import celery_app
    try:
        celery_app.send_task(
            "provision_infrastructure",
            args=[update_job.id, deployment.plugin_id, deployment.version, 
                  update_request.inputs, credential_name, str(deployment.id)]
        )
        
        return {
            "message": "Deployment update initiated",
            "job_id": update_job.id,
            "deployment_id": str(deployment_id),
            "status": "accepted"
        }
    except Exception as e:
        logger.error(f"Error queuing update task for deployment {deployment_id}: {str(e)}")
        # Reset update status on error
        deployment.update_status = None
        deployment.last_update_job_id = None
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initiate deployment update: {str(e)}"
        )

@router.delete("/{deployment_id}", status_code=status.HTTP_202_ACCEPTED)
async def destroy_deployment(
    deployment_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    enforcer: OrgAwareEnforcer = Depends(get_org_aware_enforcer)
):
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
    
    # Create a job for deletion tracking
    job_id = None
    if plugin_version:
        deletion_job = Job(
            id=str(uuid_lib.uuid4()),
            plugin_version_id=plugin_version.id,
            deployment_id=deployment.id,
            status=JobStatus.PENDING,
            triggered_by=current_user.email,
            inputs={"action": "destroy", "deployment_id": str(deployment_id), "deployment_name": deployment.name}
        )
        db.add(deletion_job)
        await db.commit()
        job_id = deletion_job.id
    
    # Route to appropriate destroy task based on deployment type
    deployment_type = deployment.deployment_type or "infrastructure"
    
    if deployment_type == "microservice":
        from app.workers import celery_app
        try:
            logger.info(f"Initiating microservice deletion for deployment {deployment_id}")
            task = celery_app.send_task("destroy_microservice", args=[str(deployment_id)])
            
            return {
                "message": "Microservice deletion initiated",
                "task_id": task.id,
                "job_id": job_id,
                "deployment_id": str(deployment_id),
                "status": "accepted"
            }
        except Exception as e:
            logger.error(f"Error initiating microservice deletion: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Failed to initiate deletion: {str(e)}"
            )
    else:
        from app.workers import celery_app
        try:
            logger.info(f"Initiating infrastructure deletion for deployment {deployment_id}, job_id: {job_id}")
            task = celery_app.send_task("destroy_infrastructure", args=[str(deployment_id)])
            logger.info(f"Celery task created successfully: task_id={task.id}, deployment_id={deployment_id}, job_id={job_id}")
            
            return {
                "message": "Infrastructure deletion initiated",
                "task_id": task.id,
                "job_id": job_id,
                "deployment_id": str(deployment_id),
                "status": "accepted"
            }
        except Exception as e:
            logger.error(f"Error initiating infrastructure deletion: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Failed to initiate deletion: {str(e)}"
            )

@router.post("/{deployment_id}/retry", status_code=status.HTTP_202_ACCEPTED)
async def retry_deployment(
    deployment_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    enforcer: OrgAwareEnforcer = Depends(get_org_aware_enforcer)
):
    """Retry a failed deployment by re-queuing the same job"""
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
    from app.workers import celery_app
    try:
        celery_app.send_task(
            "provision_infrastructure",
            args=[latest_job.id, deployment.plugin_id, deployment.version,
                  latest_job.inputs, credential_name, str(deployment.id)]
        )
        
        return {
            "message": "Deployment retry initiated",
            "job_id": latest_job.id,
            "deployment_id": str(deployment_id),
            "status": "accepted"
        }
    except Exception as e:
        logger.error(f"Error queuing retry task for deployment {deployment_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initiate deployment retry: {str(e)}"
        )

