import { apiClient } from './client';

/**
 * Groups API
 * Handles group management, member assignment, and role assignment
 */
export const groupsApi = {
    async listGroups() {
        return apiClient.request('/api/v1/groups');
    },

    async createGroup(data: { name: string; description?: string }) {
        return apiClient.request('/api/v1/groups', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    },

    async updateGroup(groupId: string, data: { name?: string; description?: string }) {
        return apiClient.request(`/api/v1/groups/${groupId}`, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    },

    async deleteGroup(groupId: string) {
        return apiClient.request(`/api/v1/groups/${groupId}`, {
            method: 'DELETE'
        });
    },

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
