import boto3
import json
import time
import httpx
import logging
from botocore.exceptions import ClientError
from app.config import settings
from app.core.redis_client import RedisClient
from app.core.oidc import oidc_provider
from fastapi import HTTPException
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class CloudIntegrationService:
    """
    Service to handle Cloud Provider integrations using Workload Identity Federation.
    Handles token exchange and Redis caching.
    """

    @staticmethod
    async def get_aws_credentials(
        user_id: str, 
        role_arn: Optional[str] = None, 
        duration_seconds: int = 3600
    ) -> Dict[str, Any]:
        """
        Get AWS temporary credentials.
        """
        target_role_arn = role_arn or settings.AWS_ROLE_ARN
        
        if not target_role_arn:
            # Fallback or error
            raise HTTPException(status_code=400, detail="AWS Role ARN not configured")
            
        cache_key = f"aws_creds:{user_id}:{target_role_arn}"
        cached = await RedisClient.get_json(cache_key)
        
        if cached:
            expiration = cached.get("expiration_ts")
            if expiration and time.time() < expiration - 300:
                return cached

        oidc_token = oidc_provider.create_oidc_token(
            subject=user_id,
            audience="sts.amazonaws.com",
            expires_in=duration_seconds + 300
        )

        try:
            # Note: In production, run this blocking call in a threadpool
            sts = boto3.client('sts', region_name=settings.AWS_REGION)
            
            response = sts.assume_role_with_web_identity(
                RoleArn=target_role_arn,
                RoleSessionName=f"devplatform-{user_id}",
                WebIdentityToken=oidc_token,
                DurationSeconds=duration_seconds
            )
            
            creds = response['Credentials']
            expiration_ts = creds['Expiration'].timestamp()
            
            result = {
                "access_key_id": creds['AccessKeyId'],
                "secret_access_key": creds['SecretAccessKey'],
                "session_token": creds['SessionToken'],
                "expiration_ts": expiration_ts,
                "region": settings.AWS_REGION,
                "aws_access_key_id": creds['AccessKeyId'], # For compatibility
                "aws_secret_access_key": creds['SecretAccessKey'],
                "aws_session_token": creds['SessionToken'],
                "aws_region": settings.AWS_REGION
            }
            
            ttl = int(expiration_ts - time.time())
            if ttl > 0:
                await RedisClient.set_json(cache_key, result, expire=ttl)
                
            return result

        except ClientError as e:
            raise HTTPException(status_code=500, detail=f"AWS STS Error: {str(e)}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"AWS Integration Error: {str(e)}")

    @staticmethod
    async def get_gcp_access_token(
        user_id: str, 
        service_account_email: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get GCP Access Token via Workload Identity Federation.
        """
        target_sa_email = service_account_email or settings.GCP_SERVICE_ACCOUNT_EMAIL
        
        cache_key = f"gcp_token:{user_id}:{target_sa_email}"
        cached = await RedisClient.get_json(cache_key)
        
        if cached:
            if time.time() < cached.get("expiration_ts", 0) - 60:
                return cached

        # Validate GCP configuration
        if not settings.GCP_PROJECT_NUMBER or not settings.GCP_PROJECT_ID:
             raise HTTPException(status_code=500, detail="GCP configuration missing (PROJECT_NUMBER and PROJECT_ID required)")
        
        if not settings.GCP_WORKLOAD_IDENTITY_POOL_ID or not settings.GCP_WORKLOAD_IDENTITY_PROVIDER_ID:
            raise HTTPException(status_code=500, detail="GCP Workload Identity configuration missing (WORKLOAD_IDENTITY_POOL_ID and WORKLOAD_IDENTITY_PROVIDER_ID required)")
        
        if not settings.OIDC_ISSUER:
            raise HTTPException(status_code=500, detail="OIDC_ISSUER not configured. This is required for GCP Workload Identity Federation.")

        # Use PROJECT_NUMBER for audience (required by GCP Workload Identity)
        audience = f"//iam.googleapis.com/projects/{settings.GCP_PROJECT_NUMBER}/locations/global/workloadIdentityPools/{settings.GCP_WORKLOAD_IDENTITY_POOL_ID}/providers/{settings.GCP_WORKLOAD_IDENTITY_PROVIDER_ID}"
        
        try:
            oidc_token = oidc_provider.create_oidc_token(
                subject=user_id,
                audience=audience, 
                expires_in=3600
            )
            
            # Verify token was created correctly (decode to check issuer claim)
            try:
                import jwt
                decoded = jwt.decode(oidc_token, options={"verify_signature": False})
                token_issuer = decoded.get("iss")
                if token_issuer != settings.OIDC_ISSUER:
                    logger.warning(f"Token issuer mismatch: token has '{token_issuer}' but expected '{settings.OIDC_ISSUER}'")
            except Exception as decode_error:
                logger.warning(f"Could not decode token for verification: {decode_error}")
                
        except Exception as e:
            raise HTTPException(
                status_code=500, 
                detail=f"Failed to create OIDC token: {str(e)}. Check OIDC_ISSUER configuration: {settings.OIDC_ISSUER}"
            )

        async with httpx.AsyncClient(timeout=30.0) as client:
            sts_url = "https://sts.googleapis.com/v1/token"
            sts_payload = {
                "grant_type": "urn:ietf:params:oauth:grant-type:token-exchange",
                "audience": audience,
                "scope": "https://www.googleapis.com/auth/cloud-platform",
                "requested_token_type": "urn:ietf:params:oauth:token-type:access_token",
                "subject_token": oidc_token,
                "subject_token_type": "urn:ietf:params:oauth:token-type:jwt"
            }
            
            try:
                sts_resp = await client.post(sts_url, data=sts_payload)
            except httpx.RequestError as e:
                raise HTTPException(
                    status_code=500, 
                    detail=f"Failed to connect to GCP STS service: {str(e)}. Check network connectivity and GCP service availability."
                )
            
            if sts_resp.status_code != 200:
                error_detail = sts_resp.text
                error_code = None
                try:
                    error_json = sts_resp.json()
                    error_code = error_json.get("error")
                    error_detail = error_json.get("error_description", error_json.get("error", error_detail))
                except:
                    pass
                
                # Log full error for debugging
                logger.error(f"GCP STS Error Response: Status={sts_resp.status_code}, Error={error_code}, Detail={error_detail}")
                logger.error(f"Request payload audience: {audience}")
                logger.error(f"OIDC Issuer: {settings.OIDC_ISSUER}")
                logger.error(f"Token issuer claim should be: {settings.OIDC_ISSUER}")
                
                # Try to decode the token to verify issuer claim
                try:
                    import jwt
                    decoded = jwt.decode(oidc_token, options={"verify_signature": False})
                    logger.error(f"Token issuer claim: {decoded.get('iss')}")
                    logger.error(f"Token audience claim: {decoded.get('aud')}")
                    logger.error(f"Token subject claim: {decoded.get('sub')}")
                except Exception:
                    pass
                
                # Provide more helpful error messages
                if "invalid_grant" in error_detail.lower() and "issuer" in error_detail.lower():
                    raise HTTPException(
                        status_code=500,
                        detail=f"GCP STS Error: {error_detail}. "
                               f"This usually means: "
                               f"1) The OIDC issuer URL in GCP Workload Identity Pool doesn't match '{settings.OIDC_ISSUER}', "
                               f"2) GCP cannot reach the issuer URL from their servers (check firewall/DNS), "
                               f"3) The issuer URL changed but GCP wasn't updated. "
                               f"Verify in GCP Console: IAM & Admin > Workload Identity Pools > {settings.GCP_WORKLOAD_IDENTITY_POOL_ID} > {settings.GCP_WORKLOAD_IDENTITY_PROVIDER_ID} "
                               f"and ensure the issuer URL exactly matches: {settings.OIDC_ISSUER}"
                    )
                else:
                    raise HTTPException(
                        status_code=500,
                        detail=f"GCP STS Error ({error_code}): {error_detail}. "
                               f"Audience: {audience}, "
                               f"OIDC Issuer: {settings.OIDC_ISSUER}. "
                               f"Full response: {sts_resp.text[:500]}"
                    )
            
            federated_token = sts_resp.json()["access_token"]
            
            # Impersonate Service Account
            sa_url = f"https://iamcredentials.googleapis.com/v1/projects/-/serviceAccounts/{target_sa_email}:generateAccessToken"
            
            sa_resp = await client.post(
                sa_url,
                headers={"Authorization": f"Bearer {federated_token}"},
                json={
                    "scope": ["https://www.googleapis.com/auth/cloud-platform"],
                    "lifetime": "3600s"
                }
            )
            
            if sa_resp.status_code != 200:
                raise HTTPException(status_code=500, detail=f"GCP SA Impersonation Error: {sa_resp.text}")
                
            data = sa_resp.json()
            access_token = data["accessToken"]
            expiration_ts = time.time() + 3500 
            
            result = {
                "access_token": access_token,
                "token_type": "Bearer",
                "expiration_ts": expiration_ts,
                # For compatibility
                "type": "gcp_access_token",
                "expires_in": 3500
            }
            
            await RedisClient.set_json(cache_key, result, expire=3500)
            return result

    @staticmethod
    async def get_azure_token(user_id: str) -> Dict[str, Any]:
        """
        Get Azure Access Token via Federated Credential.
        """
        cache_key = f"azure_token:{user_id}"
        cached = await RedisClient.get_json(cache_key)
        
        if cached:
            if time.time() < cached.get("expiration_ts", 0) - 60:
                return cached

        audience = "api://AzureADTokenExchange"
        
        oidc_token = oidc_provider.create_oidc_token(
            subject=user_id,
            audience=audience,
            expires_in=3600
        )

        async with httpx.AsyncClient() as client:
            tenant_id = settings.AZURE_TENANT_ID
            client_id = settings.AZURE_CLIENT_ID
            scope = "https://management.azure.com/.default"
            
            token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
            
            data = {
                "client_id": client_id,
                "scope": scope,
                "client_assertion_type": "urn:ietf:params:oauth:client-assertion-type:jwt-bearer",
                "client_assertion": oidc_token,
                "grant_type": "client_credentials"
            }
            
            resp = await client.post(token_url, data=data)
            
            if resp.status_code != 200:
                raise HTTPException(status_code=500, detail=f"Azure Token Error: {resp.text}")
                
            token_data = resp.json()
            access_token = token_data["access_token"]
            expires_in = int(token_data.get("expires_in", 3600))
            
            expiration_ts = time.time() + expires_in
            
            result = {
                "access_token": access_token,
                "token_type": "Bearer",
                "expiration_ts": expiration_ts,
                # For compatibility
                "azure_access_token": access_token,
                "azure_client_id": client_id,
                "azure_tenant_id": tenant_id
            }
            
            await RedisClient.set_json(cache_key, result, expire=expires_in)
            return result

cloud_service = CloudIntegrationService()
