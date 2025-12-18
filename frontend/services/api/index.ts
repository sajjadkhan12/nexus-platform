/**
 * API Services Index
 * 
 * This file exports all API modules and provides a unified API object
 * for backward compatibility with existing code.
 */

export { apiClient } from './client';
export { authApi } from './auth';
export { usersApi } from './users';
export { groupsApi } from './groups';
export { rolesApi } from './roles';
export { deploymentsApi } from './deployments';
export { pluginsApi } from './plugins';
export { provisioningApi } from './provisioning';
export { notificationsApi } from './notifications';
export { auditApi } from './audit';

// Unified API object for backward compatibility
import { authApi } from './auth';
import { usersApi } from './users';
import { groupsApi } from './groups';
import { rolesApi } from './roles';
import { deploymentsApi } from './deployments';
import { pluginsApi } from './plugins';
import { provisioningApi } from './provisioning';
import { notificationsApi } from './notifications';
import { auditApi } from './audit';
import { apiClient } from './client';

/**
 * Unified API object that combines all API modules
 * This maintains backward compatibility with the old api.ts structure
 */
const api = {
    // Base client
    request: apiClient.request.bind(apiClient),

    // Auth
    ...authApi,

    // Users
    ...usersApi,

    // Groups
    ...groupsApi,

    // Roles
    ...rolesApi,

    // Deployments (spread for backward compatibility)
    ...deploymentsApi,

    // Plugins
    ...pluginsApi,

    // Provisioning
    ...provisioningApi,

    // Notifications
    ...notificationsApi,

    // Audit Logs
    ...auditApi,

    // Nested API objects for explicit access
    deploymentsApi,
    pluginsApi,
    provisioningApi,
    notificationsApi,
    auditApi,
    authApi,
    usersApi,
    groupsApi,
    rolesApi
};

export default api;
