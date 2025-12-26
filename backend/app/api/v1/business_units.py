"""Business Units API endpoints"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy import func
from typing import List, Optional
import uuid

from app.database import get_db
from app.api.deps import get_current_user, get_org_aware_enforcer, OrgAwareEnforcer, is_allowed_bu, get_active_business_unit, is_platform_admin, is_allowed
from app.models.rbac import User
from app.models.business_unit import BusinessUnit, BusinessUnitMember
from app.models.rbac import Role
from app.schemas.business_unit import (
    BusinessUnitCreate, BusinessUnitUpdate, BusinessUnitResponse,
    BusinessUnitMemberResponse, BusinessUnitMemberAdd
)
from app.logger import logger

router = APIRouter(prefix="/business-units", tags=["Business Units"])

@router.get("/", response_model=List[BusinessUnitResponse])
async def list_business_units(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List all business units the current user has access to.
    Also ensures existing owners have the necessary permissions.
    """
    # Grant permissions to existing owners who might not have them yet
    from app.core.casbin import get_enforcer
    from app.core.organization import get_user_organization, get_organization_domain
    organization = await get_user_organization(current_user, db)
    org_domain = get_organization_domain(organization)
    enforcer = get_enforcer()
    enforcer.set_org_domain(org_domain)  # Set org domain for the wrapper
    
    # Check if current user has business_units:manage_members permission in any business unit
    # This is permission-based, not role-name-based
    from app.api.deps import check_bu_permission
    
    # Get all business units where user is a member
    all_memberships_result = await db.execute(
        select(BusinessUnitMember)
        .options(selectinload(BusinessUnitMember.role))
        .where(BusinessUnitMember.user_id == current_user.id)
    )
    all_memberships = all_memberships_result.scalars().all()
    
    # Filter memberships where user has manage_members permission
    owner_memberships = []
    for membership in all_memberships:
        has_permission = await check_bu_permission(
            current_user,
            membership.business_unit_id,
            "business_unit:business_units:manage_members",
            db,
            enforcer,
            org_domain
        )
        if has_permission:
            owner_memberships.append(membership)
    
    # Grant permissions to existing members with manage_members permission
    if owner_memberships:
        # Get user's existing roles once (outside the loop)
        user_roles = enforcer.get_roles_for_user(str(current_user.id))
        roles_updated = False
        
        # Grant platform permissions to roles that have business_units:manage_members
        # This is permission-based, not role-name-based
        from app.core.permission_registry import parse_permission_slug
        platform_permissions = [
            "platform:roles:list",
            "platform:roles:read",
            "platform:users:list",
            "platform:users:read",
        ]
        
        # For each membership with manage_members permission, grant platform permissions to that role
        for membership in owner_memberships:
            if membership.role:
                role_name = membership.role.name
                for perm_slug in platform_permissions:
                    try:
                        obj, act = parse_permission_slug(perm_slug)
                        # Check if role already has this permission
                        existing = enforcer.get_filtered_policy(0, role_name, org_domain, obj, act)
                        if not existing:
                            enforcer.add_policy(role_name, org_domain, obj, act)
                            roles_updated = True
                            # Granted platform permission to role
                    except Exception as e:
                        logger.warning(f"Failed to add permission {perm_slug} to role {role_name}: {e}")
        
        for membership in owner_memberships:
            owner_role = f"business-unit-owner-{membership.business_unit_id}"
            # Check if user already has this role
            if not enforcer.has_grouping_policy(str(current_user.id), owner_role, org_domain):
                enforcer.add_grouping_policy(str(current_user.id), owner_role, org_domain)
                # Add permissions to the owner role
                from app.core.permission_registry import parse_permission_slug
                owner_permissions = [
                    "business_unit:business_units:update",
                    "business_unit:business_units:read",
                    "business_unit:business_units:manage_members",
                    "platform:users:list",  # Allow owners to list users when adding members
                    "platform:roles:list",  # Allow owners to list roles when adding members
                    "platform:roles:read",  # Allow owners to read role details
                ]
                for perm_slug in owner_permissions:
                    try:
                        obj, act = parse_permission_slug(perm_slug)
                        # Check if policy exists using get_filtered_policy
                        existing_policies = enforcer.get_filtered_policy(0, owner_role)
                        policy_exists = any(
                            len(p) >= 4 and p[0] == owner_role and p[1] == org_domain and p[2] == obj and p[3] == act
                            for p in existing_policies
                        )
                        if not policy_exists:
                            enforcer.add_policy(owner_role, org_domain, obj, act)
                    except Exception as e:
                        logger.warning(f"Failed to add permission {perm_slug} to owner role {owner_role}: {e}")
                roles_updated = True
                logger.info(f"Granted business unit owner permissions to {current_user.email} for business unit {membership.business_unit_id}")
        
        # Also grant platform:users:list permission directly to user's existing roles for immediate effect
        # This ensures owners can list users even if they don't have the business-unit-owner role yet
        from app.core.permission_registry import parse_permission_slug
        perm_slug = "platform:users:list"
        try:
            obj, act = parse_permission_slug(perm_slug)
            for role in user_roles:
                # Check if policy exists using get_filtered_policy
                existing_policies = enforcer.get_filtered_policy(0, role)
                policy_exists = any(
                    len(p) >= 4 and p[0] == role and p[1] == org_domain and p[2] == obj and p[3] == act
                    for p in existing_policies
                )
                if not policy_exists:
                    enforcer.add_policy(role, org_domain, obj, act)
                    roles_updated = True
            
            # Also grant permission directly to the user for immediate effect
            # This ensures the permission check works even if role-based checking has issues
            user_policies = enforcer.get_filtered_policy(0, str(current_user.id))
            user_policy_exists = any(
                len(p) >= 4 and p[0] == str(current_user.id) and p[1] == org_domain and p[2] == obj and p[3] == act
                for p in user_policies
            )
            if not user_policy_exists:
                enforcer.add_policy(str(current_user.id), org_domain, obj, act)
                roles_updated = True
        except Exception as e:
            logger.warning(f"Failed to add {perm_slug} permission: {e}")
        
        if roles_updated:
            enforcer.save_policy()
            # Reload policy to ensure changes take effect immediately
            enforcer.load_policy()
            logger.info(f"Granted platform:users:list permission to {current_user.email} (roles: {user_roles})")
    
    # Get all business units where user is a member
    result = await db.execute(
        select(BusinessUnit)
        .join(BusinessUnitMember)
        .where(
            BusinessUnitMember.user_id == current_user.id,
            BusinessUnit.is_active == True
        )
        .distinct()
    )
    business_units = result.scalars().all()
    
    # Also check if user is platform admin - admins can see all business units
    is_admin = await is_platform_admin(current_user, db, enforcer)
    
    if is_admin:
        # Admins can see all business units in their organization
        admin_result = await db.execute(
            select(BusinessUnit)
            .where(
                BusinessUnit.organization_id == current_user.organization_id,
                BusinessUnit.is_active == True
            )
        )
        admin_business_units = admin_result.scalars().all()
        # Combine and deduplicate
        all_business_units = {bu.id: bu for bu in business_units}
        for bu in admin_business_units:
            all_business_units[bu.id] = bu
        business_units = list(all_business_units.values())
    
    # Get user's role and member count for each business unit
    from sqlalchemy import func
    response_list = []
    for bu in business_units:
        member_result = await db.execute(
            select(BusinessUnitMember)
            .options(selectinload(BusinessUnitMember.role))
            .where(
                BusinessUnitMember.business_unit_id == bu.id,
                BusinessUnitMember.user_id == current_user.id
            )
        )
        membership = member_result.scalar_one_or_none()
        role = None
        if membership:
            # Get role name from relationship (now eagerly loaded)
            if membership.role:
                role = membership.role.name
            else:
                # Fallback: query role directly if relationship not loaded
                role_result = await db.execute(
                    select(Role).where(Role.id == membership.role_id)
                )
                role_obj = role_result.scalar_one_or_none()
                role = role_obj.name if role_obj else None
        if is_admin and not membership:
            role = "admin"  # Admins have admin role even if not explicitly members
        
        # Count total members in this business unit
        count_result = await db.execute(
            select(func.count(BusinessUnitMember.id)).where(
                BusinessUnitMember.business_unit_id == bu.id
            )
        )
        member_count = count_result.scalar() or 0
        
        # Check if user has manage_members permission for this business unit
        can_manage = False
        if membership:
            can_manage = await check_bu_permission(
                current_user,
                bu.id,
                "business_unit:business_units:manage_members",
                db,
                enforcer,
                org_domain
            )
        elif is_admin:
            can_manage = True  # Admins can manage all business units
        
        response_list.append(BusinessUnitResponse(
            id=bu.id,
            name=bu.name,
            slug=bu.slug,
            description=bu.description,
            organization_id=bu.organization_id,
            is_active=bu.is_active,
            created_at=bu.created_at,
            updated_at=bu.updated_at,
            role=role,
            member_count=member_count,
            can_manage_members=can_manage
        ))
    
    return response_list

@router.post("/", response_model=BusinessUnitResponse, status_code=status.HTTP_201_CREATED)
async def create_business_unit(
    business_unit: BusinessUnitCreate,
    current_user: User = Depends(is_allowed("platform:business_units:create")),
    db: AsyncSession = Depends(get_db)
):
    """Create a new business unit (super admin only)"""
    # Check if slug already exists in the same organization
    result = await db.execute(
        select(BusinessUnit).where(
            BusinessUnit.slug == business_unit.slug,
            BusinessUnit.organization_id == current_user.organization_id
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Business unit with slug '{business_unit.slug}' already exists in your organization"
        )
    
    # Create business unit
    new_bu = BusinessUnit(
        name=business_unit.name,
        slug=business_unit.slug,
        description=business_unit.description,
        organization_id=current_user.organization_id,
        is_active=True
    )
    db.add(new_bu)
    await db.commit()
    await db.refresh(new_bu)
    
    logger.info(f"Business unit '{new_bu.name}' created by {current_user.email}")
    
    return BusinessUnitResponse(
        id=new_bu.id,
        name=new_bu.name,
        slug=new_bu.slug,
        description=new_bu.description,
        organization_id=new_bu.organization_id,
        is_active=new_bu.is_active,
        created_at=new_bu.created_at,
        updated_at=new_bu.updated_at,
        role="admin",  # Admin who created it has admin role
        can_manage_members=True  # Admins can manage all business units
    )

@router.get("/{business_unit_id}", response_model=BusinessUnitResponse)
async def get_business_unit(
    business_unit_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get business unit details"""
    # Check if user has access
    # Eagerly load role to avoid lazy loading issues
    result = await db.execute(
        select(BusinessUnitMember)
        .options(selectinload(BusinessUnitMember.role))
        .where(
            BusinessUnitMember.business_unit_id == business_unit_id,
            BusinessUnitMember.user_id == current_user.id
        )
    )
    membership = result.scalar_one_or_none()
    
    # Check if user is super admin
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
    
    # Get business unit
    bu_result = await db.execute(
        select(BusinessUnit).where(BusinessUnit.id == business_unit_id)
    )
    bu = bu_result.scalar_one_or_none()
    if not bu:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Business unit not found"
        )
    
    role = None
    if membership:
        if hasattr(membership.role, 'value'):
            role = membership.role.value
        elif membership.role:
            role = membership.role.name
        else:
            role = str(membership.role).lower()
    elif is_admin:
        role = "admin"
    
    # Check if user has manage_members permission
    from app.api.deps import check_bu_permission
    can_manage = False
    if membership:
        can_manage = await check_bu_permission(
            current_user,
            business_unit_id,
            "business_unit:business_units:manage_members",
            db,
            enforcer,
            org_domain
        )
    elif is_admin:
        can_manage = True  # Admins can manage all business units
    
    return BusinessUnitResponse(
        id=bu.id,
        name=bu.name,
        slug=bu.slug,
        description=bu.description,
        organization_id=bu.organization_id,
        is_active=bu.is_active,
        created_at=bu.created_at,
        updated_at=bu.updated_at,
        role=role,
        can_manage_members=can_manage
    )

@router.put("/{business_unit_id}", response_model=BusinessUnitResponse)
async def update_business_unit(
    business_unit_id: uuid.UUID,
    business_unit: BusinessUnitUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update a business unit (owner or admin only)"""
    # Get business unit
    result = await db.execute(
        select(BusinessUnit).where(BusinessUnit.id == business_unit_id)
    )
    bu = result.scalar_one_or_none()
    if not bu:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Business unit not found"
        )
    
    # Check organization
    if bu.organization_id != current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update business units in your organization"
        )
    
    # Check if user is owner or admin
    # Eagerly load role to avoid lazy loading issues
    member_result = await db.execute(
        select(BusinessUnitMember)
        .options(selectinload(BusinessUnitMember.role))
        .where(
            BusinessUnitMember.business_unit_id == business_unit_id,
            BusinessUnitMember.user_id == current_user.id
        )
    )
    membership = member_result.scalar_one_or_none()
    
    from app.core.casbin import get_enforcer
    from app.core.organization import get_user_organization, get_organization_domain
    enforcer = get_enforcer()
    organization = await get_user_organization(current_user, db)
    org_domain = get_organization_domain(organization)
    is_admin = await is_platform_admin(current_user, db, enforcer)
    # Check if user has manage_members permission (permission-based, not role-name-based)
    from app.api.deps import check_bu_permission
    has_manage_permission = False
    if membership:
        has_manage_permission = await check_bu_permission(
            current_user,
            business_unit_id,
            "business_unit:business_units:manage_members",
            db,
            enforcer,
            org_domain
        )
    
    if not has_manage_permission and not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only business unit owners or admins can update business units"
        )
    
    # Update fields
    if business_unit.name is not None:
        bu.name = business_unit.name
    if business_unit.description is not None:
        bu.description = business_unit.description
    if business_unit.is_active is not None:
        bu.is_active = business_unit.is_active
    
    await db.commit()
    await db.refresh(bu)
    
    logger.info(f"Business unit '{bu.name}' updated by {current_user.email}")
    
    # Get user's role in the business unit
    from app.core.casbin import get_enforcer
    from app.core.organization import get_user_organization, get_organization_domain
    enforcer = get_enforcer()
    organization = await get_user_organization(current_user, db)
    org_domain = get_organization_domain(organization)
    is_admin = await is_platform_admin(current_user, db, enforcer)
    
    # Get membership to determine role
    member_result = await db.execute(
        select(BusinessUnitMember).where(
            BusinessUnitMember.business_unit_id == business_unit_id,
            BusinessUnitMember.user_id == current_user.id
        )
    )
    membership = member_result.scalar_one_or_none()
    role = None
    if membership:
        if hasattr(membership.role, 'value'):
            role = membership.role.value
        elif membership.role:
            role = membership.role.name
        else:
            role = str(membership.role).lower()
    elif is_admin:
        role = "admin"
    
    # Count members
    from sqlalchemy import func
    count_result = await db.execute(
        select(func.count(BusinessUnitMember.id)).where(
            BusinessUnitMember.business_unit_id == bu.id
        )
    )
    member_count = count_result.scalar() or 0
    
    # Check if user has manage_members permission
    from app.api.deps import check_bu_permission
    can_manage = False
    if membership:
        can_manage = await check_bu_permission(
            current_user,
            business_unit_id,
            "business_unit:business_units:manage_members",
            db,
            enforcer,
            org_domain
        )
    elif is_admin:
        can_manage = True  # Admins can manage all business units
    
    return BusinessUnitResponse(
        id=bu.id,
        name=bu.name,
        slug=bu.slug,
        description=bu.description,
        organization_id=bu.organization_id,
        is_active=bu.is_active,
        created_at=bu.created_at,
        updated_at=bu.updated_at,
        role=role,
        member_count=member_count,
        can_manage_members=can_manage
    )

@router.delete("/{business_unit_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_business_unit(
    business_unit_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    enforcer: OrgAwareEnforcer = Depends(get_org_aware_enforcer)
):
    """Delete a business unit (platform admin or BU owner with delete permission)"""
    from app.core.authorization import check_permission, is_platform_admin
    
    # Check if user is platform admin
    is_admin = await is_platform_admin(current_user, db, enforcer.enforcer if hasattr(enforcer, 'enforcer') else enforcer)
    
    # If not platform admin, check if user has BU delete permission
    if not is_admin:
        has_delete_permission = await check_permission(
            current_user,
            "business_unit:business_units:delete",
            business_unit_id,
            db,
            enforcer.enforcer if hasattr(enforcer, 'enforcer') else enforcer
        )
        if not has_delete_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied: You do not have permission to delete this business unit"
            )
    # Get business unit
    result = await db.execute(
        select(BusinessUnit).where(BusinessUnit.id == business_unit_id)
    )
    bu = result.scalar_one_or_none()
    if not bu:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Business unit not found"
        )
    
    # Check organization
    if bu.organization_id != current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete business units in your organization"
        )
    
    # Check if there are any deployments associated with this business unit
    from app.models.deployment import Deployment
    deployments_result = await db.execute(
        select(Deployment).where(Deployment.business_unit_id == business_unit_id)
    )
    deployments = deployments_result.scalars().all()
    
    if deployments:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete business unit with {len(deployments)} deployment(s). Delete or reassign deployments first."
        )
    
    # Delete the business unit (members will be cascade deleted)
    await db.delete(bu)
    await db.commit()
    
    logger.info(f"Business unit '{bu.name}' deleted by {current_user.email}")
    
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@router.get("/{business_unit_id}/members", response_model=List[BusinessUnitMemberResponse])
async def list_business_unit_members(
    business_unit_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List members of a business unit"""
    # Check if user has access (owner or admin)
    # Eagerly load role to avoid lazy loading issues
    member_result = await db.execute(
        select(BusinessUnitMember)
        .options(selectinload(BusinessUnitMember.role))
        .where(
            BusinessUnitMember.business_unit_id == business_unit_id,
            BusinessUnitMember.user_id == current_user.id
        )
    )
    membership = member_result.scalar_one_or_none()
    
    from app.core.casbin import get_enforcer
    from app.core.organization import get_user_organization, get_organization_domain
    enforcer = get_enforcer()
    organization = await get_user_organization(current_user, db)
    org_domain = get_organization_domain(organization)
    is_admin = await is_platform_admin(current_user, db, enforcer)
    # Check if user has manage_members permission (permission-based, not role-name-based)
    from app.api.deps import check_bu_permission
    has_manage_permission = False
    if membership:
        has_manage_permission = await check_bu_permission(
            current_user,
            business_unit_id,
            "business_unit:business_units:manage_members",
            db,
            enforcer,
            org_domain
        )
    
    if not membership and not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this business unit"
        )
    
    # Get all members with role relationship loaded
    result = await db.execute(
        select(BusinessUnitMember, User)
        .join(User, BusinessUnitMember.user_id == User.id)
        .where(BusinessUnitMember.business_unit_id == business_unit_id)
        .options(selectinload(BusinessUnitMember.user), selectinload(BusinessUnitMember.role))
    )
    members = result.all()
    
    return [
        BusinessUnitMemberResponse(
            id=member.id,
            business_unit_id=member.business_unit_id,
            user_id=member.user_id,
            user_email=user.email,
            user_name=user.full_name or user.username,
            role=member.role.name if member.role else "unknown",
            created_at=member.created_at
        )
        for member, user in members
    ]

@router.post("/{business_unit_id}/members", response_model=BusinessUnitMemberResponse, status_code=status.HTTP_201_CREATED)
async def add_business_unit_member(
    business_unit_id: uuid.UUID,
    member_data: BusinessUnitMemberAdd,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Add a member to a business unit (owner or admin only)"""
    # Check if user is owner or admin
    # Eagerly load role to avoid lazy loading issues
    member_result = await db.execute(
        select(BusinessUnitMember)
        .options(selectinload(BusinessUnitMember.role))
        .where(
            BusinessUnitMember.business_unit_id == business_unit_id,
            BusinessUnitMember.user_id == current_user.id
        )
    )
    membership = member_result.scalar_one_or_none()
    
    from app.core.casbin import get_enforcer
    from app.core.organization import get_user_organization, get_organization_domain
    enforcer = get_enforcer()
    organization = await get_user_organization(current_user, db)
    org_domain = get_organization_domain(organization)
    is_admin = await is_platform_admin(current_user, db, enforcer)
    # Check if user has manage_members permission (permission-based, not role-name-based)
    from app.api.deps import check_bu_permission
    has_manage_permission = False
    if membership:
        has_manage_permission = await check_bu_permission(
            current_user,
            business_unit_id,
            "business_unit:business_units:manage_members",
            db,
            enforcer,
            org_domain
        )
    
    if not has_manage_permission and not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only users with 'business_unit:business_units:manage_members' permission or admins can add members"
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
    
    # Check if user is already a member
    existing_result = await db.execute(
        select(BusinessUnitMember).where(
            BusinessUnitMember.business_unit_id == business_unit_id,
            BusinessUnitMember.user_id == user.id
        )
    )
    existing = existing_result.scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already a member of this business unit"
        )
    
    # Add member - get role by role_id or role name
    role = None
    if member_data.role_id:
        # role_id provided (after validation, it's a UUID object)
        try:
            role_result = await db.execute(
                select(Role).where(Role.id == member_data.role_id)
            )
            role = role_result.scalar_one_or_none()
            if not role:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Role with ID {member_data.role_id} not found"
                )
            # Validate role is not a platform role
            if role.is_platform_role:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot assign platform roles to business unit members. Please select a Business Unit role (bu-owner, bu-admin, developer, or viewer)."
                )
        except Exception as e:
            if isinstance(e, HTTPException):
                raise
            logger.error(f"Error fetching role {member_data.role_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid role ID: {member_data.role_id}"
            )
    elif hasattr(member_data, 'role') and member_data.role:
        # role name provided (for backward compatibility)
        role_name = member_data.role.lower()
        # Map old enum values to new role names
        role_name_mapping = {
            "owner": "bu-owner",
            "member": "viewer"
        }
        role_name = role_name_mapping.get(role_name, role_name)
        
        role_result = await db.execute(
            select(Role).where(Role.name == role_name, Role.is_platform_role == False)
        )
        role = role_result.scalar_one_or_none()
        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Role '{role_name}' not found or is a platform role"
            )
    else:
        # Default to viewer role
        role_result = await db.execute(
            select(Role).where(Role.name == "viewer", Role.is_platform_role == False)
        )
        role = role_result.scalar_one_or_none()
        if not role:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Default 'viewer' role not found. Please run database migration."
            )
    
    new_member = BusinessUnitMember(
        business_unit_id=business_unit_id,
        user_id=user.id,
        role_id=role.id
    )
    db.add(new_member)
    await db.commit()
    await db.refresh(new_member, ["role"])
    
    # Create BU-scoped permissions for the role in this business unit
    from app.core.migrate_casbin_policies import create_default_bu_role_permissions
    from app.core.organization import get_user_organization, get_organization_domain
    from app.core.casbin import get_enforcer
    
    enforcer = get_enforcer()
    organization = await get_user_organization(user, db)
    org_domain = get_organization_domain(organization)
    
    # Create default permissions for this role in this business unit
    await create_default_bu_role_permissions(role.name, business_unit_id, org_domain, enforcer)
    enforcer.save_policy()
    logger.info(f"Created BU-scoped permissions for role {role.name} in business unit {business_unit_id}")
    
    # Check if the role has business_units:manage_members permission
    # If so, grant them additional platform permissions needed for management
    from app.core.permission_registry import parse_permission_slug
    from app.api.deps import check_bu_permission
    
    # Check if role has manage_members permission (check in Casbin)
    obj, act = parse_permission_slug("business_unit:business_units:manage_members")
    bu_obj = f"bu:{business_unit_id}:{obj}"
    has_manage_permission = enforcer.enforce(role.name, org_domain, bu_obj, act)
    # Also check global permission
    if not has_manage_permission:
        has_manage_permission = enforcer.enforce(role.name, org_domain, obj, act)
    
    if has_manage_permission:
        from app.core.casbin import get_enforcer
        from app.core.organization import get_user_organization, get_organization_domain
        enforcer = get_enforcer()
        organization = await get_user_organization(user, db)
        org_domain = get_organization_domain(organization)
        
        # Note: Permissions are now managed through roles, not hardcoded here
        # The role assigned to the user should have the appropriate permissions
        # Platform permissions (like roles:list, users:list) should be added to the role
        # when creating/updating the role, not here
        logger.info(f"Added {user.email} to business unit {business_unit_id} with role {role.name}")
    
    # Return the response
    role_name = new_member.role.name if new_member.role else "unknown"
    return BusinessUnitMemberResponse(
        id=new_member.id,
        business_unit_id=new_member.business_unit_id,
        user_id=new_member.user_id,
        user_email=user.email,
        user_name=user.full_name or user.username or None,
        role=role_name,
        created_at=new_member.created_at
    )

@router.delete("/{business_unit_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_business_unit_member(
    business_unit_id: uuid.UUID,
    user_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Remove a member from a business unit (owner or admin only)"""
    # Check if user is owner or admin
    # Eagerly load role to avoid lazy loading issues
    member_result = await db.execute(
        select(BusinessUnitMember)
        .options(selectinload(BusinessUnitMember.role))
        .where(
            BusinessUnitMember.business_unit_id == business_unit_id,
            BusinessUnitMember.user_id == current_user.id
        )
    )
    membership = member_result.scalar_one_or_none()
    
    from app.core.casbin import get_enforcer
    from app.core.organization import get_user_organization, get_organization_domain
    enforcer = get_enforcer()
    organization = await get_user_organization(current_user, db)
    org_domain = get_organization_domain(organization)
    is_admin = await is_platform_admin(current_user, db, enforcer)
    # Check if user has manage_members permission (permission-based, not role-name-based)
    from app.api.deps import check_bu_permission
    has_manage_permission = False
    if membership:
        has_manage_permission = await check_bu_permission(
            current_user,
            business_unit_id,
            "business_unit:business_units:manage_members",
            db,
            enforcer,
            org_domain
        )
    
    if not has_manage_permission and not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only users with 'business_unit:business_units:manage_members' permission or admins can remove members"
        )
    
    # Find and remove member
    result = await db.execute(
        select(BusinessUnitMember).where(
            BusinessUnitMember.business_unit_id == business_unit_id,
            BusinessUnitMember.user_id == user_id
        )
    )
    member = result.scalar_one_or_none()
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found"
        )
    
    await db.delete(member)
    await db.commit()
    
    return None

@router.post("/users/me/active-business-unit")
async def set_active_business_unit(
    business_unit_id: Optional[uuid.UUID] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Set the active business unit for the current user"""
    if business_unit_id:
        # Validate user has access
        result = await db.execute(
            select(BusinessUnitMember).where(
                BusinessUnitMember.business_unit_id == business_unit_id,
                BusinessUnitMember.user_id == current_user.id
            )
        )
        membership = result.scalar_one_or_none()
        
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
        
        # Store in user's active_business_unit_id field
        current_user.active_business_unit_id = business_unit_id
    else:
        # Clear active business unit
        current_user.active_business_unit_id = None
    
    await db.commit()
    await db.refresh(current_user)
    
    return {"business_unit_id": str(business_unit_id) if business_unit_id else None}

@router.get("/users/me/active-business-unit")
async def get_active_business_unit(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get the active business unit for the current user"""
    # Refresh user to get latest active_business_unit_id
    await db.refresh(current_user)
    
    if current_user.active_business_unit_id:
        # Validate user still has access to this business unit
        result = await db.execute(
            select(BusinessUnitMember).where(
                BusinessUnitMember.business_unit_id == current_user.active_business_unit_id,
                BusinessUnitMember.user_id == current_user.id
            )
        )
        membership = result.scalar_one_or_none()
        
        # Also check if admin
        from app.core.casbin import get_enforcer
        from app.core.organization import get_user_organization, get_organization_domain
        enforcer = get_enforcer()
        organization = await get_user_organization(current_user, db)
        org_domain = get_organization_domain(organization)
        is_admin = await is_platform_admin(current_user, db, enforcer)
        
        if membership or is_admin:
            return {"business_unit_id": str(current_user.active_business_unit_id)}
        else:
            # User no longer has access, clear it
            current_user.active_business_unit_id = None
            await db.commit()
    
    return {"business_unit_id": None}

@router.get("/roles/available")
async def get_available_bu_roles(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get available business unit roles (non-platform roles only).
    This endpoint doesn't require platform permissions - any authenticated user can see BU roles.
    """
    from app.models.rbac import Role
    from app.schemas.rbac import RoleResponse
    from datetime import datetime
    
    # Get only business unit roles (not platform roles)
    result = await db.execute(
        select(Role).where(Role.is_platform_role == False).order_by(Role.name)
    )
    bu_roles = result.scalars().all()
    
    # Convert to response format
    roles_response = []
    for role in bu_roles:
        roles_response.append(RoleResponse(
            id=role.id,
            name=role.name,
            description=role.description,
            is_platform_role=role.is_platform_role,
            created_at=role.created_at,
            permissions=[]  # Don't include permissions for this endpoint
        ))
    
    return roles_response

@router.get("/users/available")
async def get_available_users(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    search: Optional[str] = Query(None, description="Search by email or name")
):
    """
    Get available users in the same organization.
    This endpoint doesn't require platform permissions - any authenticated user can see users in their organization.
    """
    from sqlalchemy import or_
    
    # Get users in the same organization
    query = select(User).where(User.organization_id == current_user.organization_id)
    
    # Apply search filter if provided
    if search:
        search_pattern = f"%{search}%"
        query = query.where(
            or_(
                User.email.ilike(search_pattern),
                User.username.ilike(search_pattern),
                User.full_name.ilike(search_pattern)
            )
        )
    
    # Limit to 1000 results
    query = query.limit(1000)
    
    result = await db.execute(query)
    users = result.scalars().all()
    
    # Convert to response format (simplified, without roles for performance)
    users_response = []
    for user in users:
        users_response.append({
            "id": str(user.id),
            "email": user.email,
            "username": user.username,
            "full_name": user.full_name,
            "is_active": user.is_active
        })
    
    return users_response

