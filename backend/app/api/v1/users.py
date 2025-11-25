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
from app.schemas.user import UserResponse, UserUpdate, UserAdminUpdate, UserPasswordUpdate
from app.core.security import get_password_hash, verify_password

router = APIRouter(prefix="/users", tags=["users"])

@router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: User = Depends(get_current_user)):
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
    current_user: User = Depends(is_allowed(Permission.USER_READ_ALL)),
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
    current_user: User = Depends(get_current_user),
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
    current_user: User = Depends(get_current_user),
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
    current_user: User = Depends(get_current_user),
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
    current_user: User = Depends(is_allowed(Permission.USER_READ_ALL)),
    db: AsyncSession = Depends(get_db)
):
    query = select(User).offset(skip).limit(limit)
    
    if search:
        query = query.where(User.email.contains(search) | User.full_name.contains(search))
        
    if role:
        query = query.join(User.roles).where(Role.name == role)
        
    result = await db.execute(query)
    return result.scalars().all()
