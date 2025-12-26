"""Plugin upload endpoints"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
import tempfile
import shutil
import zipfile
import re
from pathlib import Path

from app.database import get_db
from app.models import Plugin, PluginVersion, User
from app.schemas.plugins import PluginVersionResponse
from app.services.storage import storage_service
from app.services.plugin_validator import plugin_validator
from app.api.deps import get_current_user, OrgAwareEnforcer, get_org_aware_enforcer
from app.logger import logger
from app.config import settings

router = APIRouter()

@router.post("/upload", response_model=PluginVersionResponse, status_code=status.HTTP_201_CREATED)
async def upload_plugin(
    file: UploadFile = File(...),
    git_repo_url: Optional[str] = Form(None),
    git_branch: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    enforcer: OrgAwareEnforcer = Depends(get_org_aware_enforcer)
):
    """
    Upload a new plugin or plugin version
    Requires: plugins:upload permission (admin only)
    """
    logger.info(f"Plugin upload request received from user {current_user.email}, filename: {file.filename if file else 'None'}")
    
    # Check permission - only admins can upload plugins
    from app.core.authorization import check_platform_permission
    has_permission = await check_platform_permission(current_user, "platform:plugins:upload", db, enforcer.enforcer if hasattr(enforcer, 'enforcer') else enforcer)
    if not has_permission:
        logger.warning(f"User {current_user.email} attempted to upload plugin without permission")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can upload plugins"
        )
    
    # Validate file is provided
    if not file or not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File upload is required"
        )
    
    # Initialize variables
    tmp_path = None
    manifest = None
    plugin_id = None
    version = None
    
    # ZIP file validation
    if not file.filename or not file.filename.endswith('.zip'):
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
    
    # Validate plugin ZIP
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
    
    try:
        # Check if plugin exists
        result = await db.execute(select(Plugin).where(Plugin.id == plugin_id))
        plugin = result.scalar_one_or_none()
        
        if not plugin:
            # Create new plugin
            plugin = Plugin(
                id=plugin_id,
                name=manifest.get('name', plugin_id) if manifest else plugin_id,
                description=manifest.get('description') if manifest else None,
                author=manifest.get('author') if manifest else None
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
            logger.warning(f"Plugin version already exists: {plugin_id} v{version}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Plugin '{plugin_id}' version '{version}' already exists. Please use a different version or delete the existing version first."
            )
        
        # Determine Git repository URL
        config_repo_url = getattr(settings, 'GITHUB_REPOSITORY', None) if hasattr(settings, 'GITHUB_REPOSITORY') else None
        config_repo_url = config_repo_url.strip() if config_repo_url and isinstance(config_repo_url, str) else None
        final_git_repo_url = git_repo_url or config_repo_url
        
        # Log GitOps configuration status
        if final_git_repo_url:
            github_token_set = bool(getattr(settings, 'GITHUB_TOKEN', '') and getattr(settings, 'GITHUB_TOKEN', '').strip())
            if github_token_set:
                logger.info(f"GitOps enabled: repository={final_git_repo_url}, branch={git_branch or 'auto-generated'}")
            else:
                logger.warning(f"GitOps repository configured but GITHUB_TOKEN is missing! Git push will fail.")
                logger.warning(f"GitOps enabled but GITHUB_TOKEN is missing! Git push will fail.")
        else:
            logger.debug("GitOps disabled: GITHUB_REPOSITORY not configured")
        
        # If file is uploaded, extract and push to GitHub
        storage_path = ""
        final_git_branch = git_branch
        
        if tmp_path is not None and tmp_path.exists():
            # Save to storage for backward compatibility
            with open(tmp_path, 'rb') as f:
                storage_path = storage_service.save_plugin(plugin_id, version, f)
            
            # Extract the zip file - flatten structure if ZIP contains a single root directory
            extract_dir = Path(storage_path).parent / "extracted"
            extract_dir.mkdir(parents=True, exist_ok=True)
            
            # First extract to a temp location to check structure
            temp_extract = Path(storage_path).parent / "temp_extract"
            temp_extract.mkdir(parents=True, exist_ok=True)
            
            with zipfile.ZipFile(tmp_path, 'r') as zip_ref:
                members = [m for m in zip_ref.infolist() if not (m.filename.startswith('__MACOSX') or m.filename.endswith('.DS_Store'))]
                zip_ref.extractall(temp_extract, members)
            
            # Check if there's a single root directory
            root_items = list(temp_extract.iterdir())
            if len(root_items) == 1 and root_items[0].is_dir() and root_items[0].name == plugin_id:
                # ZIP has a single root directory matching plugin_id - flatten it
                logger.info(f"Flattening ZIP structure: moving files from {root_items[0].name}/ to root")
                for item in root_items[0].iterdir():
                    dest = extract_dir / item.name
                    if item.is_dir():
                        shutil.copytree(item, dest, dirs_exist_ok=True)
                    else:
                        shutil.copy2(item, dest)
                shutil.rmtree(temp_extract, ignore_errors=True)
            else:
                # No single root directory - copy all items as-is
                for item in root_items:
                    dest = extract_dir / item.name
                    if item.is_dir():
                        shutil.copytree(item, dest, dirs_exist_ok=True)
                    else:
                        shutil.copy2(item, dest)
                shutil.rmtree(temp_extract, ignore_errors=True)
            
            logger.info(f"Plugin extracted to: {extract_dir}")
            
            # If GitOps is enabled, push to GitHub
            if final_git_repo_url:
                try:
                    from app.services.git_service import git_service
                    
                    # Create template branch name from plugin identifier
                    if not final_git_branch:
                        # Prefer a human-readable name from the manifest, fall back to plugin_id
                        raw_name = (manifest or {}).get('name') or plugin_id
                        # Normalize: lowercase, replace spaces/underscores with hyphens
                        base_name = raw_name.lower().replace(" ", "-").replace("_", "-")
                        # Remove invalid characters for Git branch names
                        base_name = re.sub(r'[^a-z0-9\-]', '-', base_name)
                        base_name = re.sub(r'-+', '-', base_name).strip('-')
                        if not base_name:
                            base_name = plugin_id.lower()
                        branch_name = f"plugin-{base_name}"
                        final_git_branch = branch_name
                    
                    logger.info(f"Pushing plugin to GitHub: {final_git_repo_url} branch {final_git_branch}")
                    
                    # Push extracted files to GitHub branch
                    git_service.initialize_and_push_plugin(
                        repo_url=final_git_repo_url,
                        branch=final_git_branch,
                        source_dir=extract_dir,
                        commit_message=f"Upload plugin {plugin_id} version {version}"
                    )
                    
                    logger.info(f"Successfully pushed plugin to GitHub branch {final_git_branch}")
                    
                except Exception as e:
                    logger.error(f"Failed to push plugin to GitHub: {e}", exc_info=True)
                    # Continue without GitOps if push fails (backward compatibility)
                    if not git_repo_url:
                        # If GitOps was optional, continue
                        final_git_repo_url = None
                        final_git_branch = None
                    else:
                        # If GitOps was required, raise error
                        raise HTTPException(
                            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Failed to push plugin to GitHub: {str(e)}"
                        )
        
        # Create plugin version record
        plugin_version = PluginVersion(
            plugin_id=plugin_id,
            version=version,
            manifest=manifest if manifest else {},
            storage_path=storage_path if file else "",
            git_repo_url=final_git_repo_url,
            git_branch=final_git_branch
        )
        db.add(plugin_version)
        
        await db.commit()
        await db.refresh(plugin_version)
        
        return plugin_version
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in plugin upload: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload plugin: {str(e)}"
        )
    finally:
        # Clean up temp file
        if tmp_path is not None and tmp_path.exists():
            tmp_path.unlink(missing_ok=True)

@router.post("/upload-template", response_model=PluginVersionResponse, status_code=status.HTTP_201_CREATED)
async def upload_microservice_template(
    request: Request,
    plugin_id: str = Form(...),
    name: str = Form(...),
    version: str = Form(...),
    description: str = Form(...),
    template_repo_url: str = Form(...),
    template_path: str = Form(...),
    author: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    enforcer: OrgAwareEnforcer = Depends(get_org_aware_enforcer)
):
    """
    Create a microservice template (no file upload required)
    Requires: plugins:upload permission (admin only)
    """
    logger.info(f"Microservice template creation request from user {current_user.email}: {plugin_id} v{version}")
    
    # Check permission
    from app.core.authorization import check_platform_permission
    has_permission = await check_platform_permission(current_user, "platform:plugins:upload", db, enforcer.enforcer if hasattr(enforcer, 'enforcer') else enforcer)
    if not has_permission:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can create microservice templates"
        )
    
    # Validate inputs
    if not template_repo_url.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Template repository URL is required"
        )
    
    if not template_path.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Template path is required"
        )
    
    try:
        # Check if plugin exists
        result = await db.execute(select(Plugin).where(Plugin.id == plugin_id))
        plugin = result.scalar_one_or_none()
        
        if not plugin:
            # Create new plugin
            plugin = Plugin(
                id=plugin_id,
                name=name,
                description=description,
                author=author or current_user.email,
                deployment_type="microservice",
                is_locked=False
            )
            db.add(plugin)
            logger.info(f"Created microservice plugin: {plugin_id}")
        else:
            # Update existing plugin
            plugin.name = name
            plugin.description = description
            plugin.deployment_type = "microservice"
            if author:
                plugin.author = author
            logger.info(f"Updated microservice plugin: {plugin_id}")
        
        await db.flush()
        
        # Check if version exists
        result = await db.execute(
            select(PluginVersion).where(
                PluginVersion.plugin_id == plugin_id,
                PluginVersion.version == version
            )
        )
        existing_version = result.scalar_one_or_none()
        if existing_version:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Plugin '{plugin_id}' version '{version}' already exists. Please use a different version."
            )
        
        # Create manifest for microservice
        manifest = {
            "id": plugin_id,
            "name": name,
            "version": version,
            "description": description,
            "deployment_type": "microservice",
            "cloud_provider": "kubernetes",
            "language": "python",
            "framework": "fastapi"
        }
        
        # Create plugin version record
        plugin_version = PluginVersion(
            plugin_id=plugin_id,
            version=version,
            manifest=manifest,
            storage_path="",
            template_repo_url=template_repo_url.strip(),
            template_path=template_path.strip(),
            git_repo_url=template_repo_url.strip(),
            git_branch="main"
        )
        db.add(plugin_version)
        
        await db.commit()
        await db.refresh(plugin_version)
        
        logger.info(f"Successfully created microservice template: {plugin_id} v{version}")
        return plugin_version
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating microservice template: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create microservice template: {str(e)}"
        )

