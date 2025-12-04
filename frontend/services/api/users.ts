import { apiClient } from './client';
import { uploadFile, buildQueryString } from './helpers';

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
        const query = buildQueryString(params);
        return apiClient.request(`/api/v1/users${query}`);
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
        return uploadFile('/api/v1/users/me/avatar', file);
    }
};
