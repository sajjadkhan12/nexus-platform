from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any, List
import httpx
from app.api.deps import get_current_user
from app.models.rbac import User
from app.services.cloud_integrations import CloudIntegrationService
from app.config import settings

router = APIRouter()

@router.post("/cloud/gcp/run-test")
async def gcp_run_test(
    current_user: User = Depends(get_current_user)
):
    """
    Test GCP integration.
    Checks if we can access the project info.
    """
    token_data = await CloudIntegrationService.get_gcp_access_token(
        user_id=str(current_user.id),
        service_account_email=current_user.gcp_service_account
    )
    access_token = token_data['access_token']
    
    async with httpx.AsyncClient() as client:
        # Get Project Info
        resp = await client.get(
            f"https://cloudresourcemanager.googleapis.com/v1/projects/{settings.GCP_PROJECT_ID}",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
            
        return resp.json()

@router.post("/cloud/gcp/projects/list")
async def list_gcp_projects(
    current_user: User = Depends(get_current_user)
):
    """List accessible GCP projects"""
    token_data = await CloudIntegrationService.get_gcp_access_token(
        user_id=str(current_user.id),
        service_account_email=current_user.gcp_service_account
    )
    access_token = token_data['access_token']
    
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://cloudresourcemanager.googleapis.com/v1/projects",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        return resp.json()

@router.post("/cloud/gcp/compute/list")
async def list_gcp_compute(
    current_user: User = Depends(get_current_user)
):
    """List Compute Engine instances in default zone"""
    token_data = await CloudIntegrationService.get_gcp_access_token(
        user_id=str(current_user.id),
        service_account_email=current_user.gcp_service_account
    )
    access_token = token_data['access_token']
    
    zone = "us-central1-a" # Default for example
    
    async with httpx.AsyncClient() as client:
        url = f"https://compute.googleapis.com/compute/v1/projects/{settings.GCP_PROJECT_ID}/zones/{zone}/instances"
        resp = await client.get(
            url,
            headers={"Authorization": f"Bearer {access_token}"}
        )
        return resp.json()
