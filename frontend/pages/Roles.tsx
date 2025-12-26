import React, { useState, useEffect } from 'react';
import { appLogger } from '../utils/logger';
import { Shield, Plus, Edit2, Trash2, X, Save, Check } from 'lucide-react';
import api from '../services/api';
import { Pagination } from '../components/Pagination';

interface Permission {
    id?: string;
    slug: string;
    name?: string;
    description?: string;
    category?: string;
    resource?: string;
    action?: string;
    environment?: string;
    icon?: string;
    created_at?: string;
}

interface Role {
    id: string;
    name: string;
    description: string;
    permissions: Permission[];
    created_at: string;
    is_platform_role?: boolean;
}

// Permission categories - now using new format (resource:action:environment)
// Categories will be dynamically determined from permission metadata
// This is kept for backward compatibility but will be replaced by category from API
const PERMISSION_CATEGORIES = {
    'Profile': ['profile:read', 'profile:update'],
    'User Management': ['users:list', 'users:read', 'users:create', 'users:update', 'users:delete'],
    'Role Management': ['roles:list', 'roles:read', 'roles:create', 'roles:update', 'roles:delete'],
    'Group Management': ['groups:list', 'groups:read', 'groups:create', 'groups:update', 'groups:delete', 'groups:manage'],
    'Permission Management': ['permissions:list'],
    'Deployment Management': ['deployments:list', 'deployments:read', 'deployments:update', 'deployments:delete'],
    'Deployment - Development': ['deployments:create:development', 'deployments:update:development', 'deployments:delete:development'],
    'Deployment - Staging': ['deployments:create:staging', 'deployments:update:staging', 'deployments:delete:staging'],
    'Deployment - Production': ['deployments:create:production', 'deployments:update:production', 'deployments:delete:production'],
    'Plugin Management': ['plugins:upload', 'plugins:delete', 'plugins:provision'],
    'Audit': ['audit:read'],
};

export const RolesPage: React.FC = () => {
    const [roles, setRoles] = useState<Role[]>([]);
    const [permissions, setPermissions] = useState<Permission[]>([]);
    const [loading, setLoading] = useState(true);
    const [loadingRoleDetails, setLoadingRoleDetails] = useState(false);
    const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
    const [isEditModalOpen, setIsEditModalOpen] = useState(false);
    const [selectedRole, setSelectedRole] = useState<Role | null>(null);
    const [formData, setFormData] = useState({ name: '', description: '', is_platform_role: false });
    const [selectedPermissions, setSelectedPermissions] = useState<Set<string>>(new Set());
    const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null);
    const [currentPage, setCurrentPage] = useState(1);
    const [itemsPerPage, setItemsPerPage] = useState(50);
    const [totalItems, setTotalItems] = useState(0);

    const fetchRoles = async () => {
        setLoading(true);
        try {
            const skip = (currentPage - 1) * itemsPerPage;
            const response = await api.listRoles({ skip, limit: itemsPerPage });
            
            // Handle both old format (array) and new format (object with items/total)
            if (Array.isArray(response)) {
                setRoles(response);
                setTotalItems(response.length);
            } else {
                setRoles(response.items || []);
                setTotalItems(response.total || 0);
            }
        } catch (error) {
            appLogger.error('Failed to fetch roles:', error);
        } finally {
            setLoading(false);
        }
    };

    const fetchPermissions = async () => {
        try {
            const data = await api.request<Permission[]>('/api/v1/permissions/');
            setPermissions(data);
        } catch (error) {
            appLogger.error('Failed to fetch permissions:', error);
        }
    };

    useEffect(() => {
        fetchRoles();
        fetchPermissions();
    }, [currentPage, itemsPerPage]);


    const handleCreateRole = async () => {
        try {
            // Convert normalized slugs back to original format by matching with available permissions
            // Also strip BU-scoped prefixes if present
            const permissionSlugs = Array.from(selectedPermissions).map(normalizedSlug => {
                // Remove BU prefix if present (bu:{uuid}:...)
                const buPrefixPattern = /^bu:[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}:/i;
                let cleanSlug = normalizedSlug.replace(buPrefixPattern, '');
                // Try to find the original permission slug from the permissions list
                const originalPerm = permissions.find(p => p.slug.toLowerCase() === cleanSlug.toLowerCase());
                return originalPerm ? originalPerm.slug : cleanSlug;
            });
            
            await api.createRole({
                name: formData.name,
                description: formData.description,
                permissions: permissionSlugs,
                is_platform_role: formData.is_platform_role
            });
            setMessage({ type: 'success', text: 'Role created successfully' });
            setIsCreateModalOpen(false);
            setFormData({ name: '', description: '', is_platform_role: false });
            setSelectedPermissions(new Set());
            fetchRoles();
        } catch (error: any) {
            setMessage({ type: 'error', text: error.message || 'Failed to create role' });
        }
    };

    const handleUpdateRole = async () => {
        if (!selectedRole) return;
        try {
            // Strip BU-scoped prefixes from permission slugs before sending
            // Format: "bu:{uuid}:resource:action" -> "resource:action"
            const cleanPermissionSlugs = Array.from(selectedPermissions).map(slug => {
                // Remove BU prefix if present (bu:{uuid}:...)
                const buPrefixPattern = /^bu:[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}:/i;
                let cleanSlug = slug.replace(buPrefixPattern, '');
                // Try to find the original permission slug from the permissions list
                const originalPerm = permissions.find(p => p.slug.toLowerCase() === cleanSlug.toLowerCase());
                return originalPerm ? originalPerm.slug : cleanSlug;
            });
            
            await api.updateRole(selectedRole.id, {
                name: formData.name,
                description: formData.description,
                permissions: cleanPermissionSlugs,
                is_platform_role: formData.is_platform_role
            });
            setMessage({ type: 'success', text: 'Role updated successfully' });
            setIsEditModalOpen(false);
            fetchRoles();
        } catch (error: any) {
            setMessage({ type: 'error', text: error.message || 'Failed to update role' });
        }
    };

    const handleDeleteRole = async (roleId: string) => {
        if (!confirm('Are you sure you want to delete this role? This action cannot be undone.')) return;
        try {
            await api.deleteRole(roleId);
            setMessage({ type: 'success', text: 'Role deleted successfully' });
            fetchRoles();
        } catch (error: any) {
            setMessage({ type: 'error', text: error.message || 'Failed to delete role' });
        }
    };

    const togglePermission = (permSlug: string) => {
        setSelectedPermissions(prev => {
            const newSet = new Set(prev);
            const normalizedSlug = permSlug.toLowerCase().trim();
            // Check both normalized and original format
            const hasNormalized = newSet.has(normalizedSlug);
            const hasOriginal = newSet.has(permSlug);
            
            if (hasNormalized || hasOriginal) {
                // Remove both normalized and original if they exist
                newSet.delete(normalizedSlug);
                newSet.delete(permSlug);
            } else {
                // Add normalized version for consistency
                newSet.add(normalizedSlug);
            }
            return newSet;
        });
    };

    const openCreateModal = () => {
        setFormData({ name: '', description: '', is_platform_role: false });
        setSelectedPermissions(new Set());
        setIsCreateModalOpen(true);
        setMessage(null);
    };

    const openEditModal = async (role: Role) => {
        setLoadingRoleDetails(true);
        try {
            // Ensure permissions are loaded first
            if (permissions.length === 0) {
                await fetchPermissions();
            }
            
            // Fetch full role details to ensure we have all permissions
            const fullRole = await api.getRole(role.id);
            setSelectedRole(fullRole);
            setFormData({ 
                name: fullRole.name, 
                description: fullRole.description || '',
                is_platform_role: fullRole.is_platform_role || false
            });
            
            // Extract permission slugs from the fetched role
            // Handle both array format and object format
            let permissionSlugs: string[] = [];
            if (fullRole.permissions && Array.isArray(fullRole.permissions)) {
                permissionSlugs = fullRole.permissions.map((p: any) => {
                    // Handle both object with slug property and string format
                    let slug: string | null = null;
                    if (typeof p === 'string') {
                        slug = p.trim();
                    } else if (p && typeof p === 'object' && 'slug' in p) {
                        slug = String(p.slug).trim();
                    }
                    return slug;
                }).filter((slug: string | null): slug is string => slug !== null && slug.length > 0);
            }
            
            // IMPORTANT: Normalize permission slugs to lowercase for consistent matching
            // This ensures that permissions from the role match permissions in the list
            const normalizedSlugs = permissionSlugs.map(slug => slug.trim().toLowerCase());
            
            // Verify that we have permissions loaded
            if (permissions.length === 0) {
                appLogger.warn('No permissions loaded from API. Role permissions may not display correctly.');
            }
            
            // Create a Set with normalized slugs for comparison
            // This Set will be used to check which permissions are already assigned
            setSelectedPermissions(new Set(normalizedSlugs));
            setIsEditModalOpen(true);
            setMessage(null);
        } catch (error: any) {
            appLogger.error('Failed to fetch role details:', error);
            // Fallback to role from list if fetch fails
            setSelectedRole(role);
            setFormData({ 
                name: role.name, 
                description: role.description || '',
                is_platform_role: role.is_platform_role || false
            });
            
            // Extract permissions from role object (fallback)
            let permissionSlugs: string[] = [];
            if (role.permissions && Array.isArray(role.permissions)) {
                permissionSlugs = role.permissions.map((p: any) => {
                    if (typeof p === 'string') {
                        return p.trim().toLowerCase();
                    } else if (p && typeof p === 'object' && 'slug' in p) {
                        return String(p.slug).trim().toLowerCase();
                    }
                    return null;
                }).filter((slug: string | null): slug is string => slug !== null && slug.length > 0);
            }
            
            setSelectedPermissions(new Set(permissionSlugs));
            setIsEditModalOpen(true);
            setMessage({ type: 'error', text: 'Failed to load role details. Some permissions may not be shown.' });
        } finally {
            setLoadingRoleDetails(false);
        }
    };

    return (
        <div className="max-w-7xl mx-auto space-y-6">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div>
                    <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Role Management</h1>
                    <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">Define roles and assign permissions</p>
                </div>
                <button
                    onClick={openCreateModal}
                    className="px-4 py-2 bg-orange-600 text-white rounded-lg hover:bg-orange-700 flex items-center gap-2"
                >
                    <Plus className="w-4 h-4" /> Create Role
                </button>
            </div>

            {message && (
                <div className={`p-4 rounded-lg ${message.type === 'success' ? 'bg-green-50 text-green-700 dark:bg-green-900/20 dark:text-green-400' : 'bg-red-50 text-red-700 dark:bg-red-900/20 dark:text-red-400'}`}>
                    {message.text}
                </div>
            )}

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {loading ? (
                    <p className="text-gray-500 dark:text-gray-400">Loading roles...</p>
                ) : roles.map((role) => (
                    <div key={role.id} className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-6 shadow-sm hover:shadow-md transition-shadow">
                        <div className="flex justify-between items-start mb-4">
                            <div className="p-2 bg-orange-50 dark:bg-orange-900/20 rounded-lg">
                                <Shield className="w-6 h-6 text-orange-600 dark:text-orange-400" />
                            </div>
                            <div className="flex gap-2">
                                <button
                                    onClick={() => openEditModal(role)}
                                    className="p-1.5 text-gray-400 hover:text-orange-600 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
                                >
                                    <Edit2 className="w-4 h-4" />
                                </button>
                                <button
                                    onClick={() => handleDeleteRole(role.id)}
                                    className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
                                >
                                    <Trash2 className="w-4 h-4" />
                                </button>
                            </div>
                        </div>
                        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-1">{role.name}</h3>
                        <p className="text-sm text-gray-500 dark:text-gray-400 mb-4 h-10 line-clamp-2">{role.description || 'No description'}</p>

                        <div className="pt-4 border-t border-gray-100 dark:border-gray-800">
                            <span className="text-sm text-gray-500 dark:text-gray-400">{role.permissions?.length || 0} permissions</span>
                        </div>
                    </div>
                ))}
            </div>

            {/* Pagination */}
            {totalItems > 0 && (
                <div className="mt-6">
                    <Pagination
                        currentPage={currentPage}
                        totalPages={Math.ceil(totalItems / itemsPerPage)}
                        totalItems={totalItems}
                        itemsPerPage={itemsPerPage}
                        onPageChange={(page) => {
                            setCurrentPage(page);
                            window.scrollTo({ top: 0, behavior: 'smooth' });
                        }}
                        onItemsPerPageChange={(newItemsPerPage) => {
                            setItemsPerPage(newItemsPerPage);
                            setCurrentPage(1);
                        }}
                        showItemsPerPage={true}
                    />
                </div>
            )}

            {/* Create/Edit Modal */}
            {(isCreateModalOpen || isEditModalOpen) && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm overflow-y-auto">
                    <div className="bg-white dark:bg-gray-900 rounded-xl shadow-xl w-full max-w-3xl border border-gray-200 dark:border-gray-800 my-8">
                        <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-800">
                            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                                {isCreateModalOpen ? 'Create New Role' : 'Edit Role'}
                            </h3>
                            <button
                                onClick={() => { setIsCreateModalOpen(false); setIsEditModalOpen(false); }}
                                className="text-gray-400 hover:text-gray-500"
                                disabled={loadingRoleDetails}
                            >
                                <X className="w-5 h-5" />
                            </button>
                        </div>
                        
                        {loadingRoleDetails && (
                            <div className="p-6 text-center">
                                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-orange-600 mx-auto"></div>
                                <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">Loading role details...</p>
                            </div>
                        )}

                        {!loadingRoleDetails && (
                        <div className="p-6 space-y-6 max-h-[60vh] overflow-y-auto">
                            <div>
                                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Role Name</label>
                                <input
                                    type="text"
                                    value={formData.name}
                                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-orange-500"
                                    placeholder="e.g. Senior Engineer"
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Description</label>
                                <textarea
                                    value={formData.description}
                                    onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-orange-500 h-24 resize-none"
                                    placeholder="Describe the role's purpose..."
                                />
                            </div>

                            {/* Platform Role Toggle */}
                            <div className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
                                <div className="flex-1">
                                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                                        Platform Role
                                    </label>
                                    <p className="text-xs text-gray-500 dark:text-gray-400">
                                        {formData.is_platform_role 
                                            ? "This role applies globally across all business units (e.g., admin, security-admin)"
                                            : "This role is scoped to business units (e.g., bu-owner, developer, viewer)"
                                        }
                                    </p>
                                </div>
                                <label className="relative inline-flex items-center cursor-pointer ml-4">
                                    <input
                                        type="checkbox"
                                        checked={formData.is_platform_role}
                                        onChange={(e) => setFormData({ ...formData, is_platform_role: e.target.checked })}
                                        className="sr-only peer"
                                    />
                                    <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-orange-300 dark:peer-focus:ring-orange-800 rounded-full peer dark:bg-gray-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-gray-600 peer-checked:bg-orange-600"></div>
                                </label>
                            </div>

                            {/* Permissions */}
                            <div>
                                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
                                    Permissions
                                    {selectedPermissions.size > 0 && (
                                        <span className="ml-2 text-xs text-orange-600 dark:text-orange-400 font-normal">
                                            ({selectedPermissions.size} selected)
                                        </span>
                                    )}
                                </label>
                                {isEditModalOpen && selectedPermissions.size === 0 && permissions.length > 0 && (
                                    <div className="mb-3 p-2 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded text-xs text-yellow-700 dark:text-yellow-400">
                                        ⚠️ No permissions selected. If this role should have permissions, they may not have loaded correctly. Check the browser console for details.
                                    </div>
                                )}
                                <div className="space-y-6">
                                    {(() => {
                                        // Group permissions by scope (platform, business_unit, user)
                                        const permissionsByScope: Record<string, Permission[]> = {
                                            'Individual': [],
                                            'Platform Level': [],
                                            'Business Unit': []
                                        };
                                        
                                        permissions.forEach(perm => {
                                            const slug = perm.slug.toLowerCase();
                                            if (slug.startsWith('user:')) {
                                                permissionsByScope['Individual'].push(perm);
                                            } else if (slug.startsWith('platform:')) {
                                                permissionsByScope['Platform Level'].push(perm);
                                            } else if (slug.startsWith('business_unit:')) {
                                                permissionsByScope['Business Unit'].push(perm);
                                            } else {
                                                // Fallback for old format - try to determine from category
                                                if (perm.category?.includes('User Specific') || perm.category?.includes('Individual')) {
                                                    permissionsByScope['Individual'].push(perm);
                                                } else if (perm.category?.includes('Platform')) {
                                                    permissionsByScope['Platform Level'].push(perm);
                                                } else {
                                                    permissionsByScope['Business Unit'].push(perm);
                                                }
                                            }
                                        });
                                        
                                        // Define scope order and metadata
                                        const scopeOrder = ['Individual', 'Platform Level', 'Business Unit'];
                                        const scopeMetadata = {
                                            'Individual': { 
                                                title: 'Individual Permissions', 
                                                description: 'User-scoped permissions for personal resources',
                                                icon: '👤',
                                                color: 'blue'
                                            },
                                            'Platform Level': { 
                                                title: 'Platform Level Permissions', 
                                                description: 'Organization-wide permissions for managing users, roles, groups, and platform resources',
                                                icon: '🏢',
                                                color: 'purple'
                                            },
                                            'Business Unit': { 
                                                title: 'Business Unit Permissions', 
                                                description: 'Business unit-scoped permissions for deployments, plugins, and BU resources',
                                                icon: '🏭',
                                                color: 'green'
                                            }
                                        };
                                        
                                        return scopeOrder.map(scope => {
                                            const scopePerms = permissionsByScope[scope];
                                            if (scopePerms.length === 0) return null;
                                            
                                            // Group permissions within scope by resource/category for better organization
                                            const permsByResource: Record<string, Permission[]> = {};
                                            scopePerms.forEach(perm => {
                                                // Extract resource from slug (e.g., "platform:users:list" -> "users")
                                                const parts = perm.slug.split(':');
                                                const resource = parts.length > 1 ? parts[1] : 'Other';
                                                if (!permsByResource[resource]) {
                                                    permsByResource[resource] = [];
                                                }
                                                permsByResource[resource].push(perm);
                                            });
                                            
                                            const sortedResources = Object.keys(permsByResource).sort();
                                            
                                            // Count selected permissions in this scope
                                            const selectedInScope = scopePerms.filter(p => 
                                                selectedPermissions.has(p.slug.toLowerCase())
                                            ).length;
                                            
                                            const metadata = scopeMetadata[scope as keyof typeof scopeMetadata];
                                            
                                            return (
                                                <div key={scope} className="border-2 border-gray-300 dark:border-gray-600 rounded-lg p-5 bg-gray-50 dark:bg-gray-900/50">
                                                    <div className="mb-4">
                                                        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-1 flex items-center gap-2">
                                                            <span className="text-2xl">{metadata.icon}</span>
                                                            {metadata.title}
                                                            {selectedInScope > 0 && (
                                                                <span className="ml-2 text-sm text-orange-600 dark:text-orange-400 font-normal">
                                                                    ({selectedInScope} selected)
                                                                </span>
                                                            )}
                                                        </h3>
                                                        <p className="text-xs text-gray-600 dark:text-gray-400 ml-8">
                                                            {metadata.description}
                                                        </p>
                                                    </div>
                                                    
                                                    <div className="space-y-4 ml-8">
                                                        {sortedResources.map(resource => {
                                                            const resourcePerms = permsByResource[resource];
                                                            const selectedInResource = resourcePerms.filter(p => 
                                                                selectedPermissions.has(p.slug.toLowerCase())
                                                            ).length;
                                                            
                                                            return (
                                                                <div key={resource} className="border border-gray-200 dark:border-gray-700 rounded-lg p-4 bg-white dark:bg-gray-800">
                                                                    <h4 className="text-sm font-medium text-gray-900 dark:text-white mb-3 flex items-center gap-2 capitalize">
                                                                        {resourcePerms[0]?.icon && (
                                                                            <span className="text-lg">{resourcePerms[0].icon}</span>
                                                                        )}
                                                                        {resource.replace(/_/g, ' ')}
                                                                        {selectedInResource > 0 && (
                                                                            <span className="ml-2 text-xs text-orange-600 dark:text-orange-400 font-normal">
                                                                                ({selectedInResource} selected)
                                                                            </span>
                                                                        )}
                                                                    </h4>
                                                                    <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                                                                        {resourcePerms.map(perm => {
                                                                            const permSlugLower = perm.slug.toLowerCase().trim();
                                                                            const isChecked = selectedPermissions.has(permSlugLower);
                                                                            
                                                                            return (
                                                                                <label
                                                                                    key={perm.id || perm.slug}
                                                                                    className={`flex items-center gap-2 p-2.5 rounded-lg cursor-pointer transition-all ${
                                                                                        isChecked 
                                                                                            ? 'bg-orange-50 dark:bg-orange-900/20 border-2 border-orange-300 dark:border-orange-700 shadow-sm' 
                                                                                            : 'border border-transparent hover:bg-gray-50 dark:hover:bg-gray-800 hover:border-gray-200 dark:hover:border-gray-700'
                                                                                    }`}
                                                                                >
                                                                                    <input
                                                                                        type="checkbox"
                                                                                        checked={isChecked}
                                                                                        onChange={() => togglePermission(perm.slug)}
                                                                                        className="w-4 h-4 text-orange-600 bg-white dark:bg-gray-800 border-gray-300 dark:border-gray-600 rounded focus:ring-2 focus:ring-orange-500 focus:ring-offset-0 checked:bg-orange-600 checked:border-orange-600"
                                                                                        aria-label={`Permission ${perm.name || perm.slug}`}
                                                                                        aria-checked={isChecked}
                                                                                    />
                                                                                    <div className="flex-1">
                                                                                        <p className={`text-sm font-medium ${isChecked ? 'text-orange-900 dark:text-orange-100 font-semibold' : 'text-gray-900 dark:text-white'} flex items-center gap-1`}>
                                                                                            {perm.icon && <span>{perm.icon}</span>}
                                                                                            {perm.name || perm.slug}
                                                                                        </p>
                                                                                        {perm.description && (
                                                                                            <p className={`text-xs ${isChecked ? 'text-orange-700 dark:text-orange-300' : 'text-gray-500 dark:text-gray-400'} mt-0.5`}>
                                                                                                {perm.description}
                                                                                            </p>
                                                                                        )}
                                                                                        {!perm.description && perm.slug && (
                                                                                            <p className={`text-xs ${isChecked ? 'text-orange-700 dark:text-orange-300' : 'text-gray-500 dark:text-gray-400'} mt-0.5 font-mono`}>
                                                                                                {perm.slug}
                                                                                            </p>
                                                                                        )}
                                                                                    </div>
                                                                                    {isChecked && (
                                                                                        <Check className="w-5 h-5 text-orange-600 dark:text-orange-400 flex-shrink-0" />
                                                                                    )}
                                                                                </label>
                                                                            );
                                                                        })}
                                                                    </div>
                                                                </div>
                                                            );
                                                        })}
                                                    </div>
                                                </div>
                                            );
                                        });
                                    })()}
                                </div>
                            </div>
                        </div>
                        )}

                        {!loadingRoleDetails && (
                        <div className="flex justify-end gap-3 p-6 border-t border-gray-200 dark:border-gray-800 bg-gray-50 dark:bg-gray-800/50">
                            <button
                                onClick={() => { setIsCreateModalOpen(false); setIsEditModalOpen(false); }}
                                className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
                            >
                                Cancel
                            </button>
                            <button
                                onClick={isCreateModalOpen ? handleCreateRole : handleUpdateRole}
                                className="px-4 py-2 text-sm font-medium text-white bg-orange-600 hover:bg-orange-700 rounded-lg shadow-sm shadow-orange-500/20 flex items-center gap-2"
                            >
                                <Save className="w-4 h-4" /> Save
                            </button>
                        </div>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
};
