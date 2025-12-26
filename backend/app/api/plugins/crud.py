"""Plugin CRUD operations"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List, Optional
import uuid
from datetime import datetime, timezone
import shutil
from pathlib import Path

from app.database import get_db
from app.models import Plugin, PluginVersion, User, Job, JobLog, PluginAccessRequest, AccessRequestStatus
from app.schemas.plugins import PluginResponse
from app.api.deps import get_current_user, OrgAwareEnforcer, get_org_aware_enforcer, is_platform_admin, get_active_business_unit
from app.logger import logger
from app.config import settings

router = APIRouter()

@router.get("/", response_model=List[PluginResponse])
async def list_plugins(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    enforcer: OrgAwareEnforcer = Depends(get_org_aware_enforcer)
):
    """List all available plugins"""
    result = await db.execute(
        select(Plugin).options(selectinload(Plugin.versions))
    )
    plugins = result.scalars().all()
    
    # Check if user is platform admin or has plugins:upload permission
    user_id = str(current_user.id)
    from app.core.authorization import check_platform_permission
    has_upload_permission = await check_platform_permission(current_user, "platform:plugins:upload", db, enforcer.enforcer if hasattr(enforcer, 'enforcer') else enforcer)
    is_admin = await is_platform_admin(current_user, db, enforcer) or has_upload_permission
    
    # Get active business unit ID from user's active_business_unit_id
    business_unit_id = None
    if current_user.active_business_unit_id:
        business_unit_id = current_user.active_business_unit_id
    
    # Check which plugins the user has access to in the current business unit (only needed for non-admins)
    # Only APPROVED requests grant access (REVOKED means access was removed)
    user_access = set()
    if not is_admin:
        from app.models.plugins import PluginAccess
        # First check PluginAccess (granted access) for current business unit
        access_result = await db.execute(
            select(PluginAccess).where(
                PluginAccess.user_id == current_user.id,
                PluginAccess.business_unit_id == business_unit_id
            )
        )
        user_access = {access.plugin_id for access in access_result.scalars().all()}
        
        # Also check approved access requests for current business unit
        access_request_result = await db.execute(
            select(PluginAccessRequest).where(
                PluginAccessRequest.user_id == current_user.id,
                PluginAccessRequest.business_unit_id == business_unit_id,
                PluginAccessRequest.status == AccessRequestStatus.APPROVED
            )
        )
        user_access.update({req.plugin_id for req in access_request_result.scalars().all()})
    
    # Check pending requests for non-admins in current business unit
    pending_requests = set()
    if not is_admin:
        pending_result = await db.execute(
            select(PluginAccessRequest).where(
                PluginAccessRequest.user_id == current_user.id,
                PluginAccessRequest.business_unit_id == business_unit_id,
                PluginAccessRequest.status == AccessRequestStatus.PENDING
            )
        )
        pending_requests = {req.plugin_id for req in pending_result.scalars().all()}
    
    response = []
    for plugin in plugins:
        # Check access: admins can deploy but still see it as locked visually
        # has_access determines if they can deploy, but is_locked shows the visual state
        if plugin.is_locked:
            # For locked plugins, check if user has explicit APPROVED access (or is admin for deployment)
            has_access = is_admin or (plugin.id in user_access)
        else:
            # Unlocked plugins are accessible to everyone
            has_access = True
        
        # Check if user has pending request (only for locked plugins without access)
        has_pending_request = False
        if plugin.is_locked and not is_admin and not has_access:
            has_pending_request = plugin.id in pending_requests
        
        plugin_data = PluginResponse(
            id=plugin.id,
            name=plugin.name,
            description=plugin.description,
            author=plugin.author,
            is_locked=plugin.is_locked,
            has_access=has_access,
            has_pending_request=has_pending_request,
            created_at=plugin.created_at,
            updated_at=plugin.updated_at,
            latest_version="0.0.0",
            versions=[v.version for v in plugin.versions],
            git_repo_url=None,  # Will be set below for admins
            git_branch=None  # Will be set below for admins
        )
        
        # Get latest version info
        latest_version = None
        if plugin.versions:
            # Sort versions
            sorted_versions = sorted(
                plugin.versions, 
                key=lambda v: v.version, 
                reverse=True
            )
            latest_version = sorted_versions[0]
        
        if latest_version and latest_version.manifest:
            manifest = latest_version.manifest
            plugin_data.category = manifest.get('category', 'service')
            plugin_data.cloud_provider = manifest.get('cloud_provider', 'other')
            plugin_data.latest_version = latest_version.version
            
            # Show GitOps info only to admins
            if is_admin and latest_version:
                plugin_data.git_repo_url = latest_version.git_repo_url
                plugin_data.git_branch = latest_version.git_branch
            
            # Handle Icon URL
            icon_path = manifest.get('icon')
            if icon_path:
                # Use Path for reliable file checking
                storage_root = Path("storage")
                version_path = storage_root / "plugins" / plugin.id / latest_version.version
                
                # Check multiple possible locations (after flattening, files should be in extracted/)
                extracted_path = version_path / "extracted"
                nested_icon_path = extracted_path / plugin.id / icon_path  # Old nested structure
                direct_icon_path = extracted_path / icon_path  # Flattened structure
                legacy_nested = version_path / plugin.id / icon_path  # Legacy nested
                legacy_direct = version_path / icon_path  # Legacy direct
                
                base_url = f"/storage/plugins/{plugin.id}/{latest_version.version}"
                
                # Construct base URL from request
                base_url_scheme = request.url.scheme
                base_url_host = request.url.hostname
                base_url_port = request.url.port
                if base_url_port:
                    base_url_full = f"{base_url_scheme}://{base_url_host}:{base_url_port}"
                else:
                    base_url_full = f"{base_url_scheme}://{base_url_host}"
                
                # Check in order of preference
                if direct_icon_path.exists():
                    plugin_data.icon = f"{base_url_full}{base_url}/extracted/{icon_path}"
                elif nested_icon_path.exists():
                    plugin_data.icon = f"{base_url_full}{base_url}/extracted/{plugin.id}/{icon_path}"
                elif legacy_direct.exists():
                    plugin_data.icon = f"{base_url_full}{base_url}/{icon_path}"
                elif legacy_nested.exists():
                    plugin_data.icon = f"{base_url_full}{base_url}/{plugin.id}/{icon_path}"
                else:
                    # Fallback to most likely path (flattened structure)
                    plugin_data.icon = f"{base_url_full}{base_url}/extracted/{icon_path}"
            
        response.append(plugin_data)
        
    return response

@router.get("/{plugin_id}", response_model=PluginResponse)
async def get_plugin(
    plugin_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    enforcer: OrgAwareEnforcer = Depends(get_org_aware_enforcer),
    business_unit_id: Optional[uuid.UUID] = Depends(get_active_business_unit)
):
    """Get plugin details"""
    from typing import Optional
    import uuid as uuid_lib
    
    # Query plugin with versions eagerly loaded
    result = await db.execute(
        select(Plugin).options(selectinload(Plugin.versions)).where(Plugin.id == plugin_id)
    )
    plugin = result.scalar_one_or_none()
    
    if not plugin:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plugin not found")
    
    # Check if user is platform admin or has plugins:upload permission
    user_id = str(current_user.id)
    from app.core.authorization import check_platform_permission
    has_upload_permission = await check_platform_permission(current_user, "platform:plugins:upload", db, enforcer.enforcer if hasattr(enforcer, 'enforcer') else enforcer)
    is_admin = await is_platform_admin(current_user, db, enforcer) or has_upload_permission
    
    # Get active business unit ID (use dependency value or fallback to user's active_business_unit_id)
    if not business_unit_id and current_user.active_business_unit_id:
        business_unit_id = current_user.active_business_unit_id
    
    # Check if user has access: admins can deploy locked plugins, but visually it's still locked
    if plugin.is_locked:
        # For locked plugins, check if user has explicit access (or is admin for deployment)
        has_access = is_admin
        if not is_admin:
            # Check for active (approved) access in the current business unit
            from app.models.plugins import PluginAccess
            # First check PluginAccess (granted access)
            access_result = await db.execute(
                select(PluginAccess).where(
                    PluginAccess.plugin_id == plugin_id,
                    PluginAccess.user_id == current_user.id,
                    PluginAccess.business_unit_id == business_unit_id
                )
            )
            has_access = access_result.scalar_one_or_none() is not None
            
            # If no direct access, check for approved request
            if not has_access:
                access_request_result = await db.execute(
                    select(PluginAccessRequest).where(
                        PluginAccessRequest.plugin_id == plugin_id,
                        PluginAccessRequest.user_id == current_user.id,
                        PluginAccessRequest.business_unit_id == business_unit_id,
                        PluginAccessRequest.status == AccessRequestStatus.APPROVED
                    )
                )
                has_access = access_request_result.scalar_one_or_none() is not None
    else:
        # Unlocked plugins are accessible to everyone
        has_access = True
    
    # Check if user has a pending access request (only for non-admins and locked plugins)
    has_pending_request = False
    if plugin.is_locked and not is_admin and not has_access:
        pending_result = await db.execute(
            select(PluginAccessRequest).where(
                PluginAccessRequest.plugin_id == plugin_id,
                PluginAccessRequest.user_id == current_user.id,
                PluginAccessRequest.business_unit_id == business_unit_id,
                PluginAccessRequest.status == "pending"
            )
        )
        has_pending_request = pending_result.scalar_one_or_none() is not None
    
    # Get latest version
    latest_version_str = "0.0.0"
    latest_version_obj = None
    if plugin.versions:
        sorted_versions = sorted(plugin.versions, key=lambda v: v.version, reverse=True)
        latest_version_obj = sorted_versions[0]
        latest_version_str = latest_version_obj.version
    
    # Get manifest info for category and cloud_provider
    category = "service"
    cloud_provider = "other"
    if latest_version_obj and latest_version_obj.manifest:
        manifest = latest_version_obj.manifest
        category = manifest.get('category', 'service')
        cloud_provider = manifest.get('cloud_provider', 'other')
    
    return PluginResponse(
        id=plugin.id,
        name=plugin.name,
        description=plugin.description,
        author=plugin.author,
        is_locked=plugin.is_locked,
        has_access=has_access,
        has_pending_request=has_pending_request,
        created_at=plugin.created_at,
        updated_at=plugin.updated_at,
        latest_version=latest_version_str,
        versions=[v.version for v in plugin.versions],
        category=category,
        cloud_provider=cloud_provider,
        git_repo_url=latest_version_obj.git_repo_url if (is_admin and latest_version_obj) else None,
        git_branch=latest_version_obj.git_branch if (is_admin and latest_version_obj) else None
    )

@router.delete("/{plugin_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_plugin(
    plugin_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    enforcer: OrgAwareEnforcer = Depends(get_org_aware_enforcer)
):
    """
    Delete a plugin and all its versions
    Requires: plugins:delete permission (admin only)
    """
    # Check permission - only admins can delete plugins
    from app.core.authorization import check_platform_permission
    has_permission = await check_platform_permission(current_user, "platform:plugins:delete", db, enforcer.enforcer if hasattr(enforcer, 'enforcer') else enforcer)
    if not has_permission:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can delete plugins"
        )
    
    # Get plugin
    from app.core.utils import get_or_404
    plugin = await get_or_404(db, Plugin, plugin_id, resource_name="Plugin")
    
    # Delete all versions and their storage files
    result = await db.execute(
        select(PluginVersion).where(PluginVersion.plugin_id == plugin_id)
    )
    versions = result.scalars().all()
    
    # Delete all jobs referencing these plugin versions
    version_ids = [v.id for v in versions]
    if version_ids:
        # First delete job logs
        job_logs_result = await db.execute(
            select(JobLog).join(Job).where(Job.plugin_version_id.in_(version_ids))
        )
        job_logs = job_logs_result.scalars().all()
        for log in job_logs:
            await db.delete(log)
        
        # Then delete jobs
        jobs_result = await db.execute(
            select(Job).where(Job.plugin_version_id.in_(version_ids))
        )
        jobs = jobs_result.scalars().all()
        for job in jobs:
            await db.delete(job)
    
    # Track plugin base directory for cleanup
    plugin_base_dir = None
    
    # Delete GitHub branches for each version that has GitOps configured
    for version in versions:
        # Delete GitHub branch if GitOps is configured
        if version.git_repo_url and version.git_branch:
            try:
                from app.services.git_service import git_service
                github_token = getattr(settings, 'GITHUB_TOKEN', None)
                if github_token:
                    logger.info(f"Deleting GitHub branch '{version.git_branch}' from {version.git_repo_url}")
                    git_service.delete_branch(version.git_repo_url, version.git_branch, github_token)
                    logger.info(f"Successfully deleted branch '{version.git_branch}' from {version.git_repo_url}")
                else:
                    logger.warning(f"GITHUB_TOKEN not configured, cannot delete branch '{version.git_branch}' from {version.git_repo_url}")
            except Exception as branch_error:
                # Log error but continue with deletion - branch might not exist or already deleted
                logger.warning(f"Failed to delete branch '{version.git_branch}' from {version.git_repo_url}: {branch_error}")
        
        # Delete storage files
        try:
            storage_path = Path(version.storage_path)
            if storage_path.exists():
                storage_path.unlink()
                logger.info(f"Deleted storage file: {storage_path}")
            
            # Delete the entire version directory (contains extracted files)
            version_dir = storage_path.parent
            if version_dir.exists():
                shutil.rmtree(version_dir)
                logger.info(f"Deleted version directory: {version_dir}")
                plugin_base_dir = version_dir.parent  # Store parent for cleanup
        except Exception as e:
            # Log error but continue with deletion
            logger.error(f"Error deleting storage files for {plugin_id} v{version.version}: {e}")
            # Still try to get the base directory for cleanup
            if not plugin_base_dir and version.storage_path:
                try:
                    plugin_base_dir = Path(version.storage_path).parent.parent
                except:
                    pass
    
    # Delete from database (cascade will delete versions)
    await db.delete(plugin)
    await db.commit()
    logger.info(f"Deleted plugin {plugin_id} from database")

    # Clean up any empty plugin directory left behind
    if plugin_base_dir and plugin_base_dir.exists():
        try:
            # Check if directory is empty (no version directories left)
            if not any(plugin_base_dir.iterdir()):
                plugin_base_dir.rmdir()
                logger.info(f"Cleaned up empty plugin directory: {plugin_base_dir}")
        except Exception as e:
            logger.warning(f"Error cleaning up plugin directory {plugin_base_dir}: {e}")

    # Return success response (204 No Content)
    from fastapi.responses import Response
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@router.put("/{plugin_id}/lock", status_code=status.HTTP_200_OK)
async def lock_plugin(
    plugin_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    enforcer: OrgAwareEnforcer = Depends(get_org_aware_enforcer)
):
    """
    Lock a plugin (admin only)
    Requires: plugins:upload permission (admin only)
    """
    from app.core.authorization import check_platform_permission
    has_permission = await check_platform_permission(current_user, "platform:plugins:upload", db, enforcer.enforcer if hasattr(enforcer, 'enforcer') else enforcer)
    if not has_permission:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can lock plugins"
        )
    
    from app.core.utils import get_or_404
    plugin = await get_or_404(db, Plugin, plugin_id, resource_name="Plugin")
    
    plugin.is_locked = True
    plugin.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(plugin)
    
    logger.info(f"Plugin {plugin_id} locked by {current_user.email}")
    return {"message": f"Plugin {plugin_id} has been locked", "is_locked": True}

@router.put("/{plugin_id}/unlock", status_code=status.HTTP_200_OK)
async def unlock_plugin(
    plugin_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    enforcer: OrgAwareEnforcer = Depends(get_org_aware_enforcer)
):
    """
    Unlock a plugin (admin only)
    Requires: plugins:upload permission (admin only)
    """
    from app.core.authorization import check_platform_permission
    has_permission = await check_platform_permission(current_user, "platform:plugins:upload", db, enforcer.enforcer if hasattr(enforcer, 'enforcer') else enforcer)
    if not has_permission:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can unlock plugins"
        )
    
    from app.core.utils import get_or_404
    plugin = await get_or_404(db, Plugin, plugin_id, resource_name="Plugin")
    
    plugin.is_locked = False
    plugin.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(plugin)
    
    logger.info(f"Plugin {plugin_id} unlocked by {current_user.email}")
    return {"message": f"Plugin {plugin_id} has been unlocked", "is_locked": False}

