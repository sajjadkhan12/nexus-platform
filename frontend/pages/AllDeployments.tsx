import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Server, ExternalLink, Clock, Search, Filter, X, AlertCircle, Loader2, User, Calendar } from 'lucide-react';
import api from '../services/api';
import { StatusBadge, PluginBadge } from '../components/Badges';
import { CloudProviderBadge, RegionBadge, MetadataTag } from '../components/CloudTags';
import { EnvironmentBadge } from '../components/EnvironmentBadge';
import { appLogger } from '../utils/logger';
import { Pagination } from '../components/Pagination';
import { useAuth } from '../contexts/AuthContext';

import { Deployment } from '../types';

interface User {
    id: string;
    email: string;
    username: string;
    full_name?: string;
}

export const AllDeploymentsPage: React.FC = () => {
    const { isAdmin } = useAuth();
    const [deployments, setDeployments] = useState<Deployment[]>([]);
    const [filteredDeployments, setFilteredDeployments] = useState<Deployment[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [searchQuery, setSearchQuery] = useState('');
    const [statusFilter, setStatusFilter] = useState<string>('all');
    const [providerFilter, setProviderFilter] = useState<string>('all');
    const [environmentFilter, setEnvironmentFilter] = useState<string>('all');
    const [userFilter, setUserFilter] = useState<string>('all');
    const [dateFromFilter, setDateFromFilter] = useState<string>('');
    const [dateToFilter, setDateToFilter] = useState<string>('');
    const [tagFilters, setTagFilters] = useState<Record<string, string>>({});
    const [showFilters, setShowFilters] = useState(false);
    const [currentPage, setCurrentPage] = useState(1);
    const [itemsPerPage, setItemsPerPage] = useState(50);
    const [totalItems, setTotalItems] = useState(0);
    const [users, setUsers] = useState<User[]>([]);
    const [loadingUsers, setLoadingUsers] = useState(false);

    // Fetch users for filter dropdown
    useEffect(() => {
        if (isAdmin) {
            fetchUsers();
        }
    }, [isAdmin]);

    const fetchUsers = async () => {
        try {
            setLoadingUsers(true);
            const usersList = await api.usersApi.listUsers({ limit: 1000 });
            setUsers(Array.isArray(usersList) ? usersList : (usersList?.items || []));
        } catch (err: any) {
            appLogger.error('Failed to fetch users:', err);
        } finally {
            setLoadingUsers(false);
        }
    };

    const fetchDeployments = async (skipPolling = false) => {
        try {
            const skip = (currentPage - 1) * itemsPerPage;
            const params: Record<string, string | number> = {
                skip,
                limit: itemsPerPage
            };
            if (searchQuery.trim()) params.search = searchQuery.trim();
            if (statusFilter !== 'all') params.status = statusFilter;
            if (providerFilter !== 'all') params.cloud_provider = providerFilter;
            if (environmentFilter !== 'all') params.environment = environmentFilter;
            // Only send user_id if explicitly filtering by a specific user (and user is admin)
            if (userFilter !== 'all' && userFilter && isAdmin) {
                params.user_id = userFilter;
            }
            
            // Add tag filters
            if (Object.keys(tagFilters).length > 0) {
                const tagPairs = Object.entries(tagFilters)
                    .filter(([k, v]) => k && v)
                    .map(([k, v]) => `${k}:${v}`);
                if (tagPairs.length > 0) {
                    params.tags = tagPairs.join(',');
                }
            }
            
            const response = await api.listDeployments(params);
            
            // Handle both old format (array) and new format (object with items/total)
            let items: Deployment[] = [];
            if (Array.isArray(response)) {
                items = response;
                setTotalItems(response.length);
            } else {
                items = response.items || [];
                setTotalItems(response.total || 0);
            }

            // Apply date filters on client side (since backend doesn't support date range yet)
            let filtered = items;
            if (dateFromFilter) {
                const fromDate = new Date(dateFromFilter);
                filtered = filtered.filter(d => new Date(d.created_at) >= fromDate);
            }
            if (dateToFilter) {
                const toDate = new Date(dateToFilter);
                toDate.setHours(23, 59, 59, 999); // End of day
                filtered = filtered.filter(d => new Date(d.created_at) <= toDate);
            }

            setDeployments(filtered);
            setFilteredDeployments(filtered);
            
            // Update total items after date filtering
            if (dateFromFilter || dateToFilter) {
                setTotalItems(filtered.length);
            }
        } catch (err: any) {
            appLogger.error('Failed to fetch deployments:', err);
            if (loading && !skipPolling) {
                setError(err.message || 'Failed to load deployments');
            }
        } finally {
            setLoading(false);
        }
    };

    // Initial load
    useEffect(() => {
        if (isAdmin) {
            fetchDeployments();
        }
    }, [isAdmin]);

    // Fetch when pagination or filters change
    useEffect(() => {
        if (isAdmin) {
            setCurrentPage(1); // Reset to first page when filters change
            fetchDeployments();
        }
    }, [searchQuery, statusFilter, providerFilter, environmentFilter, userFilter, tagFilters]);

    // Fetch when pagination changes
    useEffect(() => {
        if (isAdmin) {
            fetchDeployments();
        }
    }, [currentPage, itemsPerPage]);

    // Clear filters function
    const clearAllFilters = () => {
        setSearchQuery('');
        setStatusFilter('all');
        setProviderFilter('all');
        setEnvironmentFilter('all');
        setUserFilter('all');
        setDateFromFilter('');
        setDateToFilter('');
        setTagFilters({});
    };
    
    const hasActiveFilters = searchQuery.trim() || statusFilter !== 'all' || 
                            providerFilter !== 'all' || environmentFilter !== 'all' || 
                            userFilter !== 'all' || dateFromFilter || dateToFilter ||
                            Object.keys(tagFilters).length > 0;

    // Redirect if not admin
    if (!isAdmin) {
        return (
            <div className="flex items-center justify-center h-64">
                <div className="text-center">
                    <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
                    <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-2">Access Denied</h2>
                    <p className="text-gray-500 dark:text-gray-400">This page is only available to administrators.</p>
                    <Link to="/deployments" className="text-orange-600 dark:text-orange-400 hover:underline mt-4 inline-block">
                        Go to Deployments
                    </Link>
                </div>
            </div>
        );
    }

    if (loading && deployments.length === 0) {
        return (
            <div className="flex items-center justify-center h-64">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-orange-600"></div>
            </div>
        );
    }

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold text-gray-900 dark:text-white">All Deployments</h1>
                    <p className="text-gray-500 dark:text-gray-400 mt-1">View and manage all deployments across all users.</p>
                </div>
                <div className="flex gap-2">
                    <Link to="/deployments" className="bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 px-4 py-2 rounded-lg text-sm font-medium hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors">
                        Deployments
                    </Link>
                    <Link to="/services" className="bg-orange-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-orange-500 transition-colors shadow-md shadow-orange-500/20">
                        New Deployment
                    </Link>
                </div>
            </div>

            {/* Search and Filters */}
            <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-lg p-4">
                <div className="flex flex-col md:flex-row gap-4">
                    {/* Search Bar */}
                    <div className="flex-1 relative">
                        <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
                        <input
                            type="text"
                            placeholder="Search by name, plugin, stack, or region..."
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            className="w-full pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-transparent"
                        />
                        {searchQuery && (
                            <button
                                onClick={() => {
                                    setSearchQuery('');
                                    fetchDeployments();
                                }}
                                className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                            >
                                <X className="w-4 h-4" />
                            </button>
                        )}
                    </div>

                    {/* Filter Toggle */}
                    <button
                        onClick={() => setShowFilters(!showFilters)}
                        className="flex items-center gap-2 px-4 py-2 border border-gray-300 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
                    >
                        <Filter className="w-4 h-4" />
                        Filters
                        {hasActiveFilters && (
                            <span className="bg-orange-600 text-white text-xs px-2 py-0.5 rounded-full">
                                {[
                                    searchQuery && '1', 
                                    statusFilter !== 'all' && '1', 
                                    providerFilter !== 'all' && '1',
                                    environmentFilter !== 'all' && '1',
                                    userFilter !== 'all' && '1',
                                    (dateFromFilter || dateToFilter) && '1'
                                ].filter(Boolean).length}
                            </span>
                        )}
                    </button>
                </div>

                {/* Filter Options */}
                {showFilters && (
                    <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                        {/* Status Filter */}
                        <div>
                            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                                Status
                            </label>
                            <select
                                value={statusFilter}
                                onChange={(e) => {
                                    setStatusFilter(e.target.value);
                                    fetchDeployments();
                                }}
                                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-orange-500"
                            >
                                <option value="all">All Statuses</option>
                                <option value="active">Active</option>
                                <option value="provisioning">Provisioning</option>
                                <option value="failed">Failed</option>
                                <option value="deleted">Deleted</option>
                            </select>
                        </div>

                        {/* Cloud Provider Filter */}
                        <div>
                            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                                Cloud Provider
                            </label>
                            <select
                                value={providerFilter}
                                onChange={(e) => {
                                    setProviderFilter(e.target.value);
                                    fetchDeployments();
                                }}
                                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-orange-500"
                            >
                                <option value="all">All Providers</option>
                                <option value="aws">AWS</option>
                                <option value="gcp">GCP</option>
                                <option value="azure">Azure</option>
                            </select>
                        </div>
                        
                        {/* Environment Filter */}
                        <div>
                            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                                Environment
                            </label>
                            <select
                                value={environmentFilter}
                                onChange={(e) => {
                                    setEnvironmentFilter(e.target.value);
                                    fetchDeployments();
                                }}
                                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-orange-500"
                            >
                                <option value="all">All Environments</option>
                                <option value="development">Development</option>
                                <option value="staging">Staging</option>
                                <option value="production">Production</option>
                            </select>
                        </div>

                        {/* User Filter */}
                        <div>
                            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                                <User className="w-4 h-4 inline mr-1" />
                                User
                            </label>
                            <select
                                value={userFilter}
                                onChange={(e) => {
                                    setUserFilter(e.target.value);
                                    fetchDeployments();
                                }}
                                disabled={loadingUsers}
                                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-orange-500 disabled:opacity-50"
                            >
                                <option value="all">All Users</option>
                                {users.map((user) => (
                                    <option key={user.id} value={user.id}>
                                        {user.full_name || user.username || user.email}
                                    </option>
                                ))}
                            </select>
                        </div>

                        {/* Date From Filter */}
                        <div>
                            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                                <Calendar className="w-4 h-4 inline mr-1" />
                                Created From
                            </label>
                            <input
                                type="date"
                                value={dateFromFilter}
                                onChange={(e) => {
                                    setDateFromFilter(e.target.value);
                                    fetchDeployments();
                                }}
                                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-orange-500"
                            />
                        </div>

                        {/* Date To Filter */}
                        <div>
                            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                                <Calendar className="w-4 h-4 inline mr-1" />
                                Created To
                            </label>
                            <input
                                type="date"
                                value={dateToFilter}
                                onChange={(e) => {
                                    setDateToFilter(e.target.value);
                                    fetchDeployments();
                                }}
                                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-orange-500"
                            />
                        </div>
                    </div>
                )}

                {/* Clear Filters */}
                {hasActiveFilters && (
                    <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
                        <button
                            onClick={clearAllFilters}
                            className="text-sm text-orange-600 dark:text-orange-400 hover:text-orange-700 dark:hover:text-orange-300 flex items-center gap-1"
                        >
                            <X className="w-4 h-4" />
                            Clear all filters
                        </button>
                    </div>
                )}
            </div>

            {error && (
                <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-600 dark:text-red-400 px-4 py-3 rounded-lg">
                    {error}
                </div>
            )}

            {/* Results Count */}
            {!loading && hasActiveFilters && (
                <div className="text-sm text-gray-500 dark:text-gray-400">
                    {filteredDeployments.length === 0 ? (
                        <span>No deployments match your filters. <button onClick={clearAllFilters} className="text-orange-600 dark:text-orange-400 hover:underline">Clear filters</button></span>
                    ) : (
                        <span>Found {filteredDeployments.length} deployment{filteredDeployments.length !== 1 ? 's' : ''}</span>
                    )}
                </div>
            )}

            {filteredDeployments.length === 0 && !loading ? (
                <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-2xl p-12 text-center transition-colors">
                    <div className="w-16 h-16 bg-gray-100 dark:bg-gray-800 rounded-full flex items-center justify-center mx-auto mb-4">
                        <Server className="w-8 h-8 text-gray-400 dark:text-gray-500" />
                    </div>
                    <h3 className="text-xl font-medium text-gray-900 dark:text-white mb-2">No Deployments Found</h3>
                    <p className="text-gray-500 dark:text-gray-400 mb-6 max-w-md mx-auto">
                        {hasActiveFilters 
                            ? "No deployments match your current filters. Try adjusting your search criteria."
                            : "No deployments have been created yet."}
                    </p>
                    {hasActiveFilters ? (
                        <button
                            onClick={clearAllFilters}
                            className="text-orange-600 dark:text-orange-400 hover:text-orange-500 dark:hover:text-orange-300 font-medium"
                        >
                            Clear Filters &rarr;
                        </button>
                    ) : (
                        <Link to="/services" className="text-orange-600 dark:text-orange-400 hover:text-orange-500 dark:hover:text-orange-300 font-medium">
                            Browse Catalog &rarr;
                        </Link>
                    )}
                </div>
            ) : (
                <div className="space-y-3">
                    {filteredDeployments.map((deploy) => {
                        // Find user info for this deployment
                        const deployUser = users.find(u => u.id === deploy.user_id);
                        const userName = deployUser ? (deployUser.full_name || deployUser.username || deployUser.email) : 'Unknown User';
                        
                        return (
                            <Link
                                key={deploy.id}
                                to={`/deployment/${deploy.id}`}
                                className="block bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-lg p-4 hover:border-orange-500/30 dark:hover:border-gray-600 transition-all hover:shadow-lg hover:shadow-orange-500/10 group"
                            >
                                <div className="flex items-center justify-between gap-4">
                                    <div className="flex items-center gap-3 flex-1 min-w-0">
                                        <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-orange-500 to-orange-600 flex items-center justify-center flex-shrink-0 shadow-lg shadow-orange-500/30">
                                            <Server className="w-5 h-5 text-white" />
                                        </div>
                                        <div className="flex-1 min-w-0">
                                            <div className="flex items-center gap-2 mb-1">
                                                <h3 className="text-base font-bold text-gray-900 dark:text-white group-hover:text-orange-600 dark:group-hover:text-orange-400 transition-colors truncate">{deploy.name}</h3>
                                                {deploy.environment && (
                                                    <EnvironmentBadge environment={deploy.environment} size="sm" />
                                                )}
                                                <PluginBadge pluginId={deploy.plugin_id} provider={deploy.cloud_provider} />
                                                {deploy.version && (
                                                    <span className="text-xs text-gray-500 dark:text-gray-400">v{deploy.version}</span>
                                                )}
                                                {deploy.update_status === 'update_failed' && (
                                                    <div className="relative group">
                                                        <AlertCircle className="w-4 h-4 text-yellow-500" />
                                                        {deploy.last_update_error && (
                                                            <div className="absolute left-0 top-full mt-2 w-64 p-2 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg text-xs text-yellow-800 dark:text-yellow-200 opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity z-10">
                                                                Update failed: {deploy.last_update_error}
                                                            </div>
                                                        )}
                                                    </div>
                                                )}
                                                {deploy.update_status === 'updating' && (
                                                    <Loader2 className="w-4 h-4 text-blue-500 animate-spin" />
                                                )}
                                            </div>
                                            <div className="flex items-center gap-2 flex-wrap">
                                                {/* User Badge */}
                                                <div className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-800">
                                                    <User className="w-3 h-3" />
                                                    <span className="font-medium">{userName}</span>
                                                </div>
                                                {deploy.cloud_provider && (
                                                    <CloudProviderBadge provider={deploy.cloud_provider} size="sm" />
                                                )}
                                                <RegionBadge region={deploy.region || 'unknown'} size="sm" />
                                                <MetadataTag 
                                                    icon={<Clock className="w-3.5 h-3.5" />}
                                                    label="Created"
                                                    value={new Date(deploy.created_at).toLocaleDateString()}
                                                    size="sm"
                                                />
                                                {deploy.outputs && Object.keys(deploy.outputs).length > 0 && (
                                                    <MetadataTag 
                                                        icon={<Server className="w-3.5 h-3.5" />}
                                                        label="Outputs"
                                                        value={`${Object.keys(deploy.outputs).length} output${Object.keys(deploy.outputs).length !== 1 ? 's' : ''}`}
                                                        size="sm"
                                                    />
                                                )}
                                            </div>
                                            
                                            {/* Tags display */}
                                            {deploy.tags && deploy.tags.length > 0 && (
                                                <div className="flex flex-wrap gap-1.5 mt-2">
                                                    {deploy.tags.slice(0, 3).map((tag: any) => (
                                                        <span
                                                            key={tag.key}
                                                            className="inline-flex items-center px-2 py-0.5 rounded text-xs bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 border border-gray-200 dark:border-gray-700"
                                                        >
                                                            <span className="font-medium">{tag.key}:</span>
                                                            <span className="ml-1">{tag.value}</span>
                                                        </span>
                                                    ))}
                                                    {deploy.tags.length > 3 && (
                                                        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs bg-gray-100 dark:bg-gray-800 text-gray-500 dark:text-gray-400">
                                                            +{deploy.tags.length - 3} more
                                                        </span>
                                                    )}
                                                </div>
                                            )}
                                        </div>
                                    </div>

                                    <div className="flex items-center gap-3 flex-shrink-0">
                                        <StatusBadge status={deploy.status} />
                                        <ExternalLink className="w-4 h-4 text-gray-400 group-hover:text-orange-600 dark:group-hover:text-orange-400 transition-colors" />
                                    </div>
                                </div>
                            </Link>
                        );
                    })}
                </div>
            )}
            
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
        </div>
    );
};

