from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List
from app.database import get_db
from app.api.deps import get_current_user, get_current_active_superuser, is_allowed
from app.models.rbac import Group, User, Role
from app.core.rbac import Permission
from app.schemas.group import GroupCreate, GroupUpdate, GroupResponse

router = APIRouter(prefix="/groups", tags=["groups"])

@router.post("/", response_model=GroupResponse)
async def create_group(
    group: GroupCreate,
    current_user: User = Depends(is_allowed(Permission.ROLE_MANAGE)),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Group).where(Group.name == group.name))
    if result.scalars().first():
        raise HTTPException(status_code=400, detail="Group already exists")
    
    new_group = Group(**group.dict())
    db.add(new_group)
    await db.commit()
    await db.refresh(new_group)
    return new_group

@router.get("/", response_model=List[GroupResponse])
async def list_groups(
    current_user: User = Depends(is_allowed(Permission.USER_READ_ALL)),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Group))
    return result.scalars().all()

@router.get("/{group_id}", response_model=GroupResponse)
async def get_group(
    group_id: str,
    current_user: User = Depends(is_allowed(Permission.USER_READ_ALL)),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Group).where(Group.id == group_id))
    group = result.scalars().first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    return group

@router.put("/{group_id}", response_model=GroupResponse)
async def update_group(
    group_id: str,
    group_update: GroupUpdate,
    current_user: User = Depends(is_allowed(Permission.ROLE_MANAGE)),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Group).where(Group.id == group_id))
    group = result.scalars().first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    
    for key, value in group_update.dict(exclude_unset=True).items():
        setattr(group, key, value)
    
    await db.commit()
    await db.refresh(group)
    return group

@router.delete("/{group_id}")
async def delete_group(
    group_id: str,
    current_user: User = Depends(is_allowed(Permission.ROLE_MANAGE)),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Group).where(Group.id == group_id))
    group = result.scalars().first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    
    await db.delete(group)
    await db.commit()
    return {"message": "Group deleted successfully"}

@router.post("/{group_id}/users/{user_id}")
async def add_user_to_group(
    group_id: str,
    user_id: str,
    current_user: User = Depends(is_allowed(Permission.ROLE_MANAGE)),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Group).where(Group.id == group_id))
    group = result.scalars().first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
        
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    if user in group.users:
        raise HTTPException(status_code=400, detail="User already in group")
        
    group.users.append(user)
    await db.commit()
    return {"message": "User added to group"}

@router.delete("/{group_id}/users/{user_id}")
async def remove_user_from_group(
    group_id: str,
    user_id: str,
    current_user: User = Depends(is_allowed(Permission.ROLE_MANAGE)),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Group).where(Group.id == group_id))
    group = result.scalars().first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
        
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    if user not in group.users:
        raise HTTPException(status_code=400, detail="User not in group")
        
    group.users.remove(user)
    await db.commit()
    return {"message": "User removed from group"}

@router.post("/{group_id}/roles/{role_id}")
async def add_role_to_group(
    group_id: str,
    role_id: str,
    current_user: User = Depends(is_allowed(Permission.ROLE_MANAGE)),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Group).where(Group.id == group_id))
    group = result.scalars().first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
        
    result = await db.execute(select(Role).where(Role.id == role_id))
    role = result.scalars().first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
        
    if role in group.roles:
        raise HTTPException(status_code=400, detail="Role already assigned to group")
        
    group.roles.append(role)
    await db.commit()
    return {"message": f"Role {role.name} added to group"}

@router.delete("/{group_id}/roles/{role_id}")
async def remove_role_from_group(
    group_id: str,
    role_id: str,
    current_user: User = Depends(is_allowed(Permission.ROLE_MANAGE)),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Group).where(Group.id == group_id))
    group = result.scalars().first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
        
    result = await db.execute(select(Role).where(Role.id == role_id))
    role = result.scalars().first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
        
    if role not in group.roles:
        raise HTTPException(status_code=400, detail="Role not assigned to group")
        
    group.roles.remove(role)
    await db.commit()
    return {"message": f"Role {role.name} removed from group"}
