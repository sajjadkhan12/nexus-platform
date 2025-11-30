/**
 * API Service - Legacy Export
 * 
 * This file maintains backward compatibility by re-exporting
 * the new modular API structure.
 * 
 * For new code, prefer importing from './api/*' directly:
 * 
 * ✅ Recommended (new code):
 *   import { authApi } from './api/auth';
 *   import { usersApi } from './api/users';
 * 
 * ⚠️ Legacy (existing code):
 *   import api from './api';
 *   api.login(...)
 */

export { default } from './api/index';

// Named exports for modern imports
export {
    apiClient,
    authApi,
    usersApi,
    groupsApi,
    rolesApi,
    deploymentsApi,
    pluginsApi,
    provisioningApi,
    notificationsApi
} from './api/index';
