import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, ExternalLink, Clock, CheckCircle, XCircle, PlayCircle, AlertCircle, Trash2, Trash } from 'lucide-react';
import api from '../services/api';
import { appLogger } from '../utils/logger';

interface Job {
    id: string;
    status: string;
    triggered_by: string;
    created_at: string;
    finished_at: string | null;
}

export const AdminJobs: React.FC = () => {
    const navigate = useNavigate();
    const [jobs, setJobs] = useState<Job[]>([]);
    const [loading, setLoading] = useState(true);
    const [searchQuery, setSearchQuery] = useState('');
    const [debouncedSearch, setDebouncedSearch] = useState('');
    const [selectedJobs, setSelectedJobs] = useState<Set<string>>(new Set());
    const [deleting, setDeleting] = useState(false);
    const [deleteModalOpen, setDeleteModalOpen] = useState(false);
    const [deleteJobId, setDeleteJobId] = useState<string | null>(null);
    const [bulkDeleteModalOpen, setBulkDeleteModalOpen] = useState(false);
    const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

    // Debounce search
    useEffect(() => {
        const timer = setTimeout(() => {
            setDebouncedSearch(searchQuery);
        }, 300);
        return () => clearTimeout(timer);
    }, [searchQuery]);

    // Fetch jobs
    useEffect(() => {
        loadJobs();
    }, [debouncedSearch]);

    const loadJobs = async () => {
        try {
            setLoading(true);
            const data = await api.listJobs({
                jobId: debouncedSearch || undefined,
                limit: 100
            });
            setJobs(data);
        } catch (err) {
            appLogger.error('Failed to load jobs:', err);
        } finally {
            setLoading(false);
        }
    };

    const getStatusColor = (status: string) => {
        switch (status?.toLowerCase()) {
            case 'success': return 'text-green-600 dark:text-green-400 bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800';
            case 'failed': return 'text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800';
            case 'running': return 'text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800';
            case 'pending': return 'text-yellow-600 dark:text-yellow-400 bg-yellow-50 dark:bg-yellow-900/20 border-yellow-200 dark:border-yellow-800';
            default: return 'text-gray-600 dark:text-gray-400 bg-gray-50 dark:bg-gray-900/20 border-gray-200 dark:border-gray-800';
        }
    };

    const getStatusIcon = (status: string) => {
        switch (status?.toLowerCase()) {
            case 'success': return <CheckCircle className="w-4 h-4" />;
            case 'failed': return <XCircle className="w-4 h-4" />;
            case 'running': return <PlayCircle className="w-4 h-4 animate-pulse" />;
            case 'pending': return <Clock className="w-4 h-4" />;
            default: return <AlertCircle className="w-4 h-4" />;
        }
    };

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
                    <div className="relative">
                        <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                        <input
                            type="text"
                            placeholder="Search by Job ID..."
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            className="pl-9 pr-4 py-2 border border-gray-300 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-orange-500 w-full sm:w-64"
                        />
                    </div>
                </div>
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
                                        {searchQuery ? 'No jobs found matching your search' : 'No jobs yet'}
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
                                            <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border ${getStatusColor(job.status)}`}>
                                                {getStatusIcon(job.status)}
                                                {job.status}
                                            </span>
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
