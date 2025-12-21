from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Dict
from app.api.deps import get_db, is_allowed, OrgAwareEnforcer, get_org_aware_enforcer
from app.models.rbac import Group, Role, User
from app.schemas.rbac import GroupCreate, GroupUpdate, GroupResponse, RoleResponse
from app.logger import logger
from uuid import UUID

router = APIRouter(prefix="/groups", tags=["groups"])

async def get_group_members(group_name: str, enforcer: OrgAwareEnforcer, db: AsyncSession) -> List[dict]:
    """
    Helper function to get group members (users) from Casbin and database.
    Returns list of user dicts with id, username, full_name, email.
    """
    members = enforcer.get_filtered_grouping_policy(1, group_name)
    user_ids = [m[0] for m in members]
    
    users = []
    if user_ids:
        try:
            u_ids = [UUID(uid) for uid in user_ids if uid.replace('-', '').isalnum()]
            if u_ids:
                u_res = await db.execute(select(User).where(User.id.in_(u_ids)))
                users_db = u_res.scalars().all()
                users = [{"id": u.id, "username": u.username, "full_name": u.full_name, "email": u.email} for u in users_db]
        except ValueError as e:
            logger.warning(f"Invalid UUID in group members for group {group_name}: {e}")
            pass  # Ignore invalid UUIDs but log the issue
    
    return users

async def get_group_roles(group_name: str, enforcer: OrgAwareEnforcer, db: AsyncSession) -> List[RoleResponse]:
    """
    Helper function to get group roles from Casbin and database.
    Returns list of RoleResponse objects.
    """
    role_policies = enforcer.get_filtered_grouping_policy(0, group_name)
    role_names = [r[1] for r in role_policies]
    
    roles = []
    if role_names:
        r_res = await db.execute(select(Role).where(Role.name.in_(role_names)))
        roles_db = r_res.scalars().all()
        roles = [RoleResponse.model_validate(r) for r in roles_db]
    
    return roles

@router.get("/")
async def list_groups(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of records to return"),
    db: AsyncSession = Depends(get_db),
    enforcer: OrgAwareEnforcer = Depends(get_org_aware_enforcer),
    current_user = Depends(is_allowed("groups:list"))
):
    from sqlalchemy import func
    
    # Get total count
    # Note: Groups are managed per-organization via Casbin domains
    count_result = await db.execute(select(func.count(Group.id)))
    total = count_result.scalar() or 0
    
    # Fetch groups from DB with pagination
    # Note: Groups are managed per-organization via Casbin domains
    result = await db.execute(select(Group).offset(skip).limit(limit))
    groups = result.scalars().all()
    
    response = []
    for group in groups:
        # Use helper functions to get members and roles
        users = await get_group_members(group.name, enforcer, db)
        roles = await get_group_roles(group.name, enforcer, db)

        response.append(GroupResponse(
            id=group.id,
            name=group.name,
            description=group.description,
            created_at=group.created_at,
            users=users,
            roles=roles
        ))
    
    return {
        "items": response,
        "total": total,
        "skip": skip,
        "limit": limit
    }

@router.post("/", response_model=GroupResponse)
async def create_group(
    group_in: GroupCreate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(is_allowed("groups:create"))
):
    # Check if exists
    # Note: Group isolation is handled by Casbin domains
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
    enforcer: OrgAwareEnforcer = Depends(get_org_aware_enforcer),
    current_user = Depends(is_allowed("groups:read"))
):
    result = await db.execute(select(Group).where(Group.id == group_id))
    group = result.scalar_one_or_none()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
        
    # Use helper functions to get members and roles
    users = await get_group_members(group.name, enforcer, db)
    roles = await get_group_roles(group.name, enforcer, db)
        
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
    enforcer: OrgAwareEnforcer = Depends(get_org_aware_enforcer),
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
        # Get all policies where group name appears
        # 1. Policies where group is object: g(user_id, old_name) - users belong to group
        user_policies = enforcer.get_filtered_grouping_policy(1, old_name)
        for user_id, _ in user_policies:
            # Remove old policy and add new one
            enforcer.remove_grouping_policy(user_id, old_name)
            enforcer.add_grouping_policy(user_id, group_in.name)
        
        # 2. Policies where group is subject: g(old_name, role_name) - group has role
        role_policies = enforcer.get_filtered_grouping_policy(0, old_name)
        for _, role_name in role_policies:
            # Remove old policy and add new one
            enforcer.remove_grouping_policy(old_name, role_name)
            enforcer.add_grouping_policy(group_in.name, role_name)
        
        # Save policies to persist changes
        enforcer.save_policy()
        
    return await get_group(group_id, db, enforcer, current_user)

@router.delete("/{group_id}")
async def delete_group(
    group_id: UUID,
    db: AsyncSession = Depends(get_db),
    enforcer: OrgAwareEnforcer = Depends(get_org_aware_enforcer),
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
    enforcer: OrgAwareEnforcer = Depends(get_org_aware_enforcer),
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
    enforcer: OrgAwareEnforcer = Depends(get_org_aware_enforcer),
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
    enforcer: OrgAwareEnforcer = Depends(get_org_aware_enforcer),
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
    enforcer: OrgAwareEnforcer = Depends(get_org_aware_enforcer),
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
