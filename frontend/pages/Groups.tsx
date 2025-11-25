import React, { useState, useEffect } from 'react';
import { Search, Plus, Users, Edit2, Trash2, X, Save, UserPlus, UserMinus, Shield } from 'lucide-react';
import api from '../services/api';

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
    const [allUsers, setAllUsers] = useState<User[]>([]);
    const [allRoles, setAllRoles] = useState<Role[]>([]);
    const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null);

    const fetchGroups = async () => {
        setLoading(true);
        try {
            const data = await api.listGroups();
            setGroups(data);
        } catch (error) {
            console.error('Failed to fetch groups:', error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchGroups();
    }, []);

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

    const openMembersModal = async (group: Group) => {
        setSelectedGroup(group);
        setIsMembersModalOpen(true);
        try {
            const users = await api.listUsers();
            setAllUsers(users);
        } catch (error) {
            console.error('Failed to fetch users:', error);
        }
    };

    const handleAddMember = async (userId: string) => {
        if (!selectedGroup) return;
        try {
            await api.addUserToGroup(selectedGroup.id, userId);
            // Refresh group data locally
            const updatedGroup = await api.request<Group>(`/api/v1/groups/${selectedGroup.id}`);
            setSelectedGroup(updatedGroup);
            fetchGroups(); // Refresh list as well
        } catch (error: any) {
            setMessage({ type: 'error', text: error.message || 'Failed to add member' });
        }
    };

    const handleRemoveMember = async (userId: string) => {
        if (!selectedGroup) return;
        try {
            await api.removeUserFromGroup(selectedGroup.id, userId);
            // Refresh group data locally
            const updatedGroup = await api.request<Group>(`/api/v1/groups/${selectedGroup.id}`);
            setSelectedGroup(updatedGroup);
            fetchGroups();
        } catch (error: any) {
            setMessage({ type: 'error', text: error.message || 'Failed to remove member' });
        }
    };

    const openRolesModal = async (group: Group) => {
        setSelectedGroup(group);
        setIsRolesModalOpen(true);
        try {
            const roles = await api.listRoles();
            setAllRoles(roles);
        } catch (error) {
            console.error('Failed to fetch roles:', error);
        }
    };

    const handleAddRole = async (roleId: string) => {
        if (!selectedGroup) return;
        try {
            await api.addRoleToGroup(selectedGroup.id, roleId);
            const updatedGroup = await api.request<Group>(`/api/v1/groups/${selectedGroup.id}`);
            setSelectedGroup(updatedGroup);
            fetchGroups();
        } catch (error: any) {
            setMessage({ type: 'error', text: error.message || 'Failed to add role' });
        }
    };

    const handleRemoveRole = async (roleId: string) => {
        if (!selectedGroup) return;
        try {
            await api.removeRoleFromGroup(selectedGroup.id, roleId);
            const updatedGroup = await api.request<Group>(`/api/v1/groups/${selectedGroup.id}`);
            setSelectedGroup(updatedGroup);
            fetchGroups();
        } catch (error: any) {
            setMessage({ type: 'error', text: error.message || 'Failed to remove role' });
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
                    className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 flex items-center gap-2"
                >
                    <Plus className="w-4 h-4" /> Create Group
                </button>
            </div>

            {message && (
                <div className={`p-4 rounded-lg ${message.type === 'success' ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'}`}>
                    {message.text}
                </div>
            )}

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {loading ? (
                    <p className="text-gray-500">Loading groups...</p>
                ) : groups.map((group) => (
                    <div key={group.id} className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-6 shadow-sm hover:shadow-md transition-shadow">
                        <div className="flex justify-between items-start mb-4">
                            <div className="p-2 bg-indigo-50 dark:bg-indigo-900/20 rounded-lg">
                                <Users className="w-6 h-6 text-indigo-600 dark:text-indigo-400" />
                            </div>
                            <div className="flex gap-2">
                                <button
                                    onClick={() => {
                                        setSelectedGroup(group);
                                        setFormData({ name: group.name, description: group.description });
                                        setIsEditModalOpen(true);
                                        setMessage(null);
                                    }}
                                    className="p-1.5 text-gray-400 hover:text-indigo-600 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
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
                                    className="text-sm font-medium text-indigo-600 dark:text-indigo-400 hover:text-indigo-700 dark:hover:text-indigo-300"
                                >
                                    Manage Members
                                </button>
                            </div>
                            <div className="flex items-center justify-between">
                                <span className="text-sm text-gray-500 dark:text-gray-400">{group.roles?.length || 0} roles</span>
                                <button
                                    onClick={() => openRolesModal(group)}
                                    className="text-sm font-medium text-indigo-600 dark:text-indigo-400 hover:text-indigo-700 dark:hover:text-indigo-300"
                                >
                                    Manage Roles
                                </button>
                            </div>
                        </div>
                    </div>
                ))}
            </div>

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
                                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                                    placeholder="e.g. Data Engineers"
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Description</label>
                                <textarea
                                    value={formData.description}
                                    onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 focus:outline-none focus:ring-2 focus:ring-indigo-500 h-24 resize-none"
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
                                className="px-4 py-2 text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg shadow-sm shadow-indigo-500/20 flex items-center gap-2"
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
                                <div className="space-y-2">
                                    {allUsers.filter(u => !selectedGroup.users.find(m => m.id === u.id)).map(user => (
                                        <div key={user.id} className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
                                            <div>
                                                <p className="text-sm font-medium text-gray-900 dark:text-white">{user.full_name || user.username}</p>
                                                <p className="text-xs text-gray-500">{user.email}</p>
                                            </div>
                                            <button
                                                onClick={() => handleAddMember(user.id)}
                                                className="p-1.5 text-indigo-600 hover:bg-indigo-50 dark:hover:bg-indigo-900/20 rounded-lg transition-colors"
                                            >
                                                <UserPlus className="w-4 h-4" />
                                            </button>
                                        </div>
                                    ))}
                                </div>
                            </div>

                            {/* Current Members */}
                            <div className="flex-1 p-4 overflow-y-auto">
                                <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">Current Members</h4>
                                <div className="space-y-2">
                                    {selectedGroup.users.map(user => (
                                        <div key={user.id} className="flex items-center justify-between p-3 bg-indigo-50 dark:bg-indigo-900/10 border border-indigo-100 dark:border-indigo-900/30 rounded-lg">
                                            <div>
                                                <p className="text-sm font-medium text-gray-900 dark:text-white">{user.full_name || user.username}</p>
                                                <p className="text-xs text-gray-500">{user.email}</p>
                                            </div>
                                            <button
                                                onClick={() => handleRemoveMember(user.id)}
                                                className="p-1.5 text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors"
                                            >
                                                <UserMinus className="w-4 h-4" />
                                            </button>
                                        </div>
                                    ))}
                                    {selectedGroup.users.length === 0 && (
                                        <p className="text-sm text-gray-500 text-center py-4">No members yet</p>
                                    )}
                                </div>
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
                                    {allRoles.filter(r => !selectedGroup.roles?.find(gr => gr.id === r.id)).map(role => (
                                        <div key={role.id} className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
                                            <div>
                                                <div className="flex items-center gap-2">
                                                    <Shield className="w-4 h-4 text-indigo-600 dark:text-indigo-400" />
                                                    <p className="text-sm font-medium text-gray-900 dark:text-white">{role.name}</p>
                                                </div>
                                                <p className="text-xs text-gray-500 ml-6">{role.description || 'No description'}</p>
                                            </div>
                                            <button
                                                onClick={() => handleAddRole(role.id)}
                                                className="p-1.5 text-indigo-600 hover:bg-indigo-50 dark:hover:bg-indigo-900/20 rounded-lg transition-colors"
                                            >
                                                <Plus className="w-4 h-4" />
                                            </button>
                                        </div>
                                    ))}
                                    {allRoles.filter(r => !selectedGroup.roles?.find(gr => gr.id === r.id)).length === 0 && (
                                        <p className="text-sm text-gray-500 text-center py-4">All roles assigned</p>
                                    )}
                                </div>
                            </div>

                            {/* Assigned Roles */}
                            <div className="flex-1 p-4 overflow-y-auto">
                                <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">Assigned Roles</h4>
                                <div className="space-y-2">
                                    {selectedGroup.roles?.map(role => (
                                        <div key={role.id} className="flex items-center justify-between p-3 bg-indigo-50 dark:bg-indigo-900/10 border border-indigo-100 dark:border-indigo-900/30 rounded-lg">
                                            <div>
                                                <div className="flex items-center gap-2">
                                                    <Shield className="w-4 h-4 text-indigo-600 dark:text-indigo-400" />
                                                    <p className="text-sm font-medium text-gray-900 dark:text-white">{role.name}</p>
                                                </div>
                                                <p className="text-xs text-gray-500 ml-6">{role.description || 'No description'}</p>
                                            </div>
                                            <button
                                                onClick={() => handleRemoveRole(role.id)}
                                                className="p-1.5 text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors"
                                            >
                                                <X className="w-4 h-4" />
                                            </button>
                                        </div>
                                    ))}
                                    {(!selectedGroup.roles || selectedGroup.roles.length === 0) && (
                                        <p className="text-sm text-gray-500 text-center py-4">No roles assigned yet</p>
                                    )}
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};
