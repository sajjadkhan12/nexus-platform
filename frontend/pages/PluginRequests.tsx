import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, CheckCircle2, XCircle, Clock, Loader, Lock, ExternalLink, X } from 'lucide-react';
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
    const navigate = useNavigate();
    const { addNotification } = useNotification();
    const { isAdmin } = useAuth();
    const [requests, setRequests] = useState<AccessRequest[]>([]);
    const [filteredRequests, setFilteredRequests] = useState<AccessRequest[]>([]);
    const [grants, setGrants] = useState<AccessGrant[]>([]);
    const [filteredGrants, setFilteredGrants] = useState<AccessGrant[]>([]);
    const [loading, setLoading] = useState(true);
    const [searchEmail, setSearchEmail] = useState('');
    const [grantingAccess, setGrantingAccess] = useState<string | null>(null);
    const [revokingAccess, setRevokingAccess] = useState<string | null>(null);

    useEffect(() => {
        if (isAdmin) {
            loadRequests();
        }
    }, [isAdmin]);

    useEffect(() => {
        filterRequests();
        filterGrants();
    }, [searchEmail, requests, grants]);

    const loadRequests = async () => {
        try {
            setLoading(true);
            const [requestsData, grantsData] = await Promise.all([
                api.getAllAccessRequests(),
                api.getAllAccessGrants()
            ]);
            setRequests(requestsData);
            setGrants(grantsData);
        } catch (err: any) {
            addNotification('error', err.message || 'Failed to load access data');
        } finally {
            setLoading(false);
        }
    };

    const filterRequests = () => {
        if (!searchEmail.trim()) {
            setFilteredRequests(requests);
            return;
        }

        const filtered = requests.filter(req =>
            req.user_email.toLowerCase().includes(searchEmail.toLowerCase().trim())
        );
        setFilteredRequests(filtered);
    };

    const filterGrants = () => {
        if (!searchEmail.trim()) {
            setFilteredGrants(grants);
            return;
        }

        const filtered = grants.filter(grant =>
            grant.user_email.toLowerCase().includes(searchEmail.toLowerCase().trim())
        );
        setFilteredGrants(filtered);
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

    const handleRevokeAccess = async (grant: AccessGrant) => {
        if (!confirm(`Are you sure you want to revoke access from ${grant.user_email} for ${grant.plugin_name}? They will need to request access again.`)) {
            return;
        }

        try {
            setRevokingAccess(`${grant.plugin_id}-${grant.user_id}`);
            await api.revokeAccess(grant.plugin_id, grant.user_id);
            addNotification('success', `Access revoked from ${grant.user_email} for ${grant.plugin_name}`);
            await loadRequests();
        } catch (err: any) {
            addNotification('error', err.message || 'Failed to revoke access');
        } finally {
            setRevokingAccess(null);
        }
    };

    const getStatusBadge = (status: string) => {
        switch (status.toLowerCase()) {
            case 'pending':
                return (
                    <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400 border border-yellow-200 dark:border-yellow-800">
                        <Clock className="w-3 h-3" />
                        Pending
                    </span>
                );
            case 'approved':
                return (
                    <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400 border border-green-200 dark:border-green-800">
                        <CheckCircle2 className="w-3 h-3" />
                        Approved
                    </span>
                );
            case 'rejected':
                return (
                    <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400 border border-red-200 dark:border-red-800">
                        <XCircle className="w-3 h-3" />
                        Rejected
                    </span>
                );
            default:
                return <span className="text-xs text-gray-500">{status}</span>;
        }
    };

    const pendingRequests = filteredRequests.filter(r => r.status.toLowerCase() === 'pending');
    const otherRequests = filteredRequests.filter(r => r.status.toLowerCase() !== 'pending');

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
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Plugin Access Requests</h1>
                    <p className="text-gray-600 dark:text-gray-400 mt-1">
                        Manage and approve plugin access requests from users
                    </p>
                </div>
            </div>

            {/* Search Filter */}
            <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-4">
                <div className="relative">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                    <input
                        type="text"
                        placeholder="Filter by user email..."
                        value={searchEmail}
                        onChange={(e) => setSearchEmail(e.target.value)}
                        className="w-full pl-10 pr-4 py-2.5 bg-gray-50 dark:bg-gray-950 border border-gray-200 dark:border-gray-700 rounded-lg text-gray-900 dark:text-white placeholder-gray-500 focus:ring-2 focus:ring-orange-500/20 focus:border-orange-500 transition-all"
                    />
                </div>
            </div>

            {/* Loading State */}
            {loading ? (
                <div className="flex items-center justify-center py-12">
                    <Loader className="w-8 h-8 animate-spin text-orange-500" />
                </div>
            ) : (
                <>
                    {/* Pending Requests */}
                    {pendingRequests.length > 0 && (
                        <div className="space-y-4">
                            <h2 className="text-xl font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                                <Clock className="w-5 h-5 text-yellow-500" />
                                Pending Requests ({pendingRequests.length})
                            </h2>
                            <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 overflow-hidden">
                                <div className="overflow-x-auto">
                                    <table className="w-full">
                                        <thead className="bg-gray-50 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
                                            <tr>
                                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">User</th>
                                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Plugin</th>
                                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Requested</th>
                                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Status</th>
                                                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Actions</th>
                                            </tr>
                                        </thead>
                                        <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                                            {pendingRequests.map((request) => (
                                                <tr key={request.id} className="hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors">
                                                    <td className="px-6 py-4 whitespace-nowrap">
                                                        <div className="text-sm font-medium text-gray-900 dark:text-white">
                                                            {request.user_email}
                                                        </div>
                                                    </td>
                                                    <td className="px-6 py-4">
                                                        <div className="flex items-center gap-2">
                                                            <Lock className="w-4 h-4 text-gray-400" />
                                                            <span className="text-sm text-gray-900 dark:text-white">
                                                                {request.plugin_name || request.plugin_id}
                                                            </span>
                                                        </div>
                                                    </td>
                                                    <td className="px-6 py-4 whitespace-nowrap">
                                                        <div className="text-sm text-gray-500 dark:text-gray-400">
                                                            {new Date(request.requested_at).toLocaleString()}
                                                        </div>
                                                    </td>
                                                    <td className="px-6 py-4 whitespace-nowrap">
                                                        {getStatusBadge(request.status)}
                                                    </td>
                                                    <td className="px-6 py-4 whitespace-nowrap text-right">
                                                        <div className="flex items-center justify-end gap-2">
                                                            <button
                                                                onClick={() => navigate(`/provision/${request.plugin_id}`)}
                                                                className="p-2 text-gray-400 hover:text-orange-500 transition-colors"
                                                                title="View Plugin"
                                                            >
                                                                <ExternalLink className="w-4 h-4" />
                                                            </button>
                                                            <button
                                                                onClick={() => handleGrantAccess(request)}
                                                                disabled={grantingAccess === request.id}
                                                                className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg font-medium text-sm transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                                                            >
                                                                {grantingAccess === request.id ? (
                                                                    <>
                                                                        <Loader className="w-4 h-4 animate-spin" />
                                                                        Granting...
                                                                    </>
                                                                ) : (
                                                                    <>
                                                                        <CheckCircle2 className="w-4 h-4" />
                                                                        Grant Access
                                                                    </>
                                                                )}
                                                            </button>
                                                        </div>
                                                    </td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        </div>
                    )}

                    {/* Current Access Grants */}
                    {filteredGrants.length > 0 && (
                        <div className="space-y-4">
                            <h2 className="text-xl font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                                <CheckCircle2 className="w-5 h-5 text-green-500" />
                                Current Access ({filteredGrants.length})
                            </h2>
                            <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 overflow-hidden">
                                <div className="overflow-x-auto">
                                    <table className="w-full">
                                        <thead className="bg-gray-50 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
                                            <tr>
                                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">User</th>
                                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Plugin</th>
                                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Granted</th>
                                                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Actions</th>
                                            </tr>
                                        </thead>
                                        <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                                            {filteredGrants.map((grant) => (
                                                <tr key={`${grant.plugin_id}-${grant.user_id}`} className="hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors">
                                                    <td className="px-6 py-4 whitespace-nowrap">
                                                        <div className="text-sm font-medium text-gray-900 dark:text-white">
                                                            {grant.user_email}
                                                        </div>
                                                    </td>
                                                    <td className="px-6 py-4">
                                                        <div className="flex items-center gap-2">
                                                            <Lock className="w-4 h-4 text-gray-400" />
                                                            <span className="text-sm text-gray-900 dark:text-white">
                                                                {grant.plugin_name || grant.plugin_id}
                                                            </span>
                                                        </div>
                                                    </td>
                                                    <td className="px-6 py-4 whitespace-nowrap">
                                                        <div className="text-sm text-gray-500 dark:text-gray-400">
                                                            {new Date(grant.granted_at).toLocaleString()}
                                                        </div>
                                                    </td>
                                                    <td className="px-6 py-4 whitespace-nowrap text-right">
                                                        <div className="flex items-center justify-end gap-2">
                                                            <button
                                                                onClick={() => navigate(`/provision/${grant.plugin_id}`)}
                                                                className="p-2 text-gray-400 hover:text-orange-500 transition-colors"
                                                                title="View Plugin"
                                                            >
                                                                <ExternalLink className="w-4 h-4" />
                                                            </button>
                                                            <button
                                                                onClick={() => handleRevokeAccess(grant)}
                                                                disabled={revokingAccess === `${grant.plugin_id}-${grant.user_id}`}
                                                                className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg font-medium text-sm transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                                                            >
                                                                {revokingAccess === `${grant.plugin_id}-${grant.user_id}` ? (
                                                                    <>
                                                                        <Loader className="w-4 h-4 animate-spin" />
                                                                        Revoking...
                                                                    </>
                                                                ) : (
                                                                    <>
                                                                        <X className="w-4 h-4" />
                                                                        Revoke Access
                                                                    </>
                                                                )}
                                                            </button>
                                                        </div>
                                                    </td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        </div>
                    )}

                    {/* Other Requests (Approved/Rejected) */}
                    {otherRequests.length > 0 && (
                        <div className="space-y-4">
                            <h2 className="text-xl font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                                <CheckCircle2 className="w-5 h-5 text-gray-400" />
                                Processed Requests ({otherRequests.length})
                            </h2>
                            <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 overflow-hidden">
                                <div className="overflow-x-auto">
                                    <table className="w-full">
                                        <thead className="bg-gray-50 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
                                            <tr>
                                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">User</th>
                                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Plugin</th>
                                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Requested</th>
                                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Reviewed</th>
                                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Status</th>
                                            </tr>
                                        </thead>
                                        <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                                            {otherRequests.map((request) => (
                                                <tr key={request.id} className="hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors">
                                                    <td className="px-6 py-4 whitespace-nowrap">
                                                        <div className="text-sm font-medium text-gray-900 dark:text-white">
                                                            {request.user_email}
                                                        </div>
                                                    </td>
                                                    <td className="px-6 py-4">
                                                        <div className="flex items-center gap-2">
                                                            <Lock className="w-4 h-4 text-gray-400" />
                                                            <span className="text-sm text-gray-900 dark:text-white">
                                                                {request.plugin_name || request.plugin_id}
                                                            </span>
                                                        </div>
                                                    </td>
                                                    <td className="px-6 py-4 whitespace-nowrap">
                                                        <div className="text-sm text-gray-500 dark:text-gray-400">
                                                            {new Date(request.requested_at).toLocaleString()}
                                                        </div>
                                                    </td>
                                                    <td className="px-6 py-4 whitespace-nowrap">
                                                        <div className="text-sm text-gray-500 dark:text-gray-400">
                                                            {request.reviewed_at ? new Date(request.reviewed_at).toLocaleString() : '-'}
                                                        </div>
                                                    </td>
                                                    <td className="px-6 py-4 whitespace-nowrap">
                                                        {getStatusBadge(request.status)}
                                                    </td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        </div>
                    )}

                    {/* Empty State */}
                    {filteredRequests.length === 0 && filteredGrants.length === 0 && !loading && (
                        <div className="text-center py-12 bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800">
                            <Lock className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                            <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">No access data found</h3>
                            <p className="text-gray-500 dark:text-gray-400">
                                {searchEmail ? 'Try adjusting your search filter.' : 'No plugin access requests or grants found.'}
                            </p>
                        </div>
                    )}
                </>
            )}
        </div>
    );
};

