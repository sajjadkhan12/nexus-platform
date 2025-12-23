"""
GCP Cost Estimation and Retrieval Service

This service provides cost estimation and actual cost retrieval for GCP resources
using GCP Cloud Billing API and Cloud Billing Catalog API.
"""
import httpx
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from fastapi import HTTPException

from app.config import settings
from app.services.cloud_integrations import CloudIntegrationService

logger = logging.getLogger(__name__)


class GCPCostService:
    """Service for GCP cost estimation and retrieval"""

    # GCP API endpoints
    CLOUD_BILLING_API_BASE = "https://cloudbilling.googleapis.com/v1"
    CLOUD_BILLING_CATALOG_API = "https://cloudbilling.googleapis.com/v1/services"

    @staticmethod
    async def _get_access_token(user_id: str) -> str:
        """Get GCP access token for API calls"""
        try:
            credentials = await CloudIntegrationService.get_gcp_access_token(user_id)
            return credentials.get("access_token")
        except Exception as e:
            logger.error(f"Failed to get GCP access token: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to authenticate with GCP: {str(e)}"
            )

    @staticmethod
    async def estimate_vm_cost(
        machine_type: str,
        zone: str,
        project_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Estimate Compute Engine VM cost using GCP Pricing API.
        
        Args:
            machine_type: GCP machine type (e.g., 'e2-micro', 'n1-standard-1')
            zone: GCP zone (e.g., 'us-central1-a')
            project_id: GCP project ID (optional, uses config if not provided)
            user_id: User ID for authentication (required)
        
        Returns:
            Dictionary with estimated monthly cost and breakdown
        """
        if not user_id:
            raise HTTPException(status_code=400, detail="user_id is required for cost estimation")

        project_id = project_id or settings.GCP_PROJECT_ID
        if not project_id:
            raise HTTPException(
                status_code=400,
                detail="GCP_PROJECT_ID not configured"
            )

        access_token = await GCPCostService._get_access_token(user_id)

        # Extract region from zone (e.g., 'us-central1-a' -> 'us-central1')
        region = zone.rsplit('-', 1)[0] if '-' in zone else zone

        try:
            # Use Cloud Billing Catalog API to get pricing
            # Service ID for Compute Engine is '6F81-5844-456A'
            service_id = "6F81-5844-456A"
            catalog_url = f"{GCPCostService.CLOUD_BILLING_CATALOG_API}/{service_id}/skus"

            async with httpx.AsyncClient(timeout=30.0) as client:
                headers = {"Authorization": f"Bearer {access_token}"}
                
                # Search for VM pricing SKUs
                params = {
                    "filter": f'serviceRegions:"{region}" AND description:"{machine_type}"',
                    "pageSize": 10
                }
                
                response = await client.get(catalog_url, headers=headers, params=params)
                
                if response.status_code != 200:
                    logger.error(f"GCP Catalog API error: {response.status_code} - {response.text}")
                    # Fallback to estimated pricing based on machine type
                    return GCPCostService._estimate_vm_cost_fallback(machine_type, region)

                data = response.json()
                skus = data.get("skus", [])

                if not skus:
                    # Fallback if no SKUs found
                    return GCPCostService._estimate_vm_cost_fallback(machine_type, region)

                # Find the on-demand pricing SKU (usually has "On Demand" in description)
                vm_sku = None
                for sku in skus:
                    if "On Demand" in sku.get("description", "") or "Preemptible" not in sku.get("description", ""):
                        vm_sku = sku
                        break

                if not vm_sku:
                    vm_sku = skus[0]  # Use first SKU if no on-demand found

                # Extract pricing information
                pricing_info = vm_sku.get("pricingInfo", [])
                if not pricing_info:
                    return GCPCostService._estimate_vm_cost_fallback(machine_type, region)

                # Get the pricing expression
                pricing_expression = pricing_info[0].get("pricingExpression", {})
                unit_price = pricing_expression.get("unitPrice", {})
                
                # Calculate monthly cost (assuming 730 hours per month)
                # GCP pricing is typically per hour
                hourly_cost = float(unit_price.get("units", 0)) + (float(unit_price.get("nanos", 0)) / 1e9)
                monthly_cost = hourly_cost * 730

                return {
                    "estimated_monthly_cost": round(monthly_cost, 2),
                    "hourly_cost": round(hourly_cost, 6),
                    "currency": "USD",
                    "machine_type": machine_type,
                    "zone": zone,
                    "region": region,
                    "breakdown": {
                        "compute": round(monthly_cost, 2)
                    },
                    "source": "gcp_catalog_api"
                }

        except httpx.RequestError as e:
            logger.error(f"GCP API request error: {str(e)}")
            return GCPCostService._estimate_vm_cost_fallback(machine_type, region)
        except Exception as e:
            logger.error(f"Error estimating VM cost: {str(e)}")
            return GCPCostService._estimate_vm_cost_fallback(machine_type, region)

    @staticmethod
    def _estimate_vm_cost_fallback(machine_type: str, region: str) -> Dict[str, Any]:
        """
        Fallback cost estimation using approximate pricing.
        These are rough estimates based on typical GCP pricing.
        """
        # Approximate monthly costs (USD) for common machine types
        # These are rough estimates and should be replaced with actual API calls
        pricing_estimates = {
            "e2-micro": 7.30,      # ~$0.01/hour
            "e2-small": 14.60,     # ~$0.02/hour
            "e2-medium": 29.20,    # ~$0.04/hour
            "e2-standard-2": 58.40,  # ~$0.08/hour
            "e2-standard-4": 116.80, # ~$0.16/hour
            "n1-standard-1": 24.38,  # ~$0.033/hour
            "n1-standard-2": 48.76,  # ~$0.067/hour
            "n1-standard-4": 97.52,  # ~$0.134/hour
            "n1-standard-8": 195.04, # ~$0.267/hour
        }

        # Get base cost or use average
        base_cost = pricing_estimates.get(machine_type, 50.0)  # Default $50/month

        return {
            "estimated_monthly_cost": round(base_cost, 2),
            "hourly_cost": round(base_cost / 730, 6),
            "currency": "USD",
            "machine_type": machine_type,
            "region": region,
            "breakdown": {
                "compute": round(base_cost, 2)
            },
            "source": "fallback_estimate",
            "note": "Using fallback pricing. Enable GCP Billing Catalog API for accurate pricing."
        }

    @staticmethod
    async def estimate_disk_cost(
        disk_size_gb: int,
        disk_type: str,
        zone: str,
        project_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Estimate persistent disk cost.
        
        Args:
            disk_size_gb: Disk size in GB
            disk_type: Disk type (pd-standard, pd-ssd, pd-balanced, pd-extreme)
            zone: GCP zone
            project_id: GCP project ID (optional)
            user_id: User ID for authentication (required)
        
        Returns:
            Dictionary with estimated monthly cost
        """
        if not user_id:
            raise HTTPException(status_code=400, detail="user_id is required")

        # Approximate pricing per GB per month
        disk_pricing = {
            "pd-standard": 0.04,   # $0.04/GB/month
            "pd-ssd": 0.17,         # $0.17/GB/month
            "pd-balanced": 0.10,    # $0.10/GB/month
            "pd-extreme": 0.20,     # $0.20/GB/month
        }

        price_per_gb = disk_pricing.get(disk_type, 0.04)  # Default to standard
        monthly_cost = disk_size_gb * price_per_gb

        return {
            "estimated_monthly_cost": round(monthly_cost, 2),
            "currency": "USD",
            "disk_size_gb": disk_size_gb,
            "disk_type": disk_type,
            "breakdown": {
                "storage": round(monthly_cost, 2)
            },
            "source": "fallback_estimate"
        }

    @staticmethod
    async def get_actual_costs(
        project_id: str,
        start_date: datetime,
        end_date: datetime,
        user_id: str,
        billing_account_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get actual costs from GCP Cloud Billing API.
        
        Args:
            project_id: GCP project ID
            start_date: Start date for cost query
            end_date: End date for cost query
            user_id: User ID for authentication
            billing_account_id: Optional billing account ID
        
        Returns:
            Dictionary with actual costs and breakdown
        """
        access_token = await GCPCostService._get_access_token(user_id)

        # Use billing account ID from config if not provided
        billing_account_id = billing_account_id or settings.GCP_BILLING_ACCOUNT_ID

        if not billing_account_id:
            # Try to get billing account from project
            billing_account_id = await GCPCostService._get_billing_account_for_project(
                project_id, access_token
            )

        if not billing_account_id:
            raise HTTPException(
                status_code=400,
                detail="Billing account not configured. Set GCP_BILLING_ACCOUNT_ID or ensure project has billing enabled."
            )

        try:
            # Use Cloud Billing API to get costs
            # Format: projects/{project}/billingInfo
            # For cost data, we use the Cloud Billing Budget API or export to BigQuery
            # For simplicity, we'll use a simplified approach with the billing account

            # Note: GCP Cloud Billing API doesn't directly provide cost queries
            # We would typically use:
            # 1. Cloud Billing Export to BigQuery (requires setup)
            # 2. Cloud Billing Budget API (for budget alerts, not historical costs)
            # 3. Cloud Asset Inventory API (limited cost data)
            
            # For now, return a structure that indicates costs need to be retrieved
            # via BigQuery export or other means
            return {
                "total_cost": 0.0,
                "currency": "USD",
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "project_id": project_id,
                "billing_account_id": billing_account_id,
                "breakdown": {},
                "note": "Actual cost retrieval requires Cloud Billing Export to BigQuery. "
                       "This endpoint returns structure for future implementation."
            }

        except Exception as e:
            logger.error(f"Error retrieving actual costs: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to retrieve costs: {str(e)}"
            )

    @staticmethod
    async def _get_billing_account_for_project(
        project_id: str,
        access_token: str
    ) -> Optional[str]:
        """Get billing account ID for a project"""
        try:
            url = f"https://cloudbilling.googleapis.com/v1/projects/{project_id}/billingInfo"
            headers = {"Authorization": f"Bearer {access_token}"}

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)
                
                if response.status_code == 200:
                    data = response.json()
                    return data.get("billingAccountName", "").split("/")[-1] if data.get("billingAccountName") else None
                
                return None
        except Exception as e:
            logger.warning(f"Could not get billing account for project {project_id}: {str(e)}")
            return None

    @staticmethod
    async def estimate_bucket_cost(
        storage_class: str,
        location: str,
        estimated_storage_gb: float = 10.0,
        versioning_enabled: bool = False,
        project_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Estimate Cloud Storage bucket cost.
        
        Args:
            storage_class: Storage class (STANDARD, NEARLINE, COLDLINE, ARCHIVE)
            location: Bucket location (US, EU, ASIA, or specific region)
            estimated_storage_gb: Estimated storage in GB (default 10GB for estimation)
            versioning_enabled: Whether versioning is enabled (affects storage costs)
            project_id: GCP project ID (optional)
            user_id: User ID for authentication (optional, for API-based pricing)
        
        Returns:
            Dictionary with estimated monthly cost and breakdown
        """
        # GCP Cloud Storage pricing (per GB per month, approximate as of 2024)
        # These are base prices and may vary by region
        storage_pricing = {
            "STANDARD": 0.023,      # $0.023 per GB/month
            "NEARLINE": 0.010,      # $0.010 per GB/month
            "COLDLINE": 0.004,      # $0.004 per GB/month
            "ARCHIVE": 0.0012,      # $0.0012 per GB/month
        }
        
        # Operations pricing (Class A: $0.05 per 10,000 operations, Class B: $0.004 per 10,000)
        # Estimate: 1,000 Class A operations and 10,000 Class B operations per month (typical usage)
        operations_cost = 0.009  # ~$0.009/month for typical operations
        
        # Get base storage price
        price_per_gb = storage_pricing.get(storage_class.upper(), storage_pricing["STANDARD"])
        
        # Calculate storage cost
        storage_cost = estimated_storage_gb * price_per_gb
        
        # If versioning is enabled, assume 20% additional storage for versions
        if versioning_enabled:
            storage_cost *= 1.2
        
        # Minimum cost (even with 0 storage, there are minimal operations)
        total_cost = max(storage_cost + operations_cost, 0.01)  # Minimum $0.01/month
        
        return {
            "estimated_monthly_cost": round(total_cost, 2),
            "currency": "USD",
            "breakdown": {
                "storage": round(storage_cost, 2),
                "operations": round(operations_cost, 2)
            },
            "storage_class": storage_class.upper(),
            "location": location,
            "estimated_storage_gb": estimated_storage_gb,
            "versioning_enabled": versioning_enabled,
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
        Estimate total cost for a deployment based on inputs.
        
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

        # Handle GCP VM instance plugin
        if plugin_id == "gcp-vm-instance":
            machine_type = deployment_inputs.get("machine_type", "e2-micro")
            zone = deployment_inputs.get("zone", "us-central1-a")
            project_id = deployment_inputs.get("project_id")

            vm_cost = await GCPCostService.estimate_vm_cost(
                machine_type=machine_type,
                zone=zone,
                project_id=project_id,
                user_id=user_id
            )
            total_cost += vm_cost.get("estimated_monthly_cost", 0)
            breakdown["compute"] = vm_cost.get("estimated_monthly_cost", 0)

            # Add disk cost
            disk_size_gb = deployment_inputs.get("disk_size_gb", 20)
            disk_type = deployment_inputs.get("disk_type", "pd-standard")
            
            disk_cost = await GCPCostService.estimate_disk_cost(
                disk_size_gb=disk_size_gb,
                disk_type=disk_type,
                zone=zone,
                project_id=project_id,
                user_id=user_id
            )
            total_cost += disk_cost.get("estimated_monthly_cost", 0)
            breakdown["storage"] = disk_cost.get("estimated_monthly_cost", 0)

        # Handle GCP bucket plugin
        elif plugin_id == "gcp-bucket":
            storage_class = deployment_inputs.get("storage_class", "STANDARD")
            location = deployment_inputs.get("location", "US")
            versioning_enabled = deployment_inputs.get("versioning_enabled", False)
            project_id = deployment_inputs.get("project_id")
            
            # Estimate storage (default to 10GB for estimation, user can adjust)
            # In a real scenario, you might want to ask the user or use a default
            estimated_storage_gb = 10.0  # Default estimate
            
            bucket_cost = await GCPCostService.estimate_bucket_cost(
                storage_class=storage_class,
                location=location,
                estimated_storage_gb=estimated_storage_gb,
                versioning_enabled=versioning_enabled,
                project_id=project_id,
                user_id=user_id
            )
            total_cost += bucket_cost.get("estimated_monthly_cost", 0)
            breakdown["storage"] = bucket_cost.get("breakdown", {}).get("storage", 0)
            breakdown["operations"] = bucket_cost.get("breakdown", {}).get("operations", 0)

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
        Aggregate costs for multiple deployments.
        
        Args:
            deployments: List of deployment dictionaries with cloud_provider='gcp'
            start_date: Start date for cost period
            end_date: End date for cost period
            user_id: User ID for authentication
        
        Returns:
            Dictionary with aggregated costs
        """
        total_cost = 0.0
        deployment_costs = []

        for deployment in deployments:
            if deployment.get("cloud_provider", "").lower() != "gcp":
                continue

            deployment_id = str(deployment.get("id", ""))
            inputs = deployment.get("inputs", {})
            plugin_id = deployment.get("plugin_id", "")

            try:
                cost_estimate = await GCPCostService.estimate_deployment_cost(
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
gcp_cost_service = GCPCostService()

