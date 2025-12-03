"""
Backend utility functions for common patterns
"""
from fastapi import HTTPException, status
from typing import Optional, Any, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func

class NotFoundError(HTTPException):
    """Raised when a resource is not found"""
    def __init__(self, resource: str, identifier: str = "id"):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{resource} not found"
        )

class PermissionDeniedError(HTTPException):
    """Raised when user doesn't have permission"""
    def __init__(self, action: str = "access this resource"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permission denied: {action}"
        )

async def get_or_404(
    db: AsyncSession,
    model: Any,
    identifier: Any,
    identifier_field: str = "id",
    resource_name: Optional[str] = None
) -> Any:
    """
    Generic helper to get a model instance or raise 404
    
    Args:
        db: Database session
        model: SQLAlchemy model class
        identifier: Value to search for
        identifier_field: Field name to search (default: "id")
        resource_name: Human-readable resource name for error message
    
    Returns:
        Model instance
    
    Raises:
        NotFoundError: If resource not found
    """
    resource_name = resource_name or model.__name__
    query = select(model).where(getattr(model, identifier_field) == identifier)
    result = await db.execute(query)
    instance = result.scalars().first()
    
    if not instance:
        raise NotFoundError(resource_name, identifier_field)
    
    return instance

async def check_exists(
    db: AsyncSession,
    model: Any,
    field: str,
    value: Any,
    exclude_id: Optional[Any] = None
) -> bool:
    """
    Check if a record exists with given field value
    
    Args:
        db: Database session
        model: SQLAlchemy model class
        field: Field name to check
        value: Value to check
        exclude_id: Optional ID to exclude from check (for updates)
    
    Returns:
        True if exists, False otherwise
    """
    query = select(model).where(getattr(model, field) == value)
    if exclude_id:
        query = query.where(model.id != exclude_id)
    
    result = await db.execute(query)
    return result.scalars().first() is not None

def raise_not_found(resource: str, identifier: str = "id") -> None:
    """Raise a standardized 404 error"""
    raise NotFoundError(resource, identifier)

def raise_permission_denied(action: str = "access this resource") -> None:
    """Raise a standardized 403 error"""
    raise PermissionDeniedError(action)

async def get_count(db: AsyncSession, model: Any, filter_condition: Optional[Any] = None) -> int:
    """
    Get count of records in a model
    
    Args:
        db: Database session
        model: SQLAlchemy model class
        filter_condition: Optional filter condition
    
    Returns:
        Count of records
    """
    query = select(func.count(model.id))
    if filter_condition:
        query = query.where(filter_condition)
    
    result = await db.scalar(query)
    return result or 0

