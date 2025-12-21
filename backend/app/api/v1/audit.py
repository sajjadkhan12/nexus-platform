"""
Audit log API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_, or_, func
from sqlalchemy.orm import selectinload
from typing import Optional
from uuid import UUID
from datetime import datetime

from app.database import get_db
from app.models.audit import AuditLog
from app.models.rbac import User
from app.schemas.audit import AuditLogResponse, AuditLogListResponse
from app.api.deps import get_current_active_superuser
from app.logger import logger

router = APIRouter(prefix="/audit-logs", tags=["audit"])


def audit_log_to_response(audit_log: AuditLog, include_user: bool = True) -> dict:
    """Convert AuditLog model to response dict"""
    result = {
        "id": audit_log.id,
        "user_id": audit_log.user_id,
        "action": audit_log.action,
        "resource_type": audit_log.resource_type,
        "resource_id": audit_log.resource_id,
        "details": audit_log.details,
        "ip_address": audit_log.ip_address,
        "created_at": audit_log.created_at,
    }
    
    # Include user info if available (without avatar_url to reduce load)
    if include_user and audit_log.user:
        result["user"] = {
            "id": audit_log.user.id,
            "email": audit_log.user.email,
            "username": audit_log.user.username,
            "full_name": audit_log.user.full_name,
        }
    else:
        result["user"] = None
    
    return result


@router.get("/", response_model=AuditLogListResponse)
async def list_audit_logs(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    user_id: Optional[UUID] = Query(None),
    action: Optional[str] = Query(None),
    resource_type: Optional[str] = Query(None),
    resource_id: Optional[UUID] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    search: Optional[str] = Query(None),
    status: Optional[str] = Query(None, description="Filter by status: 'success' or 'failure'"),
    current_user: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db)
):
    """
    List audit logs with filtering and pagination (Admin only)
    """
    # Build query
    query = select(AuditLog)
    
    # Apply filters
    conditions = []
    
    if user_id:
        conditions.append(AuditLog.user_id == user_id)
    
    if action:
        conditions.append(AuditLog.action == action)
    
    if resource_type:
        conditions.append(AuditLog.resource_type == resource_type)
    
    if resource_id:
        conditions.append(AuditLog.resource_id == resource_id)
    
    if start_date:
        conditions.append(AuditLog.created_at >= start_date)
    
    if end_date:
        conditions.append(AuditLog.created_at <= end_date)
    
    if status:
        # Status is stored in details JSONB field
        # Use PostgreSQL JSONB operators for better performance
        if status == "success":
            # Success if status is "success" or status field doesn't exist (defaults to success)
            conditions.append(
                or_(
                    AuditLog.details['status'].astext == "success",
                    ~AuditLog.details.has_key('status')
                )
            )
        elif status == "failure":
            conditions.append(
                AuditLog.details['status'].astext == "failure"
            )
    
    if search:
        # Validate search length to prevent DoS
        if len(search) > 100:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Search query must be 100 characters or less"
            )
        # Full-text search in details JSONB field
        # PostgreSQL JSONB supports @> operator for containment
        # We'll search for the term in the JSON structure
        search_conditions = [
            func.cast(AuditLog.details, func.text).ilike(f"%{search}%"),
            func.cast(AuditLog.action, func.text).ilike(f"%{search}%"),
            func.cast(AuditLog.resource_type, func.text).ilike(f"%{search}%"),
        ]
        conditions.append(or_(*search_conditions))
    
    if conditions:
        query = query.where(and_(*conditions))
    
    # Get total count
    count_query = select(func.count()).select_from(AuditLog)
    if conditions:
        count_query = count_query.where(and_(*conditions))
    
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # Apply pagination and ordering
    query = query.order_by(AuditLog.created_at.desc())
    query = query.offset(skip).limit(limit)
    
    # Execute query with user relationship loaded
    result = await db.execute(
        query.options(selectinload(AuditLog.user))
    )
    audit_logs = result.scalars().all()
    
    # Convert to response format
    items = [audit_log_to_response(log) for log in audit_logs]
    
    return {
        "items": items,
        "total": total,
        "skip": skip,
        "limit": limit
    }


@router.get("/{log_id}", response_model=AuditLogResponse)
async def get_audit_log(
    log_id: UUID,
    current_user: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db)
):
    """
    Get a single audit log by ID (Admin only)
    """
    result = await db.execute(
        select(AuditLog)
        .where(AuditLog.id == log_id)
        .options(selectinload(AuditLog.user))
    )
    audit_log = result.scalars().first()
    
    if not audit_log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audit log not found"
        )
    
    return audit_log_to_response(audit_log)

