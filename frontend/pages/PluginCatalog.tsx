import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, ArrowRight, Box, Loader } from 'lucide-react';
import api from '../services/api';

interface Plugin {
    id: string;
    name: string;
    description: string;
    author: string;
    category: string;
    cloud_provider: string;
    latest_version: string;
    icon?: string;
}

import { useAuth } from '../contexts/AuthContext';

const PluginCatalog: React.FC = () => {
    const navigate = useNavigate();
    const { isAdmin } = useAuth();
    const [plugins, setPlugins] = useState<Plugin[]>([]);
    const [loading, setLoading] = useState(true);
    const [search, setSearch] = useState('');
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        loadPlugins();
    }, []);

    const loadPlugins = async () => {
        try {
            setLoading(true);
            const data = await api.listPlugins();
            setPlugins(data);
        } catch (err: any) {
            setError(err.message || 'Failed to load plugins');
        } finally {
            setLoading(false);
        }
    };

    const filteredPlugins = plugins.filter(plugin =>
        plugin.name.toLowerCase().includes(search.toLowerCase()) ||
        plugin.description.toLowerCase().includes(search.toLowerCase()) ||
        plugin.category.toLowerCase().includes(search.toLowerCase())
    );

    const getProviderBadgeColor = (provider: string) => {
        switch (provider.toLowerCase()) {
            case 'gcp':
                return 'bg-blue-500/10 text-blue-400 border-blue-500/30';
            case 'aws':
                return 'bg-orange-500/10 text-orange-400 border-orange-500/30';
            case 'azure':
                return 'bg-cyan-500/10 text-cyan-400 border-cyan-500/30';
            default:
                return 'bg-gray-500/10 text-gray-400 border-gray-500/30';
        }
    };

    const getProviderIcon = (provider: string) => {
        // You can replace these with actual cloud provider icons
        return provider.toUpperCase();
    };

    const getCategoryIcon = (category: string) => {
        // Map categories to appropriate labels
        const categoryMap: Record<string, string> = {
            'compute': 'Container',
            'storage': 'Storage',
            'networking': 'Network',
            'database': 'Database',
            'kubernetes': 'Container'
        };
        return categoryMap[category.toLowerCase()] || 'Service';
    };

    const extractTags = (plugin: Plugin) => {
        // Generate tags based on plugin metadata
        const tags = [];
        if (plugin.cloud_provider) tags.push(`#${plugin.cloud_provider.toLowerCase()}`);
        if (plugin.category) tags.push(`#${plugin.category.toLowerCase()}`);
        // You can add more dynamic tags from plugin metadata
        return tags.slice(0, 3); // Limit to 3 tags
    };

    return (
        <div className="max-w-7xl mx-auto">
            {/* Header */}
            <div className="mb-8">
                <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">Plugin Catalog</h1>
                <p className="text-gray-600 dark:text-gray-400">
                    Browse and deploy infrastructure plugins
                </p>
            </div>

            {/* Search Bar */}
            <div className="mb-8">
                <div className="relative">
                    <Search className="w-5 h-5 absolute left-4 top-1/2 -translate-y-1/2 text-gray-400 dark:text-gray-500" />
                    <input
                        type="text"
                        placeholder="Search services, tags..."
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                        className="w-full pl-12 pr-4 py-3 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl text-gray-900 dark:text-white placeholder:text-gray-400 dark:placeholder:text-gray-500 focus:outline-none focus:ring-2 focus:ring-orange-500 dark:focus:ring-orange-400"
                    />
                </div>
            </div>

            {/* Loading State */}
            {loading && (
                <div className="flex flex-col items-center justify-center py-20">
                    <Loader className="w-8 h-8 text-orange-600 dark:text-orange-400 animate-spin mb-4" />
                    <p className="text-gray-600 dark:text-gray-400">Loading plugins...</p>
                </div>
            )}

            {/* Error State */}
            {error && !loading && (
                <div className="bg-red-50 dark:bg-red-500/10 border border-red-200 dark:border-red-500/30 rounded-xl p-6 text-center">
                    <p className="text-red-600 dark:text-red-400">{error}</p>
                </div>
            )}

            {/* Empty State */}
            {!loading && !error && filteredPlugins.length === 0 && (
                <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-12 text-center">
                    <Box className="w-12 h-12 mx-auto mb-4 text-gray-400 dark:text-gray-600" />
                    <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
                        {search ? 'No plugins found' : 'No plugins available'}
                    </h3>
                    <p className="text-gray-600 dark:text-gray-400 mb-6">
                        {search
                            ? 'Try adjusting your search criteria'
                            : 'Upload your first plugin to get started'
                        }
                    </p>
                    {!search && isAdmin && (
                        <button
                            onClick={() => navigate('/plugin-upload')}
                            className="px-6 py-2.5 bg-orange-600 hover:bg-orange-700 text-white rounded-lg font-medium transition-colors"
                        >
                            Upload Plugin
                        </button>
                    )}
                </div>
            )}

            {/* Plugin Grid */}
            {!loading && !error && filteredPlugins.length > 0 && (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {filteredPlugins.map((plugin) => (
                        <div
                            key={plugin.id}
                            className="group bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-6 hover:border-orange-500/50 dark:hover:border-orange-500/50 transition-all duration-300 hover:shadow-lg hover:shadow-orange-500/10"
                        >
                            {/* Header - Icon and Provider Badge */}
                            <div className="flex items-start justify-between mb-4">
                                <div className="w-14 h-14 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 flex items-center justify-center flex-shrink-0">
                                    {plugin.icon ? (
                                        <img src={plugin.icon} alt={plugin.name} className="w-10 h-10" />
                                    ) : (
                                        <div className="w-10 h-10 bg-gradient-to-br from-orange-500 to-orange-600 rounded-lg flex items-center justify-center">
                                            <Box className="w-6 h-6 text-white" />
                                        </div>
                                    )}
                                </div>
                                <span className={`px-3 py-1 rounded-lg text-xs font-semibold border ${getProviderBadgeColor(plugin.cloud_provider)}`}>
                                    {getProviderIcon(plugin.cloud_provider)}
                                </span>
                            </div>

                            {/* Title and Description */}
                            <h3 className="text-xl font-bold text-gray-900 dark:text-white mb-2 group-hover:text-orange-600 dark:group-hover:text-orange-400 transition-colors">
                                {plugin.name}
                            </h3>
                            <p className="text-sm text-gray-600 dark:text-gray-400 mb-4 line-clamp-2">
                                {plugin.description}
                            </p>

                            {/* Tags */}
                            <div className="flex flex-wrap gap-2 mb-4">
                                {extractTags(plugin).map((tag, index) => (
                                    <span
                                        key={index}
                                        className="px-2.5 py-1 bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 rounded text-xs font-medium"
                                    >
                                        {tag}
                                    </span>
                                ))}
                            </div>

                            {/* Footer - Category and Deploy Button */}
                            <div className="flex items-center justify-between pt-4 border-t border-gray-100 dark:border-gray-800">
                                <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400">
                                    <Box className="w-4 h-4" />
                                    <span>{getCategoryIcon(plugin.category)}</span>
                                </div>
                                <button
                                    onClick={() => navigate(`/provision/${plugin.id}`)}
                                    className="flex items-center gap-2 px-4 py-2 bg-orange-600 hover:bg-orange-700 text-white rounded-lg font-medium text-sm transition-all group-hover:shadow-lg group-hover:shadow-orange-500/30"
                                >
                                    Deploy
                                    <ArrowRight className="w-4 h-4" />
                                </button>
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
};

export default PluginCatalog;
