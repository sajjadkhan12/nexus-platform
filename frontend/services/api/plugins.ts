import { apiClient } from './client';

/**
 * Plugins API
 * Handles plugin upload, listing, and management
 */
export const pluginsApi = {
    async uploadPlugin(file: File) {
        const formData = new FormData();
        formData.append('file', file);

        const token = localStorage.getItem('access_token');
        const response = await fetch(`${apiClient['baseURL']}/api/plugins/upload`, {
            method: 'POST',
            headers: {
                ...(token ? { Authorization: `Bearer ${token}` } : {})
            },
            credentials: 'include',
            body: formData
        });

        if (!response.ok) {
            throw new Error('Plugin upload failed');
        }

        return response.json();
    },

    async listPlugins() {
        return apiClient.request('/api/plugins');
    },

    async getPlugin(pluginId: string) {
        return apiClient.request(`/api/plugins/${pluginId}`);
    },

    async getPluginVersions(pluginId: string) {
        return apiClient.request(`/api/plugins/${pluginId}/versions`);
    },

    async deletePlugin(pluginId: string) {
        return apiClient.request(`/api/plugins/${pluginId}`, {
            method: 'DELETE'
        });
    }
};
