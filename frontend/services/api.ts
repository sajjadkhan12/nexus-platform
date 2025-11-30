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

        if (response.status === 204) {
            return {} as T;
        }

        return response.json();
    }

    async refreshToken(): Promise<boolean> {
        try {
            const response = await fetch(`${this.baseURL}/api/v1/auth/refresh`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                // Credentials include is required to send cookies
                credentials: 'include'
            });

            if (response.ok) {
                const data = await response.json();
                localStorage.setItem('access_token', data.access_token);
                // Refresh token is handled via HTTP-only cookie
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

    async register(email: string, password: string, full_name: string) {
        return this.request<any>('/api/v1/auth/register', {
            method: 'POST',
            body: JSON.stringify({ email, password, full_name })
        });
    }

    async logout() {
        await this.request('/api/v1/auth/logout', {
            method: 'POST'
        }).catch(() => { });

        localStorage.removeItem('access_token');
        // Refresh token cookie will be cleared by server response or ignored
    }

    // User endpoints
    async getCurrentUser() {
        return this.request<any>(`/api/v1/users/me?t=${new Date().getTime()}`);
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
        const url = `/api/v1/users/${queryString ? `?${queryString}` : ''}${queryString ? '&' : '?'}t=${new Date().getTime()}`;

        return this.request<any[]>(url);
    }

    async createUser(data: any) {
        return this.request<any>('/api/v1/users/', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }

    async adminUpdateUser(userId: string, data: any) {
        return this.request<any>(`/api/v1/users/${userId}`, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    }

    async deleteUser(userId: string) {
        return this.request<void>(`/api/v1/users/${userId}`, {
            method: 'DELETE'
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
                // Don't set Content-Type - browser will set it automatically for FormData
            },
            body: formData
        });

        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: 'Upload failed' }));
            throw new Error(error.detail || 'Upload failed');
        }

        return response.json();
    }

    // Group Management
    async listGroups() {
        return this.request<any[]>('/api/v1/groups/');
    }

    async createGroup(data: { name: string; description?: string }) {
        return this.request<any>('/api/v1/groups/', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }

    async updateGroup(groupId: string, data: { name?: string; description?: string }) {
        return this.request<any>(`/api/v1/groups/${groupId}`, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    }

    async deleteGroup(groupId: string) {
        return this.request<void>(`/api/v1/groups/${groupId}`, {
            method: 'DELETE'
        });
    }

    async addUserToGroup(groupId: string, userId: string) {
        return this.request<void>(`/api/v1/groups/${groupId}/users/${userId}`, {
            method: 'POST'
        });
    }

    async removeUserFromGroup(groupId: string, userId: string) {
        return this.request<void>(`/api/v1/groups/${groupId}/users/${userId}`, {
            method: 'DELETE'
        });
    }

    async addRoleToGroup(groupId: string, roleId: string) {
        return this.request<void>(`/api/v1/groups/${groupId}/roles/${roleId}`, {
            method: 'POST'
        });
    }

    async removeRoleFromGroup(groupId: string, roleId: string) {
        return this.request<void>(`/api/v1/groups/${groupId}/roles/${roleId}`, {
            method: 'DELETE'
        });
    }

    async listRoles() {
        return this.request<any[]>('/api/v1/roles/');
    }

    async createRole(data: { name: string; description: string; permissions: string[] }) {
        return this.request<any>('/api/v1/roles/', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }

    async updateRole(roleId: string, data: { name?: string; description?: string; permissions?: string[] }) {
        return this.request<any>(`/api/v1/roles/${roleId}`, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    }

    async deleteRole(roleId: string) {
        return this.request<void>(`/api/v1/roles/${roleId}`, {
            method: 'DELETE'
        });
    }

    async getAdminStats() {
        return this.request<any>('/api/v1/users/stats');
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

    // Plugin system endpoints
    async uploadPlugin(file: File) {
        const formData = new FormData();
        formData.append('file', file);

        const token = localStorage.getItem('access_token');
        const response = await fetch(`${this.baseURL}/api/v1/plugins/upload`, {
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

    async listPlugins() {
        return this.request<any[]>('/api/v1/plugins/');
    }

    async getPlugin(pluginId: string) {
        return this.request<any>(`/api/v1/plugins/${pluginId}`);
    }

    async getPluginVersions(pluginId: string) {
        return this.request<any[]>(`/api/v1/plugins/${pluginId}/versions`);
    }

    async deletePlugin(pluginId: string) {
        return this.request<void>(`/api/v1/plugins/${pluginId}`, {
            method: 'DELETE'
        });
    }


    // Cloud credentials
    async createCredential(data: any) {
        return this.request<any>('/api/v1/admin/credentials/', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }

    async listCredentials() {
        return this.request<any[]>('/api/v1/admin/credentials/');
    }

    async deleteCredential(credentialId: number) {
        return this.request<void>(`/api/v1/admin/credentials/${credentialId}`, {
            method: 'DELETE'
        });
    }

    // Provisioning
    async provision(data: { plugin_id: string; version: string; inputs: any }) {
        return this.request<any>('/api/v1/provision/', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }

    async getJob(jobId: string) {
        return this.request<any>(`/api/v1/provision/jobs/${jobId}`);
    }

    async getJobLogs(jobId: string) {
        return this.request<any[]>(`/api/v1/provision/jobs/${jobId}/logs`);
    }

    async listJobs(params?: { jobId?: string; limit?: number }) {
        const queryParams = new URLSearchParams();
        if (params?.jobId) queryParams.append('job_id', params.jobId);
        if (params?.limit) queryParams.append('limit', params.limit.toString());

        const queryString = queryParams.toString();
        return this.request<any[]>(`/api/v1/provision/jobs${queryString ? `?${queryString}` : ''}`);
    }

    // Notifications
    async getNotifications(unreadOnly = false) {
        return this.request<any[]>(`/api/v1/notifications?unread_only=${unreadOnly}`);
    }

    async markNotificationRead(id: string) {
        return this.request<any>(`/api/v1/notifications/${id}/read`, {
            method: 'PUT'
        });
    }

    async markAllNotificationsRead() {
        return this.request<any>('/api/v1/notifications/read-all', {
            method: 'PUT'
        });
    }
}

export const api = new ApiService();
export default api;
