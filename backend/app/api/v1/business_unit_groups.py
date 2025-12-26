"""Business Unit Groups API endpoints"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy import func
from typing import List
import uuid

from app.database import get_db
from app.api.deps import get_current_user, is_allowed_bu, get_active_business_unit, is_platform_admin
from app.models.rbac import User
from app.models.business_unit import BusinessUnit, BusinessUnitGroup, BusinessUnitGroupMember, BusinessUnitMember
from app.models.rbac import Role
from app.schemas.business_unit import (
    BusinessUnitGroupCreate, BusinessUnitGroupUpdate, BusinessUnitGroupResponse,
    BusinessUnitGroupMemberAdd, BusinessUnitGroupMemberResponse
)
from app.logger import logger

router = APIRouter(prefix="/business-units/{business_unit_id}/groups", tags=["Business Unit Groups"])


@router.get("/", response_model=List[BusinessUnitGroupResponse])
async def list_business_unit_groups(
    business_unit_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List all groups in a business unit"""
    # Verify user has access to this business unit
    membership_result = await db.execute(
        select(BusinessUnitMember)
        .options(selectinload(BusinessUnitMember.role))
        .where(
            BusinessUnitMember.business_unit_id == business_unit_id,
            BusinessUnitMember.user_id == current_user.id
        )
    )
    membership = membership_result.scalar_one_or_none()
    
    # Check if user is admin
    from app.core.casbin import get_enforcer
    from app.core.organization import get_user_organization, get_organization_domain
    enforcer = get_enforcer()
    organization = await get_user_organization(current_user, db)
    org_domain = get_organization_domain(organization)
    is_admin = await is_platform_admin(current_user, db, enforcer)
    
    if not membership and not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this business unit"
        )
    
    # Get all groups in this business unit
    result = await db.execute(
        select(BusinessUnitGroup)
        .options(selectinload(BusinessUnitGroup.role))
        .where(BusinessUnitGroup.business_unit_id == business_unit_id)
    )
    groups = result.scalars().all()
    
    # Get member count for each group
    response_list = []
    for group in groups:
        member_count_result = await db.execute(
            select(func.count(BusinessUnitGroupMember.id))
            .where(BusinessUnitGroupMember.group_id == group.id)
        )
        member_count = member_count_result.scalar_one()
        
        response_list.append(BusinessUnitGroupResponse(
            id=group.id,
            business_unit_id=group.business_unit_id,
            name=group.name,
            description=group.description,
            role_id=group.role_id,
            role_name=group.role.name if group.role else None,
            member_count=member_count,
            created_at=group.created_at,
            updated_at=group.updated_at
        ))
    
    return response_list


@router.post("/", response_model=BusinessUnitGroupResponse, status_code=status.HTTP_201_CREATED)
async def create_business_unit_group(
    business_unit_id: uuid.UUID,
    group_data: BusinessUnitGroupCreate,
    current_user: User = Depends(is_allowed_bu("business_unit:business_units:manage_members")),
    db: AsyncSession = Depends(get_db),
    active_bu_id: uuid.UUID = Depends(get_active_business_unit)
):
    """Create a new group in a business unit (owner or admin only)"""
    # Verify business unit matches active BU
    if active_bu_id != business_unit_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Business unit ID in path must match active business unit"
        )
    
    # Verify business unit exists
    bu_result = await db.execute(
        select(BusinessUnit).where(BusinessUnit.id == business_unit_id)
    )
    bu = bu_result.scalar_one_or_none()
    if not bu:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Business unit not found"
        )
    
    # Verify role exists and is not a platform role
    role_result = await db.execute(
        select(Role).where(Role.id == group_data.role_id)
    )
    role = role_result.scalar_one_or_none()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Role with ID {group_data.role_id} not found"
        )
    if role.is_platform_role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot assign platform roles to business unit groups"
        )
    
    # Check if group name already exists in this BU
    existing_result = await db.execute(
        select(BusinessUnitGroup).where(
            BusinessUnitGroup.business_unit_id == business_unit_id,
            BusinessUnitGroup.name == group_data.name
        )
    )
    if existing_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Group with name '{group_data.name}' already exists in this business unit"
        )
    
    # Create group
    new_group = BusinessUnitGroup(
        business_unit_id=business_unit_id,
        name=group_data.name,
        description=group_data.description,
        role_id=group_data.role_id
    )
    db.add(new_group)
    await db.commit()
    await db.refresh(new_group, ["role"])
    
    logger.info(f"Business unit group '{new_group.name}' created in BU {business_unit_id} by {current_user.email}")
    
    return BusinessUnitGroupResponse(
        id=new_group.id,
        business_unit_id=new_group.business_unit_id,
        name=new_group.name,
        description=new_group.description,
        role_id=new_group.role_id,
        role_name=new_group.role.name if new_group.role else None,
        member_count=0,
        created_at=new_group.created_at,
        updated_at=new_group.updated_at
    )


@router.get("/{group_id}", response_model=BusinessUnitGroupResponse)
async def get_business_unit_group(
    business_unit_id: uuid.UUID,
    group_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific group in a business unit"""
    # Verify user has access to this business unit
    membership_result = await db.execute(
        select(BusinessUnitMember).where(
            BusinessUnitMember.business_unit_id == business_unit_id,
            BusinessUnitMember.user_id == current_user.id
        )
    )
    membership = membership_result.scalar_one_or_none()
    
    from app.core.casbin import get_enforcer
    from app.core.organization import get_user_organization, get_organization_domain
    enforcer = get_enforcer()
    organization = await get_user_organization(current_user, db)
    org_domain = get_organization_domain(organization)
    is_admin = await is_platform_admin(current_user, db, enforcer)
    
    if not membership and not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this business unit"
        )
    
    # Get group
    result = await db.execute(
        select(BusinessUnitGroup)
        .options(selectinload(BusinessUnitGroup.role))
        .where(
            BusinessUnitGroup.id == group_id,
            BusinessUnitGroup.business_unit_id == business_unit_id
        )
    )
    group = result.scalar_one_or_none()
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found in this business unit"
        )
    
    # Get member count
    member_count_result = await db.execute(
        select(func.count(BusinessUnitGroupMember.id))
        .where(BusinessUnitGroupMember.group_id == group.id)
    )
    member_count = member_count_result.scalar_one()
    
    return BusinessUnitGroupResponse(
        id=group.id,
        business_unit_id=group.business_unit_id,
        name=group.name,
        description=group.description,
        role_id=group.role_id,
        role_name=group.role.name if group.role else None,
        member_count=member_count,
        created_at=group.created_at,
        updated_at=group.updated_at
    )


@router.put("/{group_id}", response_model=BusinessUnitGroupResponse)
async def update_business_unit_group(
    business_unit_id: uuid.UUID,
    group_id: uuid.UUID,
    group_data: BusinessUnitGroupUpdate,
    current_user: User = Depends(is_allowed_bu("business_unit:business_units:manage_members")),
    db: AsyncSession = Depends(get_db),
    active_bu_id: uuid.UUID = Depends(get_active_business_unit)
):
    """Update a group in a business unit (owner or admin only)"""
    # Verify business unit matches active BU
    if active_bu_id != business_unit_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Business unit ID in path must match active business unit"
        )
    
    # Get group
    result = await db.execute(
        select(BusinessUnitGroup).where(
            BusinessUnitGroup.id == group_id,
            BusinessUnitGroup.business_unit_id == business_unit_id
        )
    )
    group = result.scalar_one_or_none()
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found in this business unit"
        )
    
    # Update fields
    if group_data.name is not None:
        # Check if new name conflicts with existing group
        if group_data.name != group.name:
            existing_result = await db.execute(
                select(BusinessUnitGroup).where(
                    BusinessUnitGroup.business_unit_id == business_unit_id,
                    BusinessUnitGroup.name == group_data.name
                )
            )
            if existing_result.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Group with name '{group_data.name}' already exists in this business unit"
                )
        group.name = group_data.name
    
    if group_data.description is not None:
        group.description = group_data.description
    
    if group_data.role_id is not None:
        # Verify role exists and is not a platform role
        role_result = await db.execute(
            select(Role).where(Role.id == group_data.role_id)
        )
        role = role_result.scalar_one_or_none()
        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Role with ID {group_data.role_id} not found"
            )
        if role.is_platform_role:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot assign platform roles to business unit groups"
            )
        group.role_id = group_data.role_id
    
    await db.commit()
    await db.refresh(group, ["role"])
    
    # Get member count
    member_count_result = await db.execute(
        select(func.count(BusinessUnitGroupMember.id))
        .where(BusinessUnitGroupMember.group_id == group.id)
    )
    member_count = member_count_result.scalar_one()
    
    logger.info(f"Business unit group '{group.name}' updated in BU {business_unit_id} by {current_user.email}")
    
    return BusinessUnitGroupResponse(
        id=group.id,
        business_unit_id=group.business_unit_id,
        name=group.name,
        description=group.description,
        role_id=group.role_id,
        role_name=group.role.name if group.role else None,
        member_count=member_count,
        created_at=group.created_at,
        updated_at=group.updated_at
    )


@router.delete("/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_business_unit_group(
    business_unit_id: uuid.UUID,
    group_id: uuid.UUID,
    current_user: User = Depends(is_allowed_bu("business_unit:business_units:manage_members")),
    db: AsyncSession = Depends(get_db),
    active_bu_id: uuid.UUID = Depends(get_active_business_unit)
):
    """Delete a group from a business unit (owner or admin only)"""
    # Verify business unit matches active BU
    if active_bu_id != business_unit_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Business unit ID in path must match active business unit"
        )
    
    # Get group
    result = await db.execute(
        select(BusinessUnitGroup).where(
            BusinessUnitGroup.id == group_id,
            BusinessUnitGroup.business_unit_id == business_unit_id
        )
    )
    group = result.scalar_one_or_none()
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found in this business unit"
        )
    
    await db.delete(group)
    await db.commit()
    
    logger.info(f"Business unit group '{group.name}' deleted from BU {business_unit_id} by {current_user.email}")
    
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{group_id}/members", response_model=List[BusinessUnitGroupMemberResponse])
async def list_group_members(
    business_unit_id: uuid.UUID,
    group_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List members of a group in a business unit"""
    # Verify user has access to this business unit
    membership_result = await db.execute(
        select(BusinessUnitMember).where(
            BusinessUnitMember.business_unit_id == business_unit_id,
            BusinessUnitMember.user_id == current_user.id
        )
    )
    membership = membership_result.scalar_one_or_none()
    
    from app.core.casbin import get_enforcer
    from app.core.organization import get_user_organization, get_organization_domain
    enforcer = get_enforcer()
    organization = await get_user_organization(current_user, db)
    org_domain = get_organization_domain(organization)
    is_admin = await is_platform_admin(current_user, db, enforcer)
    
    if not membership and not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this business unit"
        )
    
    # Verify group exists in this BU
    group_result = await db.execute(
        select(BusinessUnitGroup).where(
            BusinessUnitGroup.id == group_id,
            BusinessUnitGroup.business_unit_id == business_unit_id
        )
    )
    if not group_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found in this business unit"
        )
    
    # Get all members
    result = await db.execute(
        select(BusinessUnitGroupMember, User)
        .join(User, BusinessUnitGroupMember.user_id == User.id)
        .where(BusinessUnitGroupMember.group_id == group_id)
        .options(selectinload(BusinessUnitGroupMember.user))
    )
    members = result.all()
    
    return [
        BusinessUnitGroupMemberResponse(
            id=member.id,
            group_id=member.group_id,
            user_id=member.user_id,
            user_email=user.email,
            user_name=user.full_name or user.username,
            created_at=member.created_at
        )
        for member, user in members
    ]


@router.post("/{group_id}/members", response_model=BusinessUnitGroupMemberResponse, status_code=status.HTTP_201_CREATED)
async def add_group_member(
    business_unit_id: uuid.UUID,
    group_id: uuid.UUID,
    member_data: BusinessUnitGroupMemberAdd,
    current_user: User = Depends(is_allowed_bu("business_unit:business_units:manage_members")),
    db: AsyncSession = Depends(get_db),
    active_bu_id: uuid.UUID = Depends(get_active_business_unit)
):
    """Add a member to a group in a business unit (owner or admin only)"""
    # Verify business unit matches active BU
    if active_bu_id != business_unit_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Business unit ID in path must match active business unit"
        )
    
    # Verify group exists in this BU
    group_result = await db.execute(
        select(BusinessUnitGroup).where(
            BusinessUnitGroup.id == group_id,
            BusinessUnitGroup.business_unit_id == business_unit_id
        )
    )
    group = group_result.scalar_one_or_none()
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found in this business unit"
        )
    
    # Find user by email
    user_result = await db.execute(
        select(User).where(User.email == member_data.user_email)
    )
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with email {member_data.user_email} not found"
        )
    
    # Verify user is a member of the business unit
    bu_member_result = await db.execute(
        select(BusinessUnitMember).where(
            BusinessUnitMember.business_unit_id == business_unit_id,
            BusinessUnitMember.user_id == user.id
        )
    )
    if not bu_member_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must be a member of the business unit before being added to a group"
        )
    
    # Check if user is already in the group
    existing_result = await db.execute(
        select(BusinessUnitGroupMember).where(
            BusinessUnitGroupMember.group_id == group_id,
            BusinessUnitGroupMember.user_id == user.id
        )
    )
    if existing_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already a member of this group"
        )
    
    # Add member
    new_member = BusinessUnitGroupMember(
        group_id=group_id,
        user_id=user.id
    )
    db.add(new_member)
    await db.commit()
    await db.refresh(new_member, ["user"])
    
    logger.info(f"User {user.email} added to group {group.name} in BU {business_unit_id} by {current_user.email}")
    
    return BusinessUnitGroupMemberResponse(
        id=new_member.id,
        group_id=new_member.group_id,
        user_id=new_member.user_id,
        user_email=user.email,
        user_name=user.full_name or user.username,
        created_at=new_member.created_at
    )


@router.delete("/{group_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_group_member(
    business_unit_id: uuid.UUID,
    group_id: uuid.UUID,
    user_id: uuid.UUID,
    current_user: User = Depends(is_allowed_bu("business_unit:business_units:manage_members")),
    db: AsyncSession = Depends(get_db),
    active_bu_id: uuid.UUID = Depends(get_active_business_unit)
):
    """Remove a member from a group in a business unit (owner or admin only)"""
    # Verify business unit matches active BU
    if active_bu_id != business_unit_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Business unit ID in path must match active business unit"
        )
    
    # Verify group exists in this BU
    group_result = await db.execute(
        select(BusinessUnitGroup).where(
            BusinessUnitGroup.id == group_id,
            BusinessUnitGroup.business_unit_id == business_unit_id
        )
    )
    if not group_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found in this business unit"
        )
    
    # Find member to remove
    member_result = await db.execute(
        select(BusinessUnitGroupMember).where(
            BusinessUnitGroupMember.group_id == group_id,
            BusinessUnitGroupMember.user_id == user_id
        )
    )
    member = member_result.scalar_one_or_none()
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found in this group"
        )
    
    await db.delete(member)
    await db.commit()
    
    logger.info(f"User {user_id} removed from group {group_id} in BU {business_unit_id} by {current_user.email}")
    
    return Response(status_code=status.HTTP_204_NO_CONTENT)

