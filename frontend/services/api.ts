// API Configuration
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// API Service
class ApiService {
    private baseURL: string;

    constructor() {
        this.baseURL = API_URL;
    }

    private getAuthHeaders(): HeadersInit {
        const token = localStorage.getItem('access_token');
        return {
            'Content-Type': 'application/json',
            ...(token && { 'Authorization': `Bearer ${token}` })
        };
    }

    async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
        const url = `${this.baseURL}${endpoint}`;
        const config: RequestInit = {
            ...options,
            headers: {
                ...this.getAuthHeaders(),
                ...options.headers,
            },
        };

        const response = await fetch(url, config);

        if (response.status === 401) {
            // Token expired, try to refresh
            const refreshed = await this.refreshToken();
            if (refreshed) {
                // Retry the request with new token
                return this.request(endpoint, options);
            } else {
                // Refresh failed, logout
                localStorage.removeItem('access_token');
                localStorage.removeItem('refresh_token');
                window.location.href = '/#/login';
                throw new Error('Session expired');
            }
        }

        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: 'Request failed' }));
            throw new Error(error.detail || 'Request failed');
        }

        return response.json();
    }

    async refreshToken(): Promise<boolean> {
        const refreshToken = localStorage.getItem('refresh_token');
        if (!refreshToken) return false;

        try {
            const response = await fetch(`${this.baseURL}/api/v1/auth/refresh`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ refresh_token: refreshToken })
            });

            if (response.ok) {
                const data = await response.json();
                localStorage.setItem('access_token', data.access_token);
                localStorage.setItem('refresh_token', data.refresh_token);
                return true;
            }
            return false;
        } catch {
            return false;
        }
    }

    // Auth endpoints
    async login(email: string, password: string) {
        return this.request<any>('/api/v1/auth/login', {
            method: 'POST',
            body: JSON.stringify({ email, password })
        });
    }

    async register(email: string, username: string, password: string, full_name: string) {
        return this.request<any>('/api/v1/auth/register', {
            method: 'POST',
            body: JSON.stringify({ email, username, password, full_name })
        });
    }

    async logout() {
        const refreshToken = localStorage.getItem('refresh_token');
        if (refreshToken) {
            await this.request('/api/v1/auth/logout', {
                method: 'POST',
                body: JSON.stringify({ refresh_token: refreshToken })
            }).catch(() => { });
        }
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
    }

    // User endpoints
    async getCurrentUser() {
        return this.request<any>('/api/v1/users/me');
    }

    async updateCurrentUser(data: any) {
        return this.request<any>('/api/v1/users/me', {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    }

    async listUsers(params?: { search?: string; role?: string }) {
        const queryParams = new URLSearchParams();
        if (params?.search) queryParams.append('search', params.search);
        if (params?.role) queryParams.append('role', params.role);

        const queryString = queryParams.toString();
        const url = `/api/v1/users${queryString ? `?${queryString}` : ''}`;

        return this.request<any[]>(url);
    }

    async adminUpdateUser(userId: string, data: any) {
        return this.request<any>(`/api/v1/users/${userId}`, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    }

    async updateUserRole(userId: string, role: string) {
        return this.request<any>(`/api/v1/users/${userId}/role`, {
            method: 'PUT',
            body: JSON.stringify({ role })
        });
    }

    async changePassword(data: any) {
        return this.request<any>('/api/v1/users/me/password', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }

    async uploadAvatar(file: File) {
        const formData = new FormData();
        formData.append('file', file);

        const token = localStorage.getItem('access_token');
        const response = await fetch(`${this.baseURL}/api/v1/users/me/avatar`, {
            method: 'POST',
            headers: {
                ...(token && { 'Authorization': `Bearer ${token}` })
            },
            body: formData
        });

        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: 'Upload failed' }));
            throw new Error(error.detail || 'Upload failed');
        }

        return response.json();
    }

    // Deployment endpoints
    async listDeployments() {
        return this.request<any[]>('/api/v1/deployments');
    }

    async getDeployment(id: string) {
        return this.request<any>(`/api/v1/deployments/${id}`);
    }

    async createDeployment(data: any) {
        return this.request<any>('/api/v1/deployments', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }

    async updateDeployment(id: string, data: any) {
        return this.request<any>(`/api/v1/deployments/${id}`, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    }

    async deleteDeployment(id: string) {
        return this.request<any>(`/api/v1/deployments/${id}`, {
            method: 'DELETE'
        });
    }
}

export const api = new ApiService();
export default api;
