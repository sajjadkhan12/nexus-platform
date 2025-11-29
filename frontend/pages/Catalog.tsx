import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Server, ExternalLink, Clock, Globe, Tag } from 'lucide-react';
import api from '../services/api';
import { StatusBadge, PluginBadge } from '../components/Badges';

import { Deployment } from '../types';

export const CatalogPage: React.FC = () => {
    const [deployments, setDeployments] = useState<Deployment[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');

    useEffect(() => {
        fetchDeployments();
    }, []);

    const fetchDeployments = async () => {
        try {
            const data = await api.listDeployments();
            setDeployments(data);
        } catch (err: any) {
            setError(err.message || 'Failed to load deployments');
        } finally {
            setLoading(false);
        }
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center h-64">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
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
                <Link to="/services" className="bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-indigo-500 transition-colors shadow-md shadow-indigo-500/20">
                    New Deployment
                </Link>
            </div>

            {error && (
                <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-600 dark:text-red-400 px-4 py-3 rounded-lg">
                    {error}
                </div>
            )}

            {deployments.length === 0 ? (
                <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-2xl p-12 text-center transition-colors">
                    <div className="w-16 h-16 bg-gray-100 dark:bg-gray-800 rounded-full flex items-center justify-center mx-auto mb-4">
                        <Server className="w-8 h-8 text-gray-400 dark:text-gray-500" />
                    </div>
                    <h3 className="text-xl font-medium text-gray-900 dark:text-white mb-2">No Active Deployments</h3>
                    <p className="text-gray-500 dark:text-gray-400 mb-6 max-w-md mx-auto">You haven't deployed any services yet. Visit the service catalog to get started with your first deployment.</p>
                    <Link to="/services" className="text-indigo-600 dark:text-indigo-400 hover:text-indigo-500 dark:hover:text-indigo-300 font-medium">Browse Catalog &rarr;</Link>
                </div>
            ) : (
                <div className="space-y-3">
                    {deployments.map((deploy) => (
                        <Link
                            key={deploy.id}
                            to={`/deployment/${deploy.id}`}
                            className="block bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-lg p-4 hover:border-indigo-500/30 dark:hover:border-gray-600 transition-all hover:shadow-lg hover:shadow-indigo-500/10 group"
                        >
                            <div className="flex items-center justify-between gap-4">
                                <div className="flex items-center gap-3 flex-1 min-w-0">
                                    <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center flex-shrink-0 shadow-lg shadow-indigo-500/30">
                                        <Server className="w-5 h-5 text-white" />
                                    </div>
                                    <div className="flex-1 min-w-0">
                                        <div className="flex items-center gap-2 mb-1">
                                            <h3 className="text-base font-bold text-gray-900 dark:text-white group-hover:text-indigo-600 dark:group-hover:text-indigo-400 transition-colors truncate">{deploy.name}</h3>
                                            <PluginBadge pluginId={deploy.plugin_id} provider={deploy.cloud_provider} />
                                            {deploy.version && (
                                                <span className="text-xs text-gray-500 dark:text-gray-400">v{deploy.version}</span>
                                            )}
                                        </div>
                                        <div className="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400">
                                            {deploy.cloud_provider && (
                                                <>
                                                    <span className="flex items-center gap-1">
                                                        <Tag className="w-3 h-3" />
                                                        {deploy.cloud_provider.toUpperCase()}
                                                    </span>
                                                    <span>•</span>
                                                </>
                                            )}
                                            {deploy.region && (
                                                <>
                                                    <span className="flex items-center gap-1">
                                                        <Globe className="w-3 h-3" />
                                                        {deploy.region}
                                                    </span>
                                                    <span>•</span>
                                                </>
                                            )}
                                            <span className="flex items-center gap-1">
                                                <Clock className="w-3 h-3" />
                                                {new Date(deploy.created_at).toLocaleDateString()}
                                            </span>
                                            {deploy.outputs && Object.keys(deploy.outputs).length > 0 && (
                                                <>
                                                    <span>•</span>
                                                    <span>
                                                        {Object.keys(deploy.outputs).length} output{Object.keys(deploy.outputs).length !== 1 ? 's' : ''}
                                                    </span>
                                                </>
                                            )}
                                        </div>
                                    </div>
                                </div>

                                <div className="flex items-center gap-3 flex-shrink-0">
                                    <StatusBadge status={deploy.status} />
                                    <ExternalLink className="w-4 h-4 text-gray-400 group-hover:text-indigo-600 dark:group-hover:text-indigo-400 transition-colors" />
                                </div>
                            </div>
                        </Link>
                    ))}
                </div>
            )}
        </div>
    );
};