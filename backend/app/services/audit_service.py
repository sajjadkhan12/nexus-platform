"""
Audit logging service for recording all write operations
"""
from typing import Optional, Dict, Any
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.audit import AuditLog
from app.models.rbac import User
from app.logger import logger
import uuid


async def log_audit_event(
    db: AsyncSession,
    user_id: Optional[UUID],
    action: str,
    resource_type: Optional[str] = None,
    resource_id: Optional[UUID] = None,
    details: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None,
    status: str = "success"
) -> Optional[AuditLog]:
    """
    Log an audit event to the database.
    
    Args:
        db: Database session
        user_id: ID of the user performing the action (None for unauthenticated)
        action: Action being performed (e.g., 'create', 'update', 'delete')
        resource_type: Type of resource (e.g., 'users', 'roles', 'groups')
        resource_id: ID of the resource being acted upon
        details: Full request/response data as JSON
        ip_address: IP address of the client
        status: 'success' or 'failure'
    
    Returns:
        Created AuditLog object or None if logging failed
    """
    try:
        # Mask sensitive data in details if present
        safe_details = _mask_sensitive_data(details) if details else {}
        
        # Ensure details is a dict and add status
        if not isinstance(safe_details, dict):
            safe_details = {"raw_data": safe_details}
        
        # Add status to details
        safe_details["status"] = status
        
        audit_log = AuditLog(
            id=uuid.uuid4(),
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=safe_details,
            ip_address=ip_address,
        )
        
        db.add(audit_log)
        await db.commit()
        await db.refresh(audit_log)
        
        return audit_log
    except Exception as e:
        # Log error but don't raise - audit logging should never break the request
        logger.error(f"Failed to log audit event: {str(e)}", exc_info=True)
        await db.rollback()
        return None


def _mask_sensitive_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Recursively mask sensitive fields in the data dictionary.
    
    Fields to mask:
    - password, hashed_password, current_password, new_password
    - access_token, refresh_token, token
    - secret_key, api_key, api_secret
    - credentials (in nested objects)
    """
    if not isinstance(data, dict):
        return data
    
    sensitive_fields = {
        "password", "hashed_password", "current_password", "new_password",
        "access_token", "refresh_token", "token", "secret_key", "api_key",
        "api_secret", "credentials", "encrypted_data"
    }
    
    masked_data = {}
    for key, value in data.items():
        if key.lower() in sensitive_fields:
            masked_data[key] = "***MASKED***"
        elif isinstance(value, dict):
            masked_data[key] = _mask_sensitive_data(value)
        elif isinstance(value, list):
            masked_data[key] = [
                _mask_sensitive_data(item) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            masked_data[key] = value
    
    return masked_data

