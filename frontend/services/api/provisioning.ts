import { apiClient } from './client';

/**
 * Provisioning API
 * Handles infrastructure provisioning operations
 */
export const provisioningApi = {
    async provisionInfrastructure(data: any) {
        return apiClient.request('/api/v1/provision', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    },

    // Alias for backward compatibility
    async provision(data: any) {
        return apiClient.request('/api/v1/provision', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    },

    async listCredentials() {
        return apiClient.request('/api/v1/admin/credentials');
    },

    async createCredential(data: any) {
        return apiClient.request('/api/v1/admin/credentials', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    },

    async updateCredential(credId: string, data: any) {
        return apiClient.request(`/api/v1/admin/credentials/${credId}`, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    },

    async deleteCredential(credId: string) {
        return apiClient.request(`/api/v1/admin/credentials/${credId}`, {
            method: 'DELETE'
        });
    },

    async getJob(jobId: string) {
        return apiClient.request(`/api/v1/provision/jobs/${jobId}`);
    },

    async getJobLogs(jobId: string) {
        return apiClient.request(`/api/v1/provision/jobs/${jobId}/logs`);
    },

    async listJobs(params?: { jobId?: string; limit?: number }) {
        const queryParams = new URLSearchParams();
        if (params?.jobId) queryParams.append('job_id', params.jobId);
        if (params?.limit) queryParams.append('limit', params.limit.toString());
        const query = queryParams.toString();
        return apiClient.request(`/api/v1/provision/jobs${query ? `?${query}` : ''}`);
    },

    async deleteJob(jobId: string) {
        return apiClient.request(`/api/v1/provision/jobs/${jobId}`, {
            method: 'DELETE'
        });
    },

    async bulkDeleteJobs(jobIds: string[]) {
        return apiClient.request('/api/v1/provision/jobs/bulk-delete', {
            method: 'POST',
            body: JSON.stringify({ job_ids: jobIds })
        });
    }
};
