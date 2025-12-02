"""Provisioning and job management API"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
import uuid

from app.database import get_db
from app.models import Job, JobLog, User, Deployment, DeploymentStatus, PluginVersion, JobStatus
from app.schemas.plugins import (
    ProvisionRequest, 
    JobResponse, 
    JobLogResponse,
    BulkDeleteJobsRequest,
    BulkDeleteJobsResponse
)
from app.api.deps import get_current_user, is_allowed, get_current_active_superuser

router = APIRouter(prefix="/provision", tags=["Provisioning"])

@router.post("/", response_model=JobResponse, status_code=status.HTTP_202_ACCEPTED)
async def provision(
    request: ProvisionRequest,
    current_user: User = Depends(is_allowed("plugins:provision")),
    db: AsyncSession = Depends(get_db)
):
    """
    Trigger a provisioning job
    Returns immediately with job ID for async execution
    Requires: plugins:provision permission
    """
    
    # Validate plugin version exists
    result = await db.execute(
        select(PluginVersion).where(
            PluginVersion.plugin_id == request.plugin_id,
            PluginVersion.version == request.version
        )
    )
    plugin_version = result.scalar_one_or_none()
    
    if not plugin_version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plugin {request.plugin_id} version {request.version} not found"
        )
    
    # Auto-select credentials based on plugin's cloud provider
    credential_name = None
    cloud_provider = plugin_version.manifest.get("cloud_provider")
    
    if cloud_provider and cloud_provider != "unknown":
        from app.models import CloudProvider, CloudCredential
        try:
            provider_enum = CloudProvider(cloud_provider)
            # Find the first credential for this provider
            cred_result = await db.execute(
                select(CloudCredential).where(CloudCredential.provider == provider_enum)
            )
            credential = cred_result.scalar_one_or_none()
            if credential:
                credential_name = credential.name
        except ValueError:
            pass  # Invalid provider, proceed without credentials
    
    # Create job
    job = Job(
        id=str(uuid.uuid4()),
        plugin_version_id=plugin_version.id,
        status=JobStatus.PENDING,
        triggered_by=current_user.email,
        inputs=request.inputs
    )
    db.add(job)
    
    # Add initial log with OIDC auto-exchange info
    credential_msg = f" (using static credentials: {credential_name})" if credential_name else ""
    if not credential_name and cloud_provider and cloud_provider != "unknown":
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
    
    log_entry = JobLog(
        job_id=job.id,
        level="INFO",
        message=f"Job created for {request.plugin_id}:{request.version}{credential_msg}"
    )
    db.add(log_entry)
    
    # Create Deployment record (PROVISIONING)
    stack_name = f"{request.plugin_id}-{job.id[:8]}"
    deployment = Deployment(
        name=request.inputs.get("bucket_name") or f"{request.plugin_id}-{job.id[:8]}",
        plugin_id=request.plugin_id,
        version=request.version,
        status=DeploymentStatus.PROVISIONING,
        user_id=current_user.id,
        inputs=request.inputs,
        stack_name=stack_name,
        cloud_provider=cloud_provider or "unknown",
        region=request.inputs.get("location", "unknown")
    )
    db.add(deployment)
    await db.flush() # Get ID
    
    # Link job to deployment
    job.deployment_id = deployment.id
    
    await db.commit()
    await db.refresh(job)
    
    # Enqueue job to Celery worker
    from app.worker import provision_infrastructure
    provision_infrastructure.delay(
        job_id=job.id,
        plugin_id=request.plugin_id,
        version=request.version,
        inputs=request.inputs,
        credential_name=credential_name,
        deployment_id=str(deployment.id)
    )
    
    return job

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

@router.get("/jobs", response_model=List[JobResponse])
async def list_jobs(
    job_id: str = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = 50
):
    """List recent jobs"""
    query = select(Job).order_by(Job.created_at.desc())
    
    if job_id:
        query = query.where(Job.id.ilike(f"%{job_id}%"))
        
    query = query.limit(limit)
    
    result = await db.execute(query)
    jobs = result.scalars().all()
    
    return jobs

@router.delete("/jobs/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_job(
    job_id: str,
    current_user: User = Depends(get_current_active_superuser),
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

@router.post("/jobs/bulk-delete", response_model=BulkDeleteJobsResponse)
async def bulk_delete_jobs(
    request: BulkDeleteJobsRequest,
    current_user: User = Depends(get_current_active_superuser),
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
