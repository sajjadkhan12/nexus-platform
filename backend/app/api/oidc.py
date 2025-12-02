"""
OIDC Provider Endpoints

This module provides the JWKS endpoint and OIDC discovery endpoints
for cloud providers to verify tokens.
"""

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse
from app.core.oidc import oidc_provider
from app.config import settings

router = APIRouter()


# Add OPTIONS handler for CORS preflight (AWS might send this)
@router.options("/.well-known/jwks.json")
def jwks_options():
    """Handle CORS preflight for JWKS endpoint"""
    from fastapi.responses import Response
    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Max-Age": "3600"
        }
    )


@router.options("/.well-known/openid-configuration")
def oidc_config_options():
    """Handle CORS preflight for OIDC config endpoint"""
    from fastapi.responses import Response
    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Max-Age": "3600"
        }
    )


@router.get("/.well-known/jwks.json")
def get_jwks():
    """
    JWKS (JSON Web Key Set) endpoint.
    
    Cloud providers use this endpoint to retrieve the public keys
    needed to verify JWT tokens issued by this OIDC provider.
    
    AWS Requirements:
    - Must be publicly accessible (no authentication)
    - Must return valid JSON
    - Must include at least one key with matching kid from token header
    - Must use RS256 algorithm
    - Must respond quickly (< 5 seconds)
    - Must have proper Content-Type header
    
    Returns:
        JSON object containing the public keys in JWK format
    """
    # Get cached JWKS (fast, no computation)
    jwks = oidc_provider.get_jwks()
    
    # Return immediately with proper headers
    # AWS is very strict about response format and headers
    return JSONResponse(
        content=jwks,
        headers={
            "Content-Type": "application/json",  # AWS requires this exact format
            "Cache-Control": "public, max-age=3600",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "*",
            "X-Content-Type-Options": "nosniff"
        }
    )


@router.get("/.well-known/openid-configuration")
def get_openid_configuration():
    """
    OIDC Discovery endpoint.
    
    Provides metadata about the OIDC provider configuration.
    This is used by clients to discover the provider's capabilities.
    
    Must respond quickly for AWS compatibility.
    
    Note: Using synchronous function for maximum speed and compatibility
    with Cloudflare tunnel.
    
    Returns:
        OIDC configuration metadata
    """
    # Fast path - minimal checks, no database, no complex logic, no async overhead
    if not settings.OIDC_ISSUER:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="OIDC_ISSUER is not configured. Please set OIDC_ISSUER in your .env file."
        )
    
    base_url = settings.OIDC_ISSUER.rstrip('/')
    
    config = {
        "issuer": settings.OIDC_ISSUER,
        "jwks_uri": f"{base_url}/.well-known/jwks.json",
        "response_types_supported": ["id_token"],
        "subject_types_supported": ["public"],
        "id_token_signing_alg_values_supported": ["RS256"],
        "claims_supported": ["iss", "sub", "aud", "exp", "iat"]
    }
    
    return JSONResponse(
        content=config,
        headers={
            "Content-Type": "application/json",  # Simplified for AWS compatibility
            "Cache-Control": "public, max-age=3600",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "*",
            "X-Content-Type-Options": "nosniff"
        }
    )

