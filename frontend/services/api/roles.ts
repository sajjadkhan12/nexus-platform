import { apiClient } from './client';
import { createCrudApi } from './helpers';

/**
 * Roles API
 * Handles role and permission management
 */
const baseCrud = createCrudApi('/api/v1/roles');

export const rolesApi = {
    ...baseCrud,

    // Alias for backward compatibility
    async listRoles(params?: { skip?: number; limit?: number }) {
        return baseCrud.list(params);
    },

    async getAdminStats() {
        return apiClient.request('/api/v1/users/stats');
    }
};
