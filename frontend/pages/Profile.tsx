import React, { useState, useRef } from 'react';
import { User, Mail, Shield, Camera, Lock, Save, X, Eye, EyeOff, AlertCircle, CheckCircle2 } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import api from '../services/api';
import { API_URL } from '../constants/api';

export const ProfilePage: React.FC = () => {
    const { user, logout, isAdmin } = useAuth();
    const [isEditing, setIsEditing] = useState(false);
    const [isChangingPassword, setIsChangingPassword] = useState(false);
    const [loading, setLoading] = useState(false);
    const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null);
    const [showCurrentPassword, setShowCurrentPassword] = useState(false);
    const [showNewPassword, setShowNewPassword] = useState(false);
    const [showConfirmPassword, setShowConfirmPassword] = useState(false);
    const fileInputRef = useRef<HTMLInputElement>(null);

    // Profile form state
    const [profileData, setProfileData] = useState({
        full_name: user?.full_name || '',
        username: user?.username || '',
        email: user?.email || '',
    });

    // Password form state
    const [passwordData, setPasswordData] = useState({
        current_password: '',
        new_password: '',
        confirm_password: '',
    });

    // Avatar state
    const [avatarPreview, setAvatarPreview] = useState<string | null>(null);
    const [avatarFile, setAvatarFile] = useState<File | null>(null);

    const handleProfileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        setProfileData(prev => ({
            ...prev,
            [e.target.name]: e.target.value
        }));
    };

    const handlePasswordChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        setPasswordData(prev => ({
            ...prev,
            [e.target.name]: e.target.value
        }));
    };

    const handleAvatarClick = () => {
        fileInputRef.current?.click();
    };

    const handleAvatarChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (file) {
            // Validate file size (max 5MB)
            if (file.size > 5 * 1024 * 1024) {
                setMessage({ type: 'error', text: 'Image size must be less than 5MB' });
                return;
            }

            // Validate file type
            if (!file.type.startsWith('image/')) {
                setMessage({ type: 'error', text: 'Please select an image file' });
                return;
            }

            setAvatarFile(file);
            const reader = new FileReader();
            reader.onloadend = () => {
                setAvatarPreview(reader.result as string);
            };
            reader.readAsDataURL(file);
        }
    };

    const handleSaveProfile = async () => {
        setLoading(true);
        setMessage(null);

        try {
            // Update profile information
            await api.updateCurrentUser({
                full_name: profileData.full_name,
                username: profileData.username,
            });

            // Upload avatar if changed
            if (avatarFile) {
                await api.uploadAvatar(avatarFile);
            }

            setMessage({ type: 'success', text: 'Profile updated successfully!' });
            setIsEditing(false);

            // Reload page to update user data in context
            setTimeout(() => window.location.reload(), 1500);
        } catch (error: any) {
            setMessage({ type: 'error', text: error.message || 'Failed to update profile' });
        } finally {
            setLoading(false);
        }
    };

    const handleChangePassword = async () => {
        setMessage(null);

        // Validate passwords
        if (!passwordData.current_password || !passwordData.new_password || !passwordData.confirm_password) {
            setMessage({ type: 'error', text: 'Please fill in all password fields' });
            return;
        }

        if (passwordData.new_password.length < 8) {
            setMessage({ type: 'error', text: 'New password must be at least 8 characters' });
            return;
        }

        if (passwordData.new_password !== passwordData.confirm_password) {
            setMessage({ type: 'error', text: 'New passwords do not match' });
            return;
        }

        setLoading(true);

        try {
            await api.changePassword({
                current_password: passwordData.current_password,
                new_password: passwordData.new_password
            });

            setMessage({ type: 'success', text: 'Password changed successfully! Please login again.' });
            setPasswordData({ current_password: '', new_password: '', confirm_password: '' });
            setIsChangingPassword(false);

            // Logout after password change
            setTimeout(async () => {
                await logout();
                window.location.href = '/#/login';
            }, 2000);
        } catch (error: any) {
            setMessage({ type: 'error', text: error.message || 'Failed to change password' });
        } finally {
            setLoading(false);
        }
    };

    const handleCancel = () => {
        setIsEditing(false);
        setIsChangingPassword(false);
        setProfileData({
            full_name: user?.full_name || '',
            username: user?.username || '',
            email: user?.email || '',
        });
        setPasswordData({ current_password: '', new_password: '', confirm_password: '' });
        setAvatarPreview(null);
        setAvatarFile(null);
        setMessage(null);
    };

    const getInitials = () => {
        if (user?.full_name) {
            return user.full_name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2);
        }
        return user?.username?.slice(0, 2).toUpperCase() || 'U';
    };

    return (
        <div className="max-w-4xl mx-auto space-y-6">
            <div className="flex items-center justify-between">
                <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Profile Settings</h1>
                {!isEditing && !isChangingPassword && (
                    <button
                        onClick={() => setIsEditing(true)}
                        className="px-4 py-2 bg-orange-600 text-white text-sm font-medium rounded-lg hover:bg-orange-500 transition-colors shadow-lg shadow-orange-500/25"
                    >
                        Edit Profile
                    </button>
                )}
            </div>

            {/* Message Alert */}
            {message && (
                <div className={`p-4 rounded-lg border flex items-center gap-3 ${message.type === 'success'
                    ? 'bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800 text-green-700 dark:text-green-400'
                    : 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800 text-red-700 dark:text-red-400'
                    }`}>
                    {message.type === 'success' ? <CheckCircle2 className="w-5 h-5" /> : <AlertCircle className="w-5 h-5" />}
                    <span>{message.text}</span>
                </div>
            )}

            {/* Profile Information Card */}
            <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-2xl p-8 transition-colors">
                <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-6">Profile Information</h2>

                {/* Avatar Section */}
                <div className="flex flex-col md:flex-row items-center gap-6 mb-8 pb-8 border-b border-gray-200 dark:border-gray-800">
                    <div className="relative group">
                        {avatarPreview || user?.avatar_url ? (
                            <img
                                src={avatarPreview || (user?.avatar_url?.startsWith('http') ? user.avatar_url : `${API_URL}${user?.avatar_url}`)}
                                alt="Profile Preview"
                                className="w-24 h-24 rounded-full border-4 border-white dark:border-gray-800 shadow-xl object-cover"
                            />
                        ) : (
                            <div className="w-24 h-24 rounded-full border-4 border-white dark:border-gray-800 shadow-xl bg-orange-600 dark:bg-orange-500 flex items-center justify-center text-white font-bold text-2xl">
                                {getInitials()}
                            </div>
                        )}
                        {isEditing && (
                            <button
                                onClick={handleAvatarClick}
                                className="absolute inset-0 flex items-center justify-center bg-black/50 rounded-full opacity-0 group-hover:opacity-100 transition-opacity"
                            >
                                <Camera className="w-6 h-6 text-white" />
                            </button>
                        )}
                        <input
                            ref={fileInputRef}
                            type="file"
                            accept="image/*"
                            onChange={handleAvatarChange}
                            className="hidden"
                        />
                    </div>
                    <div className="text-center md:text-left">
                        <h2 className="text-2xl font-bold text-gray-900 dark:text-white">{user?.full_name || user?.username}</h2>
                        <p className="text-gray-500 dark:text-gray-400">{user?.email}</p>
                        <div className="flex items-center justify-center md:justify-start gap-2 mt-2">
                            <span className="px-2 py-0.5 rounded bg-orange-500/10 text-orange-600 dark:text-orange-400 border border-orange-500/20 text-xs font-medium">
                                {user?.roles.join(', ') || 'No role'}
                            </span>
                        </div>
                        {isEditing && (
                            <p className="text-xs text-gray-500 dark:text-gray-400 mt-2">
                                Click on avatar to change (Max 5MB)
                            </p>
                        )}
                    </div>
                </div>

                {/* Profile Fields */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div className="space-y-2">
                        <label className="text-sm font-medium text-gray-700 dark:text-gray-300">Full Name</label>
                        {isEditing ? (
                            <input
                                type="text"
                                name="full_name"
                                value={profileData.full_name}
                                onChange={handleProfileChange}
                                className="w-full px-4 py-3 border border-gray-300 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-orange-500"
                                placeholder="Enter your full name"
                            />
                        ) : (
                            <div className="flex items-center gap-3 p-3 bg-gray-50 dark:bg-gray-950 rounded-lg border border-gray-200 dark:border-gray-800">
                                <User className="w-4 h-4 text-gray-400" />
                                <span className="text-gray-900 dark:text-gray-200">{user?.full_name}</span>
                            </div>
                        )}
                    </div>

                    <div className="space-y-2">
                        <label className="text-sm font-medium text-gray-700 dark:text-gray-300">Username</label>
                        {isEditing ? (
                            <input
                                type="text"
                                name="username"
                                value={profileData.username}
                                onChange={handleProfileChange}
                                className="w-full px-4 py-3 border border-gray-300 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-orange-500"
                                placeholder="Enter your username"
                            />
                        ) : (
                            <div className="flex items-center gap-3 p-3 bg-gray-50 dark:bg-gray-950 rounded-lg border border-gray-200 dark:border-gray-800">
                                <User className="w-4 h-4 text-gray-400" />
                                <span className="text-gray-900 dark:text-gray-200">{user?.username}</span>
                            </div>
                        )}
                    </div>

                    <div className="space-y-2">
                        <label className="text-sm font-medium text-gray-700 dark:text-gray-300">Email Address</label>
                        <div className="flex items-center gap-3 p-3 bg-gray-50 dark:bg-gray-950 rounded-lg border border-gray-200 dark:border-gray-800">
                            <Mail className="w-4 h-4 text-gray-400" />
                            <span className="text-gray-900 dark:text-gray-200">{user?.email}</span>
                        </div>
                        <p className="text-xs text-gray-500">Email cannot be changed</p>
                    </div>

                    <div className="space-y-2">
                        <label className="text-sm font-medium text-gray-700 dark:text-gray-300">Role</label>
                        <div className="flex items-center gap-3 p-3 bg-gray-50 dark:bg-gray-950 rounded-lg border border-gray-200 dark:border-gray-800">
                            <Shield className="w-4 h-4 text-gray-400" />
                            <span className="text-gray-900 dark:text-gray-200">
                                {user?.roles.join(', ') || 'No role'}
                            </span>
                        </div>
                        <p className="text-xs text-gray-500">Role is managed by administrators</p>
                    </div>
                </div>

                {/* Action Buttons for Profile */}
                {isEditing && (
                    <div className="mt-8 pt-6 border-t border-gray-200 dark:border-gray-800 flex justify-end gap-3">
                        <button
                            onClick={handleCancel}
                            disabled={loading}
                            className="px-4 py-2 text-sm text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white transition-colors disabled:opacity-50"
                        >
                            Cancel
                        </button>
                        <button
                            onClick={handleSaveProfile}
                            disabled={loading}
                            className="px-4 py-2 bg-orange-600 text-white text-sm font-medium rounded-lg hover:bg-orange-500 transition-colors shadow-lg shadow-orange-500/25 flex items-center gap-2 disabled:opacity-50"
                        >
                            {loading ? (
                                <>
                                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                                    Saving...
                                </>
                            ) : (
                                <>
                                    <Save className="w-4 h-4" />
                                    Save Changes
                                </>
                            )}
                        </button>
                    </div>
                )}
            </div>

            {/* Password Change Card */}
            <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-2xl p-8 transition-colors">
                <div className="flex items-center justify-between mb-6">
                    <div>
                        <h2 className="text-xl font-bold text-gray-900 dark:text-white">Password & Security</h2>
                        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">Manage your password and security settings</p>
                    </div>
                    {!isChangingPassword && !isEditing && (
                        <button
                            onClick={() => setIsChangingPassword(true)}
                            className="px-4 py-2 border border-gray-300 dark:border-gray-700 text-gray-700 dark:text-gray-300 text-sm font-medium rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors flex items-center gap-2"
                        >
                            <Lock className="w-4 h-4" />
                            Change Password
                        </button>
                    )}
                </div>

                {isChangingPassword ? (
                    <div className="space-y-4">
                        <div className="space-y-2">
                            <label className="text-sm font-medium text-gray-700 dark:text-gray-300">Current Password</label>
                            <div className="relative">
                                <input
                                    type={showCurrentPassword ? 'text' : 'password'}
                                    name="current_password"
                                    value={passwordData.current_password}
                                    onChange={handlePasswordChange}
                                    className="w-full px-4 py-3 pr-12 border border-gray-300 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-orange-500"
                                    placeholder="Enter current password"
                                />
                                <button
                                    type="button"
                                    onClick={() => setShowCurrentPassword(!showCurrentPassword)}
                                    className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                                >
                                    {showCurrentPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                                </button>
                            </div>
                        </div>

                        <div className="space-y-2">
                            <label className="text-sm font-medium text-gray-700 dark:text-gray-300">New Password</label>
                            <div className="relative">
                                <input
                                    type={showNewPassword ? 'text' : 'password'}
                                    name="new_password"
                                    value={passwordData.new_password}
                                    onChange={handlePasswordChange}
                                    className="w-full px-4 py-3 pr-12 border border-gray-300 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-orange-500"
                                    placeholder="Enter new password (min 8 characters)"
                                />
                                <button
                                    type="button"
                                    onClick={() => setShowNewPassword(!showNewPassword)}
                                    className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                                >
                                    {showNewPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                                </button>
                            </div>
                        </div>

                        <div className="space-y-2">
                            <label className="text-sm font-medium text-gray-700 dark:text-gray-300">Confirm New Password</label>
                            <div className="relative">
                                <input
                                    type={showConfirmPassword ? 'text' : 'password'}
                                    name="confirm_password"
                                    value={passwordData.confirm_password}
                                    onChange={handlePasswordChange}
                                    className="w-full px-4 py-3 pr-12 border border-gray-300 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-orange-500"
                                    placeholder="Confirm new password"
                                />
                                <button
                                    type="button"
                                    onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                                    className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                                >
                                    {showConfirmPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                                </button>
                            </div>
                        </div>

                        <div className="mt-6 pt-6 border-t border-gray-200 dark:border-gray-800 flex justify-end gap-3">
                            <button
                                onClick={handleCancel}
                                disabled={loading}
                                className="px-4 py-2 text-sm text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white transition-colors disabled:opacity-50"
                            >
                                Cancel
                            </button>
                            <button
                                onClick={handleChangePassword}
                                disabled={loading}
                                className="px-4 py-2 bg-orange-600 text-white text-sm font-medium rounded-lg hover:bg-orange-500 transition-colors shadow-lg shadow-orange-500/25 flex items-center gap-2 disabled:opacity-50"
                            >
                                {loading ? (
                                    <>
                                        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                                        Changing...
                                    </>
                                ) : (
                                    <>
                                        <Lock className="w-4 h-4" />
                                        Change Password
                                    </>
                                )}
                            </button>
                        </div>
                    </div>
                ) : (
                    <div className="text-sm text-gray-600 dark:text-gray-400">
                        <p>• Use a strong password with at least 8 characters</p>
                        <p>• Include uppercase, lowercase, numbers, and special characters</p>
                        <p>• Don't reuse passwords from other accounts</p>
                    </div>
                )}
            </div>

            {/* Roles & Permissions */}
            <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-2xl p-8 transition-colors">
                <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-4">Roles & Permissions</h2>

                {/* Roles */}
                <div className="mb-6">
                    <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">Your Roles</h3>
                    <div className="flex flex-wrap gap-2">
                        {user?.roles && user.roles.length > 0 ? (
                            user.roles.map((role) => (
                                <span
                                    key={role}
                                    className="inline-flex items-center px-3 py-1.5 rounded-lg text-sm font-medium bg-orange-50 dark:bg-orange-900/20 text-orange-600 dark:text-orange-400 border border-orange-100 dark:border-orange-800"
                                >
                                    <Shield className="w-4 h-4 mr-1.5" />
                                    {role}
                                </span>
                            ))
                        ) : (
                            <span className="text-gray-500 dark:text-gray-400 text-sm">No roles assigned</span>
                        )}
                    </div>
                </div>

                {/* Permissions */}
                <div>
                    <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">Your Permissions</h3>
                    <div className="space-y-2">
                        <p className="text-gray-500 dark:text-gray-400 text-sm">Permissions are managed through Casbin policies and not displayed here.</p>
                    </div>
                </div>
            </div>

            {/* Account Information */}
            <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-2xl p-8 transition-colors">
                <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-4">Account Information</h2>
                <div className="space-y-3 text-sm">
                    <div className="flex justify-between py-2 border-b border-gray-100 dark:border-gray-800">
                        <span className="text-gray-600 dark:text-gray-400">Account ID</span>
                        <span className="text-gray-900 dark:text-white font-mono">{user?.id.slice(0, 8)}...</span>
                    </div>
                    <div className="flex justify-between py-2 border-b border-gray-100 dark:border-gray-800">
                        <span className="text-gray-600 dark:text-gray-400">Account Status</span>
                        <span className="text-green-600 dark:text-green-400 font-medium">
                            {user?.is_active ? 'Active' : 'Inactive'}
                        </span>
                    </div>
                    <div className="flex justify-between py-2">
                        <span className="text-gray-600 dark:text-gray-400">Member Since</span>
                        <span className="text-gray-900 dark:text-white">
                            {new Date(user?.created_at || Date.now()).toLocaleDateString('en-US', {
                                year: 'numeric',
                                month: 'long',
                                day: 'numeric'
                            })}
                        </span>
                    </div>
                </div>
            </div>

            {/* Debug Info - Temporary */}
            <div className="p-4 bg-gray-100 dark:bg-gray-800 rounded-lg overflow-auto text-xs font-mono">
                <p>User Debug:</p>
                <pre>{JSON.stringify(user, null, 2)}</pre>
            </div>
        </div>
    );
};