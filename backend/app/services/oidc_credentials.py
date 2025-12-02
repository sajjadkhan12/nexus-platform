"""
OIDC Credential Exchange Service

This service automatically exchanges OIDC tokens for cloud provider credentials
when deploying resources. It's used internally by the provisioning system.
"""

import boto3
from botocore.exceptions import ClientError
from typing import Dict, Optional
import httpx
from app.core.oidc import oidc_provider
from app.config import settings
import logging

logger = logging.getLogger(__name__)


class OIDCCredentialService:
    """Service for automatically exchanging OIDC tokens for cloud credentials"""
    
    def get_aws_credentials(
        self,
        user_id: str,
        role_arn: Optional[str] = None,
        role_session_name: Optional[str] = None,
        duration_seconds: int = 3600
    ) -> Dict[str, str]:
        """
        Automatically exchange OIDC token for AWS credentials.
        
        This is used internally by the provisioning system when deploying
        AWS resources. It generates an OIDC token for the user and exchanges
        it for temporary AWS credentials.
        
        Args:
            user_id: The ID of the user requesting the credentials
            role_arn: AWS IAM Role ARN to assume (defaults to AWS_ROLE_ARN from config)
            role_session_name: Session name for the assumed role
            duration_seconds: Duration of the credentials (default 1 hour)
        
        Returns:
            Dictionary with AWS credentials:
            {
                "aws_access_key_id": "...",
                "aws_secret_access_key": "...",
                "aws_session_token": "...",
                "aws_region": "us-east-1"
            }
        
        Raises:
            Exception: If credential exchange fails
        """
        # Determine role ARN to use
        role_arn = role_arn or settings.AWS_ROLE_ARN
        if not role_arn:
            raise ValueError(
                "AWS_ROLE_ARN must be configured in .env file or provided as parameter. "
                "This is required for automatic AWS credential exchange."
            )
        
        # Generate OIDC token for the user
        oidc_token = oidc_provider.create_oidc_token(
            subject=str(user_id),
            audience="sts.amazonaws.com",
            expires_in=duration_seconds + 300  # Token expires 5 min after session
        )
        
        logger.info(f"Exchanging OIDC token for AWS credentials (user_id={user_id}, role={role_arn})")
        
        # Create STS client
        sts_client = boto3.client('sts')
        
        # Assume role with web identity
        try:
            role_session_name = role_session_name or f"devplatform-{user_id[:8]}"
            
            response = sts_client.assume_role_with_web_identity(
                RoleArn=role_arn,
                RoleSessionName=role_session_name,
                WebIdentityToken=oidc_token,
                DurationSeconds=duration_seconds
            )
            
            credentials = response['Credentials']
            
            # Return in format expected by PulumiService
            return {
                "aws_access_key_id": credentials['AccessKeyId'],
                "aws_secret_access_key": credentials['SecretAccessKey'],
                "aws_session_token": credentials['SessionToken'],
                "aws_region": "us-east-1"  # Default region, can be overridden
            }
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            error_message = e.response.get('Error', {}).get('Message', str(e))
            
            logger.error(f"AWS STS ClientError: {error_code} - {error_message}")
            logger.error(f"Full Response: {e.response}")
            
            raise Exception(f"AWS credential exchange failed: {error_code} - {error_message}")
        except Exception as e:
            logger.error(f"Failed to exchange OIDC token for AWS credentials: {str(e)}")
            raise
    
    def get_gcp_credentials(
        self,
        user_id: str,
        service_account_email: Optional[str] = None,
        scope: str = "https://www.googleapis.com/auth/cloud-platform"
    ) -> Dict[str, str]:
        """
        Automatically exchange OIDC token for GCP access token.
        
        Args:
            user_id: The ID of the user requesting the credentials
            service_account_email: Service account to impersonate (defaults to config)
            scope: OAuth2 scope for the token
        
        Returns:
            Dictionary with GCP credentials:
            {
                "type": "service_account",
                "project_id": "...",
                "private_key_id": "...",
                "private_key": "...",
                "client_email": "...",
                "client_id": "...",
                "auth_uri": "...",
                "token_uri": "...",
                "access_token": "..."
            }
        
        Raises:
            Exception: If credential exchange fails
        """
        # Determine service account to use
        service_account = service_account_email or settings.GCP_SERVICE_ACCOUNT_EMAIL
        if not service_account:
            raise ValueError(
                "GCP_SERVICE_ACCOUNT_EMAIL must be configured in .env file. "
                "This is required for automatic GCP credential exchange."
            )
        
        # Check required GCP configuration
        if not settings.GCP_WORKLOAD_IDENTITY_POOL_ID or not settings.GCP_WORKLOAD_IDENTITY_PROVIDER_ID:
            raise ValueError(
                "GCP_WORKLOAD_IDENTITY_POOL_ID and GCP_WORKLOAD_IDENTITY_PROVIDER_ID "
                "must be configured in .env file."
            )
        
        # Generate OIDC token for the user
        oidc_token = oidc_provider.create_oidc_token(
            subject=str(user_id),
            audience="sts.googleapis.com",
            expires_in=3600
        )
        
        logger.info(f"Exchanging OIDC token for GCP credentials (user_id={user_id})")
        
        # Build token request for GCP STS
        token_request = {
            "audience": f"//iam.googleapis.com/projects/{settings.GCP_PROJECT_NUMBER}/locations/global/workloadIdentityPools/{settings.GCP_WORKLOAD_IDENTITY_POOL_ID}/providers/{settings.GCP_WORKLOAD_IDENTITY_PROVIDER_ID}",
            "grantType": "urn:ietf:params:oauth:grant-type:token-exchange",
            "requestedTokenType": "urn:ietf:params:oauth:token-type:access_token",
            "scope": scope,
            "subjectToken": oidc_token,
            "subjectTokenType": "urn:ietf:params:oauth:token-type:jwt"
        }
        
        # Exchange token with GCP STS
        try:
            with httpx.Client() as client:
                response = client.post(
                    settings.GCP_STS_ENDPOINT,
                    json=token_request,
                    headers={"Content-Type": "application/json"},
                    timeout=30.0
                )
                
                if response.status_code != 200:
                    error_detail = response.text
                    raise Exception(f"GCP STS error: {error_detail}")
                
                sts_response = response.json()
                access_token = sts_response.get("access_token")
                
                if not access_token:
                    raise Exception("GCP STS did not return an access token")
                
                # Return in format expected by PulumiService
                # Note: GCP typically uses service account JSON, but for simplicity
                # we'll return the access token. The PulumiService will need to handle this.
                return {
                    "type": "gcp_access_token",
                    "access_token": access_token,
                    "token_type": "Bearer",
                    "expires_in": sts_response.get("expires_in", 3600)
                }
                
        except httpx.HTTPError as e:
            logger.error(f"Failed to communicate with GCP STS: {str(e)}")
            raise Exception(f"GCP credential exchange failed: {str(e)}")
    
    def get_azure_credentials(
        self,
        user_id: str,
        scope: str = "https://management.azure.com/.default"
    ) -> Dict[str, str]:
        """
        Automatically exchange OIDC token for Azure access token.
        
        Args:
            user_id: The ID of the user requesting the credentials
            scope: OAuth2 scope for the token
        
        Returns:
            Dictionary with Azure credentials:
            {
                "azure_client_id": "...",
                "azure_access_token": "...",
                "azure_tenant_id": "...",
                "azure_subscription_id": "..."  # Must be configured separately
            }
        
        Raises:
            Exception: If credential exchange fails
        """
        if not settings.AZURE_TENANT_ID or not settings.AZURE_CLIENT_ID:
            raise ValueError(
                "AZURE_TENANT_ID and AZURE_CLIENT_ID must be configured in .env file. "
                "This is required for automatic Azure credential exchange."
            )
        
        # Generate OIDC token for the user
        oidc_token = oidc_provider.create_oidc_token(
            subject=str(user_id),
            audience=settings.AZURE_CLIENT_ID,
            expires_in=3600
        )
        
        logger.info(f"Exchanging OIDC token for Azure credentials (user_id={user_id})")
        
        # Build Azure token endpoint URL
        token_endpoint = settings.AZURE_TOKEN_ENDPOINT.format(
            tenant_id=settings.AZURE_TENANT_ID
        )
        
        # Prepare the token request
        token_request_data = {
            "client_id": settings.AZURE_CLIENT_ID,
            "scope": scope,
            "client_assertion_type": "urn:ietf:params:oauth:client-assertion-type:jwt-bearer",
            "client_assertion": oidc_token,
            "grant_type": "client_credentials"
        }
        
        # Exchange token with Azure AD
        try:
            with httpx.Client() as client:
                response = client.post(
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
                    
                    raise Exception(f"Azure AD error ({error_code}): {error_description}")
                
                token_response = response.json()
                access_token = token_response.get("access_token")
                
                if not access_token:
                    raise Exception("Azure AD did not return an access token")
                
                # Return in format expected by PulumiService
                return {
                    "azure_client_id": settings.AZURE_CLIENT_ID,
                    "azure_access_token": access_token,
                    "azure_tenant_id": settings.AZURE_TENANT_ID,
                    "azure_subscription_id": getattr(settings, "AZURE_SUBSCRIPTION_ID", "")
                }
                
        except httpx.HTTPError as e:
            logger.error(f"Failed to communicate with Azure AD: {str(e)}")
            raise Exception(f"Azure credential exchange failed: {str(e)}")


# Singleton instance
oidc_credential_service = OIDCCredentialService()

