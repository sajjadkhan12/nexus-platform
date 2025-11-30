# API Services Architecture

This directory contains the modular API client implementation for the DevPlatform IDP frontend.

## 📁 Structure

```
services/
├── api/
│   ├── index.ts           # Main exports & unified API object
│   ├── client.ts          # Base API client with auth & token refresh
│   ├── auth.ts            # Authentication (login, logout, register)
│   ├── users.ts           # User management & profiles
│   ├── groups.ts          # Group management
│   ├── roles.ts           # Role & permission management
│   ├── deployments.ts     # Deployment CRUD operations
│   ├── plugins.ts         # Plugin upload & management
│   ├── provisioning.ts    # Infrastructure provisioning & jobs
│   └── notifications.ts   # Notifications
└── api.ts                 # Legacy export for backward compatibility
```

## 🎯 Usage

### New Code (Recommended)

Import only what you need for better tree-shaking and code organization:

```typescript
// Import specific modules
import { authApi } from '@/services/api/auth';
import { usersApi } from '@/services/api/users';
import { groupsApi } from '@/services/api/groups';

// Use them
const users = await usersApi.listUsers({ search: 'john' });
const groups = await groupsApi.listGroups();
```

### Existing Code (Backward Compatible)

The old import pattern still works:

```typescript
import api from '@/services/api';

// All methods available as before
const users = await api.listUsers({ search: 'john' });
const groups = await api.listGroups();
```

## 📦 Available Modules

### `client.ts` - Base API Client
- `apiClient.request<T>(endpoint, options)` - Generic HTTP request handler
- `apiClient.refreshToken()` - Auto token refresh
- `apiClient.getAuthHeaders()` - JWT headers

### `auth.ts` - Authentication
- `authApi.login(email, password)`
- `authApi.register(email, password, full_name)`
- `authApi.logout()`

### `users.ts` - User Management
- `usersApi.getCurrentUser()`
- `usersApi.updateCurrentUser(data)`
- `usersApi.listUsers(params?)`
- `usersApi.createUser(data)`
- `usersApi.adminUpdateUser(userId, data)`
- `usersApi.deleteUser(userId)`
- `usersApi.changePassword(data)`
- `usersApi.uploadAvatar(file)`

### `groups.ts` - Group Management
- `groupsApi.listGroups()`
- `groupsApi.createGroup(data)`
- `groupsApi.updateGroup(groupId, data)`
- `groupsApi.deleteGroup(groupId)`
- `groupsApi.addUserToGroup(groupId, userId)`
- `groupsApi.removeUserFromGroup(groupId, userId)`
- `groupsApi.addRoleToGroup(groupId, roleId)`
- `groupsApi.removeRoleFromGroup(groupId, roleId)`

### `roles.ts` - Role Management
- `rolesApi.listRoles()`
- `rolesApi.createRole(data)`
- `rolesApi.updateRole(roleId, data)`
- `rolesApi.deleteRole(roleId)`
- `rolesApi.getAdminStats()`

### `deployments.ts` - Deployments
- `deploymentsApi.listDeployments()`
- `deploymentsApi.getDeployment(id)`
- `deploymentsApi.createDeployment(data)`
- `deploymentsApi.updateDeployment(id, data)`
- `deploymentsApi.deleteDeployment(id)`

### `plugins.ts` - Plugins
- `pluginsApi.uploadPlugin(file)`
- `pluginsApi.listPlugins()`
- `pluginsApi.getPlugin(pluginId)`
- `pluginsApi.getPluginVersions(pluginId)`
- `pluginsApi.deletePlugin(pluginId)`

### `provisioning.ts` - Infrastructure Provisioning
- `provisioningApi.provisionInfrastructure(data)`
- `provisioningApi.listCredentials()`
- `provisioningApi.createCredential(data)`
- `provisioningApi.updateCredential(credId, data)`
- `provisioningApi.deleteCredential(credId)`
- `provisioningApi.getJob(jobId)`
- `provisioningApi.getJobLogs(jobId)`
- `provisioningApi.listJobs(params?)`

### `notifications.ts` - Notifications
- `notificationsApi.getNotifications(unreadOnly?)`
- `notificationsApi.markNotificationRead(id)`
- `notificationsApi.markAllNotificationsRead()`

## ✨ Benefits

### 1. **Better Code Organization**
- Each feature domain has its own file
- Easier to find and maintain API calls
- Clear separation of concerns

### 2. **Improved Developer Experience**
- Auto-complete works better with smaller modules
- Easier to understand what APIs are available
- Self-documenting through module names

### 3. **Better Performance**
- Tree-shaking can remove unused API modules
- Smaller bundle sizes
- Faster compilation

### 4. **Easier Testing**
- Can mock individual modules
- Test each API domain independently
- More focused test files

### 5. **Team Collaboration**
- Reduces merge conflicts (fewer people editing same file)
- Clear ownership of API domains
- Easier to review changes

## 🔄 Migration Guide

### Step 1: Update Imports (Optional)
For new features or when refactoring, prefer modular imports:

```diff
- import api from '@/services/api';
+ import { usersApi } from '@/services/api/users';
+ import { groupsApi } from '@/services/api/groups';
```

### Step 2: Update Usage (Optional)
```diff
- const users = await api.listUsers();
+ const users = await usersApi.listUsers();
```

### No Breaking Changes!
Your existing code will continue to work without any changes. The old `api.ts` re-exports everything from the new modules.

## 🏗️ Architecture

```
Component/Page
    ↓
usersApi.listUsers()
    ↓
apiClient.request('/api/v1/users')
    ↓
- Add JWT headers
- Handle 401 (auto-refresh token)
- Parse response
    ↓
Return data or throw error
```

## 🔐 Authentication Flow

1. User logs in → `authApi.login()`
2. Access token stored in localStorage
3. All requests include token via `apiClient.getAuthHeaders()`
4. If 401 error → `apiClient.refreshToken()` auto-called
5. Original request retried with new token
6. If refresh fails → redirect to login

## 📝 Adding New API Endpoints

1. **Choose the right module** or create a new one in `api/`
2. **Add the method**:
   ```typescript
   async myNewEndpoint(param: string) {
       return apiClient.request(`/api/v1/my-endpoint/${param}`);
   }
   ```
3. **Export from index.ts**
4. **Use in components**

## 🎓 Best Practices

1. **Use TypeScript types** for request/response data
2. **Handle errors** at the component level
3. **Use async/await** instead of promises
4. **Leverage modular imports** for new code
5. **Document complex endpoints** with JSDoc comments

## 🤝 Contributing

When adding new API endpoints:
- Place them in the appropriate module
- Update this README
- Add TypeScript types if possible
- Test with real backend
