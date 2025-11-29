from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List
from app.database import get_db
from app.api.deps import get_current_active_superuser, is_allowed
from app.models.rbac import Role, Permission, role_permissions
from app.core.rbac import Permission
from app.schemas.rbac import RoleCreate, RoleUpdate, RoleResponse

router = APIRouter(prefix="/roles", tags=["roles"])

@router.post("/", response_model=RoleResponse)
async def create_role(
    role: RoleCreate,
    current_user = Depends(is_allowed(Permission.ROLES_CREATE)),
    db: AsyncSession = Depends(get_db)
):
    # Check if role exists
    result = await db.execute(select(Role).where(Role.name == role.name))
    if result.scalars().first():
        raise HTTPException(status_code=400, detail="Role already exists")
    
    new_role = Role(name=role.name, description=role.description)
    
    # Assign permissions
    if role.permissions:
        stmt = select(Permission).where(Permission.slug.in_(role.permissions))
        result = await db.execute(stmt)
        perms = result.scalars().all()
        if len(perms) != len(role.permissions):
            raise HTTPException(status_code=400, detail="One or more permissions not found")
        new_role.permissions = perms
        
    db.add(new_role)
    await db.commit()
    await db.refresh(new_role)
    return new_role

@router.get("/", response_model=List[RoleResponse])
async def list_roles(
    current_user = Depends(is_allowed(Permission.ROLES_LIST)),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Role))
    return result.scalars().all()

@router.put("/{role_id}", response_model=RoleResponse)
async def update_role(
    role_id: str,
    role_update: RoleUpdate,
    current_user = Depends(is_allowed(Permission.ROLES_UPDATE)),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Role).where(Role.id == role_id))
    role = result.scalars().first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
        
    if role_update.name:
        role.name = role_update.name
    if role_update.description:
        role.description = role_update.description
        
    if role_update.permissions is not None:
        stmt = select(Permission).where(Permission.slug.in_(role_update.permissions))
        result = await db.execute(stmt)
        perms = result.scalars().all()
        role.permissions = perms
        
    await db.commit()
    await db.refresh(role)
    return role

@router.delete("/{role_id}")
async def delete_role(
    role_id: str,
    current_user = Depends(is_allowed(Permission.ROLES_DELETE)),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Role).where(Role.id == role_id))
    role = result.scalars().first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
        
    await db.delete(role)
    await db.commit()
    return {"message": "Role deleted successfully"}
