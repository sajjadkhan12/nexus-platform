from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List
import shutil
import os
from pathlib import Path
from app.database import get_db
from app.api.deps import get_current_user, get_current_active_superuser, is_allowed
from app.models.rbac import User
from app.schemas.user import UserResponse, UserUpdate, UserAdminUpdate, UserPasswordUpdate, UserCreate
from app.core.security import get_password_hash, verify_password
from app.core.casbin import get_enforcer
from casbin import Enforcer

router = APIRouter(prefix="/users", tags=["users"])

def user_to_response(user: User, enforcer: Enforcer) -> UserResponse:
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
    enforcer: Enforcer = Depends(get_enforcer)
):
    return user_to_response(current_user, enforcer)


@router.get("/stats")
async def get_admin_stats(
    current_user: User = Depends(is_allowed("users:list")),
    db: AsyncSession = Depends(get_db),
    enforcer: Enforcer = Depends(get_enforcer)
):
    """Get system statistics for admin dashboard"""
    from sqlalchemy import func
    from app.models.rbac import Group
    
    # Count users
    total_users = await db.scalar(select(func.count(User.id)))
    active_users = await db.scalar(select(func.count(User.id)).where(User.is_active == True))
    
    # Count groups from database
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
    enforcer: Enforcer = Depends(get_enforcer)
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
    enforcer: Enforcer = Depends(get_enforcer)
):
    # Create static/avatars directory if it doesn't exist
    avatars_dir = Path("static/avatars")
    avatars_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate unique filename
    file_extension = file.filename.split(".")[-1] if "." in file.filename else "jpg"
    filename = f"{current_user.id}.{file_extension}"
    file_path = avatars_dir / filename
    
    # Save file
    with file_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
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

@router.get("/", response_model=List[UserResponse])
async def list_users(
    skip: int = 0,
    limit: int = 100,
    search: str = None,
    role: str = None,
    current_user: User = Depends(is_allowed("users:list")),
    db: AsyncSession = Depends(get_db),
    enforcer: Enforcer = Depends(get_enforcer)
):
    query = select(User).offset(skip).limit(limit)
    
    if search:
        # Case-insensitive search across email, username, and full_name
        search_pattern = f"%{search}%"
        query = query.where(
            (User.email.ilike(search_pattern)) | 
            (User.username.ilike(search_pattern)) | 
            (User.full_name.ilike(search_pattern))
        )
        
    # Role filtering is harder now since it's not in the User model
    # We would need to get all users with that role from Casbin and then filter the SQL query
    # For now, let's ignore role filtering or implement it if critical
    if role:
        # Get users with role from Casbin
        users_with_role = enforcer.get_users_for_role(role)
        # users_with_role is list of user_ids (strings)
        if users_with_role:
             # Convert to UUIDs if needed, but SQL IN clause handles strings usually
             query = query.where(User.id.in_(users_with_role))
        else:
             # No users with this role, return empty
             return []
        
    result = await db.execute(query)
    users = result.scalars().all()
    return [user_to_response(user, enforcer) for user in users]

@router.post("/", response_model=UserResponse)
async def create_user(
    user_in: UserCreate,
    current_user: User = Depends(is_allowed("users:create")),
    db: AsyncSession = Depends(get_db),
    enforcer: Enforcer = Depends(get_enforcer)
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
    enforcer: Enforcer = Depends(get_enforcer)
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
    enforcer: Enforcer = Depends(get_enforcer)
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
