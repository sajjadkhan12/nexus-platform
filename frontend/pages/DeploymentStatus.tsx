import React, { useEffect, useState } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { Terminal, ArrowLeft, Package, Tag, Globe, Clock, Trash2, ExternalLink, Copy, Check, AlertCircle, Loader2 } from 'lucide-react';
import api from '../services/api';
import { StatusBadge } from '../components/Badges';
import { useNotification } from '../contexts/NotificationContext';

import { Deployment } from '../types';

export const DeploymentStatusPage: React.FC = () => {
    const { id } = useParams<{ id: string }>();
    const navigate = useNavigate();
    const { addNotification } = useNotification();
    const [deployment, setDeployment] = useState<Deployment | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [copiedField, setCopiedField] = useState<string | null>(null);
    const [showDeleteModal, setShowDeleteModal] = useState(false);
    const [isDeleting, setIsDeleting] = useState(false);

    useEffect(() => {
        if (id) {
            fetchDeployment();
        }
    }, [id]);

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
            addNotification('info', 'Deletion started. You will be notified when complete.');
            setShowDeleteModal(false);
            // Navigate after a short delay to allow notification to show
            setTimeout(() => {
                navigate('/catalog');
            }, 500);
        } catch (err: any) {
            console.error('Delete deployment error:', err);
            addNotification('error', err.message || 'Failed to delete deployment');
            setIsDeleting(false);
            setShowDeleteModal(false);
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
                <Link to="/catalog" className="flex items-center gap-2 text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white transition-colors mb-4">
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
            <Link to="/catalog" className="flex items-center gap-2 text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white transition-colors">
                <ArrowLeft className="w-4 h-4" /> Back to Deployments
            </Link>

            {/* Header Card */}
            <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-2xl p-8 shadow-xl transition-colors">
                <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
                    <div className="flex items-start gap-4">
                        <div className="w-16 h-16 rounded-xl bg-gradient-to-br from-orange-500 to-orange-600 flex items-center justify-center shadow-lg shadow-orange-500/30 flex-shrink-0">
                            <Package className="w-8 h-8 text-white" />
                        </div>
                        <div>
                            <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">{deployment.name}</h1>
                            <div className="flex flex-wrap items-center gap-3 text-sm text-gray-500 dark:text-gray-400">
                                <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-orange-500/10 text-orange-600 dark:text-orange-400 border border-orange-500/20 font-medium">
                                    <Package className="w-3.5 h-3.5" />
                                    {deployment.plugin_id}
                                </span>
                                {deployment.version && (
                                    <span className="px-2.5 py-1 rounded-md bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 border border-gray-200 dark:border-gray-700 font-mono text-xs">
                                        v{deployment.version}
                                    </span>
                                )}
                                {deployment.cloud_provider && (
                                    <span className="flex items-center gap-1">
                                        <Tag className="w-3.5 h-3.5" />
                                        {deployment.cloud_provider.toUpperCase()}
                                    </span>
                                )}
                                {deployment.region && (
                                    <>
                                        <span>•</span>
                                        <span className="flex items-center gap-1">
                                            <Globe className="w-3.5 h-3.5" />
                                            {deployment.region}
                                        </span>
                                    </>
                                )}
                                {deployment.job_id && (
                                    <>
                                        <span>•</span>
                                        <span className="flex items-center gap-1">
                                            <span className="text-gray-500 dark:text-gray-400">Job ID:</span>
                                            <span className="font-mono text-gray-700 dark:text-gray-300 text-xs">
                                                {deployment.job_id}
                                            </span>
                                        </span>
                                    </>
                                )}
                                {deployment.created_at && (
                                    <>
                                        <span>•</span>
                                        <span className="flex items-center gap-1">
                                            <Clock className="w-3.5 h-3.5" />
                                            {new Date(deployment.created_at).toLocaleString()}
                                        </span>
                                    </>
                                )}
                            </div>
                        </div>
                    </div>
                    <div className="flex flex-col items-end gap-3">
                        <StatusBadge status={deployment.status} size="lg" />
                        {deployment.stack_name && (
                            <span className="text-xs text-gray-500 dark:text-gray-400 font-mono">
                                Stack: {deployment.stack_name}
                            </span>
                        )}
                    </div>
                </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Inputs Card */}
                {deployment.inputs && Object.keys(deployment.inputs).length > 0 && (
                    <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-2xl p-6 transition-colors">
                        <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
                            <Terminal className="w-5 h-5 text-orange-600 dark:text-orange-400" />
                            Configuration Inputs
                        </h3>
                        <div className="space-y-3">
                            {Object.entries(deployment.inputs).map(([key, value]) => (
                                <div key={key} className="flex flex-col border-b border-gray-100 dark:border-gray-800 pb-3 last:border-0 last:pb-0">
                                    <span className="text-xs text-gray-500 dark:text-gray-400 uppercase font-semibold tracking-wide mb-1">{key}</span>
                                    <span className="text-gray-900 dark:text-gray-100 font-mono text-sm break-all">
                                        {typeof value === 'object' ? JSON.stringify(value, null, 2) : String(value)}
                                    </span>
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {/* Outputs Card */}
                {deployment.outputs && Object.keys(deployment.outputs).length > 0 && (
                    <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-2xl p-6 transition-colors">
                        <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
                            <ExternalLink className="w-5 h-5 text-green-600 dark:text-green-400" />
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

            {/* Actions Card */}
            {(deployment.status === 'active' || deployment.status === 'failed' || deployment.status === 'provisioning') && (
                <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-2xl p-6 transition-colors">
                    <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-4">Actions</h3>
                    <div className="flex gap-3">
                        <button
                            onClick={() => setShowDeleteModal(true)}
                            className="flex items-center gap-2 px-4 py-2 bg-red-500/10 text-red-600 dark:text-red-400 border border-red-500/20 rounded-lg hover:bg-red-500/20 transition-colors text-sm font-medium"
                        >
                            <Trash2 className="w-4 h-4" />
                            Delete Deployment
                        </button>
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
                                className="flex-1 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-500 transition-colors text-sm font-medium disabled:opacity-50 flex items-center justify-center gap-2"
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
        </div>
    );
};