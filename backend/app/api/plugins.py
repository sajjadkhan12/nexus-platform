"""Plugin management API endpoints"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List
import tempfile
import shutil
import os
import zipfile
from pathlib import Path

from app.database import get_db
from app.models import Plugin, PluginVersion, User, Job, JobLog
from app.schemas.plugins import PluginResponse, PluginVersionResponse
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
    
    response = []
    for plugin in plugins:
        plugin_data = PluginResponse(
            id=plugin.id,
            name=plugin.name,
            description=plugin.description,
            author=plugin.author,
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
    from app.core.utils import get_or_404
    plugin = await get_or_404(db, Plugin, plugin_id, resource_name="Plugin")
    return plugin

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
