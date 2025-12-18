import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, ExternalLink, Trash2, Trash, Filter, X, Calendar, Clock, RotateCcw } from 'lucide-react';
import api from '../services/api';
import { appLogger } from '../utils/logger';
import { getStatusColor, getStatusIcon } from '../utils/jobStatus';
import { Pagination } from '../components/Pagination';

interface Job {
    id: string;
    status: string;
    triggered_by: string;
    created_at: string;
    finished_at: string | null;
    retry_count?: number;
    error_state?: string;
    error_message?: string;
}

export const AdminJobs: React.FC = () => {
    const navigate = useNavigate();
    const [jobs, setJobs] = useState<Job[]>([]);
    const [loading, setLoading] = useState(true);
    const [searchQuery, setSearchQuery] = useState('');
    const [emailFilter, setEmailFilter] = useState('');
    const [startDate, setStartDate] = useState('');
    const [endDate, setEndDate] = useState('');
    const [showFilters, setShowFilters] = useState(false);
    const [debouncedSearch, setDebouncedSearch] = useState('');
    const [debouncedEmail, setDebouncedEmail] = useState('');
    const [selectedJobs, setSelectedJobs] = useState<Set<string>>(new Set());
    const [deleting, setDeleting] = useState(false);
    const [deleteModalOpen, setDeleteModalOpen] = useState(false);
    const [deleteJobId, setDeleteJobId] = useState<string | null>(null);
    const [bulkDeleteModalOpen, setBulkDeleteModalOpen] = useState(false);
    const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
    const [currentPage, setCurrentPage] = useState(1);
    const [itemsPerPage, setItemsPerPage] = useState(50);
    const [totalItems, setTotalItems] = useState(0);

    // Debounce search queries
    useEffect(() => {
        const timer = setTimeout(() => {
            setDebouncedSearch(searchQuery);
        }, 300);
        return () => clearTimeout(timer);
    }, [searchQuery]);

    useEffect(() => {
        const timer = setTimeout(() => {
            setDebouncedEmail(emailFilter);
        }, 300);
        return () => clearTimeout(timer);
    }, [emailFilter]);

    // Fetch jobs when filters or pagination change
    useEffect(() => {
        loadJobs();
    }, [debouncedSearch, debouncedEmail, startDate, endDate, currentPage, itemsPerPage]);

    const loadJobs = async () => {
        try {
            setLoading(true);
            const skip = (currentPage - 1) * itemsPerPage;
            const response = await api.listJobs({
                jobId: debouncedSearch || undefined,
                email: debouncedEmail || undefined,
                startDate: startDate || undefined,
                endDate: endDate || undefined,
                skip,
                limit: itemsPerPage
            });
            
            // Handle both old format (array) and new format (object with items/total)
            if (Array.isArray(response)) {
                setJobs(response);
                setTotalItems(response.length);
            } else {
                setJobs(response.items || []);
                setTotalItems(response.total || 0);
            }
        } catch (err) {
            appLogger.error('Failed to load jobs:', err);
        } finally {
            setLoading(false);
        }
    };

    const clearFilters = () => {
        setSearchQuery('');
        setEmailFilter('');
        setStartDate('');
        setEndDate('');
        setCurrentPage(1); // Reset to first page when clearing filters
    };

    const hasActiveFilters = (searchQuery || emailFilter) || startDate || endDate;

    const handlePageChange = (page: number) => {
        setCurrentPage(page);
        // Scroll to top when page changes
        window.scrollTo({ top: 0, behavior: 'smooth' });
    };

    const handleItemsPerPageChange = (newItemsPerPage: number) => {
        setItemsPerPage(newItemsPerPage);
        setCurrentPage(1); // Reset to first page when changing items per page
    };

    const totalPages = Math.ceil(totalItems / itemsPerPage);


    const formatDate = (dateString: string) => {
        return new Date(dateString).toLocaleString();
    };

    const handleSelectJob = (jobId: string) => {
        const newSelected = new Set(selectedJobs);
        if (newSelected.has(jobId)) {
            newSelected.delete(jobId);
        } else {
            newSelected.add(jobId);
        }
        setSelectedJobs(newSelected);
    };

    const handleSelectAll = () => {
        if (selectedJobs.size === jobs.length) {
            setSelectedJobs(new Set());
        } else {
            setSelectedJobs(new Set(jobs.map(job => job.id)));
        }
    };

    const handleDeleteJob = async (jobId: string) => {
        setDeleting(true);
        try {
            await api.deleteJob(jobId);
            setJobs(jobs.filter(job => job.id !== jobId));
            setDeleteModalOpen(false);
            setDeleteJobId(null);
            setMessage({ type: 'success', text: 'Job deleted successfully' });
            setTimeout(() => setMessage(null), 3000);
        } catch (err: any) {
            setMessage({ type: 'error', text: err.message || 'Failed to delete job' });
            setTimeout(() => setMessage(null), 5000);
        } finally {
            setDeleting(false);
        }
    };

    const handleBulkDelete = async () => {
        if (selectedJobs.size === 0) return;

        setDeleting(true);
        try {
            const jobIds = Array.from(selectedJobs);
            const result = await api.bulkDeleteJobs(jobIds);
            
            // Remove deleted jobs from the list
            setJobs(jobs.filter(job => !selectedJobs.has(job.id)));
            setSelectedJobs(new Set());
            setBulkDeleteModalOpen(false);
            
            if (result.failed_count > 0) {
                setMessage({ 
                    type: 'error', 
                    text: `Deleted ${result.deleted_count} jobs. ${result.failed_count} failed.` 
                });
            } else {
                setMessage({ 
                    type: 'success', 
                    text: `Successfully deleted ${result.deleted_count} jobs` 
                });
            }
            setTimeout(() => setMessage(null), 5000);
        } catch (err: any) {
            setMessage({ type: 'error', text: err.message || 'Failed to delete jobs' });
            setTimeout(() => setMessage(null), 5000);
        } finally {
            setDeleting(false);
        }
    };

    const openDeleteModal = (jobId: string) => {
        setDeleteJobId(jobId);
        setDeleteModalOpen(true);
    };

    return (
        <div className="max-w-7xl mx-auto space-y-6">
            {/* Header */}
            <div className="flex flex-col gap-4">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                    <div>
                        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">All Jobs</h1>
                        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">Monitor and manage provisioning jobs</p>
                    </div>
                    <div className="flex items-center gap-3">
                        {selectedJobs.size > 0 && (
                            <button
                                onClick={() => setBulkDeleteModalOpen(true)}
                                className="inline-flex items-center gap-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors text-sm font-medium"
                            >
                                <Trash className="w-4 h-4" />
                                Delete Selected ({selectedJobs.size})
                            </button>
                        )}
                        <button
                            onClick={() => setShowFilters(!showFilters)}
                            className={`inline-flex items-center gap-2 px-4 py-2 rounded-lg transition-colors text-sm font-medium ${
                                showFilters || hasActiveFilters
                                    ? 'bg-orange-600 text-white hover:bg-orange-700'
                                    : 'bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700'
                            }`}
                        >
                            <Filter className="w-4 h-4" />
                            Filters
                            {hasActiveFilters && (
                                <span className="ml-1 px-1.5 py-0.5 bg-white/20 dark:bg-black/20 rounded text-xs">
                                    {[searchQuery, emailFilter, startDate, endDate].filter(Boolean).length}
                                </span>
                            )}
                        </button>
                    </div>
                </div>

                {/* Filters Panel */}
                {showFilters && (
                    <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-6 shadow-sm">
                        <div className="space-y-4">
                            {/* Unified Search Box */}
                            <div className="relative">
                                <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-2">
                                    Search by Job ID or Email
                                </label>
                                <div className="relative">
                                    <Search className="w-5 h-5 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 dark:text-gray-500 pointer-events-none" />
                                    <input
                                        type="text"
                                        placeholder="Search by Job ID or email address..."
                                        value={searchQuery || emailFilter}
                                        onChange={(e) => {
                                            const value = e.target.value;
                                            // Detect if it looks like an email (contains @) or job ID
                                            if (value.includes('@')) {
                                                setEmailFilter(value);
                                                setSearchQuery('');
                                            } else {
                                                setSearchQuery(value);
                                                setEmailFilter('');
                                            }
                                        }}
                                        className="pl-10 pr-4 py-2.5 w-full border border-gray-300 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-orange-500"
                                    />
                                </div>
                            </div>

                            {/* Date Range */}
                            <div>
                                <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-3">
                                    <Calendar className="w-4 h-4 inline-block mr-1.5" />
                                    Date & Time Range
                                </label>
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                    {/* Start Date */}
                                    <div className="relative group">
                                        <div className="absolute inset-0 bg-gradient-to-r from-orange-500/10 to-orange-600/10 rounded-xl opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none"></div>
                                        <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-2 ml-1">
                                            From
                                        </label>
                                        <div className="relative">
                                            <Calendar className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 dark:text-gray-500 pointer-events-none" />
                                            <input
                                                type="datetime-local"
                                                value={startDate}
                                                onChange={(e) => setStartDate(e.target.value)}
                                                className="w-full pl-10 pr-4 py-3 border border-gray-300 dark:border-gray-700 rounded-xl bg-white dark:bg-gray-800 text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-orange-500 transition-all shadow-sm hover:shadow-md"
                                            />
                                        </div>
                                        {startDate && (
                                            <div className="mt-1.5 ml-1 text-xs text-gray-400 dark:text-gray-500">
                                                {new Date(startDate).toLocaleString()}
                                            </div>
                                        )}
                                    </div>

                                    {/* End Date */}
                                    <div className="relative group">
                                        <div className="absolute inset-0 bg-gradient-to-r from-orange-500/10 to-orange-600/10 rounded-xl opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none"></div>
                                        <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-2 ml-1">
                                            To
                                        </label>
                                        <div className="relative">
                                            <Calendar className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 dark:text-gray-500 pointer-events-none" />
                                            <input
                                                type="datetime-local"
                                                value={endDate}
                                                onChange={(e) => setEndDate(e.target.value)}
                                                min={startDate || undefined}
                                                className="w-full pl-10 pr-4 py-3 border border-gray-300 dark:border-gray-700 rounded-xl bg-white dark:bg-gray-800 text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-orange-500 transition-all shadow-sm hover:shadow-md"
                                            />
                                        </div>
                                        {endDate && (
                                            <div className="mt-1.5 ml-1 text-xs text-gray-400 dark:text-gray-500">
                                                {new Date(endDate).toLocaleString()}
                                            </div>
                                        )}
                                    </div>
                                </div>
                                
                                {/* Quick Date Presets */}
                                <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-800">
                                    <div className="flex flex-wrap gap-2">
                                        <span className="text-xs font-medium text-gray-500 dark:text-gray-400 mr-2 self-center">Quick select:</span>
                                        <button
                                            onClick={() => {
                                                const now = new Date();
                                                const todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 0, 0, 0);
                                                const todayEnd = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 23, 59, 59);
                                                setStartDate(todayStart.toISOString().slice(0, 16));
                                                setEndDate(todayEnd.toISOString().slice(0, 16));
                                            }}
                                            className="px-3 py-1.5 text-xs font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-lg transition-colors"
                                        >
                                            Today
                                        </button>
                                        <button
                                            onClick={() => {
                                                const now = new Date();
                                                const yesterdayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate() - 1, 0, 0, 0);
                                                const yesterdayEnd = new Date(now.getFullYear(), now.getMonth(), now.getDate() - 1, 23, 59, 59);
                                                setStartDate(yesterdayStart.toISOString().slice(0, 16));
                                                setEndDate(yesterdayEnd.toISOString().slice(0, 16));
                                            }}
                                            className="px-3 py-1.5 text-xs font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-lg transition-colors"
                                        >
                                            Yesterday
                                        </button>
                                        <button
                                            onClick={() => {
                                                const now = new Date();
                                                const weekStart = new Date(now.getFullYear(), now.getMonth(), now.getDate() - 7, 0, 0, 0);
                                                const weekEnd = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 23, 59, 59);
                                                setStartDate(weekStart.toISOString().slice(0, 16));
                                                setEndDate(weekEnd.toISOString().slice(0, 16));
                                            }}
                                            className="px-3 py-1.5 text-xs font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-lg transition-colors"
                                        >
                                            Last 7 Days
                                        </button>
                                        <button
                                            onClick={() => {
                                                const now = new Date();
                                                const monthStart = new Date(now.getFullYear(), now.getMonth(), 1, 0, 0, 0);
                                                const monthEnd = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 23, 59, 59);
                                                setStartDate(monthStart.toISOString().slice(0, 16));
                                                setEndDate(monthEnd.toISOString().slice(0, 16));
                                            }}
                                            className="px-3 py-1.5 text-xs font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-lg transition-colors"
                                        >
                                            This Month
                                        </button>
                                        <button
                                            onClick={() => {
                                                const now = new Date();
                                                const lastMonthStart = new Date(now.getFullYear(), now.getMonth() - 1, 1, 0, 0, 0);
                                                const lastMonthEnd = new Date(now.getFullYear(), now.getMonth(), 0, 23, 59, 59);
                                                setStartDate(lastMonthStart.toISOString().slice(0, 16));
                                                setEndDate(lastMonthEnd.toISOString().slice(0, 16));
                                            }}
                                            className="px-3 py-1.5 text-xs font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-lg transition-colors"
                                        >
                                            Last Month
                                        </button>
                                    </div>
                                </div>
                            </div>

                            {/* Clear Filters Button */}
                            {hasActiveFilters && (
                                <div className="flex justify-end border-t border-gray-200 dark:border-gray-800 pt-4">
                                    <button
                                        onClick={clearFilters}
                                        className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white transition-colors"
                                    >
                                        <X className="w-4 h-4" />
                                        Clear All Filters
                                    </button>
                                </div>
                            )}
                        </div>
                    </div>
                )}
            </div>

            {/* Message */}
            {message && (
                <div className={`p-4 rounded-lg ${
                    message.type === 'success' 
                        ? 'bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 text-green-800 dark:text-green-200'
                        : 'bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-800 dark:text-red-200'
                }`}>
                    {message.text}
                </div>
            )}

            {/* Jobs Table */}
            <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl overflow-hidden shadow-sm">
                <div className="overflow-x-auto">
                    <table className="w-full text-left text-sm">
                        <thead className="bg-gray-50 dark:bg-gray-800/50 border-b border-gray-200 dark:border-gray-800">
                            <tr>
                                <th className="px-6 py-4 font-medium text-gray-500 dark:text-gray-400">
                                    <input
                                        type="checkbox"
                                        checked={selectedJobs.size === jobs.length && jobs.length > 0}
                                        onChange={handleSelectAll}
                                        className="w-4 h-4 text-orange-600 rounded focus:ring-orange-500"
                                    />
                                </th>
                                <th className="px-6 py-4 font-medium text-gray-500 dark:text-gray-400">Job ID</th>
                                <th className="px-6 py-4 font-medium text-gray-500 dark:text-gray-400">Status</th>
                                <th className="px-6 py-4 font-medium text-gray-500 dark:text-gray-400">Triggered By</th>
                                <th className="px-6 py-4 font-medium text-gray-500 dark:text-gray-400">Created</th>
                                <th className="px-6 py-4 font-medium text-gray-500 dark:text-gray-400">Finished</th>
                                <th className="px-6 py-4 font-medium text-gray-500 dark:text-gray-400 text-right">Actions</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-200 dark:divide-gray-800">
                            {loading ? (
                                <tr>
                                    <td colSpan={7} className="px-6 py-12 text-center">
                                        <div className="flex justify-center items-center gap-2">
                                            <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-orange-600"></div>
                                            <span className="text-gray-500">Loading jobs...</span>
                                        </div>
                                    </td>
                                </tr>
                            ) : jobs.length === 0 ? (
                                <tr>
                                    <td colSpan={7} className="px-6 py-12 text-center text-gray-500">
                                        {hasActiveFilters ? 'No jobs found matching your filters' : 'No jobs yet'}
                                    </td>
                                </tr>
                            ) : (
                                jobs.map((job) => (
                                    <tr key={job.id} className="hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors">
                                        <td className="px-6 py-4">
                                            <input
                                                type="checkbox"
                                                checked={selectedJobs.has(job.id)}
                                                onChange={() => handleSelectJob(job.id)}
                                                className="w-4 h-4 text-orange-600 rounded focus:ring-orange-500"
                                            />
                                        </td>
                                        <td className="px-6 py-4">
                                            <code className="text-xs bg-gray-100 dark:bg-gray-800 px-2 py-1 rounded font-mono">
                                                {job.id.substring(0, 8)}...
                                            </code>
                                        </td>
                                        <td className="px-6 py-4">
                                            <div className="flex flex-col gap-1">
                                                <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border ${getStatusColor(job.status, job)}`}>
                                                    {getStatusIcon(job.status)}
                                                    {job.status === 'dead_letter' ? 'Dead Letter' : job.status}
                                                </span>
                                                {job.retry_count !== undefined && job.retry_count > 0 && (
                                                    <span className="text-xs text-gray-500 dark:text-gray-400">
                                                        Retries: {job.retry_count}
                                                    </span>
                                                )}
                                                {job.error_state && (
                                                    <span className="text-xs text-gray-500 dark:text-gray-400">
                                                        Error: {job.error_state}
                                                    </span>
                                                )}
                                            </div>
                                        </td>
                                        <td className="px-6 py-4 text-gray-700 dark:text-gray-300">
                                            {job.triggered_by}
                                        </td>
                                        <td className="px-6 py-4 text-gray-500 dark:text-gray-400 text-xs">
                                            {formatDate(job.created_at)}
                                        </td>
                                        <td className="px-6 py-4 text-gray-500 dark:text-gray-400 text-xs">
                                            {job.finished_at ? formatDate(job.finished_at) : '-'}
                                        </td>
                                        <td className="px-6 py-4 text-right">
                                            <div className="flex items-center justify-end gap-2">
                                                {job.status === 'dead_letter' && (
                                                    <button
                                                        onClick={async () => {
                                                            try {
                                                                setMessage({ type: 'success', text: 'Replaying job...' });
                                                                await api.replayJob(job.id);
                                                                setMessage({ type: 'success', text: 'Job replayed successfully' });
                                                                setTimeout(() => setMessage(null), 3000);
                                                                loadJobs();
                                                            } catch (err: any) {
                                                                setMessage({ type: 'error', text: err.message || 'Failed to replay job' });
                                                                setTimeout(() => setMessage(null), 5000);
                                                            }
                                                        }}
                                                        className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm text-purple-600 dark:text-purple-400 hover:bg-purple-50 dark:hover:bg-purple-900/20 rounded-lg transition-colors"
                                                    >
                                                        <RotateCcw className="w-3.5 h-3.5" />
                                                        Replay
                                                    </button>
                                                )}
                                                <button
                                                    onClick={() => navigate(`/jobs/${job.id}`)}
                                                    className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm text-orange-600 dark:text-orange-400 hover:bg-orange-50 dark:hover:bg-orange-900/20 rounded-lg transition-colors"
                                                >
                                                    View Details
                                                    <ExternalLink className="w-3.5 h-3.5" />
                                                </button>
                                                <button
                                                    onClick={() => openDeleteModal(job.id)}
                                                    className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors"
                                                >
                                                    <Trash2 className="w-3.5 h-3.5" />
                                                </button>
                                            </div>
                                        </td>
                                    </tr>
                                ))
                            )}
                        </tbody>
                    </table>
                </div>
                
                {/* Pagination */}
                {totalItems > 0 && (
                    <Pagination
                        currentPage={currentPage}
                        totalPages={totalPages}
                        totalItems={totalItems}
                        itemsPerPage={itemsPerPage}
                        onPageChange={handlePageChange}
                        onItemsPerPageChange={handleItemsPerPageChange}
                        showItemsPerPage={true}
                    />
                )}
            </div>

            {/* Delete Single Job Modal */}
            {deleteModalOpen && deleteJobId && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
                    <div className="bg-white dark:bg-gray-900 rounded-xl p-6 max-w-md w-full mx-4 shadow-xl">
                        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">Delete Job</h3>
                        <p className="text-sm text-gray-600 dark:text-gray-400 mb-6">
                            Are you sure you want to delete this job? This action cannot be undone.
                        </p>
                        <div className="flex gap-3 justify-end">
                            <button
                                onClick={() => {
                                    setDeleteModalOpen(false);
                                    setDeleteJobId(null);
                                }}
                                className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-800 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
                                disabled={deleting}
                            >
                                Cancel
                            </button>
                            <button
                                onClick={() => handleDeleteJob(deleteJobId)}
                                disabled={deleting}
                                className="px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                                {deleting ? 'Deleting...' : 'Delete'}
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Bulk Delete Modal */}
            {bulkDeleteModalOpen && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
                    <div className="bg-white dark:bg-gray-900 rounded-xl p-6 max-w-md w-full mx-4 shadow-xl">
                        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">Delete Multiple Jobs</h3>
                        <p className="text-sm text-gray-600 dark:text-gray-400 mb-6">
                            Are you sure you want to delete <strong>{selectedJobs.size}</strong> job{selectedJobs.size > 1 ? 's' : ''}? This action cannot be undone.
                        </p>
                        <div className="flex gap-3 justify-end">
                            <button
                                onClick={() => setBulkDeleteModalOpen(false)}
                                className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-800 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
                                disabled={deleting}
                            >
                                Cancel
                            </button>
                            <button
                                onClick={handleBulkDelete}
                                disabled={deleting}
                                className="px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                                {deleting ? 'Deleting...' : `Delete ${selectedJobs.size} Job${selectedJobs.size > 1 ? 's' : ''}`}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};
