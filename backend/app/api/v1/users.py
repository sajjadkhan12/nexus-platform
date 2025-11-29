from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List
import shutil
import os
from pathlib import Path
from app.database import get_db
from app.api.deps import get_current_user, get_current_active_superuser, is_allowed
from app.models.rbac import User, Role
from app.core.rbac import Permission
from app.schemas.user import UserResponse, UserUpdate, UserAdminUpdate, UserPasswordUpdate, UserCreate
from app.core.security import get_password_hash, verify_password

router = APIRouter(prefix="/users", tags=["users"])

@router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: User = Depends(is_allowed(Permission.PROFILE_READ))):
    return current_user

@router.get("/me/debug")
async def debug_user_roles(current_user: User = Depends(get_current_user)):
    """Debug endpoint to check roles"""
    return {
        "email": current_user.email,
        "roles_count": len(current_user.roles),
        "roles": [{"id": str(r.id), "name": r.name} for r in current_user.roles],
        "permissions": [
            {"role": r.name, "perms": [p.slug for p in r.permissions]}
            for r in current_user.roles
        ]
    }

@router.get("/stats")
async def get_admin_stats(
    current_user: User = Depends(is_allowed(Permission.USERS_LIST)),
    db: AsyncSession = Depends(get_db)
):
    """Get system statistics for admin dashboard"""
    from sqlalchemy import func
    from app.models.rbac import Group, user_roles
    
    # Import func locally to avoid issues
    total_users = await db.scalar(select(func.count(User.id)))
    active_users = await db.scalar(select(func.count(User.id)).where(User.is_active == True))
    total_groups = await db.scalar(select(func.count(Group.id)))
    total_roles = await db.scalar(select(func.count(Role.id)))
    
    # Get role distribution
    role_dist_result = await db.execute(
        select(Role.name, func.count(user_roles.c.user_id).label('count'))
        .join(user_roles, Role.id == user_roles.c.role_id, isouter=True)
        .group_by(Role.name)
    )
    
    return {
        "total_users": total_users or 0,
        "active_users": active_users or 0,
        "inactive_users": (total_users or 0) - (active_users or 0),
        "total_groups": total_groups or 0,
        "total_roles": total_roles or 0,
        "role_distribution": [
            {"role": row[0], "count": row[1] or 0} 
            for row in role_dist_result
        ]
    }

@router.put("/me", response_model=UserResponse)
async def update_user_me(
    user_update: UserUpdate,
    current_user: User = Depends(is_allowed(Permission.PROFILE_UPDATE)),
    db: AsyncSession = Depends(get_db)
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
    return current_user

@router.post("/me/avatar", response_model=UserResponse)
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(is_allowed(Permission.PROFILE_UPDATE)),
    db: AsyncSession = Depends(get_db)
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
    
    return current_user

@router.put("/me/password")
async def change_password(
    password_update: UserPasswordUpdate,
    current_user: User = Depends(is_allowed(Permission.PROFILE_UPDATE)),
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
    current_user: User = Depends(is_allowed(Permission.USERS_LIST)),
    db: AsyncSession = Depends(get_db)
):
    query = select(User).offset(skip).limit(limit)
    
    if search:
        query = query.where(User.email.contains(search) | User.full_name.contains(search))
        
    if role:
        query = query.join(User.roles).where(Role.name == role)
        
    result = await db.execute(query)
    return result.scalars().all()

@router.post("/", response_model=UserResponse)
async def create_user(
    user_in: UserCreate,
    current_user: User = Depends(is_allowed(Permission.USERS_CREATE)),
    db: AsyncSession = Depends(get_db)
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
    
    # Check if username exists and append random string if needed
    # For simplicity, we'll just use the email prefix for now, 
    # but in a real app we might want to ensure uniqueness more robustly
    
    user = User(
        email=user_in.email,
        username=username,
        hashed_password=get_password_hash(user_in.password),
        full_name=user_in.full_name,
        is_active=True
    )
    
    # Assign default 'engineer' role
    result = await db.execute(select(Role).where(Role.name == "engineer"))
    default_role = result.scalars().first()
    if default_role:
        user.roles.append(default_role)
        
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user

@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    user_in: UserAdminUpdate,
    current_user: User = Depends(is_allowed(Permission.USERS_UPDATE)),
    db: AsyncSession = Depends(get_db)
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
        # Clear existing roles
        user.roles = []
        # Add new roles
        for role_name in user_in.roles:
            result = await db.execute(select(Role).where(Role.name == role_name))
            role = result.scalars().first()
            if role:
                user.roles.append(role)
                
    await db.commit()
    await db.refresh(user)
    return user

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: str,
    current_user: User = Depends(is_allowed(Permission.USERS_DELETE)),
    db: AsyncSession = Depends(get_db)
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
        
    await db.delete(user)
    await db.commit()
