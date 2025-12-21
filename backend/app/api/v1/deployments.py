from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List, Dict, Optional
from app.database import get_db
from app.api.deps import get_current_user, get_org_domain, get_org_aware_enforcer
from app.models.rbac import User
from app.models.deployment import Deployment, DeploymentStatus, DeploymentHistory
from app.schemas.deployment import DeploymentCreate, DeploymentResponse, DeploymentUpdateRequest
from app.logger import logger
from app.api.deps import OrgAwareEnforcer

router = APIRouter(prefix="/deployments", tags=["deployments"])

@router.get("/{deployment_id}/ci-cd-status")
async def get_cicd_status(
    deployment_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    enforcer: OrgAwareEnforcer = Depends(get_org_aware_enforcer)
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
            from datetime import datetime, timezone
            deployment.ci_cd_updated_at = datetime.now(timezone.utc)
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
    db: AsyncSession = Depends(get_db),
    enforcer: OrgAwareEnforcer = Depends(get_org_aware_enforcer)
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
    db: AsyncSession = Depends(get_db),
    enforcer: OrgAwareEnforcer = Depends(get_org_aware_enforcer)
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
            deployment.ci_cd_updated_at = datetime.now(timezone.utc)
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
    environment: str = None,  # NEW: Filter by environment
    tags: str = None,  # NEW: Filter by tags (format: "key1:value1,key2:value2")
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
    from sqlalchemy import or_, func
    from sqlalchemy.orm import selectinload
    from app.models.deployment import DeploymentTag
    
    # Admin sees all, engineer sees only their own
    user_id = str(current_user.id)
    
    # Base query based on permissions - eager load tags
    # OrgAwareEnforcer automatically handles org_domain
    base_filter = None
    if enforcer.enforce(user_id, "deployments", "list"):
        base_query = select(Deployment).options(selectinload(Deployment.tags))
        base_count_query = select(func.count(Deployment.id))
    elif enforcer.enforce(user_id, "deployments", "list:own"):
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
    
    # Apply environment filter (NEW)
    if environment:
        base_query = base_query.where(Deployment.environment == environment)
        base_count_query = base_count_query.where(Deployment.environment == environment)
    
    # Apply tags filter (NEW) - Optimized with JOIN instead of multiple IN subqueries
    if tags:
        # Parse tags: "team:backend,purpose:api"
        tag_filters = {}
        for tag_pair in tags.split(','):
            if ':' in tag_pair:
                key, value = tag_pair.split(':', 1)
                tag_filters[key.strip()] = value.strip()
        
        if tag_filters:
            # Optimized: Use JOIN-based approach for better performance
            # Join with deployment_tags and filter by all tag conditions
            from sqlalchemy import join, and_
            
            # Create join condition
            tag_join = join(Deployment, DeploymentTag, Deployment.id == DeploymentTag.deployment_id)
            
            # Build filter conditions for all tags
            tag_conditions = [
                and_(DeploymentTag.key == key, DeploymentTag.value == value)
                for key, value in tag_filters.items()
            ]
            
            # For multiple tags, we need deployments that have ALL tags
            # Use a subquery that groups by deployment_id and counts matching tags
            from sqlalchemy import func
            
            tag_match_subquery = (
                select(DeploymentTag.deployment_id)
                .where(
                    or_(*tag_conditions)  # Deployment has at least one matching tag
                )
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
    # OrgAwareEnforcer automatically handles org_domain
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

# ============================================================================
# Utility Endpoints - Must come BEFORE /{deployment_id} to avoid path conflicts
# ============================================================================

@router.get("/environments")
async def list_environments():
    """Get list of available environments"""
    from app.models.deployment import Environment
    
    return [
        {
            "name": env.value,
            "display": env.value.title(),
            "description": f"{env.value.title()} environment"
        }
        for env in Environment
    ]

@router.get("/tags/keys")
async def list_tag_keys(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get list of unique tag keys used across all deployments (for autocomplete)"""
    from app.models.deployment import DeploymentTag
    
    result = await db.execute(
        select(DeploymentTag.key).distinct().order_by(DeploymentTag.key)
    )
    
    return [{"key": row[0]} for row in result]

@router.get("/tags/values/{tag_key}")
async def list_tag_values(
    tag_key: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get list of unique values for a specific tag key (for autocomplete)"""
    from app.models.deployment import DeploymentTag
    
    result = await db.execute(
        select(DeploymentTag.value).where(DeploymentTag.key == tag_key).distinct().order_by(DeploymentTag.value)
    )
    
    return [{"value": row[0]} for row in result]

@router.get("/stats/by-environment")
async def deployment_stats_by_environment(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    enforcer: OrgAwareEnforcer = Depends(get_org_aware_enforcer)
):
    """Get deployment counts grouped by environment"""
    from sqlalchemy import func
    
    # Check permissions
    user_id = str(current_user.id)
    query = select(
        Deployment.environment,
        func.count(Deployment.id).label('count')
    )
    
    if enforcer.enforce(user_id, "deployments", "list"):
        # Can see all deployments in organization
        pass
    elif enforcer.enforce(user_id, "deployments", "list:own"):
        # Can only see own deployments
        query = query.where(Deployment.user_id == current_user.id)
    else:
        raise HTTPException(status_code=403, detail="Permission denied")
    
    query = query.group_by(Deployment.environment)
    result = await db.execute(query)
    
    stats = []
    for row in result:
        stats.append({
            "environment": row[0],
            "count": row[1]
        })
    
    return stats

@router.get("/stats/tags")
async def tag_usage_stats(
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    enforcer: OrgAwareEnforcer = Depends(get_org_aware_enforcer)
):
    """Get most commonly used tags across all deployments"""
    from sqlalchemy import func
    from app.models.deployment import DeploymentTag
    
    # Check permissions
    user_id = str(current_user.id)
    
    # Base query
    query = select(
        DeploymentTag.key,
        DeploymentTag.value,
        func.count(DeploymentTag.id).label('usage_count')
    )
    
    # Filter by user if not admin
    if not enforcer.enforce(user_id, "deployments", "list"):
        # Only show tags from user's own deployments
        query = query.join(Deployment).where(Deployment.user_id == current_user.id)
    
    query = (query
             .group_by(DeploymentTag.key, DeploymentTag.value)
             .order_by(func.count(DeploymentTag.id).desc())
             .limit(limit))
    
    result = await db.execute(query)
    
    stats = []
    for row in result:
        stats.append({
            "key": row[0],
            "value": row[1],
            "count": row[2]
        })
    
    return stats

# ============================================================================
# Individual Deployment Operations
# ============================================================================

@router.get("/{deployment_id}", response_model=DeploymentResponse)
async def get_deployment(
    deployment_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    enforcer: OrgAwareEnforcer = Depends(get_org_aware_enforcer)
):
    from app.core.utils import raise_permission_denied
    from sqlalchemy.orm import selectinload
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
    # OrgAwareEnforcer automatically handles org_domain
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
    from app.core.utils import get_or_404, raise_permission_denied
    from app.models.plugins import Job, JobStatus, JobLog
    from app.models import PluginVersion
    from datetime import datetime, timezone
    import uuid as uuid_lib
    
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
        from app.models.deployment import DeploymentTag
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
    from app.worker import provision_infrastructure
    try:
        provision_infrastructure.delay(
            job_id=update_job.id,
            plugin_id=deployment.plugin_id,
            version=deployment.version,
            inputs=update_request.inputs,
            credential_name=credential_name,
            deployment_id=str(deployment.id)
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
    from app.core.utils import get_or_404, raise_permission_denied
    from app.schemas.deployment import DeploymentHistoryResponse
    
    deployment = await get_or_404(db, Deployment, deployment_id, resource_name="Deployment")
    
    # Check permissions - use same permission check as get_deployment endpoint
    # If user can view the deployment, they can view its history
    user_id = str(current_user.id)
    if not (enforcer.enforce(user_id, "deployments", "list") or
            (enforcer.enforce(user_id, "deployments", "list:own") and deployment.user_id == current_user.id)):
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
    from app.core.utils import get_or_404, raise_permission_denied
    from app.models.plugins import Job, JobStatus, JobLog, PluginVersion
    from datetime import datetime, timezone
    import uuid as uuid_lib
    
    deployment = await get_or_404(db, Deployment, deployment_id, resource_name="Deployment")
    
    # Check permissions
    user_id = str(current_user.id)
    if not (enforcer.enforce(user_id, "deployments", "update") or
            (enforcer.enforce(user_id, "deployments", "update:own") and deployment.user_id == current_user.id)):
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
    from app.worker import provision_infrastructure
    try:
        provision_infrastructure.delay(
            job_id=rollback_job.id,
            plugin_id=deployment.plugin_id,
            version=deployment.version,
            inputs=history_entry.inputs,
            credential_name=credential_name,
            deployment_id=str(deployment.id)
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


@router.post("/{deployment_id}/retry", status_code=status.HTTP_202_ACCEPTED)
async def retry_deployment(
    deployment_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    enforcer: OrgAwareEnforcer = Depends(get_org_aware_enforcer)
):
    """Retry a failed deployment by re-queuing the same job"""
    from app.core.utils import get_or_404, raise_permission_denied
    from app.models.plugins import Job, JobStatus, JobLog
    from app.models import PluginVersion
    
    deployment = await get_or_404(db, Deployment, deployment_id, resource_name="Deployment")
    
    # Check ownership or admin permission
    # OrgAwareEnforcer automatically handles org_domain
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
    enforcer: OrgAwareEnforcer = Depends(get_org_aware_enforcer)
):
    from app.core.utils import get_or_404, raise_permission_denied
    from app.models import Job, JobStatus, PluginVersion
    from sqlalchemy import select
    from sqlalchemy.future import select as future_select
    import uuid
    
    deployment = await get_or_404(db, Deployment, deployment_id, resource_name="Deployment")
    
    # Check ownership or admin permission
    # OrgAwareEnforcer automatically handles org_domain
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
    from app.logger import logger
    
    if deployment_type == "microservice":
        # Microservice deletion - simpler, just delete the deployment record
        # Optionally could delete GitHub repo, but for now just mark as deleted
        from app.worker import destroy_microservice
        try:
            logger.info(f"Initiating microservice deletion for deployment {deployment_id}")
            task = destroy_microservice.delay(str(deployment_id))
            
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
        # Infrastructure deletion - destroy using Pulumi
        from app.worker import destroy_infrastructure
        try:
            logger.info(f"Initiating infrastructure deletion for deployment {deployment_id}, job_id: {job_id}")
            try:
                task = destroy_infrastructure.delay(str(deployment_id))
                logger.info(f"Celery task created successfully: task_id={task.id}, deployment_id={deployment_id}, job_id={job_id}")
            except Exception as task_error:
                logger.error(f"Failed to create Celery task: {task_error}", exc_info=True)
                # Update job status to failed
                if job_id:
                    job_result = await db.execute(
                        future_select(Job).where(Job.id == job_id)
                    )
                    job = job_result.scalar_one_or_none()
                    if job:
                        job.status = JobStatus.FAILED
                        await db.commit()
                raise
            
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

# ============================================================================
# Tag Management Endpoints
# ============================================================================

@router.post("/{deployment_id}/tags")
async def add_deployment_tags(
    deployment_id: str,
    tags: Dict[str, str],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    enforcer: OrgAwareEnforcer = Depends(get_org_aware_enforcer)
):
    """Add or update tags for a deployment"""
    from uuid import UUID
    from app.models.deployment import DeploymentTag
    from app.services.tag_validator import validate_tag_key, validate_tag_value
    
    try:
        deployment_uuid = UUID(deployment_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid deployment ID format")
    
    # Get deployment
    result = await db.execute(select(Deployment).where(Deployment.id == deployment_uuid))
    deployment = result.scalar_one_or_none()
    
    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")
    
    # Check permissions
    user_id = str(current_user.id)
    if not (enforcer.enforce(user_id, "deployments", "update") or
            (enforcer.enforce(user_id, "deployments", "update:own") and 
             deployment.user_id == current_user.id)):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    # Validate each tag
    for key, value in tags.items():
        is_valid_key, key_error = validate_tag_key(key)
        if not is_valid_key:
            raise HTTPException(status_code=400, detail=f"Invalid tag key '{key}': {key_error}")
        
        is_valid_value, value_error = validate_tag_value(value)
        if not is_valid_value:
            raise HTTPException(status_code=400, detail=f"Invalid tag value for '{key}': {value_error}")
    
    # Add or update tags
    tags_added = []
    for key, value in tags.items():
        # Check if tag already exists
        existing_tag_result = await db.execute(
            select(DeploymentTag).where(
                DeploymentTag.deployment_id == deployment.id,
                DeploymentTag.key == key
            )
        )
        existing_tag = existing_tag_result.scalar_one_or_none()
        
        if existing_tag:
            # Update existing tag
            existing_tag.value = value
            tags_added.append({"key": key, "value": value, "action": "updated"})
        else:
            # Create new tag
            new_tag = DeploymentTag(
                deployment_id=deployment.id,
                key=key,
                value=value
            )
            db.add(new_tag)
            tags_added.append({"key": key, "value": value, "action": "created"})
    
    await db.commit()
    
    # Refresh deployment to get updated tags
    await db.refresh(deployment)
    
    return {
        "message": "Tags updated successfully",
        "tags_modified": tags_added,
        "total_tags": len(deployment.tags)
    }

@router.delete("/{deployment_id}/tags/{tag_key}")
async def remove_deployment_tag(
    deployment_id: str,
    tag_key: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    enforcer: OrgAwareEnforcer = Depends(get_org_aware_enforcer)
):
    """Remove a specific tag from deployment"""
    from uuid import UUID
    from app.models.deployment import DeploymentTag
    from sqlalchemy import delete as sql_delete
    
    try:
        deployment_uuid = UUID(deployment_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid deployment ID format")
    
    # Get deployment
    result = await db.execute(select(Deployment).where(Deployment.id == deployment_uuid))
    deployment = result.scalar_one_or_none()
    
    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")
    
    # Check permissions
    user_id = str(current_user.id)
    if not (enforcer.enforce(user_id, "deployments", "update") or
            (enforcer.enforce(user_id, "deployments", "update:own") and 
             deployment.user_id == current_user.id)):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    # Delete the tag
    delete_result = await db.execute(
        sql_delete(DeploymentTag).where(
            DeploymentTag.deployment_id == deployment_uuid,
            DeploymentTag.key == tag_key
        )
    )
    
    if delete_result.rowcount == 0:
        raise HTTPException(status_code=404, detail=f"Tag '{tag_key}' not found on this deployment")
    
    await db.commit()
    
    return {"message": f"Tag '{tag_key}' removed successfully"}

