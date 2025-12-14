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
    stack_name: Optional[str] = None
    cloud_provider: Optional[str] = None
    region: Optional[str] = None
    inputs: Optional[Dict[str, Any]] = None
    outputs: Optional[Dict[str, Any]] = None
    git_branch: Optional[str] = None

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
