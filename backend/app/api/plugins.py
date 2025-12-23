"""Plugin management API - backward compatibility layer"""
# Import from modular structure
from app.api.plugins import router

@router.post("/upload", response_model=PluginVersionResponse, status_code=status.HTTP_201_CREATED)
async def upload_plugin(
    file: UploadFile = File(...),  # Required for ZIP uploads
    git_repo_url: Optional[str] = Form(None),  # Optional form field
    git_branch: Optional[str] = Form(None),  # Optional form field
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
    user_id = str(current_user.id)
    if not enforcer.enforce(user_id, "plugins", "upload"):
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
            # Plugin version already exists - return error instead of replacing
            logger.warning(f"Plugin version already exists: {plugin_id} v{version}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Plugin '{plugin_id}' version '{version}' already exists. Please use a different version or delete the existing version first."
            )
        
        # Determine Git repository URL (use provided or default from config)
        # Check if GITHUB_REPOSITORY is set (not empty string)
        config_repo_url = getattr(settings, 'GITHUB_REPOSITORY', None) if hasattr(settings, 'GITHUB_REPOSITORY') else None
        config_repo_url = config_repo_url.strip() if config_repo_url and isinstance(config_repo_url, str) else None
        final_git_repo_url = git_repo_url or config_repo_url
        
        # Log GitOps configuration status with detailed info
        if final_git_repo_url:
            github_token_set = bool(getattr(settings, 'GITHUB_TOKEN', '') and getattr(settings, 'GITHUB_TOKEN', '').strip())
            if github_token_set:
                logger.info(f"GitOps enabled: repository={final_git_repo_url}, branch={git_branch or 'auto-generated'}")
            else:
                logger.warning(f"GitOps repository configured but GITHUB_TOKEN is missing! Git push will fail.")
                logger.info(f"GitOps enabled: repository={final_git_repo_url}, branch={git_branch or 'auto-generated'} (WARNING: No token)")
        else:
            logger.info("GitOps disabled: GITHUB_REPOSITORY not configured in .env file.")
            logger.info("To enable GitOps, add to your .env file:")
            logger.info("  GITHUB_REPOSITORY=https://github.com/your-org/your-repo.git")
            logger.info("  GITHUB_TOKEN=ghp_your_personal_access_token")
        
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
            
            # Check if there's a single root directory (common in ZIP files)
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
                    
                    # Create template branch name from plugin identifier (e.g., "plugin-gcp-bucket")
                    # This branch will act as the long‑lived template for all deployments.
                    if not final_git_branch:
                        import re
                        # Prefer a human‑readable name from the manifest, fall back to plugin_id
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
            manifest=manifest if manifest else {},  # Ensure manifest is not None
            storage_path=storage_path if file else "",  # Empty for GitOps-only
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
        # Clean up temp file (if ZIP was uploaded)
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
    logger.debug(f"Request content-type: {request.headers.get('content-type')}")
    logger.debug(f"Form data - plugin_id: {plugin_id}, name: {name}, template_repo_url: {template_repo_url}, template_path: {template_path}")
    
    # Check permission
    user_id = str(current_user.id)
    if not enforcer.enforce(user_id, "plugins", "upload"):
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
            "language": "python",  # Could be extracted from template_path or made configurable
            "framework": "fastapi"  # Could be extracted or made configurable
        }
        
        # Create plugin version record
        plugin_version = PluginVersion(
            plugin_id=plugin_id,
            version=version,
            manifest=manifest,
            storage_path="",  # Not used for microservices
            template_repo_url=template_repo_url.strip(),
            template_path=template_path.strip(),
            git_repo_url=template_repo_url.strip(),  # Use same URL for git_repo_url
            git_branch="main"  # Default branch
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
    
    # Check if user is admin
    user_id = str(current_user.id)
    is_admin = enforcer.has_grouping_policy(user_id, "admin") or enforcer.enforce(user_id, "plugins", "upload")
    
    # Check which plugins the user has access to (only needed for non-admins)
    # Only APPROVED requests grant access (REVOKED means access was removed)
    user_access = set()
    if not is_admin:
        access_result = await db.execute(
            select(PluginAccessRequest).where(
                PluginAccessRequest.user_id == current_user.id,
                PluginAccessRequest.status == AccessRequestStatus.APPROVED
            )
        )
        user_access = {req.plugin_id for req in access_result.scalars().all()}
    
    # Check pending requests for non-admins
    pending_requests = set()
    if not is_admin:
        pending_result = await db.execute(
            select(PluginAccessRequest).where(
                PluginAccessRequest.user_id == current_user.id,
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
    enforcer: OrgAwareEnforcer = Depends(get_org_aware_enforcer)
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
    user_id = str(current_user.id)
    is_admin = enforcer.has_grouping_policy(user_id, "admin") or enforcer.enforce(user_id, "plugins", "upload")
    
    # Check if user has access: admins can deploy locked plugins, but visually it's still locked
    if plugin.is_locked:
        # For locked plugins, check if user has explicit access (or is admin for deployment)
        has_access = is_admin
        if not is_admin:
            # Check for active (approved) access - must not be revoked
            access_request_result = await db.execute(
                select(PluginAccessRequest).where(
                    PluginAccessRequest.plugin_id == plugin_id,
                    PluginAccessRequest.user_id == current_user.id,
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
    enforcer: OrgAwareEnforcer = Depends(get_org_aware_enforcer)
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
    user_id = str(current_user.id)
    if not enforcer.enforce(user_id, "plugins", "upload"):
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
    user_id = str(current_user.id)
    if not enforcer.enforce(user_id, "plugins", "upload"):
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

@router.post("/{plugin_id}/access/request", response_model=PluginAccessRequestResponse, status_code=status.HTTP_201_CREATED)
async def request_plugin_access(
    plugin_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    enforcer: OrgAwareEnforcer = Depends(get_org_aware_enforcer)
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
    
    # Check if user already has approved access
    access_result = await db.execute(
        select(PluginAccessRequest).where(
            PluginAccessRequest.plugin_id == plugin_id,
            PluginAccessRequest.user_id == current_user.id,
            PluginAccessRequest.status == AccessRequestStatus.APPROVED
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
            PluginAccessRequest.status == AccessRequestStatus.PENDING
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
    
    # Create notification for admins in the same organization
    from app.models import Notification, NotificationType
    from sqlalchemy import select as sql_select
    
    # Get all users in the same organization
    admin_users_result = await db.execute(
        sql_select(User).where(User.organization_id == current_user.organization_id)
    )
    org_users = admin_users_result.scalars().all()
    
    # Filter to only admins using enforcer
    admin_user_ids = []
    for user in org_users:
        user_id_str = str(user.id)
        # Check if user has admin role or plugins:upload permission
        if enforcer.has_grouping_policy(user_id_str, "admin") or enforcer.enforce(user_id_str, "plugins", "upload"):
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
    enforcer: OrgAwareEnforcer = Depends(get_org_aware_enforcer),
    search: str = Query(None, description="Search by user email, username, full name, or plugin name (partial match)"),
    status: str = Query(None, description="Filter by status: pending, approved, rejected")
):
    """
    List all access requests across all plugins (admin only)
    Optional search by user email, username, full name, or plugin name
    Optional filter by status
    """
    from sqlalchemy import or_
    
    user_id = str(current_user.id)
    if not enforcer.enforce(user_id, "plugins", "upload"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can view access requests"
        )
    
    # Build query with joins
    query = select(PluginAccessRequest, User.email, User.username, User.full_name, Plugin.name).join(
        User, PluginAccessRequest.user_id == User.id
    ).join(
        Plugin, PluginAccessRequest.plugin_id == Plugin.id
    )
    
    # Apply search filter (searches across email, username, full_name, and plugin name)
    if search:
        search_pattern = f"%{search}%"
        query = query.where(
            or_(
                User.email.ilike(search_pattern),
                User.username.ilike(search_pattern),
                User.full_name.ilike(search_pattern),
                Plugin.name.ilike(search_pattern),
                Plugin.id.ilike(search_pattern)
            )
        )
    
    # Apply status filter
    if status:
        query = query.where(PluginAccessRequest.status == status)
    
    query = query.order_by(PluginAccessRequest.requested_at.desc())
    
    result = await db.execute(query)
    rows = result.all()
    
    # Convert to response format with user email and plugin name
    from app.schemas.plugins import PluginAccessRequestResponse
    requests = []
    for row in rows:
        request, user_email_val, username, full_name, plugin_name = row
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
    enforcer: OrgAwareEnforcer = Depends(get_org_aware_enforcer)
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
    enforcer: OrgAwareEnforcer = Depends(get_org_aware_enforcer)
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
        req.reviewed_at = datetime.now(timezone.utc)
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

@router.post("/{plugin_id}/access/reject", status_code=status.HTTP_200_OK)
async def reject_plugin_access_request(
    plugin_id: str,
    request: PluginAccessGrantRequest,  # Reuse same schema for user_id
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    enforcer: OrgAwareEnforcer = Depends(get_org_aware_enforcer)
):
    """
    Reject a pending plugin access request (admin only)
    """
    user_id = str(current_user.id)
    if not enforcer.enforce(user_id, "plugins", "upload"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can reject plugin access requests"
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
    
    # Find pending access requests for this user and plugin
    pending_requests_result = await db.execute(
        select(PluginAccessRequest).where(
            PluginAccessRequest.plugin_id == plugin_id,
            PluginAccessRequest.user_id == request.user_id,
            PluginAccessRequest.status == AccessRequestStatus.PENDING
        )
    )
    pending_requests = pending_requests_result.scalars().all()
    
    if not pending_requests:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No pending access request found for this user and plugin"
        )
    
    # Update all pending requests to rejected
    for req in pending_requests:
        req.status = AccessRequestStatus.REJECTED
        req.reviewed_at = datetime.now(timezone.utc)
        req.reviewed_by = current_user.id
    
    # Create notification for the user
    from app.models import Notification, NotificationType
    notification = Notification(
        id=str(uuid.uuid4()),
        user_id=request.user_id,
        title=f"Plugin Access Request Rejected",
        message=f"Your access request for plugin '{plugin.name}' has been rejected. Please contact an administrator if you believe this is an error.",
        type=NotificationType.WARNING,
        link=f"/provision/{plugin_id}"
    )
    db.add(notification)
    
    await db.commit()
    
    logger.info(f"Access request rejected for user {target_user.email} for plugin {plugin_id} by {current_user.email}")
    
    return {"message": "Access request rejected successfully", "status": "rejected"}

@router.delete("/{plugin_id}/access/{user_id}", status_code=status.HTTP_200_OK)
async def revoke_plugin_access(
    plugin_id: str,
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    enforcer: OrgAwareEnforcer = Depends(get_org_aware_enforcer)
):
    """
    Revoke access from a user for a locked plugin (admin only)
    Sets the access request status to 'revoked' instead of deleting
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
    
    # Find and delete the access grant (user loses access)
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
    
    # Update any approved access requests to revoked status
    # This allows tracking of revoked access in the revoked tab
    approved_requests_result = await db.execute(
        select(PluginAccessRequest).where(
            PluginAccessRequest.plugin_id == plugin_id,
            PluginAccessRequest.user_id == target_user_uuid,
            PluginAccessRequest.status == AccessRequestStatus.APPROVED
        )
    )
    approved_requests = approved_requests_result.scalars().all()
    for req in approved_requests:
        req.status = AccessRequestStatus.REVOKED  # Mark as revoked to show in revoked tab
        req.reviewed_at = datetime.now(timezone.utc)
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
    
    return {"message": "Access revoked successfully", "status": "revoked"}

@router.post("/{plugin_id}/access/{user_id}/restore", status_code=status.HTTP_200_OK)
async def restore_plugin_access(
    plugin_id: str,
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    enforcer: OrgAwareEnforcer = Depends(get_org_aware_enforcer)
):
    """
    Restore access for a user (admin only)
    Changes the revoked status back to approved and creates a new PluginAccess record
    """
    admin_user_id = str(current_user.id)
    if not enforcer.enforce(admin_user_id, "plugins", "upload"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can restore plugin access"
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
    
    # Find the revoked request
    revoked_request_result = await db.execute(
        select(PluginAccessRequest).where(
            PluginAccessRequest.plugin_id == plugin_id,
            PluginAccessRequest.user_id == target_user_uuid,
            PluginAccessRequest.status == AccessRequestStatus.REVOKED
        )
    )
    revoked_request = revoked_request_result.scalar_one_or_none()
    
    if not revoked_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No revoked access found for this user and plugin"
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
    
    # Check if access already exists (shouldn't happen, but just in case)
    existing_access_result = await db.execute(
        select(PluginAccess).where(
            PluginAccess.plugin_id == plugin_id,
            PluginAccess.user_id == target_user_uuid
        )
    )
    existing_access = existing_access_result.scalar_one_or_none()
    
    if not existing_access:
        # Create new access grant
        new_access = PluginAccess(
            plugin_id=plugin_id,
            user_id=target_user_uuid,
            granted_by=current_user.id
        )
        db.add(new_access)
    
    # Update request status back to approved
    revoked_request.status = AccessRequestStatus.APPROVED
    revoked_request.reviewed_at = datetime.now(timezone.utc)
    revoked_request.reviewed_by = current_user.id
    
    # Create notification for the user
    from app.models import Notification, NotificationType
    notification = Notification(
        id=str(uuid.uuid4()),
        user_id=target_user_uuid,
        title=f"Plugin Access Restored",
        message=f"Your access to plugin '{plugin.name}' has been restored by an administrator.",
        type=NotificationType.INFO,
        link=f"/provision/{plugin_id}"
    )
    db.add(notification)
    
    await db.commit()
    
    logger.info(f"Access restored to user {target_user.email} for plugin {plugin_id} by {current_user.email}")
    
    return {"message": "Access restored successfully", "status": "approved"}

@router.get("/{plugin_id}/access", response_model=List[PluginAccessResponse])
async def list_plugin_access(
    plugin_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    enforcer: OrgAwareEnforcer = Depends(get_org_aware_enforcer)
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
    enforcer: OrgAwareEnforcer = Depends(get_org_aware_enforcer),
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
