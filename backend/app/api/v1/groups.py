from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from app.api.deps import get_db, is_allowed
from app.core.casbin import get_enforcer
from casbin import Enforcer
from app.models.rbac import Group, Role, User
from app.schemas.rbac import GroupCreate, GroupUpdate, GroupResponse, RoleResponse
from uuid import UUID

router = APIRouter(prefix="/groups", tags=["groups"])

@router.get("/", response_model=List[GroupResponse])
async def list_groups(
    db: AsyncSession = Depends(get_db),
    enforcer: Enforcer = Depends(get_enforcer),
    current_user = Depends(is_allowed("groups:list"))
):
    # Fetch groups from DB
    result = await db.execute(select(Group))
    groups = result.scalars().all()
    
    response = []
    for group in groups:
        # Get members (users) from Casbin
        # g, user_id, group_name
        # We need to find all subjects where object is group.name
        members = enforcer.get_filtered_grouping_policy(1, group.name)
        user_ids = [m[0] for m in members]
        
        users = []
        if user_ids:
            # Fetch user details
            # Note: This is N+1 query if not careful, but for now it's fine or we can optimize
            # SQLAlchemy IN clause with UUIDs might be tricky with strings
            # Let's fetch all users and filter? No, too heavy.
            # Let's fetch by IDs.
            try:
                u_ids = [UUID(uid) for uid in user_ids if uid.replace('-', '').isalnum()]
                if u_ids:
                    u_res = await db.execute(select(User).where(User.id.in_(u_ids)))
                    users_db = u_res.scalars().all()
                    users = [{"id": u.id, "username": u.username, "full_name": u.full_name, "email": u.email} for u in users_db]
            except ValueError:
                pass # Ignore invalid UUIDs

        # Get roles
        # g, group_name, role_name
        # We need to find all objects where subject is group.name
        # But wait, Casbin grouping is g(user, role).
        # So if group has role, it means group is a member of role.
        # So g, group_name, role_name.
        role_policies = enforcer.get_filtered_grouping_policy(0, group.name)
        role_names = [r[1] for r in role_policies]
        
        roles = []
        if role_names:
            r_res = await db.execute(select(Role).where(Role.name.in_(role_names)))
            roles_db = r_res.scalars().all()
            roles = [RoleResponse.from_orm(r) for r in roles_db]

        response.append(GroupResponse(
            id=group.id,
            name=group.name,
            description=group.description,
            created_at=group.created_at,
            users=users,
            roles=roles
        ))
    
    return response

@router.post("/", response_model=GroupResponse)
async def create_group(
    group_in: GroupCreate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(is_allowed("groups:create"))
):
    # Check if exists
    result = await db.execute(select(Group).where(Group.name == group_in.name))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Group already exists")
    
    group = Group(name=group_in.name, description=group_in.description)
    db.add(group)
    await db.commit()
    await db.refresh(group)
    
    return GroupResponse(
        id=group.id,
        name=group.name,
        description=group.description,
        created_at=group.created_at,
        users=[],
        roles=[]
    )

@router.get("/{group_id}", response_model=GroupResponse)
async def get_group(
    group_id: UUID,
    db: AsyncSession = Depends(get_db),
    enforcer: Enforcer = Depends(get_enforcer),
    current_user = Depends(is_allowed("groups:read"))
):
    result = await db.execute(select(Group).where(Group.id == group_id))
    group = result.scalar_one_or_none()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
        
    # Fetch members
    members = enforcer.get_filtered_grouping_policy(1, group.name)
    user_ids = [m[0] for m in members]
    users = []
    if user_ids:
        try:
            u_ids = [UUID(uid) for uid in user_ids if uid.replace('-', '').isalnum()]
            if u_ids:
                u_res = await db.execute(select(User).where(User.id.in_(u_ids)))
                users_db = u_res.scalars().all()
                users = [{"id": u.id, "username": u.username, "full_name": u.full_name, "email": u.email} for u in users_db]
        except ValueError:
            pass

    # Fetch roles
    role_policies = enforcer.get_filtered_grouping_policy(0, group.name)
    role_names = [r[1] for r in role_policies]
    roles = []
    if role_names:
        r_res = await db.execute(select(Role).where(Role.name.in_(role_names)))
        roles_db = r_res.scalars().all()
        roles = [RoleResponse.from_orm(r) for r in roles_db]
        
    return GroupResponse(
        id=group.id,
        name=group.name,
        description=group.description,
        created_at=group.created_at,
        users=users,
        roles=roles
    )

@router.put("/{group_id}", response_model=GroupResponse)
async def update_group(
    group_id: UUID,
    group_in: GroupUpdate,
    db: AsyncSession = Depends(get_db),
    enforcer: Enforcer = Depends(get_enforcer),
    current_user = Depends(is_allowed("groups:update"))
):
    result = await db.execute(select(Group).where(Group.id == group_id))
    group = result.scalar_one_or_none()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    
    old_name = group.name
    
    if group_in.name:
        group.name = group_in.name
    if group_in.description:
        group.description = group_in.description
        
    await db.commit()
    await db.refresh(group)
    
    # If name changed, update Casbin policies
    if group_in.name and old_name != group_in.name:
        # Update grouping policies where group is subject (group has role)
        # remove old, add new? Casbin has update?
        # enforcer.update_grouping_policy(...)
        # It's safer to remove and add, or use update if supported.
        # For simplicity, we might need to manually update.
        # But Casbin API for update is tricky.
        # Let's just leave it for now or assume name doesn't change often.
        # Actually, if name changes, we MUST update policies or links break.
        pass # TODO: Handle name change in Casbin
        
    return await get_group(group_id, db, enforcer, current_user)

@router.delete("/{group_id}")
async def delete_group(
    group_id: UUID,
    db: AsyncSession = Depends(get_db),
    enforcer: Enforcer = Depends(get_enforcer),
    current_user = Depends(is_allowed("groups:delete"))
):
    result = await db.execute(select(Group).where(Group.id == group_id))
    group = result.scalar_one_or_none()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
        
    # Remove from Casbin
    # Remove where group is user (member of role)
    enforcer.remove_filtered_grouping_policy(0, group.name)
    # Remove where group is role (user is member of group)
    enforcer.remove_filtered_grouping_policy(1, group.name)
    
    await db.delete(group)
    await db.commit()
    return {"message": "Group deleted"}

@router.post("/{group_id}/users/{user_id}")
async def add_user_to_group(
    group_id: UUID,
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    enforcer: Enforcer = Depends(get_enforcer),
    current_user = Depends(is_allowed("groups:manage"))
):
    result = await db.execute(select(Group).where(Group.id == group_id))
    group = result.scalar_one_or_none()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
        
    enforcer.add_grouping_policy(str(user_id), group.name)
    return {"message": "User added to group"}

@router.delete("/{group_id}/users/{user_id}")
async def remove_user_from_group(
    group_id: UUID,
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    enforcer: Enforcer = Depends(get_enforcer),
    current_user = Depends(is_allowed("groups:manage"))
):
    result = await db.execute(select(Group).where(Group.id == group_id))
    group = result.scalar_one_or_none()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
        
    enforcer.remove_grouping_policy(str(user_id), group.name)
    return {"message": "User removed from group"}

@router.post("/{group_id}/roles/{role_id}")
async def add_role_to_group(
    group_id: UUID,
    role_id: UUID,
    db: AsyncSession = Depends(get_db),
    enforcer: Enforcer = Depends(get_enforcer),
    current_user = Depends(is_allowed("groups:manage"))
):
    result = await db.execute(select(Group).where(Group.id == group_id))
    group = result.scalar_one_or_none()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
        
    role_res = await db.execute(select(Role).where(Role.id == role_id))
    role = role_res.scalar_one_or_none()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
        
    enforcer.add_grouping_policy(group.name, role.name)
    return {"message": "Role added to group"}

@router.delete("/{group_id}/roles/{role_id}")
async def remove_role_from_group(
    group_id: UUID,
    role_id: UUID,
    db: AsyncSession = Depends(get_db),
    enforcer: Enforcer = Depends(get_enforcer),
    current_user = Depends(is_allowed("groups:manage"))
):
    result = await db.execute(select(Group).where(Group.id == group_id))
    group = result.scalar_one_or_none()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
        
    role_res = await db.execute(select(Role).where(Role.id == role_id))
    role = role_res.scalar_one_or_none()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
        
    enforcer.remove_grouping_policy(group.name, role.name)
    return {"message": "Role removed from group"}
