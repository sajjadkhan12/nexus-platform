import React, { useState, useEffect } from 'react';
import { Search, CheckCircle2, XCircle, Clock, Loader, MessageCircle } from 'lucide-react';
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

                                                {/* Status Badge for non-pending */}
                                                {!isPending && (
                                                    <div className="flex-shrink-0">
                                                        {request.status.toLowerCase() === 'approved' ? (
                                                            <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-medium bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400 border border-green-300 dark:border-green-800">
                                                                <CheckCircle2 className="w-3 h-3" />
                                                                Approved
                                                            </span>
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
        </div>
    );
};
