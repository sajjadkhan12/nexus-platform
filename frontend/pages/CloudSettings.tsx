import React, { useState, useEffect } from 'react';
import {
    CloudCog,
    Plus,
    Trash2,
    Upload,
    CheckCircle2,
    AlertCircle,
    Loader,
    Key,
    FileJson,
    Info
} from 'lucide-react';
import api from '../services/api';

interface Credential {
    id: number;
    name: string;
    provider: string;
    created_at: string;
    updated_at: string;
}

const CloudSettings: React.FC = () => {
    const [credentials, setCredentials] = useState<Credential[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [success, setSuccess] = useState<string | null>(null);
    const [showForm, setShowForm] = useState(false);

    // Form state
    const [name, setName] = useState('');
    const [provider, setProvider] = useState('gcp');
    const [credentialData, setCredentialData] = useState('');
    const [saving, setSaving] = useState(false);
    const [uploadedFileName, setUploadedFileName] = useState<string | null>(null);

    useEffect(() => {
        loadCredentials();
    }, []);

    const loadCredentials = async () => {
        try {
            setLoading(true);
            const data = await api.listCredentials();
            setCredentials(data);
        } catch (err: any) {
            setError(err.message || 'Failed to load credentials');
        } finally {
            setLoading(false);
        }
    };

    const handleFileUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
        const file = event.target.files?.[0];
        if (!file) return;

        setUploadedFileName(file.name);

        const reader = new FileReader();
        reader.onload = (e) => {
            try {
                const content = e.target?.result as string;
                // Validate JSON
                JSON.parse(content);
                setCredentialData(content);
                setError(null);
                setSuccess('File uploaded successfully!');
                setTimeout(() => setSuccess(null), 3000);
            } catch (err) {
                setError('Invalid JSON file');
                setCredentialData('');
                setUploadedFileName(null);
            }
        };
        reader.readAsText(file);
    };

    const handleSave = async () => {
        setSaving(true);
        setError(null);
        setSuccess(null);

        try {
            let parsedCredentials;
            try {
                parsedCredentials = JSON.parse(credentialData);
            } catch {
                throw new Error('Invalid JSON format');
            }

            await api.createCredential({
                name,
                provider,
                credentials: parsedCredentials
            });

            setSuccess('Credentials saved successfully!');
            setShowForm(false);
            setName('');
            setProvider('gcp');
            setCredentialData('');
            setUploadedFileName(null);
            await loadCredentials();

            setTimeout(() => setSuccess(null), 3000);
        } catch (err: any) {
            setError(err.message || 'Failed to save credentials');
        } finally {
            setSaving(false);
        }
    };

    const handleDelete = async (id: number, credName: string) => {
        if (!confirm(`Are you sure you want to delete "${credName}"?`)) {
            return;
        }

        try {
            await api.deleteCredential(id);
            setSuccess('Credential deleted successfully');
            await loadCredentials();
            setTimeout(() => setSuccess(null), 3000);
        } catch (err: any) {
            setError(err.message || 'Failed to delete credential');
        }
    };

    const getProviderExample = (provider: string) => {
        switch (provider) {
            case 'gcp':
                return JSON.stringify({
                    type: "service_account",
                    project_id: "my-project-id",
                    private_key_id: "abc123...",
                    private_key: "-----BEGIN PRIVATE KEY-----\\n...\\n-----END PRIVATE KEY-----\\n",
                    client_email: "service-account@my-project.iam.gserviceaccount.com",
                    client_id: "123456789",
                    auth_uri: "https://accounts.google.com/o/oauth2/auth",
                    token_uri: "https://oauth2.googleapis.com/token"
                }, null, 2);
            case 'aws':
                return JSON.stringify({
                    aws_access_key_id: "AKIAIOSFODNN7EXAMPLE",
                    aws_secret_access_key: "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
                    aws_region: "us-east-1"
                }, null, 2);
            case 'azure':
                return JSON.stringify({
                    azure_client_id: "client-id",
                    azure_client_secret: "client-secret",
                    azure_tenant_id: "tenant-id",
                    azure_subscription_id: "subscription-id"
                }, null, 2);
            default:
                return '{}';
        }
    };

    const getProviderBadgeColor = (provider: string) => {
        switch (provider.toLowerCase()) {
            case 'gcp':
                return 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400 border-blue-200 dark:border-blue-800';
            case 'aws':
                return 'bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-400 border-orange-200 dark:border-orange-800';
            case 'azure':
                return 'bg-cyan-100 text-cyan-800 dark:bg-cyan-900/30 dark:text-cyan-400 border-cyan-200 dark:border-cyan-800';
            default:
                return 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-400 border-gray-200 dark:border-gray-700';
        }
    };

    if (loading) {
        return (
            <div className="flex flex-col items-center justify-center min-h-[60vh]">
                <Loader className="w-10 h-10 text-indigo-600 dark:text-indigo-400 animate-spin mb-4" />
                <p className="text-gray-600 dark:text-gray-400">Loading credentials...</p>
            </div>
        );
    }

    return (
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 animate-in fade-in duration-500">
            {/* Header */}
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 mb-8">
                <div>
                    <h1 className="text-3xl font-bold text-gray-900 dark:text-white flex items-center gap-3">
                        <CloudCog className="w-8 h-8 text-indigo-500" />
                        Cloud Credentials
                    </h1>
                    <p className="text-gray-500 dark:text-gray-400 mt-2">
                        Securely manage cloud provider credentials for infrastructure provisioning
                    </p>
                </div>
                <button
                    onClick={() => setShowForm(!showForm)}
                    className="flex items-center gap-2 px-6 py-3 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl font-medium shadow-lg shadow-indigo-500/20 transition-all transform hover:scale-[1.02]"
                >
                    {showForm ? (
                        <>Cancel</>
                    ) : (
                        <>
                            <Plus className="w-5 h-5" />
                            Add Credentials
                        </>
                    )}
                </button>
            </div>

            {/* Success/Error Alerts */}
            {error && (
                <div className="mb-6 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl p-4 flex items-start gap-3 animate-in slide-in-from-top duration-300">
                    <AlertCircle className="w-5 h-5 text-red-600 dark:text-red-400 flex-shrink-0 mt-0.5" />
                    <div>
                        <h3 className="text-sm font-medium text-red-800 dark:text-red-300">Error</h3>
                        <p className="text-sm text-red-700 dark:text-red-400 mt-1">{error}</p>
                    </div>
                </div>
            )}

            {success && (
                <div className="mb-6 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-xl p-4 flex items-start gap-3 animate-in slide-in-from-top duration-300">
                    <CheckCircle2 className="w-5 h-5 text-green-600 dark:text-green-400 flex-shrink-0 mt-0.5" />
                    <div>
                        <h3 className="text-sm font-medium text-green-800 dark:text-green-300">Success</h3>
                        <p className="text-sm text-green-700 dark:text-green-400 mt-1">{success}</p>
                    </div>
                </div>
            )}

            {/* Add Credentials Form */}
            {showForm && (
                <div className="mb-8 bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-800 shadow-sm overflow-hidden">
                    <div className="p-6 border-b border-gray-100 dark:border-gray-800">
                        <h2 className="text-xl font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                            <Key className="w-5 h-5 text-indigo-500" />
                            Add New Credentials
                        </h2>
                        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                            Upload or paste your cloud provider credentials
                        </p>
                    </div>

                    <div className="p-6 space-y-6">
                        {/* Name */}
                        <div>
                            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                                Credential Name <span className="text-red-500">*</span>
                            </label>
                            <input
                                type="text"
                                value={name}
                                onChange={(e) => setName(e.target.value)}
                                placeholder="e.g., prod-gcp, dev-aws"
                                className="w-full bg-gray-50 dark:bg-gray-950 border border-gray-200 dark:border-gray-700 rounded-xl px-4 py-2.5 text-gray-900 dark:text-white focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all"
                            />
                        </div>

                        {/* Provider */}
                        <div>
                            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                                Cloud Provider <span className="text-red-500">*</span>
                            </label>
                            <select
                                value={provider}
                                onChange={(e) => {
                                    setProvider(e.target.value);
                                    if (!credentialData) {
                                        setCredentialData(getProviderExample(e.target.value));
                                    }
                                }}
                                className="w-full bg-gray-50 dark:bg-gray-950 border border-gray-200 dark:border-gray-700 rounded-xl px-4 py-2.5 text-gray-900 dark:text-white focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all"
                            >
                                <option value="gcp">Google Cloud Platform (GCP)</option>
                                <option value="aws">Amazon Web Services (AWS)</option>
                                <option value="azure">Microsoft Azure</option>
                                <option value="kubernetes">Kubernetes</option>
                            </select>
                        </div>

                        {/* File Upload (for GCP) */}
                        {provider === 'gcp' && (
                            <div>
                                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                                    Upload Service Account JSON
                                </label>
                                <div className="flex items-center gap-4">
                                    <label className="flex-1 cursor-pointer">
                                        <div className="flex items-center justify-center gap-3 px-6 py-4 bg-gray-50 dark:bg-gray-950 border-2 border-dashed border-gray-300 dark:border-gray-700 rounded-xl hover:border-indigo-500 dark:hover:border-indigo-500 transition-colors">
                                            <Upload className="w-5 h-5 text-gray-400" />
                                            <span className="text-sm text-gray-600 dark:text-gray-400">
                                                {uploadedFileName || 'Choose JSON file or drag here'}
                                            </span>
                                            <FileJson className="w-5 h-5 text-indigo-500" />
                                        </div>
                                        <input
                                            type="file"
                                            accept=".json"
                                            onChange={handleFileUpload}
                                            className="hidden"
                                        />
                                    </label>
                                </div>
                                <div className="mt-3 flex items-start gap-2 p-3 bg-blue-50 dark:bg-blue-900/10 border border-blue-200 dark:border-blue-800 rounded-lg">
                                    <Info className="w-4 h-4 text-blue-600 dark:text-blue-400 flex-shrink-0 mt-0.5" />
                                    <p className="text-xs text-blue-700 dark:text-blue-400">
                                        Download your service account key from Google Cloud Console:
                                        IAM & Admin → Service Accounts → Create Key (JSON)
                                    </p>
                                </div>
                            </div>
                        )}

                        {/* Manual JSON Input */}
                        <div>
                            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                                Credentials (JSON) <span className="text-red-500">*</span>
                            </label>
                            <textarea
                                value={credentialData}
                                onChange={(e) => setCredentialData(e.target.value)}
                                placeholder={getProviderExample(provider)}
                                rows={12}
                                className="w-full bg-gray-50 dark:bg-gray-950 border border-gray-200 dark:border-gray-700 rounded-xl px-4 py-3 text-gray-900 dark:text-green-400 focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all font-mono text-sm"
                            />
                        </div>

                        {/* Save Button */}
                        <div className="flex items-center justify-end gap-3 pt-4 border-t border-gray-100 dark:border-gray-800">
                            <button
                                onClick={() => {
                                    setShowForm(false);
                                    setName('');
                                    setCredentialData('');
                                    setUploadedFileName(null);
                                }}
                                className="px-6 py-2.5 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-xl font-medium transition-colors"
                            >
                                Cancel
                            </button>
                            <button
                                onClick={handleSave}
                                disabled={saving || !name || !credentialData}
                                className={`px-6 py-2.5 rounded-xl font-medium transition-all ${saving || !name || !credentialData
                                        ? 'bg-gray-300 dark:bg-gray-700 text-gray-500 cursor-not-allowed'
                                        : 'bg-indigo-600 hover:bg-indigo-700 text-white shadow-lg shadow-indigo-500/20'
                                    }`}
                            >
                                {saving ? (
                                    <div className="flex items-center gap-2">
                                        <Loader className="w-4 h-4 animate-spin" />
                                        Saving...
                                    </div>
                                ) : (
                                    'Save Credentials'
                                )}
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Credentials List */}
            <div>
                <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">Configured Credentials</h2>
                {credentials.length === 0 ? (
                    <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-2xl p-12 text-center">
                        <div className="inline-flex p-4 bg-gray-100 dark:bg-gray-800 rounded-full mb-4">
                            <Key className="w-8 h-8 text-gray-400" />
                        </div>
                        <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">No credentials configured</h3>
                        <p className="text-gray-500 dark:text-gray-400 mb-6">
                            Add your first cloud provider credentials to start deploying infrastructure
                        </p>
                        <button
                            onClick={() => setShowForm(true)}
                            className="inline-flex items-center gap-2 px-6 py-3 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl font-medium shadow-lg shadow-indigo-500/20 transition-all"
                        >
                            <Plus className="w-5 h-5" />
                            Add Credentials
                        </button>
                    </div>
                ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {credentials.map((cred) => (
                            <div
                                key={cred.id}
                                className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-6 hover:shadow-lg hover:border-indigo-500/50 transition-all group"
                            >
                                <div className="flex items-start justify-between mb-4">
                                    <div className="flex-1">
                                        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">{cred.name}</h3>
                                        <span className={`inline-flex items-center px-2.5 py-1 rounded-lg text-xs font-medium border ${getProviderBadgeColor(cred.provider)}`}>
                                            {cred.provider.toUpperCase()}
                                        </span>
                                    </div>
                                    <button
                                        onClick={() => handleDelete(cred.id, cred.name)}
                                        className="p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors"
                                        title="Delete credential"
                                    >
                                        <Trash2 className="w-4 h-4" />
                                    </button>
                                </div>
                                <div className="text-xs text-gray-500 dark:text-gray-400">
                                    <p>Created: {new Date(cred.created_at).toLocaleDateString()}</p>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
};

export default CloudSettings;
