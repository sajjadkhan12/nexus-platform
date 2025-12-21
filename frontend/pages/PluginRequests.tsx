import React, { useState, useEffect } from 'react';
import { Search, CheckCircle2, XCircle, Clock, Loader, MessageCircle, UserX, AlertTriangle, Box } from 'lucide-react';
import api from '../services/api';
import { useNotification } from '../contexts/NotificationContext';
import { useAuth } from '../contexts/AuthContext';

interface AccessRequest {
    id: string;
    plugin_id: string;
    plugin_name?: string;
    user_id: string;
    user_email: string;
    status: string;
    requested_at: string;
    reviewed_at?: string;
    reviewed_by?: string;
    reason?: string; // Optional reason field
}

interface AccessGrant {
    id: number;
    plugin_id: string;
    plugin_name: string;
    user_id: string;
    user_email: string;
    granted_by: string;
    granted_at: string;
}

export const PluginRequestsPage: React.FC = () => {
    const { addNotification } = useNotification();
    const { isAdmin } = useAuth();
    const [requests, setRequests] = useState<AccessRequest[]>([]);
    const [loading, setLoading] = useState(true);
    const [searchQuery, setSearchQuery] = useState('');
    const [debouncedSearch, setDebouncedSearch] = useState('');
    const [statusFilter, setStatusFilter] = useState<'pending' | 'approved' | 'rejected' | 'revoked' | 'all'>('pending');
    const [grantingAccess, setGrantingAccess] = useState<string | null>(null);
    const [rejectingAccess, setRejectingAccess] = useState<string | null>(null);
    const [revokingAccess, setRevokingAccess] = useState<string | null>(null);
    const [restoringAccess, setRestoringAccess] = useState<string | null>(null);
    const [showRevokeModal, setShowRevokeModal] = useState(false);
    const [selectedRequest, setSelectedRequest] = useState<AccessRequest | null>(null);
    const [statusCounts, setStatusCounts] = useState({ pending: 0, approved: 0, rejected: 0, revoked: 0 });

    // Debounce search query (300ms delay)
    useEffect(() => {
        const timer = setTimeout(() => {
            setDebouncedSearch(searchQuery);
        }, 300);

        return () => clearTimeout(timer);
    }, [searchQuery]);

    // Load requests when search or status filter changes
    useEffect(() => {
        if (isAdmin) {
            loadRequests();
        }
    }, [isAdmin, debouncedSearch, statusFilter]);

    const loadRequests = async () => {
        try {
            setLoading(true);
            // Pass search query and status filter to backend
            const searchParam = debouncedSearch.trim() || undefined;
            const statusParam = statusFilter !== 'all' ? statusFilter : undefined;
            const requestsData = await api.getAllAccessRequests(searchParam, statusParam);
            setRequests(requestsData);
        } catch (err: any) {
            addNotification('error', err.message || 'Failed to load access requests');
        } finally {
            setLoading(false);
        }
    };

    const handleGrantAccess = async (request: AccessRequest) => {
        try {
            setGrantingAccess(request.id);
            await api.grantAccess(request.plugin_id, request.user_id);
            addNotification('success', `Access granted to ${request.user_email} for ${request.plugin_name || request.plugin_id}`);
            await loadRequests();
        } catch (err: any) {
            addNotification('error', err.message || 'Failed to grant access');
        } finally {
            setGrantingAccess(null);
        }
    };

    const handleRejectAccess = async (request: AccessRequest) => {
        if (!confirm(`Are you sure you want to reject the access request from ${request.user_email} for ${request.plugin_name || request.plugin_id}?`)) {
            return;
        }

        try {
            setRejectingAccess(request.id);
            await api.rejectAccess(request.plugin_id, request.user_id);
            addNotification('success', `Access request rejected for ${request.user_email} for ${request.plugin_name || request.plugin_id}`);
            await loadRequests();
        } catch (err: any) {
            addNotification('error', err.message || 'Failed to reject access request');
        } finally {
            setRejectingAccess(null);
        }
    };

    const handleRevokeClick = (request: AccessRequest) => {
        setSelectedRequest(request);
        setShowRevokeModal(true);
    };

    const handleRevokeConfirm = async () => {
        if (!selectedRequest) return;

        try {
            setRevokingAccess(selectedRequest.id);
            await api.revokeAccess(selectedRequest.plugin_id, selectedRequest.user_id);
            addNotification('success', `Access revoked for ${selectedRequest.user_email} from ${selectedRequest.plugin_name || selectedRequest.plugin_id}`);
            setShowRevokeModal(false);
            setSelectedRequest(null);
            await loadRequests();
            await loadStatusCounts(); // Refresh counts
        } catch (err: any) {
            addNotification('error', err.message || 'Failed to revoke access');
        } finally {
            setRevokingAccess(null);
        }
    };

    const handleRevokeCancel = () => {
        setShowRevokeModal(false);
        setSelectedRequest(null);
    };

    const handleRestoreAccess = async (request: AccessRequest) => {
        if (!confirm(`Are you sure you want to restore access for ${request.user_email} to ${request.plugin_name || request.plugin_id}?`)) {
            return;
        }

        try {
            setRestoringAccess(request.id);
            await api.restoreAccess(request.plugin_id, request.user_id);
            addNotification('success', `Access restored for ${request.user_email} to ${request.plugin_name || request.plugin_id}`);
            await loadRequests();
            await loadStatusCounts(); // Refresh counts
        } catch (err: any) {
            addNotification('error', err.message || 'Failed to restore access');
        } finally {
            setRestoringAccess(null);
        }
    };

    // Get user initials for avatar
    const getUserInitials = (email: string) => {
        const parts = email.split('@')[0].split('.');
        if (parts.length >= 2) {
            return (parts[0][0] + parts[1][0]).toUpperCase();
        }
        return email.substring(0, 2).toUpperCase();
    };

    // Get user display name from email
    const getUserName = (email: string) => {
        const parts = email.split('@')[0].split('.');
        if (parts.length >= 2) {
            return parts.map(p => p.charAt(0).toUpperCase() + p.slice(1)).join(' ');
        }
        return email.split('@')[0];
    };

    // Format date
    const formatDate = (dateString: string) => {
        const date = new Date(dateString);
        return date.toLocaleDateString('en-US', { month: '2-digit', day: '2-digit', year: 'numeric' });
    };

    // Load counts separately (without filters) to show accurate numbers
    useEffect(() => {
        if (isAdmin) {
            loadStatusCounts();
        }
    }, [isAdmin]);

    const loadStatusCounts = async () => {
        try {
            // Fetch all requests without filters to get accurate counts
            const allRequests = await api.getAllAccessRequests(undefined, undefined);
            
            setStatusCounts({
                pending: allRequests.filter(r => r.status.toLowerCase() === 'pending').length,
                approved: allRequests.filter(r => r.status.toLowerCase() === 'approved').length,
                rejected: allRequests.filter(r => r.status.toLowerCase() === 'rejected').length,
                revoked: allRequests.filter(r => r.status.toLowerCase() === 'revoked').length
            });
        } catch (err) {
            // Silently fail - counts are not critical
        }
    };

    if (!isAdmin) {
        return (
            <div className="min-h-screen flex items-center justify-center">
                <div className="text-center">
                    <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">Access Denied</h1>
                    <p className="text-gray-600 dark:text-gray-400">You need administrator privileges to view this page.</p>
                </div>
            </div>
        );
    }

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-start justify-between">
                <div>
                    <h1 className="text-4xl font-bold text-gray-900 dark:text-white mb-2">Plugin Access Management</h1>
                    <p className="text-gray-600 dark:text-gray-400 text-lg">
                        Review, approve, revoke, and restore permission requests for locked plugins.
                    </p>
                </div>
                
                {/* Status Filter Buttons */}
                <div className="flex items-center gap-2">
                    <button
                        onClick={() => setStatusFilter('pending')}
                        className={`relative px-5 py-2.5 rounded-xl font-semibold text-sm transition-all duration-200 ${
                            statusFilter === 'pending'
                                ? 'bg-gradient-to-r from-orange-500 to-orange-600 text-white shadow-lg shadow-orange-500/30 scale-105'
                                : 'bg-white dark:bg-gray-900 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 border border-gray-200 dark:border-gray-700'
                        }`}
                    >
                        <span className="flex items-center gap-2">
                            Pending 
                            {statusCounts.pending > 0 && (
                                <span className={`inline-flex items-center justify-center min-w-[1.25rem] h-5 px-1.5 rounded-full text-xs font-bold ${
                                    statusFilter === 'pending' 
                                        ? 'bg-white/20 text-white' 
                                        : 'bg-orange-500/10 text-orange-600 dark:text-orange-400'
                                }`}>
                                    {statusCounts.pending}
                                </span>
                            )}
                        </span>
                    </button>
                    <button
                        onClick={() => setStatusFilter('approved')}
                        className={`relative px-5 py-2.5 rounded-xl font-semibold text-sm transition-all duration-200 ${
                            statusFilter === 'approved'
                                ? 'bg-gradient-to-r from-orange-500 to-orange-600 text-white shadow-lg shadow-orange-500/30 scale-105'
                                : 'bg-white dark:bg-gray-900 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 border border-gray-200 dark:border-gray-700'
                        }`}
                    >
                        <span className="flex items-center gap-2">
                            Approved 
                            {statusCounts.approved > 0 && (
                                <span className={`inline-flex items-center justify-center min-w-[1.25rem] h-5 px-1.5 rounded-full text-xs font-bold ${
                                    statusFilter === 'approved' 
                                        ? 'bg-white/20 text-white' 
                                        : 'bg-green-500/10 text-green-600 dark:text-green-400'
                                }`}>
                                    {statusCounts.approved}
                                </span>
                            )}
                        </span>
                    </button>
                    <button
                        onClick={() => setStatusFilter('rejected')}
                        className={`relative px-5 py-2.5 rounded-xl font-semibold text-sm transition-all duration-200 ${
                            statusFilter === 'rejected'
                                ? 'bg-gradient-to-r from-orange-500 to-orange-600 text-white shadow-lg shadow-orange-500/30 scale-105'
                                : 'bg-white dark:bg-gray-900 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 border border-gray-200 dark:border-gray-700'
                        }`}
                    >
                        <span className="flex items-center gap-2">
                            Rejected 
                            {statusCounts.rejected > 0 && (
                                <span className={`inline-flex items-center justify-center min-w-[1.25rem] h-5 px-1.5 rounded-full text-xs font-bold ${
                                    statusFilter === 'rejected' 
                                        ? 'bg-white/20 text-white' 
                                        : 'bg-red-500/10 text-red-600 dark:text-red-400'
                                }`}>
                                    {statusCounts.rejected}
                                </span>
                            )}
                        </span>
                    </button>
                    <button
                        onClick={() => setStatusFilter('revoked')}
                        className={`relative px-5 py-2.5 rounded-xl font-semibold text-sm transition-all duration-200 ${
                            statusFilter === 'revoked'
                                ? 'bg-gradient-to-r from-orange-500 to-orange-600 text-white shadow-lg shadow-orange-500/30 scale-105'
                                : 'bg-white dark:bg-gray-900 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 border border-gray-200 dark:border-gray-700'
                        }`}
                    >
                        <span className="flex items-center gap-2">
                            Revoked 
                            {statusCounts.revoked > 0 && (
                                <span className={`inline-flex items-center justify-center min-w-[1.25rem] h-5 px-1.5 rounded-full text-xs font-bold ${
                                    statusFilter === 'revoked' 
                                        ? 'bg-white/20 text-white' 
                                        : 'bg-purple-500/10 text-purple-600 dark:text-purple-400'
                                }`}>
                                    {statusCounts.revoked}
                                </span>
                            )}
                        </span>
                    </button>
                </div>
            </div>

            {/* Info Banner for Revoked Tab */}
            {statusFilter === 'revoked' && (
                <div className="bg-gradient-to-r from-purple-50 to-violet-50 dark:from-purple-900/20 dark:to-violet-900/20 border border-purple-200/50 dark:border-purple-700/30 rounded-xl p-4">
                    <div className="flex items-start gap-3">
                        <div className="w-10 h-10 rounded-lg bg-purple-500/10 flex items-center justify-center flex-shrink-0">
                            <UserX className="w-5 h-5 text-purple-600 dark:text-purple-400" />
                        </div>
                        <div className="flex-1">
                            <h3 className="font-bold text-purple-900 dark:text-purple-200 mb-1">Revoked Access</h3>
                            <p className="text-sm text-purple-700 dark:text-purple-300 leading-relaxed">
                                These users previously had access but it was revoked. You can restore their access at any time using the "Restore Access" button.
                            </p>
                        </div>
                    </div>
                </div>
            )}

            {/* Search Bar */}
            <div className="relative group">
                <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400 dark:text-gray-500 group-focus-within:text-orange-500 transition-colors" />
                <input
                    type="text"
                    placeholder="Search by user, email, or plugin name..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="w-full pl-12 pr-4 py-3.5 bg-white dark:bg-gray-900 border-2 border-gray-200 dark:border-gray-700 rounded-xl text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500 focus:ring-2 focus:ring-orange-500/50 focus:border-orange-500 transition-all shadow-sm hover:shadow-md"
                />
            </div>

            {/* Loading State */}
            {loading ? (
                <div className="flex flex-col items-center justify-center py-16 bg-gradient-to-br from-white to-gray-50 dark:from-gray-900 dark:to-gray-800 rounded-2xl border border-gray-200/50 dark:border-gray-700/50">
                    <div className="relative">
                        <div className="absolute inset-0 bg-gradient-to-r from-orange-500 to-purple-500 rounded-full blur-xl opacity-50 animate-pulse" />
                        <Loader className="relative w-10 h-10 animate-spin text-orange-500" />
                    </div>
                    <p className="mt-4 text-gray-600 dark:text-gray-400 font-medium">Loading access requests...</p>
                </div>
            ) : (
                <>
                    {/* Request Cards */}
                    {requests.length > 0 ? (
                        <div className="space-y-4">
                            {requests.map((request) => {
                                const userName = getUserName(request.user_email);
                                const userInitials = getUserInitials(request.user_email);
                                const isPending = request.status.toLowerCase() === 'pending';

                                return (
                                    <div
                                        key={request.id}
                                        className="group relative bg-gradient-to-br from-white to-gray-50 dark:from-gray-900 dark:to-gray-800 rounded-2xl border border-gray-200/50 dark:border-gray-700/50 p-6 hover:shadow-xl hover:shadow-orange-500/5 dark:hover:shadow-orange-500/10 transition-all duration-300 overflow-hidden"
                                    >
                                        {/* Decorative gradient overlay */}
                                        <div className="absolute inset-0 bg-gradient-to-r from-orange-500/5 via-transparent to-purple-500/5 opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none" />
                                        
                                        <div className="relative flex items-start gap-5">
                                            {/* User Avatar with glow */}
                                            <div className="flex-shrink-0">
                                                <div className="relative">
                                                    <div className="absolute inset-0 bg-gradient-to-br from-orange-500 to-pink-500 rounded-full blur-md opacity-50 group-hover:opacity-75 transition-opacity" />
                                                    <div className="relative w-14 h-14 rounded-full bg-gradient-to-br from-orange-500 via-pink-500 to-purple-500 flex items-center justify-center text-white font-bold text-base shadow-lg ring-2 ring-white dark:ring-gray-900">
                                                        {userInitials}
                                                    </div>
                                                </div>
                                            </div>

                                            {/* Request Details */}
                                            <div className="flex-1 min-w-0">
                                                <div className="flex items-start justify-between gap-4">
                                                    <div className="flex-1 space-y-3">
                                                        {/* Header */}
                                                        <div className="flex items-center gap-2 flex-wrap">
                                                            <span className="font-bold text-gray-900 dark:text-white text-lg tracking-tight">{userName}</span>
                                                            <span className="text-gray-500 dark:text-gray-400 text-sm">requested access to</span>
                                                            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-sm font-semibold bg-gradient-to-r from-orange-500/10 to-orange-600/10 text-orange-700 dark:text-orange-300 border border-orange-500/20">
                                                                <Box className="w-3.5 h-3.5" />
                                                                {request.plugin_name || request.plugin_id}
                                                            </span>
                                                        </div>
                                                        
                                                        {/* Metadata */}
                                                        <div className="flex items-center gap-3 text-gray-600 dark:text-gray-400 text-sm">
                                                            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-gray-100/80 dark:bg-gray-800/80 border border-gray-200/50 dark:border-gray-700/50">
                                                                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 12a4 4 0 10-8 0 4 4 0 008 0zm0 0v1.5a2.5 2.5 0 005 0V12a9 9 0 10-9 9m4.5-1.206a8.959 8.959 0 01-4.5 1.207" />
                                                                </svg>
                                                                {request.user_email}
                                                            </span>
                                                            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-gray-100/80 dark:bg-gray-800/80 border border-gray-200/50 dark:border-gray-700/50">
                                                                <Clock className="w-3.5 h-3.5" />
                                                                {formatDate(request.requested_at)}
                                                            </span>
                                                        </div>

                                                        {/* Reason with better styling */}
                                                        {request.reason && (
                                                            <div className="flex items-start gap-2 p-3 bg-blue-50/50 dark:bg-blue-900/10 border border-blue-200/50 dark:border-blue-800/30 rounded-lg">
                                                                <MessageCircle className="w-4 h-4 mt-0.5 flex-shrink-0 text-blue-600 dark:text-blue-400" />
                                                                <span className="text-sm text-gray-700 dark:text-gray-300 italic leading-relaxed">"{request.reason}"</span>
                                                            </div>
                                                        )}
                                                    </div>

                                                    {/* Action Buttons - Pending */}
                                                    {isPending && (
                                                        <div className="flex items-center gap-2 flex-shrink-0">
                                                            <button
                                                                onClick={() => handleGrantAccess(request)}
                                                                disabled={grantingAccess === request.id}
                                                                className="px-4 py-2 bg-green-600/80 dark:bg-green-950/40 hover:bg-green-600 dark:hover:bg-green-950/60 text-green-50 dark:text-green-400 hover:text-white dark:hover:text-green-300 border border-green-700/50 dark:border-green-800/50 hover:border-green-800 dark:hover:border-green-700/70 rounded-lg font-medium text-sm transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                                                            >
                                                                {grantingAccess === request.id ? (
                                                                    <>
                                                                        <Loader className="w-4 h-4 animate-spin" />
                                                                        Approving...
                                                                    </>
                                                                ) : (
                                                                    <>
                                                                        <CheckCircle2 className="w-4 h-4" />
                                                                        Approve
                                                                    </>
                                                                )}
                                                            </button>
                                                            <button
                                                                onClick={() => handleRejectAccess(request)}
                                                                disabled={rejectingAccess === request.id}
                                                                className="px-4 py-2 bg-red-600/80 dark:bg-red-950/40 hover:bg-red-600 dark:hover:bg-red-950/60 text-red-50 dark:text-red-400 hover:text-white dark:hover:text-red-300 border border-red-700/50 dark:border-red-800/50 hover:border-red-800 dark:hover:border-red-700/70 rounded-lg font-medium text-sm transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                                                            >
                                                                {rejectingAccess === request.id ? (
                                                                    <>
                                                                        <Loader className="w-4 h-4 animate-spin" />
                                                                        Rejecting...
                                                                    </>
                                                                ) : (
                                                                    <>
                                                                        <XCircle className="w-4 h-4" />
                                                                        Reject
                                                                    </>
                                                                )}
                                                            </button>
                                                        </div>
                                                    )}

                                                    {/* Status Badge and Actions - Non-pending */}
                                                    {!isPending && (
                                                        <div className="flex items-center gap-3 flex-shrink-0">
                                                            {request.status.toLowerCase() === 'approved' ? (
                                                                <>
                                                                    <span className="inline-flex items-center gap-1.5 px-4 py-2 rounded-full text-sm font-bold bg-gradient-to-r from-green-500/15 to-emerald-500/15 text-green-700 dark:text-green-300 border border-green-500/30 shadow-sm">
                                                                        <CheckCircle2 className="w-4 h-4" />
                                                                        Approved
                                                                    </span>
                                                                    <button
                                                                        onClick={() => handleRevokeClick(request)}
                                                                        disabled={revokingAccess === request.id}
                                                                        className="px-4 py-2 bg-red-600/80 dark:bg-red-950/40 hover:bg-red-600 dark:hover:bg-red-950/60 text-red-50 dark:text-red-400 hover:text-white dark:hover:text-red-300 border border-red-700/50 dark:border-red-800/50 hover:border-red-800 dark:hover:border-red-700/70 rounded-lg font-medium text-sm transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                                                                        title="Revoke access"
                                                                    >
                                                                        <UserX className="w-4 h-4" />
                                                                        Revoke
                                                                    </button>
                                                                </>
                                                            ) : request.status.toLowerCase() === 'revoked' ? (
                                                                <>
                                                                    <span className="inline-flex items-center gap-1.5 px-4 py-2 rounded-full text-sm font-bold bg-gradient-to-r from-purple-500/15 to-violet-500/15 text-purple-700 dark:text-purple-300 border border-purple-500/30 shadow-sm">
                                                                        <UserX className="w-4 h-4" />
                                                                        Revoked
                                                                    </span>
                                                                    <button
                                                                        onClick={() => handleRestoreAccess(request)}
                                                                        disabled={restoringAccess === request.id}
                                                                        className="px-4 py-2 bg-green-600/80 dark:bg-green-950/40 hover:bg-green-600 dark:hover:bg-green-950/60 text-green-50 dark:text-green-400 hover:text-white dark:hover:text-green-300 border border-green-700/50 dark:border-green-800/50 hover:border-green-800 dark:hover:border-green-700/70 rounded-lg font-medium text-sm transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                                                                        title="Restore access"
                                                                    >
                                                                        {restoringAccess === request.id ? (
                                                                            <>
                                                                                <Loader className="w-4 h-4 animate-spin" />
                                                                                Restoring...
                                                                            </>
                                                                        ) : (
                                                                            <>
                                                                                <CheckCircle2 className="w-4 h-4" />
                                                                                Restore
                                                                            </>
                                                                        )}
                                                                    </button>
                                                                </>
                                                            ) : (
                                                                <span className="inline-flex items-center gap-1.5 px-4 py-2 rounded-full text-sm font-bold bg-gradient-to-r from-red-500/15 to-rose-500/15 text-red-700 dark:text-red-300 border border-red-500/30 shadow-sm">
                                                                    <XCircle className="w-4 h-4" />
                                                                    Rejected
                                                                </span>
                                                            )}
                                                        </div>
                                                    )}
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    ) : (
                        <div className="text-center py-16 bg-gradient-to-br from-white to-gray-50 dark:from-gray-900 dark:to-gray-800 rounded-2xl border border-gray-200/50 dark:border-gray-700/50">
                            <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-gradient-to-br from-orange-500/10 to-purple-500/10 flex items-center justify-center">
                                {statusFilter === 'pending' ? (
                                    <Clock className="w-8 h-8 text-gray-400 dark:text-gray-500" />
                                ) : statusFilter === 'approved' ? (
                                    <CheckCircle2 className="w-8 h-8 text-gray-400 dark:text-gray-500" />
                                ) : statusFilter === 'rejected' ? (
                                    <XCircle className="w-8 h-8 text-gray-400 dark:text-gray-500" />
                                ) : statusFilter === 'revoked' ? (
                                    <UserX className="w-8 h-8 text-gray-400 dark:text-gray-500" />
                                ) : (
                                    <Search className="w-8 h-8 text-gray-400 dark:text-gray-500" />
                                )}
                            </div>
                            <p className="text-gray-600 dark:text-gray-400 text-lg font-medium">
                                {debouncedSearch ? (
                                    'No requests found matching your search.'
                                ) : statusFilter === 'pending' ? (
                                    'No pending requests'
                                ) : statusFilter === 'approved' ? (
                                    'No approved requests'
                                ) : statusFilter === 'rejected' ? (
                                    'No rejected requests'
                                ) : statusFilter === 'revoked' ? (
                                    'No revoked access'
                                ) : (
                                    'No access requests found'
                                )}
                            </p>
                            <p className="text-gray-500 dark:text-gray-500 text-sm mt-2">
                                {debouncedSearch ? (
                                    'Try adjusting your search criteria.'
                                ) : statusFilter === 'pending' ? (
                                    'Pending requests will appear here when users request plugin access.'
                                ) : statusFilter === 'approved' ? (
                                    'Approved requests will show here. You can revoke access at any time.'
                                ) : statusFilter === 'rejected' ? (
                                    'Rejected requests are shown here for your records.'
                                ) : statusFilter === 'revoked' ? (
                                    'Revoked access will appear here. You can restore access if needed.'
                                ) : (
                                    'Access requests will appear here when users request plugin access.'
                                )}
                            </p>
                        </div>
                    )}
                </>
            )}

            {/* Revoke Confirmation Modal */}
            {showRevokeModal && selectedRequest && (
                <div className="fixed inset-0 bg-black/60 backdrop-blur-md flex items-center justify-center z-50 p-4 animate-in fade-in duration-200">
                    <div className="relative bg-gradient-to-br from-white to-gray-50 dark:from-gray-900 dark:to-gray-800 border border-gray-200/50 dark:border-gray-700/50 rounded-2xl p-8 max-w-md w-full shadow-2xl animate-in zoom-in duration-300">
                        {/* Decorative gradient */}
                        <div className="absolute inset-0 bg-gradient-to-br from-red-500/5 via-transparent to-orange-500/5 rounded-2xl pointer-events-none" />
                        
                        {/* Warning Icon */}
                        <div className="relative flex items-start gap-4 mb-6">
                            <div className="relative flex-shrink-0">
                                <div className="absolute inset-0 bg-red-500 rounded-full blur-xl opacity-25" />
                                <div className="relative w-14 h-14 rounded-full bg-gradient-to-br from-red-500 to-rose-600 flex items-center justify-center shadow-lg">
                                    <AlertTriangle className="w-7 h-7 text-white" />
                                </div>
                            </div>
                            <div className="flex-1">
                                <h3 className="text-xl font-bold text-gray-900 dark:text-white mb-2">Revoke Plugin Access</h3>
                                <p className="text-sm text-gray-600 dark:text-gray-400 leading-relaxed">
                                    This action will immediately revoke access for this user.
                                </p>
                            </div>
                        </div>

                        {/* Details */}
                        <div className="relative bg-white/50 dark:bg-gray-800/50 backdrop-blur-sm border border-gray-200/50 dark:border-gray-700/50 rounded-xl p-5 mb-5 shadow-sm">
                            <div className="space-y-3 text-sm">
                                <div className="flex items-start gap-2">
                                    <span className="text-gray-500 dark:text-gray-400 font-medium min-w-[60px]">User:</span>
                                    <div className="flex-1">
                                        <div className="font-bold text-gray-900 dark:text-white">{getUserName(selectedRequest.user_email)}</div>
                                        <div className="text-gray-600 dark:text-gray-400 text-xs mt-0.5">{selectedRequest.user_email}</div>
                                    </div>
                                </div>
                                <div className="flex items-center gap-2">
                                    <span className="text-gray-500 dark:text-gray-400 font-medium min-w-[60px]">Plugin:</span>
                                    <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-bold bg-orange-500/10 text-orange-700 dark:text-orange-300 border border-orange-500/20">
                                        <Box className="w-3 h-3" />
                                        {selectedRequest.plugin_name || selectedRequest.plugin_id}
                                    </span>
                                </div>
                            </div>
                        </div>

                        {/* Warning Message */}
                        <div className="relative bg-red-50 dark:bg-red-900/20 border border-red-200/50 dark:border-red-800/30 rounded-xl p-4 mb-6">
                            <div className="flex items-start gap-3">
                                <AlertTriangle className="w-5 h-5 text-red-600 dark:text-red-400 flex-shrink-0 mt-0.5" />
                                <p className="text-sm text-red-700 dark:text-red-300 font-medium leading-relaxed">
                                    The user will lose access immediately and won't be able to deploy this plugin.
                                </p>
                            </div>
                        </div>

                        {/* Actions */}
                        <div className="relative flex gap-3">
                            <button
                                onClick={handleRevokeCancel}
                                disabled={revokingAccess === selectedRequest.id}
                                className="flex-1 px-5 py-3 border-2 border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-300 rounded-xl hover:bg-gray-50 dark:hover:bg-gray-800 transition-all duration-200 text-sm font-semibold disabled:opacity-50 hover:-translate-y-0.5"
                            >
                                Cancel
                            </button>
                            <button
                                onClick={handleRevokeConfirm}
                                disabled={revokingAccess === selectedRequest.id}
                                className="flex-1 px-5 py-3 bg-gradient-to-r from-red-600 to-rose-600 hover:from-red-500 hover:to-rose-500 text-white rounded-xl transition-all duration-200 text-sm font-semibold disabled:opacity-50 flex items-center justify-center gap-2 shadow-lg shadow-red-500/30 hover:shadow-xl hover:shadow-red-500/40 hover:-translate-y-0.5"
                            >
                                {revokingAccess === selectedRequest.id ? (
                                    <>
                                        <Loader className="w-4 h-4 animate-spin" />
                                        Revoking...
                                    </>
                                ) : (
                                    <>
                                        <UserX className="w-4 h-4" />
                                        Revoke Access
                                    </>
                                )}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};
