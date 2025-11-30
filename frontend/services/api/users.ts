import { apiClient } from './client';

/**
 * Users API
 * Handles user management, profile updates, and avatar uploads
 */
export const usersApi = {
    async getCurrentUser() {
        return apiClient.request('/api/v1/users/me');
    },

    async updateCurrentUser(data: any) {
        return apiClient.request('/api/v1/users/me', {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    },

    async listUsers(params?: { search?: string; role?: string }) {
        const queryParams = new URLSearchParams();
        if (params?.search) queryParams.append('search', params.search);
        if (params?.role) queryParams.append('role', params.role);
        const query = queryParams.toString();
        return apiClient.request(`/api/v1/users${query ? `?${query}` : ''}`);
    },

    async createUser(data: any) {
        return apiClient.request('/api/v1/users', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    },

    async adminUpdateUser(userId: string, data: any) {
        return apiClient.request(`/api/v1/users/${userId}`, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    },

    async deleteUser(userId: string) {
        return apiClient.request(`/api/v1/users/${userId}`, {
            method: 'DELETE'
        });
    },

    async updateUserRole(userId: string, role: string) {
        return apiClient.request(`/api/v1/users/${userId}/role`, {
            method: 'PUT',
            body: JSON.stringify({ role })
        });
    },

    async changePassword(data: any) {
        return apiClient.request('/api/v1/users/me/change-password', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    },

    async uploadAvatar(file: File) {
        const formData = new FormData();
        formData.append('file', file);

        const token = localStorage.getItem('access_token');
        const response = await fetch(`${apiClient['baseURL']}/api/v1/users/me/avatar`, {
            method: 'POST',
            headers: {
                ...(token ? { Authorization: `Bearer ${token}` } : {})
            },
            credentials: 'include',
            body: formData
        });

        if (!response.ok) {
            throw new Error('Avatar upload failed');
        }

        return response.json();
    }
};
