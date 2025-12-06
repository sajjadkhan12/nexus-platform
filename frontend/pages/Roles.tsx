import React, { useState, useEffect } from 'react';
import { appLogger } from '../utils/logger';
import { Shield, Plus, Edit2, Trash2, X, Save, Check } from 'lucide-react';
import api from '../services/api';
import { Pagination } from '../components/Pagination';

interface Permission {
    id: string;
    slug: string;
    description: string;
}

interface Role {
    id: string;
    name: string;
    description: string;
    permissions: Permission[];
    created_at: string;
}

// Permission categories for better UX
const PERMISSION_CATEGORIES = {
    'Deployments': ['deployment:create', 'deployment:read:own', 'deployment:read:all', 'deployment:update:own', 'deployment:update:all', 'deployment:delete:own', 'deployment:delete:all'],
    'Users': ['user:read:own', 'user:read:all', 'user:manage'],
    'Roles & Groups': ['roles:list', 'roles:create', 'roles:update', 'roles:delete', 'permissions:list', 'groups:list', 'groups:create', 'groups:read', 'groups:update', 'groups:delete', 'groups:manage'],
    'Costs': ['cost:read:own', 'cost:read:all'],
    'Plugins': ['plugin:read', 'plugin:manage'],
    'Settings': ['settings:read', 'settings:manage'],
};

export const RolesPage: React.FC = () => {
    const [roles, setRoles] = useState<Role[]>([]);
    const [permissions, setPermissions] = useState<Permission[]>([]);
    const [loading, setLoading] = useState(true);
    const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
    const [isEditModalOpen, setIsEditModalOpen] = useState(false);
    const [selectedRole, setSelectedRole] = useState<Role | null>(null);
    const [formData, setFormData] = useState({ name: '', description: '' });
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
            await api.createRole({
                name: formData.name,
                description: formData.description,
                permissions: Array.from(selectedPermissions)
            });
            setMessage({ type: 'success', text: 'Role created successfully' });
            setIsCreateModalOpen(false);
            setFormData({ name: '', description: '' });
            setSelectedPermissions(new Set());
            fetchRoles();
        } catch (error: any) {
            setMessage({ type: 'error', text: error.message || 'Failed to create role' });
        }
    };

    const handleUpdateRole = async () => {
        if (!selectedRole) return;
        try {
            await api.updateRole(selectedRole.id, {
                name: formData.name,
                description: formData.description,
                permissions: Array.from(selectedPermissions)
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
            if (newSet.has(permSlug)) {
                newSet.delete(permSlug);
            } else {
                newSet.add(permSlug);
            }
            return newSet;
        });
    };

    const openCreateModal = () => {
        setFormData({ name: '', description: '' });
        setSelectedPermissions(new Set());
        setIsCreateModalOpen(true);
        setMessage(null);
    };

    const openEditModal = (role: Role) => {
        setSelectedRole(role);
        setFormData({ name: role.name, description: role.description });
        setSelectedPermissions(new Set(role.permissions.map(p => p.slug)));
        setIsEditModalOpen(true);
        setMessage(null);
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
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
                    <div className="bg-white dark:bg-gray-900 rounded-xl shadow-xl w-full max-w-3xl border border-gray-200 dark:border-gray-800 max-h-[90vh] flex flex-col">
                        <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-800">
                            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                                {isCreateModalOpen ? 'Create New Role' : 'Edit Role'}
                            </h3>
                            <button
                                onClick={() => { setIsCreateModalOpen(false); setIsEditModalOpen(false); }}
                                className="text-gray-400 hover:text-gray-500"
                            >
                                <X className="w-5 h-5" />
                            </button>
                        </div>

                        <div className="flex-1 overflow-y-auto p-6 space-y-6">
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

                            {/* Permissions */}
                            <div>
                                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">Permissions</label>
                                <div className="space-y-4">
                                    {Object.entries(PERMISSION_CATEGORIES).map(([category, permSlugs]) => {
                                        const categoryPerms = permissions.filter(p => permSlugs.includes(p.slug));
                                        if (categoryPerms.length === 0) return null;

                                        return (
                                            <div key={category} className="border border-gray-200 dark:border-gray-700 rounded-lg p-4">
                                                <h4 className="text-sm font-medium text-gray-900 dark:text-white mb-3">{category}</h4>
                                                <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                                                    {categoryPerms.map(perm => (
                                                        <label
                                                            key={perm.id}
                                                            className="flex items-center gap-2 p-2 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 cursor-pointer"
                                                        >
                                                            <input
                                                                type="checkbox"
                                                                checked={selectedPermissions.has(perm.slug)}
                                                                onChange={() => togglePermission(perm.slug)}
                                                                className="w-4 h-4 text-orange-600 rounded focus:ring-orange-500"
                                                            />
                                                            <div className="flex-1">
                                                                <p className="text-sm font-medium text-gray-900 dark:text-white">{perm.slug}</p>
                                                                {perm.description && (
                                                                    <p className="text-xs text-gray-500 dark:text-gray-400">{perm.description}</p>
                                                                )}
                                                            </div>
                                                            {selectedPermissions.has(perm.slug) && (
                                                                <Check className="w-4 h-4 text-orange-600 dark:text-orange-400" />
                                                            )}
                                                        </label>
                                                    ))}
                                                </div>
                                            </div>
                                        );
                                    })}
                                </div>
                            </div>
                        </div>

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
                    </div>
                </div>
            )}
        </div>
    );
};
