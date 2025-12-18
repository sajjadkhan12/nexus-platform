"""
Schemas for microservice provisioning
"""
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class MicroserviceProvisionRequest(BaseModel):
    """Simplified schema for microservice provisioning"""
    plugin_id: str
    version: str
    deployment_name: str  # Only required input for microservices


class CICDStatusResponse(BaseModel):
    """Schema for CI/CD status response"""
    ci_cd_status: Optional[str] = None  # pending, running, success, failed, cancelled
    ci_cd_run_id: Optional[int] = None
    ci_cd_run_url: Optional[str] = None
    message: Optional[str] = None
    error: Optional[str] = None


class RepositoryInfoResponse(BaseModel):
    """Schema for repository information response"""
    full_name: str
    name: str
    clone_url: str
    ssh_url: str
    html_url: str
    default_branch: str
    private: bool
    description: Optional[str] = None
    created_at: str
    updated_at: str

