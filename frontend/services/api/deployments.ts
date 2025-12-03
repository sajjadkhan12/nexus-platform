import { createCrudApi } from './helpers';
import { apiClient } from './client';

/**
 * Deployments API
 * Handles deployment CRUD operations
 */
const baseApi = createCrudApi('/api/v1/deployments');

export const deploymentsApi = {
    ...baseApi,
    
    // Alias methods for backward compatibility
    getDeployment: baseApi.get,
    deleteDeployment: baseApi.delete,
    listDeployments: baseApi.list,
    createDeployment: baseApi.create,
    updateDeployment: baseApi.update,
    
    // Retry a failed deployment
    async retryDeployment(deploymentId: string) {
        return apiClient.request(`/api/v1/deployments/${deploymentId}/retry`, {
            method: 'POST'
        });
    }
};
