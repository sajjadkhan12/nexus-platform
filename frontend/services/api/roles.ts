import { apiClient } from './client';

/**
 * Roles API
 * Handles role and permission management
 */
export const rolesApi = {
    async listRoles() {
        return apiClient.request('/api/v1/roles');
    },

    async createRole(data: { name: string; description: string; permissions: string[] }) {
        return apiClient.request('/api/v1/roles', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    },

    async updateRole(roleId: string, data: { name?: string; description?: string; permissions?: string[] }) {
        return apiClient.request(`/api/v1/roles/${roleId}`, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    },

    async deleteRole(roleId: string) {
        return apiClient.request(`/api/v1/roles/${roleId}`, {
            method: 'DELETE'
        });
    },

    async getAdminStats() {
        return apiClient.request('/api/v1/users/admin/stats');
    }
};
