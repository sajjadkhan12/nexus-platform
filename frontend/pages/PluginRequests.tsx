import React, { useState, useEffect } from 'react';
import { Search, CheckCircle2, XCircle, Clock, Loader, MessageCircle, UserX, AlertTriangle } from 'lucide-react';
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
    const [statusFilter, setStatusFilter] = useState<'pending' | 'approved' | 'rejected' | 'all'>('pending');
    const [grantingAccess, setGrantingAccess] = useState<string | null>(null);
    const [rejectingAccess, setRejectingAccess] = useState<string | null>(null);
    const [revokingAccess, setRevokingAccess] = useState<string | null>(null);
    const [showRevokeModal, setShowRevokeModal] = useState(false);
    const [selectedRequest, setSelectedRequest] = useState<AccessRequest | null>(null);
    const [statusCounts, setStatusCounts] = useState({ pending: 0, approved: 0, rejected: 0 });

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
            // Use the API to reject the request (if endpoint exists) or just reload
            // For now, we'll need to add this endpoint or handle it differently
            // This is a placeholder - you may need to implement the reject endpoint
            addNotification('info', 'Reject functionality needs to be implemented in the backend API');
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
                rejected: allRequests.filter(r => r.status.toLowerCase() === 'rejected').length
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
                    <h1 className="text-4xl font-bold text-gray-900 dark:text-white mb-2">Plugin Access Requests</h1>
                    <p className="text-gray-600 dark:text-gray-400 text-lg">
                        Review and manage permission requests for restricted plugins.
                    </p>
                </div>
                
                {/* Status Filter Buttons */}
                <div className="flex items-center gap-3">
                    <button
                        onClick={() => setStatusFilter('pending')}
                        className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                            statusFilter === 'pending'
                                ? 'bg-orange-500 text-white'
                                : 'bg-gray-200 dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-300 dark:hover:bg-gray-700'
                        }`}
                    >
                        Pending {statusCounts.pending > 0 && <span className="ml-1">{statusCounts.pending}</span>}
                    </button>
                    <button
                        onClick={() => setStatusFilter('approved')}
                        className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                            statusFilter === 'approved'
                                ? 'bg-orange-500 text-white'
                                : 'bg-gray-200 dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-300 dark:hover:bg-gray-700'
                        }`}
                    >
                        Approved {statusCounts.approved > 0 && <span className="ml-1">{statusCounts.approved}</span>}
                    </button>
                    <button
                        onClick={() => setStatusFilter('rejected')}
                        className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                            statusFilter === 'rejected'
                                ? 'bg-orange-500 text-white'
                                : 'bg-gray-200 dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-300 dark:hover:bg-gray-700'
                        }`}
                    >
                        Rejected {statusCounts.rejected > 0 && <span className="ml-1">{statusCounts.rejected}</span>}
                    </button>
                </div>
            </div>

            {/* Search Bar */}
            <div className="relative">
                <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400 dark:text-gray-500" />
                <input
                    type="text"
                    placeholder="Search requests..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="w-full pl-12 pr-4 py-3 bg-white dark:bg-gray-900 border border-gray-300 dark:border-gray-700 rounded-lg text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:ring-2 focus:ring-orange-500 focus:border-orange-500 transition-all"
                />
            </div>

            {/* Loading State */}
            {loading ? (
                <div className="flex items-center justify-center py-12">
                    <Loader className="w-8 h-8 animate-spin text-orange-500" />
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
                                        className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6 flex items-start gap-4"
                                    >
                                        {/* User Avatar */}
                                        <div className="flex-shrink-0">
                                            <div className="w-12 h-12 rounded-full bg-gradient-to-br from-orange-500 to-pink-500 flex items-center justify-center text-white font-semibold text-sm">
                                                {userInitials}
                                            </div>
                                        </div>

                                        {/* Request Details */}
                                        <div className="flex-1 min-w-0">
                                            <div className="flex items-start justify-between gap-4">
                                                <div className="flex-1">
                                                    <div className="flex items-center gap-2 mb-1 flex-wrap">
                                                        <span className="font-bold text-gray-900 dark:text-white text-lg">{userName}</span>
                                                        <span className="text-gray-600 dark:text-gray-400">requested access to</span>
                                                        <span className="font-bold text-gray-900 dark:text-white">{request.plugin_name || request.plugin_id}</span>
                                                    </div>
                                                    
                                                    <div className="flex items-center gap-2 text-gray-600 dark:text-gray-400 text-sm mb-3">
                                                        <span>{request.user_email}</span>
                                                        <span>•</span>
                                                        <Clock className="w-4 h-4" />
                                                        <span>{formatDate(request.requested_at)}</span>
                                                    </div>

                                                    {/* Reason */}
                                                    {request.reason && (
                                                        <div className="flex items-start gap-2 text-gray-700 dark:text-gray-300 text-sm mb-2">
                                                            <MessageCircle className="w-4 h-4 mt-0.5 flex-shrink-0 text-gray-500 dark:text-gray-400" />
                                                            <span className="italic">"{request.reason}"</span>
                                                        </div>
                                                    )}
                                                </div>

                                                {/* Action Buttons */}
                                                {isPending && (
                                                    <div className="flex items-center gap-2 flex-shrink-0">
                                                        <button
                                                            onClick={() => handleGrantAccess(request)}
                                                            disabled={grantingAccess === request.id}
                                                            className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg font-medium text-sm transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
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
                                                            className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg font-medium text-sm transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
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

                                                {/* Status Badge and Revoke Button for non-pending */}
                                                {!isPending && (
                                                    <div className="flex items-center gap-2 flex-shrink-0">
                                                        {request.status.toLowerCase() === 'approved' ? (
                                                            <>
                                                                <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-medium bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400 border border-green-300 dark:border-green-800">
                                                                    <CheckCircle2 className="w-3 h-3" />
                                                                    Approved
                                                                </span>
                                                                <button
                                                                    onClick={() => handleRevokeClick(request)}
                                                                    disabled={revokingAccess === request.id}
                                                                    className="px-3 py-1 bg-red-600 hover:bg-red-700 text-white rounded-lg font-medium text-xs transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1"
                                                                    title="Revoke access"
                                                                >
                                                                    <UserX className="w-3 h-3" />
                                                                    Revoke
                                                                </button>
                                                            </>
                                                        ) : (
                                                            <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-medium bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400 border border-red-300 dark:border-red-800">
                                                                <XCircle className="w-3 h-3" />
                                                                Rejected
                                                            </span>
                                                        )}
                                                    </div>
                                                )}
                                            </div>
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    ) : (
                        <div className="text-center py-12 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
                            <p className="text-gray-600 dark:text-gray-400 text-lg">
                                {debouncedSearch || statusFilter !== 'all'
                                    ? 'No requests found matching your search or filters.'
                                    : 'No access requests found.'}
                            </p>
                        </div>
                    )}
                </>
            )}

            {/* Revoke Confirmation Modal */}
            {showRevokeModal && selectedRequest && (
                <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
                    <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-2xl p-6 max-w-md w-full shadow-2xl animate-in fade-in zoom-in duration-200">
                        {/* Warning Icon */}
                        <div className="flex items-start gap-4 mb-4">
                            <div className="w-12 h-12 rounded-full bg-red-500/10 flex items-center justify-center flex-shrink-0">
                                <AlertTriangle className="w-6 h-6 text-red-600 dark:text-red-400" />
                            </div>
                            <div className="flex-1">
                                <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-1">Revoke Plugin Access</h3>
                                <p className="text-sm text-gray-600 dark:text-gray-400">
                                    This action will immediately revoke access for this user.
                                </p>
                            </div>
                        </div>

                        {/* Details */}
                        <div className="bg-gray-50 dark:bg-gray-800/50 border border-gray-200 dark:border-gray-700 rounded-lg p-4 mb-4">
                            <div className="space-y-2 text-sm">
                                <div>
                                    <span className="text-gray-600 dark:text-gray-400">User: </span>
                                    <span className="font-semibold text-gray-900 dark:text-white">{getUserName(selectedRequest.user_email)}</span>
                                    <span className="text-gray-600 dark:text-gray-400"> ({selectedRequest.user_email})</span>
                                </div>
                                <div>
                                    <span className="text-gray-600 dark:text-gray-400">Plugin: </span>
                                    <span className="font-semibold text-gray-900 dark:text-white">{selectedRequest.plugin_name || selectedRequest.plugin_id}</span>
                                </div>
                            </div>
                        </div>

                        {/* Warning Message */}
                        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-3 mb-4">
                            <p className="text-sm text-red-600 dark:text-red-400 font-medium">
                                ⚠️ The user will lose access immediately and won't be able to deploy this plugin.
                            </p>
                        </div>

                        {/* Actions */}
                        <div className="flex gap-3">
                            <button
                                onClick={handleRevokeCancel}
                                disabled={revokingAccess === selectedRequest.id}
                                className="flex-1 px-4 py-2 border border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors text-sm font-medium disabled:opacity-50"
                            >
                                Cancel
                            </button>
                            <button
                                onClick={handleRevokeConfirm}
                                disabled={revokingAccess === selectedRequest.id}
                                className="flex-1 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-500 transition-colors text-sm font-medium disabled:opacity-50 flex items-center justify-center gap-2"
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
