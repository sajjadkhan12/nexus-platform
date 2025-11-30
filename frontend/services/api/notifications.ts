import { apiClient } from './client';

/**
 * Notifications API
 * Handles notification retrieval and management
 */
export const notificationsApi = {
    async getNotifications(unreadOnly = false) {
        return apiClient.request(`/api/v1/notifications?unread_only=${unreadOnly}`);
    },

    async markNotificationRead(id: string) {
        return apiClient.request(`/api/v1/notifications/${id}/read`, {
            method: 'POST'
        });
    },

    async markAllNotificationsRead() {
        return apiClient.request('/api/v1/notifications/read-all', {
            method: 'POST'
        });
    }
};
