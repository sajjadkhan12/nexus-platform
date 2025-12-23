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
    
    // Update deployment with new inputs
    async updateDeployment(deploymentId: string, data: { inputs: Record<string, any>; tags?: Record<string, string>; cost_center?: string; project_code?: string }) {
        return apiClient.request(`/api/v1/deployments/${deploymentId}`, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    },
    
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
    },
    
    // Get deployment history
    async getDeploymentHistory(deploymentId: string) {
        return apiClient.request(`/api/v1/deployments/${deploymentId}/history`);
    },
    
    // Rollback deployment to a previous version
    async rollbackDeployment(deploymentId: string, versionNumber: number) {
        return apiClient.request(`/api/v1/deployments/${deploymentId}/rollback/${versionNumber}`, {
            method: 'POST'
        });
    }
};
