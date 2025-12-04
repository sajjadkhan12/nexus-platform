import { apiClient } from './client';
import { buildQueryString } from './helpers';

/**
 * Notifications API
 * Handles notification retrieval and management
 */
export const notificationsApi = {
    async getNotifications(unreadOnly = false) {
        const query = buildQueryString({ unread_only: unreadOnly });
        return apiClient.request(`/api/v1/notifications${query}`);
    },

    async markNotificationRead(id: string) {
        return apiClient.request(`/api/v1/notifications/${id}/read`, {
            method: 'PUT'
        });
    },

    async markAllNotificationsRead() {
        return apiClient.request('/api/v1/notifications/read-all', {
            method: 'PUT'
        });
    }
};
