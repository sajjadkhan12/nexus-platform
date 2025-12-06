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
    Info,
    Lock,
    Clock,
    Trash2
} from 'lucide-react';
import api from '../services/api';
import { useNotification } from '../contexts/NotificationContext';
import { useAuth } from '../contexts/AuthContext';
import { API_URL } from '../constants/api';

interface PluginVersion {
    id: number;
    plugin_id: string;
    version: string;
    manifest: any;
}

const Provision: React.FC = () => {
    const { pluginId } = useParams<{ pluginId: string }>();
    const navigate = useNavigate();
    const { addNotification } = useNotification();
    const { isAdmin, user } = useAuth();

    const [versions, setVersions] = useState<PluginVersion[]>([]);
    const [selectedVersion, setSelectedVersion] = useState<string>('');
    const [inputs, setInputs] = useState<Record<string, any>>({});
    const [loading, setLoading] = useState(true);
    const [provisioning, setProvisioning] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [pluginInfo, setPluginInfo] = useState<{ is_locked?: boolean; has_access?: boolean; has_pending_request?: boolean; name?: string } | null>(null);
    const [requestingAccess, setRequestingAccess] = useState(false);
    const [showDeleteModal, setShowDeleteModal] = useState(false);
    const [isDeleting, setIsDeleting] = useState(false);
    
    // More robust admin check - case-insensitive and checks for 'admin' role
    const userIsAdmin = isAdmin || (user?.roles || []).some(role => role.toLowerCase() === 'admin');

    useEffect(() => {
        if (pluginId) {
            loadData();
        }
    }, [pluginId]);

    const loadData = async () => {
        try {
            setLoading(true);
            const versionsData = await api.getPluginVersions(pluginId!);
            setVersions(versionsData);

            // Load plugin info to check lock status
            try {
                const pluginData = await api.getPlugin(pluginId!);
                setPluginInfo({
                    is_locked: pluginData.is_locked || false,
                    has_access: pluginData.has_access || false,
                    has_pending_request: pluginData.has_pending_request || false,
                    name: pluginData.name
                });
            } catch (err) {
                // If plugin info fails, assume not locked
                setPluginInfo({ is_locked: false, has_access: true, has_pending_request: false });
            }

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

    const handleRequestAccess = async () => {
        try {
            setRequestingAccess(true);
            await api.requestAccess(pluginId!);
            addNotification('success', 'Access request submitted. An administrator will review your request.');
            // Reload plugin info to update pending status
            const pluginData = await api.getPlugin(pluginId!);
            setPluginInfo({
                is_locked: pluginData.is_locked || false,
                has_access: pluginData.has_access || false,
                has_pending_request: pluginData.has_pending_request || false,
                name: pluginData.name
            });
        } catch (err: any) {
            addNotification('error', err.message || 'Failed to request access');
        } finally {
            setRequestingAccess(false);
        }
    };

    const handleDelete = async () => {
        if (!pluginId) return;
        
        setIsDeleting(true);
        try {
            await api.deletePlugin(pluginId);
            addNotification('success', `Plugin ${pluginInfo?.name || pluginId} has been deleted`);
            navigate('/services');
        } catch (err: any) {
            addNotification('error', err.message || 'Failed to delete plugin');
        } finally {
            setIsDeleting(false);
            setShowDeleteModal(false);
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
        // Check if plugin is locked and user doesn't have access
        if (pluginInfo?.is_locked && !pluginInfo?.has_access) {
            addNotification('error', 'This plugin is locked. Please request access first.');
            return;
        }

        setProvisioning(true);
        setError(null);

        try {
            const result = await api.provision({
                plugin_id: pluginId!,
                version: selectedVersion,
                inputs
            });

            // Show success notification
            const resourceName = inputs['bucket_name'] || inputs['name'] || `${pluginId}-${result.id.substring(0, 8)}`;
            addNotification('success', `Provisioning started for ${resourceName}`);

            // Wait a moment for user to see the notification before redirecting
            setTimeout(() => {
                if (result.deployment_id) {
                    navigate(`/deployment/${result.deployment_id}`);
                } else {
                    navigate(`/jobs/${result.id}`);
                }
            }, 2000); // 2 seconds delay as requested
        } catch (err: any) {
            // Show error notification
            addNotification('error', err.message || 'Provisioning failed');
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
        return `${API_URL}/storage/plugins/${pluginId}/${selectedVersion}/${manifest.icon}`;
    };

    const iconUrl = getIconUrl();

    if (loading) {
        return (
            <div className="flex flex-col items-center justify-center min-h-[60vh]">
                <Loader className="w-10 h-10 text-orange-600 dark:text-orange-400 animate-spin mb-4" />
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
                    className="px-4 py-2 bg-orange-600 text-white rounded-lg hover:bg-orange-700 transition-colors"
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
                            <div className="relative">
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
                                    <div className={`hidden w-10 h-10 bg-gradient-to-br from-orange-500 to-orange-600 rounded-lg flex items-center justify-center ${!iconUrl ? 'block' : ''}`}>
                                        <Box className="w-6 h-6 text-white" />
                                    </div>
                                </div>
                                {pluginInfo?.is_locked && !pluginInfo?.has_access && (
                                    <div className="absolute -top-2 -right-2">
                                        <div className="flex items-center gap-1 px-2 py-1 bg-red-500/10 text-red-600 dark:text-red-400 rounded-full border border-red-500/30 shadow-sm">
                                            <Lock className="w-3 h-3" />
                                        </div>
                                    </div>
                                )}
                            </div>
                            <div className="flex-1">
                                <div className="flex items-center gap-3 mb-2">
                                    <h1 className="text-2xl font-bold text-gray-900 dark:text-white">{manifest.name}</h1>
                                    {userIsAdmin && (
                                        <button
                                            onClick={() => setShowDeleteModal(true)}
                                            className="p-1.5 text-gray-400 hover:text-red-600 dark:hover:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors"
                                            title="Delete plugin"
                                        >
                                            <Trash2 className="w-5 h-5" />
                                        </button>
                                    )}
                                    {pluginInfo?.is_locked && !pluginInfo?.has_access && (
                                        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium border bg-red-500/10 text-red-600 dark:text-red-400 border-red-500/30">
                                            <Lock className="w-3 h-3" />
                                            Locked
                                        </span>
                                    )}
                                </div>
                                <p className="text-gray-600 dark:text-gray-400 leading-relaxed">
                                    {manifest.description}
                                </p>
                                <div className="flex flex-wrap gap-2 mt-4">
                                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-400 border border-orange-200 dark:border-orange-800">
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
                                <Server className="w-5 h-5 text-orange-500" />
                                Configuration
                            </h2>
                            <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                                Configure your deployment parameters
                            </p>
                        </div>


                        <div className="p-6 space-y-6">


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
                                                        className="w-full bg-gray-50 dark:bg-gray-950 border border-gray-200 dark:border-gray-700 rounded-xl px-4 py-2.5 text-gray-900 dark:text-white focus:ring-2 focus:ring-orange-500/20 focus:border-orange-500 transition-all"
                                                    >
                                                        {prop.enum.map((option: string) => (
                                                            <option key={option} value={option}>{option}</option>
                                                        ))}
                                                    </select>
                                                ) : prop.type === 'boolean' ? (
                                                    <label className="flex items-center gap-3 p-4 bg-gray-50 dark:bg-gray-950 border border-gray-200 dark:border-gray-700 rounded-xl cursor-pointer hover:border-orange-500/50 transition-colors">
                                                        <input
                                                            type="checkbox"
                                                            checked={inputs[key] || false}
                                                            onChange={(e) => handleInputChange(key, e.target.checked)}
                                                            className="w-5 h-5 text-orange-600 rounded focus:ring-orange-500 border-gray-300 dark:border-gray-600"
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
                                                        className="w-full bg-gray-50 dark:bg-gray-950 border border-gray-200 dark:border-gray-700 rounded-xl px-4 py-2.5 text-gray-900 dark:text-white focus:ring-2 focus:ring-orange-500/20 focus:border-orange-500 transition-all"
                                                        placeholder={prop.default?.toString()}
                                                    />
                                                ) : (
                                                    <input
                                                        type="text"
                                                        value={inputs[key] || ''}
                                                        onChange={(e) => handleInputChange(key, e.target.value)}
                                                        placeholder={prop.default}
                                                        className="w-full bg-gray-50 dark:bg-gray-950 border border-gray-200 dark:border-gray-700 rounded-xl px-4 py-2.5 text-gray-900 dark:text-white focus:ring-2 focus:ring-orange-500/20 focus:border-orange-500 transition-all"
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
                                disabled={provisioning || (pluginInfo?.is_locked && !pluginInfo?.has_access)}
                                className={`w-full py-3 px-4 rounded-xl font-semibold text-white shadow-lg shadow-orange-500/20 transition-all transform active:scale-[0.98] ${
                                    provisioning || (pluginInfo?.is_locked && !pluginInfo?.has_access)
                                        ? 'bg-gray-400 cursor-not-allowed'
                                        : 'bg-orange-600 hover:bg-orange-700 hover:shadow-orange-500/30'
                                }`}
                            >
                                {provisioning ? (
                                    <div className="flex items-center justify-center gap-2">
                                        <Loader className="w-5 h-5 animate-spin" />
                                        Provisioning Infrastructure...
                                    </div>
                                ) : pluginInfo?.is_locked && !pluginInfo?.has_access ? (
                                    <div className="flex items-center justify-center gap-2">
                                        <Lock className="w-5 h-5" />
                                        Plugin Is Locked 
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
                    {/* Request Access - Top of Sidebar (for normal users) */}
                    {pluginInfo?.is_locked && !pluginInfo?.has_access && !isAdmin && (
                        <div className={`border rounded-xl p-5 shadow-sm ${
                            pluginInfo?.has_pending_request 
                                ? "bg-yellow-50 dark:bg-yellow-900/20 border-yellow-200 dark:border-yellow-800"
                                : "bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800"
                        }`}>
                            <div className="flex items-start gap-3 mb-4">
                                <div className={`p-2 rounded-lg ${
                                    pluginInfo?.has_pending_request
                                        ? "bg-yellow-100 dark:bg-yellow-900/30"
                                        : "bg-red-100 dark:bg-red-900/30"
                                }`}>
                                    {pluginInfo?.has_pending_request ? (
                                        <Loader className="w-5 h-5 text-yellow-600 dark:text-yellow-400 animate-spin" />
                                    ) : (
                                        <Lock className="w-5 h-5 text-red-600 dark:text-red-400" />
                                    )}
                                </div>
                                <div className="flex-1">
                                    <h3 className={`text-sm font-semibold mb-1 ${
                                        pluginInfo?.has_pending_request
                                            ? "text-yellow-800 dark:text-yellow-300"
                                            : "text-red-800 dark:text-red-300"
                                    }`}>
                                        {pluginInfo?.has_pending_request ? "Request Pending" : "Plugin is Locked"}
                                    </h3>
                                    <p className={`text-xs ${
                                        pluginInfo?.has_pending_request
                                            ? "text-yellow-700 dark:text-yellow-400"
                                            : "text-red-700 dark:text-red-400"
                                    }`}>
                                        {pluginInfo?.has_pending_request
                                            ? "Your access request is pending administrator review."
                                            : "This plugin requires administrator approval to deploy."}
                                    </p>
                                </div>
                            </div>
                            <button
                                onClick={handleRequestAccess}
                                disabled={requestingAccess || pluginInfo?.has_pending_request}
                                className={`w-full px-4 py-2.5 rounded-lg font-medium text-sm transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 shadow-sm ${
                                    pluginInfo?.has_pending_request
                                        ? "bg-yellow-600 hover:bg-yellow-700 text-white"
                                        : "bg-red-600 hover:bg-red-700 text-white"
                                }`}
                            >
                                {requestingAccess ? (
                                    <>
                                        <Loader className="w-4 h-4 animate-spin" />
                                        Requesting...
                                    </>
                                ) : pluginInfo?.has_pending_request ? (
                                    <>
                                        <Clock className="w-4 h-4" />
                                        Request Pending
                                    </>
                                ) : (
                                    <>
                                        <Lock className="w-4 h-4" />
                                        Request Access
                                    </>
                                )}
                            </button>
                        </div>
                    )}

                    {/* About Card */}
                    <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-800 p-6 shadow-sm">
                        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
                            <Cloud className="w-5 h-5 text-orange-500" />
                            About this Plugin
                        </h3>
                        <div className="space-y-4 text-sm text-gray-600 dark:text-gray-400">
                            <p className="whitespace-pre-line">
                                {manifest.about?.description || manifest.about?.long_description || manifest.description || (
                                    "This plugin provisions infrastructure resources using Pulumi. " +
                                    "Ensure you have the necessary permissions and quota in your cloud provider account."
                                )}
                            </p>

                            <div className="pt-4 border-t border-gray-100 dark:border-gray-800">
                                <h4 className="font-medium text-gray-900 dark:text-white mb-2">Requirements</h4>
                                <ul className="space-y-2">
                                    {(manifest.requirements && manifest.requirements.length > 0) ? (
                                        manifest.requirements.map((req: any, index: number) => (
                                            <li key={index} className="flex items-start gap-2">
                                                <CheckCircle2 className="w-4 h-4 text-green-500 mt-0.5 flex-shrink-0" />
                                                <div>
                                                    <span>{req.text}</span>
                                                    {req.details && (
                                                        <div className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                                                            {req.details}
                                                        </div>
                                                    )}
                                                </div>
                                            </li>
                                        ))
                                    ) : manifest.inputs?.required ? (
                                        manifest.inputs.required.map((key: string) => {
                                            const prop = manifest.inputs.properties[key];
                                            return (
                                                <li key={key} className="flex items-start gap-2">
                                                    <CheckCircle2 className="w-4 h-4 text-green-500 mt-0.5 flex-shrink-0" />
                                                    <span>{prop?.title || key.replace(/_/g, ' ')}</span>
                                                </li>
                                            );
                                        })
                                    ) : (
                                        <li className="text-gray-500 dark:text-gray-400 text-xs">No specific requirements</li>
                                    )}
                                </ul>
                            </div>
                        </div>
                    </div>

                    {/* Cost Estimate (Dynamic) */}
                    {manifest.cost_estimate && (
                        <div className="bg-gradient-to-br from-orange-500 to-orange-600 rounded-2xl p-6 text-white shadow-lg shadow-orange-500/20">
                            <h3 className="font-semibold mb-2 flex items-center gap-2">
                                <Cpu className="w-5 h-5" />
                                Estimated Cost
                            </h3>
                            <p className="text-orange-100 text-sm mb-4">
                                {manifest.cost_estimate.description || "Based on standard configuration and regional pricing."}
                            </p>
                            <div className="text-3xl font-bold mb-1">
                                ~${typeof manifest.cost_estimate.amount === 'number' ? manifest.cost_estimate.amount.toFixed(2) : manifest.cost_estimate.amount}
                                <span className="text-sm font-normal text-orange-200">
                                    {manifest.cost_estimate.currency ? ` ${manifest.cost_estimate.currency}` : ''} / {manifest.cost_estimate.period || 'month'}
                                </span>
                            </div>
                            <p className="text-xs text-orange-200">
                                *{manifest.cost_estimate.disclaimer || "Actual costs may vary based on usage"}
                            </p>
                        </div>
                    )}
                </div>
            </div>

            {/* Delete Confirmation Modal */}
            {showDeleteModal && (
                <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
                    <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-2xl p-6 max-w-md w-full shadow-2xl">
                        <div className="flex items-start gap-4 mb-4">
                            <div className="w-12 h-12 rounded-full bg-red-500/10 flex items-center justify-center flex-shrink-0">
                                <Trash2 className="w-6 h-6 text-red-600 dark:text-red-400" />
                            </div>
                            <div>
                                <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-1">Delete Plugin</h3>
                                <p className="text-sm text-gray-500 dark:text-gray-400">
                                    Are you sure you want to delete "{pluginInfo?.name || manifest.name || pluginId}"? This will remove all versions and deployments using this plugin.
                                </p>
                            </div>
                        </div>

                        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-3 mb-4">
                            <p className="text-sm text-red-600 dark:text-red-400 font-medium">
                                ⚠️ Warning: This action cannot be undone
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
                                        <Loader className="w-4 h-4 animate-spin" />
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

export default Provision;
