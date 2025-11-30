import { apiClient } from './client';

/**
 * Provisioning API
 * Handles infrastructure provisioning operations
 */
export const provisioningApi = {
    async provisionInfrastructure(data: any) {
        return apiClient.request('/api/provision', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    },

    async listCredentials() {
        return apiClient.request('/api/credentials');
    },

    async createCredential(data: any) {
        return apiClient.request('/api/credentials', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    },

    async updateCredential(credId: string, data: any) {
        return apiClient.request(`/api/credentials/${credId}`, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    },

    async deleteCredential(credId: string) {
        return apiClient.request(`/api/credentials/${credId}`, {
            method: 'DELETE'
        });
    },

    async getJob(jobId: string) {
        return apiClient.request(`/api/provision/jobs/${jobId}`);
    },

    async getJobLogs(jobId: string) {
        return apiClient.request(`/api/provision/jobs/${jobId}/logs`);
    },

    async listJobs(params?: { jobId?: string; limit?: number }) {
        const queryParams = new URLSearchParams();
        if (params?.jobId) queryParams.append('job_id', params.jobId);
        if (params?.limit) queryParams.append('limit', params.limit.toString());
        const query = queryParams.toString();
        return apiClient.request(`/api/provision/jobs${query ? `?${query}` : ''}`);
    }
};
