"""Provisioning and job management API"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
import uuid

from app.database import get_db
from app.models import (
    Job, JobLog, User, Deployment, DeploymentStatus, PluginVersion, JobStatus,
    Plugin, PluginAccess
)
from app.schemas.plugins import (
    ProvisionRequest, 
    JobResponse, 
    JobLogResponse,
    BulkDeleteJobsRequest,
    BulkDeleteJobsResponse
)
from fastapi import Request
from typing import Optional
import uuid
from app.api.deps import get_current_user, is_allowed, is_allowed_bu, get_current_active_superuser, get_active_business_unit, is_platform_admin

router = APIRouter(prefix="/provision", tags=["Provisioning"])

@router.post("/", response_model=JobResponse, status_code=status.HTTP_202_ACCEPTED)
async def provision(
    request: ProvisionRequest,
    current_user: User = Depends(is_allowed_bu("business_unit:plugins:provision")),
    db: AsyncSession = Depends(get_db),
    business_unit_id: Optional[uuid.UUID] = Depends(get_active_business_unit),
):
    """
    Trigger a provisioning job
    Returns immediately with job ID for async execution
    Requires: plugins:provision permission + environment-specific permission
    """
    from app.api.deps import get_org_aware_enforcer
    from app.logger import logger
    
    try:
        # 1. VALIDATE ENVIRONMENT PERMISSION (Strict enforcement)
        # Get enforcer with proper dependency injection
        enforcer_instance = await get_org_aware_enforcer(current_user, db)
        # Use new permission format: business_unit:deployments:create:{environment}
        permission_slug = f"business_unit:deployments:create:{request.environment}"
        
        logger.info(f"User {current_user.email} attempting to provision to {request.environment} environment")
        
        from app.core.authorization import check_permission
        has_permission = await check_permission(
            current_user,
            permission_slug,
            business_unit_id,
            db,
            enforcer_instance.enforcer if hasattr(enforcer_instance, 'enforcer') else enforcer_instance
        )
        
        if not has_permission:
            logger.warning(f"User {current_user.email} denied permission to deploy to {request.environment}. Required: {permission_slug}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"You don't have permission to deploy to {request.environment} environment. Required permission: {permission_slug}"
            )
    
        # 2. VALIDATE REQUIRED TAGS
        from app.services.tag_validator import validate_tags
        is_valid, error_msg = validate_tags(request.tags, request.environment)
        if not is_valid:
            logger.warning(f"Tag validation failed for user {current_user.email}: {error_msg}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Tag validation failed: {error_msg}"
            )
    
        # 3. Validate plugin version exists
        result = await db.execute(
            select(PluginVersion).where(
                PluginVersion.plugin_id == request.plugin_id,
                PluginVersion.version == request.version
            )
        )
        plugin_version = result.scalar_one_or_none()
        
        if not plugin_version:
            logger.warning(f"Plugin version not found: {request.plugin_id} version {request.version}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Plugin {request.plugin_id} version {request.version} not found"
            )
        
        # Get plugin to check deployment type and access
        plugin_result = await db.execute(
            select(Plugin).where(Plugin.id == request.plugin_id)
        )
        plugin = plugin_result.scalar_one_or_none()
        
        if not plugin:
            logger.warning(f"Plugin not found: {request.plugin_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Plugin {request.plugin_id} not found"
            )
        
        # Determine deployment type
        deployment_type = plugin.deployment_type or "infrastructure"
        
        if plugin.is_locked:
            # Check if user is admin - admins always have access
            from app.models.plugins import PluginAccessRequest, AccessRequestStatus
            
            # Use the enforcer_instance we already have
            user_id = str(current_user.id)
            # Check if user is platform admin or has plugins:upload permission
            from app.core.authorization import check_platform_permission
            has_upload_permission = await check_platform_permission(current_user, "platform:plugins:upload", db, enforcer_instance.enforcer if hasattr(enforcer_instance, 'enforcer') else enforcer_instance)
            is_admin = await is_platform_admin(current_user, db, enforcer_instance) or has_upload_permission
            
            if not is_admin:
                # Check if user has approved access in the current business unit
                # First check PluginAccess (granted access)
                from app.models.plugins import PluginAccess
                access_result = await db.execute(
                    select(PluginAccess).where(
                        PluginAccess.plugin_id == request.plugin_id,
                        PluginAccess.user_id == current_user.id,
                        PluginAccess.business_unit_id == business_unit_id
                    )
                )
                user_access = access_result.scalar_one_or_none()
                
                # If no direct access, check for approved request
                if not user_access:
                    access_request_result = await db.execute(
                        select(PluginAccessRequest).where(
                            PluginAccessRequest.plugin_id == request.plugin_id,
                            PluginAccessRequest.user_id == current_user.id,
                            PluginAccessRequest.business_unit_id == business_unit_id,
                            PluginAccessRequest.status == AccessRequestStatus.APPROVED
                        )
                    )
                    user_access = access_request_result.scalar_one_or_none()
                
                if not user_access:
                    logger.warning(f"User {current_user.email} denied access to locked plugin {request.plugin_id} in business unit {business_unit_id}")
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Plugin {request.plugin_id} is locked. Please request access from an administrator or business unit owner for this business unit."
                    )
        
        # OIDC-only: No static credentials, always use OIDC token exchange
        credential_name = None
        # Get cloud provider from plugin manifest
        cloud_provider = plugin_version.manifest.get("cloud_provider", "unknown")
        
        logger.info(f"Creating provisioning job for user {current_user.email}, plugin {request.plugin_id}, environment {request.environment}")
        
        # Create job
        # Store business_unit_id in inputs so we can filter jobs even after deployment is deleted
        job_inputs = request.inputs.copy() if request.inputs else {}
        if business_unit_id:
            job_inputs["_business_unit_id"] = str(business_unit_id)
        
        job = Job(
            id=str(uuid.uuid4()),
            plugin_version_id=plugin_version.id,
            status=JobStatus.PENDING,
            triggered_by=current_user.email,
            inputs=job_inputs
        )
        db.add(job)
        
        # Add initial log with OIDC auto-exchange info
        credential_msg = ""
        if cloud_provider and cloud_provider != "unknown":
            # Check if OIDC is configured for this provider
            from app.config import settings
            oidc_configured = False
            if cloud_provider.lower() == "aws" and settings.AWS_ROLE_ARN:
                oidc_configured = True
            elif cloud_provider.lower() == "gcp" and settings.GCP_SERVICE_ACCOUNT_EMAIL:
                oidc_configured = True
            elif cloud_provider.lower() == "azure" and settings.AZURE_CLIENT_ID:
                oidc_configured = True
            
            if oidc_configured:
                credential_msg = " (will auto-exchange OIDC token for credentials)"
            else:
                credential_msg = " (no credentials - deployment may fail)"
        else:
            credential_msg = " (no cloud provider specified)"
        
        log_entry = JobLog(
            job_id=job.id,
            level="INFO",
            message=f"Job created for {request.plugin_id}:{request.version}{credential_msg}"
        )
        db.add(log_entry)
        
        # Create Deployment record (PROVISIONING) with environment and metadata
        from app.models.deployment import DeploymentTag
        from app.models.business_unit import BusinessUnit
        
        # Get business unit name if business_unit_id is provided
        business_unit_name = None
        if business_unit_id:
            bu_result = await db.execute(
                select(BusinessUnit).where(BusinessUnit.id == business_unit_id)
            )
            business_unit = bu_result.scalar_one_or_none()
            if business_unit:
                business_unit_name = business_unit.name
        
        if deployment_type == "microservice":
            # Microservice deployment - simpler structure
            deployment_name = request.deployment_name or request.inputs.get("deployment_name") or request.inputs.get("name") or f"{request.plugin_id}-{job.id[:8]}"
            deployment = Deployment(
                name=deployment_name,
                plugin_id=request.plugin_id,
                version=request.version,
                status=DeploymentStatus.PROVISIONING,
                deployment_type="microservice",
                environment=request.environment,  # NEW
                cost_center=request.cost_center,  # NEW
                project_code=request.project_code,  # NEW
                user_id=current_user.id,
                business_unit_id=business_unit_id,  # Set business unit
                inputs=request.inputs,
            )
        else:
            # Infrastructure deployment - existing structure
            stack_name = f"{request.plugin_id}-{job.id[:8]}"
            deployment_name = request.deployment_name or request.inputs.get("bucket_name") or f"{request.plugin_id}-{job.id[:8]}"
            
            # Ensure deployment_name is used as bucket_name in inputs if not already set
            # This ensures the bucket gets the correct name from deployment name
            inputs_with_bucket_name = request.inputs.copy() if request.inputs else {}
            if deployment_name and "bucket_name" not in inputs_with_bucket_name:
                inputs_with_bucket_name["bucket_name"] = deployment_name
            if deployment_name and "name" not in inputs_with_bucket_name:
                inputs_with_bucket_name["name"] = deployment_name
            
            deployment = Deployment(
                name=deployment_name,
                plugin_id=request.plugin_id,
                version=request.version,
                status=DeploymentStatus.PROVISIONING,
                deployment_type="infrastructure",
                environment=request.environment,  # NEW
                cost_center=request.cost_center,  # NEW
                project_code=request.project_code,  # NEW
                user_id=current_user.id,
                business_unit_id=business_unit_id,  # Set business unit
                inputs=inputs_with_bucket_name,  # Use inputs with bucket_name set
                stack_name=stack_name,
                cloud_provider=cloud_provider or "unknown",
                region=inputs_with_bucket_name.get("location", "unknown")
            )
        db.add(deployment)
        await db.flush() # Get ID
        
        # Create tags for deployment
        tags_to_add = request.tags.copy() if request.tags else {}
        
        # Automatically add business_unit tag if business unit is selected
        # Only add tag if business unit is actually selected (not for admins without selection)
        if business_unit_name and "business_unit" not in tags_to_add:
            tags_to_add["business_unit"] = business_unit_name
        elif not business_unit_id:
            # If no business unit selected, don't add the tag
            # This allows admins to deploy without business unit
            pass
        
        for key, value in tags_to_add.items():
            tag = DeploymentTag(
                deployment_id=deployment.id,
                key=key,
                value=value
            )
            db.add(tag)
        
        # Link job to deployment
        job.deployment_id = deployment.id
        
        await db.commit()
        await db.refresh(job)
        await db.refresh(deployment)
        
        # Route to appropriate Celery task based on deployment type
        if deployment_type == "microservice":
            # Microservice provisioning
            from app.workers import provision_microservice
            deployment_name = request.inputs.get("deployment_name") or request.inputs.get("name") or deployment.name
            provision_microservice.delay(
                job_id=job.id,
                plugin_id=request.plugin_id,
                version=request.version,
                deployment_name=deployment_name,
                user_id=str(current_user.id),
                deployment_id=str(deployment.id)
            )
        else:
            # Infrastructure provisioning - existing flow
            from app.workers import provision_infrastructure
            provision_infrastructure.delay(
                job_id=job.id,
                plugin_id=request.plugin_id,
                version=request.version,
                inputs=request.inputs,
                credential_name=credential_name,
                deployment_id=str(deployment.id)
            )
        
        logger.info(f"Provisioning job {job.id} created successfully for user {current_user.email}")
        return job
    
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Error in provision endpoint for user {current_user.email}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create provisioning job: {str(e)}"
        )

@router.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get job status and details"""
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return job

@router.get("/jobs/{job_id}/logs", response_model=List[JobLogResponse])
async def get_job_logs(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get job logs"""
    # Verify job exists
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Get logs
    result = await db.execute(
        select(JobLog)
        .where(JobLog.job_id == job_id)
        .order_by(JobLog.timestamp)
    )
    logs = result.scalars().all()
    
    return logs

@router.get("/jobs")
async def list_jobs(
    job_id: str = None,
    email: str = None,
    start_date: str = None,
    end_date: str = None,
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    business_unit_id: Optional[uuid.UUID] = Depends(get_active_business_unit),
):
    """
    List recent jobs with optional filters and pagination
    
    Args:
        job_id: Filter by job ID (partial match)
        email: Filter by triggered_by email (partial match)
        start_date: Filter jobs created on or after this date (ISO format: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)
        end_date: Filter jobs created on or before this date (ISO format: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)
        skip: Number of records to skip (for pagination)
        limit: Maximum number of jobs to return per page
    """
    from datetime import datetime
    from sqlalchemy import func
    from app.models.deployment import Deployment
    from app.api.deps import get_org_aware_enforcer
    from app.core.casbin import get_enforcer
    from app.core.organization import get_user_organization, get_organization_domain
    from app.core.authorization import get_user_platform_roles
    
    # Check if user is admin (has platform admin role)
    enforcer_instance = get_enforcer()
    organization = await get_user_organization(current_user, db)
    org_domain = get_organization_domain(organization)
    platform_roles = await get_user_platform_roles(current_user, db, enforcer_instance, org_domain)
    is_admin = "admin" in platform_roles or "platform-admin" in platform_roles
    
    from app.logger import logger
    # Removed debug logging with user email
    
    # Base query for counting
    # When business_unit_id is provided (admin or regular user), filter by business unit
    # When no business_unit_id: admins see all jobs, regular users see jobs without business unit
    # Note: Jobs store business_unit_id in inputs._business_unit_id to handle unlinked jobs from deleted deployments
    if business_unit_id:
        # Filter by business unit - show jobs linked to deployments with this business unit
        # OR jobs that have the business_unit_id stored in their inputs (for unlinked jobs)
        from sqlalchemy import or_, cast, String
        from sqlalchemy.dialects.postgresql import JSONB
        bu_id_str = str(business_unit_id)
        
        # Check if business_unit_id matches in deployment OR in job inputs
        count_query = select(func.count(Job.id)).outerjoin(Deployment, Job.deployment_id == Deployment.id).where(
            (Deployment.business_unit_id == business_unit_id) |
            (cast(Job.inputs, JSONB)['_business_unit_id'].astext == bu_id_str)
        )
        # Filtering by business_unit_id
    elif not is_admin:
        # Regular users without business unit - show only jobs for deployments without business unit or jobs without deployment
        from sqlalchemy import or_
        count_query = select(func.count(Job.id)).outerjoin(Deployment, Job.deployment_id == Deployment.id).where(
            or_(Deployment.business_unit_id.is_(None), Job.deployment_id.is_(None))
        )
    else:
        # Admins without business unit selection - see all jobs
        count_query = select(func.count(Job.id))
    
    # Base query for data
    if business_unit_id:
        # Filter by business unit - show jobs linked to deployments with this business unit
        # OR jobs that have the business_unit_id stored in their inputs (for unlinked jobs)
        # This applies to both admins and regular users when they have a business unit selected
        from sqlalchemy import or_, cast, String
        from sqlalchemy.dialects.postgresql import JSONB
        bu_id_str = str(business_unit_id)
        
        # Check if business_unit_id matches in deployment OR in job inputs
        query = select(Job).outerjoin(Deployment, Job.deployment_id == Deployment.id).where(
            (Deployment.business_unit_id == business_unit_id) |
            (cast(Job.inputs, JSONB)['_business_unit_id'].astext == bu_id_str)
        ).order_by(Job.created_at.desc())
    elif not is_admin:
        # Regular users without business unit - show only jobs for deployments without business unit or jobs without deployment
        from sqlalchemy import or_
        query = select(Job).outerjoin(Deployment, Job.deployment_id == Deployment.id).where(
            or_(Deployment.business_unit_id.is_(None), Job.deployment_id.is_(None))
        ).order_by(Job.created_at.desc())
    else:
        # Admins without business unit selection - see all jobs
        query = select(Job).order_by(Job.created_at.desc())
    
    # Apply filters to both queries
    filters = []
    
    if job_id:
        filter_condition = Job.id.ilike(f"%{job_id}%")
        filters.append(filter_condition)
    
    if email:
        filter_condition = Job.triggered_by.ilike(f"%{email}%")
        filters.append(filter_condition)
    
    if start_date:
        try:
            try:
                start_datetime = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            except ValueError:
                start_datetime = datetime.fromisoformat(start_date)
            filter_condition = Job.created_at >= start_datetime
            filters.append(filter_condition)
        except ValueError:
            pass
    
    if end_date:
        try:
            try:
                end_datetime = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            except ValueError:
                end_datetime = datetime.fromisoformat(end_date)
            
            # If the datetime doesn't have a time component (date-only input),
            # set it to end of day to include all records from that day
            if end_datetime.hour == 0 and end_datetime.minute == 0 and end_datetime.second == 0 and end_datetime.microsecond == 0:
                end_datetime = end_datetime.replace(hour=23, minute=59, second=59)
            
            filter_condition = Job.created_at <= end_datetime
            filters.append(filter_condition)
        except ValueError:
            pass
    
    # Apply all filters
    if filters:
        for filter_condition in filters:
            query = query.where(filter_condition)
            count_query = count_query.where(filter_condition)
    
    # Get total count
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # Apply pagination
    query = query.offset(skip).limit(limit)
    
    # Get jobs
    result = await db.execute(query)
    jobs = result.scalars().all()
    
    return {
        "items": jobs,
        "total": total,
        "skip": skip,
        "limit": limit
    }

@router.delete("/jobs/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_job(
    job_id: str,
    current_user: User = Depends(is_allowed("platform:jobs:delete")),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a single job and its logs
    Requires: Admin access
    """
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Delete job (logs will be cascade deleted due to relationship)
    await db.delete(job)
    await db.commit()
    
    return None

@router.post("/jobs/{job_id}/replay", response_model=JobResponse, status_code=status.HTTP_202_ACCEPTED)
async def replay_dead_letter_job(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Replay a dead-letter job (manual remediation)
    Resets retry count and re-queues the job for execution
    Requires: plugins:provision permission
    """
    # Get the job
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    # Only allow replaying dead-letter jobs
    if job.status != JobStatus.DEAD_LETTER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Job is not in dead-letter state. Current status: {job.status}"
        )
    
    # Get plugin version
    plugin_version = await db.get(PluginVersion, job.plugin_version_id)
    if not plugin_version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plugin version not found"
        )
    
    # Reset job for replay
    job.status = JobStatus.PENDING
    job.retry_count = 0  # Reset retry count
    job.error_state = None
    job.error_message = None
    job.finished_at = None
    
    # Add replay log entry
    replay_log = JobLog(
        job_id=job.id,
        level="INFO",
        message=f"Job replay initiated by {current_user.email}. Retry count reset to 0."
    )
    db.add(replay_log)
    db.add(job)
    
    # Update deployment status if exists
    if job.deployment_id:
        deployment = await db.get(Deployment, job.deployment_id)
        if deployment:
            deployment.status = DeploymentStatus.PROVISIONING
            db.add(deployment)
    
    await db.commit()
    await db.refresh(job)
    
    # Re-queue the job
    from app.workers import provision_infrastructure
    
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
    
    try:
        provision_infrastructure.delay(
            job_id=job.id,
            plugin_id=plugin_version.plugin_id,
            version=plugin_version.version,
            inputs=job.inputs,
            credential_name=credential_name,
            deployment_id=str(job.deployment_id) if job.deployment_id else None
        )
        
        return job
    except Exception as e:
        from app.logger import logger
        logger.error(f"Error queuing replay task for job {job_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initiate job replay: {str(e)}"
        )


@router.post("/jobs/bulk-delete", response_model=BulkDeleteJobsResponse)
async def bulk_delete_jobs(
    request: BulkDeleteJobsRequest,
    current_user: User = Depends(is_allowed("platform:jobs:delete")),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete multiple jobs in bulk
    Requires: Admin access
    """
    if not request.job_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one job ID is required"
        )
    
    # Find all jobs that exist
    result = await db.execute(
        select(Job).where(Job.id.in_(request.job_ids))
    )
    jobs_to_delete = result.scalars().all()
    
    found_job_ids = {job.id for job in jobs_to_delete}
    failed_job_ids = [job_id for job_id in request.job_ids if job_id not in found_job_ids]
    
    # Delete all found jobs (logs will be cascade deleted)
    deleted_count = 0
    for job in jobs_to_delete:
        try:
            await db.delete(job)
            deleted_count += 1
        except Exception as e:
            # If deletion fails for a job, add it to failed list
            failed_job_ids.append(job.id)
    
    await db.commit()
    
    return BulkDeleteJobsResponse(
        deleted_count=deleted_count,
        failed_count=len(failed_job_ids),
        failed_job_ids=failed_job_ids
    )