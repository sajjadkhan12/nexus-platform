import React, { useState, useEffect } from 'react';
import { Search, Filter, MoreVertical, Shield, User as UserIcon, Lock, CheckCircle2, XCircle, Edit2, Save, X, Trash2, Users } from 'lucide-react';
import api from '../services/api';
import { useAuth } from '../contexts/AuthContext';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

interface User {
    id: string;
    email: string;
    username: string;
    full_name: string;
    roles: string[];
    is_active: boolean;
    avatar_url?: string;
    created_at: string;
}

export const UsersPage: React.FC = () => {
    const [users, setUsers] = useState<User[]>([]);
    const [loading, setLoading] = useState(true);
    const [search, setSearch] = useState('');
    const [roleFilter, setRoleFilter] = useState('');
    const [selectedUser, setSelectedUser] = useState<User | null>(null);
    const [isEditModalOpen, setIsEditModalOpen] = useState(false);
    const [editForm, setEditForm] = useState({
        role: '',
        password: '',
        is_active: true
    });
    const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null);

    const fetchUsers = async () => {
        setLoading(true);
        try {
            const data = await api.listUsers({ search, role: roleFilter });
            setUsers(data);
        } catch (error) {
            console.error('Failed to fetch users:', error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        const debounce = setTimeout(() => {
            fetchUsers();
        }, 300);
        return () => clearTimeout(debounce);
    }, [search, roleFilter]);

    const handleEditClick = (user: User) => {
        setSelectedUser(user);
        setEditForm({
            role: user.roles?.[0] || 'engineer',
            password: '',
            is_active: user.is_active
        });
        setIsEditModalOpen(true);
        setMessage(null);
    };

    const handleSaveUser = async () => {
        if (!selectedUser) return;

        try {
            const updateData: any = {
                roles: [editForm.role],
                is_active: editForm.is_active
            };

            if (editForm.password) {
                if (editForm.password.length < 8) {
                    setMessage({ type: 'error', text: 'Password must be at least 8 characters' });
                    return;
                }
                updateData.password = editForm.password;
            }

            await api.adminUpdateUser(selectedUser.id, updateData);

            setMessage({ type: 'success', text: 'User updated successfully' });
            fetchUsers();
            setTimeout(() => setIsEditModalOpen(false), 1500);
        } catch (error: any) {
            setMessage({ type: 'error', text: error.message || 'Failed to update user' });
        }
    };

    const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
    const [createForm, setCreateForm] = useState({
        email: '',
        full_name: '',
        password: ''
    });

    const handleCreateUser = async () => {
        try {
            if (!createForm.email || !createForm.password) {
                setMessage({ type: 'error', text: 'Email and password are required' });
                return;
            }

            if (createForm.password.length < 8) {
                setMessage({ type: 'error', text: 'Password must be at least 8 characters' });
                return;
            }

            await api.createUser({
                ...createForm
            });
            setMessage({ type: 'success', text: 'User created successfully' });
            setIsCreateModalOpen(false);
            setCreateForm({ email: '', full_name: '', password: '' });

            // Clear filters to ensure new user is visible
            // This will trigger the useEffect to fetch users
            setSearch('');
            setRoleFilter('');
        } catch (error: any) {
            setMessage({ type: 'error', text: error.message || 'Failed to create user' });
        }
    };

    const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
    const [userToDelete, setUserToDelete] = useState<User | null>(null);

    const handleDeleteUser = (user: User) => {
        setUserToDelete(user);
        setIsDeleteModalOpen(true);
    };

    const confirmDeleteUser = async () => {
        if (!userToDelete) return;

        try {
            await api.deleteUser(userToDelete.id);
            setMessage({ type: 'success', text: 'User deleted successfully' });
            setIsDeleteModalOpen(false);
            setUserToDelete(null);
            // Small delay to ensure backend processing is complete
            await new Promise(resolve => setTimeout(resolve, 200));
            await fetchUsers();
        } catch (error: any) {
            setMessage({ type: 'error', text: error.message || 'Failed to delete user' });
        }
    };

    return (
        <div className="max-w-7xl mx-auto space-y-6">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div>
                    <h1 className="text-2xl font-bold text-gray-900 dark:text-white">User Management</h1>
                    <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">Manage system users, roles, and access</p>
                </div>
                <div className="flex items-center gap-3">
                    <button
                        onClick={() => setIsCreateModalOpen(true)}
                        className="px-4 py-2 bg-orange-600 text-white rounded-lg hover:bg-orange-700 flex items-center gap-2 text-sm font-medium"
                    >
                        <UserIcon className="w-4 h-4" /> Create User
                    </button>
                    <div className="relative">
                        <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                        <input
                            type="text"
                            placeholder="Search users..."
                            value={search}
                            onChange={(e) => setSearch(e.target.value)}
                            className="pl-9 pr-4 py-2 border border-gray-300 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-orange-500 w-full sm:w-64"
                        />
                    </div>
                    <select
                        value={roleFilter}
                        onChange={(e) => setRoleFilter(e.target.value)}
                        className="px-3 py-2 border border-gray-300 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-orange-500"
                    >
                        <option value="">All Roles</option>
                        <option value="admin">Admin</option>
                        <option value="engineer">Engineer</option>
                    </select>
                </div>
            </div>

            {message && (
                <div className={`p-4 rounded-lg ${message.type === 'success' ? 'bg-green-50 text-green-700 dark:bg-green-900/20 dark:text-green-400' : 'bg-red-50 text-red-700 dark:bg-red-900/20 dark:text-red-400'}`}>
                    {message.text}
                </div>
            )}

            <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl overflow-hidden shadow-sm">
                <div className="overflow-x-auto">
                    <table className="w-full text-left text-sm">
                        <thead className="bg-gray-50 dark:bg-gray-800/50 border-b border-gray-200 dark:border-gray-800">
                            <tr>
                                <th className="px-6 py-4 font-medium text-gray-500 dark:text-gray-400">User</th>
                                <th className="px-6 py-4 font-medium text-gray-500 dark:text-gray-400">Role</th>
                                <th className="px-6 py-4 font-medium text-gray-500 dark:text-gray-400">Status</th>
                                <th className="px-6 py-4 font-medium text-gray-500 dark:text-gray-400">Joined</th>
                                <th className="px-6 py-4 font-medium text-gray-500 dark:text-gray-400 text-right">Actions</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-200 dark:divide-gray-800">
                            {loading ? (
                                <tr>
                                    <td colSpan={5} className="px-6 py-8 text-center text-gray-500">
                                        <div className="flex justify-center items-center gap-2">
                                            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-orange-600"></div>
                                            Loading users...
                                        </div>
                                    </td>
                                </tr>
                            ) : users.length === 0 ? (
                                <tr>
                                    <td colSpan={5} className="px-6 py-8 text-center text-gray-500">
                                        No users found matching your criteria
                                    </td>
                                </tr>
                            ) : (
                                users.map((user) => (
                                    <tr key={user.id} className="hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors">
                                        <td className="px-6 py-4">
                                            <div className="flex items-center gap-3">
                                                {user.avatar_url ? (
                                                    <img
                                                        src={user.avatar_url.startsWith('http') ? user.avatar_url : `${API_URL}${user.avatar_url}`}
                                                        alt={user.username}
                                                        className="w-10 h-10 rounded-full object-cover ring-2 ring-gray-100 dark:ring-gray-800"
                                                    />
                                                ) : (
                                                    <div className="w-10 h-10 rounded-full bg-orange-100 dark:bg-orange-900/30 flex items-center justify-center text-orange-600 dark:text-orange-400 font-bold">
                                                        {user.full_name?.charAt(0) || user.username.charAt(0)}
                                                    </div>
                                                )}
                                                <div>
                                                    <p className="font-medium text-gray-900 dark:text-white">{user.full_name || user.username}</p>
                                                    <p className="text-xs text-gray-500">{user.email}</p>
                                                </div>
                                            </div>
                                        </td>
                                        <td className="px-6 py-4">
                                            <div className="flex flex-wrap gap-1">
                                                {user.roles && user.roles.length > 0 ? (
                                                    user.roles.map((role) => {
                                                        // Distinguish between roles and groups
                                                        // Standard roles: admin, engineer
                                                        // Groups: anything else (custom names)
                                                        const isStandardRole = role === 'admin' || role === 'engineer';
                                                        const isAdmin = role === 'admin';

                                                        return (
                                                            <span
                                                                key={role}
                                                                className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium border ${isAdmin
                                                                    ? 'bg-orange-50 dark:bg-orange-900/20 text-orange-700 dark:text-orange-400 border-orange-200 dark:border-orange-800'
                                                                    : isStandardRole
                                                                        ? 'bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-400 border-blue-200 dark:border-blue-800'
                                                                        : 'bg-emerald-50 dark:bg-emerald-900/20 text-emerald-700 dark:text-emerald-400 border-emerald-200 dark:border-emerald-800'
                                                                    }`}
                                                            >
                                                                {isAdmin ? <Shield className="w-3 h-3" /> : isStandardRole ? <UserIcon className="w-3 h-3" /> : <Users className="w-3 h-3" />}
                                                                {/* Capitalize first letter of role/group name */}
                                                                {role.charAt(0).toUpperCase() + role.slice(1).replace(/-/g, ' ')}
                                                            </span>
                                                        );
                                                    })
                                                ) : (
                                                    <span className="text-gray-500 text-xs">No roles</span>
                                                )}
                                            </div>
                                        </td>
                                        <td className="px-6 py-4">
                                            <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium border ${user.is_active
                                                ? 'bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-400 border-green-200 dark:border-green-800'
                                                : 'bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400 border-red-200 dark:border-red-800'
                                                }`}>
                                                {user.is_active ? <CheckCircle2 className="w-3 h-3" /> : <XCircle className="w-3 h-3" />}
                                                {user.is_active ? 'Active' : 'Inactive'}
                                            </span>
                                        </td>
                                        <td className="px-6 py-4 text-gray-500 dark:text-gray-400">
                                            {new Date(user.created_at).toLocaleDateString()}
                                        </td>
                                        <td className="px-6 py-4 text-right">
                                            <div className="flex justify-end gap-2">
                                                <button
                                                    onClick={() => handleEditClick(user)}
                                                    className="p-2 text-gray-400 hover:text-orange-600 dark:hover:text-orange-400 hover:bg-orange-50 dark:hover:bg-orange-900/20 rounded-lg transition-colors"
                                                    title="Edit User"
                                                >
                                                    <Edit2 className="w-4 h-4" />
                                                </button>
                                                <button
                                                    onClick={() => handleDeleteUser(user)}
                                                    className="p-2 text-gray-400 hover:text-red-600 dark:hover:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors"
                                                    title="Delete User"
                                                >
                                                    <Trash2 className="w-4 h-4" />
                                                </button>
                                            </div>
                                        </td>
                                    </tr>
                                ))
                            )}
                        </tbody>
                    </table>
                </div>
            </div>

            {/* Create User Modal */}
            {isCreateModalOpen && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
                    <div className="bg-white dark:bg-gray-900 rounded-xl shadow-xl w-full max-w-md border border-gray-200 dark:border-gray-800 animate-in fade-in zoom-in-95 duration-200">
                        <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-800">
                            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Create New User</h3>
                            <button onClick={() => setIsCreateModalOpen(false)} className="text-gray-400 hover:text-gray-500">
                                <X className="w-5 h-5" />
                            </button>
                        </div>

                        <div className="p-6 space-y-4">
                            <div>
                                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Email Address</label>
                                <input
                                    type="email"
                                    value={createForm.email}
                                    onChange={(e) => setCreateForm({ ...createForm, email: e.target.value })}
                                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 focus:outline-none focus:ring-2 focus:ring-orange-500"
                                    placeholder="user@example.com"
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Full Name</label>
                                <input
                                    type="text"
                                    value={createForm.full_name}
                                    onChange={(e) => setCreateForm({ ...createForm, full_name: e.target.value })}
                                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 focus:outline-none focus:ring-2 focus:ring-orange-500"
                                    placeholder="John Doe"
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Password</label>
                                <input
                                    type="password"
                                    value={createForm.password}
                                    onChange={(e) => setCreateForm({ ...createForm, password: e.target.value })}
                                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 focus:outline-none focus:ring-2 focus:ring-orange-500"
                                    placeholder="••••••••"
                                />
                            </div>
                        </div>

                        <div className="flex justify-end gap-3 p-6 border-t border-gray-200 dark:border-gray-800 bg-gray-50 dark:bg-gray-800/50 rounded-b-xl">
                            <button
                                onClick={() => setIsCreateModalOpen(false)}
                                className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
                            >
                                Cancel
                            </button>
                            <button
                                onClick={handleCreateUser}
                                className="px-4 py-2 text-sm font-medium text-white bg-orange-600 hover:bg-orange-700 rounded-lg shadow-sm shadow-orange-500/20 flex items-center gap-2"
                            >
                                <UserIcon className="w-4 h-4" /> Create User
                            </button>
                        </div>
                    </div>
                </div>
            )
            }

            {/* Edit User Modal */}
            {
                isEditModalOpen && selectedUser && (
                    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
                        <div className="bg-white dark:bg-gray-900 rounded-xl shadow-xl w-full max-w-md border border-gray-200 dark:border-gray-800 animate-in fade-in zoom-in-95 duration-200">
                            <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-800">
                                <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Edit User</h3>
                                <button onClick={() => setIsEditModalOpen(false)} className="text-gray-400 hover:text-gray-500">
                                    <X className="w-5 h-5" />
                                </button>
                            </div>

                            <div className="p-6 space-y-4">
                                {message && (
                                    <div className={`p-3 rounded-lg text-sm ${message.type === 'success' ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'}`}>
                                        {message.text}
                                    </div>
                                )}

                                <div>
                                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">User</label>
                                    <div className="p-3 bg-gray-50 dark:bg-gray-800 rounded-lg flex items-center gap-3">
                                        <div className="w-8 h-8 rounded-full bg-orange-100 dark:bg-orange-900/30 flex items-center justify-center text-orange-600 dark:text-orange-400 font-bold text-xs">
                                            {selectedUser.username.charAt(0).toUpperCase()}
                                        </div>
                                        <div>
                                            <p className="text-sm font-medium text-gray-900 dark:text-white">{selectedUser.full_name || selectedUser.username}</p>
                                            <p className="text-xs text-gray-500">{selectedUser.email}</p>
                                        </div>
                                    </div>
                                </div>

                                <div>
                                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Role</label>
                                    <select
                                        value={editForm.role}
                                        onChange={(e) => setEditForm({ ...editForm, role: e.target.value })}
                                        className="w-full px-3 py-2 border border-gray-300 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 focus:outline-none focus:ring-2 focus:ring-orange-500"
                                    >
                                        <option value="engineer">Engineer</option>
                                        <option value="admin">Administrator</option>
                                    </select>
                                </div>

                                <div>
                                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Status</label>
                                    <div className="flex items-center gap-3">
                                        <button
                                            onClick={() => setEditForm({ ...editForm, is_active: !editForm.is_active })}
                                            className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-orange-500 focus:ring-offset-2 ${editForm.is_active ? 'bg-orange-600' : 'bg-gray-200 dark:bg-gray-700'
                                                }`}
                                        >
                                            <span
                                                className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${editForm.is_active ? 'translate-x-6' : 'translate-x-1'
                                                    }`}
                                            />
                                        </button>
                                        <span className="text-sm text-gray-600 dark:text-gray-400">
                                            {editForm.is_active ? 'Active Account' : 'Inactive Account'}
                                        </span>
                                    </div>
                                </div>

                                <div>
                                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                                        Reset Password <span className="text-gray-400 font-normal">(Optional)</span>
                                    </label>
                                    <div className="relative">
                                        <Lock className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                                        <input
                                            type="password"
                                            value={editForm.password}
                                            onChange={(e) => setEditForm({ ...editForm, password: e.target.value })}
                                            placeholder="Enter new password to reset"
                                            className="w-full pl-9 pr-4 py-2 border border-gray-300 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 focus:outline-none focus:ring-2 focus:ring-orange-500"
                                        />
                                    </div>
                                </div>
                            </div>

                            <div className="flex justify-end gap-3 p-6 border-t border-gray-200 dark:border-gray-800 bg-gray-50 dark:bg-gray-800/50 rounded-b-xl">
                                <button
                                    onClick={() => setIsEditModalOpen(false)}
                                    className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
                                >
                                    Cancel
                                </button>
                                <button
                                    onClick={handleSaveUser}
                                    className="px-4 py-2 text-sm font-medium text-white bg-orange-600 hover:bg-orange-700 rounded-lg shadow-sm shadow-orange-500/20 flex items-center gap-2"
                                >
                                    <Save className="w-4 h-4" /> Save Changes
                                </button>
                            </div>
                        </div>
                    </div>
                )
            }
            {/* Delete Confirmation Modal */}
            {
                isDeleteModalOpen && userToDelete && (
                    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
                        <div className="bg-white dark:bg-gray-900 rounded-xl shadow-xl w-full max-w-md border border-gray-200 dark:border-gray-800 animate-in fade-in zoom-in-95 duration-200">
                            <div className="p-6 text-center">
                                <div className="w-12 h-12 rounded-full bg-red-100 dark:bg-red-900/30 flex items-center justify-center mx-auto mb-4 text-red-600 dark:text-red-400">
                                    <Trash2 className="w-6 h-6" />
                                </div>
                                <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">Delete User</h3>
                                <p className="text-gray-500 dark:text-gray-400 mb-6">
                                    Are you sure you want to delete <strong>{userToDelete.full_name || userToDelete.email}</strong>? This action cannot be undone.
                                </p>

                                <div className="flex justify-center gap-3">
                                    <button
                                        onClick={() => setIsDeleteModalOpen(false)}
                                        className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
                                    >
                                        Cancel
                                    </button>
                                    <button
                                        onClick={confirmDeleteUser}
                                        className="px-4 py-2 text-sm font-medium text-white bg-red-600 hover:bg-red-700 rounded-lg shadow-sm shadow-red-500/20 flex items-center gap-2"
                                    >
                                        <Trash2 className="w-4 h-4" /> Delete User
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                )
            }
        </div >
    );
};
