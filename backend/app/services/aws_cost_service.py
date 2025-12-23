"""
AWS Cost Estimation and Retrieval Service

This service provides cost estimation for AWS resources using AWS Pricing API
and fallback pricing estimates.
"""
import boto3
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from fastapi import HTTPException
from botocore.exceptions import ClientError

from app.config import settings
from app.services.cloud_integrations import CloudIntegrationService

logger = logging.getLogger(__name__)


class AWSCostService:
    """Service for AWS cost estimation and retrieval"""

    @staticmethod
    async def _get_aws_credentials(user_id: str) -> Dict[str, Any]:
        """Get AWS credentials for API calls"""
        try:
            credentials = await CloudIntegrationService.get_aws_credentials(user_id)
            return credentials
        except Exception as e:
            logger.error(f"Failed to get AWS credentials: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to authenticate with AWS: {str(e)}"
            )

    @staticmethod
    async def estimate_ec2_cost(
        instance_type: str,
        region: str,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Estimate EC2 instance cost using AWS Pricing API.
        
        Args:
            instance_type: EC2 instance type (e.g., 't3.micro', 'm5.large')
            region: AWS region (e.g., 'us-east-1')
            user_id: User ID for authentication (required)
        
        Returns:
            Dictionary with estimated monthly cost and breakdown
        """
        if not user_id:
            raise HTTPException(status_code=400, detail="user_id is required for cost estimation")

        try:
            # Get AWS credentials
            credentials = await AWSCostService._get_aws_credentials(user_id)
            
            # Create pricing client
            pricing_client = boto3.client(
                'pricing',
                region_name='us-east-1',  # Pricing API is only available in us-east-1
                aws_access_key_id=credentials.get('aws_access_key_id') or credentials.get('access_key_id'),
                aws_secret_access_key=credentials.get('aws_secret_access_key') or credentials.get('secret_access_key'),
                aws_session_token=credentials.get('aws_session_token') or credentials.get('session_token')
            )

            # Get product pricing
            # Service code for EC2 is 'AmazonEC2'
            response = pricing_client.get_products(
                ServiceCode='AmazonEC2',
                Filters=[
                    {'Type': 'TERM_MATCH', 'Field': 'instanceType', 'Value': instance_type},
                    {'Type': 'TERM_MATCH', 'Field': 'location', 'Value': AWSCostService._get_pricing_region(region)},
                    {'Type': 'TERM_MATCH', 'Field': 'tenancy', 'Value': 'Shared'},
                    {'Type': 'TERM_MATCH', 'Field': 'operatingSystem', 'Value': 'Linux'},
                    {'Type': 'TERM_MATCH', 'Field': 'preInstalledSw', 'Value': 'NA'},
                ],
                MaxResults=1
            )

            if response.get('PriceList'):
                # Parse pricing from JSON string
                import json
                price_data = json.loads(response['PriceList'][0])
                
                # Extract on-demand pricing
                terms = price_data.get('terms', {}).get('OnDemand', {})
                if terms:
                    price_dimensions = list(terms.values())[0].get('priceDimensions', {})
                    if price_dimensions:
                        price_per_hour = float(list(price_dimensions.values())[0]['pricePerUnit']['USD'])
                        monthly_cost = price_per_hour * 730  # 730 hours per month
                        
                        return {
                            "estimated_monthly_cost": round(monthly_cost, 2),
                            "hourly_cost": round(price_per_hour, 6),
                            "currency": "USD",
                            "instance_type": instance_type,
                            "region": region,
                            "breakdown": {
                                "compute": round(monthly_cost, 2)
                            },
                            "source": "aws_pricing_api"
                        }

            # Fallback if API call fails or no results
            return AWSCostService._estimate_ec2_cost_fallback(instance_type, region)

        except ClientError as e:
            logger.error(f"AWS Pricing API error: {str(e)}")
            return AWSCostService._estimate_ec2_cost_fallback(instance_type, region)
        except Exception as e:
            logger.error(f"Error estimating EC2 cost: {str(e)}")
            return AWSCostService._estimate_ec2_cost_fallback(instance_type, region)

    @staticmethod
    def _estimate_ec2_cost_fallback(instance_type: str, region: str) -> Dict[str, Any]:
        """
        Fallback cost estimation using approximate pricing.
        These are rough estimates based on typical AWS pricing.
        """
        # Approximate monthly costs (USD) for common instance types
        pricing_estimates = {
            "t3.micro": 7.30,      # ~$0.0104/hour
            "t3.small": 14.60,     # ~$0.0208/hour
            "t3.medium": 29.20,    # ~$0.0416/hour
            "t3.large": 58.40,     # ~$0.0832/hour
            "t3.xlarge": 116.80,   # ~$0.1664/hour
            "t3.2xlarge": 233.60,  # ~$0.3328/hour
            "m5.large": 70.08,     # ~$0.096/hour
            "m5.xlarge": 140.16,   # ~$0.192/hour
            "m5.2xlarge": 280.32,  # ~$0.384/hour
            "m5.4xlarge": 560.64,  # ~$0.768/hour
            "c5.large": 68.40,     # ~$0.085/hour
            "c5.xlarge": 136.80,   # ~$0.17/hour
            "c5.2xlarge": 273.60,  # ~$0.34/hour
            "c5.4xlarge": 547.20,  # ~$0.68/hour
        }

        base_cost = pricing_estimates.get(instance_type, 50.0)  # Default $50/month

        return {
            "estimated_monthly_cost": round(base_cost, 2),
            "hourly_cost": round(base_cost / 730, 6),
            "currency": "USD",
            "instance_type": instance_type,
            "region": region,
            "breakdown": {
                "compute": round(base_cost, 2)
            },
            "source": "fallback_estimate",
            "note": "Using fallback pricing. Enable AWS Pricing API access for accurate pricing."
        }

    @staticmethod
    def _get_pricing_region(region: str) -> str:
        """Convert AWS region to pricing API location format"""
        region_mapping = {
            "us-east-1": "US East (N. Virginia)",
            "us-east-2": "US East (Ohio)",
            "us-west-1": "US West (N. California)",
            "us-west-2": "US West (Oregon)",
            "eu-west-1": "EU (Ireland)",
            "eu-west-2": "EU (London)",
            "eu-central-1": "EU (Frankfurt)",
            "ap-southeast-1": "Asia Pacific (Singapore)",
            "ap-southeast-2": "Asia Pacific (Sydney)",
            "ap-northeast-1": "Asia Pacific (Tokyo)",
            "ap-south-1": "Asia Pacific (Mumbai)",
        }
        return region_mapping.get(region, "US East (N. Virginia)")

    @staticmethod
    async def estimate_ebs_cost(
        volume_size_gb: int,
        volume_type: str,
        region: str,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Estimate EBS volume cost.
        
        Args:
            volume_size_gb: Volume size in GB
            volume_type: Volume type (gp3, gp2, io1, io2, st1, sc1)
            region: AWS region
            user_id: User ID for authentication (optional)
        
        Returns:
            Dictionary with estimated monthly cost
        """
        # Approximate pricing per GB per month
        ebs_pricing = {
            "gp3": 0.08,      # $0.08/GB/month
            "gp2": 0.10,      # $0.10/GB/month
            "io1": 0.125,     # $0.125/GB/month
            "io2": 0.125,     # $0.125/GB/month
            "st1": 0.045,     # $0.045/GB/month
            "sc1": 0.025,     # $0.025/GB/month
        }

        price_per_gb = ebs_pricing.get(volume_type.lower(), 0.10)  # Default to gp2
        monthly_cost = volume_size_gb * price_per_gb

        return {
            "estimated_monthly_cost": round(monthly_cost, 2),
            "currency": "USD",
            "volume_size_gb": volume_size_gb,
            "volume_type": volume_type,
            "breakdown": {
                "storage": round(monthly_cost, 2)
            },
            "source": "fallback_estimate"
        }

    @staticmethod
    async def estimate_s3_cost(
        storage_class: str = "STANDARD",
        estimated_storage_gb: float = 10.0,
        region: str = "us-east-1",
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Estimate S3 bucket cost.
        
        Args:
            storage_class: S3 storage class (STANDARD, STANDARD_IA, GLACIER, etc.)
            estimated_storage_gb: Estimated storage in GB (default 10GB for estimation)
            region: AWS region
            user_id: User ID for authentication (optional)
        
        Returns:
            Dictionary with estimated monthly cost and breakdown
        """
        # S3 pricing per GB per month (approximate)
        s3_pricing = {
            "STANDARD": 0.023,           # $0.023/GB/month
            "STANDARD_IA": 0.0125,       # $0.0125/GB/month
            "ONEZONE_IA": 0.01,          # $0.01/GB/month
            "GLACIER": 0.004,            # $0.004/GB/month
            "DEEP_ARCHIVE": 0.00099,     # $0.00099/GB/month
            "INTELLIGENT_TIERING": 0.023, # $0.023/GB/month (varies)
        }
        
        # Operations pricing (requests)
        # PUT requests: ~$0.005 per 1,000 requests
        # GET requests: ~$0.0004 per 1,000 requests
        operations_cost = 0.01  # Estimate for typical operations
        
        price_per_gb = s3_pricing.get(storage_class.upper(), s3_pricing["STANDARD"])
        storage_cost = estimated_storage_gb * price_per_gb
        total_cost = storage_cost + operations_cost
        
        return {
            "estimated_monthly_cost": round(total_cost, 2),
            "currency": "USD",
            "breakdown": {
                "storage": round(storage_cost, 2),
                "operations": round(operations_cost, 2)
            },
            "storage_class": storage_class.upper(),
            "region": region,
            "estimated_storage_gb": estimated_storage_gb,
            "source": "fallback_estimate",
            "note": f"Based on {estimated_storage_gb}GB storage estimate. Actual costs depend on usage."
        }

    @staticmethod
    async def estimate_deployment_cost(
        deployment_inputs: Dict[str, Any],
        plugin_id: str,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Estimate total cost for an AWS deployment based on inputs.
        
        Args:
            deployment_inputs: Deployment input parameters
            plugin_id: Plugin ID to determine resource type
            user_id: User ID for authentication
        
        Returns:
            Dictionary with total estimated cost and breakdown
        """
        total_cost = 0.0
        breakdown = {}
        currency = "USD"

        # Handle AWS EC2 instance plugin
        if plugin_id == "aws-ec2-instance":
            instance_type = deployment_inputs.get("instance_type", "t3.micro")
            region = deployment_inputs.get("region", "us-east-1")

            ec2_cost = await AWSCostService.estimate_ec2_cost(
                instance_type=instance_type,
                region=region,
                user_id=user_id
            )
            total_cost += ec2_cost.get("estimated_monthly_cost", 0)
            breakdown["compute"] = ec2_cost.get("estimated_monthly_cost", 0)

            # Add EBS volume cost
            root_volume_size = deployment_inputs.get("root_volume_size", 20)
            root_volume_type = deployment_inputs.get("root_volume_type", "gp3")
            
            ebs_cost = await AWSCostService.estimate_ebs_cost(
                volume_size_gb=root_volume_size,
                volume_type=root_volume_type,
                region=region,
                user_id=user_id
            )
            total_cost += ebs_cost.get("estimated_monthly_cost", 0)
            breakdown["storage"] = ebs_cost.get("estimated_monthly_cost", 0)

        # Handle AWS S3 bucket plugin
        elif plugin_id == "aws-s3-bucket":
            storage_class = deployment_inputs.get("storage_class", "STANDARD")
            region = deployment_inputs.get("region", "us-east-1")
            
            # Estimate storage (default to 10GB for estimation)
            estimated_storage_gb = 10.0
            
            s3_cost = await AWSCostService.estimate_s3_cost(
                storage_class=storage_class,
                estimated_storage_gb=estimated_storage_gb,
                region=region,
                user_id=user_id
            )
            total_cost += s3_cost.get("estimated_monthly_cost", 0)
            breakdown["storage"] = s3_cost.get("breakdown", {}).get("storage", 0)
            breakdown["operations"] = s3_cost.get("breakdown", {}).get("operations", 0)

        return {
            "estimated_monthly_cost": round(total_cost, 2),
            "currency": currency,
            "breakdown": breakdown,
            "period": "month"
        }

    @staticmethod
    async def aggregate_costs_by_deployment(
        deployments: List[Dict[str, Any]],
        start_date: datetime,
        end_date: datetime,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Aggregate costs for multiple AWS deployments.
        
        Args:
            deployments: List of deployment dictionaries with cloud_provider='aws'
            start_date: Start date for cost period
            end_date: End date for cost period
            user_id: User ID for authentication
        
        Returns:
            Dictionary with aggregated costs
        """
        total_cost = 0.0
        deployment_costs = []

        for deployment in deployments:
            if deployment.get("cloud_provider", "").lower() != "aws":
                continue

            deployment_id = str(deployment.get("id", ""))
            inputs = deployment.get("inputs", {})
            plugin_id = deployment.get("plugin_id", "")

            try:
                cost_estimate = await AWSCostService.estimate_deployment_cost(
                    deployment_inputs=inputs,
                    plugin_id=plugin_id,
                    user_id=user_id
                )

                deployment_cost = cost_estimate.get("estimated_monthly_cost", 0)
                total_cost += deployment_cost

                deployment_costs.append({
                    "deployment_id": deployment_id,
                    "deployment_name": deployment.get("name", ""),
                    "estimated_cost": deployment_cost,
                    "currency": "USD"
                })
            except Exception as e:
                logger.warning(f"Failed to estimate cost for deployment {deployment_id}: {str(e)}")
                continue

        return {
            "total_cost": round(total_cost, 2),
            "currency": "USD",
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "deployment_count": len(deployment_costs),
            "deployments": deployment_costs
        }


# Create singleton instance
aws_cost_service = AWSCostService()

