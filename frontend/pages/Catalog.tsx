import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Server, ExternalLink, Clock, Globe } from 'lucide-react';
import api from '../services/api';

interface Deployment {
    id: string;
    service_id: string;
    name: string;
    provider: string;
    region: string;
    status: string;
    created_at: string;
    cost_per_month?: number;
}

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
                <div className="space-y-4">
                    {deployments.map((deploy) => (
                        <Link
                            key={deploy.id}
                            to={`/deployment/${deploy.id}`}
                            className="block bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-6 hover:border-indigo-500/30 dark:hover:border-gray-600 transition-all hover:bg-gray-50 dark:hover:bg-gray-800/50 group"
                        >
                            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                                <div className="flex items-start gap-4">
                                    <div className="w-12 h-12 rounded-lg bg-gray-100 dark:bg-gray-800 flex items-center justify-center flex-shrink-0 group-hover:bg-white dark:group-hover:bg-gray-700 transition-colors">
                                        <Server className="w-6 h-6 text-indigo-600 dark:text-indigo-400" />
                                    </div>
                                    <div>
                                        <h3 className="text-lg font-bold text-gray-900 dark:text-white group-hover:text-indigo-600 dark:group-hover:text-indigo-400 transition-colors">{deploy.name}</h3>
                                        <div className="flex items-center gap-3 text-sm text-gray-500 dark:text-gray-400 mt-1">
                                            <span className="flex items-center gap-1"><Globe className="w-3 h-3" /> {deploy.region}</span>
                                            <span>•</span>
                                            <span className="flex items-center gap-1"><Clock className="w-3 h-3" /> {new Date(deploy.created_at).toLocaleDateString()}</span>
                                        </div>
                                    </div>
                                </div>

                                <div className="flex items-center gap-6">
                                    <div className="flex flex-col items-end">
                                        <span className={`inline-block w-2.5 h-2.5 rounded-full mb-1 ${deploy.status === 'Running' ? 'bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.6)]' :
                                                deploy.status === 'Provisioning' ? 'bg-yellow-500 animate-pulse' :
                                                    'bg-red-500'
                                            }`}></span>
                                        <span className="text-sm font-medium text-gray-700 dark:text-gray-300">{deploy.status}</span>
                                    </div>
                                    <ExternalLink className="w-5 h-5 text-gray-400 group-hover:text-gray-600 dark:group-hover:text-white transition-colors" />
                                </div>
                            </div>
                        </Link>
                    ))}
                </div>
            )}
        </div>
    );
};