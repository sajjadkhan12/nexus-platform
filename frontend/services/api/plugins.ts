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
    }
};
