import { apiClient } from './client';

/**
 * Cost API
 * Handles cost estimation and retrieval operations
 */

export interface CostEstimate {
  estimated_monthly_cost: number;
  currency: string;
  period: string;
  breakdown: Record<string, number>;
  machine_type?: string;
  zone?: string;
  region?: string;
  source?: string;
  note?: string;
}

export interface ActualCost {
  total_cost: number;
  currency: string;
  start_date: string;
  end_date: string;
  project_id: string;
  billing_account_id?: string;
  breakdown: Record<string, number>;
  note?: string;
}

export interface CostTrendItem {
  month: string;
  amount: number;
  projected: boolean;
  currency: string;
}

export interface CostTrend {
  trend: CostTrendItem[];
  total: number;
  currency: string;
}

export interface CostByProviderItem {
  provider: string;
  amount: number;
  currency: string;
  deployment_count: number;
}

export interface CostByProvider {
  costs: CostByProviderItem[];
  total: number;
  currency: string;
}

export interface DeploymentCostItem {
  deployment_id: string;
  deployment_name: string;
  estimated_cost: number;
  currency: string;
}

export interface AggregateCost {
  total_cost: number;
  currency: string;
  period: {
    start: string;
    end: string;
  };
  deployment_count: number;
  deployments: DeploymentCostItem[];
}

export interface AggregateCostFilters {
  start_date?: string;
  end_date?: string;
  provider?: string;
  environment?: string;
}

export const costApi = {
  /**
   * Get cost estimate before provisioning (based on plugin and inputs)
   */
  async getPreProvisionCostEstimate(
    pluginId: string,
    inputs: Record<string, any>
  ): Promise<CostEstimate> {
    return apiClient.request<CostEstimate>(
      `/api/v1/deployments/costs/estimate/pre-provision?plugin_id=${encodeURIComponent(pluginId)}`,
      {
        method: 'POST',
        body: JSON.stringify(inputs),
      }
    );
  },

  /**
   * Get cost estimate for a deployment
   */
  async getCostEstimate(deploymentId: string): Promise<CostEstimate> {
    return apiClient.request<CostEstimate>(
      `/api/v1/deployments/costs/estimate/${deploymentId}`
    );
  },

  /**
   * Get actual costs for a deployment
   */
  async getActualCost(
    deploymentId: string,
    startDate?: string,
    endDate?: string
  ): Promise<ActualCost> {
    const params = new URLSearchParams();
    if (startDate) params.append('start_date', startDate);
    if (endDate) params.append('end_date', endDate);
    
    const queryString = params.toString();
    const url = `/api/v1/deployments/costs/actual/${deploymentId}${queryString ? `?${queryString}` : ''}`;
    
    return apiClient.request<ActualCost>(url);
  },

  /**
   * Get monthly cost trend
   */
  async getCostTrend(months: number = 6): Promise<CostTrend> {
    return apiClient.request<CostTrend>(
      `/api/v1/deployments/costs/trend?months=${months}`
    );
  },

  /**
   * Get costs grouped by provider
   */
  async getCostsByProvider(
    startDate?: string,
    endDate?: string
  ): Promise<CostByProvider> {
    const params = new URLSearchParams();
    if (startDate) params.append('start_date', startDate);
    if (endDate) params.append('end_date', endDate);
    
    const queryString = params.toString();
    const url = `/api/v1/deployments/costs/by-provider${queryString ? `?${queryString}` : ''}`;
    
    return apiClient.request<CostByProvider>(url);
  },

  /**
   * Get aggregated costs with filters
   */
  async getAggregateCosts(
    filters?: AggregateCostFilters
  ): Promise<AggregateCost> {
    const params = new URLSearchParams();
    if (filters?.start_date) params.append('start_date', filters.start_date);
    if (filters?.end_date) params.append('end_date', filters.end_date);
    if (filters?.provider) params.append('provider', filters.provider);
    if (filters?.environment) params.append('environment', filters.environment);
    
    const queryString = params.toString();
    const url = `/api/v1/deployments/costs/aggregate${queryString ? `?${queryString}` : ''}`;
    
    return apiClient.request<AggregateCost>(url);
  },
};

