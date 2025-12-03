import { apiClient } from './client';
import { API_URL } from '../../constants/api';

/**
 * Helper function for file uploads
 * Centralizes file upload logic to avoid duplication
 */
export async function uploadFile(
    endpoint: string,
    file: File,
    fieldName: string = 'file'
): Promise<any> {
    const formData = new FormData();
    formData.append(fieldName, file);

    const token = localStorage.getItem('access_token');
    const response = await fetch(`${API_URL}${endpoint}`, {
        method: 'POST',
        headers: {
            ...(token ? { Authorization: `Bearer ${token}` } : {})
        },
        credentials: 'include',
        body: formData
    });

    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: response.statusText }));
        throw new Error(error.detail || 'File upload failed');
    }

    return response.json();
}

/**
 * Helper function to build query strings from params
 */
export function buildQueryString(params?: Record<string, string | number | boolean | undefined>): string {
    if (!params) return '';
    
    const queryParams = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== '') {
            queryParams.append(key, String(value));
        }
    });
    
    const query = queryParams.toString();
    return query ? `?${query}` : '';
}

/**
 * Generic CRUD operations helper
 * Reduces boilerplate for standard CRUD endpoints
 */
export function createCrudApi(basePath: string) {
    return {
        async list<T = any>(params?: Record<string, string | number | boolean | undefined>): Promise<T> {
            const query = buildQueryString(params);
            return apiClient.request<T>(`${basePath}${query}`);
        },

        async get<T = any>(id: string): Promise<T> {
            return apiClient.request<T>(`${basePath}/${id}`);
        },

        async create<T = any>(data: any): Promise<T> {
            return apiClient.request<T>(basePath, {
                method: 'POST',
                body: JSON.stringify(data)
            });
        },

        async update<T = any>(id: string, data: any): Promise<T> {
            return apiClient.request<T>(`${basePath}/${id}`, {
                method: 'PUT',
                body: JSON.stringify(data)
            });
        },

        async delete(id: string): Promise<void> {
            return apiClient.request(`${basePath}/${id}`, {
                method: 'DELETE'
            });
        }
    };
}

