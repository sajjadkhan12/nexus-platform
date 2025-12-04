import { apiClient } from './client';

/**
 * Authentication API
 * Handles login, logout, and registration
 */
export const authApi = {
    async login(email: string, password: string) {
        const response = await apiClient.request<any>('/api/v1/auth/login', {
            method: 'POST',
            body: JSON.stringify({ email, password })
        });
        localStorage.setItem('access_token', response.access_token);
        return response;
    },

    async logout() {
        try {
            await apiClient.request('/api/v1/auth/logout', {
                method: 'POST'
            });
        } finally {
            localStorage.removeItem('access_token');
        }
    }
};
