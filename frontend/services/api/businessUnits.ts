import { apiClient } from './client';

export interface BusinessUnit {
    id: string;
    name: string;
    slug: string;
    description?: string;
    role?: string;  // Role name (e.g., "bu-owner", "developer", "viewer")
    member_count?: number;  // Number of members in this business unit
    can_manage_members?: boolean;  // Whether user has business_units:manage_members permission
}

export interface BusinessUnitMember {
    id: string;
    business_unit_id: string;
    user_id: string;
    user_email: string;
    user_name?: string;
    role: string;  // Role name (e.g., "bu-owner", "developer", "viewer")
    role_id?: string;  // Role ID (optional, for reference)
    created_at: string;
}

export interface BusinessUnitCreate {
    name: string;
    slug: string;
    description?: string;
}

export interface BusinessUnitUpdate {
    name?: string;
    description?: string;
    is_active?: boolean;
}

export interface BusinessUnitMemberAdd {
    user_email: string;
    role_id?: string;  // Role ID (UUID)
    role?: string;  // Role name (for backward compatibility)
}

export const businessUnitsApi = {
    async listBusinessUnits(): Promise<BusinessUnit[]> {
        return apiClient.request<BusinessUnit[]>('/api/v1/business-units');
    },

    async getBusinessUnit(businessUnitId: string): Promise<BusinessUnit> {
        return apiClient.request<BusinessUnit>(`/api/v1/business-units/${businessUnitId}`);
    },

    async createBusinessUnit(data: BusinessUnitCreate): Promise<BusinessUnit> {
        return apiClient.request<BusinessUnit>('/api/v1/business-units', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    },

    async updateBusinessUnit(businessUnitId: string, data: BusinessUnitUpdate): Promise<BusinessUnit> {
        return apiClient.request<BusinessUnit>(`/api/v1/business-units/${businessUnitId}`, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    },

    async deleteBusinessUnit(businessUnitId: string): Promise<void> {
        return apiClient.request<void>(`/api/v1/business-units/${businessUnitId}`, {
            method: 'DELETE'
        });
    },

    async setActiveBusinessUnit(businessUnitId: string): Promise<void> {
        return apiClient.request<void>(`/api/v1/business-units/users/me/active-business-unit?business_unit_id=${businessUnitId}`, {
            method: 'POST'
        });
    },

    async getActiveBusinessUnit(): Promise<{ business_unit_id: string | null }> {
        return apiClient.request<{ business_unit_id: string | null }>('/api/v1/business-units/users/me/active-business-unit');
    },

    async listMembers(businessUnitId: string): Promise<BusinessUnitMember[]> {
        return apiClient.request<BusinessUnitMember[]>(`/api/v1/business-units/${businessUnitId}/members`);
    },

    async addMember(businessUnitId: string, data: BusinessUnitMemberAdd): Promise<BusinessUnitMember> {
        return apiClient.request<BusinessUnitMember>(`/api/v1/business-units/${businessUnitId}/members`, {
            method: 'POST',
            body: JSON.stringify(data)
        });
    },

    async removeMember(businessUnitId: string, userId: string): Promise<void> {
        return apiClient.request<void>(`/api/v1/business-units/${businessUnitId}/members/${userId}`, {
            method: 'DELETE'
        });
    },

    async getAvailableRoles(): Promise<any[]> {
        return apiClient.request<any[]>('/api/v1/business-units/roles/available');
    },

    async getAvailableUsers(search?: string): Promise<any[]> {
        const url = search 
            ? `/api/v1/business-units/users/available?search=${encodeURIComponent(search)}`
            : '/api/v1/business-units/users/available';
        return apiClient.request<any[]>(url);
    }
};

