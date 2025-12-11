import React, { useState, useEffect } from 'react';
import { appLogger } from '../utils/logger';
import { Search, Plus, Users, Edit2, Trash2, X, Save, UserPlus, UserMinus, Shield } from 'lucide-react';
import api from '../services/api';
import { Pagination } from '../components/Pagination';

interface User {
    id: string;
    username: string;
    full_name: string;
    email: string;
}

interface Role {
    id: string;
    name: string;
    description: string;
}

interface Group {
    id: string;
    name: string;
    description: string;
    users: User[];
    roles: Role[];
    created_at: string;
}

export const GroupsPage: React.FC = () => {
    const [groups, setGroups] = useState<Group[]>([]);
    const [loading, setLoading] = useState(true);
    const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
    const [isEditModalOpen, setIsEditModalOpen] = useState(false);
    const [isMembersModalOpen, setIsMembersModalOpen] = useState(false);
    const [isRolesModalOpen, setIsRolesModalOpen] = useState(false);
    const [selectedGroup, setSelectedGroup] = useState<Group | null>(null);
    const [formData, setFormData] = useState({ name: '', description: '' });
    const [allUsers, setAllUsers] = useState<User[]>([]); // Ensure it's always an array
    const [allRoles, setAllRoles] = useState<Role[]>([]);
    const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null);
    const [userSearch, setUserSearch] = useState('');
    const [loadingUsers, setLoadingUsers] = useState(false);
    const [currentPage, setCurrentPage] = useState(1);
    const [itemsPerPage, setItemsPerPage] = useState(50);
    const [totalItems, setTotalItems] = useState(0);

    const fetchGroups = async () => {
        setLoading(true);
        try {
            const skip = (currentPage - 1) * itemsPerPage;
            const response = await api.listGroups({ skip, limit: itemsPerPage });
            
            // Handle both old format (array) and new format (object with items/total)
            if (Array.isArray(response)) {
                setGroups(response);
                setTotalItems(response.length);
            } else {
                setGroups(response.items || []);
                setTotalItems(response.total || 0);
            }
        } catch (error) {
            appLogger.error('Failed to fetch groups:', error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchGroups();
    }, [currentPage, itemsPerPage]);

    const handleCreateGroup = async () => {
        try {
            await api.createGroup(formData);
            setMessage({ type: 'success', text: 'Group created successfully' });
            setIsCreateModalOpen(false);
            setFormData({ name: '', description: '' });
            fetchGroups();
        } catch (error: any) {
            setMessage({ type: 'error', text: error.message || 'Failed to create group' });
        }
    };

    const handleUpdateGroup = async () => {
        if (!selectedGroup) return;
        try {
            await api.updateGroup(selectedGroup.id, formData);
            setMessage({ type: 'success', text: 'Group updated successfully' });
            setIsEditModalOpen(false);
            fetchGroups();
        } catch (error: any) {
            setMessage({ type: 'error', text: error.message || 'Failed to update group' });
        }
    };

    const handleDeleteGroup = async (groupId: string) => {
        if (!confirm('Are you sure you want to delete this group?')) return;
        try {
            await api.deleteGroup(groupId);
            setMessage({ type: 'success', text: 'Group deleted successfully' });
            fetchGroups();
        } catch (error: any) {
            setMessage({ type: 'error', text: error.message || 'Failed to delete group' });
        }
    };

    const [pendingUserChanges, setPendingUserChanges] = useState<{ toAdd: Set<string>; toRemove: Set<string> }>({
        toAdd: new Set(),
        toRemove: new Set()
    });

    const fetchUsersForModal = async (search: string = '') => {
        setLoadingUsers(true);
        try {
            const response = await api.listUsers({ search });
            // Handle both old format (array) and new format (object with items/total)
            if (Array.isArray(response)) {
                setAllUsers(response);
            } else {
                setAllUsers(response?.items || []);
            }
        } catch (error) {
            appLogger.error('Failed to fetch users:', error);
            setAllUsers([]); // Ensure allUsers is always an array
        } finally {
            setLoadingUsers(false);
        }
    };

    const openMembersModal = async (group: Group) => {
        setSelectedGroup(group);
        setPendingUserChanges({ toAdd: new Set(), toRemove: new Set() });
        setUserSearch('');
        setIsMembersModalOpen(true);
        fetchUsersForModal('');
    };

    // Debounced user search
    useEffect(() => {
        if (!isMembersModalOpen) return;

        const debounce = setTimeout(() => {
            fetchUsersForModal(userSearch);
        }, 300);

        return () => clearTimeout(debounce);
    }, [userSearch, isMembersModalOpen]);

    const handleStageAddMember = (userId: string) => {
        setPendingUserChanges(prev => {
            const newToAdd = new Set(prev.toAdd);
            const newToRemove = new Set(prev.toRemove);

            if (newToRemove.has(userId)) {
                newToRemove.delete(userId);
            } else {
                newToAdd.add(userId);
            }

            return { toAdd: newToAdd, toRemove: newToRemove };
        });
    };

    const handleStageRemoveMember = (userId: string) => {
        setPendingUserChanges(prev => {
            const newToAdd = new Set(prev.toAdd);
            const newToRemove = new Set(prev.toRemove);

            if (newToAdd.has(userId)) {
                newToAdd.delete(userId);
            } else {
                newToRemove.add(userId);
            }

            return { toAdd: newToAdd, toRemove: newToRemove };
        });
    };

    const handleSaveMembers = async () => {
        if (!selectedGroup) return;

        try {
            // Process additions
            for (const userId of pendingUserChanges.toAdd) {
                await api.addUserToGroup(selectedGroup.id, userId);
            }

            // Process removals
            for (const userId of pendingUserChanges.toRemove) {
                await api.removeUserFromGroup(selectedGroup.id, userId);
            }

            // Refresh data
            const updatedGroup = await api.request<Group>(`/api/v1/groups/${selectedGroup.id}`);
            setSelectedGroup(updatedGroup);
            fetchGroups();

            setMessage({ type: 'success', text: 'Group members updated successfully' });
            setIsMembersModalOpen(false);
        } catch (error: any) {
            setMessage({ type: 'error', text: error.message || 'Failed to save changes' });
        }
    };

    const [pendingRoleChanges, setPendingRoleChanges] = useState<{ toAdd: Set<string>; toRemove: Set<string> }>({
        toAdd: new Set(),
        toRemove: new Set()
    });

    const openRolesModal = async (group: Group) => {
        setSelectedGroup(group);
        setPendingRoleChanges({ toAdd: new Set(), toRemove: new Set() });
        setIsRolesModalOpen(true);
        try {
            const response = await api.listRoles();
            // Handle both old format (array) and new format (object with items/total)
            if (Array.isArray(response)) {
                setAllRoles(response);
            } else {
                setAllRoles(response?.items || []);
            }
        } catch (error) {
            appLogger.error('Failed to fetch roles:', error);
            setAllRoles([]); // Ensure allRoles is always an array
        }
    };

    const handleStageAddRole = (roleId: string) => {
        setPendingRoleChanges(prev => {
            const newToAdd = new Set(prev.toAdd);
            const newToRemove = new Set(prev.toRemove);

            if (newToRemove.has(roleId)) {
                newToRemove.delete(roleId);
            } else {
                newToAdd.add(roleId);
            }

            return { toAdd: newToAdd, toRemove: newToRemove };
        });
    };

    const handleStageRemoveRole = (roleId: string) => {
        setPendingRoleChanges(prev => {
            const newToAdd = new Set(prev.toAdd);
            const newToRemove = new Set(prev.toRemove);

            if (newToAdd.has(roleId)) {
                newToAdd.delete(roleId);
            } else {
                newToRemove.add(roleId);
            }

            return { toAdd: newToAdd, toRemove: newToRemove };
        });
    };

    const handleSaveRoles = async () => {
        if (!selectedGroup) return;

        try {
            // Process additions
            for (const roleId of pendingRoleChanges.toAdd) {
                await api.addRoleToGroup(selectedGroup.id, roleId);
            }

            // Process removals
            for (const roleId of pendingRoleChanges.toRemove) {
                await api.removeRoleFromGroup(selectedGroup.id, roleId);
            }

            // Refresh data
            const updatedGroup = await api.request<Group>(`/api/v1/groups/${selectedGroup.id}`);
            setSelectedGroup(updatedGroup);
            fetchGroups();

            setMessage({ type: 'success', text: 'Group roles updated successfully' });
            setIsRolesModalOpen(false);
        } catch (error: any) {
            setMessage({ type: 'error', text: error.message || 'Failed to save roles' });
        }
    };

    return (
        <div className="max-w-7xl mx-auto space-y-6">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div>
                    <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Group Management</h1>
                    <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">Manage user groups and permissions</p>
                </div>
                <button
                    onClick={() => {
                        setFormData({ name: '', description: '' });
                        setIsCreateModalOpen(true);
                        setMessage(null);
                    }}
                    className="px-4 py-2 bg-orange-600 text-white rounded-lg hover:bg-orange-700 flex items-center gap-2"
                >
                    <Plus className="w-4 h-4" /> Create Group
                </button>
            </div>

            {message && (
                <div className={`p-4 rounded-lg ${message.type === 'success' ? 'bg-green-50 text-green-700 dark:bg-green-900/20 dark:text-green-400' : 'bg-red-50 text-red-700 dark:bg-red-900/20 dark:text-red-400'}`}>
                    {message.text}
                </div>
            )}

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {loading ? (
                    <p className="text-gray-500">Loading groups...</p>
                ) : groups.map((group) => (
                    <div key={group.id} className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-6 shadow-sm hover:shadow-md transition-shadow">
                        <div className="flex justify-between items-start mb-4">
                            <div className="p-2 bg-orange-50 dark:bg-orange-900/20 rounded-lg">
                                <Users className="w-6 h-6 text-orange-600 dark:text-orange-400" />
                            </div>
                            <div className="flex gap-2">
                                <button
                                    onClick={() => {
                                        setSelectedGroup(group);
                                        setFormData({ name: group.name, description: group.description });
                                        setIsEditModalOpen(true);
                                        setMessage(null);
                                    }}
                                    className="p-1.5 text-gray-400 hover:text-orange-600 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
                                >
                                    <Edit2 className="w-4 h-4" />
                                </button>
                                <button
                                    onClick={() => handleDeleteGroup(group.id)}
                                    className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
                                >
                                    <Trash2 className="w-4 h-4" />
                                </button>
                            </div>
                        </div>
                        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-1">{group.name}</h3>
                        <p className="text-sm text-gray-500 dark:text-gray-400 mb-4 h-10 line-clamp-2">{group.description || 'No description'}</p>

                        <div className="space-y-2 pt-4 border-t border-gray-100 dark:border-gray-800">
                            <div className="flex items-center justify-between">
                                <span className="text-sm text-gray-500 dark:text-gray-400">{group.users?.length || 0} members</span>
                                <button
                                    onClick={() => openMembersModal(group)}
                                    className="text-sm font-medium text-orange-600 dark:text-orange-400 hover:text-orange-700 dark:hover:text-orange-300"
                                >
                                    Manage Members
                                </button>
                            </div>
                            <div className="flex items-center justify-between">
                                <span className="text-sm text-gray-500 dark:text-gray-400">{group.roles?.length || 0} roles</span>
                                <button
                                    onClick={() => openRolesModal(group)}
                                    className="text-sm font-medium text-orange-600 dark:text-orange-400 hover:text-orange-700 dark:hover:text-orange-300"
                                >
                                    Manage Roles
                                </button>
                            </div>
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
                    <div className="bg-white dark:bg-gray-900 rounded-xl shadow-xl w-full max-w-md border border-gray-200 dark:border-gray-800">
                        <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-800">
                            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                                {isCreateModalOpen ? 'Create New Group' : 'Edit Group'}
                            </h3>
                            <button
                                onClick={() => { setIsCreateModalOpen(false); setIsEditModalOpen(false); }}
                                className="text-gray-400 hover:text-gray-500"
                            >
                                <X className="w-5 h-5" />
                            </button>
                        </div>
                        <div className="p-6 space-y-4">
                            <div>
                                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Group Name</label>
                                <input
                                    type="text"
                                    value={formData.name}
                                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 focus:outline-none focus:ring-2 focus:ring-orange-500"
                                    placeholder="e.g. Data Engineers"
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Description</label>
                                <textarea
                                    value={formData.description}
                                    onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 focus:outline-none focus:ring-2 focus:ring-orange-500 h-24 resize-none"
                                    placeholder="Describe the group's purpose..."
                                />
                            </div>
                        </div>
                        <div className="flex justify-end gap-3 p-6 border-t border-gray-200 dark:border-gray-800 bg-gray-50 dark:bg-gray-800/50 rounded-b-xl">
                            <button
                                onClick={() => { setIsCreateModalOpen(false); setIsEditModalOpen(false); }}
                                className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
                            >
                                Cancel
                            </button>
                            <button
                                onClick={isCreateModalOpen ? handleCreateGroup : handleUpdateGroup}
                                className="px-4 py-2 text-sm font-medium text-white bg-orange-600 hover:bg-orange-700 rounded-lg shadow-sm shadow-orange-500/20 flex items-center gap-2"
                            >
                                <Save className="w-4 h-4" /> Save
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Members Modal */}
            {isMembersModalOpen && selectedGroup && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
                    <div className="bg-white dark:bg-gray-900 rounded-xl shadow-xl w-full max-w-2xl border border-gray-200 dark:border-gray-800 h-[600px] flex flex-col">
                        <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-800">
                            <div>
                                <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Manage Members</h3>
                                <p className="text-sm text-gray-500">{selectedGroup.name}</p>
                            </div>
                            <button onClick={() => setIsMembersModalOpen(false)} className="text-gray-400 hover:text-gray-500">
                                <X className="w-5 h-5" />
                            </button>
                        </div>

                        <div className="flex-1 overflow-hidden flex flex-col md:flex-row">
                            {/* Available Users */}
                            <div className="flex-1 p-4 border-r border-gray-200 dark:border-gray-800 overflow-y-auto">
                                <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">Available Users</h4>

                                {/* Search Input */}
                                <div className="relative mb-3">
                                    <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                                    <input
                                        type="text"
                                        placeholder="Search by name or email..."
                                        value={userSearch}
                                        onChange={(e) => setUserSearch(e.target.value)}
                                        className="w-full pl-9 pr-3 py-2 text-sm border border-gray-300 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 focus:outline-none focus:ring-2 focus:ring-orange-500"
                                    />
                                </div>

                                <div className="space-y-2">
                                    {loadingUsers ? (
                                        <div className="flex items-center justify-center py-8 text-gray-500">
                                            <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-orange-600"></div>
                                        </div>
                                    ) : (Array.isArray(allUsers) ? allUsers : []).filter(u =>
                                        (!selectedGroup.users.find(m => m.id === u.id) && !pendingUserChanges.toAdd.has(u.id)) ||
                                        pendingUserChanges.toRemove.has(u.id)
                                    ).length === 0 ? (
                                        <p className="text-sm text-gray-500 text-center py-8">
                                            {userSearch ? 'No users found' : 'No available users'}
                                        </p>
                                    ) : (
                                        (Array.isArray(allUsers) ? allUsers : []).filter(u =>
                                            (!selectedGroup.users.find(m => m.id === u.id) && !pendingUserChanges.toAdd.has(u.id)) ||
                                            pendingUserChanges.toRemove.has(u.id)
                                        ).map(user => (
                                            <div key={user.id} className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
                                                <div>
                                                    <p className="text-sm font-medium text-gray-900 dark:text-white">{user.full_name || user.username}</p>
                                                    <p className="text-xs text-gray-500">{user.email}</p>
                                                </div>
                                                <button
                                                    onClick={() => handleStageAddMember(user.id)}
                                                    className="p-1.5 text-orange-600 hover:bg-orange-50 dark:hover:bg-orange-900/20 rounded-lg transition-colors"
                                                >
                                                    <UserPlus className="w-4 h-4" />
                                                </button>
                                            </div>
                                        ))
                                    )}
                                </div>
                            </div>

                            {/* Current Members */}
                            <div className="flex-1 p-4 overflow-y-auto">
                                <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">Current Members</h4>
                                <div className="space-y-2">
                                    {/* Existing Members */}
                                    {selectedGroup.users.map(user => {
                                        const isPendingRemove = pendingUserChanges.toRemove.has(user.id);
                                        return (
                                            <div key={user.id} className={`flex items-center justify-between p-3 rounded-lg border ${isPendingRemove
                                                ? 'bg-red-50 dark:bg-red-900/10 border-red-100 dark:border-red-900/30 opacity-60'
                                                : 'bg-orange-50 dark:bg-orange-900/10 border-orange-100 dark:border-orange-900/30'
                                                }`}>
                                                <div>
                                                    <p className={`text-sm font-medium ${isPendingRemove ? 'line-through text-gray-500' : 'text-gray-900 dark:text-white'}`}>
                                                        {user.full_name || user.username}
                                                    </p>
                                                    <p className="text-xs text-gray-500">{user.email}</p>
                                                </div>
                                                <button
                                                    onClick={() => handleStageRemoveMember(user.id)}
                                                    className={`p-1.5 rounded-lg transition-colors ${isPendingRemove
                                                        ? 'text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800'
                                                        : 'text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20'
                                                        }`}
                                                >
                                                    {isPendingRemove ? <UserPlus className="w-4 h-4" /> : <UserMinus className="w-4 h-4" />}
                                                </button>
                                            </div>
                                        );
                                    })}

                                    {/* Pending Additions */}
                                    {Array.from(pendingUserChanges.toAdd).map(userId => {
                                        const user = (Array.isArray(allUsers) ? allUsers : []).find(u => u.id === userId);
                                        if (!user) return null;
                                        return (
                                            <div key={user.id} className="flex items-center justify-between p-3 bg-green-50 dark:bg-green-900/10 border border-green-100 dark:border-green-900/30 rounded-lg">
                                                <div>
                                                    <div className="flex items-center gap-2">
                                                        <p className="text-sm font-medium text-gray-900 dark:text-white">{user.full_name || user.username}</p>
                                                        <span className="text-[10px] font-bold text-green-600 bg-green-100 dark:bg-green-900/40 px-1.5 py-0.5 rounded">NEW</span>
                                                    </div>
                                                    <p className="text-xs text-gray-500">{user.email}</p>
                                                </div>
                                                <button
                                                    onClick={() => handleStageAddMember(user.id)}
                                                    className="p-1.5 text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors"
                                                >
                                                    <X className="w-4 h-4" />
                                                </button>
                                            </div>
                                        );
                                    })}

                                    {selectedGroup.users.length === 0 && pendingUserChanges.toAdd.size === 0 && (
                                        <p className="text-sm text-gray-500 text-center py-4">No members yet</p>
                                    )}
                                </div>
                            </div>
                        </div>

                        {/* Footer with Save Button */}
                        <div className="flex justify-between items-center p-6 border-t border-gray-200 dark:border-gray-800 bg-gray-50 dark:bg-gray-800/50 rounded-b-xl">
                            <div className="text-sm">
                                {(pendingUserChanges.toAdd.size > 0 || pendingUserChanges.toRemove.size > 0) && (
                                    <span className="text-amber-600 dark:text-amber-400 font-medium flex items-center gap-2">
                                        <div className="w-2 h-2 rounded-full bg-amber-500 animate-pulse"></div>
                                        Unsaved changes
                                    </span>
                                )}
                            </div>
                            <div className="flex gap-3">
                                <button
                                    onClick={() => setIsMembersModalOpen(false)}
                                    className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
                                >
                                    Cancel
                                </button>
                                <button
                                    onClick={handleSaveMembers}
                                    disabled={pendingUserChanges.toAdd.size === 0 && pendingUserChanges.toRemove.size === 0}
                                    className={`px-4 py-2 text-sm font-medium text-white rounded-lg shadow-sm flex items-center gap-2 ${pendingUserChanges.toAdd.size === 0 && pendingUserChanges.toRemove.size === 0
                                        ? 'bg-gray-400 cursor-not-allowed'
                                        : 'bg-orange-600 hover:bg-orange-700 shadow-orange-500/20'
                                        }`}
                                >
                                    <Save className="w-4 h-4" /> Save Changes
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {/* Roles Modal */}
            {isRolesModalOpen && selectedGroup && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
                    <div className="bg-white dark:bg-gray-900 rounded-xl shadow-xl w-full max-w-2xl border border-gray-200 dark:border-gray-800 h-[600px] flex flex-col">
                        <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-800">
                            <div>
                                <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Manage Roles</h3>
                                <p className="text-sm text-gray-500">{selectedGroup.name}</p>
                            </div>
                            <button onClick={() => setIsRolesModalOpen(false)} className="text-gray-400 hover:text-gray-500">
                                <X className="w-5 h-5" />
                            </button>
                        </div>

                        <div className="flex-1 overflow-hidden flex flex-col md:flex-row">
                            {/* Available Roles */}
                            <div className="flex-1 p-4 border-r border-gray-200 dark:border-gray-800 overflow-y-auto">
                                <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">Available Roles</h4>
                                <div className="space-y-2">
                                    {(Array.isArray(allRoles) ? allRoles : []).filter(r =>
                                        (!selectedGroup.roles.find(gr => gr.id === r.id) && !pendingRoleChanges.toAdd.has(r.id)) ||
                                        pendingRoleChanges.toRemove.has(r.id)
                                    ).map(role => (
                                        <div key={role.id} className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
                                            <div className="flex items-center gap-3">
                                                <div className="p-1.5 bg-orange-50 dark:bg-orange-900/20 rounded-lg">
                                                    <Shield className="w-4 h-4 text-orange-600 dark:text-orange-400" />
                                                </div>
                                                <div>
                                                    <p className="text-sm font-medium text-gray-900 dark:text-white">{role.name}</p>
                                                    <p className="text-xs text-gray-500 line-clamp-1">{role.description}</p>
                                                </div>
                                            </div>
                                            <button
                                                onClick={() => handleStageAddRole(role.id)}
                                                className="p-1.5 text-orange-600 hover:bg-orange-50 dark:hover:bg-orange-900/20 rounded-lg transition-colors"
                                            >
                                                <Plus className="w-4 h-4" />
                                            </button>
                                        </div>
                                    ))}
                                </div>
                            </div>

                            {/* Assigned Roles */}
                            <div className="flex-1 p-4 overflow-y-auto">
                                <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">Assigned Roles</h4>
                                <div className="space-y-2">
                                    {/* Existing Roles */}
                                    {selectedGroup.roles.map(role => {
                                        const isPendingRemove = pendingRoleChanges.toRemove.has(role.id);
                                        return (
                                            <div key={role.id} className={`flex items-center justify-between p-3 rounded-lg border ${isPendingRemove
                                                ? 'bg-red-50 dark:bg-red-900/10 border-red-100 dark:border-red-900/30 opacity-60'
                                                : 'bg-orange-50 dark:bg-orange-900/10 border-orange-100 dark:border-orange-900/30'
                                                }`}>
                                                <div className="flex items-center gap-3">
                                                    <div className={`p-1.5 rounded-lg ${isPendingRemove ? 'bg-gray-100 dark:bg-gray-800' : 'bg-white dark:bg-orange-900/30'}`}>
                                                        <Shield className={`w-4 h-4 ${isPendingRemove ? 'text-gray-400' : 'text-orange-600 dark:text-orange-400'}`} />
                                                    </div>
                                                    <div>
                                                        <p className={`text-sm font-medium ${isPendingRemove ? 'line-through text-gray-500' : 'text-gray-900 dark:text-white'}`}>
                                                            {role.name}
                                                        </p>
                                                    </div>
                                                </div>
                                                <button
                                                    onClick={() => handleStageRemoveRole(role.id)}
                                                    className={`p-1.5 rounded-lg transition-colors ${isPendingRemove
                                                        ? 'text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800'
                                                        : 'text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20'
                                                        }`}
                                                >
                                                    {isPendingRemove ? <Plus className="w-4 h-4" /> : <X className="w-4 h-4" />}
                                                </button>
                                            </div>
                                        );
                                    })}

                                    {/* Pending Additions */}
                                    {Array.from(pendingRoleChanges.toAdd).map(roleId => {
                                        const role = (Array.isArray(allRoles) ? allRoles : []).find(r => r.id === roleId);
                                        if (!role) return null;
                                        return (
                                            <div key={role.id} className="flex items-center justify-between p-3 bg-green-50 dark:bg-green-900/10 border border-green-100 dark:border-green-900/30 rounded-lg">
                                                <div className="flex items-center gap-3">
                                                    <div className="p-1.5 bg-green-100 dark:bg-green-900/30 rounded-lg">
                                                        <Shield className="w-4 h-4 text-green-600 dark:text-green-400" />
                                                    </div>
                                                    <div>
                                                        <div className="flex items-center gap-2">
                                                            <p className="text-sm font-medium text-gray-900 dark:text-white">{role.name}</p>
                                                            <span className="text-[10px] font-bold text-green-600 bg-green-100 dark:bg-green-900/40 px-1.5 py-0.5 rounded">NEW</span>
                                                        </div>
                                                    </div>
                                                </div>
                                                <button
                                                    onClick={() => handleStageAddRole(role.id)}
                                                    className="p-1.5 text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors"
                                                >
                                                    <X className="w-4 h-4" />
                                                </button>
                                            </div>
                                        );
                                    })}

                                    {selectedGroup.roles.length === 0 && pendingRoleChanges.toAdd.size === 0 && (
                                        <p className="text-sm text-gray-500 text-center py-4">No roles assigned</p>
                                    )}
                                </div>
                            </div>
                        </div>

                        {/* Footer with Save Button */}
                        <div className="flex justify-between items-center p-6 border-t border-gray-200 dark:border-gray-800 bg-gray-50 dark:bg-gray-800/50 rounded-b-xl">
                            <div className="text-sm">
                                {(pendingRoleChanges.toAdd.size > 0 || pendingRoleChanges.toRemove.size > 0) && (
                                    <span className="text-amber-600 dark:text-amber-400 font-medium flex items-center gap-2">
                                        <div className="w-2 h-2 rounded-full bg-amber-500 animate-pulse"></div>
                                        Unsaved changes
                                    </span>
                                )}
                            </div>
                            <div className="flex gap-3">
                                <button
                                    onClick={() => setIsRolesModalOpen(false)}
                                    className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
                                >
                                    Cancel
                                </button>
                                <button
                                    onClick={handleSaveRoles}
                                    disabled={pendingRoleChanges.toAdd.size === 0 && pendingRoleChanges.toRemove.size === 0}
                                    className={`px-4 py-2 text-sm font-medium text-white rounded-lg shadow-sm flex items-center gap-2 ${pendingRoleChanges.toAdd.size === 0 && pendingRoleChanges.toRemove.size === 0
                                        ? 'bg-gray-400 cursor-not-allowed'
                                        : 'bg-orange-600 hover:bg-orange-700 shadow-orange-500/20'
                                        }`}
                                >
                                    <Save className="w-4 h-4" /> Save Changes
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};
