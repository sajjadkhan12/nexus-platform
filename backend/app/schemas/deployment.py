from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime
import uuid
from app.models.deployment import DeploymentStatus

class DeploymentBase(BaseModel):
    name: str
    status: str
    plugin_id: str
    version: str
    deployment_type: Optional[str] = "infrastructure"
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

class DeploymentCreate(DeploymentBase):
    pass

class DeploymentUpdate(BaseModel):
    name: Optional[str] = None
    status: Optional[str] = None
    inputs: Optional[Dict[str, Any]] = None
    outputs: Optional[Dict[str, Any]] = None

class DeploymentResponse(DeploymentBase):
    id: uuid.UUID
    user_id: uuid.UUID
    job_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
