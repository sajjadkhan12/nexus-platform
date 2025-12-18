from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID

class AuditLogResponse(BaseModel):
    """Response schema for a single audit log entry"""
    id: UUID
    user_id: Optional[UUID] = None
    action: str
    resource_type: Optional[str] = None
    resource_id: Optional[UUID] = None
    details: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = None
    created_at: datetime
    
    # Include user info if available
    user: Optional[Dict[str, Any]] = None
    
    model_config = {"from_attributes": True}

class AuditLogListResponse(BaseModel):
    """Response schema for paginated audit log list"""
    items: List[AuditLogResponse]
    total: int
    skip: int
    limit: int

class AuditLogFilter(BaseModel):
    """Query parameters for filtering audit logs"""
    skip: int = Field(default=0, ge=0, description="Number of records to skip")
    limit: int = Field(default=50, ge=1, le=100, description="Number of records to return")
    user_id: Optional[UUID] = Field(default=None, description="Filter by user ID")
    action: Optional[str] = Field(default=None, description="Filter by action (e.g., 'create', 'update', 'delete')")
    resource_type: Optional[str] = Field(default=None, description="Filter by resource type (e.g., 'users', 'roles', 'groups')")
    resource_id: Optional[UUID] = Field(default=None, description="Filter by resource ID")
    start_date: Optional[datetime] = Field(default=None, description="Filter logs from this date onwards")
    end_date: Optional[datetime] = Field(default=None, description="Filter logs up to this date")
    search: Optional[str] = Field(default=None, description="Full-text search in details JSON")
    status: Optional[str] = Field(default=None, description="Filter by status: 'success' or 'failure'")

