import React, { useState, useEffect, useRef } from 'react';
import { Search, Plus, Edit2, Trash2, Users, Building2, X, Save, Mail, UserPlus, UserMinus, AlertCircle, Loader } from 'lucide-react';
import { businessUnitsApi, BusinessUnit, BusinessUnitMember, BusinessUnitCreate, BusinessUnitUpdate, BusinessUnitMemberAdd } from '../services/api/businessUnits';
import { useAuth } from '../contexts/AuthContext';
import { useNotification } from '../contexts/NotificationContext';
import api from '../services/api';

export const BusinessUnitsPage: React.FC = () => {
    const { user, isAdmin } = useAuth();
    const { addNotification } = useNotification();
    const [businessUnits, setBusinessUnits] = useState<BusinessUnit[]>([]);
    const [loading, setLoading] = useState(true);
    const [search, setSearch] = useState('');
    const [showCreateModal, setShowCreateModal] = useState(false);
    const [showEditModal, setShowEditModal] = useState(false);
    const [showMembersModal, setShowMembersModal] = useState(false);
    const [selectedBusinessUnit, setSelectedBusinessUnit] = useState<BusinessUnit | null>(null);
    const [members, setMembers] = useState<BusinessUnitMember[]>([]);
    const [loadingMembers, setLoadingMembers] = useState(false);
    const [allUsers, setAllUsers] = useState<any[]>([]);
    
    const [createForm, setCreateForm] = useState<BusinessUnitCreate>({
        name: '',
        slug: '',
        description: ''
    });

    const [editForm, setEditForm] = useState<BusinessUnitUpdate>({
        name: '',
        description: '',
        is_active: true
    });

    const [addMemberForm, setAddMemberForm] = useState<BusinessUnitMemberAdd>({
        user_email: '',
        role_id: undefined
    });
    const [availableRoles, setAvailableRoles] = useState<any[]>([]);
    const [loadingRoles, setLoadingRoles] = useState(false);
    const [userSearchQuery, setUserSearchQuery] = useState('');
    const [showUserDropdown, setShowUserDropdown] = useState(false);
    const [selectedUser, setSelectedUser] = useState<any | null>(null);
    const userSearchRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        fetchBusinessUnits();
        fetchAllUsers();
        fetchAvailableRoles();
    }, []);

    const fetchAvailableRoles = async () => {
        setLoadingRoles(true);
        try {
            // Use the business units endpoint which doesn't require platform permissions
            const buRoles = await businessUnitsApi.getAvailableRoles();
            setAvailableRoles(buRoles);
            if (buRoles.length === 0) {
                // No business unit roles found
            }
        } catch (error) {
            console.error('Failed to fetch roles:', error);
            // Don't set fallback roles - only show roles that actually exist in the database
            setAvailableRoles([]);
            addNotification('error', 'Failed to load roles. Please refresh the page.');
        } finally {
            setLoadingRoles(false);
        }
    };

    // Close dropdown when clicking outside
    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (userSearchRef.current && !userSearchRef.current.contains(event.target as Node)) {
                setShowUserDropdown(false);
            }
        };

        document.addEventListener('mousedown', handleClickOutside);
        return () => {
            document.removeEventListener('mousedown', handleClickOutside);
        };
    }, []);

    const fetchBusinessUnits = async () => {
        setLoading(true);
        try {
            const data = await businessUnitsApi.listBusinessUnits();
            setBusinessUnits(data);
        } catch (error: any) {
            addNotification('error', error.message || 'Failed to fetch business units');
        } finally {
            setLoading(false);
        }
    };

    const fetchAllUsers = async () => {
        try {
            // Use the business units endpoint which doesn't require platform permissions
            const users = await businessUnitsApi.getAvailableUsers();
            setAllUsers(users);
        } catch (error) {
            console.error('Failed to fetch users:', error);
        }
    };

    const fetchMembers = async (businessUnitId: string) => {
        setLoadingMembers(true);
        try {
            const data = await businessUnitsApi.listMembers(businessUnitId);
            setMembers(data);
        } catch (error: any) {
            addNotification('error', error.message || 'Failed to fetch members');
        } finally {
            setLoadingMembers(false);
        }
    };

    const handleCreate = async () => {
        if (!createForm.name || !createForm.slug) {
            addNotification('error', 'Name and slug are required');
            return;
        }

        try {
            const created = await businessUnitsApi.createBusinessUnit(createForm);
            addNotification('success', `Business unit "${created.name}" created successfully`);
            setShowCreateModal(false);
            setCreateForm({ name: '', slug: '', description: '' });
            // Refresh the list to show the new business unit
            await fetchBusinessUnits();
        } catch (error: any) {
            addNotification('error', error.message || 'Failed to create business unit');
        }
    };

    const handleEdit = (bu: BusinessUnit) => {
        setSelectedBusinessUnit(bu);
        setEditForm({
            name: bu.name,
            description: bu.description || '',
            is_active: true
        });
        setShowEditModal(true);
    };

    const handleUpdate = async () => {
        if (!selectedBusinessUnit) return;

        try {
            await businessUnitsApi.updateBusinessUnit(selectedBusinessUnit.id, editForm);
            addNotification('success', 'Business unit updated successfully');
            setShowEditModal(false);
            setSelectedBusinessUnit(null);
            fetchBusinessUnits();
        } catch (error: any) {
            addNotification('error', error.message || 'Failed to update business unit');
        }
    };

    const handleDelete = async (bu: BusinessUnit) => {
        if (!confirm(`Are you sure you want to delete "${bu.name}"? This action cannot be undone.`)) {
            return;
        }

        try {
            await businessUnitsApi.deleteBusinessUnit(bu.id);
            addNotification('success', 'Business unit deleted successfully');
            fetchBusinessUnits();
        } catch (error: any) {
            addNotification('error', error.message || 'Failed to delete business unit');
        }
    };

    const handleViewMembers = async (bu: BusinessUnit) => {
        // Check if user has permission to view/manage members (permission-based, not role-name-based)
        const canManage = bu.can_manage_members === true || isAdmin;
        if (!canManage) {
            addNotification('error', 'You do not have permission to manage members of this business unit');
            return;
        }
        setSelectedBusinessUnit(bu);
        setShowMembersModal(true);
        setUserSearchQuery('');
        setSelectedUser(null);
        setShowUserDropdown(false);
        // Don't set a default role - user must select one
        setAddMemberForm({ user_email: '', role_id: undefined });
        await fetchMembers(bu.id);
    };

    const handleAddMember = async () => {
        if (!selectedBusinessUnit || !addMemberForm.user_email) {
            addNotification('error', 'Please enter a user email');
            return;
        }

        if (!addMemberForm.role_id) {
            addNotification('error', 'Please select a role');
            return;
        }

        try {
            await businessUnitsApi.addMember(selectedBusinessUnit.id, addMemberForm);
            const roleName = availableRoles.find(r => r.id === addMemberForm.role_id)?.name || 'member';
            addNotification('success', `Member added successfully as ${roleName}`);
            // Reset form without default role
            setAddMemberForm({ user_email: '', role_id: undefined });
            setUserSearchQuery('');
            setSelectedUser(null);
            setShowUserDropdown(false);
            await fetchMembers(selectedBusinessUnit.id);
            // Refresh the business units list to update role information
            await fetchBusinessUnits();
        } catch (error: any) {
            const errorMessage = error?.response?.data?.detail || error?.message || 'Failed to add member';
            addNotification('error', errorMessage);
        }
    };

    // Filter users based on search query
    const filteredUsers = allUsers.filter((user) => {
        if (!userSearchQuery.trim()) return false;
        const query = userSearchQuery.toLowerCase();
        const email = (user.email || '').toLowerCase();
        const name = (user.full_name || user.username || '').toLowerCase();
        return email.includes(query) || name.includes(query);
    });

    const handleUserSelect = (user: any) => {
        setSelectedUser(user);
        setAddMemberForm({ ...addMemberForm, user_email: user.email });
        setUserSearchQuery(user.email);
        setShowUserDropdown(false);
    };

    const handleRemoveMember = async (member: BusinessUnitMember) => {
        if (!selectedBusinessUnit) return;
        if (!confirm(`Remove ${member.user_email} from this business unit?`)) {
            return;
        }

        try {
            await businessUnitsApi.removeMember(selectedBusinessUnit.id, member.user_id);
            addNotification('success', 'Member removed successfully');
            await fetchMembers(selectedBusinessUnit.id);
        } catch (error: any) {
            addNotification('error', error.message || 'Failed to remove member');
        }
    };

    const filteredBusinessUnits = businessUnits.filter(bu =>
        bu.name.toLowerCase().includes(search.toLowerCase()) ||
        bu.slug.toLowerCase().includes(search.toLowerCase())
    );

    if (loading) {
        return (
            <div className="flex items-center justify-center min-h-[400px]">
                <Loader className="w-8 h-8 animate-spin text-orange-600" />
            </div>
        );
    }

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Business Units</h1>
                    <p className="text-gray-500 dark:text-gray-400 mt-1">Manage business units and their members</p>
                </div>
                {isAdmin && (
                    <button
                        onClick={() => setShowCreateModal(true)}
                        className="flex items-center gap-2 px-4 py-2 bg-orange-600 hover:bg-orange-700 text-white rounded-lg transition-colors font-medium"
                    >
                        <Plus className="w-5 h-5" />
                        Create Business Unit
                    </button>
                )}
            </div>

            {/* Search */}
            <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                <input
                    type="text"
                    placeholder="Search business units..."
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    className="w-full pl-10 pr-4 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-orange-500"
                />
            </div>

            {/* Business Units List */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {filteredBusinessUnits.map((bu) => (
                    <div
                        key={bu.id}
                        className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-6 hover:border-orange-500 dark:hover:border-orange-500 transition-colors"
                    >
                        <div className="flex items-start justify-between mb-4">
                            <div className="flex items-center gap-3">
                                <div className="p-2 bg-orange-100 dark:bg-orange-900/20 rounded-lg">
                                    <Building2 className="w-6 h-6 text-orange-600 dark:text-orange-400" />
                                </div>
                                <div>
                                    <h3 className="font-semibold text-gray-900 dark:text-white">{bu.name}</h3>
                                    <p className="text-sm text-gray-500 dark:text-gray-400">/{bu.slug}</p>
                                </div>
                            </div>
                            {(bu.can_manage_members === true || isAdmin) && (
                                <div className="flex items-center gap-2">
                                    <button
                                        onClick={() => handleEdit(bu)}
                                        className="p-1.5 text-gray-400 hover:text-blue-600 dark:hover:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded transition-colors"
                                        title="Edit Business Unit"
                                    >
                                        <Edit2 className="w-4 h-4" />
                                    </button>
                                    {isAdmin && (
                                        <button
                                            onClick={() => handleDelete(bu)}
                                            className="p-1.5 text-gray-400 hover:text-red-600 dark:hover:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 rounded transition-colors"
                                            title="Delete Business Unit"
                                        >
                                            <Trash2 className="w-4 h-4" />
                                        </button>
                                    )}
                                </div>
                            )}
                        </div>
                        {bu.description && (
                            <p className="text-sm text-gray-600 dark:text-gray-400 mb-3">{bu.description}</p>
                        )}
                        <div className="flex items-center gap-2 mb-4 text-sm text-gray-500 dark:text-gray-400">
                            <Users className="w-4 h-4" />
                            <span>{bu.member_count || 0} {bu.member_count === 1 ? 'member' : 'members'}</span>
                        </div>
                        <button
                            onClick={() => handleViewMembers(bu)}
                            className="w-full flex items-center justify-center gap-2 px-4 py-2 border border-gray-200 dark:border-gray-700 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors text-sm font-medium"
                        >
                            <Users className="w-4 h-4" />
                            Manage Members
                        </button>
                    </div>
                ))}
            </div>

            {filteredBusinessUnits.length === 0 && (
                <div className="text-center py-12">
                    <Building2 className="w-16 h-16 text-gray-400 mx-auto mb-4" />
                    <p className="text-gray-500 dark:text-gray-400">No business units found</p>
                </div>
            )}

            {/* Create Modal */}
            {showCreateModal && (
                <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4 overflow-y-auto">
                    <div className="bg-white dark:bg-gray-900 rounded-2xl p-4 sm:p-6 max-w-md w-full border border-gray-200 dark:border-gray-800 my-4">
                        <div className="flex items-center justify-between mb-4">
                            <h2 className="text-xl font-bold text-gray-900 dark:text-white">Create Business Unit</h2>
                            <button
                                onClick={() => setShowCreateModal(false)}
                                className="p-1 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg"
                            >
                                <X className="w-5 h-5" />
                            </button>
                        </div>
                        <div className="space-y-4">
                            <div>
                                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                                    Name *
                                </label>
                                <input
                                    type="text"
                                    value={createForm.name}
                                    onChange={(e) => setCreateForm({ ...createForm, name: e.target.value })}
                                    className="w-full px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
                                    placeholder="e.g., it-operations"
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                                    Slug *
                                </label>
                                <input
                                    type="text"
                                    value={createForm.slug}
                                    onChange={(e) => setCreateForm({ ...createForm, slug: e.target.value.toLowerCase().replace(/\s+/g, '-') })}
                                    className="w-full px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
                                    placeholder="e.g., it-operations"
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                                    Description
                                </label>
                                <textarea
                                    value={createForm.description}
                                    onChange={(e) => setCreateForm({ ...createForm, description: e.target.value })}
                                    className="w-full px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
                                    rows={3}
                                    placeholder="Optional description"
                                />
                            </div>
                            <div className="flex gap-3 pt-4">
                                <button
                                    onClick={() => setShowCreateModal(false)}
                                    className="flex-1 px-4 py-2 border border-gray-200 dark:border-gray-700 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
                                >
                                    Cancel
                                </button>
                                <button
                                    onClick={handleCreate}
                                    className="flex-1 px-4 py-2 bg-orange-600 hover:bg-orange-700 text-white rounded-lg transition-colors font-medium"
                                >
                                    Create
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {/* Edit Modal */}
            {showEditModal && selectedBusinessUnit && (
                <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4 overflow-y-auto">
                    <div className="bg-white dark:bg-gray-900 rounded-2xl p-4 sm:p-6 max-w-md w-full border border-gray-200 dark:border-gray-800 my-4">
                        <div className="flex items-center justify-between mb-4">
                            <h2 className="text-xl font-bold text-gray-900 dark:text-white">Edit Business Unit</h2>
                            <button
                                onClick={() => setShowEditModal(false)}
                                className="p-1 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg"
                            >
                                <X className="w-5 h-5" />
                            </button>
                        </div>
                        <div className="space-y-4">
                            <div>
                                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                                    Name
                                </label>
                                <input
                                    type="text"
                                    value={editForm.name}
                                    onChange={(e) => setEditForm({ ...editForm, name: e.target.value })}
                                    className="w-full px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                                    Description
                                </label>
                                <textarea
                                    value={editForm.description}
                                    onChange={(e) => setEditForm({ ...editForm, description: e.target.value })}
                                    className="w-full px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
                                    rows={3}
                                />
                            </div>
                            <div className="flex gap-3 pt-4">
                                <button
                                    onClick={() => setShowEditModal(false)}
                                    className="flex-1 px-4 py-2 border border-gray-200 dark:border-gray-700 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
                                >
                                    Cancel
                                </button>
                                <button
                                    onClick={handleUpdate}
                                    className="flex-1 px-4 py-2 bg-orange-600 hover:bg-orange-700 text-white rounded-lg transition-colors font-medium"
                                >
                                    Save
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {/* Members Modal */}
            {showMembersModal && selectedBusinessUnit && (
                <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4 overflow-y-auto">
                    <div className="bg-white dark:bg-gray-900 rounded-2xl p-4 sm:p-6 max-w-2xl w-full border border-gray-200 dark:border-gray-800 max-h-[90vh] my-4">
                        <div className="flex items-center justify-between mb-4">
                            <div>
                                <h2 className="text-lg sm:text-xl font-bold text-gray-900 dark:text-white">{selectedBusinessUnit.name} - Members</h2>
                                <p className="text-xs sm:text-sm text-gray-500 dark:text-gray-400">Manage members and owners</p>
                            </div>
                            <button
                                onClick={() => {
                                    setShowMembersModal(false);
                                    setSelectedBusinessUnit(null);
                                    setUserSearchQuery('');
                                    setSelectedUser(null);
                                    setShowUserDropdown(false);
                                    // Reset form without default role
                                    setAddMemberForm({ user_email: '', role_id: undefined });
                                }}
                                className="p-1 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
                            >
                                <X className="w-5 h-5 text-gray-500 dark:text-gray-400" />
                            </button>
                        </div>

                        {/* Add Member Form - Only show for owners/admins */}
                        {(() => {
                            // Check if user can manage members - check both selectedBusinessUnit.role and also check if user is owner in the businessUnits list
                            const selectedBURole = selectedBusinessUnit.role;
                            const matchingBU = businessUnits.find(bu => bu.id === selectedBusinessUnit.id);
                            const canManage = isAdmin || (matchingBU && matchingBU.can_manage_members === true);
                            return canManage;
                        })() && (
                            <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-3 sm:p-4 mb-4">
                                <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-3">Add Member</h3>
                                <div className="space-y-3">
                                    {/* User Search */}
                                    <div className="relative" ref={userSearchRef}>
                                        <div className="relative">
                                            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                                            <input
                                                type="text"
                                                value={userSearchQuery}
                                                onChange={(e) => {
                                                    setUserSearchQuery(e.target.value);
                                                    setShowUserDropdown(true);
                                                    if (e.target.value !== selectedUser?.email) {
                                                        setSelectedUser(null);
                                                        setAddMemberForm({ ...addMemberForm, user_email: '' });
                                                    }
                                                }}
                                                onFocus={() => {
                                                    if (userSearchQuery) {
                                                        setShowUserDropdown(true);
                                                    }
                                                }}
                                                placeholder="Search by email or name..."
                                                className="w-full pl-10 pr-3 py-2 text-sm border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-orange-500"
                                            />
                                        </div>
                                        {showUserDropdown && filteredUsers.length > 0 && (
                                            <div className="absolute z-10 w-full mt-1 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg max-h-60 overflow-y-auto">
                                                {filteredUsers.map((user) => (
                                                    <button
                                                        key={user.id}
                                                        type="button"
                                                        onClick={() => handleUserSelect(user)}
                                                        className="w-full text-left px-4 py-2 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors flex items-center gap-3"
                                                    >
                                                        <div className="flex-1">
                                                            <p className="font-medium text-sm text-gray-900 dark:text-white">{user.email}</p>
                                                            {(user.full_name || user.username) && (
                                                                <p className="text-xs text-gray-500 dark:text-gray-400">
                                                                    {user.full_name || user.username}
                                                                </p>
                                                            )}
                                                        </div>
                                                    </button>
                                                ))}
                                            </div>
                                        )}
                                        {showUserDropdown && userSearchQuery && filteredUsers.length === 0 && (
                                            <div className="absolute z-10 w-full mt-1 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg p-4 text-center text-sm text-gray-500 dark:text-gray-400">
                                                No users found matching "{userSearchQuery}"
                                            </div>
                                        )}
                                    </div>
                                    
                                    {/* Role Selector */}
                                    <div>
                                        <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1.5">
                                            Role
                                        </label>
                                        <select
                                            value={addMemberForm.role_id || ''}
                                            onChange={(e) => setAddMemberForm({ ...addMemberForm, role_id: e.target.value || undefined })}
                                            className="w-full px-3 py-2 text-sm border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-orange-500"
                                            disabled={loadingRoles}
                                        >
                                            <option value="">Select Role</option>
                                            {availableRoles.map((role) => (
                                                <option key={role.id} value={role.id}>
                                                    {role.name.charAt(0).toUpperCase() + role.name.slice(1).replace(/-/g, ' ')}
                                                </option>
                                            ))}
                                        </select>
                                        <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                                            Roles are managed on the <span className="font-medium">Roles</span> page
                                        </p>
                                    </div>
                                    
                                    {/* Add Button */}
                                    <button
                                        onClick={handleAddMember}
                                        disabled={!addMemberForm.user_email || !addMemberForm.role_id}
                                        className="w-full px-4 py-2 bg-orange-600 hover:bg-orange-700 disabled:bg-gray-400 disabled:cursor-not-allowed text-white rounded-lg transition-colors font-medium flex items-center justify-center gap-2 text-sm"
                                    >
                                        <UserPlus className="w-4 h-4" />
                                        Add Member
                                    </button>
                                </div>
                            </div>
                        )}

                        {/* Members List */}
                        {loadingMembers ? (
                            <div className="flex items-center justify-center py-8">
                                <Loader className="w-6 h-6 animate-spin text-orange-600" />
                            </div>
                        ) : (
                            <div className="space-y-2">
                                {members.map((member) => (
                                    <div
                                        key={member.id}
                                        className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800 rounded-lg"
                                    >
                                        <div className="flex items-center gap-3 min-w-0 flex-1">
                                            <div className="p-2 bg-white dark:bg-gray-900 rounded-lg flex-shrink-0">
                                                <Users className="w-4 h-4 text-gray-600 dark:text-gray-400" />
                                            </div>
                                            <div className="min-w-0 flex-1">
                                                <p className="font-medium text-sm text-gray-900 dark:text-white truncate">{member.user_email}</p>
                                                <p className="text-xs text-gray-500 dark:text-gray-400 capitalize">
                                                    {member.role ? member.role.replace(/-/g, ' ').replace(/\b\w/g, l => l.toUpperCase()) : 'No role'}
                                                </p>
                                            </div>
                                        </div>
                                        {(() => {
                                            // Check if user can manage members (permission-based, not role-name-based)
                                            const matchingBU = businessUnits.find(bu => bu.id === selectedBusinessUnit.id);
                                            const canManage = isAdmin || (matchingBU && matchingBU.can_manage_members === true);
                                            return canManage;
                                        })() && (
                                            <button
                                                onClick={() => handleRemoveMember(member)}
                                                className="p-1.5 text-gray-400 hover:text-red-600 dark:hover:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 rounded transition-colors flex-shrink-0 ml-2"
                                                title="Remove Member"
                                            >
                                                <UserMinus className="w-4 h-4" />
                                            </button>
                                        )}
                                    </div>
                                ))}
                                {members.length === 0 && (
                                    <div className="text-center py-8 text-gray-500 dark:text-gray-400 text-sm">
                                        No members yet. Add members using the form above.
                                    </div>
                                )}
                            </div>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
};

