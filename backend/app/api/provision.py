"""Provisioning and job management API"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
import uuid

from app.database import get_db
from app.models import Job, JobLog, PluginVersion, User, JobStatus
from app.schemas.plugins import ProvisionRequest, JobResponse, JobLogResponse
from app.api.deps import get_current_user

router = APIRouter(prefix="/provision", tags=["Provisioning"])

@router.post("/", response_model=JobResponse, status_code=status.HTTP_202_ACCEPTED)
async def provision(
    request: ProvisionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Trigger a provisioning job
    Returns immediately with job ID for async execution
    """
    # TODO: Check permission - plugins:provision
    
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
    
    # Create job
    job = Job(
        id=str(uuid.uuid4()),
        plugin_version_id=plugin_version.id,
        status=JobStatus.PENDING,
        triggered_by=current_user.email,
        inputs=request.inputs
    )
    db.add(job)
    
    # Add initial log
    log_entry = JobLog(
        job_id=job.id,
        level="INFO",
        message=f"Job created for {request.plugin_id}:{request.version}"
    )
    db.add(log_entry)
    
    await db.commit()
    await db.refresh(job)
    
    # Enqueue job to Celery worker
    from app.worker import provision_infrastructure
    provision_infrastructure.delay(
        job_id=job.id,
        plugin_id=request.plugin_id,
        version=request.version,
        inputs=request.inputs,
        credential_name=request.credential_name
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
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = 50
):
    """List recent jobs"""
    result = await db.execute(
        select(Job)
        .order_by(Job.created_at.desc())
        .limit(limit)
    )
    jobs = result.scalars().all()
    
    return jobs
