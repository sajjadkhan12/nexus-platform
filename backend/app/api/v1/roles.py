from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.api.deps import get_current_active_superuser, is_allowed, get_db
from app.core.casbin import get_enforcer
from casbin import Enforcer
from app.schemas.rbac import RoleCreate, RoleUpdate, RoleResponse, PermissionResponse
from app.models.rbac import Role
from uuid import uuid4, UUID
from datetime import datetime

router = APIRouter(prefix="/roles", tags=["roles"])

@router.get("/")
async def list_roles(
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    enforcer: Enforcer = Depends(get_enforcer),
    current_user = Depends(is_allowed("roles:list"))
):
    """
    List all roles from DB and their permissions from Casbin with pagination.
    """
    from sqlalchemy import func
    
    # Get total count
    count_result = await db.execute(select(func.count(Role.id)))
    total = count_result.scalar() or 0
    
    # Fetch roles with pagination
    result = await db.execute(select(Role).offset(skip).limit(limit))
    roles_db = result.scalars().all()
    
    response = []
    for role in roles_db:
        # Get permissions for this role from Casbin
        # p, role_name, obj, act
        role_policies = enforcer.get_filtered_policy(0, role.name)
        permissions = []
        for policy in role_policies:
            if len(policy) >= 3:
                # Reconstruct permission slug from obj:act
                perm_slug = f"{policy[1]}:{policy[2]}"
                permissions.append(PermissionResponse(
                    id=uuid4(), # Generate random ID as permissions aren't in DB
                    slug=perm_slug,
                    description=None,
                    created_at=datetime.now()
                ))
        
        response.append(RoleResponse(
            id=role.id,
            name=role.name,
            description=role.description,
            created_at=role.created_at,
            permissions=permissions
        ))
    
    return {
        "items": response,
        "total": total,
        "skip": skip,
        "limit": limit
    }

@router.post("/", response_model=RoleResponse)
async def create_role(
    role_in: RoleCreate,
    db: AsyncSession = Depends(get_db),
    enforcer: Enforcer = Depends(get_enforcer),
    current_user = Depends(is_allowed("roles:create"))
):
    """
    Create a new role in DB and Casbin.
    """
    # Check if role exists in DB
    result = await db.execute(select(Role).where(Role.name == role_in.name))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Role already exists")
    
    # Create in DB
    role = Role(name=role_in.name, description=role_in.description)
    db.add(role)
    await db.commit()
    await db.refresh(role)
    
    # Add permissions in Casbin
    if role_in.permissions:
        for perm_slug in role_in.permissions:
            parts = perm_slug.split(":")
            if len(parts) >= 2:
                obj = parts[0]
                act = ":".join(parts[1:])
                enforcer.add_policy(role.name, obj, act)
    
    # Construct response
    permissions = []
    for perm_slug in role_in.permissions:
        permissions.append(PermissionResponse(
            id=uuid4(),
            slug=perm_slug,
            created_at=datetime.now()
        ))

    return RoleResponse(
        id=role.id,
        name=role.name,
        description=role.description,
        created_at=role.created_at,
        permissions=permissions
    )

@router.put("/{role_id}", response_model=RoleResponse)
async def update_role(
    role_id: UUID,
    role_in: RoleUpdate,
    db: AsyncSession = Depends(get_db),
    enforcer: Enforcer = Depends(get_enforcer),
    current_user = Depends(is_allowed("roles:update"))
):
    """
    Update a role in DB and Casbin.
    """
    result = await db.execute(select(Role).where(Role.id == role_id))
    role = result.scalar_one_or_none()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    
    old_name = role.name
    
    # Update DB
    if role_in.name:
        role.name = role_in.name
    if role_in.description:
        role.description = role_in.description
        
    await db.commit()
    await db.refresh(role)
    
    # Update Casbin
    # If name changed, we have a problem with existing policies.
    # For now, assume name doesn't change or we need to migrate policies.
    # But permissions might change.
    
    if role_in.permissions is not None:
        # Remove old permissions
        enforcer.remove_filtered_policy(0, old_name)
        
        # Add new permissions
        for perm_slug in role_in.permissions:
            parts = perm_slug.split(":")
            if len(parts) >= 2:
                obj = parts[0]
                act = ":".join(parts[1:])
                enforcer.add_policy(role.name, obj, act)
                
    return await get_role(role.id, db, enforcer, current_user)

@router.get("/{role_id}", response_model=RoleResponse)
async def get_role(
    role_id: UUID,
    db: AsyncSession = Depends(get_db),
    enforcer: Enforcer = Depends(get_enforcer),
    current_user = Depends(is_allowed("roles:read"))
):
    result = await db.execute(select(Role).where(Role.id == role_id))
    role = result.scalar_one_or_none()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
        
    role_policies = enforcer.get_filtered_policy(0, role.name)
    permissions = []
    for policy in role_policies:
        if len(policy) >= 3:
            perm_slug = f"{policy[1]}:{policy[2]}"
            permissions.append(PermissionResponse(
                id=uuid4(),
                slug=perm_slug,
                created_at=datetime.now()
            ))
            
    return RoleResponse(
        id=role.id,
        name=role.name,
        description=role.description,
        created_at=role.created_at,
        permissions=permissions
    )

@router.delete("/{role_id}")
async def delete_role(
    role_id: UUID,
    db: AsyncSession = Depends(get_db),
    enforcer: Enforcer = Depends(get_enforcer),
    current_user = Depends(is_allowed("roles:delete"))
):
    """
    Delete a role from DB and Casbin.
    """
    result = await db.execute(select(Role).where(Role.id == role_id))
    role = result.scalar_one_or_none()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    
    # Remove from Casbin
    enforcer.remove_filtered_policy(0, role.name)
    # Remove grouping policies (where role is used)
    enforcer.remove_filtered_grouping_policy(1, role.name)
    
    await db.delete(role)
    await db.commit()
    
    return {"message": "Role deleted successfully"}
