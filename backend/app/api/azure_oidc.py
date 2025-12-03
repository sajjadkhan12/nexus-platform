from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any
import httpx
from app.api.deps import get_current_user
from app.models.rbac import User
from app.services.cloud_integrations import CloudIntegrationService
from app.config import settings

router = APIRouter()

@router.post("/cloud/azure/run-test")
async def azure_run_test(
    current_user: User = Depends(get_current_user)
):
    """
    Test Azure integration.
    Tries to list subscriptions.
    """
    token_data = await CloudIntegrationService.get_azure_token(str(current_user.id))
    access_token = token_data['access_token']
    
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://management.azure.com/subscriptions?api-version=2020-01-01",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
            
        return resp.json()

@router.post("/cloud/azure/resource-groups")
async def list_azure_resource_groups(
    current_user: User = Depends(get_current_user)
):
    """List Resource Groups in the first subscription found"""
    token_data = await CloudIntegrationService.get_azure_token(str(current_user.id))
    access_token = token_data['access_token']
    
    async with httpx.AsyncClient() as client:
        # Get Subscription ID
        sub_resp = await client.get(
            "https://management.azure.com/subscriptions?api-version=2020-01-01",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        if sub_resp.status_code != 200:
             raise HTTPException(status_code=sub_resp.status_code, detail=sub_resp.text)
             
        subs = sub_resp.json().get('value', [])
        if not subs:
            return {"message": "No subscriptions found"}
            
        sub_id = subs[0]['subscriptionId']
        
        # List Resource Groups
        rg_resp = await client.get(
            f"https://management.azure.com/subscriptions/{sub_id}/resourcegroups?api-version=2021-04-01",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        return rg_resp.json()

@router.post("/cloud/azure/vms")
async def list_azure_vms(
    current_user: User = Depends(get_current_user)
):
    """List Virtual Machines in the first subscription found"""
    token_data = await CloudIntegrationService.get_azure_token(str(current_user.id))
    access_token = token_data['access_token']
    
    async with httpx.AsyncClient() as client:
        # Get Subscription ID
        sub_resp = await client.get(
            "https://management.azure.com/subscriptions?api-version=2020-01-01",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        if sub_resp.status_code != 200:
             raise HTTPException(status_code=sub_resp.status_code, detail=sub_resp.text)
             
        subs = sub_resp.json().get('value', [])
        if not subs:
            return {"message": "No subscriptions found"}
            
        sub_id = subs[0]['subscriptionId']
        
        # List VMs
        vm_resp = await client.get(
            f"https://management.azure.com/subscriptions/{sub_id}/providers/Microsoft.Compute/virtualMachines?api-version=2021-03-01",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        return vm_resp.json()
