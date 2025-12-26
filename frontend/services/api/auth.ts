import { apiClient } from './client';
import { setAccessToken, removeAccessToken } from '../../utils/tokenStorage';

/**
 * Authentication API
 * Handles login, logout, and registration
 */
export const authApi = {
    async login(identifier: string, password: string) {
        const response = await apiClient.request<any>('/api/v1/auth/login', {
            method: 'POST',
            body: JSON.stringify({ identifier, password })
        });
        setAccessToken(response.access_token);
        return response;
    },

    async logout() {
        try {
            await apiClient.request('/api/v1/auth/logout', {
                method: 'POST'
            });
        } finally {
            removeAccessToken();
        }
    }
};
