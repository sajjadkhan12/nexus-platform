import React, { useState, useEffect } from 'react';
import { appLogger } from '../utils/logger';
import {
    Cloud,
    Key,
    CheckCircle2,
    XCircle,
    Loader2,
    Copy,
    Eye,
    EyeOff,
    RefreshCw,
    Info,
    AlertCircle,
    Shield,
    Globe
} from 'lucide-react';
import { oidcApi, AssumeRoleRequest, GCPTokenRequest, AzureTokenRequest } from '../services/api/oidc';
import { useAuth } from '../contexts/AuthContext';

type CloudProvider = 'aws' | 'gcp' | 'azure';

interface Credentials {
    aws?: {
        access_key_id: string;
        secret_access_key: string;
        session_token: string;
        expiration: string;
        region: string;
    };
    gcp?: {
        access_token: string;
        token_type: string;
        expires_in: number;
    };
    azure?: {
        access_token: string;
        token_type: string;
        expires_in: number;
        resource: string;
    };
}

const OIDCTestPage: React.FC = () => {
    const { user } = useAuth();
    const [activeTab, setActiveTab] = useState<CloudProvider>('aws');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [success, setSuccess] = useState<string | null>(null);
    const [credentials, setCredentials] = useState<Credentials>({});
    const [showSecrets, setShowSecrets] = useState<{ [key: string]: boolean }>({});
    const [oidcConfig, setOidcConfig] = useState<any>(null);

    // AWS form state
    const [awsRoleArn, setAwsRoleArn] = useState('');
    const [awsSessionName, setAwsSessionName] = useState('');
    const [awsDuration, setAwsDuration] = useState(3600);

    // GCP form state
    const [gcpServiceAccount, setGcpServiceAccount] = useState('');
    const [gcpScope, setGcpScope] = useState('https://www.googleapis.com/auth/cloud-platform');

    // Azure form state
    const [azureScope, setAzureScope] = useState('https://management.azure.com/.default');

    useEffect(() => {
        loadOIDCConfig();
    }, []);

    const loadOIDCConfig = async () => {
        try {
            const config = await oidcApi.getOIDCConfig();
            setOidcConfig(config);
        } catch (err) {
            appLogger.error('Failed to load OIDC config:', err);
        }
    };

    const toggleSecret = (key: string) => {
        setShowSecrets(prev => ({ ...prev, [key]: !prev[key] }));
    };

    const copyToClipboard = (text: string) => {
        navigator.clipboard.writeText(text);
        setSuccess('Copied to clipboard!');
        setTimeout(() => setSuccess(null), 2000);
    };

    const handleAWSAssumeRole = async () => {
        setLoading(true);
        setError(null);
        setSuccess(null);

        try {
            const request: AssumeRoleRequest = {
                ...(awsRoleArn && { role_arn: awsRoleArn }),
                ...(awsSessionName && { role_session_name: awsSessionName }),
                duration_seconds: awsDuration
            };

            const response = await oidcApi.assumeAWSRole(request);
            setCredentials(prev => ({ ...prev, aws: response }));
            setSuccess('AWS credentials retrieved successfully!');
        } catch (err: any) {
            setError(err.message || 'Failed to assume AWS role');
        } finally {
            setLoading(false);
        }
    };

    const handleGCPToken = async () => {
        setLoading(true);
        setError(null);
        setSuccess(null);

        try {
            const request: GCPTokenRequest = {
                ...(gcpServiceAccount && { service_account_email: gcpServiceAccount }),
                scope: gcpScope
            };

            const response = await oidcApi.getGCPToken(request);
            setCredentials(prev => ({ ...prev, gcp: response }));
            setSuccess('GCP access token retrieved successfully!');
        } catch (err: any) {
            setError(err.message || 'Failed to get GCP token');
        } finally {
            setLoading(false);
        }
    };

    const handleAzureToken = async () => {
        setLoading(true);
        setError(null);
        setSuccess(null);

        try {
            const request: AzureTokenRequest = {
                scope: azureScope
            };

            const response = await oidcApi.getAzureToken(request);
            setCredentials(prev => ({ ...prev, azure: response }));
            setSuccess('Azure access token retrieved successfully!');
        } catch (err: any) {
            setError(err.message || 'Failed to get Azure token');
        } finally {
            setLoading(false);
        }
    };

    const renderAWS = () => (
        <div className="space-y-6">
            <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
                <div className="flex items-start gap-3">
                    <Info className="w-5 h-5 text-blue-600 dark:text-blue-400 mt-0.5" />
                    <div className="text-sm text-blue-800 dark:text-blue-200">
                        <p className="font-medium mb-1">AWS Workload Identity Federation</p>
                        <p>This will generate an OIDC token and exchange it for AWS credentials using AssumeRoleWithWebIdentity.</p>
                        <p className="mt-2 text-xs">Role ARN is optional if configured in backend .env file.</p>
                    </div>
                </div>
            </div>

            <div className="space-y-4">
                <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                        IAM Role ARN (Optional)
                    </label>
                    <input
                        type="text"
                        value={awsRoleArn}
                        onChange={(e) => setAwsRoleArn(e.target.value)}
                        placeholder="arn:aws:iam::123456789012:role/MyRole"
                        className="w-full px-4 py-2 border border-gray-300 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-orange-500 focus:border-transparent"
                    />
                </div>

                <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                        Session Name (Optional)
                    </label>
                    <input
                        type="text"
                        value={awsSessionName}
                        onChange={(e) => setAwsSessionName(e.target.value)}
                        placeholder="my-session"
                        className="w-full px-4 py-2 border border-gray-300 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-orange-500 focus:border-transparent"
                    />
                </div>

                <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                        Duration (seconds)
                    </label>
                    <input
                        type="number"
                        value={awsDuration}
                        onChange={(e) => setAwsDuration(parseInt(e.target.value) || 3600)}
                        min={900}
                        max={43200}
                        className="w-full px-4 py-2 border border-gray-300 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-orange-500 focus:border-transparent"
                    />
                </div>

                <button
                    onClick={handleAWSAssumeRole}
                    disabled={loading}
                    className="w-full bg-orange-600 text-white px-6 py-3 rounded-lg font-medium hover:bg-orange-500 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 transition-colors"
                >
                    {loading ? (
                        <>
                            <Loader2 className="w-5 h-5 animate-spin" />
                            Requesting Credentials...
                        </>
                    ) : (
                        <>
                            <Key className="w-5 h-5" />
                            Get AWS Credentials
                        </>
                    )}
                </button>
            </div>

            {credentials.aws && (
                <div className="mt-6 space-y-4">
                    <h3 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                        <CheckCircle2 className="w-5 h-5 text-green-500" />
                        AWS Credentials
                    </h3>
                    <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4 space-y-3">
                        <CredentialField
                            label="Access Key ID"
                            value={credentials.aws.access_key_id}
                            onCopy={() => copyToClipboard(credentials.aws!.access_key_id)}
                        />
                        <CredentialField
                            label="Secret Access Key"
                            value={credentials.aws.secret_access_key}
                            secret
                            showSecret={showSecrets['aws_secret']}
                            onToggle={() => toggleSecret('aws_secret')}
                            onCopy={() => copyToClipboard(credentials.aws!.secret_access_key)}
                        />
                        <CredentialField
                            label="Session Token"
                            value={credentials.aws.session_token}
                            secret
                            showSecret={showSecrets['aws_token']}
                            onToggle={() => toggleSecret('aws_token')}
                            onCopy={() => copyToClipboard(credentials.aws!.session_token)}
                        />
                        <CredentialField
                            label="Expiration"
                            value={new Date(credentials.aws.expiration).toLocaleString()}
                        />
                        <CredentialField
                            label="Region"
                            value={credentials.aws.region}
                        />
                    </div>
                </div>
            )}
        </div>
    );

    const renderGCP = () => (
        <div className="space-y-6">
            <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-4">
                <div className="flex items-start gap-3">
                    <Info className="w-5 h-5 text-green-600 dark:text-green-400 mt-0.5" />
                    <div className="text-sm text-green-800 dark:text-green-200">
                        <p className="font-medium mb-1">GCP Workload Identity Federation</p>
                        <p>This will generate an OIDC token and exchange it for a GCP access token via Workload Identity Federation.</p>
                    </div>
                </div>
            </div>

            <div className="space-y-4">
                <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                        Service Account Email (Optional)
                    </label>
                    <input
                        type="text"
                        value={gcpServiceAccount}
                        onChange={(e) => setGcpServiceAccount(e.target.value)}
                        placeholder="my-sa@project.iam.gserviceaccount.com"
                        className="w-full px-4 py-2 border border-gray-300 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-orange-500 focus:border-transparent"
                    />
                </div>

                <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                        Scope
                    </label>
                    <input
                        type="text"
                        value={gcpScope}
                        onChange={(e) => setGcpScope(e.target.value)}
                        className="w-full px-4 py-2 border border-gray-300 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-orange-500 focus:border-transparent"
                    />
                </div>

                <button
                    onClick={handleGCPToken}
                    disabled={loading}
                    className="w-full bg-orange-600 text-white px-6 py-3 rounded-lg font-medium hover:bg-orange-500 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 transition-colors"
                >
                    {loading ? (
                        <>
                            <Loader2 className="w-5 h-5 animate-spin" />
                            Requesting Token...
                        </>
                    ) : (
                        <>
                            <Key className="w-5 h-5" />
                            Get GCP Access Token
                        </>
                    )}
                </button>
            </div>

            {credentials.gcp && (
                <div className="mt-6 space-y-4">
                    <h3 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                        <CheckCircle2 className="w-5 h-5 text-green-500" />
                        GCP Access Token
                    </h3>
                    <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4 space-y-3">
                        <CredentialField
                            label="Access Token"
                            value={credentials.gcp.access_token}
                            secret
                            showSecret={showSecrets['gcp_token']}
                            onToggle={() => toggleSecret('gcp_token')}
                            onCopy={() => copyToClipboard(credentials.gcp!.access_token)}
                        />
                        <CredentialField
                            label="Token Type"
                            value={credentials.gcp.token_type}
                        />
                        <CredentialField
                            label="Expires In"
                            value={`${credentials.gcp.expires_in} seconds`}
                        />
                    </div>
                </div>
            )}
        </div>
    );

    const renderAzure = () => (
        <div className="space-y-6">
            <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
                <div className="flex items-start gap-3">
                    <Info className="w-5 h-5 text-blue-600 dark:text-blue-400 mt-0.5" />
                    <div className="text-sm text-blue-800 dark:text-blue-200">
                        <p className="font-medium mb-1">Azure Federated Identity Credential</p>
                        <p>This will generate an OIDC token and exchange it for an Azure access token using Federated Identity Credential flow.</p>
                    </div>
                </div>
            </div>

            <div className="space-y-4">
                <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                        Scope
                    </label>
                    <input
                        type="text"
                        value={azureScope}
                        onChange={(e) => setAzureScope(e.target.value)}
                        className="w-full px-4 py-2 border border-gray-300 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-orange-500 focus:border-transparent"
                    />
                </div>

                <button
                    onClick={handleAzureToken}
                    disabled={loading}
                    className="w-full bg-orange-600 text-white px-6 py-3 rounded-lg font-medium hover:bg-orange-500 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 transition-colors"
                >
                    {loading ? (
                        <>
                            <Loader2 className="w-5 h-5 animate-spin" />
                            Requesting Token...
                        </>
                    ) : (
                        <>
                            <Key className="w-5 h-5" />
                            Get Azure Access Token
                        </>
                    )}
                </button>
            </div>

            {credentials.azure && (
                <div className="mt-6 space-y-4">
                    <h3 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                        <CheckCircle2 className="w-5 h-5 text-blue-500" />
                        Azure Access Token
                    </h3>
                    <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4 space-y-3">
                        <CredentialField
                            label="Access Token"
                            value={credentials.azure.access_token}
                            secret
                            showSecret={showSecrets['azure_token']}
                            onToggle={() => toggleSecret('azure_token')}
                            onCopy={() => copyToClipboard(credentials.azure!.access_token)}
                        />
                        <CredentialField
                            label="Token Type"
                            value={credentials.azure.token_type}
                        />
                        <CredentialField
                            label="Expires In"
                            value={`${credentials.azure.expires_in} seconds`}
                        />
                        <CredentialField
                            label="Resource"
                            value={credentials.azure.resource}
                        />
                    </div>
                </div>
            )}
        </div>
    );

    return (
        <div className="space-y-6 animate-in fade-in duration-500">
            <div className="flex justify-between items-center">
                <div>
                    <h1 className="text-3xl font-bold text-gray-900 dark:text-white flex items-center gap-3">
                        <Shield className="w-8 h-8 text-orange-600" />
                        OIDC Workload Identity Test
                    </h1>
                    <p className="text-gray-500 dark:text-gray-400 mt-1">
                        Test workload identity federation with AWS, GCP, and Azure
                    </p>
                </div>
            </div>

            {oidcConfig && (
                <div className="bg-white dark:bg-gray-900 p-4 rounded-lg border border-gray-200 dark:border-gray-800">
                    <div className="flex items-center gap-2 text-sm">
                        <Globe className="w-4 h-4 text-gray-500" />
                        <span className="text-gray-600 dark:text-gray-400">Issuer:</span>
                        <span className="font-mono text-gray-900 dark:text-white">{oidcConfig.issuer}</span>
                    </div>
                </div>
            )}

            {error && (
                <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4 flex items-start gap-3">
                    <XCircle className="w-5 h-5 text-red-600 dark:text-red-400 mt-0.5" />
                    <div className="flex-1">
                        <p className="text-sm font-medium text-red-800 dark:text-red-200">Error</p>
                        <p className="text-sm text-red-700 dark:text-red-300 mt-1">{error}</p>
                    </div>
                </div>
            )}

            {success && (
                <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-4 flex items-start gap-3">
                    <CheckCircle2 className="w-5 h-5 text-green-600 dark:text-green-400 mt-0.5" />
                    <p className="text-sm text-green-800 dark:text-green-200">{success}</p>
                </div>
            )}

            <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-800 overflow-hidden">
                <div className="border-b border-gray-200 dark:border-gray-800">
                    <div className="flex">
                        {(['aws', 'gcp', 'azure'] as CloudProvider[]).map((provider) => (
                            <button
                                key={provider}
                                onClick={() => setActiveTab(provider)}
                                className={`flex-1 px-6 py-4 text-sm font-medium transition-colors ${
                                    activeTab === provider
                                        ? 'bg-orange-50 dark:bg-orange-900/20 text-orange-600 dark:text-orange-400 border-b-2 border-orange-600'
                                        : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white hover:bg-gray-50 dark:hover:bg-gray-800'
                                }`}
                            >
                                <div className="flex items-center justify-center gap-2">
                                    <Cloud className="w-5 h-5" />
                                    {provider.toUpperCase()}
                                </div>
                            </button>
                        ))}
                    </div>
                </div>

                <div className="p-6">
                    {activeTab === 'aws' && renderAWS()}
                    {activeTab === 'gcp' && renderGCP()}
                    {activeTab === 'azure' && renderAzure()}
                </div>
            </div>
        </div>
    );
};

interface CredentialFieldProps {
    label: string;
    value: string;
    secret?: boolean;
    showSecret?: boolean;
    onToggle?: () => void;
    onCopy: () => void;
}

const CredentialField: React.FC<CredentialFieldProps> = ({
    label,
    value,
    secret = false,
    showSecret = false,
    onToggle,
    onCopy
}) => (
    <div>
        <div className="flex items-center justify-between mb-1">
            <label className="text-xs font-medium text-gray-600 dark:text-gray-400">{label}</label>
            <div className="flex items-center gap-2">
                {secret && onToggle && (
                    <button
                        onClick={onToggle}
                        className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
                    >
                        {showSecret ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                )}
                <button
                    onClick={onCopy}
                    className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
                    title="Copy to clipboard"
                >
                    <Copy className="w-4 h-4" />
                </button>
            </div>
        </div>
        <div className="font-mono text-sm bg-white dark:bg-gray-900 px-3 py-2 rounded border border-gray-200 dark:border-gray-700 text-gray-900 dark:text-white break-all">
            {secret && !showSecret ? '•'.repeat(20) : value}
        </div>
    </div>
);

export default OIDCTestPage;


