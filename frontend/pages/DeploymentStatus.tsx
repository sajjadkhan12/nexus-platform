import React, { useEffect, useState } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { Terminal, ArrowLeft, Package, Tag, Globe, Clock, Trash2, ExternalLink, Copy, Check, AlertCircle, Loader2, RotateCw, Github, Code, Edit2, X, History, Undo2 } from 'lucide-react';
import api from '../services/api';
import { StatusBadge } from '../components/Badges';
import { EnvironmentBadge } from '../components/EnvironmentBadge';
import { useNotification } from '../contexts/NotificationContext';
import { appLogger } from '../utils/logger';
import { CICDStatus } from '../components/CICDStatus';
import { useAuth } from '../contexts/AuthContext';
import { BusinessUnitWarningModal } from '../components/BusinessUnitWarningModal';

import { Deployment, DeploymentHistory } from '../types';

export const DeploymentStatusPage: React.FC = () => {
    const { id } = useParams<{ id: string }>();
    const navigate = useNavigate();
    const { addNotification } = useNotification();
    const { activeBusinessUnit, hasBusinessUnitAccess, isAdmin, user, isLoadingBusinessUnits } = useAuth();
    const [showBusinessUnitWarning, setShowBusinessUnitWarning] = useState(false);
    const [deployment, setDeployment] = useState<Deployment | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [copiedField, setCopiedField] = useState<string | null>(null);
    const [showDeleteModal, setShowDeleteModal] = useState(false);
    const [isDeleting, setIsDeleting] = useState(false);
    const [isRetrying, setIsRetrying] = useState(false);
    const [pollInterval, setPollInterval] = useState<NodeJS.Timeout | null>(null);
    const [autoPollInterval, setAutoPollInterval] = useState<NodeJS.Timeout | null>(null);
    const [repositoryInfo, setRepositoryInfo] = useState<any>(null);
    const [loadingRepo, setLoadingRepo] = useState(false);
    const [showUpdateModal, setShowUpdateModal] = useState(false);
    const [isUpdating, setIsUpdating] = useState(false);
    const [updateInputs, setUpdateInputs] = useState<Record<string, any>>({});
    const [pluginManifest, setPluginManifest] = useState<any>(null);
    const [loadingManifest, setLoadingManifest] = useState(false);
    const [deploymentHistory, setDeploymentHistory] = useState<DeploymentHistory[]>([]);
    const [loadingHistory, setLoadingHistory] = useState(false);
    const [isRollingBack, setIsRollingBack] = useState(false);
    const [showConfigModal, setShowConfigModal] = useState(false);
    const [selectedConfig, setSelectedConfig] = useState<{ inputs: Record<string, any>; version: number } | null>(null);

    useEffect(() => {
        if (id) {
            // Wait for business units to load before checking
            if (isLoadingBusinessUnits) {
                return;
            }
            
            // Check if business unit is selected (admins can bypass)
            const userIsAdmin = isAdmin || (user?.roles || []).some(role => role.toLowerCase() === 'admin');
            if (!userIsAdmin && (!activeBusinessUnit || !hasBusinessUnitAccess)) {
                setShowBusinessUnitWarning(true);
                return;
            }
            fetchDeployment();
            fetchDeploymentHistory();
        }
    }, [id, activeBusinessUnit, hasBusinessUnitAccess, isAdmin, isLoadingBusinessUnits]);
    
    const fetchDeploymentHistory = async () => {
        if (!id) return;
        try {
            setLoadingHistory(true);
            const response = await api.deploymentsApi.getDeploymentHistory(id);
            
            // Handle different response formats
            let historyArray: DeploymentHistory[] = [];
            if (response) {
                if (Array.isArray(response)) {
                    // If response is directly an array
                    historyArray = response;
                } else if (response.history && Array.isArray(response.history)) {
                    // If response has a history property
                    historyArray = response.history;
                } else if (response.data && Array.isArray(response.data)) {
                    // If response has a data property
                    historyArray = response.data;
                }
            }
            
            setDeploymentHistory(historyArray);
        } catch (err: any) {
            appLogger.error('Failed to fetch deployment history:', err);
            setDeploymentHistory([]); // Set empty array on error
            // Don't show error to user - history is optional
        } finally {
            setLoadingHistory(false);
        }
    };
    
    // Load plugin manifest when deployment is loaded and we need to show update modal
    useEffect(() => {
        if (deployment && deployment.plugin_id && deployment.version) {
            loadPluginManifest();
        }
    }, [deployment?.plugin_id, deployment?.version]);
    
    const loadPluginManifest = async () => {
        if (!deployment) return;
        try {
            setLoadingManifest(true);
            const versions = await api.pluginsApi.getPluginVersions(deployment.plugin_id);
            const version = versions.find((v: any) => v.version === deployment.version);
            if (version) {
                setPluginManifest(version.manifest);
                // Pre-fill update inputs with current deployment inputs
                if (deployment.inputs) {
                    setUpdateInputs({ ...deployment.inputs });
                }
            }
        } catch (err) {
            appLogger.error('Failed to load plugin manifest:', err);
        } finally {
            setLoadingManifest(false);
        }
    };
    
    // Fetch repository info for microservices
    useEffect(() => {
        if (deployment?.deployment_type === 'microservice' && deployment.github_repo_name) {
            fetchRepositoryInfo();
        }
    }, [deployment?.id, deployment?.deployment_type, deployment?.github_repo_name]);
    
    const fetchRepositoryInfo = async () => {
        if (!deployment?.id) return;
        try {
            setLoadingRepo(true);
            const info = await api.deploymentsApi.getRepositoryInfo(deployment.id);
            setRepositoryInfo(info);
        } catch (err: any) {
            // Repository might not be created yet, that's okay
            if (err.message && !err.message.includes('not yet created')) {
                appLogger.error('Failed to fetch repository info:', err);
            }
        } finally {
            setLoadingRepo(false);
        }
    };
    
    // Auto-poll when deployment is provisioning (separate from retry polling)
    useEffect(() => {
        // Poll for updates when status is provisioning or deleting
        if (!deployment || (deployment.status !== 'provisioning' && deployment.status !== 'deleting') || isRetrying) {
            // Clear auto-polling if status is not provisioning/deleting or if retry is active
            if (autoPollInterval) {
                clearInterval(autoPollInterval);
                setAutoPollInterval(null);
            }
            return;
        }
        
        // Start polling every 2 seconds for provisioning/deleting deployments
        const interval = setInterval(async () => {
            try {
                const updated = await api.getDeployment(deployment.id);
                setDeployment(updated);
                
                // Stop polling if deployment is no longer provisioning or deleting
                if (updated.status !== 'provisioning' && updated.status !== 'deleting') {
                    clearInterval(interval);
                    setAutoPollInterval(null);
                }
            } catch (err) {
                // Continue polling on error, but log it
                appLogger.error('Error polling deployment status:', err);
            }
        }, 2000);
        
        setAutoPollInterval(interval);
        
        // Cleanup on unmount or when dependencies change
        return () => {
            clearInterval(interval);
        };
    }, [deployment?.id, deployment?.status, isRetrying]);
    
    // Cleanup all polling intervals on unmount
    useEffect(() => {
        return () => {
            if (pollInterval) {
                clearInterval(pollInterval);
            }
            if (autoPollInterval) {
                clearInterval(autoPollInterval);
            }
        };
    }, [pollInterval, autoPollInterval]);

    const fetchDeployment = async () => {
        try {
            const data = await api.getDeployment(id!);
            setDeployment(data);
        } catch (err: any) {
            setError(err.message || 'Failed to load deployment');
        } finally {
            setLoading(false);
        }
    };

    const handleDelete = async () => {
        setIsDeleting(true);
        try {
            const result = await api.deleteDeployment(deployment!.id);
            // Success - deletion task has been initiated
            // Update deployment status to deleting immediately
            setDeployment({
                ...deployment!,
                status: 'deleting'
            });
            addNotification('info', 'Deletion started. The deployment will be removed once the infrastructure is destroyed.');
            setShowDeleteModal(false);
            
            // Poll for status updates (similar to provisioning)
            const interval = setInterval(async () => {
                try {
                    const updated = await api.getDeployment(deployment!.id);
                    setDeployment(updated);
                    
                    // Stop polling if deployment is deleted or failed
                    if (updated.status === 'deleted' || updated.status === 'failed') {
                        clearInterval(interval);
                        setIsDeleting(false);
                        if (updated.status === 'deleted') {
                            addNotification('success', 'Deployment deleted successfully');
                        } else {
                            addNotification('error', 'Deployment deletion failed');
                        }
                    }
                } catch (err: any) {
                    appLogger.error('Error polling deployment status:', err);
                    clearInterval(interval);
                    setIsDeleting(false);
                }
            }, 2000); // Poll every 2 seconds
            
            setPollInterval(interval);
        } catch (err: any) {
            appLogger.error('Delete deployment error:', err);
            addNotification('error', err.message || 'Failed to delete deployment');
            setIsDeleting(false);
            setShowDeleteModal(false);
        }
    };

    const handleRetry = async () => {
        if (!deployment) return;
        
        setIsRetrying(true);
        try {
            // Retry the same deployment/job
            await api.retryDeployment(deployment.id);
            
            addNotification('success', 'Deployment retry initiated. Refreshing status...');
            
            // Update deployment status to provisioning
            setDeployment({
                ...deployment,
                status: 'provisioning'
            });
            
            // Poll for updates every 2 seconds
            const interval = setInterval(async () => {
                try {
                    const updated = await api.getDeployment(deployment.id);
                    setDeployment(updated);
                    
                    // Stop polling if deployment is no longer provisioning
                    if (updated.status !== 'provisioning' && updated.status !== 'failed' && updated.status !== 'deleting') {
                        clearInterval(interval);
                        setPollInterval(null);
                        setIsRetrying(false);
                        addNotification('success', 'Deployment status updated');
                    } else if (updated.status === 'failed') {
                        clearInterval(interval);
                        setPollInterval(null);
                        setIsRetrying(false);
                    }
                } catch (err) {
                    // Continue polling on error
                    appLogger.error('Error polling deployment status:', err);
                }
            }, 2000);
            
            setPollInterval(interval);
            
            // Clean up polling after 5 minutes max
            setTimeout(() => {
                clearInterval(interval);
                setPollInterval(null);
                setIsRetrying(false);
            }, 5 * 60 * 1000);
            
        } catch (err: any) {
            addNotification('error', err.message || 'Failed to retry deployment');
            setIsRetrying(false);
        }
    };

    const handleUpdate = async () => {
        if (!deployment) return;
        
        setIsUpdating(true);
        try {
            await api.deploymentsApi.updateDeployment(deployment.id, {
                inputs: updateInputs
            });
            
            addNotification('success', 'Deployment update initiated. The deployment will be updated with new configuration.');
            setShowUpdateModal(false);
            
            // Refresh deployment to show updating status
            const updated = await api.getDeployment(deployment.id);
            setDeployment(updated);
            
            // Poll for update completion
            const interval = setInterval(async () => {
                try {
                    const updated = await api.getDeployment(deployment.id);
                    setDeployment(updated);
                    
                    // Stop polling if update is complete (succeeded or failed)
                    if (updated.update_status === 'update_succeeded' || updated.update_status === 'update_failed') {
                        clearInterval(interval);
                        if (updated.update_status === 'update_succeeded') {
                            addNotification('success', 'Deployment updated successfully');
                        } else {
                            addNotification('error', `Deployment update failed: ${updated.last_update_error || 'Unknown error'}`);
                        }
                    }
                } catch (err) {
                    appLogger.error('Error polling deployment update status:', err);
                }
            }, 2000);
            
            // Clean up polling after 5 minutes max
            setTimeout(() => {
                clearInterval(interval);
            }, 5 * 60 * 1000);
            
        } catch (err: any) {
            addNotification('error', err.message || 'Failed to update deployment');
        } finally {
            setIsUpdating(false);
        }
    };

    const handleInputChange = (key: string, value: any) => {
        setUpdateInputs({
            ...updateInputs,
            [key]: value
        });
    };

    // Helper function to format time ago
    const getTimeAgo = (date: Date): string => {
        const now = new Date();
        const diffInSeconds = Math.floor((now.getTime() - date.getTime()) / 1000);
        
        if (diffInSeconds < 60) return 'Just now';
        if (diffInSeconds < 3600) return `${Math.floor(diffInSeconds / 60)} minutes ago`;
        if (diffInSeconds < 86400) return `${Math.floor(diffInSeconds / 3600)} hours ago`;
        if (diffInSeconds < 604800) return `${Math.floor(diffInSeconds / 86400)} days ago`;
        if (diffInSeconds < 2592000) return `${Math.floor(diffInSeconds / 604800)} weeks ago`;
        return `${Math.floor(diffInSeconds / 2592000)} months ago`;
    };

    const handleRollback = async (versionNumber: number) => {
        if (!deployment || !window.confirm(`Are you sure you want to rollback to version ${versionNumber}? This will update the deployment with the configuration from that version.`)) {
            return;
        }
        
        setIsRollingBack(true);
        try {
            await api.deploymentsApi.rollbackDeployment(deployment.id, versionNumber);
            
            addNotification('success', `Rollback to version ${versionNumber} initiated. The deployment will be updated with the previous configuration.`);
            
            // Refresh deployment to show updating status
            const updated = await api.getDeployment(deployment.id);
            setDeployment(updated);
            
            // Refresh history
            await fetchDeploymentHistory();
            
            // Poll for update completion
            const interval = setInterval(async () => {
                try {
                    const updated = await api.getDeployment(deployment.id);
                    setDeployment(updated);
                    
                    // Stop polling if update is complete (succeeded or failed)
                    if (updated.update_status === 'update_succeeded' || updated.update_status === 'update_failed') {
                        clearInterval(interval);
                        await fetchDeploymentHistory(); // Refresh history after update
                        if (updated.update_status === 'update_succeeded') {
                            addNotification('success', 'Deployment rollback completed successfully');
                        } else {
                            addNotification('error', `Deployment rollback failed: ${updated.last_update_error || 'Unknown error'}`);
                        }
                    }
                } catch (err) {
                    appLogger.error('Error polling deployment rollback status:', err);
                }
            }, 2000);
            
            // Clean up polling after 5 minutes max
            setTimeout(() => {
                clearInterval(interval);
            }, 5 * 60 * 1000);
            
        } catch (err: any) {
            addNotification('error', err.message || 'Failed to rollback deployment');
        } finally {
            setIsRollingBack(false);
        }
    };


    const copyToClipboard = (text: string, field: string) => {
        navigator.clipboard.writeText(text);
        setCopiedField(field);
        setTimeout(() => setCopiedField(null), 2000);
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center h-64">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-orange-600"></div>
            </div>
        );
    }

    if (error || !deployment) {
        return (
            <div className="max-w-5xl mx-auto">
                <Link to="/deployments" className="flex items-center gap-2 text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white transition-colors mb-4">
                    <ArrowLeft className="w-4 h-4" /> Back to Deployments
                </Link>
                <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-600 dark:text-red-400 px-4 py-3 rounded-lg">
                    {error || 'Deployment not found'}
                </div>
            </div>
        );
    }

    return (
        <div className="max-w-6xl mx-auto space-y-6">
            <Link to="/deployments" className="flex items-center gap-2 text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white transition-colors">
                <ArrowLeft className="w-4 h-4" /> Back to Deployments
            </Link>

            {/* Header Card and History Card in one row */}
            <div className="grid grid-cols-1 lg:grid-cols-10 gap-6">
                {/* Header Card - 70% (7 columns) */}
                <div className="lg:col-span-7 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-2xl p-6 shadow-xl transition-colors">
                    <div className="flex items-start gap-4 mb-6">
                        <div className="w-14 h-14 rounded-lg bg-gradient-to-br from-orange-500 to-orange-600 flex items-center justify-center shadow-lg shadow-orange-500/30 flex-shrink-0">
                            <Package className="w-7 h-7 text-white" />
                        </div>
                        <div className="flex-1">
                            <div className="flex items-center justify-between mb-3">
                                <div className="flex items-center gap-3">
                                    <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
                                        {deployment.name || 'Unnamed Deployment'}
                                    </h1>
                                    {deployment.environment && (
                                        <EnvironmentBadge environment={deployment.environment} showIcon={false} />
                                    )}
                                </div>
                                {/* Status Badge in top corner */}
                                <div className="flex items-center gap-2">
                                    <StatusBadge status={deployment.status} size="lg" />
                                    {deployment.update_status === 'update_failed' && (
                                        <div className="relative group">
                                            <AlertCircle className="w-5 h-5 text-yellow-500" />
                                            {deployment.last_update_error && (
                                                <div className="absolute right-0 top-full mt-2 w-64 p-2 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg text-xs text-yellow-800 dark:text-yellow-200 opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity z-10">
                                                    Update failed: {deployment.last_update_error}
                                                </div>
                                            )}
                                        </div>
                                    )}
                                    {deployment.update_status === 'updating' && (
                                        <Loader2 className="w-5 h-5 text-blue-500 animate-spin" />
                                    )}
                                    {deployment.update_status === 'update_succeeded' && (
                                        <Check className="w-5 h-5 text-green-500" />
                                    )}
                                </div>
                            </div>
                            
                            {/* Metadata row */}
                            <div className="flex flex-wrap items-center gap-3 text-sm text-gray-600 dark:text-gray-400 mb-4">
                                {deployment.cloud_provider && (
                                    <span className="font-medium">{deployment.cloud_provider.toUpperCase()}</span>
                                )}
                                {deployment.version && (
                                    <span className="text-gray-500 dark:text-gray-500">v{deployment.version}</span>
                                )}
                                {deployment.region && (
                                    <span className="text-gray-500 dark:text-gray-500">{deployment.region}</span>
                                )}
                                {deployment.stack_name && (
                                    <span className="text-gray-500 dark:text-gray-500 font-mono text-xs">{deployment.stack_name}</span>
                                )}
                                {deployment.job_id && (
                                    <>
                                        <span className="text-gray-400 dark:text-gray-500">•</span>
                                        <span className="text-gray-500 dark:text-gray-500 font-mono text-xs">
                                            Job ID: {deployment.job_id}
                                        </span>
                                    </>
                                )}
                            </div>
                            
                            {/* Tags Section */}
                            {deployment.tags && deployment.tags.length > 0 && (
                                <div className="flex flex-wrap gap-2 mb-4">
                                    {deployment.tags.map((tag, idx) => (
                                        <span
                                            key={idx}
                                            className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 border border-gray-200 dark:border-gray-700 text-xs"
                                        >
                                            <Tag className="w-3 h-3" />
                                            <span className="font-medium">{tag.key}:</span>
                                            <span>{tag.value}</span>
                                        </span>
                                    ))}
                                </div>
                            )}
                        </div>
                    </div>
                    
                    {/* Actions Row */}
                    <div className="flex items-center justify-end pt-4 border-t border-gray-200 dark:border-gray-800">
                        {/* Action Buttons */}
                        <div className="flex items-center gap-3">
                            {deployment.status === 'active' && deployment.deployment_type === 'infrastructure' && (
                                <button
                                    onClick={() => setShowUpdateModal(true)}
                                    disabled={deployment.update_status === 'updating'}
                                    className="flex items-center gap-2 px-4 py-2 bg-blue-500/10 text-blue-600 dark:text-blue-400 border border-blue-500/20 rounded-lg hover:bg-blue-500/20 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed font-medium text-sm"
                                >
                                    {deployment.update_status === 'updating' ? (
                                        <>
                                            <Loader2 className="w-4 h-4 animate-spin" />
                                            Updating...
                                        </>
                                    ) : (
                                        <>
                                            <Edit2 className="w-4 h-4" />
                                            Update Deployment
                                        </>
                                    )}
                                </button>
                            )}
                            {(deployment.status === 'failed' || isRetrying) && (
                                <button
                                    onClick={handleRetry}
                                    disabled={isRetrying || deployment.status === 'provisioning'}
                                    className="flex items-center gap-2 px-4 py-2 bg-orange-500/10 text-orange-600 dark:text-orange-400 border border-orange-500/20 rounded-lg hover:bg-orange-500/20 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed font-medium text-sm"
                                >
                                    {isRetrying || deployment.status === 'provisioning' ? (
                                        <>
                                            <Loader2 className="w-4 h-4 animate-spin" />
                                            Retrying...
                                        </>
                                    ) : (
                                        <>
                                            <RotateCw className="w-4 h-4" />
                                            Retry
                                        </>
                                    )}
                                </button>
                            )}
                            {/* Hide delete button if deployment is already deleted or deleting */}
                            {deployment.status !== 'deleted' && deployment.status !== 'deleting' && (
                                <button
                                    onClick={() => setShowDeleteModal(true)}
                                    disabled={isDeleting || isRetrying || deployment.status === 'provisioning'}
                                    className="flex items-center gap-2 px-4 py-2 bg-red-500/10 text-red-600 dark:text-red-400 border border-red-500/20 rounded-lg hover:bg-red-500/20 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed font-medium text-sm"
                                >
                                    <Trash2 className="w-4 h-4" />
                                    Delete
                                </button>
                            )}
                        </div>
                    </div>
                </div>

                {/* Deployment History Card - 30% (3 columns) */}
                {deployment && (
                    <div className="lg:col-span-3 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-2xl p-6 transition-colors">
                        <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
                            <Clock className="w-5 h-5 text-gray-600 dark:text-gray-400" />
                            Deployment History
                        </h3>
                        {loadingHistory ? (
                            <div className="flex items-center justify-center py-8">
                                <Loader2 className="w-6 h-6 text-orange-600 dark:text-orange-400 animate-spin" />
                            </div>
                        ) : deploymentHistory.length === 0 ? (
                            <div className="text-center py-8 text-gray-500 dark:text-gray-400">
                                <History className="w-12 h-12 mx-auto mb-2 opacity-50" />
                                <p className="text-sm">No deployment history available</p>
                            </div>
                        ) : (
                            <div className="space-y-4 max-h-[calc(100vh-300px)] overflow-y-auto">
                                {deploymentHistory.map((entry, index) => {
                                    const isCurrentVersion = index === 0 && deployment.status === 'active';
                                    const timeAgo = entry.created_at ? getTimeAgo(new Date(entry.created_at)) : '';
                                    // Only show current version as active, others as stopped (superseded)
                                    const displayStatus = isCurrentVersion ? 'active' : 'stopped';
                                    
                                    return (
                                        <div
                                            key={entry.id}
                                            className={`border-l-2 pl-4 pb-4 ${
                                                isCurrentVersion
                                                    ? 'border-green-500'
                                                    : 'border-gray-300 dark:border-gray-600'
                                            }`}
                                        >
                                            <div className="flex items-start justify-between gap-3 mb-2">
                                                <div className="flex-1 min-w-0">
                                                    <div className="flex items-center gap-2 mb-2">
                                                        <span className="text-sm font-semibold text-gray-900 dark:text-white">
                                                            v{entry.version_number}
                                                        </span>
                                                        <StatusBadge status={displayStatus} size="sm" />
                                                    </div>
                                                    {entry.created_by && (
                                                        <p className="text-xs text-gray-600 dark:text-gray-400 mb-1">
                                                            Deployed by: <span className="font-medium">{entry.created_by}</span>
                                                        </p>
                                                    )}
                                                    {timeAgo && (
                                                        <p className="text-xs text-gray-500 dark:text-gray-500">
                                                            {timeAgo}
                                                        </p>
                                                    )}
                                                </div>
                                            </div>
                                            {entry.inputs && Object.keys(entry.inputs).length > 0 && (
                                                <button
                                                    onClick={() => {
                                                        setSelectedConfig({ inputs: entry.inputs, version: entry.version_number });
                                                        setShowConfigModal(true);
                                                    }}
                                                    className="text-xs text-orange-600 dark:text-orange-400 hover:text-orange-700 dark:hover:text-orange-300 font-medium flex items-center gap-1 transition-colors"
                                                >
                                                    View Config <span className="text-orange-600 dark:text-orange-400">→</span>
                                                </button>
                                            )}
                                            {!isCurrentVersion && deployment.status === 'active' && deployment.deployment_type === 'infrastructure' && (
                                                <button
                                                    onClick={() => handleRollback(entry.version_number)}
                                                    disabled={isRollingBack || deployment.update_status === 'updating'}
                                                    className="mt-2 text-xs text-purple-600 dark:text-purple-400 hover:text-purple-700 dark:hover:text-purple-300 font-medium disabled:opacity-50 disabled:cursor-not-allowed"
                                                >
                                                    Rollback
                                                </button>
                                            )}
                                        </div>
                                    );
                                })}
                            </div>
                        )}
                    </div>
                )}
            </div>

            {/* Microservice-specific sections */}
            {deployment.deployment_type === 'microservice' && (
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    {/* CI/CD Status Card */}
                    {deployment.github_repo_name && (
                        <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-2xl p-6 transition-colors">
                            <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
                                <Code className="w-5 h-5 text-purple-600 dark:text-purple-400" />
                                CI/CD Status
                            </h3>
                            <CICDStatus 
                                deploymentId={deployment.id}
                                autoRefresh={true}
                                refreshInterval={15000}
                            />
                        </div>
                    )}
                    
                    {/* Repository Info Card */}
                    {deployment.github_repo_name && (
                        <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-2xl p-6 transition-colors">
                            <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
                                <Github className="w-5 h-5 text-gray-600 dark:text-gray-400" />
                                Repository
                            </h3>
                            {loadingRepo ? (
                                <div className="flex items-center justify-center py-8">
                                    <Loader2 className="w-5 h-5 animate-spin text-gray-400" />
                                </div>
                            ) : repositoryInfo ? (
                                <div className="space-y-3">
                                    <div>
                                        <span className="text-xs text-gray-500 dark:text-gray-400 uppercase font-semibold tracking-wide mb-1 block">Repository Name</span>
                                        <div className="flex items-center gap-2 group">
                                            <a
                                                href={repositoryInfo.html_url}
                                                target="_blank"
                                                rel="noopener noreferrer"
                                                className="text-gray-900 dark:text-gray-100 font-medium hover:text-orange-600 dark:hover:text-orange-400 transition-colors flex items-center gap-2"
                                            >
                                                {repositoryInfo.full_name}
                                                <ExternalLink className="w-4 h-4" />
                                            </a>
                                        </div>
                                    </div>
                                    <div>
                                        <span className="text-xs text-gray-500 dark:text-gray-400 uppercase font-semibold tracking-wide mb-1 block">Clone URL (HTTPS)</span>
                                        <div className="flex items-center gap-2 group">
                                            <span className="text-gray-900 dark:text-gray-100 font-mono text-sm break-all flex-1">
                                                {repositoryInfo.clone_url}
                                            </span>
                                            <button
                                                onClick={() => copyToClipboard(repositoryInfo.clone_url, 'clone_url')}
                                                className="opacity-0 group-hover:opacity-100 transition-opacity p-1.5 hover:bg-gray-100 dark:hover:bg-gray-800 rounded"
                                                title="Copy to clipboard"
                                            >
                                                {copiedField === 'clone_url' ? (
                                                    <Check className="w-4 h-4 text-green-600" />
                                                ) : (
                                                    <Copy className="w-4 h-4 text-gray-400" />
                                                )}
                                            </button>
                                        </div>
                                    </div>
                                    {repositoryInfo.ssh_url && (
                                        <div>
                                            <span className="text-xs text-gray-500 dark:text-gray-400 uppercase font-semibold tracking-wide mb-1 block">Clone URL (SSH)</span>
                                            <div className="flex items-center gap-2 group">
                                                <span className="text-gray-900 dark:text-gray-100 font-mono text-sm break-all flex-1">
                                                    {repositoryInfo.ssh_url}
                                                </span>
                                                <button
                                                    onClick={() => copyToClipboard(repositoryInfo.ssh_url, 'ssh_url')}
                                                    className="opacity-0 group-hover:opacity-100 transition-opacity p-1.5 hover:bg-gray-100 dark:hover:bg-gray-800 rounded"
                                                    title="Copy to clipboard"
                                                >
                                                    {copiedField === 'ssh_url' ? (
                                                        <Check className="w-4 h-4 text-green-600" />
                                                    ) : (
                                                        <Copy className="w-4 h-4 text-gray-400" />
                                                    )}
                                                </button>
                                            </div>
                                        </div>
                                    )}
                                    <div>
                                        <span className="text-xs text-gray-500 dark:text-gray-400 uppercase font-semibold tracking-wide mb-1 block">Default Branch</span>
                                        <span className="text-gray-900 dark:text-gray-100 font-mono text-sm">
                                            {repositoryInfo.default_branch}
                                        </span>
                                    </div>
                                    {repositoryInfo.description && (
                                        <div>
                                            <span className="text-xs text-gray-500 dark:text-gray-400 uppercase font-semibold tracking-wide mb-1 block">Description</span>
                                            <span className="text-gray-900 dark:text-gray-100 text-sm">
                                                {repositoryInfo.description}
                                            </span>
                                        </div>
                                    )}
                                </div>
                            ) : (
                                <div className="text-sm text-gray-500 dark:text-gray-400">
                                    Repository information not available yet.
                                </div>
                            )}
                        </div>
                    )}
                </div>
            )}


            {/* Configuration Inputs and Deployment Outputs */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Inputs Card */}
                {deployment.inputs && Object.keys(deployment.inputs).length > 0 && (
                    <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-2xl p-6 transition-colors">
                        <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
                            <div className="w-1 h-6 bg-orange-600 rounded"></div>
                            Configuration Inputs
                        </h3>
                        <div className="space-y-4">
                            {Object.entries(deployment.inputs).map(([key, value]) => (
                                <div key={key} className="flex flex-col">
                                    <label className="text-xs text-gray-500 dark:text-gray-400 uppercase font-semibold tracking-wide mb-2">
                                        {key.replace(/_/g, ' ')}
                                    </label>
                                    <input
                                        type="text"
                                        value={typeof value === 'object' ? JSON.stringify(value) : String(value)}
                                        readOnly
                                        className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg text-gray-900 dark:text-gray-100 font-mono text-sm"
                                    />
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {/* Outputs Card */}
                {deployment.outputs && Object.keys(deployment.outputs).length > 0 && (
                    <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-2xl p-6 transition-colors">
                        <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
                            <div className="w-1 h-6 bg-green-600 rounded"></div>
                            Deployment Outputs
                        </h3>
                        <div className="space-y-3">
                            {Object.entries(deployment.outputs).map(([key, value]) => (
                                <div key={key} className="flex flex-col border-b border-gray-100 dark:border-gray-800 pb-3 last:border-0 last:pb-0">
                                    <span className="text-xs text-gray-500 dark:text-gray-400 uppercase font-semibold tracking-wide mb-1">{key}</span>
                                    <div className="flex items-center gap-2 group">
                                        <span className="text-gray-900 dark:text-gray-100 font-mono text-sm break-all flex-1">
                                            {typeof value === 'object' ? JSON.stringify(value, null, 2) : String(value)}
                                        </span>
                                        <button
                                            onClick={() => copyToClipboard(typeof value === 'object' ? JSON.stringify(value) : String(value), key)}
                                            className="opacity-0 group-hover:opacity-100 transition-opacity p-1.5 hover:bg-gray-100 dark:hover:bg-gray-800 rounded"
                                            title="Copy to clipboard"
                                        >
                                            {copiedField === key ? (
                                                <Check className="w-4 h-4 text-green-600" />
                                            ) : (
                                                <Copy className="w-4 h-4 text-gray-400" />
                                            )}
                                        </button>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                )}
            </div>

            {/* Update Deployment Modal */}
            {showUpdateModal && deployment && (
                <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4 overflow-y-auto">
                    <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-2xl p-6 max-w-3xl w-full shadow-2xl my-8">
                        <div className="flex items-center justify-between mb-6">
                            <h2 className="text-2xl font-bold text-gray-900 dark:text-white">Update Deployment</h2>
                            <button
                                onClick={() => setShowUpdateModal(false)}
                                className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                            >
                                <X className="w-6 h-6" />
                            </button>
                        </div>
                        
                        {loadingManifest ? (
                            <div className="flex items-center justify-center py-8">
                                <Loader2 className="w-8 h-8 text-orange-600 dark:text-orange-400 animate-spin" />
                            </div>
                        ) : pluginManifest?.inputs?.properties ? (
                            <div className="space-y-4 max-h-[60vh] overflow-y-auto pr-2">
                                {Object.entries(pluginManifest.inputs.properties).map(([key, prop]: [string, any]) => {
                                    const isRequired = pluginManifest.inputs.required?.includes(key);
                                    const currentValue = updateInputs[key] ?? prop.default ?? '';
                                    
                                    return (
                                        <div key={key} className="space-y-2">
                                            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                                                {prop.title || key.replace(/_/g, ' ')}
                                                {isRequired && <span className="text-red-500 ml-1">*</span>}
                                            </label>
                                            
                                            {prop.type === 'boolean' ? (
                                                <label className="flex items-center gap-2 cursor-pointer">
                                                    <input
                                                        type="checkbox"
                                                        checked={updateInputs[key] ?? prop.default ?? false}
                                                        onChange={(e) => handleInputChange(key, e.target.checked)}
                                                        className="w-4 h-4 text-orange-600 border-gray-300 rounded focus:ring-orange-500"
                                                    />
                                                    <span className="text-sm text-gray-600 dark:text-gray-400">
                                                        {prop.description || `Enable ${key.replace(/_/g, ' ')}`}
                                                    </span>
                                                </label>
                                            ) : prop.type === 'integer' || prop.type === 'number' ? (
                                                <input
                                                    type="number"
                                                    value={currentValue}
                                                    onChange={(e) => handleInputChange(key, parseInt(e.target.value) || 0)}
                                                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-orange-500 focus:border-orange-500"
                                                    placeholder={prop.default?.toString()}
                                                />
                                            ) : prop.type === 'string' && prop.enum ? (
                                                <select
                                                    value={currentValue}
                                                    onChange={(e) => handleInputChange(key, e.target.value)}
                                                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-orange-500 focus:border-orange-500"
                                                >
                                                    {prop.enum.map((option: string) => (
                                                        <option key={option} value={option}>{option}</option>
                                                    ))}
                                                </select>
                                            ) : (
                                                <input
                                                    type="text"
                                                    value={currentValue}
                                                    onChange={(e) => handleInputChange(key, e.target.value)}
                                                    placeholder={prop.default?.toString()}
                                                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-orange-500 focus:border-orange-500"
                                                />
                                            )}
                                            
                                            {prop.description && (
                                                <p className="text-xs text-gray-500 dark:text-gray-400">
                                                    {prop.description}
                                                </p>
                                            )}
                                        </div>
                                    );
                                })}
                            </div>
                        ) : (
                            <div className="text-center py-8 text-gray-500 dark:text-gray-400">
                                <AlertCircle className="w-12 h-12 mx-auto mb-4 text-gray-400" />
                                <p>Unable to load plugin manifest. Please try again later.</p>
                            </div>
                        )}
                        
                        <div className="flex justify-end gap-3 mt-6 pt-6 border-t border-gray-200 dark:border-gray-800">
                            <button
                                onClick={() => setShowUpdateModal(false)}
                                disabled={isUpdating}
                                className="px-4 py-2 border border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors text-sm font-medium disabled:opacity-50"
                            >
                                Cancel
                            </button>
                            <button
                                onClick={handleUpdate}
                                disabled={isUpdating || loadingManifest}
                                className="px-4 py-2 bg-blue-500/10 text-blue-600 dark:text-blue-400 border border-blue-500/20 rounded-lg hover:bg-blue-500/20 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed font-medium text-sm flex items-center gap-2"
                            >
                                {isUpdating ? (
                                    <>
                                        <Loader2 className="w-4 h-4 animate-spin" />
                                        Updating...
                                    </>
                                ) : (
                                    <>
                                        <Edit2 className="w-4 h-4" />
                                        Update Deployment
                                    </>
                                )}
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Configuration View Modal */}
            {showConfigModal && selectedConfig && (
                <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
                    <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-2xl p-6 max-w-3xl w-full shadow-2xl max-h-[90vh] flex flex-col">
                        <div className="flex items-center justify-between mb-6">
                            <div>
                                <h2 className="text-2xl font-bold text-gray-900 dark:text-white">Configuration</h2>
                                <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">Version {selectedConfig.version}</p>
                            </div>
                            <button
                                onClick={() => {
                                    setShowConfigModal(false);
                                    setSelectedConfig(null);
                                }}
                                className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
                            >
                                <X className="w-6 h-6" />
                            </button>
                        </div>
                        
                        <div className="flex-1 overflow-y-auto pr-2">
                            <div className="space-y-4">
                                {Object.entries(selectedConfig.inputs).map(([key, value]) => (
                                    <div key={key} className="flex flex-col">
                                        <label className="text-xs text-gray-500 dark:text-gray-400 uppercase font-semibold tracking-wide mb-2">
                                            {key.replace(/_/g, ' ')}
                                        </label>
                                        <div className="flex items-center gap-2 group">
                                            <input
                                                type="text"
                                                value={typeof value === 'object' ? JSON.stringify(value, null, 2) : String(value)}
                                                readOnly
                                                className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg text-gray-900 dark:text-gray-100 font-mono text-sm"
                                            />
                                            <button
                                                onClick={() => {
                                                    const valueStr = typeof value === 'object' ? JSON.stringify(value) : String(value);
                                                    navigator.clipboard.writeText(valueStr);
                                                    addNotification('success', `${key} copied to clipboard`);
                                                }}
                                                className="opacity-0 group-hover:opacity-100 transition-opacity p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded"
                                                title="Copy to clipboard"
                                            >
                                                <Copy className="w-4 h-4 text-gray-400" />
                                            </button>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                        
                        <div className="flex justify-end gap-3 mt-6 pt-6 border-t border-gray-200 dark:border-gray-800">
                            <button
                                onClick={() => {
                                    const configStr = JSON.stringify(selectedConfig.inputs, null, 2);
                                    navigator.clipboard.writeText(configStr);
                                    addNotification('success', 'Full configuration copied to clipboard');
                                }}
                                className="px-4 py-2 bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors text-sm font-medium flex items-center gap-2"
                            >
                                <Copy className="w-4 h-4" />
                                Copy All
                            </button>
                            <button
                                onClick={() => {
                                    setShowConfigModal(false);
                                    setSelectedConfig(null);
                                }}
                                className="px-4 py-2 bg-orange-500/10 text-orange-600 dark:text-orange-400 border border-orange-500/20 rounded-lg hover:bg-orange-500/20 transition-colors text-sm font-medium"
                            >
                                Close
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Delete Confirmation Modal */}
            {showDeleteModal && (
                <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
                    <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-2xl p-6 max-w-md w-full shadow-2xl">
                        <div className="flex items-start gap-4 mb-4">
                            <div className="w-12 h-12 rounded-full bg-red-500/10 flex items-center justify-center flex-shrink-0">
                                <AlertCircle className="w-6 h-6 text-red-600 dark:text-red-400" />
                            </div>
                            <div>
                                <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-1">Delete Deployment</h3>
                                <p className="text-sm text-gray-500 dark:text-gray-400">
                                    This will destroy all infrastructure resources and delete the deployment record. This action cannot be undone.
                                </p>
                            </div>
                        </div>

                        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-3 mb-4">
                            <p className="text-sm text-red-600 dark:text-red-400 font-medium">
                                ⚠️ Warning: All cloud resources will be permanently deleted
                            </p>
                        </div>

                        <div className="flex gap-3">
                            <button
                                onClick={() => setShowDeleteModal(false)}
                                disabled={isDeleting}
                                className="flex-1 px-4 py-2 border border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors text-sm font-medium disabled:opacity-50"
                            >
                                Cancel
                            </button>
                            <button
                                onClick={handleDelete}
                                disabled={isDeleting}
                                className="flex-1 px-4 py-2 bg-red-500/10 text-red-600 dark:text-red-400 border border-red-500/20 rounded-lg hover:bg-red-500/20 transition-all duration-200 text-sm font-medium disabled:opacity-50 flex items-center justify-center gap-2"
                            >
                                {isDeleting ? (
                                    <>
                                        <Loader2 className="w-4 h-4 animate-spin" />
                                        Deleting...
                                    </>
                                ) : (
                                    <>
                                        <Trash2 className="w-4 h-4" />
                                        Delete
                                    </>
                                )}
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Business Unit Warning Modal */}
            <BusinessUnitWarningModal
                isOpen={showBusinessUnitWarning}
                onClose={() => {
                    setShowBusinessUnitWarning(false);
                    navigate('/');
                }}
                onSelectBusinessUnit={() => {
                    const selector = document.querySelector('[data-business-unit-selector]');
                    if (selector) {
                        (selector as HTMLElement).click();
                    }
                }}
                action="view this deployment"
            />
        </div>
    );
};