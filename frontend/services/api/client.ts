// API Configuration
// Import from centralized constants to ensure consistency
import { API_URL } from '../../constants/api';
import { getAccessToken, setAccessToken, removeAccessToken } from '../../utils/tokenStorage';
import { appLogger } from '../../utils/logger';

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
        const token = getAccessToken();
        const headers: HeadersInit = {
            'Content-Type': 'application/json',
            ...(token ? { Authorization: `Bearer ${token}` } : {})
        };
        
        // Add business unit ID from localStorage if available
        try {
            const activeBU = localStorage.getItem('activeBusinessUnit');
            if (activeBU) {
                const bu = JSON.parse(activeBU);
                if (bu.id) {
                    headers['X-Business-Unit-Id'] = bu.id;
                }
            }
        } catch (e) {
            // Ignore errors parsing localStorage
        }
        
        return headers;
    }

    async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
        const url = `${this.baseURL}${endpoint}`;
        
        // Check if token needs refresh before making request
        // Skip for auth endpoints to avoid infinite loops
        if (!endpoint.includes('/auth/') && !endpoint.includes('/refresh')) {
            const { shouldRefreshToken } = await import('../../utils/tokenStorage');
            if (shouldRefreshToken()) {
                appLogger.debug('Token expiring soon, refreshing proactively...');
                await this.refreshToken();
            }
        }
        
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
                    removeAccessToken();
                    window.location.href = '/login';
                    throw new Error('Session expired');
                }
            }

            if (!response.ok) {
                const error = await response.json().catch(() => ({ detail: response.statusText }));
                const errorMessage = error.detail || 'Request failed';
                
                // Handle BU context errors gracefully
                if (response.status === 400 && (
                    errorMessage.includes('Business unit context required') ||
                    errorMessage.includes('business unit') ||
                    errorMessage.includes('BU context')
                )) {
                    // This is a BU context error - let the UI handle it
                    const buError = new Error(errorMessage);
                    (buError as any).isBusinessUnitError = true;
                    throw buError;
                }
                
                throw new Error(errorMessage);
            }

            // Handle 204 No Content responses (no body to parse)
            if (response.status === 204) {
                return null as T;
            }

            // Check if response has content to parse
            const contentType = response.headers.get('content-type');
            const contentLength = response.headers.get('content-length');
            
            // If there's content, try to parse as JSON
            if (contentLength && parseInt(contentLength) > 0) {
                try {
                    return await response.json();
                } catch (e) {
                    // If JSON parsing fails, return empty object
                    return {} as T;
                }
            } else if (contentType && contentType.includes('application/json')) {
                // Even if content-length is 0, try to parse if content-type says JSON
                try {
                    return await response.json();
                } catch (e) {
                    return {} as T;
                }
            }

            // Return empty object for other successful responses without JSON
            return {} as T;
        } catch (error: unknown) {
            // Don't log connection reset errors as errors - they're usually temporary (server restart)
            const errorMessage = error instanceof Error ? error.message : String(error);
            const errorName = error instanceof Error ? error.name : '';
            if (errorMessage.includes('Failed to fetch') || errorMessage.includes('ERR_CONNECTION_RESET') || errorName === 'TypeError') {
                appLogger.debug('Connection error (server may be restarting):', errorMessage || 'Connection reset');
            }
            throw error;
        }
    }

    async refreshToken(): Promise<boolean> {
        try {
            const response = await fetch(`${this.baseURL}/api/v1/auth/refresh`, {
                method: 'POST',
                credentials: 'include',
                headers: { 'Content-Type': 'application/json' }
            });

            if (!response.ok) return false;

            const data = await response.json();
            setAccessToken(data.access_token);
            return true;
        } catch (error) {
            appLogger.error('Token refresh failed:', error);
            return false;
        }
    }
}

export const apiClient = new ApiClient();
export type { ApiClient };
