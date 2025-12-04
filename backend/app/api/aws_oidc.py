from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import boto3
from app.api.deps import get_current_user
from app.models.rbac import User
from app.services.cloud_integrations import CloudIntegrationService

router = APIRouter()

class AwsResourceRequest(BaseModel):
    region: str = "us-east-1"

@router.post("/cloud/aws/role-test")
async def aws_role_test(
    current_user: User = Depends(get_current_user)
):
    """
    Test AWS integration by getting CallerIdentity.
    Uses cached credentials from OIDC exchange.
    """
    # Note: Pass user_id and optional role_arn from user profile
    creds = await CloudIntegrationService.get_aws_credentials(
        user_id=str(current_user.id),
        role_arn=current_user.aws_role_arn
    )
    
    client = boto3.client(
        'sts',
        aws_access_key_id=creds['access_key_id'],
        aws_secret_access_key=creds['secret_access_key'],
        aws_session_token=creds['session_token'],
        region_name=creds['region']
    )
    
    response = client.get_caller_identity()
    return {
        "Arn": response['Arn'],
        "UserId": response['UserId'],
        "Account": response['Account']
    }

@router.post("/cloud/aws/s3/list")
async def list_s3_buckets(
    current_user: User = Depends(get_current_user)
):
    """List S3 buckets using assumed role"""
    creds = await CloudIntegrationService.get_aws_credentials(
        user_id=str(current_user.id),
        role_arn=current_user.aws_role_arn
    )
    
    client = boto3.client(
        's3',
        aws_access_key_id=creds['access_key_id'],
        aws_secret_access_key=creds['secret_access_key'],
        aws_session_token=creds['session_token'],
        region_name=creds['region']
    )
    
    response = client.list_buckets()
    return {"buckets": [b['Name'] for b in response.get('Buckets', [])]}

@router.post("/cloud/aws/ec2/instances")
async def list_ec2_instances(
    request: AwsResourceRequest,
    current_user: User = Depends(get_current_user)
):
    """List EC2 instances using assumed role"""
    creds = await CloudIntegrationService.get_aws_credentials(
        user_id=str(current_user.id),
        role_arn=current_user.aws_role_arn
    )
    
    client = boto3.client(
        'ec2',
        aws_access_key_id=creds['access_key_id'],
        aws_secret_access_key=creds['secret_access_key'],
        aws_session_token=creds['session_token'],
        region_name=request.region
    )
    
    response = client.describe_instances()
    instances = []
    for reservation in response['Reservations']:
        for instance in reservation['Instances']:
            instances.append({
                "id": instance['InstanceId'],
                "type": instance['InstanceType'],
                "state": instance['State']['Name']
            })
            
    return {"instances": instances}
