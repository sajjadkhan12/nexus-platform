"""Plugin management API endpoints"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status, Request, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List
from datetime import datetime
import tempfile
import shutil
import os
import zipfile
import uuid
from pathlib import Path

from app.database import get_db
from app.models import (
    Plugin, PluginVersion, User, Job, JobLog,
    PluginAccess, PluginAccessRequest, AccessRequestStatus
)
from app.schemas.plugins import (
    PluginResponse, PluginVersionResponse,
    PluginAccessRequestCreate, PluginAccessRequestResponse,
    PluginAccessGrantRequest, PluginAccessResponse
)
from app.services.storage import storage_service
from app.services.plugin_validator import plugin_validator
from app.api.deps import get_current_user
from app.core.casbin import get_enforcer
from app.logger import logger
from casbin import Enforcer

router = APIRouter(prefix="/plugins", tags=["Plugins"])

@router.post("/upload", response_model=PluginVersionResponse, status_code=status.HTTP_201_CREATED)
async def upload_plugin(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    enforcer: Enforcer = Depends(get_enforcer)
):
    """
    Upload a new plugin or plugin version
    Requires: plugins:upload permission (admin only)
    """
    logger.info(f"Plugin upload request received from user {current_user.email}, filename: {file.filename}")
    
    # Check permission - only admins can upload plugins
    user_id = str(current_user.id)
    if not enforcer.enforce(user_id, "plugins", "upload"):
        logger.warning(f"User {current_user.email} attempted to upload plugin without permission")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can upload plugins"
        )
    
    if not file.filename.endswith('.zip'):
        logger.error(f"Invalid file type uploaded: {file.filename}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only ZIP files are accepted"
        )
    
    # Save to temporary file for validation
    with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as tmp_file:
        shutil.copyfileobj(file.file, tmp_file)
        tmp_path = Path(tmp_file.name)
    
    logger.info(f"Temporary file created: {tmp_path}, size: {tmp_path.stat().st_size} bytes")
    
    try:
        # Validate plugin
        logger.info(f"Starting plugin validation for {file.filename}")
        is_valid, error_msg, manifest = plugin_validator.validate_zip(tmp_path)
        
        if not is_valid:
            logger.error(f"Plugin validation failed: {error_msg}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid plugin: {error_msg}"
            )
        
        logger.info(f"Plugin validation successful. Plugin ID: {manifest.get('id')}, Version: {manifest.get('version')}")
        
        plugin_id = manifest['id']
        version = manifest['version']
        
        # Check if plugin exists
        result = await db.execute(select(Plugin).where(Plugin.id == plugin_id))
        plugin = result.scalar_one_or_none()
        
        if not plugin:
            # Create new plugin
            plugin = Plugin(
                id=plugin_id,
                name=manifest['name'],
                description=manifest.get('description'),
                author=manifest.get('author')
            )
            db.add(plugin)
        
        # Check if version exists
        result = await db.execute(
            select(PluginVersion).where(
                PluginVersion.plugin_id == plugin_id,
                PluginVersion.version == version
            )
        )
        existing_version = result.scalar_one_or_none()
        if existing_version:
            # Delete old version files from storage
            logger.info(f"Version {version} already exists. Replacing with new version...")
            try:
                old_storage_path = Path(existing_version.storage_path)
                if old_storage_path.exists():
                    old_storage_path.unlink()
                    logger.info(f"Deleted old storage file: {old_storage_path}")
                
                # Delete the entire version directory (contains extracted files)
                version_dir = old_storage_path.parent
                if version_dir.exists():
                    shutil.rmtree(version_dir)
                    logger.info(f"Deleted old version directory: {version_dir}")
            except Exception as e:
                logger.warning(f"Error deleting old version files: {e}")
            
            # Delete old version record from database
            await db.delete(existing_version)
            await db.flush()  # Flush to ensure deletion before creating new one
        
        # Save to storage
        with open(tmp_path, 'rb') as f:
            storage_path = storage_service.save_plugin(plugin_id, version, f)
            
        # Extract the zip file for asset serving - extract directly to version folder
        extract_dir = Path(storage_path).parent
        with zipfile.ZipFile(tmp_path, 'r') as zip_ref:
            for member in zip_ref.infolist():
                # Skip macOS metadata and junk files
                if member.filename.startswith('__MACOSX') or member.filename.endswith('.DS_Store'):
                    continue
                zip_ref.extract(member, extract_dir)
        
        # Create plugin version record
        plugin_version = PluginVersion(
            plugin_id=plugin_id,
            version=version,
            manifest=manifest,
            storage_path=storage_path
        )
        db.add(plugin_version)
        
        await db.commit()
        await db.refresh(plugin_version)
        
        return plugin_version
    
    finally:
        # Clean up temp file
        tmp_path.unlink(missing_ok=True)

@router.get("/", response_model=List[PluginResponse])
async def list_plugins(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List all available plugins"""
    result = await db.execute(
        select(Plugin).options(selectinload(Plugin.versions))
    )
    plugins = result.scalars().all()
    
    # Check if user is admin
    from app.core.casbin import get_enforcer
    enforcer = get_enforcer()
    user_id = str(current_user.id)
    is_admin = enforcer.has_grouping_policy(user_id, "admin") or enforcer.enforce(user_id, "plugins", "upload")
    
    # Check which plugins the user has access to (only needed for non-admins)
    user_access = set()
    if not is_admin:
        access_result = await db.execute(
            select(PluginAccess).where(PluginAccess.user_id == current_user.id)
        )
        user_access = {access.plugin_id for access in access_result.scalars().all()}
    
    # Check pending requests for non-admins
    pending_requests = set()
    if not is_admin:
        pending_result = await db.execute(
            select(PluginAccessRequest).where(
                PluginAccessRequest.user_id == current_user.id,
                PluginAccessRequest.status == "pending"
            )
        )
        pending_requests = {req.plugin_id for req in pending_result.scalars().all()}
    
    response = []
    for plugin in plugins:
        # Check access: admins can deploy but still see it as locked visually
        # has_access determines if they can deploy, but is_locked shows the visual state
        if plugin.is_locked:
            # For locked plugins, check if user has explicit access (or is admin for deployment)
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
            versions=[v.version for v in plugin.versions]
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
            
            # Handle Icon URL
            icon_path = manifest.get('icon')
            if icon_path:
                # Use Path for reliable file checking
                storage_root = Path("storage")
                version_path = storage_root / "plugins" / plugin.id / latest_version.version
                
                # Check for nested directory structure (common in zips)
                nested_icon_path = version_path / plugin.id / icon_path
                direct_icon_path = version_path / icon_path
                
                base_url = f"/storage/plugins/{plugin.id}/{latest_version.version}"
                
                # Construct base URL from request
                base_url_scheme = request.url.scheme
                base_url_host = request.url.hostname
                base_url_port = request.url.port
                if base_url_port:
                    base_url_full = f"{base_url_scheme}://{base_url_host}:{base_url_port}"
                else:
                    base_url_full = f"{base_url_scheme}://{base_url_host}"
                
                if nested_icon_path.exists():
                     plugin_data.icon = f"{base_url_full}{base_url}/{plugin.id}/{icon_path}"
                elif direct_icon_path.exists():
                     plugin_data.icon = f"{base_url_full}{base_url}/{icon_path}"
                else:
                    # Fallback to direct path even if check fails (might be permission issue?)
                    plugin_data.icon = f"{base_url_full}{base_url}/{icon_path}"
            
        response.append(plugin_data)
        
    return response

@router.get("/{plugin_id}", response_model=PluginResponse)
async def get_plugin(
    plugin_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get plugin details"""
    # Query plugin with versions eagerly loaded
    result = await db.execute(
        select(Plugin).options(selectinload(Plugin.versions)).where(Plugin.id == plugin_id)
    )
    plugin = result.scalar_one_or_none()
    
    if not plugin:
        from fastapi import HTTPException, status
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plugin not found")
    
    # Check if user is admin
    from app.core.casbin import get_enforcer
    enforcer = get_enforcer()
    user_id = str(current_user.id)
    is_admin = enforcer.has_grouping_policy(user_id, "admin") or enforcer.enforce(user_id, "plugins", "upload")
    
    # Check if user has access: admins can deploy locked plugins, but visually it's still locked
    if plugin.is_locked:
        # For locked plugins, check if user has explicit access (or is admin for deployment)
        has_access = is_admin
        if not is_admin:
            access_result = await db.execute(
                select(PluginAccess).where(
                    PluginAccess.plugin_id == plugin_id,
                    PluginAccess.user_id == current_user.id
                )
            )
            has_access = access_result.scalar_one_or_none() is not None
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
                PluginAccessRequest.status == "pending"
            )
        )
        has_pending_request = pending_result.scalar_one_or_none() is not None
    
    # Get latest version
    latest_version = "0.0.0"
    if plugin.versions:
        sorted_versions = sorted(plugin.versions, key=lambda v: v.version, reverse=True)
        latest_version = sorted_versions[0].version
    
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
        latest_version=latest_version,
        versions=[v.version for v in plugin.versions]
    )

@router.get("/{plugin_id}/versions", response_model=List[PluginVersionResponse])
async def list_plugin_versions(
    plugin_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List all versions of a plugin"""
    result = await db.execute(
        select(PluginVersion).where(PluginVersion.plugin_id == plugin_id)
    )
    versions = result.scalars().all()
    return versions

@router.get("/{plugin_id}/versions/{version}", response_model=PluginVersionResponse)
async def get_plugin_version(
    plugin_id: str,
    version: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get specific plugin version details"""
    result = await db.execute(
        select(PluginVersion).where(
            PluginVersion.plugin_id == plugin_id,
            PluginVersion.version == version
        )
    )
    from app.core.utils import get_or_404
    plugin_version = await get_or_404(
        db, PluginVersion, version, 
        identifier_field="version",
        resource_name="Plugin version"
    )
    return plugin_version

@router.delete("/{plugin_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_plugin(
    plugin_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    enforcer: Enforcer = Depends(get_enforcer)
):
    """
    Delete a plugin and all its versions
    Requires: plugins:delete permission (admin only)
    """
    # Check permission - only admins can delete plugins
    user_id = str(current_user.id)
    if not enforcer.enforce(user_id, "plugins", "delete"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can delete plugins"
        )
    
    # Get plugin
    from app.core.utils import get_or_404, raise_permission_denied
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
        await db.execute(
            select(JobLog).where(JobLog.job_id.in_(
                select(Job.id).where(Job.plugin_version_id.in_(version_ids))
            ))
        )
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
    
    for version in versions:
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
    enforcer: Enforcer = Depends(get_enforcer)
):
    """
    Lock a plugin (admin only)
    Requires: plugins:upload permission (admin only)
    """
    user_id = str(current_user.id)
    if not enforcer.enforce(user_id, "plugins", "upload"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can lock plugins"
        )
    
    from app.core.utils import get_or_404
    plugin = await get_or_404(db, Plugin, plugin_id, resource_name="Plugin")
    
    plugin.is_locked = True
    plugin.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(plugin)
    
    logger.info(f"Plugin {plugin_id} locked by {current_user.email}")
    return {"message": f"Plugin {plugin_id} has been locked", "is_locked": True}

@router.put("/{plugin_id}/unlock", status_code=status.HTTP_200_OK)
async def unlock_plugin(
    plugin_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    enforcer: Enforcer = Depends(get_enforcer)
):
    """
    Unlock a plugin (admin only)
    Requires: plugins:upload permission (admin only)
    """
    user_id = str(current_user.id)
    if not enforcer.enforce(user_id, "plugins", "upload"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can unlock plugins"
        )
    
    from app.core.utils import get_or_404
    plugin = await get_or_404(db, Plugin, plugin_id, resource_name="Plugin")
    
    plugin.is_locked = False
    plugin.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(plugin)
    
    logger.info(f"Plugin {plugin_id} unlocked by {current_user.email}")
    return {"message": f"Plugin {plugin_id} has been unlocked", "is_locked": False}

@router.post("/{plugin_id}/access/request", response_model=PluginAccessRequestResponse, status_code=status.HTTP_201_CREATED)
async def request_plugin_access(
    plugin_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Request access to a locked plugin
    """
    from app.core.utils import get_or_404
    plugin = await get_or_404(db, Plugin, plugin_id, resource_name="Plugin")
    
    if not plugin.is_locked:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Plugin is not locked, access request not needed"
        )
    
    # Check if user already has access
    access_result = await db.execute(
        select(PluginAccess).where(
            PluginAccess.plugin_id == plugin_id,
            PluginAccess.user_id == current_user.id
        )
    )
    existing_access = access_result.scalar_one_or_none()
    if existing_access:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You already have access to this plugin"
        )
    
    # Check if there's already a pending request
    request_result = await db.execute(
        select(PluginAccessRequest).where(
            PluginAccessRequest.plugin_id == plugin_id,
            PluginAccessRequest.user_id == current_user.id,
            PluginAccessRequest.status == "pending"
        )
    )
    existing_request = request_result.scalar_one_or_none()
    if existing_request:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You already have a pending access request for this plugin"
        )
    
    # Create new access request
    # TypeDecorator will automatically convert enum to its value
    access_request = PluginAccessRequest(
        plugin_id=plugin_id,
        user_id=current_user.id,
        status=AccessRequestStatus.PENDING
    )
    db.add(access_request)
    await db.commit()
    await db.refresh(access_request)
    
    # Create notification for admins
    from app.models import Notification, NotificationType
    from sqlalchemy import select as sql_select
    from app.core.casbin import enforcer as casbin_enforcer
    
    # Get all admin users
    admin_users_result = await db.execute(
        sql_select(User)
    )
    all_users = admin_users_result.scalars().all()
    
    admin_user_ids = []
    for user in all_users:
        user_id_str = str(user.id)
        if casbin_enforcer.enforce(user_id_str, "plugins", "upload"):
            admin_user_ids.append(user.id)
    
    # Create notifications for all admins
    for admin_id in admin_user_ids:
        notification = Notification(
            id=str(uuid.uuid4()),
            user_id=admin_id,
            title=f"Plugin Access Request",
            message=f"{current_user.email} requested access to locked plugin: {plugin.name}",
            type=NotificationType.INFO,
            link=f"/admin/plugin-requests"
        )
        db.add(notification)
    
    await db.commit()
    
    logger.info(f"Access request created for plugin {plugin_id} by user {current_user.email}")
    return access_request

@router.get("/access/requests", response_model=List[PluginAccessRequestResponse])
async def list_all_access_requests(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    enforcer: Enforcer = Depends(get_enforcer),
    user_email: str = Query(None, description="Filter by user email (partial match)")
):
    """
    List all access requests across all plugins (admin only)
    Optional filter by user_email
    """
    user_id = str(current_user.id)
    if not enforcer.enforce(user_id, "plugins", "upload"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can view access requests"
        )
    
    # Build query with optional user email filter
    query = select(PluginAccessRequest, User.email, Plugin.name).join(
        User, PluginAccessRequest.user_id == User.id
    ).join(
        Plugin, PluginAccessRequest.plugin_id == Plugin.id
    )
    
    if user_email:
        query = query.where(User.email.ilike(f"%{user_email}%"))
    
    query = query.order_by(PluginAccessRequest.requested_at.desc())
    
    result = await db.execute(query)
    rows = result.all()
    
    # Convert to response format with user email and plugin name
    from app.schemas.plugins import PluginAccessRequestResponse
    requests = []
    for row in rows:
        request, user_email_val, plugin_name = row
        request_dict = {
            "id": request.id,
            "plugin_id": request.plugin_id,
            "plugin_name": plugin_name,  # Add plugin name for display
            "user_id": request.user_id,
            "user_email": user_email_val,
            "status": request.status.value if hasattr(request.status, 'value') else str(request.status),
            "requested_at": request.requested_at,
            "reviewed_at": request.reviewed_at,
            "reviewed_by": request.reviewed_by
        }
        requests.append(PluginAccessRequestResponse(**request_dict))
    
    return requests

@router.get("/{plugin_id}/access/requests", response_model=List[PluginAccessRequestResponse])
async def list_access_requests(
    plugin_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    enforcer: Enforcer = Depends(get_enforcer)
):
    """
    List access requests for a plugin (admin only)
    """
    user_id = str(current_user.id)
    if not enforcer.enforce(user_id, "plugins", "upload"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can view access requests"
        )
    
    from app.core.utils import get_or_404
    plugin = await get_or_404(db, Plugin, plugin_id, resource_name="Plugin")
    
    result = await db.execute(
        select(PluginAccessRequest, User.email)
        .join(User, PluginAccessRequest.user_id == User.id)
        .where(PluginAccessRequest.plugin_id == plugin_id)
        .order_by(PluginAccessRequest.requested_at.desc())
    )
    rows = result.all()
    
    # Convert to response format with user email
    from app.schemas.plugins import PluginAccessRequestResponse
    requests = []
    for request, user_email in rows:
        request_dict = {
            "id": request.id,
            "plugin_id": request.plugin_id,
            "user_id": request.user_id,
            "user_email": user_email,
            "status": request.status.value if hasattr(request.status, 'value') else str(request.status),
            "requested_at": request.requested_at,
            "reviewed_at": request.reviewed_at,
            "reviewed_by": request.reviewed_by
        }
        requests.append(PluginAccessRequestResponse(**request_dict))
    
    return requests

@router.post("/{plugin_id}/access/grant", response_model=PluginAccessResponse, status_code=status.HTTP_201_CREATED)
async def grant_plugin_access(
    plugin_id: str,
    request: PluginAccessGrantRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    enforcer: Enforcer = Depends(get_enforcer)
):
    """
    Grant access to a user for a locked plugin (admin only)
    """
    user_id = str(current_user.id)
    if not enforcer.enforce(user_id, "plugins", "upload"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can grant plugin access"
        )
    
    from app.core.utils import get_or_404
    plugin = await get_or_404(db, Plugin, plugin_id, resource_name="Plugin")
    
    # Check if user exists
    user_result = await db.execute(
        select(User).where(User.id == request.user_id)
    )
    target_user = user_result.scalar_one_or_none()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Check if access already exists
    existing_result = await db.execute(
        select(PluginAccess).where(
            PluginAccess.plugin_id == plugin_id,
            PluginAccess.user_id == request.user_id
        )
    )
    existing_access = existing_result.scalar_one_or_none()
    if existing_access:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already has access to this plugin"
        )
    
    # Grant access
    plugin_access = PluginAccess(
        plugin_id=plugin_id,
        user_id=request.user_id,
        granted_by=current_user.id
    )
    db.add(plugin_access)
    
    # Update any pending requests to approved
    pending_requests_result = await db.execute(
        select(PluginAccessRequest).where(
            PluginAccessRequest.plugin_id == plugin_id,
            PluginAccessRequest.user_id == request.user_id,
            PluginAccessRequest.status == "pending"
        )
    )
    pending_requests = pending_requests_result.scalars().all()
    for req in pending_requests:
        req.status = AccessRequestStatus.APPROVED  # TypeDecorator handles conversion
        req.reviewed_at = datetime.utcnow()
        req.reviewed_by = current_user.id
    
    # Create notification for the user
    from app.models import Notification, NotificationType
    notification = Notification(
        id=str(uuid.uuid4()),
        user_id=request.user_id,
        title=f"Plugin Access Granted",
        message=f"You have been granted access to plugin: {plugin.name}",
        type=NotificationType.SUCCESS,
        link=f"/provision/{plugin_id}"
    )
    db.add(notification)
    
    await db.commit()
    await db.refresh(plugin_access)
    
    logger.info(f"Access granted to user {target_user.email} for plugin {plugin_id} by {current_user.email}")
    return plugin_access

@router.delete("/{plugin_id}/access/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_plugin_access(
    plugin_id: str,
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    enforcer: Enforcer = Depends(get_enforcer)
):
    """
    Revoke access from a user for a locked plugin (admin only)
    """
    admin_user_id = str(current_user.id)
    if not enforcer.enforce(admin_user_id, "plugins", "upload"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can revoke plugin access"
        )
    
    from app.core.utils import get_or_404
    plugin = await get_or_404(db, Plugin, plugin_id, resource_name="Plugin")
    
    # Convert user_id string to UUID
    from uuid import UUID
    try:
        target_user_uuid = UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID format"
        )
    
    # Find and delete access
    access_result = await db.execute(
        select(PluginAccess).where(
            PluginAccess.plugin_id == plugin_id,
            PluginAccess.user_id == target_user_uuid
        )
    )
    access = access_result.scalar_one_or_none()
    
    if not access:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Access record not found"
        )
    
    # Get target user for notification
    user_result = await db.execute(
        select(User).where(User.id == target_user_uuid)
    )
    target_user = user_result.scalar_one_or_none()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Update any approved access requests to rejected status
    # This ensures the user must request again after revocation
    approved_requests_result = await db.execute(
        select(PluginAccessRequest).where(
            PluginAccessRequest.plugin_id == plugin_id,
            PluginAccessRequest.user_id == target_user_uuid,
            PluginAccessRequest.status == AccessRequestStatus.APPROVED
        )
    )
    approved_requests = approved_requests_result.scalars().all()
    for req in approved_requests:
        req.status = AccessRequestStatus.REJECTED  # Mark as rejected so they must request again
        req.reviewed_at = datetime.utcnow()
        req.reviewed_by = current_user.id
    
    # Delete the access record
    await db.delete(access)
    
    # Create notification for the user
    from app.models import Notification, NotificationType
    notification = Notification(
        id=str(uuid.uuid4()),
        user_id=target_user_uuid,
        title=f"Plugin Access Revoked",
        message=f"Your access to plugin '{plugin.name}' has been revoked. You will need to request access again if needed.",
        type=NotificationType.WARNING,
        link=f"/provision/{plugin_id}"
    )
    db.add(notification)
    
    await db.commit()
    
    logger.info(f"Access revoked from user {target_user.email} for plugin {plugin_id} by {current_user.email}")
    
    from fastapi.responses import Response
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@router.get("/{plugin_id}/access", response_model=List[PluginAccessResponse])
async def list_plugin_access(
    plugin_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    enforcer: Enforcer = Depends(get_enforcer)
):
    """
    List users with access to a plugin (admin only)
    """
    user_id = str(current_user.id)
    if not enforcer.enforce(user_id, "plugins", "upload"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can view plugin access"
        )
    
    from app.core.utils import get_or_404
    plugin = await get_or_404(db, Plugin, plugin_id, resource_name="Plugin")
    
    result = await db.execute(
        select(PluginAccess).where(
            PluginAccess.plugin_id == plugin_id
        ).order_by(PluginAccess.granted_at.desc())
    )
    access_list = result.scalars().all()
    
    return access_list

@router.get("/access/grants", response_model=List[dict])
async def list_all_access_grants(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    enforcer: Enforcer = Depends(get_enforcer),
    user_email: str = Query(None, description="Filter by user email (partial match)")
):
    """
    List all access grants across all plugins with user and plugin info (admin only)
    Used for the plugin requests page to show who currently has access
    """
    user_id = str(current_user.id)
    if not enforcer.enforce(user_id, "plugins", "upload"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can view access grants"
        )
    
    # Build query with joins to get user email and plugin name
    query = select(PluginAccess, User.email, Plugin.name, User.id).join(
        User, PluginAccess.user_id == User.id
    ).join(
        Plugin, PluginAccess.plugin_id == Plugin.id
    )
    
    if user_email:
        query = query.where(User.email.ilike(f"%{user_email}%"))
    
    query = query.order_by(PluginAccess.granted_at.desc())
    
    result = await db.execute(query)
    rows = result.all()
    
    # Convert to response format with user email and plugin name
    grants = []
    for row in rows:
        access, user_email_val, plugin_name, user_uuid = row
        grants.append({
            "id": access.id,
            "plugin_id": access.plugin_id,
            "plugin_name": plugin_name,
            "user_id": str(access.user_id),
            "user_email": user_email_val,
            "granted_by": str(access.granted_by),
            "granted_at": access.granted_at.isoformat()
        })
    
    return grants
