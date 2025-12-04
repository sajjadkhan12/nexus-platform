import { apiClient } from './client';
import { uploadFile } from './helpers';

/**
 * Plugins API
 * Handles plugin upload, listing, and management
 */
export const pluginsApi = {
    async uploadPlugin(file: File) {
        return uploadFile('/api/v1/plugins/upload', file);
    },

    async listPlugins() {
        return apiClient.request('/api/v1/plugins');
    },

    async getPlugin(pluginId: string) {
        return apiClient.request(`/api/v1/plugins/${pluginId}`);
    },

    async getPluginVersions(pluginId: string) {
        return apiClient.request(`/api/v1/plugins/${pluginId}/versions`);
    },

    async deletePlugin(pluginId: string) {
        return apiClient.request(`/api/v1/plugins/${pluginId}`, {
            method: 'DELETE'
        });
    },

    async lockPlugin(pluginId: string) {
        return apiClient.request(`/api/v1/plugins/${pluginId}/lock`, {
            method: 'PUT'
        });
    },

    async unlockPlugin(pluginId: string) {
        return apiClient.request(`/api/v1/plugins/${pluginId}/unlock`, {
            method: 'PUT'
        });
    },

    async requestAccess(pluginId: string) {
        return apiClient.request(`/api/v1/plugins/${pluginId}/access/request`, {
            method: 'POST'
        });
    },

    async grantAccess(pluginId: string, userId: string) {
        return apiClient.request(`/api/v1/plugins/${pluginId}/access/grant`, {
            method: 'POST',
            body: JSON.stringify({ user_id: userId })
        });
    },

    async revokeAccess(pluginId: string, userId: string) {
        return apiClient.request(`/api/v1/plugins/${pluginId}/access/${userId}`, {
            method: 'DELETE'
        });
    },

    async getAccessRequests(pluginId: string) {
        return apiClient.request(`/api/v1/plugins/${pluginId}/access/requests`);
    },

    async getAllAccessRequests(userEmail?: string) {
        const params = userEmail ? `?user_email=${encodeURIComponent(userEmail)}` : '';
        return apiClient.request(`/api/v1/plugins/access/requests${params}`);
    },

    async getPluginAccess(pluginId: string) {
        return apiClient.request(`/api/v1/plugins/${pluginId}/access`);
    }
};
