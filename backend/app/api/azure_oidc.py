"""
Azure Federated Identity Credential Endpoint

This module implements the Azure Federated Identity Credential flow.
It generates OIDC tokens and exchanges them for Azure ARM access tokens.
"""

import httpx
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel
from typing import Optional
from app.core.oidc import oidc_provider
from app.config import settings
from app.api.deps import get_current_user
from app.models.rbac import User

router = APIRouter()


class AzureTokenRequest(BaseModel):
    """Request model for Azure token exchange"""
    scope: str = "https://management.azure.com/.default"  # Azure ARM scope
    resource: Optional[str] = None  # Optional resource override


class AzureTokenResponse(BaseModel):
    """Response model for Azure token exchange"""
    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    resource: str


@router.post("/azure/token", response_model=AzureTokenResponse)
async def exchange_azure_token(
    request: AzureTokenRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Exchange OIDC token for Azure access token using Federated Identity Credential.
    
    This endpoint:
    1. Creates an OIDC token for the user
    2. Exchanges it with Azure AD using the Federated Identity Credential flow
    3. Produces a short-lived Azure ARM access token using the "client_assertion" OAuth flow
    
    The user must have already configured:
    - An Azure AD App Registration
    - A Federated Identity Credential that trusts this OIDC issuer
    - The credential must match the subject (sub) claim from the OIDC token
    
    Args:
        request: AzureTokenRequest with scope and optional resource
        current_user: Authenticated user (from JWT token)
    
    Returns:
        AzureTokenResponse with access token
    
    Example Azure Federated Identity Credential Configuration:
    - Subject: The user ID that will be in the OIDC token's "sub" claim
    - Issuer: Your OIDC issuer URL (from OIDC_ISSUER in .env)
    - Audiences: api://AzureADTokenExchange (or your custom audience)
    - Name: Any descriptive name for the credential
    """
    # Validate Azure configuration
    if not settings.AZURE_TENANT_ID or not settings.AZURE_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Azure Tenant ID and Client ID must be configured"
        )
    
    # Generate OIDC token for the user
    # Azure expects a specific audience, typically "api://AzureADTokenExchange"
    # or the App ID URI of the app registration
    azure_audience = f"api://{settings.AZURE_CLIENT_ID}"
    
    oidc_token = oidc_provider.create_oidc_token(
        subject=str(current_user.id),
        audience=azure_audience,
        expires_in=3600  # 1 hour
    )
    
    # Build Azure token endpoint URL
    token_endpoint = settings.AZURE_TOKEN_ENDPOINT.format(
        tenant_id=settings.AZURE_TENANT_ID
    )
    
    # Prepare the token request using client_assertion flow
    # This is the OAuth 2.0 client credentials flow with federated identity
    token_request_data = {
        "client_id": settings.AZURE_CLIENT_ID,
        "scope": request.scope,
        "client_assertion_type": "urn:ietf:params:oauth:client-assertion-type:jwt-bearer",
        "client_assertion": oidc_token,
        "grant_type": "client_credentials"
    }
    
    # Exchange token with Azure AD
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                token_endpoint,
                data=token_request_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=30.0
            )
            
            if response.status_code != 200:
                error_detail = response.text
                try:
                    error_json = response.json()
                    error_description = error_json.get("error_description", error_detail)
                    error_code = error_json.get("error", "unknown_error")
                except:
                    error_description = error_detail
                    error_code = "http_error"
                
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Azure AD error ({error_code}): {error_description}"
                )
            
            token_response = response.json()
            access_token = token_response.get("access_token")
            
            if not access_token:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Azure AD did not return an access token"
                )
            
            expires_in = token_response.get("expires_in", 3600)
            token_type = token_response.get("token_type", "Bearer")
            
            # Extract resource from scope if not provided
            resource = request.resource or request.scope.replace("/.default", "")
            
            return AzureTokenResponse(
                access_token=access_token,
                token_type=token_type,
                expires_in=expires_in,
                resource=resource
            )
            
    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to communicate with Azure AD: {str(e)}"
        )

