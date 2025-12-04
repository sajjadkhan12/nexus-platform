from fastapi import APIRouter
from app.config import settings
from app.core.oidc import oidc_provider

router = APIRouter()

@router.get("/.well-known/openid-configuration")
def get_openid_configuration():
    """
    OIDC Discovery Endpoint
    Cloud providers use this to verify the issuer and find the JWKS URI.
    """
    return {
        "issuer": settings.OIDC_ISSUER,
        "jwks_uri": f"{settings.OIDC_ISSUER}/.well-known/jwks.json",
        "response_types_supported": ["id_token"],
        "subject_types_supported": ["public"],
        "id_token_signing_alg_values_supported": ["RS256"],
        "token_endpoint": f"{settings.OIDC_ISSUER}/oidc/token",
        "claims_supported": ["sub", "iss", "aud", "exp", "iat", "jti"]
    }

@router.get("/.well-known/jwks.json")
def get_jwks():
    """
    JSON Web Key Set Endpoint
    Returns public keys used to verify OIDC tokens.
    """
    return oidc_provider.get_jwks()

@router.post("/oidc/token")
def issue_token(subject: str = "test-user"):
    """
    Manual token issuance for testing.
    In production, this would be part of a proper OAuth2 flow.
    """
    # For testing purposes, we allow generating a token for a subject
    token = oidc_provider.create_oidc_token(
        subject=subject,
        audience="test-audience",
        expires_in=3600
    )
    return {
        "access_token": token,
        "token_type": "Bearer",
        "expires_in": 3600
    }
