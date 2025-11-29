import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
    ArrowLeft,
    Box,
    Cloud,
    Shield,
    Server,
    Cpu,
    AlertCircle,
    CheckCircle2,
    Loader,
    Info
} from 'lucide-react';
import api from '../services/api';

interface PluginVersion {
    id: number;
    plugin_id: string;
    version: string;
    manifest: any;
}

const Provision: React.FC = () => {
    const { pluginId } = useParams<{ pluginId: string }>();
    const navigate = useNavigate();

    const [versions, setVersions] = useState<PluginVersion[]>([]);
    const [selectedVersion, setSelectedVersion] = useState<string>('');
    const [credentials, setCredentials] = useState<any[]>([]);
    const [selectedCredential, setSelectedCredential] = useState<string>('');
    const [inputs, setInputs] = useState<Record<string, any>>({});
    const [loading, setLoading] = useState(true);
    const [provisioning, setProvisioning] = useState(false);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        if (pluginId) {
            loadData();
        }
    }, [pluginId]);

    const loadData = async () => {
        try {
            setLoading(true);
            const [versionsData, credentialsData] = await Promise.all([
                api.getPluginVersions(pluginId!),
                api.listCredentials()
            ]);
            setVersions(versionsData);
            setCredentials(credentialsData);

            if (versionsData.length > 0) {
                // Sort versions descending
                const sortedVersions = versionsData.sort((a, b) =>
                    b.version.localeCompare(a.version, undefined, { numeric: true, sensitivity: 'base' })
                );
                const latestVersion = sortedVersions[0];
                setSelectedVersion(latestVersion.version);
                initializeInputs(latestVersion.manifest);
            }
        } catch (err: any) {
            setError(err.message || 'Failed to load data');
        } finally {
            setLoading(false);
        }
    };

    const initializeInputs = (manifest: any) => {
        const initialInputs: Record<string, any> = {};
        if (manifest.inputs && manifest.inputs.properties) {
            Object.keys(manifest.inputs.properties).forEach(key => {
                const prop = manifest.inputs.properties[key];
                if (prop.default !== undefined) {
                    initialInputs[key] = prop.default;
                } else {
                    initialInputs[key] = '';
                }
            });
        }
        setInputs(initialInputs);
    };

    const handleVersionChange = (version: string) => {
        setSelectedVersion(version);
        const versionData = versions.find(v => v.version === version);
        if (versionData) {
            initializeInputs(versionData.manifest);
        }
    };

    const handleInputChange = (key: string, value: any) => {
        setInputs(prev => ({ ...prev, [key]: value }));
    };

    const handleProvision = async () => {
        setProvisioning(true);
        setError(null);

        try {
            const result = await api.provision({
                plugin_id: pluginId!,
                version: selectedVersion,
                inputs,
                credential_name: selectedCredential || undefined
            });
            // Navigate to job status page
            navigate(`/jobs/${result.id}`);
        } catch (err: any) {
            setError(err.message || 'Provisioning failed');
            window.scrollTo({ top: 0, behavior: 'smooth' });
        } finally {
            setProvisioning(false);
        }
    };

    const selectedVersionData = versions.find(v => v.version === selectedVersion);
    const manifest = selectedVersionData?.manifest;

    // Construct icon URL if available
    const getIconUrl = () => {
        if (!manifest?.icon) return null;
        // If it's a full URL, return it
        if (manifest.icon.startsWith('http')) return manifest.icon;

        // Otherwise construct it
        // Note: This logic mirrors the backend logic but simplified for display
        // We assume the backend serves it correctly if we point to the right place
        // But since we don't have the full logic here, we might rely on what the backend API returns
        // However, we are getting manifest directly here.

        // We'll try the standard path.
        return `http://localhost:8000/storage/plugins/${pluginId}/${selectedVersion}/${manifest.icon}`;
    };

    const iconUrl = getIconUrl();

    if (loading) {
        return (
            <div className="flex flex-col items-center justify-center min-h-[60vh]">
                <Loader className="w-10 h-10 text-indigo-600 dark:text-indigo-400 animate-spin mb-4" />
                <p className="text-gray-600 dark:text-gray-400">Loading provisioning template...</p>
            </div>
        );
    }

    if (!manifest) {
        return (
            <div className="flex flex-col items-center justify-center min-h-[60vh] text-center">
                <AlertCircle className="w-12 h-12 text-red-500 mb-4" />
                <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-2">Plugin Not Found</h2>
                <p className="text-gray-600 dark:text-gray-400 mb-6">Could not load plugin definition.</p>
                <button
                    onClick={() => navigate('/services')}
                    className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors"
                >
                    Back to Catalog
                </button>
            </div>
        );
    }

    return (
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 animate-in fade-in duration-500">
            {/* Back Button */}
            <button
                onClick={() => navigate('/services')}
                className="flex items-center text-gray-500 hover:text-gray-900 dark:text-gray-400 dark:hover:text-white mb-6 transition-colors"
            >
                <ArrowLeft className="w-4 h-4 mr-2" />
                Back to Catalog
            </button>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                {/* Main Content - Form */}
                <div className="lg:col-span-2 space-y-6">

                    {/* Header Card */}
                    <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-800 p-6 shadow-sm">
                        <div className="flex items-start gap-6">
                            <div className="w-20 h-20 bg-gray-50 dark:bg-gray-800 rounded-2xl border border-gray-200 dark:border-gray-700 flex items-center justify-center flex-shrink-0 shadow-sm">
                                {iconUrl ? (
                                    <img
                                        src={iconUrl}
                                        alt={manifest.name}
                                        className="w-14 h-14 object-contain"
                                        onError={(e) => {
                                            // Fallback if image fails to load
                                            (e.target as HTMLImageElement).style.display = 'none';
                                            (e.target as HTMLImageElement).nextElementSibling?.classList.remove('hidden');
                                        }}
                                    />
                                ) : null}
                                <div className={`hidden w-10 h-10 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-lg flex items-center justify-center ${!iconUrl ? 'block' : ''}`}>
                                    <Box className="w-6 h-6 text-white" />
                                </div>
                            </div>
                            <div>
                                <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">{manifest.name}</h1>
                                <p className="text-gray-600 dark:text-gray-400 leading-relaxed">
                                    {manifest.description}
                                </p>
                                <div className="flex flex-wrap gap-2 mt-4">
                                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-indigo-100 text-indigo-800 dark:bg-indigo-900/30 dark:text-indigo-400 border border-indigo-200 dark:border-indigo-800">
                                        v{selectedVersion}
                                    </span>
                                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400 border border-blue-200 dark:border-blue-800">
                                        {manifest.cloud_provider?.toUpperCase()}
                                    </span>
                                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-400 border border-gray-200 dark:border-gray-700">
                                        {manifest.category}
                                    </span>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Error Alert */}
                    {error && (
                        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl p-4 flex items-start gap-3">
                            <AlertCircle className="w-5 h-5 text-red-600 dark:text-red-400 mt-0.5 flex-shrink-0" />
                            <div>
                                <h3 className="text-sm font-medium text-red-800 dark:text-red-300">Provisioning Failed</h3>
                                <p className="text-sm text-red-700 dark:text-red-400 mt-1">{error}</p>
                            </div>
                        </div>
                    )}

                    {/* Configuration Form */}
                    <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-800 overflow-hidden shadow-sm">
                        <div className="p-6 border-b border-gray-100 dark:border-gray-800">
                            <h2 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                                <Server className="w-5 h-5 text-indigo-500" />
                                Configuration
                            </h2>
                            <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                                Configure your deployment parameters
                            </p>
                        </div>

                        <div className="p-6 space-y-6">
                            {/* Version Selection */}
                            <div>
                                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                                    Plugin Version
                                </label>
                                <select
                                    value={selectedVersion}
                                    onChange={(e) => handleVersionChange(e.target.value)}
                                    className="w-full bg-gray-50 dark:bg-gray-950 border border-gray-200 dark:border-gray-700 rounded-xl px-4 py-2.5 text-gray-900 dark:text-white focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all"
                                >
                                    {versions.map(v => (
                                        <option key={v.version} value={v.version}>{v.version}</option>
                                    ))}
                                </select>
                            </div>

                            {/* Credentials Selection */}
                            {credentials.length > 0 && (
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                                        Cloud Credentials <span className="text-red-500">*</span>
                                    </label>
                                    <div className="relative">
                                        <Shield className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                                        <select
                                            value={selectedCredential}
                                            onChange={(e) => setSelectedCredential(e.target.value)}
                                            className="w-full pl-12 pr-4 py-2.5 bg-gray-50 dark:bg-gray-950 border border-gray-200 dark:border-gray-700 rounded-xl text-gray-900 dark:text-white focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all"
                                        >
                                            <option value="">Select credentials...</option>
                                            {credentials.map(c => (
                                                <option key={c.id} value={c.name}>{c.name} ({c.provider})</option>
                                            ))}
                                        </select>
                                    </div>
                                    <p className="text-xs text-gray-500 mt-2">
                                        Select the cloud provider credentials to use for this deployment.
                                    </p>
                                </div>
                            )}

                            {/* Dynamic Inputs */}
                            {manifest.inputs?.properties && (
                                <div className="space-y-6 pt-4 border-t border-gray-100 dark:border-gray-800">
                                    {Object.entries(manifest.inputs.properties).map(([key, prop]: [string, any]) => {
                                        const isRequired = manifest.inputs.required?.includes(key);
                                        return (
                                            <div key={key} className="group">
                                                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2 flex items-center gap-1">
                                                    {prop.title || key}
                                                    {isRequired && <span className="text-red-500">*</span>}
                                                    {prop.description && (
                                                        <div className="group relative ml-1">
                                                            <Info className="w-4 h-4 text-gray-400 cursor-help" />
                                                            <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-3 py-2 bg-gray-900 text-white text-xs rounded-lg opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none z-10">
                                                                {prop.description}
                                                                <div className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-gray-900"></div>
                                                            </div>
                                                        </div>
                                                    )}
                                                </label>

                                                {prop.enum ? (
                                                    <select
                                                        value={inputs[key] || ''}
                                                        onChange={(e) => handleInputChange(key, e.target.value)}
                                                        className="w-full bg-gray-50 dark:bg-gray-950 border border-gray-200 dark:border-gray-700 rounded-xl px-4 py-2.5 text-gray-900 dark:text-white focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all"
                                                    >
                                                        {prop.enum.map((option: string) => (
                                                            <option key={option} value={option}>{option}</option>
                                                        ))}
                                                    </select>
                                                ) : prop.type === 'boolean' ? (
                                                    <label className="flex items-center gap-3 p-4 bg-gray-50 dark:bg-gray-950 border border-gray-200 dark:border-gray-700 rounded-xl cursor-pointer hover:border-indigo-500/50 transition-colors">
                                                        <input
                                                            type="checkbox"
                                                            checked={inputs[key] || false}
                                                            onChange={(e) => handleInputChange(key, e.target.checked)}
                                                            className="w-5 h-5 text-indigo-600 rounded focus:ring-indigo-500 border-gray-300 dark:border-gray-600"
                                                        />
                                                        <span className="text-sm text-gray-700 dark:text-gray-300 font-medium">
                                                            {prop.description || prop.title || key}
                                                        </span>
                                                    </label>
                                                ) : prop.type === 'integer' ? (
                                                    <input
                                                        type="number"
                                                        value={inputs[key] || ''}
                                                        onChange={(e) => handleInputChange(key, parseInt(e.target.value))}
                                                        className="w-full bg-gray-50 dark:bg-gray-950 border border-gray-200 dark:border-gray-700 rounded-xl px-4 py-2.5 text-gray-900 dark:text-white focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all"
                                                        placeholder={prop.default?.toString()}
                                                    />
                                                ) : (
                                                    <input
                                                        type="text"
                                                        value={inputs[key] || ''}
                                                        onChange={(e) => handleInputChange(key, e.target.value)}
                                                        placeholder={prop.default}
                                                        className="w-full bg-gray-50 dark:bg-gray-950 border border-gray-200 dark:border-gray-700 rounded-xl px-4 py-2.5 text-gray-900 dark:text-white focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all"
                                                    />
                                                )}

                                                {prop.description && prop.type !== 'boolean' && (
                                                    <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">
                                                        {prop.description}
                                                    </p>
                                                )}
                                            </div>
                                        );
                                    })}
                                </div>
                            )}
                        </div>

                        <div className="p-6 bg-gray-50 dark:bg-gray-900/50 border-t border-gray-100 dark:border-gray-800">
                            <button
                                onClick={handleProvision}
                                disabled={provisioning}
                                className={`w-full py-3 px-4 rounded-xl font-semibold text-white shadow-lg shadow-indigo-500/20 transition-all transform active:scale-[0.98] ${provisioning
                                    ? 'bg-gray-400 cursor-not-allowed'
                                    : 'bg-indigo-600 hover:bg-indigo-700 hover:shadow-indigo-500/30'
                                    }`}
                            >
                                {provisioning ? (
                                    <div className="flex items-center justify-center gap-2">
                                        <Loader className="w-5 h-5 animate-spin" />
                                        Provisioning Infrastructure...
                                    </div>
                                ) : (
                                    'Deploy Infrastructure'
                                )}
                            </button>
                        </div>
                    </div>
                </div>

                {/* Sidebar - Summary & Info */}
                <div className="space-y-6">
                    {/* About Card */}
                    <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-800 p-6 shadow-sm">
                        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
                            <Cloud className="w-5 h-5 text-indigo-500" />
                            About this Plugin
                        </h3>
                        <div className="space-y-4 text-sm text-gray-600 dark:text-gray-400">
                            <p>
                                This plugin provisions infrastructure resources using Pulumi.
                                Ensure you have the necessary permissions and quota in your cloud provider account.
                            </p>

                            <div className="pt-4 border-t border-gray-100 dark:border-gray-800">
                                <h4 className="font-medium text-gray-900 dark:text-white mb-2">Requirements</h4>
                                <ul className="space-y-2">
                                    <li className="flex items-start gap-2">
                                        <CheckCircle2 className="w-4 h-4 text-green-500 mt-0.5 flex-shrink-0" />
                                        <span>Valid Cloud Credentials</span>
                                    </li>
                                    <li className="flex items-start gap-2">
                                        <CheckCircle2 className="w-4 h-4 text-green-500 mt-0.5 flex-shrink-0" />
                                        <span>Project/Account ID</span>
                                    </li>
                                    <li className="flex items-start gap-2">
                                        <CheckCircle2 className="w-4 h-4 text-green-500 mt-0.5 flex-shrink-0" />
                                        <span>Region Selection</span>
                                    </li>
                                </ul>
                            </div>
                        </div>
                    </div>

                    {/* Cost Estimate (Placeholder) */}
                    <div className="bg-gradient-to-br from-indigo-500 to-purple-600 rounded-2xl p-6 text-white shadow-lg shadow-indigo-500/20">
                        <h3 className="font-semibold mb-2 flex items-center gap-2">
                            <Cpu className="w-5 h-5" />
                            Estimated Cost
                        </h3>
                        <p className="text-indigo-100 text-sm mb-4">
                            Based on standard instance types and regional pricing.
                        </p>
                        <div className="text-3xl font-bold mb-1">
                            ~$45.00 <span className="text-sm font-normal text-indigo-200">/ month</span>
                        </div>
                        <p className="text-xs text-indigo-200">
                            *Actual costs may vary based on usage
                        </p>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default Provision;
