"""
GCP Workload Identity Federation Endpoint

This module implements the GCP Workload Identity Federation flow.
It generates OIDC tokens and exchanges them for GCP access tokens.
"""

import httpx
import json
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel
from typing import Optional
from app.core.oidc import oidc_provider
from app.config import settings
from app.api.deps import get_current_user
from app.models.rbac import User

router = APIRouter()


class GCPTokenRequest(BaseModel):
    """Request model for GCP token exchange"""
    service_account_email: Optional[str] = None  # Override default service account
    scope: str = "https://www.googleapis.com/auth/cloud-platform"  # OAuth2 scope


class GCPTokenResponse(BaseModel):
    """Response model for GCP token exchange"""
    access_token: str
    token_type: str = "Bearer"
    expires_in: int


@router.post("/gcp/token", response_model=GCPTokenResponse)
async def exchange_gcp_token(
    request: GCPTokenRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Exchange OIDC token for GCP access token using Workload Identity Federation.
    
    This endpoint:
    1. Creates an OIDC token for the user
    2. Exchanges it with GCP STS via Workload Identity Federation API
    3. Produces short-lived GCP access tokens that impersonate a GCP Service Account
    
    The user must have already configured:
    - A Workload Identity Pool
    - A Workload Identity Provider that trusts this OIDC issuer
    - A Service Account with Workload Identity binding
    
    Args:
        request: GCPTokenRequest with optional service account email and scope
        current_user: Authenticated user (from JWT token)
    
    Returns:
        GCPTokenResponse with access token
    
    Example GCP Workload Identity Provider Configuration:
    - Pool ID: projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/POOL_ID
    - Provider ID: PROVIDER_ID
    - Issuer: Your OIDC issuer URL (from OIDC_ISSUER in .env)
    - Allowed audiences: sts.googleapis.com
    """
    # Determine service account to use
    service_account = request.service_account_email or settings.GCP_SERVICE_ACCOUNT_EMAIL
    if not service_account:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Service account email must be provided either in request or GCP_SERVICE_ACCOUNT_EMAIL environment variable"
        )
    
    # Check required GCP configuration
    if not settings.GCP_WORKLOAD_IDENTITY_POOL_ID or not settings.GCP_WORKLOAD_IDENTITY_PROVIDER_ID:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="GCP Workload Identity Pool and Provider IDs must be configured"
        )
    
    # Generate OIDC token for the user
    # GCP expects the audience to be "sts.googleapis.com"
    oidc_token = oidc_provider.create_oidc_token(
        subject=str(current_user.id),
        audience="sts.googleapis.com",
        expires_in=3600  # 1 hour
    )
    
    # Build the GCP STS token exchange request
    # Format: projects/{project_number}/locations/{location}/workloadIdentityPools/{pool_id}/providers/{provider_id}
    sts_resource_name = (
        f"projects/{settings.GCP_PROJECT_NUMBER}/locations/global/"
        f"workloadIdentityPools/{settings.GCP_WORKLOAD_IDENTITY_POOL_ID}/"
        f"providers/{settings.GCP_WORKLOAD_IDENTITY_PROVIDER_ID}"
    )
    
    # Prepare the token exchange request
    token_request = {
        "audience": f"//iam.googleapis.com/{sts_resource_name}",
        "grantType": "urn:ietf:params:oauth:grant-type:token-exchange",
        "requestedTokenType": "urn:ietf:params:oauth:token-type:access_token",
        "scope": request.scope,
        "subjectToken": oidc_token,
        "subjectTokenType": "urn:ietf:params:oauth:token-type:jwt"
    }
    
    # Exchange token with GCP STS
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                settings.GCP_STS_ENDPOINT,
                json=token_request,
                headers={"Content-Type": "application/json"},
                timeout=30.0
            )
            
            if response.status_code != 200:
                error_detail = response.text
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"GCP STS error: {error_detail}"
                )
            
            sts_response = response.json()
            access_token = sts_response.get("access_token")
            
            if not access_token:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="GCP STS did not return an access token"
                )
            
            expires_in = sts_response.get("expires_in", 3600)
            
    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to communicate with GCP STS: {str(e)}"
        )
    
    # Now impersonate the service account to get final access token
    # This step uses the token from STS to impersonate the service account
    try:
        impersonate_url = (
            f"https://iamcredentials.googleapis.com/v1/"
            f"projects/-/serviceAccounts/{service_account}:generateAccessToken"
        )
        
        impersonate_request = {
            "scope": [request.scope]
        }
        
        async with httpx.AsyncClient() as client:
            impersonate_response = await client.post(
                impersonate_url,
                json=impersonate_request,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json"
                },
                timeout=30.0
            )
            
            if impersonate_response.status_code != 200:
                error_detail = impersonate_response.text
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"GCP Service Account impersonation error: {error_detail}"
                )
            
            impersonate_data = impersonate_response.json()
            final_access_token = impersonate_data.get("accessToken")
            expire_time = impersonate_data.get("expireTime")
            
            if not final_access_token:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="GCP did not return an access token from service account impersonation"
                )
            
            # Calculate expires_in from expireTime
            # expireTime is in RFC3339 format
            from datetime import datetime
            if expire_time:
                expire_dt = datetime.fromisoformat(expire_time.replace('Z', '+00:00'))
                now = datetime.utcnow().replace(tzinfo=expire_dt.tzinfo)
                expires_in = int((expire_dt - now).total_seconds())
            else:
                expires_in = 3600
            
            return GCPTokenResponse(
                access_token=final_access_token,
                token_type="Bearer",
                expires_in=expires_in
            )
            
    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to impersonate service account: {str(e)}"
        )

