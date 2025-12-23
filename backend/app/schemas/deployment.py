from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime
import uuid
from app.models.deployment import DeploymentStatus

class DeploymentTagSchema(BaseModel):
    """Schema for deployment tags"""
    key: str
    value: str
    
    class Config:
        from_attributes = True

class DeploymentBase(BaseModel):
    name: str
    status: str
    plugin_id: str
    version: str
    deployment_type: Optional[str] = "infrastructure"
    environment: str = "development"
    tags: List[DeploymentTagSchema] = []
    cost_center: Optional[str] = None
    project_code: Optional[str] = None
    stack_name: Optional[str] = None
    cloud_provider: Optional[str] = None
    region: Optional[str] = None
    inputs: Optional[Dict[str, Any]] = None
    outputs: Optional[Dict[str, Any]] = None
    git_branch: Optional[str] = None
    # Microservice fields
    github_repo_url: Optional[str] = None
    github_repo_name: Optional[str] = None
    ci_cd_status: Optional[str] = None
    ci_cd_run_id: Optional[int] = None
    ci_cd_run_url: Optional[str] = None
    ci_cd_updated_at: Optional[datetime] = None
    # Update tracking fields
    update_status: Optional[str] = None
    last_update_job_id: Optional[str] = None
    last_update_error: Optional[str] = None
    last_update_attempted_at: Optional[datetime] = None

class DeploymentCreate(DeploymentBase):
    pass

class DeploymentUpdate(BaseModel):
    name: Optional[str] = None
    status: Optional[str] = None
    inputs: Optional[Dict[str, Any]] = None
    outputs: Optional[Dict[str, Any]] = None

class DeploymentUpdateRequest(BaseModel):
    """Schema for updating deployment inputs"""
    inputs: Dict[str, Any]
    # Optional: allow updating other fields like tags, cost_center, etc.
    tags: Optional[Dict[str, str]] = None
    cost_center: Optional[str] = None
    project_code: Optional[str] = None

class DeploymentHistoryResponse(BaseModel):
    """Schema for deployment history entries"""
    id: uuid.UUID
    version_number: int
    inputs: Dict[str, Any]
    outputs: Optional[Dict[str, Any]] = None
    status: str
    job_id: Optional[str] = None
    created_at: datetime
    created_by: Optional[str] = None
    description: Optional[str] = None
    
    class Config:
        from_attributes = True

class DeploymentResponse(DeploymentBase):
    id: uuid.UUID
    user_id: uuid.UUID
    job_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    # Update tracking fields
    update_status: Optional[str] = None
    last_update_job_id: Optional[str] = None
    last_update_error: Optional[str] = None
    last_update_attempted_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True
