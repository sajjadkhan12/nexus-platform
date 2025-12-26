"""Plugin access management endpoints"""
from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from typing import List, Optional
from datetime import datetime, timezone
import uuid
from uuid import UUID

from app.database import get_db
from app.models import (
    Plugin, PluginVersion, User, PluginAccess, PluginAccessRequest, AccessRequestStatus,
    Notification, NotificationType
)
from app.schemas.plugins import (
    PluginAccessRequestCreate, PluginAccessRequestResponse, PluginAccessGrantRequest, PluginAccessResponse
)
from app.api.deps import get_current_user, OrgAwareEnforcer, get_org_aware_enforcer, is_platform_admin
from app.logger import logger

router = APIRouter()

@router.post("/{plugin_id}/access/request", response_model=PluginAccessRequestResponse, status_code=status.HTTP_201_CREATED)
async def request_plugin_access(
    plugin_id: str,
    request_data: Optional[PluginAccessRequestCreate] = Body(default=None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    enforcer: OrgAwareEnforcer = Depends(get_org_aware_enforcer)
):
    """
    Request access to a locked plugin
    """
    from app.core.utils import get_or_404
    plugin = await get_or_404(db, Plugin, plugin_id, resource_name="Plugin")
    
    if not plugin.is_locked:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Plugin is not locked, access request not needed"
        )
    
    # Get user's active business unit
    business_unit_id = None
    if current_user.active_business_unit_id:
        business_unit_id = current_user.active_business_unit_id
    
    # Check if user already has approved access in this business unit
    access_result = await db.execute(
        select(PluginAccessRequest).where(
            PluginAccessRequest.plugin_id == plugin_id,
            PluginAccessRequest.user_id == current_user.id,
            PluginAccessRequest.business_unit_id == business_unit_id,
            PluginAccessRequest.status == AccessRequestStatus.APPROVED
        )
    )
    existing_access = access_result.scalar_one_or_none()
    if existing_access:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You already have access to this plugin in this business unit"
        )
    
    # Check if there's already a pending request
    request_result = await db.execute(
        select(PluginAccessRequest).where(
            PluginAccessRequest.plugin_id == plugin_id,
            PluginAccessRequest.user_id == current_user.id,
            PluginAccessRequest.status == AccessRequestStatus.PENDING
        )
    )
    existing_request = request_result.scalar_one_or_none()
    if existing_request:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You already have a pending access request for this plugin"
        )
    
    # Get user's active business unit
    business_unit_id = None
    if current_user.active_business_unit_id:
        business_unit_id = current_user.active_business_unit_id
    
    # Create new access request
    # Extract note from request body, handling both None and empty string
    if request_data and hasattr(request_data, 'note'):
        note = request_data.note if request_data.note and request_data.note.strip() else None
    else:
        note = None
    logger.info(f"Creating access request for plugin {plugin_id} by user {current_user.email} with note: {repr(note)}")
    access_request = PluginAccessRequest(
        plugin_id=plugin_id,
        user_id=current_user.id,
        business_unit_id=business_unit_id,
        status=AccessRequestStatus.PENDING,
        note=note
    )
    db.add(access_request)
    await db.commit()
    await db.refresh(access_request)
    
    # Create notification for admins and BU owners
    from app.models.business_unit import BusinessUnitMember
    from sqlalchemy.orm import selectinload
    from app.core.authorization import check_platform_permission, check_bu_permission
    
    # Collect user IDs to notify
    notify_user_ids = []
    
    # Get all users in the same organization
    admin_users_result = await db.execute(
        select(User).where(User.organization_id == current_user.organization_id)
    )
    org_users = admin_users_result.scalars().all()
    
    logger.info(f"Checking {len(org_users)} users in organization for admin/upload permissions")
    
    # Add admins - check all users in the organization
    for user in org_users:
        try:
            # Check if user is platform admin
            user_is_admin = await is_platform_admin(user, db, enforcer)
            # Check if user has plugins:upload permission
            base_enforcer = enforcer.enforcer if hasattr(enforcer, 'enforcer') else enforcer
            has_upload = await check_platform_permission(user, "platform:plugins:upload", db, base_enforcer)
            
            if user_is_admin or has_upload:
                if user.id not in notify_user_ids:
                    notify_user_ids.append(user.id)
                    logger.info(f"Added admin/upload user to notify list: {user.email} (admin: {user_is_admin}, upload: {has_upload})")
        except Exception as e:
            logger.warning(f"Error checking permissions for user {user.email}: {e}")
            continue
    
    # Add BU owners if user has a business unit
    if business_unit_id:
        logger.info(f"Checking BU owners for business_unit_id: {business_unit_id}")
        # Get all members of this business unit
        owners_result = await db.execute(
            select(BusinessUnitMember)
            .options(selectinload(BusinessUnitMember.role), selectinload(BusinessUnitMember.user))
            .where(BusinessUnitMember.business_unit_id == business_unit_id)
        )
        bu_members = owners_result.scalars().all()
        
        logger.info(f"Found {len(bu_members)} members in business unit")
        
        # Check if members have permission to manage BU (which includes approving plugin access)
        for member in bu_members:
            if member.role and member.user:
                try:
                    # Check if member has permission to manage business unit members (indicates BU owner/manager)
                    has_manage_permission = await check_bu_permission(
                        member.user, 
                        "business_unit:business_units:manage_members",
                        business_unit_id,
                        db,
                        enforcer
                    )
                    if has_manage_permission and member.user_id not in notify_user_ids:
                        notify_user_ids.append(member.user_id)
                        logger.info(f"Added BU owner to notify list: {member.user.email}")
                except Exception as e:
                    logger.warning(f"Error checking BU permission for user {member.user.email if member.user else 'unknown'}: {e}")
                    continue
    else:
        logger.warning("No business_unit_id provided, skipping BU owner notification")
    
    logger.info(f"Total users to notify: {len(notify_user_ids)}")
    
    # Create notifications for all admins and BU owners
    note_text = f"\n\nReason: {note}" if note else ""
    for notify_user_id in notify_user_ids:
        notification = Notification(
            id=str(uuid.uuid4()),
            user_id=notify_user_id,
            title=f"Plugin Access Request",
            message=f"{current_user.email} requested access to locked plugin: {plugin.name}{note_text}",
            type=NotificationType.INFO,
            link=f"/admin/plugin-requests"
        )
        db.add(notification)
        logger.info(f"Created notification for user_id: {notify_user_id}")
    
    await db.commit()
    await db.refresh(access_request)
    
    logger.info(f"Access request created for plugin {plugin_id} by user {current_user.email} with note: {repr(access_request.note)}")
    
    # Convert to response format
    return PluginAccessRequestResponse(
        id=access_request.id,
        plugin_id=access_request.plugin_id,
        plugin_name=plugin.name,
        user_id=access_request.user_id,
        user_email=current_user.email,
        status=access_request.status.value if hasattr(access_request.status, 'value') else str(access_request.status),
        requested_at=access_request.requested_at,
        reviewed_at=access_request.reviewed_at,
        reviewed_by=access_request.reviewed_by,
        note=access_request.note
    )

@router.get("/access/requests", response_model=List[PluginAccessRequestResponse])
async def list_all_access_requests(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    enforcer: OrgAwareEnforcer = Depends(get_org_aware_enforcer),
    search: str = Query(None, description="Search by user email, username, full name, or plugin name (partial match)"),
    status_filter: str = Query(None, description="Filter by status: pending, approved, rejected")
):
    """
    List all access requests across all plugins (admin or BU owner)
    Optional search by user email, username, full name, or plugin name
    Optional filter by status
    """
    from app.models.business_unit import BusinessUnitMember
    from sqlalchemy.orm import selectinload
    
    from app.core.authorization import check_platform_permission
    is_admin = await check_platform_permission(current_user, "platform:plugins:upload", db, enforcer.enforcer if hasattr(enforcer, 'enforcer') else enforcer)
    
    # Check if user is a BU owner
    is_bu_owner = False
    bu_ids_owned = []
    if not is_admin:
        # Get all business units where user is an owner
        owners_result = await db.execute(
            select(BusinessUnitMember)
            .options(selectinload(BusinessUnitMember.role))
            .where(BusinessUnitMember.user_id == current_user.id)
        )
        bu_memberships = owners_result.scalars().all()
        
        # Check if user has permission to manage BU members (indicates BU owner/manager)
        from app.core.authorization import check_bu_permission
        from app.core.organization import get_user_organization, get_organization_domain
        org = await get_user_organization(current_user, db)
        org_domain = get_organization_domain(org)
        
        for membership in bu_memberships:
            if membership.role:
                has_manage_permission = await check_bu_permission(
                    current_user,
                    "business_unit:business_units:manage_members",
                    membership.business_unit_id,
                    db,
                    enforcer
                )
                if has_manage_permission:
                    is_bu_owner = True
                    bu_ids_owned.append(membership.business_unit_id)
    
    if not is_admin and not is_bu_owner:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators or business unit owners can view access requests"
        )
    
    # Build query with joins
    query = select(PluginAccessRequest, User.email, User.username, User.full_name, Plugin.name).join(
        User, PluginAccessRequest.user_id == User.id
    ).join(
        Plugin, PluginAccessRequest.plugin_id == Plugin.id
    )
    
    # Filter by business unit if user is a BU owner (not admin)
    if is_bu_owner and not is_admin:
        # Only show requests from users in business units owned by this user
        if bu_ids_owned:
            # Filter by business_unit_id matching owned BUs, and exclude NULL business_unit_id
            query = query.where(
                PluginAccessRequest.business_unit_id.in_(bu_ids_owned),
                PluginAccessRequest.business_unit_id.isnot(None)
            )
        else:
            # No business units owned, return empty list
            return []
    
    # Apply search filter (searches across email, username, full_name, and plugin name)
    if search:
        search_pattern = f"%{search}%"
        query = query.where(
            or_(
                User.email.ilike(search_pattern),
                User.username.ilike(search_pattern),
                User.full_name.ilike(search_pattern),
                Plugin.name.ilike(search_pattern),
                Plugin.id.ilike(search_pattern)
            )
        )
    
    # Apply status filter
    if status_filter:
        # Convert string status to enum
        try:
            status_enum = AccessRequestStatus(status_filter.lower())
            query = query.where(PluginAccessRequest.status == status_enum)
        except ValueError:
            # Invalid status value, ignore filter
            pass
    
    query = query.order_by(PluginAccessRequest.requested_at.desc())
    
    result = await db.execute(query)
    rows = result.all()
    
    # Convert to response format with user email and plugin name
    requests = []
    for row in rows:
        request, user_email_val, username, full_name, plugin_name = row
        request_dict = {
            "id": request.id,
            "plugin_id": request.plugin_id,
            "plugin_name": plugin_name,  # Add plugin name for display
            "user_id": request.user_id,
            "user_email": user_email_val,
            "status": request.status.value if hasattr(request.status, 'value') else str(request.status),
            "requested_at": request.requested_at,
            "reviewed_at": request.reviewed_at,
            "reviewed_by": request.reviewed_by,
            "note": request.note
        }
        requests.append(PluginAccessRequestResponse(**request_dict))
    
    return requests

@router.get("/{plugin_id}/access/requests", response_model=List[PluginAccessRequestResponse])
async def list_access_requests(
    plugin_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    enforcer: OrgAwareEnforcer = Depends(get_org_aware_enforcer)
):
    """
    List access requests for a plugin (admin or BU owner)
    """
    from app.models.business_unit import BusinessUnitMember
    from sqlalchemy.orm import selectinload
    
    from app.core.authorization import check_platform_permission
    is_admin = await check_platform_permission(current_user, "platform:plugins:upload", db, enforcer.enforcer if hasattr(enforcer, 'enforcer') else enforcer)
    
    # Check if user is a BU owner
    is_bu_owner = False
    bu_ids_owned = []
    if not is_admin:
        # Get all business units where user is an owner
        owners_result = await db.execute(
            select(BusinessUnitMember)
            .options(selectinload(BusinessUnitMember.role))
            .where(BusinessUnitMember.user_id == current_user.id)
        )
        bu_memberships = owners_result.scalars().all()
        
        # Check if user has permission to manage BU members (indicates BU owner/manager)
        from app.core.authorization import check_bu_permission
        from app.core.organization import get_user_organization, get_organization_domain
        org = await get_user_organization(current_user, db)
        org_domain = get_organization_domain(org)
        
        for membership in bu_memberships:
            if membership.role:
                has_manage_permission = await check_bu_permission(
                    current_user,
                    "business_unit:business_units:manage_members",
                    membership.business_unit_id,
                    db,
                    enforcer
                )
                if has_manage_permission:
                    is_bu_owner = True
                    bu_ids_owned.append(membership.business_unit_id)
    
    if not is_admin and not is_bu_owner:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators or business unit owners can view access requests"
        )
    
    from app.core.utils import get_or_404
    plugin = await get_or_404(db, Plugin, plugin_id, resource_name="Plugin")
    
    # Build query
    query = select(PluginAccessRequest, User.email).join(
        User, PluginAccessRequest.user_id == User.id
    ).where(PluginAccessRequest.plugin_id == plugin_id)
    
    # Filter by business unit if user is a BU owner (not admin)
    if is_bu_owner and not is_admin:
        # Only show requests from users in business units owned by this user
        if bu_ids_owned:
            # Filter by business_unit_id matching owned BUs, and exclude NULL business_unit_id
            query = query.where(
                PluginAccessRequest.business_unit_id.in_(bu_ids_owned),
                PluginAccessRequest.business_unit_id.isnot(None)
            )
        else:
            # No business units owned, return empty list
            return []
    
    query = query.order_by(PluginAccessRequest.requested_at.desc())
    
    result = await db.execute(query)
    rows = result.all()
    
    # Convert to response format with user email
    requests = []
    for request, user_email in rows:
        request_dict = {
            "id": request.id,
            "plugin_id": request.plugin_id,
            "user_id": request.user_id,
            "user_email": user_email,
            "status": request.status.value if hasattr(request.status, 'value') else str(request.status),
            "requested_at": request.requested_at,
            "reviewed_at": request.reviewed_at,
            "reviewed_by": request.reviewed_by,
            "note": request.note
        }
        requests.append(PluginAccessRequestResponse(**request_dict))
    
    return requests

@router.post("/{plugin_id}/access/grant", response_model=PluginAccessResponse, status_code=status.HTTP_201_CREATED)
async def grant_plugin_access(
    plugin_id: str,
    request: PluginAccessGrantRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    enforcer: OrgAwareEnforcer = Depends(get_org_aware_enforcer)
):
    """
    Grant access to a user for a locked plugin (admin or BU owner)
    """
    from app.models.business_unit import BusinessUnitMember
    from sqlalchemy.orm import selectinload
    
    from app.core.authorization import check_platform_permission
    is_admin = await check_platform_permission(current_user, "platform:plugins:upload", db, enforcer.enforcer if hasattr(enforcer, 'enforcer') else enforcer)
    
    # Check if user is a BU owner and if the target user is in their BU
    is_authorized = is_admin
    if not is_admin:
        # Get the access request to find the business unit
        access_request_result = await db.execute(
            select(PluginAccessRequest).where(
                PluginAccessRequest.plugin_id == plugin_id,
                PluginAccessRequest.user_id == request.user_id,
                PluginAccessRequest.status == AccessRequestStatus.PENDING
            )
        )
        access_request = access_request_result.scalar_one_or_none()
        
        if access_request and access_request.business_unit_id:
            # Check if current user is owner of this business unit
            owner_result = await db.execute(
                select(BusinessUnitMember)
                .options(selectinload(BusinessUnitMember.role))
                .where(
                    BusinessUnitMember.business_unit_id == access_request.business_unit_id,
                    BusinessUnitMember.user_id == current_user.id
                )
            )
            membership = owner_result.scalar_one_or_none()
            if membership and membership.role:
                # Check if user has permission to manage BU members
                from app.core.authorization import check_bu_permission
                from app.core.organization import get_user_organization, get_organization_domain
                org = await get_user_organization(current_user, db)
                org_domain = get_organization_domain(org)
                has_manage_permission = await check_bu_permission(
                    current_user,
                    "business_unit:business_units:manage_members",
                    access_request.business_unit_id,
                    db,
                    enforcer
                )
                if has_manage_permission:
                    is_authorized = True
    
    if not is_authorized:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators or business unit owners can grant plugin access"
        )
    
    from app.core.utils import get_or_404
    plugin = await get_or_404(db, Plugin, plugin_id, resource_name="Plugin")
    
    # Check if user exists
    user_result = await db.execute(
        select(User).where(User.id == request.user_id)
    )
    target_user = user_result.scalar_one_or_none()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Get the business_unit_id from the pending request
    pending_requests_result = await db.execute(
        select(PluginAccessRequest).where(
            PluginAccessRequest.plugin_id == plugin_id,
            PluginAccessRequest.user_id == request.user_id,
            PluginAccessRequest.status == AccessRequestStatus.PENDING
        )
    )
    pending_requests = pending_requests_result.scalars().all()
    
    # Get business_unit_id from the first pending request (they should all be for the same BU)
    business_unit_id = None
    if pending_requests:
        business_unit_id = pending_requests[0].business_unit_id
    
    # Check if access already exists for this business unit
    existing_result = await db.execute(
        select(PluginAccess).where(
            PluginAccess.plugin_id == plugin_id,
            PluginAccess.user_id == request.user_id,
            PluginAccess.business_unit_id == business_unit_id
        )
    )
    existing_access = existing_result.scalar_one_or_none()
    if existing_access:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already has access to this plugin in this business unit"
        )
    
    # Grant access with business_unit_id
    plugin_access = PluginAccess(
        plugin_id=plugin_id,
        user_id=request.user_id,
        business_unit_id=business_unit_id,
        granted_by=current_user.id
    )
    db.add(plugin_access)
    for req in pending_requests:
        req.status = AccessRequestStatus.APPROVED  # TypeDecorator handles conversion
        req.reviewed_at = datetime.now(timezone.utc)
        req.reviewed_by = current_user.id
    
    # Create notification for the user
    notification = Notification(
        id=str(uuid.uuid4()),
        user_id=request.user_id,
        title=f"Plugin Access Granted",
        message=f"You have been granted access to plugin: {plugin.name}",
        type=NotificationType.SUCCESS,
        link=f"/provision/{plugin_id}"
    )
    db.add(notification)
    
    await db.commit()
    await db.refresh(plugin_access)
    
    logger.info(f"Access granted to user {target_user.email} for plugin {plugin_id} by {current_user.email}")
    return plugin_access

@router.post("/{plugin_id}/access/reject", status_code=status.HTTP_200_OK)
async def reject_plugin_access_request(
    plugin_id: str,
    request: PluginAccessGrantRequest,  # Reuse same schema for user_id
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    enforcer: OrgAwareEnforcer = Depends(get_org_aware_enforcer)
):
    """
    Reject a pending plugin access request (admin or BU owner)
    """
    from app.models.business_unit import BusinessUnitMember
    from sqlalchemy.orm import selectinload
    
    from app.core.authorization import check_platform_permission
    is_admin = await check_platform_permission(current_user, "platform:plugins:upload", db, enforcer.enforcer if hasattr(enforcer, 'enforcer') else enforcer)
    
    # Check if user is a BU owner and if the target user is in their BU
    is_authorized = is_admin
    if not is_admin:
        # Get the access request to find the business unit
        access_request_result = await db.execute(
            select(PluginAccessRequest).where(
                PluginAccessRequest.plugin_id == plugin_id,
                PluginAccessRequest.user_id == request.user_id,
                PluginAccessRequest.status == AccessRequestStatus.PENDING
            )
        )
        access_request = access_request_result.scalar_one_or_none()
        
        if access_request and access_request.business_unit_id:
            # Check if current user is owner of this business unit
            owner_result = await db.execute(
                select(BusinessUnitMember)
                .options(selectinload(BusinessUnitMember.role))
                .where(
                    BusinessUnitMember.business_unit_id == access_request.business_unit_id,
                    BusinessUnitMember.user_id == current_user.id
                )
            )
            membership = owner_result.scalar_one_or_none()
            if membership and membership.role:
                # Check if user has permission to manage BU members
                from app.core.authorization import check_bu_permission
                from app.core.organization import get_user_organization, get_organization_domain
                org = await get_user_organization(current_user, db)
                org_domain = get_organization_domain(org)
                has_manage_permission = await check_bu_permission(
                    current_user,
                    "business_unit:business_units:manage_members",
                    access_request.business_unit_id,
                    db,
                    enforcer
                )
                if has_manage_permission:
                    is_authorized = True
    
    if not is_authorized:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators or business unit owners can reject plugin access requests"
        )
    
    from app.core.utils import get_or_404
    plugin = await get_or_404(db, Plugin, plugin_id, resource_name="Plugin")
    
    # Check if user exists
    user_result = await db.execute(
        select(User).where(User.id == request.user_id)
    )
    target_user = user_result.scalar_one_or_none()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Find pending access requests for this user and plugin
    pending_requests_result = await db.execute(
        select(PluginAccessRequest).where(
            PluginAccessRequest.plugin_id == plugin_id,
            PluginAccessRequest.user_id == request.user_id,
            PluginAccessRequest.status == AccessRequestStatus.PENDING
        )
    )
    pending_requests = pending_requests_result.scalars().all()
    
    if not pending_requests:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No pending access request found for this user and plugin"
        )
    
    # Update all pending requests to rejected
    for req in pending_requests:
        req.status = AccessRequestStatus.REJECTED
        req.reviewed_at = datetime.now(timezone.utc)
        req.reviewed_by = current_user.id
    
    # Create notification for the user
    notification = Notification(
        id=str(uuid.uuid4()),
        user_id=request.user_id,
        title=f"Plugin Access Request Rejected",
        message=f"Your access request for plugin '{plugin.name}' has been rejected. Please contact an administrator if you believe this is an error.",
        type=NotificationType.WARNING,
        link=f"/provision/{plugin_id}"
    )
    db.add(notification)
    
    await db.commit()
    
    logger.info(f"Access request rejected for user {target_user.email} for plugin {plugin_id} by {current_user.email}")
    
    return {"message": "Access request rejected successfully", "status": "rejected"}

@router.delete("/{plugin_id}/access/{user_id}", status_code=status.HTTP_200_OK)
async def revoke_plugin_access(
    plugin_id: str,
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    enforcer: OrgAwareEnforcer = Depends(get_org_aware_enforcer)
):
    """
    Revoke access from a user for a locked plugin (admin only)
    Sets the access request status to 'revoked' instead of deleting
    """
    from app.core.authorization import check_platform_permission
    has_permission = await check_platform_permission(current_user, "platform:plugins:upload", db, enforcer.enforcer if hasattr(enforcer, 'enforcer') else enforcer)
    if not has_permission:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can revoke plugin access"
        )
    
    from app.core.utils import get_or_404
    plugin = await get_or_404(db, Plugin, plugin_id, resource_name="Plugin")
    
    # Convert user_id string to UUID
    try:
        target_user_uuid = UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID format"
        )
    
    # Find and delete the access grant (user loses access)
    # Note: For backward compatibility, we'll revoke all access records for this plugin+user
    # In the future, we might want to add a business_unit_id parameter to revoke specific BU access
    access_result = await db.execute(
        select(PluginAccess).where(
            PluginAccess.plugin_id == plugin_id,
            PluginAccess.user_id == target_user_uuid
        )
    )
    access_records = access_result.scalars().all()
    
    if not access_records:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Access record not found"
        )
    
    # Get target user for notification
    user_result = await db.execute(
        select(User).where(User.id == target_user_uuid)
    )
    target_user = user_result.scalar_one_or_none()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Update any approved access requests to revoked status
    # This allows tracking of revoked access in the revoked tab
    approved_requests_result = await db.execute(
        select(PluginAccessRequest).where(
            PluginAccessRequest.plugin_id == plugin_id,
            PluginAccessRequest.user_id == target_user_uuid,
            PluginAccessRequest.status == AccessRequestStatus.APPROVED
        )
    )
    approved_requests = approved_requests_result.scalars().all()
    for req in approved_requests:
        req.status = AccessRequestStatus.REVOKED  # Mark as revoked to show in revoked tab
        req.reviewed_at = datetime.now(timezone.utc)
        req.reviewed_by = current_user.id
    
    # Delete all access records for this plugin+user (across all business units)
    for access in access_records:
        await db.delete(access)
    
    # Create notification for the user
    notification = Notification(
        id=str(uuid.uuid4()),
        user_id=target_user_uuid,
        title=f"Plugin Access Revoked",
        message=f"Your access to plugin '{plugin.name}' has been revoked. You will need to request access again if needed.",
        type=NotificationType.WARNING,
        link=f"/provision/{plugin_id}"
    )
    db.add(notification)
    
    await db.commit()
    
    logger.info(f"Access revoked from user {target_user.email} for plugin {plugin_id} by {current_user.email}")
    
    return {"message": "Access revoked successfully", "status": "revoked"}

@router.post("/{plugin_id}/access/{user_id}/restore", status_code=status.HTTP_200_OK)
async def restore_plugin_access(
    plugin_id: str,
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    enforcer: OrgAwareEnforcer = Depends(get_org_aware_enforcer)
):
    """
    Restore access for a user (admin only)
    Changes the revoked status back to approved and creates a new PluginAccess record
    """
    from app.core.authorization import check_platform_permission
    has_permission = await check_platform_permission(current_user, "platform:plugins:upload", db, enforcer.enforcer if hasattr(enforcer, 'enforcer') else enforcer)
    if not has_permission:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can restore plugin access"
        )
    
    from app.core.utils import get_or_404
    plugin = await get_or_404(db, Plugin, plugin_id, resource_name="Plugin")
    
    # Convert user_id string to UUID
    try:
        target_user_uuid = UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID format"
        )
    
    # Find the revoked request
    revoked_request_result = await db.execute(
        select(PluginAccessRequest).where(
            PluginAccessRequest.plugin_id == plugin_id,
            PluginAccessRequest.user_id == target_user_uuid,
            PluginAccessRequest.status == AccessRequestStatus.REVOKED
        )
    )
    revoked_request = revoked_request_result.scalar_one_or_none()
    
    if not revoked_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No revoked access found for this user and plugin"
        )
    
    # Get target user for notification
    user_result = await db.execute(
        select(User).where(User.id == target_user_uuid)
    )
    target_user = user_result.scalar_one_or_none()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Get business_unit_id from the revoked request
    business_unit_id = revoked_request.business_unit_id
    
    # Check if access already exists for this business unit (shouldn't happen, but just in case)
    existing_access_result = await db.execute(
        select(PluginAccess).where(
            PluginAccess.plugin_id == plugin_id,
            PluginAccess.user_id == target_user_uuid,
            PluginAccess.business_unit_id == business_unit_id
        )
    )
    existing_access = existing_access_result.scalar_one_or_none()
    
    if not existing_access:
        # Create new access grant with business_unit_id
        new_access = PluginAccess(
            plugin_id=plugin_id,
            user_id=target_user_uuid,
            business_unit_id=business_unit_id,
            granted_by=current_user.id
        )
        db.add(new_access)
    
    # Update request status back to approved
    revoked_request.status = AccessRequestStatus.APPROVED
    revoked_request.reviewed_at = datetime.now(timezone.utc)
    revoked_request.reviewed_by = current_user.id
    
    # Create notification for the user
    notification = Notification(
        id=str(uuid.uuid4()),
        user_id=target_user_uuid,
        title=f"Plugin Access Restored",
        message=f"Your access to plugin '{plugin.name}' has been restored by an administrator.",
        type=NotificationType.INFO,
        link=f"/provision/{plugin_id}"
    )
    db.add(notification)
    
    await db.commit()
    
    logger.info(f"Access restored to user {target_user.email} for plugin {plugin_id} by {current_user.email}")
    
    return {"message": "Access restored successfully", "status": "approved"}

@router.get("/{plugin_id}/access", response_model=List[PluginAccessResponse])
async def list_plugin_access(
    plugin_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    enforcer: OrgAwareEnforcer = Depends(get_org_aware_enforcer)
):
    """
    List users with access to a plugin (admin only)
    """
    from app.core.authorization import check_platform_permission
    has_permission = await check_platform_permission(current_user, "platform:plugins:upload", db, enforcer.enforcer if hasattr(enforcer, 'enforcer') else enforcer)
    if not has_permission:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can view plugin access"
        )
    
    from app.core.utils import get_or_404
    plugin = await get_or_404(db, Plugin, plugin_id, resource_name="Plugin")
    
    result = await db.execute(
        select(PluginAccess).where(
            PluginAccess.plugin_id == plugin_id
        ).order_by(PluginAccess.granted_at.desc())
    )
    access_list = result.scalars().all()
    
    return access_list

@router.get("/access/grants", response_model=List[dict])
async def list_all_access_grants(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    enforcer: OrgAwareEnforcer = Depends(get_org_aware_enforcer),
    user_email: str = Query(None, description="Filter by user email (partial match)")
):
    """
    List all access grants across all plugins with user and plugin info (admin only)
    Used for the plugin requests page to show who currently has access
    """
    from app.core.authorization import check_platform_permission
    has_permission = await check_platform_permission(current_user, "platform:plugins:upload", db, enforcer.enforcer if hasattr(enforcer, 'enforcer') else enforcer)
    if not has_permission:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can view access grants"
        )
    
    # Build query with joins to get user email and plugin name
    query = select(PluginAccess, User.email, Plugin.name, User.id).join(
        User, PluginAccess.user_id == User.id
    ).join(
        Plugin, PluginAccess.plugin_id == Plugin.id
    )
    
    if user_email:
        query = query.where(User.email.ilike(f"%{user_email}%"))
    
    query = query.order_by(PluginAccess.granted_at.desc())
    
    result = await db.execute(query)
    rows = result.all()
    
    # Convert to response format with user email and plugin name
    grants = []
    for row in rows:
        access, user_email_val, plugin_name, user_uuid = row
        grants.append({
            "id": access.id,
            "plugin_id": access.plugin_id,
            "plugin_name": plugin_name,
            "user_id": str(access.user_id),
            "user_email": user_email_val,
            "granted_by": str(access.granted_by),
            "granted_at": access.granted_at.isoformat()
        })
    
    return grants

