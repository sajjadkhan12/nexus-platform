import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Server, ExternalLink, Clock, Search, Filter, X } from 'lucide-react';
import api from '../services/api';
import { StatusBadge, PluginBadge } from '../components/Badges';
import { CloudProviderBadge, RegionBadge, MetadataTag } from '../components/CloudTags';
import { appLogger } from '../utils/logger';
import { Pagination } from '../components/Pagination';

import { Deployment } from '../types';

export const CatalogPage: React.FC = () => {
    const [deployments, setDeployments] = useState<Deployment[]>([]);
    const [filteredDeployments, setFilteredDeployments] = useState<Deployment[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [searchQuery, setSearchQuery] = useState('');
    const [statusFilter, setStatusFilter] = useState<string>('all');
    const [providerFilter, setProviderFilter] = useState<string>('all');
    const [showFilters, setShowFilters] = useState(false);
    const [currentPage, setCurrentPage] = useState(1);
    const [itemsPerPage, setItemsPerPage] = useState(50);
    const [totalItems, setTotalItems] = useState(0);

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
            
            const response = await api.listDeployments(params);
            
            // Handle both old format (array) and new format (object with items/total)
            if (Array.isArray(response)) {
                setDeployments(response);
                setFilteredDeployments(response);
                setTotalItems(response.length);
            } else {
                const items = response.items || [];
                setDeployments(items);
                setFilteredDeployments(items);
                setTotalItems(response.total || 0);
            }
        } catch (err: any) {
            appLogger.error('Failed to fetch deployments:', err);
            // Don't show error on polling to avoid annoying UI
            if (loading && !skipPolling) {
                setError(err.message || 'Failed to load deployments');
            }
        } finally {
            setLoading(false);
        }
    };

    // Initial load
    useEffect(() => {
        fetchDeployments();

        // Poll for updates every 10 seconds (only when no active filters) - reduced frequency to avoid rate limits
        const interval = setInterval(() => {
            if (!searchQuery.trim() && statusFilter === 'all' && providerFilter === 'all') {
                fetchDeployments(true);
            }
        }, 10000); // Increased from 5s to 10s to reduce API calls
        return () => clearInterval(interval);
    }, []);

    // Debounce search and filter changes
    useEffect(() => {
        const timeoutId = setTimeout(() => {
            setCurrentPage(1); // Reset to first page when filters change
            fetchDeployments();
        }, 500);

        return () => clearTimeout(timeoutId);
    }, [searchQuery, statusFilter, providerFilter]);

    // Fetch when pagination changes
    useEffect(() => {
        fetchDeployments();
    }, [currentPage, itemsPerPage]);

    const clearFilters = () => {
        setSearchQuery('');
        setStatusFilter('all');
        setProviderFilter('all');
        fetchDeployments();
    };

    const hasActiveFilters = searchQuery.trim() || statusFilter !== 'all' || providerFilter !== 'all';

    if (loading) {
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
                    <h1 className="text-3xl font-bold text-gray-900 dark:text-white">My Deployments</h1>
                    <p className="text-gray-500 dark:text-gray-400 mt-1">Manage and monitor your active infrastructure.</p>
                </div>
                <Link to="/services" className="bg-orange-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-orange-500 transition-colors shadow-md shadow-orange-500/20">
                    New Deployment
                </Link>
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
                                {[searchQuery && '1', statusFilter !== 'all' && '1', providerFilter !== 'all' && '1'].filter(Boolean).length}
                            </span>
                        )}
                    </button>
                </div>

                {/* Filter Options */}
                {showFilters && (
                    <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700 grid grid-cols-1 md:grid-cols-2 gap-4">
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
                    </div>
                )}

                {/* Clear Filters */}
                {hasActiveFilters && (
                    <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
                        <button
                            onClick={clearFilters}
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
                        <span>No deployments match your filters. <button onClick={clearFilters} className="text-orange-600 dark:text-orange-400 hover:underline">Clear filters</button></span>
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
                    <h3 className="text-xl font-medium text-gray-900 dark:text-white mb-2">No Active Deployments</h3>
                    <p className="text-gray-500 dark:text-gray-400 mb-6 max-w-md mx-auto">You haven't deployed any services yet. Visit the service catalog to get started with your first deployment.</p>
                    <Link to="/services" className="text-orange-600 dark:text-orange-400 hover:text-orange-500 dark:hover:text-orange-300 font-medium">Browse Catalog &rarr;</Link>
                </div>
            ) : (
                <div className="space-y-3">
                    {filteredDeployments.map((deploy) => (
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
                                            <PluginBadge pluginId={deploy.plugin_id} provider={deploy.cloud_provider} />
                                            {deploy.version && (
                                                <span className="text-xs text-gray-500 dark:text-gray-400">v{deploy.version}</span>
                                            )}
                                        </div>
                                        <div className="flex items-center gap-2 flex-wrap">
                                            {deploy.cloud_provider && (
                                                <CloudProviderBadge provider={deploy.cloud_provider} size="sm" />
                                            )}
                                            <RegionBadge region={deploy.region || 'unknown'} size="sm" />
                                            <MetadataTag 
                                                icon={<Clock className="w-3.5 h-3.5" />}
                                                label="Created"
                                                value={new Date(deploy.created_at).toLocaleDateString()}
                                                size="sm"
                                                color="blue"
                                            />
                                            {deploy.outputs && Object.keys(deploy.outputs).length > 0 && (
                                                <MetadataTag 
                                                    icon={<Server className="w-3.5 h-3.5" />}
                                                    label="Outputs"
                                                    value={`${Object.keys(deploy.outputs).length} output${Object.keys(deploy.outputs).length !== 1 ? 's' : ''}`}
                                                    size="sm"
                                                    color="teal"
                                                />
                                            )}
                                        </div>
                                    </div>
                                </div>

                                <div className="flex items-center gap-3 flex-shrink-0">
                                    <StatusBadge status={deploy.status} />
                                    <ExternalLink className="w-4 h-4 text-gray-400 group-hover:text-orange-600 dark:group-hover:text-orange-400 transition-colors" />
                                </div>
                            </div>
                        </Link>
                    ))}
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