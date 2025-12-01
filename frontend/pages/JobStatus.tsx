import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Clock, Terminal, CheckCircle, XCircle, PlayCircle, AlertCircle } from 'lucide-react';
import api from '../services/api';
import { useAuth } from '../contexts/AuthContext';

interface Job {
    id: string;
    status: string;
    triggered_by: string;
    inputs: any;
    outputs: any;
    created_at: string;
    finished_at: string;
}

interface JobLog {
    id: number;
    timestamp: string;
    level: string;
    message: string;
}

const JobStatus: React.FC = () => {
    const { jobId } = useParams<{ jobId: string }>();
    const navigate = useNavigate();
    const { isAdmin } = useAuth();
    const [job, setJob] = useState<Job | null>(null);
    const [logs, setLogs] = useState<JobLog[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        if (jobId) {
            loadJob();
            const interval = setInterval(loadJob, 3000); // Poll every 3 seconds
            return () => clearInterval(interval);
        }
    }, [jobId]);

    const loadJob = async () => {
        try {
            const [jobData, logsData] = await Promise.all([
                api.getJob(jobId!),
                api.getJobLogs(jobId!)
            ]);
            setJob(jobData);
            setLogs(logsData);
            setLoading(false);
        } catch (err: any) {
            setError(err.message || 'Failed to load job');
            setLoading(false);
        }
    };

    const getStatusColor = (status: string) => {
        switch (status?.toLowerCase()) {
            case 'success': return 'text-green-500 bg-green-500/10 border-green-500/20';
            case 'failed': return 'text-red-500 bg-red-500/10 border-red-500/20';
            case 'running': return 'text-blue-500 bg-blue-500/10 border-blue-500/20';
            case 'pending': return 'text-yellow-500 bg-yellow-500/10 border-yellow-500/20';
            default: return 'text-gray-500 bg-gray-500/10 border-gray-500/20';
        }
    };

    const getStatusIcon = (status: string) => {
        switch (status?.toLowerCase()) {
            case 'success': return <CheckCircle className="w-5 h-5" />;
            case 'failed': return <XCircle className="w-5 h-5" />;
            case 'running': return <PlayCircle className="w-5 h-5 animate-pulse" />;
            case 'pending': return <Clock className="w-5 h-5" />;
            default: return <AlertCircle className="w-5 h-5" />;
        }
    };

    const getLevelColor = (level: string) => {
        switch (level.toLowerCase()) {
            case 'error': return 'text-red-400';
            case 'warning': return 'text-yellow-400';
            case 'info': return 'text-blue-400';
            default: return 'text-gray-400';
        }
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center min-h-screen">
                <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-orange-500"></div>
            </div>
        );
    }

    if (error || !job) {
        return (
            <div className="flex flex-col items-center justify-center min-h-screen text-red-500">
                <AlertCircle className="w-12 h-12 mb-4" />
                <p className="text-xl font-semibold">{error || 'Job not found'}</p>
                <button
                    onClick={() => navigate(-1)}
                    className="mt-4 px-4 py-2 bg-gray-800 rounded-lg hover:bg-gray-700 text-white transition-colors"
                >
                    Go Back
                </button>
            </div>
        );
    }

    return (
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
            {/* Header */}
            <div className="mb-8">
                <button
                    onClick={() => navigate(-1)}
                    className="flex items-center text-gray-500 hover:text-gray-900 dark:text-gray-400 dark:hover:text-white mb-4 transition-colors"
                >
                    <ArrowLeft className="w-4 h-4 mr-2" />
                    Back
                </button>
                <div className="flex items-center justify-between">
                    <div>
                        <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">Provisioning Job</h1>
                        <p className="text-gray-500 dark:text-gray-400 font-mono text-sm">{job.id}</p>
                    </div>
                    <div className={`flex items-center px-4 py-2 rounded-lg border ${getStatusColor(job.status)}`}>
                        <span className="mr-2">{getStatusIcon(job.status)}</span>
                        <span className="font-semibold uppercase tracking-wide">{job.status}</span>
                    </div>
                </div>
            </div>
            {/* Restricted View for Non-Admins */}
            {!isAdmin ? (
                <div className="max-w-2xl mx-auto">
                    <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-8 text-center transition-colors">
                        <div className="mb-4">
                            <AlertCircle className="w-12 h-12 mx-auto text-yellow-500" />
                        </div>
                        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">Job Status</h3>
                        <p className="text-gray-500 dark:text-gray-400 mb-6">
                            Your provisioning request has been submitted. An administrator will review the job details.
                        </p>
                        <div className="space-y-3 text-left bg-gray-50 dark:bg-black/30 rounded-lg p-4 border border-gray-200 dark:border-gray-800">
                            <div className="flex justify-between">
                                <span className="text-gray-500">Job ID:</span>
                                <code className="text-gray-700 dark:text-gray-300 font-mono text-sm">{job.id}</code>
                            </div>
                            <div className="flex justify-between">
                                <span className="text-gray-500">Status:</span>
                                <span className={`px-3 py-1 rounded-full text-xs font-medium ${getStatusColor(job.status)}`}>
                                    {job.status}
                                </span>
                            </div>
                            <div className="flex justify-between">
                                <span className="text-gray-500">Created:</span>
                                <span className="text-gray-700 dark:text-gray-300">{new Date(job.created_at).toLocaleString()}</span>
                            </div>
                        </div>
                    </div>
                </div>
            ) : (
                /* Admin Full View */
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                    {/* Left Column: Details & Inputs */}
                    <div className="lg:col-span-1 space-y-6">
                        {/* Job Details Card */}
                        <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-6 transition-colors">
                            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Details</h3>
                            <div className="space-y-4">
                                <div>
                                    <label className="block text-sm text-gray-500 mb-1">Triggered By</label>
                                    <div className="text-gray-900 dark:text-gray-200 font-medium">{job.triggered_by}</div>
                                </div>
                                <div>
                                    <label className="block text-sm text-gray-500 mb-1">Created At</label>
                                    <div className="text-gray-900 dark:text-gray-200 font-medium">
                                        {new Date(job.created_at).toLocaleString()}
                                    </div>
                                </div>
                            </div>
                        </div>

                        {/* Inputs Card */}
                        <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-6 transition-colors">
                            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Inputs</h3>
                            <div className="space-y-3">
                                {Object.entries(job.inputs).map(([key, value]) => (
                                    <div key={key} className="group">
                                        <label className="block text-xs uppercase tracking-wider text-gray-500 mb-1 group-hover:text-orange-600 dark:group-hover:text-orange-400 transition-colors">
                                            {key.replace(/_/g, ' ')}
                                        </label>
                                        <div className="text-sm text-gray-700 dark:text-gray-300 font-mono bg-gray-50 dark:bg-black/50 p-2 rounded border border-gray-200 dark:border-gray-800 break-all">
                                            {String(value)}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>

                        {/* Outputs Card (if success) */}
                        {job.outputs && Object.keys(job.outputs).length > 0 && (
                            <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-6 transition-colors">
                                <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Outputs</h3>
                                <div className="space-y-3">
                                    {Object.entries(job.outputs).map(([key, value]) => (
                                        <div key={key} className="group">
                                            <label className="block text-xs uppercase tracking-wider text-gray-500 mb-1 group-hover:text-green-600 dark:group-hover:text-green-400 transition-colors">
                                                {key}
                                            </label>
                                            <div className="text-sm text-green-700 dark:text-green-400 font-mono bg-green-50 dark:bg-green-900/10 p-2 rounded border border-green-200 dark:border-green-900/20 break-all">
                                                {String(value)}
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}
                    </div>

                    {/* Right Column: Logs */}
                    <div className="lg:col-span-2">
                        <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl flex flex-col h-[600px] transition-colors">
                            <div className="p-4 border-b border-gray-200 dark:border-gray-800 flex items-center justify-between">
                                <h3 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center">
                                    <Terminal className="w-5 h-5 mr-2 text-gray-400" />
                                    Execution Logs
                                </h3>
                                <span className="text-xs text-gray-500">
                                    {logs.length} lines
                                </span>
                            </div>
                            <div className="flex-1 overflow-y-auto p-4 font-mono text-sm space-y-2 bg-gray-50 dark:bg-black/50">
                                {logs.length === 0 ? (
                                    <div className="flex flex-col items-center justify-center h-full text-gray-500">
                                        <Clock className="w-8 h-8 mb-2 opacity-50" />
                                        <p>Waiting for logs...</p>
                                    </div>
                                ) : (
                                    logs.map((log) => (
                                        <div key={log.id} className="flex items-start gap-3 hover:bg-gray-100 dark:hover:bg-white/5 p-1 rounded transition-colors">
                                            <span className="text-gray-500 dark:text-gray-600 text-xs whitespace-nowrap pt-0.5">
                                                {new Date(log.timestamp).toLocaleTimeString()}
                                            </span>
                                            <span className={`text-xs font-bold uppercase w-16 pt-0.5 ${getLevelColor(log.level)}`}>
                                                {log.level}
                                            </span>
                                            <span className="text-gray-800 dark:text-gray-300 break-words whitespace-pre-wrap flex-1">
                                                {log.message}
                                            </span>
                                        </div>
                                    ))
                                )}
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default JobStatus;
