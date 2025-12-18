import { apiClient } from './client';
import { createCrudApi } from './helpers';

/**
 * Roles API
 * Handles role and permission management
 */
const baseCrud = createCrudApi('/api/v1/roles');

export const rolesApi = {
    ...baseCrud,

    // Aliases for backward compatibility
    async listRoles(params?: { skip?: number; limit?: number }) {
        return baseCrud.list(params);
    },

    async getRole(id: string) {
        return baseCrud.get(id);
    },

    async createRole(data: any) {
        return baseCrud.create(data);
    },

    async updateRole(id: string, data: any) {
        return baseCrud.update(id, data);
    },

    async deleteRole(id: string) {
        return baseCrud.delete(id);
    },

    async getAdminStats() {
        return apiClient.request('/api/v1/users/stats');
    }
};
