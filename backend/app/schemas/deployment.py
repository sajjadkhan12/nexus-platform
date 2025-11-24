from pydantic import BaseModel
from typing import Optional, Dict
from datetime import datetime
import uuid


class DeploymentBase(BaseModel):
    service_id: str
    name: str
    provider: str
    region: str
    status: str
    configuration: Optional[Dict] = None
    cost_per_month: Optional[float] = None


class DeploymentCreate(DeploymentBase):
    pass


class DeploymentUpdate(BaseModel):
    name: Optional[str] = None
    status: Optional[str] = None
    configuration: Optional[Dict] = None
    cost_per_month: Optional[float] = None


class DeploymentResponse(DeploymentBase):
    id: uuid.UUID
    owner_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
