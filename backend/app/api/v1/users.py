from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List
import shutil
import os
from pathlib import Path
from app.database import get_db
from app.api.deps import get_current_user, get_current_active_superuser, is_allowed, OrgAwareEnforcer, get_org_aware_enforcer
from app.models.rbac import User
from app.schemas.user import UserResponse, UserUpdate, UserAdminUpdate, UserPasswordUpdate, UserCreate, PaginatedUserResponse
from app.core.security import get_password_hash, verify_password

router = APIRouter(prefix="/users", tags=["users"])

def user_to_response(user: User, enforcer: OrgAwareEnforcer) -> UserResponse:
    """Helper function to convert User model to UserResponse with Casbin roles"""
    user_roles = enforcer.get_roles_for_user(str(user.id))
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
    current_user: User = Depends(is_allowed("profile:read")),
    enforcer: OrgAwareEnforcer = Depends(get_org_aware_enforcer)
):
    return user_to_response(current_user, enforcer)


@router.get("/stats")
async def get_admin_stats(
    current_user: User = Depends(is_allowed("users:list")),
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
    current_user: User = Depends(is_allowed("profile:update")),
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
    return user_to_response(current_user, enforcer)

@router.post("/me/avatar", response_model=UserResponse)
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(is_allowed("profile:update")),
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
    
    return user_to_response(current_user, enforcer)

@router.put("/me/password")
async def change_password(
    password_update: UserPasswordUpdate,
    current_user: User = Depends(is_allowed("profile:update")),
    db: AsyncSession = Depends(get_db)
):
    # Verify current password
    if not verify_password(password_update.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect current password")
    
    # Update to new password
    current_user.hashed_password = get_password_hash(password_update.new_password)
    await db.commit()
    
    return {"message": "Password updated successfully"}

@router.get("/", response_model=PaginatedUserResponse)
async def list_users(
    skip: int = 0,
    limit: int = 50,
    search: str = None,
    role: str = None,
    current_user: User = Depends(is_allowed("users:list")),
    db: AsyncSession = Depends(get_db),
    enforcer: OrgAwareEnforcer = Depends(get_org_aware_enforcer)
):
    from sqlalchemy import func, or_
    
    # Base count query - filter by organization
    count_query = select(func.count(User.id)).where(User.organization_id == current_user.organization_id)
    
    # Base data query - filter by organization
    query = select(User).where(User.organization_id == current_user.organization_id)
    
    # Apply search filter
    if search:
        search_pattern = f"%{search}%"
        search_filter = or_(
            User.email.ilike(search_pattern),
            User.username.ilike(search_pattern),
            User.full_name.ilike(search_pattern)
        )
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)
        
    # Role filtering
    if role:
        users_with_role = enforcer.get_users_for_role(role)
        if users_with_role:
            query = query.where(User.id.in_(users_with_role))
            count_query = count_query.where(User.id.in_(users_with_role))
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
    
    return {
        "items": [user_to_response(user, enforcer) for user in users],
        "total": total,
        "skip": skip,
        "limit": limit
    }

@router.post("/", response_model=UserResponse)
async def create_user(
    user_in: UserCreate,
    current_user: User = Depends(is_allowed("users:create")),
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
    
    # Generate username from email
    username = user_in.email.split("@")[0]
    
    user = User(
        email=user_in.email,
        username=username,
        hashed_password=get_password_hash(user_in.password),
        full_name=user_in.full_name,
        is_active=True
    )
    
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    # User is created without roles. Roles will be assigned via Groups.
    
    return user_to_response(user, enforcer)

@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    user_in: UserAdminUpdate,
    current_user: User = Depends(is_allowed("users:update")),
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
    return user_to_response(user, enforcer)

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: str,
    current_user: User = Depends(is_allowed("users:delete")),
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
        
    # Remove all Casbin policies for this user
    enforcer.delete_user(str(user.id))
        
    await db.delete(user)
    await db.commit()
