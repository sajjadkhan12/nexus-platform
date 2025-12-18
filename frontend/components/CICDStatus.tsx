import React, { useState, useEffect } from 'react';
import { CheckCircle, XCircle, Clock, Loader, ExternalLink, RefreshCw, AlertCircle } from 'lucide-react';
import api from '../services/api';

interface CICDStatusProps {
    deploymentId: string;
    autoRefresh?: boolean;
    refreshInterval?: number; // in milliseconds
    onStatusChange?: (status: string) => void;
}

interface CICDStatusData {
    ci_cd_status?: string;
    ci_cd_run_id?: number;
    ci_cd_run_url?: string;
    message?: string;
    error?: string;
}

export const CICDStatus: React.FC<CICDStatusProps> = ({
    deploymentId,
    autoRefresh = true,
    refreshInterval = 15000, // 15 seconds
    onStatusChange
}) => {
    const [status, setStatus] = useState<CICDStatusData | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [isRefreshing, setIsRefreshing] = useState(false);

    const fetchStatus = async (showLoading = true) => {
        try {
            if (showLoading) setLoading(true);
            setIsRefreshing(true);
            setError(null);
            
            const data = await api.deploymentsApi.getCICDStatus(deploymentId);
            setStatus(data);
            
            if (onStatusChange && data.ci_cd_status) {
                onStatusChange(data.ci_cd_status);
            }
        } catch (err: any) {
            setError(err.message || 'Failed to fetch CI/CD status');
            console.error('Error fetching CI/CD status:', err);
        } finally {
            setLoading(false);
            setIsRefreshing(false);
        }
    };

    useEffect(() => {
        fetchStatus();
    }, [deploymentId]);

    useEffect(() => {
        if (!autoRefresh) return;
        
        // Only auto-refresh if status is pending or running
        const shouldRefresh = status?.ci_cd_status === 'pending' || status?.ci_cd_status === 'running';
        
        if (shouldRefresh) {
            const interval = setInterval(() => {
                fetchStatus(false); // Don't show loading spinner on auto-refresh
            }, refreshInterval);
            
            return () => clearInterval(interval);
        }
    }, [status?.ci_cd_status, autoRefresh, refreshInterval]);

    const getStatusIcon = () => {
        if (loading) {
            return <Loader className="w-5 h-5 animate-spin text-gray-400" />;
        }
        
        switch (status?.ci_cd_status) {
            case 'success':
                return <CheckCircle className="w-5 h-5 text-green-500" />;
            case 'failed':
            case 'cancelled':
                return <XCircle className="w-5 h-5 text-red-500" />;
            case 'running':
                return <Loader className="w-5 h-5 animate-spin text-blue-500" />;
            case 'pending':
                return <Clock className="w-5 h-5 text-yellow-500" />;
            default:
                return <AlertCircle className="w-5 h-5 text-gray-400" />;
        }
    };

    const getStatusColor = () => {
        switch (status?.ci_cd_status) {
            case 'success':
                return 'bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800 text-green-700 dark:text-green-300';
            case 'failed':
            case 'cancelled':
                return 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800 text-red-700 dark:text-red-300';
            case 'running':
                return 'bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800 text-blue-700 dark:text-blue-300';
            case 'pending':
                return 'bg-yellow-50 dark:bg-yellow-900/20 border-yellow-200 dark:border-yellow-800 text-yellow-700 dark:text-yellow-300';
            default:
                return 'bg-gray-50 dark:bg-gray-900/20 border-gray-200 dark:border-gray-800 text-gray-700 dark:text-gray-300';
        }
    };

    const getStatusText = () => {
        if (loading) return 'Loading...';
        if (error) return 'Error';
        if (!status?.ci_cd_status) return 'Unknown';
        
        const statusMap: Record<string, string> = {
            'pending': 'Pending',
            'running': 'Running',
            'success': 'Success',
            'failed': 'Failed',
            'cancelled': 'Cancelled'
        };
        
        return statusMap[status.ci_cd_status] || status.ci_cd_status;
    };

    const handleManualRefresh = async () => {
        await fetchStatus();
    };

    if (loading && !status) {
        return (
            <div className="flex items-center gap-2 text-gray-500 dark:text-gray-400">
                <Loader className="w-4 h-4 animate-spin" />
                <span>Loading CI/CD status...</span>
            </div>
        );
    }

    return (
        <div className={`border rounded-lg p-4 ${getStatusColor()}`}>
            <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                    {getStatusIcon()}
                    <span className="font-semibold">CI/CD Status: {getStatusText()}</span>
                </div>
                <div className="flex items-center gap-2">
                    <button
                        onClick={handleManualRefresh}
                        disabled={isRefreshing}
                        className="p-1 hover:bg-white/20 dark:hover:bg-black/20 rounded transition-colors disabled:opacity-50"
                        title="Refresh status"
                    >
                        <RefreshCw className={`w-4 h-4 ${isRefreshing ? 'animate-spin' : ''}`} />
                    </button>
                    {status?.ci_cd_run_url && (
                        <a
                            href={status.ci_cd_run_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="p-1 hover:bg-white/20 dark:hover:bg-black/20 rounded transition-colors"
                            title="View on GitHub Actions"
                        >
                            <ExternalLink className="w-4 h-4" />
                        </a>
                    )}
                </div>
            </div>
            
            {status?.ci_cd_run_id && (
                <div className="text-sm opacity-75 mt-1">
                    Run ID: {status.ci_cd_run_id}
                </div>
            )}
            
            {status?.message && (
                <div className="text-sm mt-2 opacity-75">
                    {status.message}
                </div>
            )}
            
            {error && (
                <div className="text-sm mt-2 text-red-600 dark:text-red-400">
                    {error}
                </div>
            )}
            
            {autoRefresh && (status?.ci_cd_status === 'pending' || status?.ci_cd_status === 'running') && (
                <div className="text-xs mt-2 opacity-60">
                    Auto-refreshing every {refreshInterval / 1000} seconds...
                </div>
            )}
        </div>
    );
};

