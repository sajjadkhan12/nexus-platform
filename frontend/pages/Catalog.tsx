import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Server, ExternalLink, Clock, Search, Filter, X, AlertCircle, Loader2 } from 'lucide-react';
import api from '../services/api';
import { StatusBadge, PluginBadge } from '../components/Badges';
import { CloudProviderBadge, RegionBadge, MetadataTag } from '../components/CloudTags';
import { EnvironmentBadge } from '../components/EnvironmentBadge';
import { appLogger } from '../utils/logger';
import { Pagination } from '../components/Pagination';
import { useAuth } from '../contexts/AuthContext';
import { BusinessUnitWarningModal } from '../components/BusinessUnitWarningModal';

import { Deployment } from '../types';

export const CatalogPage: React.FC = () => {
    const { user, activeBusinessUnit, hasBusinessUnitAccess, isAdmin, isLoadingBusinessUnits } = useAuth();
    const [showBusinessUnitWarning, setShowBusinessUnitWarning] = useState(false);
    const [deployments, setDeployments] = useState<Deployment[]>([]);
    const [filteredDeployments, setFilteredDeployments] = useState<Deployment[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [searchQuery, setSearchQuery] = useState('');
    const [statusFilter, setStatusFilter] = useState<string>('all');
    const [providerFilter, setProviderFilter] = useState<string>('all');
    const [environmentFilter, setEnvironmentFilter] = useState<string>('all');  // NEW
    const [tagFilters, setTagFilters] = useState<Record<string, string>>({});  // NEW
    const [showFilters, setShowFilters] = useState(false);
    const [currentPage, setCurrentPage] = useState(1);
    const [itemsPerPage, setItemsPerPage] = useState(50);
    const [totalItems, setTotalItems] = useState(0);

    const fetchDeployments = async (skipPolling = false) => {
        // Wait for business units to load before checking
        if (isLoadingBusinessUnits) {
            return;
        }
        
        // Check if business unit is selected (admins can bypass)
        const userIsAdmin = isAdmin || (user?.roles || []).some(role => role.toLowerCase() === 'admin');
        if (!userIsAdmin && (!activeBusinessUnit || !hasBusinessUnitAccess)) {
            setShowBusinessUnitWarning(true);
            setLoading(false);
            return;
        }

        // Show loading when switching business units (unless it's a polling call)
        if (!skipPolling) {
            setLoading(true);
        }

        try {
            const skip = (currentPage - 1) * itemsPerPage;
            const params: Record<string, string | number> = {
                skip,
                limit: itemsPerPage
            };
            if (searchQuery.trim()) params.search = searchQuery.trim();
            if (statusFilter !== 'all') params.status = statusFilter;
            if (providerFilter !== 'all') params.cloud_provider = providerFilter;
            if (environmentFilter !== 'all') params.environment = environmentFilter;  // NEW
            
            // Add tag filters (NEW)
            if (Object.keys(tagFilters).length > 0) {
                const tagPairs = Object.entries(tagFilters)
                    .filter(([k, v]) => k && v)
                    .map(([k, v]) => `${k}:${v}`);
                if (tagPairs.length > 0) {
                    params.tags = tagPairs.join(',');
                }
            }
            
            // IMPORTANT: Never send user_id from Catalog page - this is "Deployments" 
            // and should only show current user's deployments (filtered client-side for admins)
            // The backend will return all for admins, but we filter client-side to show only own
            
            const response = await api.listDeployments(params);
            
            // Handle both old format (array) and new format (object with items/total)
            let items: Deployment[] = [];
            if (Array.isArray(response)) {
                items = response;
            } else {
                items = response.items || [];
            }

            // Filter to show only current user's deployments (even for admins on "Deployments" page)
            if (user?.id) {
                const userId = String(user.id);
                items = items.filter((deploy: Deployment) => deploy.user_id && String(deploy.user_id) === userId);
            }

            setDeployments(items);
            setFilteredDeployments(items);
            setTotalItems(items.length);
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

    // Initial load and reload when business unit changes
    useEffect(() => {
        fetchDeployments();
    }, [activeBusinessUnit?.id]); // Reload when business unit changes

    // Poll for updates every 10 seconds (only when no active filters) - reduced frequency to avoid rate limits
    useEffect(() => {
        // Only poll when there are no active filters
        if (searchQuery.trim() || statusFilter !== 'all' || providerFilter !== 'all' || 
            environmentFilter !== 'all' || Object.keys(tagFilters).length > 0) {
            return; // Don't poll when filters are active
        }

        const interval = setInterval(() => {
            fetchDeployments(true);
        }, 10000); // Increased from 5s to 10s to reduce API calls
        
        return () => clearInterval(interval);
    }, [searchQuery, statusFilter, providerFilter, environmentFilter, tagFilters]); // Recreate interval when filters change

    // Clear filters function (NEW)
    const clearAllFilters = () => {
        setSearchQuery('');
        setStatusFilter('all');
        setProviderFilter('all');
        setEnvironmentFilter('all');
        setTagFilters({});
    };
    
    const hasActiveFilters = searchQuery.trim() || statusFilter !== 'all' || 
                            providerFilter !== 'all' || environmentFilter !== 'all' || 
                            Object.keys(tagFilters).length > 0;
    
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
                    <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Deployments</h1>
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
                    <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700 grid grid-cols-1 md:grid-cols-3 gap-4">
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
                        
                        {/* Environment Filter (NEW) */}
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
                                        
                                        {/* Tags display (NEW) */}
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
                    ))}
                </div>
            )}
            
            {/* Business Unit Warning Modal */}
            <BusinessUnitWarningModal
                isOpen={showBusinessUnitWarning}
                onClose={() => setShowBusinessUnitWarning(false)}
                onSelectBusinessUnit={() => {
                    const selector = document.querySelector('[data-business-unit-selector]');
                    if (selector) {
                        (selector as HTMLElement).click();
                    }
                }}
                action="view deployments"
            />
            
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