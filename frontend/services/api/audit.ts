/**
 * Audit Logs API Service
 */
import { apiClient } from './client';

export interface AuditLog {
    id: string;
    user_id?: string;
    action: string;
    resource_type?: string;
    resource_id?: string;
    details?: Record<string, any>;
    ip_address?: string;
    created_at: string;
    user?: {
        id: string;
        email: string;
        username: string;
        full_name?: string;
        avatar_url?: string;
    };
}

export interface AuditLogListResponse {
    items: AuditLog[];
    total: number;
    skip: number;
    limit: number;
}

export interface AuditLogFilters {
    skip?: number;
    limit?: number;
    user_id?: string;
    action?: string;
    resource_type?: string;
    resource_id?: string;
    start_date?: string;
    end_date?: string;
    search?: string;
    status?: 'success' | 'failure';
}

/**
 * List audit logs with filtering and pagination
 */
export async function listAuditLogs(filters: AuditLogFilters = {}): Promise<AuditLogListResponse> {
    const params = new URLSearchParams();
    
    if (filters.skip !== undefined) params.append('skip', filters.skip.toString());
    if (filters.limit !== undefined) params.append('limit', filters.limit.toString());
    if (filters.user_id) params.append('user_id', filters.user_id);
    if (filters.action) params.append('action', filters.action);
    if (filters.resource_type) params.append('resource_type', filters.resource_type);
    if (filters.resource_id) params.append('resource_id', filters.resource_id);
    if (filters.start_date) params.append('start_date', filters.start_date);
    if (filters.end_date) params.append('end_date', filters.end_date);
    if (filters.search) params.append('search', filters.search);
    if (filters.status) params.append('status', filters.status);
    
    const queryString = params.toString();
    const endpoint = `/api/v1/audit-logs${queryString ? `?${queryString}` : ''}`;
    
    return apiClient.request<AuditLogListResponse>(endpoint);
}

/**
 * Get a single audit log by ID
 */
export async function getAuditLog(logId: string): Promise<AuditLog> {
    return apiClient.request<AuditLog>(`/api/v1/audit-logs/${logId}`);
}

export const auditApi = {
    listAuditLogs,
    getAuditLog,
};

