import { apiClient } from './client';
import { uploadFile } from './helpers';

/**
 * Plugins API
 * Handles plugin upload, listing, and management
 */
export const pluginsApi = {
    async uploadPlugin(
        file: File,
        options?: {
            gitBranch?: string;
            gitRepoUrl?: string;
        }
    ) {
        const extraFields: Record<string, string> = {};
        if (options?.gitBranch) {
            extraFields['git_branch'] = options.gitBranch;
        }
        if (options?.gitRepoUrl) {
            extraFields['git_repo_url'] = options.gitRepoUrl;
        }

        return uploadFile('/api/v1/plugins/upload', file, 'file', extraFields);
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

    async restoreAccess(pluginId: string, userId: string) {
        return apiClient.request(`/api/v1/plugins/${pluginId}/access/${userId}/restore`, {
            method: 'POST'
        });
    },

    async getAccessRequests(pluginId: string) {
        return apiClient.request(`/api/v1/plugins/${pluginId}/access/requests`);
    },

    async getAllAccessRequests(search?: string, status?: string) {
        const params = new URLSearchParams();
        if (search) params.append('search', search);
        if (status) params.append('status', status);
        const queryString = params.toString();
        return apiClient.request(`/api/v1/plugins/access/requests${queryString ? `?${queryString}` : ''}`);
    },

    async getPluginAccess(pluginId: string) {
        return apiClient.request(`/api/v1/plugins/${pluginId}/access`);
    },

    async getAllAccessGrants(userEmail?: string) {
        const params = userEmail ? `?user_email=${encodeURIComponent(userEmail)}` : '';
        return apiClient.request(`/api/v1/plugins/access/grants${params}`);
    },

    async uploadMicroserviceTemplate(data: {
        plugin_id: string;
        name: string;
        version: string;
        description: string;
        template_repo_url: string;
        template_path: string;
        author?: string;
    }) {
        const formData = new FormData();
        formData.append('plugin_id', data.plugin_id);
        formData.append('name', data.name);
        formData.append('version', data.version);
        formData.append('description', data.description);
        formData.append('template_repo_url', data.template_repo_url);
        formData.append('template_path', data.template_path);
        if (data.author) {
            formData.append('author', data.author);
        }
        
        // Use raw fetch to avoid Content-Type header being set by apiClient
        const token = localStorage.getItem('access_token');
        const response = await fetch(`${window.location.origin.replace('3000', '8000')}/api/v1/plugins/upload-template`, {
            method: 'POST',
            credentials: 'include',
            headers: {
                ...(token ? { Authorization: `Bearer ${token}` } : {})
                // Don't set Content-Type - browser will set it automatically with boundary
            },
            body: formData
        });
        
        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: response.statusText }));
            throw new Error(error.detail || 'Request failed');
        }
        
        return await response.json();
    }
};
