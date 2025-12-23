"""
Cost-related Pydantic schemas for API responses
"""
from pydantic import BaseModel, Field
from typing import Dict, List, Optional
from datetime import datetime


class CostBreakdown(BaseModel):
    """Cost breakdown by resource type"""
    compute: Optional[float] = None
    storage: Optional[float] = None
    network: Optional[float] = None
    other: Optional[float] = None

    class Config:
        from_attributes = True


class CostEstimateResponse(BaseModel):
    """Response model for cost estimation"""
    estimated_monthly_cost: float = Field(..., description="Estimated monthly cost in USD")
    currency: str = Field(default="USD", description="Currency code")
    period: str = Field(default="month", description="Cost period (month, day, hour)")
    breakdown: Dict[str, float] = Field(default_factory=dict, description="Cost breakdown by resource type")
    machine_type: Optional[str] = Field(None, description="Machine type (for VM estimates)")
    zone: Optional[str] = Field(None, description="GCP zone")
    region: Optional[str] = Field(None, description="GCP region")
    source: Optional[str] = Field(None, description="Source of estimate (gcp_catalog_api, fallback_estimate)")
    note: Optional[str] = Field(None, description="Additional notes about the estimate")

    class Config:
        from_attributes = True


class ActualCostResponse(BaseModel):
    """Response model for actual costs"""
    total_cost: float = Field(..., description="Total actual cost")
    currency: str = Field(default="USD", description="Currency code")
    start_date: str = Field(..., description="Start date of cost period (ISO format)")
    end_date: str = Field(..., description="End date of cost period (ISO format)")
    project_id: str = Field(..., description="GCP project ID")
    billing_account_id: Optional[str] = Field(None, description="Billing account ID")
    breakdown: Dict[str, float] = Field(default_factory=dict, description="Cost breakdown")
    note: Optional[str] = Field(None, description="Additional notes")

    class Config:
        from_attributes = True


class DeploymentCostItem(BaseModel):
    """Cost item for a single deployment"""
    deployment_id: str = Field(..., description="Deployment ID")
    deployment_name: str = Field(..., description="Deployment name")
    estimated_cost: float = Field(..., description="Estimated cost")
    currency: str = Field(default="USD", description="Currency code")

    class Config:
        from_attributes = True


class AggregateCostResponse(BaseModel):
    """Response model for aggregated costs"""
    total_cost: float = Field(..., description="Total aggregated cost")
    currency: str = Field(default="USD", description="Currency code")
    period: Dict[str, str] = Field(..., description="Cost period with start and end dates")
    deployment_count: int = Field(..., description="Number of deployments included")
    deployments: List[DeploymentCostItem] = Field(default_factory=list, description="Cost per deployment")

    class Config:
        from_attributes = True


class CostTrendItem(BaseModel):
    """Single item in cost trend"""
    month: str = Field(..., description="Month in YYYY-MM format")
    amount: float = Field(..., description="Cost amount for the month")
    projected: bool = Field(default=False, description="Whether this is a projected/estimated value")
    currency: str = Field(default="USD", description="Currency code")

    class Config:
        from_attributes = True


class CostTrendResponse(BaseModel):
    """Response model for cost trend"""
    trend: List[CostTrendItem] = Field(..., description="Monthly cost trend")
    total: float = Field(..., description="Total cost across all months")
    currency: str = Field(default="USD", description="Currency code")

    class Config:
        from_attributes = True


class CostByProviderItem(BaseModel):
    """Cost item grouped by provider"""
    provider: str = Field(..., description="Cloud provider name")
    amount: float = Field(..., description="Total cost for this provider")
    currency: str = Field(default="USD", description="Currency code")
    deployment_count: int = Field(..., description="Number of deployments for this provider")

    class Config:
        from_attributes = True


class CostByProviderResponse(BaseModel):
    """Response model for costs grouped by provider"""
    costs: List[CostByProviderItem] = Field(..., description="Costs grouped by provider")
    total: float = Field(..., description="Total cost across all providers")
    currency: str = Field(default="USD", description="Currency code")

    class Config:
        from_attributes = True

