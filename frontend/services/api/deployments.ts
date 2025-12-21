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
    },
    
    // CI/CD status for microservices
    async getCICDStatus(deploymentId: string) {
        return apiClient.request(`/api/v1/deployments/${deploymentId}/ci-cd-status`);
    },
    
    // Repository information for microservices
    async getRepositoryInfo(deploymentId: string) {
        return apiClient.request(`/api/v1/deployments/${deploymentId}/repository`);
    },
    
    // Sync CI/CD status manually
    async syncCICDStatus(deploymentId: string) {
        return apiClient.request(`/api/v1/deployments/${deploymentId}/sync-ci-cd`, {
            method: 'POST'
        });
    }
};
