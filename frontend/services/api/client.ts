// API Configuration
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

/**
 * Base API Client
 * Handles authentication, request/response, and token refresh
 */
class ApiClient {
    private baseURL: string;

    constructor() {
        this.baseURL = API_URL;
    }

    getAuthHeaders(): HeadersInit {
        const token = localStorage.getItem('access_token');
        return {
            'Content-Type': 'application/json',
            ...(token ? { Authorization: `Bearer ${token}` } : {})
        };
    }

    async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
        const url = `${this.baseURL}${endpoint}`;
        const config: RequestInit = {
            ...options,
            headers: {
                ...this.getAuthHeaders(),
                ...options.headers
            },
            credentials: 'include' // Important for cookies
        };

        try {
            let response = await fetch(url, config);

            // If unauthorized and not already retrying, try to refresh token
            if (response.status === 401 && !endpoint.includes('/refresh')) {
                const refreshed = await this.refreshToken();
                if (refreshed) {
                    // Retry the original request with new token
                    config.headers = {
                        ...this.getAuthHeaders(),
                        ...options.headers
                    };
                    response = await fetch(url, config);
                } else {
                    // Refresh failed, logout
                    localStorage.removeItem('access_token');
                    window.location.href = '/login';
                    throw new Error('Session expired');
                }
            }

            if (!response.ok) {
                const error = await response.json().catch(() => ({ detail: response.statusText }));
                throw new Error(error.detail || 'Request failed');
            }

            return response.json();
        } catch (error) {
            throw error;
        }
    }

    async refreshToken(): Promise<boolean> {
        try {
            const response: any = await fetch(`${this.baseURL}/api/v1/auth/refresh`, {
                method: 'POST',
                credentials: 'include',
                headers: { 'Content-Type': 'application/json' }
            });

            if (!response.ok) return false;

            const data = await response.json();
            localStorage.setItem('access_token', data.access_token);
            return true;
        } catch (error) {
            console.error('Token refresh failed:', error);
            return false;
        }
    }
}

export const apiClient = new ApiClient();
export type { ApiClient };
