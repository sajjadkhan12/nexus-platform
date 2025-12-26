from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List
import shutil
import os
from pathlib import Path
from app.database import get_db
from app.api.deps import get_current_user, get_current_active_superuser, is_allowed, OrgAwareEnforcer, get_org_aware_enforcer
from app.models.rbac import User, Role
from app.schemas.user import UserResponse, UserUpdate, UserAdminUpdate, UserPasswordUpdate, UserCreate, PaginatedUserResponse
from app.core.security import get_password_hash, verify_password

router = APIRouter(prefix="/users", tags=["users"])

async def user_to_response(user: User, enforcer: OrgAwareEnforcer, db: AsyncSession) -> UserResponse:
    """
    Helper function to convert User model to UserResponse with Casbin roles.
    Filters roles to ensure only actual roles from the database are returned (not group names).
    """
    # Get organization domain for role queries
    from app.core.organization import get_user_organization, get_organization_domain
    org = await get_user_organization(user, db)
    org_domain = get_organization_domain(org)
    
    user_roles = enforcer.get_roles_for_user(str(user.id))
    
    # Filter roles to ensure they exist in the database (exclude group names)
    if user_roles:
        # Get all valid role names from database
        result = await db.execute(select(Role.name))
        valid_role_names = {role_name for role_name in result.scalars().all()}
        
        # Filter user_roles to only include valid roles
        filtered_roles = [role for role in user_roles if role in valid_role_names]
        
        # Remove duplicates
        user_roles = list(set(filtered_roles))
    else:
        user_roles = []
    
    return UserResponse(
        id=user.id,
        email=user.email,
        username=user.username,
        full_name=user.full_name,
        avatar_url=user.avatar_url,
        is_active=user.is_active,
        created_at=user.created_at,
        roles=user_roles
    )

@router.get("/me", response_model=UserResponse)
async def read_users_me(
    current_user: User = Depends(get_current_user),  # Users should always be able to view their own profile
    enforcer: OrgAwareEnforcer = Depends(get_org_aware_enforcer),
    db: AsyncSession = Depends(get_db)
):
    return await user_to_response(current_user, enforcer, db)

@router.get("/me/permissions")
async def get_my_permissions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    enforcer: OrgAwareEnforcer = Depends(get_org_aware_enforcer)
):
    """
    Get all permissions for the current user based on their roles.
    Returns a list of permission slugs the user has access to.
    """
    from app.schemas.rbac import PermissionResponse
    from app.core.organization import get_user_organization, get_organization_domain
    from uuid import uuid4
    from datetime import datetime
    
    user_id = str(current_user.id)
    
    # Get organization domain for proper role filtering
    organization = await get_user_organization(current_user, db)
    org_domain = get_organization_domain(organization)
    
    # Get all roles for the user within their organization domain
    # OrgAwareEnforcer.get_roles_for_user() automatically uses org_domain
    user_roles = enforcer.get_roles_for_user(user_id)
    
    # Get all permissions for these roles
    # Access base enforcer to get all policies and filter manually
    from app.core.casbin import get_enforcer as get_base_enforcer
    from app.core.permission_registry import get_permission
    from app.models.rbac import PermissionMetadata
    from sqlalchemy import select
    
    base_enforcer = get_base_enforcer()
    
    all_permissions = set()
    for role in user_roles:
        # Get all policies for this role (across all domains)
        # Then filter by domain manually to ensure we get the right ones
        role_policies = base_enforcer.get_filtered_policy(0, role)
        
        for policy in role_policies:
            # Check if policy belongs to this organization domain
            if len(policy) >= 4:
                # Multi-tenant format: [role, domain, obj, act]
                # New format: obj="deployments", act="create:development" -> slug="deployments:create:development"
                policy_domain = str(policy[1]) if len(policy) > 1 else None
                # Compare domains as strings to handle UUID formatting
                if policy_domain == str(org_domain):
                    obj = policy[2]
                    act = policy[3]
                    # Construct permission slug: obj:act (act may contain environment, e.g., "create:development")
                    perm_slug = f"{obj}:{act}"
                    all_permissions.add(perm_slug)
            elif len(policy) >= 3:
                # Old format: [role, obj, act] - include it (no domain filtering needed)
                perm_slug = f"{policy[1]}:{policy[2]}"
                all_permissions.add(perm_slug)
    
    # Debug: Log extracted permissions for troubleshooting
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"User {user_id} (org_domain: {org_domain}) has roles: {user_roles}")
    logger.info(f"User {user_id} total permissions extracted: {len(all_permissions)}")
    deployment_perms = [p for p in all_permissions if p.startswith('deployments:')]
    if deployment_perms:
        logger.info(f"User {user_id} has deployment permissions: {deployment_perms}")
    else:
        logger.warning(f"User {user_id} has NO deployment permissions! All permissions: {sorted(all_permissions)}")
    
    # Get metadata from database or registry (gracefully handle if table doesn't exist yet)
    db_metadata = {}
    try:
        result = await db.execute(select(PermissionMetadata))
        db_metadata = {perm.slug: perm for perm in result.scalars().all()}
    except Exception:
        # Table doesn't exist yet - will use registry metadata only
        pass
    
    # Convert to response format with enriched metadata
    perm_responses = []
    for perm_slug in sorted(all_permissions):
        # Try to get metadata from registry first, then database
        perm_def = get_permission(perm_slug)
        db_perm = db_metadata.get(perm_slug)
        
        perm_response = PermissionResponse(
            id=db_perm.id if db_perm else None,
            slug=perm_slug,
            name=perm_def.get("name") if perm_def else None,
            description=perm_def.get("description") if perm_def else f"Permission for {perm_slug}",
            category=perm_def.get("category") if perm_def else None,
            resource=perm_def.get("resource") if perm_def else None,
            action=perm_def.get("action") if perm_def else None,
            environment=perm_def.get("environment") if perm_def else None,
            icon=perm_def.get("icon") if perm_def else None,
            created_at=db_perm.created_at if db_perm else None
        )
        perm_responses.append(perm_response)
    
    return perm_responses

@router.get("/me/debug")
async def get_my_debug_info(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    enforcer: OrgAwareEnforcer = Depends(get_org_aware_enforcer)
):
    """
    Debug endpoint to check user's roles and permissions.
    This helps diagnose permission issues.
    Only available in development mode.
    """
    from app.config import settings
    if not settings.DEBUG:
        raise HTTPException(
            status_code=404,
            detail="Not found"
        )
    from app.core.organization import get_user_organization, get_organization_domain
    from app.core.casbin import get_enforcer as get_base_enforcer
    
    user_id = str(current_user.id)
    
    # Get organization domain
    organization = await get_user_organization(current_user, db)
    org_domain = get_organization_domain(organization)
    
    # Get user roles (OrgAwareEnforcer automatically uses org_domain)
    user_roles = enforcer.get_roles_for_user(user_id)
    
    # Get all policies for user's roles, filtered by domain
    base_enforcer = get_base_enforcer()
    all_policies = []
    for role in user_roles:
        # Get all policies for this role, then filter by domain
        role_policies = base_enforcer.get_filtered_policy(0, role)
        for policy in role_policies:
            policy_domain = str(policy[1]) if len(policy) >= 4 else None
            matches_domain = policy_domain == str(org_domain) if len(policy) >= 4 else True
            all_policies.append({
                'role': role,
                'policy': policy,
                'format': 'multi-tenant' if len(policy) >= 4 else 'legacy',
                'policy_domain': policy_domain,
                'org_domain': str(org_domain),
                'matches_org_domain': matches_domain,
                'permission_slug': f"{policy[2]}:{policy[3]}" if len(policy) >= 4 else f"{policy[1]}:{policy[2]}"
            })
    
    # Check specific environment permissions using OrgAwareEnforcer
    # Permission format: deployments:development:create is stored as obj="deployments", act="development:create"
    env_permissions = {}
    for env in ['development', 'staging', 'production']:
        env_permission_obj = "deployments"
        env_permission_act = f"{env}:create"
        # Check if user can create in this environment
        # OrgAwareEnforcer.enforce() automatically adds org_domain
        can_create = enforcer.enforce(user_id, env_permission_obj, env_permission_act)
        env_permissions[env] = {
            'permission': f"{env_permission_obj}:{env_permission_act}",
            'has_permission': can_create
        }
    
    return {
        'user_id': user_id,
        'user_email': current_user.email,
        'organization_id': str(organization.id),
        'organization_domain': org_domain,
        'roles': user_roles,
        'policies': all_policies,
        'environment_permissions': env_permissions
    }


@router.get("/stats")
async def get_admin_stats(
    current_user: User = Depends(is_allowed("platform:users:list")),
    db: AsyncSession = Depends(get_db),
    enforcer: OrgAwareEnforcer = Depends(get_org_aware_enforcer)
):
    """Get system statistics for admin dashboard"""
    from sqlalchemy import func
    from app.models.rbac import Group
    
    # Count users in the same organization
    total_users = await db.scalar(
        select(func.count(User.id)).where(User.organization_id == current_user.organization_id)
    )
    active_users = await db.scalar(
        select(func.count(User.id)).where(
            User.is_active == True,
            User.organization_id == current_user.organization_id
        )
    )
    
    # Count groups from database
    # Note: Group isolation is handled by Casbin domains
    total_groups = await db.scalar(select(func.count(Group.id)))
    
    # Count roles from Casbin
    all_casbin_roles = enforcer.get_all_roles()
    total_roles = len(all_casbin_roles)
    
    # Calculate role distribution
    role_distribution = []
    for role in all_casbin_roles:
        users_in_role = enforcer.get_users_for_role(role)
        role_distribution.append({"role": role, "count": len(users_in_role)})
    
    return {
        "total_users": total_users or 0,
        "active_users": active_users or 0,
        "inactive_users": (total_users or 0) - (active_users or 0),
        "total_groups": total_groups or 0,
        "total_roles": total_roles,
        "role_distribution": role_distribution
    }

@router.put("/me", response_model=UserResponse)
async def update_user_me(
    user_update: UserUpdate,
    current_user: User = Depends(is_allowed("user:profile:update")),
    db: AsyncSession = Depends(get_db),
    enforcer: OrgAwareEnforcer = Depends(get_org_aware_enforcer)
):
    if user_update.email and user_update.email != current_user.email:
        result = await db.execute(select(User).where(User.email == user_update.email))
        if result.scalars().first():
            raise HTTPException(status_code=400, detail="Email already registered")
        current_user.email = user_update.email

    if user_update.full_name:
        current_user.full_name = user_update.full_name
    
    if user_update.password:
        current_user.hashed_password = get_password_hash(user_update.password)
        
    await db.commit()
    await db.refresh(current_user)
    return await user_to_response(current_user, enforcer, db)

@router.post("/me/avatar", response_model=UserResponse)
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(is_allowed("user:profile:update")),
    db: AsyncSession = Depends(get_db),
    enforcer: OrgAwareEnforcer = Depends(get_org_aware_enforcer)
):
    from app.core.file_validation import validate_avatar_upload, sanitize_filename
    
    # Read file content for validation
    file_content = await file.read()
    file_size = len(file_content)
    
    # Validate file
    is_valid, error_msg = validate_avatar_upload(file_content, file.filename or "", file_size)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)
    
    # Sanitize filename
    sanitized_name = sanitize_filename(file.filename or "avatar")
    file_extension = Path(sanitized_name).suffix or ".jpg"
    
    # Create static/avatars directory if it doesn't exist
    avatars_dir = Path("static/avatars")
    avatars_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate unique filename using user ID (prevents conflicts and path traversal)
    filename = f"{current_user.id}{file_extension}"
    file_path = avatars_dir / filename
    
    # Save file
    with file_path.open("wb") as buffer:
        buffer.write(file_content)
    
    # Update user avatar URL
    current_user.avatar_url = f"/static/avatars/{filename}"
    await db.commit()
    await db.refresh(current_user)
    
    return await user_to_response(current_user, enforcer, db)

@router.put("/me/password")
async def change_password(
    password_update: UserPasswordUpdate,
    current_user: User = Depends(is_allowed("user:profile:update")),
    db: AsyncSession = Depends(get_db)
):
    from app.core.security import validate_password_strength
    
    # Verify current password
    if not verify_password(password_update.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect current password")
    
    # Validate password strength
    is_valid, error_message = validate_password_strength(password_update.new_password)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_message)
    
    # Update to new password
    current_user.hashed_password = get_password_hash(password_update.new_password)
    await db.commit()
    
    return {"message": "Password updated successfully"}

@router.get("/", response_model=PaginatedUserResponse)
async def list_users(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=1000, description="Maximum number of records to return"),
    search: str = Query(None, description="Search by email, username, or full name"),
    role: str = Query(None, description="Filter by role name"),
    current_user: User = Depends(is_allowed("platform:users:list")),
    db: AsyncSession = Depends(get_db),
    enforcer: OrgAwareEnforcer = Depends(get_org_aware_enforcer)
):
    from sqlalchemy import func, or_
    
    # Base count query - filter by organization
    count_query = select(func.count(User.id)).where(User.organization_id == current_user.organization_id)
    
    # Base data query - filter by organization
    query = select(User).where(User.organization_id == current_user.organization_id)
    
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
            User.email.ilike(search_pattern),
            User.username.ilike(search_pattern),
            User.full_name.ilike(search_pattern)
        )
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)
        
    # Get organization domain for role queries
    from app.core.organization import get_user_organization, get_organization_domain
    org = await get_user_organization(current_user, db)
    org_domain = get_organization_domain(org)
    
    # Role filtering
    if role:
        users_with_role = enforcer.get_users_for_role(role)
        if users_with_role:
            # Convert string IDs to UUIDs for the query
            from uuid import UUID
            try:
                user_uuids = [UUID(uid) for uid in users_with_role]
                query = query.where(User.id.in_(user_uuids))
                count_query = count_query.where(User.id.in_(user_uuids))
            except (ValueError, TypeError):
                # If conversion fails, return empty result
                return {
                    "items": [],
                    "total": 0,
                    "skip": skip,
                    "limit": limit
                }
        else:
            return {
                "items": [],
                "total": 0,
                "skip": skip,
                "limit": limit
            }
    
    # Get total count
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # Apply pagination
    query = query.offset(skip).limit(limit)
    
    result = await db.execute(query)
    users = result.scalars().all()
    
    # Debug: Log users found
    from app.logger import logger
    # Removed debug logging with sensitive user data
    
    # Optimize: Load all valid role names once (instead of per user)
    role_result = await db.execute(select(Role.name))
    valid_role_names = {role_name for role_name in role_result.scalars().all()}
    
    # Build response with filtered roles - batch process
    user_responses = []
    # org_domain is already retrieved above for role filtering, reuse it here
    
    # Ensure enforcer has org_domain set (OrgAwareEnforcer should already have it, but be safe)
    if hasattr(enforcer, 'set_org_domain') and (not hasattr(enforcer, '_org_domain') or not enforcer._org_domain):
        enforcer.set_org_domain(org_domain)
    
    for user in users:
        # Get roles for user with organization domain
        user_roles = enforcer.get_roles_for_user(str(user.id))
        
        # Filter roles to ensure they exist in the database (exclude group names)
        if user_roles:
            filtered_roles = [role for role in user_roles if role in valid_role_names]
            user_roles = list(set(filtered_roles))  # Remove duplicates
        else:
            user_roles = []
        
        user_responses.append(UserResponse(
            id=user.id,
            email=user.email,
            username=user.username,
            full_name=user.full_name,
            avatar_url=user.avatar_url,
            is_active=user.is_active,
            created_at=user.created_at,
            roles=user_roles
        ))
    
    return {
        "items": user_responses,
        "total": total,
        "skip": skip,
        "limit": limit
    }

@router.post("/", response_model=UserResponse)
async def create_user(
    user_in: UserCreate,
    current_user: User = Depends(is_allowed("platform:users:create")),
    db: AsyncSession = Depends(get_db),
    enforcer: OrgAwareEnforcer = Depends(get_org_aware_enforcer)
):
    """
    Create a new user (Admin only)
    """
    # Check if user exists
    result = await db.execute(select(User).where(User.email == user_in.email))
    if result.scalars().first():
        raise HTTPException(
            status_code=400,
            detail="The user with this email already exists in the system.",
        )
    
    # Validate password strength
    from app.core.security import validate_password_strength
    is_valid, error_message = validate_password_strength(user_in.password)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_message)
    
    # Generate username from email with validation and uniqueness check
    base_username = user_in.email.split("@")[0]
    # Sanitize username: remove invalid characters, keep alphanumeric, dots, hyphens, underscores
    import re
    base_username = re.sub(r'[^a-zA-Z0-9._-]', '', base_username)
    # Remove leading/trailing dots and hyphens
    base_username = base_username.strip('.-_')
    # Ensure it's not empty
    if not base_username:
        base_username = "user"
    
    # Check for uniqueness and handle collisions
    username = base_username
    counter = 1
    while True:
        result = await db.execute(select(User).where(User.username == username))
        if not result.scalars().first():
            break  # Username is available
        username = f"{base_username}{counter}"
        counter += 1
        # Safety limit to prevent infinite loop
        if counter > 1000:
            raise HTTPException(
                status_code=500,
                detail="Unable to generate unique username. Please try again."
            )
    
    user = User(
        email=user_in.email,
        username=username,
        hashed_password=get_password_hash(user_in.password),
        full_name=user_in.full_name,
        organization_id=current_user.organization_id,
        is_active=True
    )
    
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    # User is created without roles. Roles will be assigned via Groups.
    
    return await user_to_response(user, enforcer, db)

@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    user_in: UserAdminUpdate,
    current_user: User = Depends(is_allowed("platform:users:update")),
    db: AsyncSession = Depends(get_db),
    enforcer: OrgAwareEnforcer = Depends(get_org_aware_enforcer)
):
    """
    Update a user (Admin only)
    """
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    if user_in.email and user_in.email != user.email:
        result = await db.execute(select(User).where(User.email == user_in.email))
        if result.scalars().first():
            raise HTTPException(status_code=400, detail="Email already registered")
        user.email = user_in.email
        
    if user_in.full_name is not None:
        user.full_name = user_in.full_name
        
    if user_in.is_active is not None:
        user.is_active = user_in.is_active
        
    if user_in.password:
        user.hashed_password = get_password_hash(user_in.password)
        
    if user_in.roles is not None:
        # Update roles via Casbin
        # First remove all existing roles for this user
        enforcer.delete_roles_for_user(str(user.id))
        # Add new roles
        for role_name in user_in.roles:
            enforcer.add_grouping_policy(str(user.id), role_name)
                
    await db.commit()
    await db.refresh(user)
    return await user_to_response(user, enforcer, db)

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: str,
    current_user: User = Depends(is_allowed("platform:users:delete")),
    db: AsyncSession = Depends(get_db),
    enforcer: OrgAwareEnforcer = Depends(get_org_aware_enforcer)
):
    """
    Delete a user (Admin only)
    """
    if str(current_user.id) == user_id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
        
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Delete related records that might not cascade automatically
    # (Even though schema has CASCADE, we'll be explicit for safety)
    from app.models.notification import Notification
    
    # Delete notifications for this user
    notifications_result = await db.execute(
        select(Notification).where(Notification.user_id == user.id)
    )
    notifications = notifications_result.scalars().all()
    for notification in notifications:
        await db.delete(notification)
    
    # Flush to ensure notifications are deleted before user deletion
    await db.flush()
    
    # Remove all Casbin policies for this user
    enforcer.delete_user(str(user.id))
        
    # Delete the user (other related records should cascade from schema)
    await db.delete(user)
    await db.commit()
