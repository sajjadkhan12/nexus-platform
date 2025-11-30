import { apiClient } from './client';

/**
 * Deployments API
 * Handles deployment CRUD operations
 */
export const deploymentsApi = {
    async listDeployments() {
        return apiClient.request('/api/v1/deployments');
    },

    async getDeployment(id: string) {
        return apiClient.request(`/api/v1/deployments/${id}`);
    },

    async createDeployment(data: any) {
        return apiClient.request('/api/v1/deployments', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    },

    async updateDeployment(id: string, data: any) {
        return apiClient.request(`/api/v1/deployments/${id}`, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    },

    async deleteDeployment(id: string) {
        return apiClient.request(`/api/v1/deployments/${id}`, {
            method: 'DELETE'
        });
    }
};
