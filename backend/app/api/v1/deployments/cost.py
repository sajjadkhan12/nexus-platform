"""Cost estimation and retrieval endpoints for deployments"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta, timezone
from uuid import UUID
from fastapi import Body

from app.database import get_db
from app.api.deps import get_current_user, OrgAwareEnforcer, get_org_aware_enforcer, get_active_business_unit
from app.models.rbac import User
from app.models.deployment import Deployment
from typing import Optional
import uuid
from app.schemas.cost import (
    CostEstimateResponse,
    ActualCostResponse,
    CostTrendResponse,
    CostTrendItem,
    CostByProviderResponse,
    CostByProviderItem,
    AggregateCostResponse,
    DeploymentCostItem
)
from app.services.gcp_cost_service import gcp_cost_service
from app.services.aws_cost_service import aws_cost_service
from app.logger import logger

router = APIRouter()


@router.post("/costs/estimate/pre-provision", response_model=CostEstimateResponse)
async def estimate_cost_pre_provision(
    plugin_id: str = Query(..., description="Plugin ID"),
    inputs: Dict[str, Any] = Body(..., description="Deployment inputs"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Estimate cost before provisioning a deployment.
    
    This endpoint allows users to see cost estimates based on their
    configuration before actually creating the deployment.
    """
    user_id = str(current_user.id)
    
    # Validate that it's a GCP plugin
    from app.models.plugins import PluginVersion
    from sqlalchemy import select
    
    # Get plugin to check cloud provider
    plugin_result = await db.execute(
        select(PluginVersion).where(PluginVersion.plugin_id == plugin_id)
        .order_by(PluginVersion.version.desc())
    )
    plugin_version = plugin_result.scalar_one_or_none()
    
    if not plugin_version:
        raise HTTPException(status_code=404, detail="Plugin not found")
    
    manifest = plugin_version.manifest or {}
    cloud_provider = manifest.get("cloud_provider", "").lower()
    
    if cloud_provider not in ["gcp", "aws"]:
        raise HTTPException(
            status_code=400,
            detail=f"Cost estimation not yet implemented for {cloud_provider}. Only GCP and AWS are supported."
        )
    
    try:
        if cloud_provider == "gcp":
            cost_estimate = await gcp_cost_service.estimate_deployment_cost(
                deployment_inputs=inputs,
                plugin_id=plugin_id,
                user_id=user_id
            )
        elif cloud_provider == "aws":
            cost_estimate = await aws_cost_service.estimate_deployment_cost(
                deployment_inputs=inputs,
                plugin_id=plugin_id,
                user_id=user_id
            )
        else:
            raise HTTPException(status_code=400, detail="Unsupported cloud provider")
        
        response = CostEstimateResponse(
            estimated_monthly_cost=cost_estimate.get("estimated_monthly_cost", 0),
            currency=cost_estimate.get("currency", "USD"),
            period=cost_estimate.get("period", "month"),
            breakdown=cost_estimate.get("breakdown", {}),
            source=cost_estimate.get("source"),
            note=cost_estimate.get("note")
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error estimating cost for plugin {plugin_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to estimate cost: {str(e)}"
        )


@router.get("/costs/estimate/{deployment_id}", response_model=CostEstimateResponse)
async def get_cost_estimate(
    deployment_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    enforcer: OrgAwareEnforcer = Depends(get_org_aware_enforcer)
):
    """
    Get cost estimate for a deployment.
    
    This endpoint estimates the monthly cost based on the deployment's
    configuration and inputs.
    """
    try:
        deployment_uuid = UUID(deployment_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid deployment ID format")

    # Get deployment
    result = await db.execute(
        select(Deployment).where(Deployment.id == deployment_uuid)
    )
    deployment = result.scalar_one_or_none()

    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")

    # Check permissions
    from app.core.authorization import check_permission
    
    # Get user's active business unit
    business_unit_id = None
    if current_user.active_business_unit_id:
        business_unit_id = current_user.active_business_unit_id
    
    has_list_permission = False
    if business_unit_id and deployment.business_unit_id:
        has_list_permission = await check_permission(
            current_user,
            "business_unit:deployments:list",
            deployment.business_unit_id,
            db,
            enforcer.enforcer if hasattr(enforcer, 'enforcer') else enforcer
        )
    
    has_list_own = await check_permission(
        current_user,
        "user:deployments:list:own",
        None,
        db,
        enforcer.enforcer if hasattr(enforcer, 'enforcer') else enforcer
    )
    
    if not has_list_permission and not (has_list_own and deployment.user_id == current_user.id):
        raise HTTPException(status_code=403, detail="Permission denied")

    # Route to appropriate cost service based on cloud provider
    cloud_provider = deployment.cloud_provider and deployment.cloud_provider.lower()
    
    if cloud_provider not in ["gcp", "aws"]:
        raise HTTPException(
            status_code=400,
            detail=f"Cost estimation not yet implemented for {deployment.cloud_provider}. Only GCP and AWS are supported."
        )

    try:
        # Get cost estimate
        inputs = deployment.inputs or {}
        
        if cloud_provider == "gcp":
            cost_estimate = await gcp_cost_service.estimate_deployment_cost(
                deployment_inputs=inputs,
                plugin_id=deployment.plugin_id,
                user_id=user_id
            )
        elif cloud_provider == "aws":
            cost_estimate = await aws_cost_service.estimate_deployment_cost(
                deployment_inputs=inputs,
                plugin_id=deployment.plugin_id,
                user_id=user_id
            )
        else:
            raise HTTPException(status_code=400, detail="Unsupported cloud provider")

        # Convert to response model
        response = CostEstimateResponse(
            estimated_monthly_cost=cost_estimate.get("estimated_monthly_cost", 0),
            currency=cost_estimate.get("currency", "USD"),
            period=cost_estimate.get("period", "month"),
            breakdown=cost_estimate.get("breakdown", {}),
            source=cost_estimate.get("source")
        )

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error estimating cost for deployment {deployment_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to estimate cost: {str(e)}"
        )


@router.get("/costs/actual/{deployment_id}", response_model=ActualCostResponse)
async def get_actual_costs(
    deployment_id: str,
    start_date: Optional[datetime] = Query(None, description="Start date for cost query (ISO format)"),
    end_date: Optional[datetime] = Query(None, description="End date for cost query (ISO format)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    enforcer: OrgAwareEnforcer = Depends(get_org_aware_enforcer)
):
    """
    Get actual costs for a deployment.
    
    This endpoint retrieves actual costs from GCP Cloud Billing API.
    Note: This requires Cloud Billing Export to BigQuery for full functionality.
    """
    try:
        deployment_uuid = UUID(deployment_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid deployment ID format")

    # Get deployment
    result = await db.execute(
        select(Deployment).where(Deployment.id == deployment_uuid)
    )
    deployment = result.scalar_one_or_none()

    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")

    # Check permissions
    from app.core.authorization import check_permission
    
    # Get user's active business unit
    business_unit_id = None
    if current_user.active_business_unit_id:
        business_unit_id = current_user.active_business_unit_id
    
    has_list_permission = False
    if business_unit_id and deployment.business_unit_id:
        has_list_permission = await check_permission(
            current_user,
            "business_unit:deployments:list",
            deployment.business_unit_id,
            db,
            enforcer.enforcer if hasattr(enforcer, 'enforcer') else enforcer
        )
    
    has_list_own = await check_permission(
        current_user,
        "user:deployments:list:own",
        None,
        db,
        enforcer.enforcer if hasattr(enforcer, 'enforcer') else enforcer
    )
    
    if not has_list_permission and not (has_list_own and deployment.user_id == current_user.id):
        raise HTTPException(status_code=403, detail="Permission denied")

    # Only get actual costs for GCP deployments (AWS requires Cost Explorer setup)
    cloud_provider = deployment.cloud_provider and deployment.cloud_provider.lower()
    if cloud_provider != "gcp":
        raise HTTPException(
            status_code=400,
            detail=f"Actual cost retrieval not yet implemented for {deployment.cloud_provider}. Only GCP is supported."
        )

    # Set default date range (last 30 days)
    if not end_date:
        end_date = datetime.now(timezone.utc)
    if not start_date:
        start_date = end_date - timedelta(days=30)

    # Get project ID from deployment inputs
    inputs = deployment.inputs or {}
    project_id = inputs.get("project_id")

    if not project_id:
        raise HTTPException(
            status_code=400,
            detail="Project ID not found in deployment inputs. Cannot retrieve costs."
        )

    try:
        actual_costs = await gcp_cost_service.get_actual_costs(
            project_id=project_id,
            start_date=start_date,
            end_date=end_date,
            user_id=user_id
        )

        return ActualCostResponse(**actual_costs)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving actual costs for deployment {deployment_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve costs: {str(e)}"
        )


@router.get("/costs/trend", response_model=CostTrendResponse)
async def get_cost_trend(
    months: int = Query(6, ge=1, le=24, description="Number of months to include in trend"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    enforcer: OrgAwareEnforcer = Depends(get_org_aware_enforcer),
    business_unit_id: Optional[uuid.UUID] = Depends(get_active_business_unit)
):
    """
    Get monthly cost trend for the last N months.
    
    Returns estimated costs grouped by month for all GCP deployments
    the user has access to.
    """
    from app.core.authorization import check_permission

    # Build query based on permissions - include both GCP and AWS
    query = select(Deployment).where(
        and_(
            Deployment.cloud_provider.in_(["gcp", "aws"]),
            Deployment.status != "deleted"
        )
    )

    has_list_permission = False
    if business_unit_id:
        has_list_permission = await check_permission(
            current_user,
            "business_unit:deployments:list",
            business_unit_id,
            db,
            enforcer.enforcer if hasattr(enforcer, 'enforcer') else enforcer
        )
    
    has_list_own = await check_permission(
        current_user,
        "user:deployments:list:own",
        None,
        db,
        enforcer.enforcer if hasattr(enforcer, 'enforcer') else enforcer
    )
    
    is_admin = has_list_permission
    
    if not is_admin:
        # Only show own deployments
        if has_list_own:
            query = query.where(Deployment.user_id == current_user.id)
        else:
            raise HTTPException(status_code=403, detail="Permission denied")

    # Apply business unit filter if provided
    # Admins can work without business unit (see all), regular users need business unit
    if business_unit_id:
        query = query.where(Deployment.business_unit_id == business_unit_id)
    elif not is_admin:
        # Regular users without business unit - show only unassigned deployments
        query = query.where(Deployment.business_unit_id.is_(None))

    result = await db.execute(query)
    deployments = result.scalars().all()

    # Group deployments by month and calculate costs
    trend_items: List[CostTrendItem] = []
    total_cost = 0.0

    # Generate months list
    end_date = datetime.now(timezone.utc)
    for i in range(months):
        month_date = end_date - timedelta(days=30 * i)
        month_str = month_date.strftime("%Y-%m")
        
        # For each deployment, estimate cost
        month_cost = 0.0
        for deployment in deployments:
            try:
                inputs = deployment.inputs or {}
                cloud_provider = deployment.cloud_provider and deployment.cloud_provider.lower()
                
                if cloud_provider == "gcp":
                    cost_estimate = await gcp_cost_service.estimate_deployment_cost(
                        deployment_inputs=inputs,
                        plugin_id=deployment.plugin_id,
                        user_id=user_id
                    )
                elif cloud_provider == "aws":
                    cost_estimate = await aws_cost_service.estimate_deployment_cost(
                        deployment_inputs=inputs,
                        plugin_id=deployment.plugin_id,
                        user_id=user_id
                    )
                else:
                    continue
                    
                month_cost += cost_estimate.get("estimated_monthly_cost", 0)
            except Exception as e:
                logger.warning(f"Failed to estimate cost for deployment {deployment.id}: {str(e)}")
                continue

        trend_items.append(CostTrendItem(
            month=month_str,
            amount=round(month_cost, 2),
            projected=i > 0,  # Past months are actual, future months are projected
            currency="USD"
        ))
        total_cost += month_cost

    # Reverse to show oldest first
    trend_items.reverse()

    return CostTrendResponse(
        trend=trend_items,
        total=round(total_cost, 2),
        currency="USD"
    )


@router.get("/costs/by-provider", response_model=CostByProviderResponse)
async def get_costs_by_provider(
    start_date: Optional[datetime] = Query(None, description="Start date for cost query"),
    end_date: Optional[datetime] = Query(None, description="End date for cost query"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    enforcer: OrgAwareEnforcer = Depends(get_org_aware_enforcer),
    business_unit_id: Optional[uuid.UUID] = Depends(get_active_business_unit)
):
    """
    Get costs grouped by cloud provider.
    
    Currently only supports GCP, but structure allows for future expansion.
    """
    from app.core.authorization import check_permission

    # Build query based on permissions
    query = select(Deployment).where(Deployment.status != "deleted")

    has_list_permission = False
    if business_unit_id:
        has_list_permission = await check_permission(
            current_user,
            "business_unit:deployments:list",
            business_unit_id,
            db,
            enforcer.enforcer if hasattr(enforcer, 'enforcer') else enforcer
        )
    
    has_list_own = await check_permission(
        current_user,
        "user:deployments:list:own",
        None,
        db,
        enforcer.enforcer if hasattr(enforcer, 'enforcer') else enforcer
    )

    if not has_list_permission:
        if has_list_own:
            query = query.where(Deployment.user_id == current_user.id)
        else:
            raise HTTPException(status_code=403, detail="Permission denied")

    # Apply business unit filter if provided
    if business_unit_id:
        query = query.where(Deployment.business_unit_id == business_unit_id)

    result = await db.execute(query)
    deployments = result.scalars().all()

    # Group by provider
    provider_costs: Dict[str, float] = {}
    provider_counts: Dict[str, int] = {}

    for deployment in deployments:
        provider = deployment.cloud_provider or "unknown"
        provider_lower = provider.lower()
        
        # Calculate costs for GCP and AWS
        if provider_lower in ["gcp", "aws"]:
            try:
                inputs = deployment.inputs or {}
                
                if provider_lower == "gcp":
                    cost_estimate = await gcp_cost_service.estimate_deployment_cost(
                        deployment_inputs=inputs,
                        plugin_id=deployment.plugin_id,
                        user_id=user_id
                    )
                elif provider_lower == "aws":
                    cost_estimate = await aws_cost_service.estimate_deployment_cost(
                        deployment_inputs=inputs,
                        plugin_id=deployment.plugin_id,
                        user_id=user_id
                    )
                else:
                    continue
                    
                cost = cost_estimate.get("estimated_monthly_cost", 0)
                provider_costs[provider] = provider_costs.get(provider, 0) + cost
                provider_counts[provider] = provider_counts.get(provider, 0) + 1
            except Exception as e:
                logger.warning(f"Failed to estimate cost for deployment {deployment.id}: {str(e)}")
                continue
        else:
            # For other providers, set cost to 0 (not yet implemented)
            provider_costs[provider] = provider_costs.get(provider, 0)
            provider_counts[provider] = provider_counts.get(provider, 0) + 1

    # Build response
    cost_items = [
        CostByProviderItem(
            provider=provider,
            amount=round(cost, 2),
            currency="USD",
            deployment_count=provider_counts.get(provider, 0)
        )
        for provider, cost in provider_costs.items()
    ]

    total = sum(item.amount for item in cost_items)

    return CostByProviderResponse(
        costs=cost_items,
        total=round(total, 2),
        currency="USD"
    )


@router.get("/costs/aggregate", response_model=AggregateCostResponse)
async def get_aggregate_costs(
    start_date: Optional[datetime] = Query(None, description="Start date for cost period"),
    end_date: Optional[datetime] = Query(None, description="End date for cost period"),
    provider: Optional[str] = Query(None, description="Filter by cloud provider"),
    environment: Optional[str] = Query(None, description="Filter by environment"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    enforcer: OrgAwareEnforcer = Depends(get_org_aware_enforcer),
    business_unit_id: Optional[uuid.UUID] = Depends(get_active_business_unit)
):
    """
    Get aggregated costs with optional filters.
    
    Aggregates costs for all deployments matching the filters.
    """
    user_id = str(current_user.id)

    # Set default date range
    if not end_date:
        end_date = datetime.now(timezone.utc)
    if not start_date:
        start_date = end_date - timedelta(days=30)

    # Build query with filters
    conditions = [Deployment.status != "deleted"]

    if provider:
        conditions.append(Deployment.cloud_provider == provider.lower())

    if environment:
        conditions.append(Deployment.environment == environment.lower())

    query = select(Deployment).where(and_(*conditions))

    from app.core.authorization import check_permission
    
    has_list_permission = False
    if business_unit_id:
        has_list_permission = await check_permission(
            current_user,
            "business_unit:deployments:list",
            business_unit_id,
            db,
            enforcer.enforcer if hasattr(enforcer, 'enforcer') else enforcer
        )
    
    has_list_own = await check_permission(
        current_user,
        "user:deployments:list:own",
        None,
        db,
        enforcer.enforcer if hasattr(enforcer, 'enforcer') else enforcer
    )
    
    if not has_list_permission:
        if has_list_own:
            query = query.where(Deployment.user_id == current_user.id)
        else:
            raise HTTPException(status_code=403, detail="Permission denied")

    # Apply business unit filter if provided
    if business_unit_id:
        query = query.where(Deployment.business_unit_id == business_unit_id)

    result = await db.execute(query)
    deployments = result.scalars().all()

    # Group deployments by provider and aggregate
    gcp_deployments = []
    aws_deployments = []
    
    for dep in deployments:
        deployment_dict = {
            "id": str(dep.id),
            "name": dep.name,
            "cloud_provider": dep.cloud_provider,
            "plugin_id": dep.plugin_id,
            "inputs": dep.inputs or {}
        }
        
        if dep.cloud_provider and dep.cloud_provider.lower() == "gcp":
            gcp_deployments.append(deployment_dict)
        elif dep.cloud_provider and dep.cloud_provider.lower() == "aws":
            aws_deployments.append(deployment_dict)
    
    # Aggregate costs for each provider
    all_deployment_costs = []
    total_cost = 0.0
    
    if gcp_deployments:
        gcp_aggregated = await gcp_cost_service.aggregate_costs_by_deployment(
            deployments=gcp_deployments,
            start_date=start_date,
            end_date=end_date,
            user_id=user_id
        )
        all_deployment_costs.extend(gcp_aggregated.get("deployments", []))
        total_cost += gcp_aggregated.get("total_cost", 0)
    
    if aws_deployments:
        aws_aggregated = await aws_cost_service.aggregate_costs_by_deployment(
            deployments=aws_deployments,
            start_date=start_date,
            end_date=end_date,
            user_id=user_id
        )
        all_deployment_costs.extend(aws_aggregated.get("deployments", []))
        total_cost += aws_aggregated.get("total_cost", 0)
    
    aggregated = {
        "total_cost": total_cost,
        "currency": "USD",
        "deployment_count": len(all_deployment_costs),
        "deployments": all_deployment_costs
    }

    # Convert to response model
    deployment_items = [
        DeploymentCostItem(**item)
        for item in aggregated.get("deployments", [])
    ]

    return AggregateCostResponse(
        total_cost=aggregated.get("total_cost", 0),
        currency=aggregated.get("currency", "USD"),
        period={
            "start": start_date.isoformat(),
            "end": end_date.isoformat()
        },
        deployment_count=aggregated.get("deployment_count", 0),
        deployments=deployment_items
    )

