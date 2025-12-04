import { apiClient } from './client';
import { createCrudApi } from './helpers';

/**
 * Groups API
 * Handles group management, member assignment, and role assignment
 */
const baseCrud = createCrudApi('/api/v1/groups');

export const groupsApi = {
    ...baseCrud,
    
    // Alias for backward compatibility
    async listGroups() {
        return baseCrud.list();
    },

    // Keep custom methods
    async addUserToGroup(groupId: string, userId: string) {
        return apiClient.request(`/api/v1/groups/${groupId}/users/${userId}`, {
            method: 'POST'
        });
    },

    async removeUserFromGroup(groupId: string, userId: string) {
        return apiClient.request(`/api/v1/groups/${groupId}/users/${userId}`, {
            method: 'DELETE'
        });
    },

    async addRoleToGroup(groupId: string, roleId: string) {
        return apiClient.request(`/api/v1/groups/${groupId}/roles/${roleId}`, {
            method: 'POST'
        });
    },

    async removeRoleFromGroup(groupId: string, roleId: string) {
        return apiClient.request(`/api/v1/groups/${groupId}/roles/${roleId}`, {
            method: 'DELETE'
        });
    }
};
