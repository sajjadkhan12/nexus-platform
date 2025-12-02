"""
AWS Workload Identity Federation Endpoint

This module implements the AWS AssumeRoleWithWebIdentity flow.
It generates OIDC tokens and exchanges them for AWS credentials.
"""

import boto3
from botocore.exceptions import ClientError
from fastapi import APIRouter, HTTPException, status, Depends, Header
from pydantic import BaseModel
from typing import Optional
from app.core.oidc import oidc_provider
from app.config import settings
from app.api.deps import get_current_user
from app.models.rbac import User

router = APIRouter()


class AssumeRoleRequest(BaseModel):
    """Request model for AWS assume role"""
    role_arn: Optional[str] = None  # Override default role ARN if provided
    role_session_name: Optional[str] = None  # Custom session name
    duration_seconds: int = 3600  # Session duration (1 hour default)


class AssumeRoleResponse(BaseModel):
    """Response model for AWS assume role"""
    access_key_id: str
    secret_access_key: str
    session_token: str
    expiration: str
    region: str = "us-east-1"  # Default region


@router.post("/aws/assume-role", response_model=AssumeRoleResponse)
async def assume_role_with_web_identity(
    request: AssumeRoleRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Assume AWS IAM Role using Web Identity Federation.
    
    This endpoint:
    1. Validates the calling user (via JWT authentication)
    2. Generates an OIDC token for that user
    3. Calls AWS STS AssumeRoleWithWebIdentity
    4. Returns short-lived AWS credentials
    
    The user must have already configured an AWS IAM Role that trusts
    this OIDC provider. The role ARN can be provided in the request
    or configured via AWS_ROLE_ARN environment variable.
    
    Args:
        request: AssumeRoleRequest with optional role ARN and session name
        current_user: Authenticated user (from JWT token)
    
    Returns:
        AssumeRoleResponse with AWS credentials
    
    Example AWS IAM Role Trust Policy:
    {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "Federated": "arn:aws:iam::ACCOUNT_ID:oidc-provider/YOUR_OIDC_PROVIDER"
                },
                "Action": "sts:AssumeRoleWithWebIdentity",
                "Condition": {
                    "StringEquals": {
                        "YOUR_OIDC_PROVIDER:sub": "user-id-here",
                        "YOUR_OIDC_PROVIDER:aud": "sts.amazonaws.com"
                    }
                }
            }
        ]
    }
    """
    # Determine role ARN to use
    role_arn = request.role_arn or settings.AWS_ROLE_ARN
    if not role_arn:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role ARN must be provided either in request or AWS_ROLE_ARN environment variable"
        )
    
    # Generate OIDC token for the user
    # AWS expects the audience to be "sts.amazonaws.com"
    # Important: The issuer in the token must match the OIDC provider URL in AWS exactly
    # AWS normalizes provider URLs, so we need to ensure the issuer matches
    oidc_token = oidc_provider.create_oidc_token(
        subject=str(current_user.id),
        audience="sts.amazonaws.com",
        expires_in=request.duration_seconds + 300  # Token expires 5 min after session
    )
    
    # Debug: Log the issuer being used (remove in production)
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"OIDC Token Issuer: {settings.OIDC_ISSUER}")
    logger.info(f"User ID (sub): {current_user.id}")
    
    # Create STS client
    sts_client = boto3.client('sts')
    
    # Assume role with web identity
    try:
        role_session_name = request.role_session_name or f"devplatform-session-{current_user.id}"
        
        # Run blocking boto3 call in threadpool to avoid blocking the event loop
        # This is CRITICAL because AWS STS will call back to our /.well-known/openid-configuration
        # endpoint to verify the token. If the event loop is blocked here, that callback will timeout.
        from starlette.concurrency import run_in_threadpool
        
        response = await run_in_threadpool(
            sts_client.assume_role_with_web_identity,
            RoleArn=role_arn,
            RoleSessionName=role_session_name,
            WebIdentityToken=oidc_token,
            DurationSeconds=request.duration_seconds
        )
        
        credentials = response['Credentials']
        
        return AssumeRoleResponse(
            access_key_id=credentials['AccessKeyId'],
            secret_access_key=credentials['SecretAccessKey'],
            session_token=credentials['SessionToken'],
            expiration=credentials['Expiration'].isoformat(),
            region="us-east-1"  # You might want to make this configurable
        )
        
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        error_message = e.response.get('Error', {}).get('Message', str(e))
        
        # Log full error details for debugging
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"AWS STS ClientError: {error_code}")
        logger.error(f"Error Message: {error_message}")
        logger.error(f"Full Response: {e.response}")
        
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"AWS STS error: {error_code} - {error_message}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to assume role: {str(e)}"
        )

