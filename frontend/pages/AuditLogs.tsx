import React, { useState, useEffect } from 'react';
import { Search, Filter, X, ChevronDown, ChevronUp, Calendar, User, Activity, FileText, Globe, CheckCircle2, XCircle, Eye } from 'lucide-react';
import { auditApi, AuditLog } from '../services/api/audit';
import { appLogger } from '../utils/logger';
import { Pagination } from '../components/Pagination';

export const AuditLogsPage: React.FC = () => {
    const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);
    const [loading, setLoading] = useState(true);
    const [searchQuery, setSearchQuery] = useState('');
    const [userFilter, setUserFilter] = useState('');
    const [actionFilter, setActionFilter] = useState('');
    const [resourceTypeFilter, setResourceTypeFilter] = useState('');
    const [statusFilter, setStatusFilter] = useState('');
    const [startDate, setStartDate] = useState('');
    const [endDate, setEndDate] = useState('');
    const [showFilters, setShowFilters] = useState(false);
    const [expandedLogs, setExpandedLogs] = useState<Set<string>>(new Set());
    const [selectedLog, setSelectedLog] = useState<AuditLog | null>(null);
    const [showDetailsModal, setShowDetailsModal] = useState(false);
    
    const [debouncedSearch, setDebouncedSearch] = useState('');
    const [currentPage, setCurrentPage] = useState(1);
    const [itemsPerPage, setItemsPerPage] = useState(50);
    const [totalItems, setTotalItems] = useState(0);

    // Debounce search query
    useEffect(() => {
        const timer = setTimeout(() => {
            setDebouncedSearch(searchQuery);
        }, 300);
        return () => clearTimeout(timer);
    }, [searchQuery]);

    useEffect(() => {
        loadAuditLogs();
    }, [debouncedSearch, userFilter, actionFilter, resourceTypeFilter, statusFilter, startDate, endDate, currentPage, itemsPerPage]);

    const loadAuditLogs = async () => {
        try {
            setLoading(true);
            const skip = (currentPage - 1) * itemsPerPage;
            const response = await auditApi.listAuditLogs({
                skip,
                limit: itemsPerPage,
                search: debouncedSearch || undefined,
                user_id: userFilter || undefined,
                action: actionFilter || undefined,
                resource_type: resourceTypeFilter || undefined,
                status: statusFilter as 'success' | 'failure' | undefined,
                start_date: startDate || undefined,
                end_date: endDate || undefined,
            });
            
            setAuditLogs(response.items || []);
            setTotalItems(response.total || 0);
        } catch (err) {
            appLogger.error('Failed to load audit logs:', err);
        } finally {
            setLoading(false);
        }
    };

    const clearFilters = () => {
        setSearchQuery('');
        setUserFilter('');
        setActionFilter('');
        setResourceTypeFilter('');
        setStatusFilter('');
        setStartDate('');
        setEndDate('');
        setCurrentPage(1);
    };

    const hasActiveFilters = searchQuery || userFilter || actionFilter || resourceTypeFilter || statusFilter || startDate || endDate;

    const handlePageChange = (page: number) => {
        setCurrentPage(page);
        window.scrollTo({ top: 0, behavior: 'smooth' });
    };

    const handleItemsPerPageChange = (newItemsPerPage: number) => {
        setItemsPerPage(newItemsPerPage);
        setCurrentPage(1);
    };

    const toggleExpand = (logId: string) => {
        setExpandedLogs(prev => {
            const newSet = new Set(prev);
            if (newSet.has(logId)) {
                newSet.delete(logId);
            } else {
                newSet.add(logId);
            }
            return newSet;
        });
    };

    const openDetailsModal = (log: AuditLog) => {
        setSelectedLog(log);
        setShowDetailsModal(true);
    };

    const formatDate = (dateString: string) => {
        return new Date(dateString).toLocaleString();
    };

    const getActionColor = (action: string) => {
        const colors: Record<string, string> = {
            create: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
            update: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
            delete: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
            password_change: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
            avatar_upload: 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200',
        };
        return colors[action] || 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-200';
    };

    // Get unique values for filters
    const uniqueActions = Array.from(new Set(auditLogs.map(log => log.action))).sort();
    const uniqueResourceTypes = Array.from(new Set(auditLogs.map(log => log.resource_type).filter(Boolean))).sort();

    return (
        <div className="p-3 sm:p-4 md:p-6 max-w-7xl mx-auto">
            <div className="mb-4 sm:mb-6">
                <h1 className="text-2xl sm:text-3xl font-bold text-gray-900 dark:text-white mb-2">Audit Logs</h1>
                <p className="text-sm sm:text-base text-gray-600 dark:text-gray-400">
                    View and search all system activity and changes
                </p>
            </div>

            {/* Search and Filter Bar */}
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-3 sm:p-4 mb-4 sm:mb-6">
                <div className="flex flex-col sm:flex-row gap-3 sm:gap-4">
                    <div className="flex-1 relative">
                        <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4 sm:w-5 sm:h-5" />
                        <input
                            type="text"
                            placeholder="Search audit logs..."
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            className="w-full pl-9 sm:pl-10 pr-4 py-2 text-sm sm:text-base border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                        />
                    </div>
                    <div className="flex gap-2">
                        <button
                            onClick={() => setShowFilters(!showFilters)}
                            className={`flex-1 sm:flex-none px-3 sm:px-4 py-2 rounded-lg border flex items-center justify-center gap-2 text-sm transition-colors ${
                                showFilters || hasActiveFilters
                                    ? 'bg-blue-50 border-blue-300 text-blue-700 dark:bg-blue-900 dark:border-blue-700 dark:text-blue-200'
                                    : 'bg-white border-gray-300 text-gray-700 dark:bg-gray-700 dark:border-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-600'
                            }`}
                        >
                            <Filter className="w-4 h-4" />
                            <span className="hidden sm:inline">Filters</span>
                            {hasActiveFilters && (
                                <span className="bg-blue-500 text-white text-xs rounded-full px-2 py-0.5">
                                    {hasActiveFilters ? '•' : 'Active'}
                                </span>
                            )}
                        </button>
                        {hasActiveFilters && (
                            <button
                                onClick={clearFilters}
                                className="flex-1 sm:flex-none px-3 sm:px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 flex items-center justify-center gap-2 text-sm"
                            >
                                <X className="w-4 h-4" />
                                <span className="hidden sm:inline">Clear</span>
                            </button>
                        )}
                    </div>
                </div>

                {/* Advanced Filters */}
                {showFilters && (
                    <div className="mt-3 sm:mt-4 pt-3 sm:pt-4 border-t border-gray-200 dark:border-gray-700 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-3 sm:gap-4">
                        <div>
                            <label className="block text-xs sm:text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                                Action
                            </label>
                            <select
                                value={actionFilter}
                                onChange={(e) => setActionFilter(e.target.value)}
                                className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                            >
                                <option value="">All Actions</option>
                                {uniqueActions.map(action => (
                                    <option key={action} value={action}>{action}</option>
                                ))}
                            </select>
                        </div>
                        <div>
                            <label className="block text-xs sm:text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                                Resource Type
                            </label>
                            <select
                                value={resourceTypeFilter}
                                onChange={(e) => setResourceTypeFilter(e.target.value)}
                                className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                            >
                                <option value="">All Resources</option>
                                {uniqueResourceTypes.map(type => (
                                    <option key={type} value={type}>{type}</option>
                                ))}
                            </select>
                        </div>
                        <div>
                            <label className="block text-xs sm:text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                                Status
                            </label>
                            <select
                                value={statusFilter}
                                onChange={(e) => setStatusFilter(e.target.value)}
                                className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                            >
                                <option value="">All Status</option>
                                <option value="success">Success</option>
                                <option value="failure">Failure</option>
                            </select>
                        </div>
                        <div>
                            <label className="block text-xs sm:text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                                Start Date
                            </label>
                            <input
                                type="datetime-local"
                                value={startDate}
                                onChange={(e) => setStartDate(e.target.value)}
                                className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                            />
                        </div>
                        <div>
                            <label className="block text-xs sm:text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                                End Date
                            </label>
                            <input
                                type="datetime-local"
                                value={endDate}
                                onChange={(e) => setEndDate(e.target.value)}
                                className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                            />
                        </div>
                    </div>
                )}
            </div>

            {/* Audit Logs - Responsive Layout */}
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 overflow-hidden">
                {loading ? (
                    <div className="p-6 sm:p-8 text-center text-gray-500 dark:text-gray-400">
                        Loading audit logs...
                    </div>
                ) : auditLogs.length === 0 ? (
                    <div className="p-6 sm:p-8 text-center text-gray-500 dark:text-gray-400">
                        No audit logs found
                    </div>
                ) : (
                    <>
                        {/* Desktop Table View */}
                        <div className="hidden lg:block overflow-x-auto">
                            <table className="w-full">
                                <thead className="bg-gray-50 dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700">
                                    <tr>
                                        <th className="px-4 xl:px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                                            Timestamp
                                        </th>
                                        <th className="px-4 xl:px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                                            User
                                        </th>
                                        <th className="px-4 xl:px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                                            Action
                                        </th>
                                        <th className="px-4 xl:px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                                            Resource
                                        </th>
                                        <th className="px-4 xl:px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                                            IP Address
                                        </th>
                                        <th className="px-4 xl:px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                                            Status
                                        </th>
                                        <th className="px-4 xl:px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                                            Details
                                        </th>
                                    </tr>
                                </thead>
                                <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                                    {auditLogs.map((log) => {
                                        const status = log.details?.status || 'success';
                                        return (
                                            <tr key={log.id} className="hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors">
                                                <td className="px-4 xl:px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-gray-100">
                                                    {formatDate(log.created_at)}
                                                </td>
                                                <td className="px-4 xl:px-6 py-4 whitespace-nowrap">
                                                    {log.user ? (
                                                        <div>
                                                            <div className="text-sm font-medium text-gray-900 dark:text-white">
                                                                {log.user.full_name || log.user.username}
                                                            </div>
                                                            <div className="text-xs text-gray-500 dark:text-gray-400 truncate max-w-[200px]">
                                                                {log.user.email}
                                                            </div>
                                                        </div>
                                                    ) : (
                                                        <span className="text-sm text-gray-500 dark:text-gray-400">
                                                            System
                                                        </span>
                                                    )}
                                                </td>
                                                <td className="px-4 xl:px-6 py-4 whitespace-nowrap">
                                                    <span className={`px-2 py-1 text-xs font-medium rounded-full ${getActionColor(log.action)}`}>
                                                        {log.action}
                                                    </span>
                                                </td>
                                                <td className="px-4 xl:px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-gray-100">
                                                    {log.resource_type && (
                                                        <div>
                                                            <div className="font-medium">{log.resource_type}</div>
                                                            {log.resource_id && (
                                                                <div className="text-xs text-gray-500 dark:text-gray-400 truncate max-w-[150px]" title={log.resource_id}>
                                                                    {log.resource_id}
                                                                </div>
                                                            )}
                                                        </div>
                                                    )}
                                                </td>
                                                <td className="px-4 xl:px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                                                    {log.ip_address || '-'}
                                                </td>
                                                <td className="px-4 xl:px-6 py-4 whitespace-nowrap">
                                                    {status === 'success' ? (
                                                        <span className="flex items-center gap-1 text-green-600 dark:text-green-400 text-sm">
                                                            <CheckCircle2 className="w-4 h-4" />
                                                            <span className="hidden xl:inline">Success</span>
                                                        </span>
                                                    ) : (
                                                        <span className="flex items-center gap-1 text-red-600 dark:text-red-400 text-sm">
                                                            <XCircle className="w-4 h-4" />
                                                            <span className="hidden xl:inline">Failure</span>
                                                        </span>
                                                    )}
                                                </td>
                                                <td className="px-4 xl:px-6 py-4 whitespace-nowrap">
                                                    <button
                                                        onClick={() => openDetailsModal(log)}
                                                        className="text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 flex items-center gap-1 text-sm"
                                                    >
                                                        <Eye className="w-4 h-4" />
                                                        <span className="hidden xl:inline">View</span>
                                                    </button>
                                                </td>
                                            </tr>
                                        );
                                    })}
                                </tbody>
                            </table>
                        </div>

                        {/* Mobile/Tablet Card View */}
                        <div className="lg:hidden divide-y divide-gray-200 dark:divide-gray-700">
                            {auditLogs.map((log) => {
                                const status = log.details?.status || 'success';
                                return (
                                    <div key={log.id} className="p-4 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors">
                                        <div className="flex items-start justify-between mb-3">
                                            <div className="flex-1 min-w-0">
                                                <div className="flex items-center gap-2 mb-1">
                                                    <span className={`px-2 py-1 text-xs font-medium rounded-full ${getActionColor(log.action)}`}>
                                                        {log.action}
                                                    </span>
                                                    {status === 'success' ? (
                                                        <CheckCircle2 className="w-4 h-4 text-green-600 dark:text-green-400 flex-shrink-0" />
                                                    ) : (
                                                        <XCircle className="w-4 h-4 text-red-600 dark:text-red-400 flex-shrink-0" />
                                                    )}
                                                </div>
                                                <p className="text-xs text-gray-500 dark:text-gray-400">
                                                    {formatDate(log.created_at)}
                                                </p>
                                            </div>
                                            <button
                                                onClick={() => openDetailsModal(log)}
                                                className="ml-2 text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 flex-shrink-0"
                                            >
                                                <Eye className="w-5 h-5" />
                                            </button>
                                        </div>

                                        <div className="space-y-2">
                                            {log.user && (
                                                <div>
                                                    <p className="text-sm font-medium text-gray-900 dark:text-white">
                                                        {log.user.full_name || log.user.username}
                                                    </p>
                                                    <p className="text-xs text-gray-500 dark:text-gray-400 truncate">
                                                        {log.user.email}
                                                    </p>
                                                </div>
                                            )}

                                            {log.resource_type && (
                                                <div className="flex items-start gap-2">
                                                    <FileText className="w-4 h-4 text-gray-400 mt-0.5 flex-shrink-0" />
                                                    <div className="min-w-0 flex-1">
                                                        <p className="text-sm font-medium text-gray-900 dark:text-white">
                                                            {log.resource_type}
                                                        </p>
                                                        {log.resource_id && (
                                                            <p className="text-xs text-gray-500 dark:text-gray-400 truncate" title={log.resource_id}>
                                                                {log.resource_id}
                                                            </p>
                                                        )}
                                                    </div>
                                                </div>
                                            )}

                                            {log.ip_address && (
                                                <div className="flex items-center gap-2">
                                                    <Globe className="w-4 h-4 text-gray-400 flex-shrink-0" />
                                                    <p className="text-xs text-gray-500 dark:text-gray-400">
                                                        {log.ip_address}
                                                    </p>
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    </>
                )}
            </div>

            {/* Pagination */}
            {!loading && auditLogs.length > 0 && (
                <div className="mt-4 sm:mt-6">
                    <Pagination
                        currentPage={currentPage}
                        totalPages={Math.ceil(totalItems / itemsPerPage)}
                        itemsPerPage={itemsPerPage}
                        totalItems={totalItems}
                        onPageChange={handlePageChange}
                        onItemsPerPageChange={handleItemsPerPageChange}
                    />
                </div>
            )}

            {/* Details Modal */}
            {showDetailsModal && selectedLog && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-2 sm:p-4">
                    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-4xl w-full max-h-[95vh] sm:max-h-[90vh] overflow-hidden flex flex-col">
                        <div className="px-4 sm:px-6 py-3 sm:py-4 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
                            <h2 className="text-lg sm:text-xl font-bold text-gray-900 dark:text-white">
                                Audit Log Details
                            </h2>
                            <button
                                onClick={() => setShowDetailsModal(false)}
                                className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 p-1"
                            >
                                <X className="w-5 h-5 sm:w-6 sm:h-6" />
                            </button>
                        </div>
                        <div className="px-4 sm:px-6 py-3 sm:py-4 overflow-y-auto flex-1">
                            <div className="space-y-3 sm:space-y-4">
                                <div>
                                    <h3 className="text-xs sm:text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">ID</h3>
                                    <p className="text-xs sm:text-sm text-gray-900 dark:text-white font-mono break-all">{selectedLog.id}</p>
                                </div>
                                <div>
                                    <h3 className="text-xs sm:text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">Timestamp</h3>
                                    <p className="text-xs sm:text-sm text-gray-900 dark:text-white">{formatDate(selectedLog.created_at)}</p>
                                </div>
                                <div>
                                    <h3 className="text-xs sm:text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">User</h3>
                                    <p className="text-xs sm:text-sm text-gray-900 dark:text-white break-all">
                                        {selectedLog.user ? `${selectedLog.user.full_name || selectedLog.user.username} (${selectedLog.user.email})` : 'System / Anonymous'}
                                    </p>
                                </div>
                                <div>
                                    <h3 className="text-xs sm:text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">Action</h3>
                                    <p className="text-xs sm:text-sm text-gray-900 dark:text-white">{selectedLog.action}</p>
                                </div>
                                <div>
                                    <h3 className="text-xs sm:text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">Resource</h3>
                                    <p className="text-xs sm:text-sm text-gray-900 dark:text-white break-all">
                                        {selectedLog.resource_type || 'N/A'}
                                        {selectedLog.resource_id && ` (${selectedLog.resource_id})`}
                                    </p>
                                </div>
                                <div>
                                    <h3 className="text-xs sm:text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">IP Address</h3>
                                    <p className="text-xs sm:text-sm text-gray-900 dark:text-white">{selectedLog.ip_address || 'N/A'}</p>
                                </div>
                                <div>
                                    <h3 className="text-xs sm:text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">Details</h3>
                                    <pre className="text-[10px] sm:text-xs bg-gray-100 dark:bg-gray-900 p-3 sm:p-4 rounded-lg overflow-x-auto text-gray-900 dark:text-gray-100 whitespace-pre-wrap break-words">
                                        {JSON.stringify(selectedLog.details, null, 2)}
                                    </pre>
                                </div>
                            </div>
                        </div>
                        <div className="px-4 sm:px-6 py-3 sm:py-4 border-t border-gray-200 dark:border-gray-700 flex justify-end">
                            <button
                                onClick={() => setShowDetailsModal(false)}
                                className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                            >
                                Close
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

