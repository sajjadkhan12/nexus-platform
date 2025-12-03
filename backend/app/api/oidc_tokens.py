from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from app.api.deps import get_current_user
from app.models.rbac import User
from app.services.cloud_integrations import CloudIntegrationService


router = APIRouter()


class AssumeRoleRequest(BaseModel):
    role_arn: Optional[str] = None
    role_session_name: Optional[str] = None  # Currently unused, reserved for future
    duration_seconds: int = 3600


class GCPTokenRequest(BaseModel):
    service_account_email: Optional[str] = None
    scope: Optional[str] = "https://www.googleapis.com/auth/cloud-platform"  # For future use


class AzureTokenRequest(BaseModel):
    scope: Optional[str] = "https://management.azure.com/.default"  # For future use
    resource: Optional[str] = "https://management.azure.com/"


@router.post("/aws/assume-role")
async def assume_aws_role(
    request: AssumeRoleRequest,
    current_user: User = Depends(get_current_user),
):
    """
    OIDC test endpoint: return AWS credentials via Workload Identity Federation.

    This powers the OIDC test page in the frontend.
    """
    creds = await CloudIntegrationService.get_aws_credentials(
        user_id=str(current_user.id),
        role_arn=request.role_arn or current_user.aws_role_arn,
        duration_seconds=request.duration_seconds,
    )

    expiration_ts = creds.get("expiration_ts")
    expiration_iso = (
        datetime.utcfromtimestamp(expiration_ts).isoformat() + "Z"
        if expiration_ts
        else ""
    )

    return {
        "access_key_id": creds["access_key_id"],
        "secret_access_key": creds["secret_access_key"],
        "session_token": creds["session_token"],
        "expiration": expiration_iso,
        "region": creds.get("region") or creds.get("aws_region"),
    }


@router.post("/gcp/token")
async def get_gcp_token(
    request: GCPTokenRequest,
    current_user: User = Depends(get_current_user),
):
    """
    OIDC test endpoint: return GCP access token via Workload Identity Federation.
    """
    token_data = await CloudIntegrationService.get_gcp_access_token(
        user_id=str(current_user.id),
        service_account_email=request.service_account_email
        or current_user.gcp_service_account,
    )

    # CloudIntegrationService already returns these fields
    return {
        "access_token": token_data["access_token"],
        "token_type": token_data.get("token_type", "Bearer"),
        "expires_in": int(token_data.get("expires_in", 3500)),
    }


@router.post("/azure/token")
async def get_azure_token(
    request: AzureTokenRequest,
    current_user: User = Depends(get_current_user),
):
    """
    OIDC test endpoint: return Azure access token using Federated Identity Credential.
    """
    token_data = await CloudIntegrationService.get_azure_token(str(current_user.id))

    expiration_ts = token_data.get("expiration_ts")
    expires_in = int(expiration_ts - datetime.utcnow().timestamp()) if expiration_ts else 3600

    return {
        "access_token": token_data["access_token"],
        "token_type": token_data.get("token_type", "Bearer"),
        "expires_in": expires_in,
        "resource": request.resource or "https://management.azure.com/",
    }


