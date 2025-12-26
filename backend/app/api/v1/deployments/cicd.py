"""CI/CD related endpoints for deployments"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import datetime, timezone

from app.database import get_db
from app.api.deps import get_current_user, OrgAwareEnforcer, get_org_aware_enforcer
from app.models.rbac import User
from app.models.deployment import Deployment
from app.logger import logger
from app.config import settings

router = APIRouter()

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
    
    try:
        deployment_uuid = UUID(deployment_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid deployment ID format")
    
    result = await db.execute(select(Deployment).where(Deployment.id == deployment_uuid))
    deployment = result.scalar_one_or_none()
    
    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")
    
    # Check permissions - user must own the deployment or be admin
    from app.core.authorization import check_permission
    from app.models.business_unit import BusinessUnitMember
    
    # Get user's active business unit
    business_unit_id = None
    if current_user.active_business_unit_id:
        business_unit_id = current_user.active_business_unit_id
    
    has_read_permission = False
    if business_unit_id:
        has_read_permission = await check_permission(
            current_user,
            "business_unit:deployments:read",
            business_unit_id,
            db,
            enforcer.enforcer if hasattr(enforcer, 'enforcer') else enforcer
        )
    
    has_read_own = await check_permission(
        current_user,
        "user:deployments:read:own",
        None,
        db,
        enforcer.enforcer if hasattr(enforcer, 'enforcer') else enforcer
    )
    
    if deployment.user_id != current_user.id and not has_read_permission:
        raise HTTPException(status_code=403, detail="Permission denied")
    elif deployment.user_id == current_user.id and not has_read_own and not has_read_permission:
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
            "ci_cd_status": deployment.ci_cd_status or "error",
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
    
    try:
        deployment_uuid = UUID(deployment_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid deployment ID format")
    
    result = await db.execute(select(Deployment).where(Deployment.id == deployment_uuid))
    deployment = result.scalar_one_or_none()
    
    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")
    
    # Check permissions
    from app.core.authorization import check_permission
    
    has_read_permission = False
    if deployment.business_unit_id:
        has_read_permission = await check_permission(
            current_user,
            "business_unit:deployments:read",
            deployment.business_unit_id,
            db,
            enforcer.enforcer if hasattr(enforcer, 'enforcer') else enforcer
        )
    
    has_read_own = await check_permission(
        current_user,
        "user:deployments:read:own",
        None,
        db,
        enforcer.enforcer if hasattr(enforcer, 'enforcer') else enforcer
    )
    
    if deployment.user_id != current_user.id and not has_read_permission:
        raise HTTPException(status_code=403, detail="Permission denied")
    elif deployment.user_id == current_user.id and not has_read_own and not has_read_permission:
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
    
    try:
        deployment_uuid = UUID(deployment_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid deployment ID format")
    
    result = await db.execute(select(Deployment).where(Deployment.id == deployment_uuid))
    deployment = result.scalar_one_or_none()
    
    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")
    
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
    
    if deployment.user_id != current_user.id and not has_update_permission:
        raise HTTPException(status_code=403, detail="Permission denied")
    elif deployment.user_id == current_user.id and not has_update_own and not has_update_permission:
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

