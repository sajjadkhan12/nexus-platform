"""Pydantic schemas for Plugin API"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Dict, List
from uuid import UUID

class PluginCreate(BaseModel):
    """Schema for creating a plugin"""
    pass  # File upload handled separately

class PluginResponse(BaseModel):
    """Schema for plugin response"""
    id: str
    name: str
    description: Optional[str]
    author: Optional[str]
    category: Optional[str] = "service"
    cloud_provider: Optional[str] = "other"
    latest_version: Optional[str] = "0.0.0"
    icon: Optional[str] = None
    is_locked: bool = False
    has_access: bool = False  # Computed per user
    has_pending_request: bool = False  # True if user has a pending access request
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class PluginVersionResponse(BaseModel):
    """Schema for plugin version response"""
    id: int
    plugin_id: str
    version: str
    manifest: Dict
    created_at: datetime
    
    class Config:
        from_attributes = True

class CloudCredentialCreate(BaseModel):
    """Schema for creating cloud credentials"""
    name: str = Field(..., description="Credential name (e.g., 'prod-gcp')")
    provider: str = Field(..., description="Cloud provider: aws, gcp, azure, kubernetes")
    credentials: Dict = Field(..., description="Provider-specific credentials")
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "prod-gcp",
                "provider": "gcp",
                "credentials": {
                    "type": "service_account",
                    "project_id": "my-project",
                    "private_key": "...",
                    "client_email": "sa@project.iam.gserviceaccount.com"
                }
            }
        }

class CloudCredentialResponse(BaseModel):
    """Schema for cloud credential response (no secrets)"""
    id: int
    name: str
    provider: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class ProvisionRequest(BaseModel):
    """Schema for provisioning request"""
    plugin_id: str
    version: str
    inputs: Dict

class JobResponse(BaseModel):
    """Schema for job response"""
    id: str
    plugin_version_id: int
    deployment_id: Optional[UUID] = None
    status: str
    triggered_by: str
    inputs: Dict
    outputs: Optional[Dict]
    created_at: datetime
    finished_at: Optional[datetime]
    
    class Config:
        from_attributes = True

class JobLogResponse(BaseModel):
    """Schema for job log response"""
    id: int
    job_id: str
    timestamp: datetime
    level: str
    message: str
    
    class Config:
        from_attributes = True

class BulkDeleteJobsRequest(BaseModel):
    """Schema for bulk job deletion request"""
    job_ids: List[str] = Field(..., description="List of job IDs to delete", min_length=1)
    
    class Config:
        json_schema_extra = {
            "example": {
                "job_ids": ["job-id-1", "job-id-2", "job-id-3"]
            }
        }

class BulkDeleteJobsResponse(BaseModel):
    """Schema for bulk job deletion response"""
    deleted_count: int
    failed_count: int
    failed_job_ids: List[str] = []
    
    class Config:
        from_attributes = True

class PluginAccessRequestCreate(BaseModel):
    """Schema for creating an access request"""
    pass  # plugin_id comes from URL, user_id from current_user

class PluginAccessRequestResponse(BaseModel):
    """Schema for access request response"""
    id: UUID
    plugin_id: str
    plugin_name: Optional[str] = None  # Include plugin name for display
    user_id: UUID
    user_email: Optional[str] = None  # Include user email for display
    status: str
    requested_at: datetime
    reviewed_at: Optional[datetime]
    reviewed_by: Optional[UUID]
    
    class Config:
        from_attributes = True

class PluginAccessGrantRequest(BaseModel):
    """Schema for granting access to a user"""
    user_id: UUID = Field(..., description="User ID to grant access to")

class PluginAccessResponse(BaseModel):
    """Schema for plugin access response"""
    id: int
    plugin_id: str
    user_id: UUID
    granted_by: UUID
    granted_at: datetime
    
    class Config:
        from_attributes = True
