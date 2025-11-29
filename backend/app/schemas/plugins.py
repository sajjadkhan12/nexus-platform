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
    credential_name: Optional[str] = None

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
