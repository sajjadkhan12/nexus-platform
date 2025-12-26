import React, { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { Upload, FileArchive, CheckCircle2, AlertCircle, Info, Code, FileText, Zap, Server, Box } from 'lucide-react';
import api from '../services/api';
import { useAuth } from '../contexts/AuthContext';

const PluginUpload: React.FC = () => {
    const { isAdmin, loading: authLoading, hasPermission } = useAuth();
    const navigate = useNavigate();
    const [deploymentType, setDeploymentType] = useState<'infrastructure' | 'microservice'>('infrastructure');
    const [file, setFile] = useState<File | null>(null);
    const [uploading, setUploading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [success, setSuccess] = useState<string | null>(null);
    const [pluginName, setPluginName] = useState('');
    const [version, setVersion] = useState('');
    const [description, setDescription] = useState('');
    const [dragActive, setDragActive] = useState(false);
    // Microservice-specific fields
    const [templateRepoUrl, setTemplateRepoUrl] = useState('');
    const [templatePath, setTemplatePath] = useState('');

    useEffect(() => {
        if (!authLoading && !isAdmin && !hasPermission('platform:plugins:upload')) {
            navigate('/');
        }
    }, [authLoading, isAdmin, hasPermission, navigate]);

    if (authLoading) {
        return null;
    }



    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const selectedFile = e.target.files?.[0];
        if (selectedFile) {
            if (!selectedFile.name.endsWith('.zip')) {
                setError('Please select a ZIP file');
                setFile(null);
                return;
            }
            setFile(selectedFile);
            setError(null);
            setSuccess(null);
        }
    };

    const slugify = (value: string) => {
        return value
            .toLowerCase()
            .replace(/\s+/g, '-')
            .replace(/_/g, '-')
            .replace(/[^a-z0-9-]/g, '-')
            .replace(/-+/g, '-')
            .replace(/^-|-$/g, '');
    };

    const templateBranch = useMemo(() => {
        if (!pluginName.trim()) return '';
        const base = slugify(pluginName.trim());
        return base ? `plugin-${base}` : '';
    }, [pluginName]);

    const handleDrag = (e: React.DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
        if (e.type === "dragenter" || e.type === "dragover") {
            setDragActive(true);
        } else if (e.type === "dragleave") {
            setDragActive(false);
        }
    };

    const handleDrop = (e: React.DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
        setDragActive(false);

        const droppedFile = e.dataTransfer.files?.[0];
        if (droppedFile) {
            if (!droppedFile.name.endsWith('.zip')) {
                setError('Please select a ZIP file');
                setFile(null);
                return;
            }
            setFile(droppedFile);
            setError(null);
            setSuccess(null);
        }
    };

    const handleUpload = async () => {
        if (!pluginName.trim()) {
            setError('Please provide a plugin name.');
            return;
        }

        if (!version.trim()) {
            setError('Please provide a version.');
            return;
        }

        if (!description.trim()) {
            setError('Please provide a short description.');
            return;
        }

        if (deploymentType === 'infrastructure') {
            if (!file) {
                setError('Please select a plugin package (.zip).');
                return;
            }
        } else {
            // Microservice validation
            if (!templateRepoUrl.trim()) {
                setError('Please provide a template repository URL.');
                return;
            }
            if (!templatePath.trim()) {
                setError('Please provide a template path (subdirectory).');
                return;
            }
        }

        setUploading(true);
        setError(null);
        setSuccess(null);

        try {
            if (deploymentType === 'infrastructure') {
                // Existing infrastructure upload
                const result = await api.uploadPlugin(file!, {
                    gitBranch: templateBranch || undefined
                });
                setSuccess(`✅ Plugin "${result.plugin_id || pluginName}" v${result.version || version} uploaded successfully. Template branch: ${templateBranch || result.git_branch || 'n/a'}`);
            } else {
                // Microservice template upload
                const pluginId = slugify(pluginName);
                const result = await api.uploadMicroserviceTemplate({
                    plugin_id: pluginId,
                    name: pluginName,
                    version: version,
                    description: description,
                    template_repo_url: templateRepoUrl,
                    template_path: templatePath
                });
                setSuccess(`✅ Microservice template "${result.plugin_id || pluginName}" v${result.version || version} created successfully.`);
            }
            
            // Reset form
            setFile(null);
            setPluginName('');
            setVersion('');
            setDescription('');
            setTemplateRepoUrl('');
            setTemplatePath('');
            // Reset file input
            const fileInput = document.getElementById('plugin-file') as HTMLInputElement;
            if (fileInput) fileInput.value = '';
        } catch (err: any) {
            setError(err.message || 'Upload failed');
        } finally {
            setUploading(false);
        }
    };

    return (
        <div className="max-w-7xl mx-auto">
            {/* Header */}
            <div className="mb-8">
                <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">Upload Plugin</h1>
                <p className="text-gray-600 dark:text-gray-400">
                    Upload infrastructure plugins or microservice templates to extend your platform capabilities
                </p>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                {/* Left Column - Metadata + Upload Form */}
                <div className="lg:col-span-2 space-y-6">
                    {/* Deployment Type Toggle */}
                    <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-6">
                        <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">
                            Deployment Type
                        </h2>
                        <div className="flex gap-4">
                            <button
                                type="button"
                                onClick={() => {
                                    setDeploymentType('infrastructure');
                                    setFile(null);
                                    setError(null);
                                }}
                                className={`flex-1 flex items-center justify-center gap-3 px-4 py-3 rounded-lg font-medium transition-all ${
                                    deploymentType === 'infrastructure'
                                        ? 'bg-orange-600 text-white shadow-lg shadow-orange-500/30'
                                        : 'bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700'
                                }`}
                            >
                                <Server className="w-5 h-5" />
                                Infrastructure
                            </button>
                            <button
                                type="button"
                                onClick={() => {
                                    setDeploymentType('microservice');
                                    setFile(null);
                                    setError(null);
                                }}
                                className={`flex-1 flex items-center justify-center gap-3 px-4 py-3 rounded-lg font-medium transition-all ${
                                    deploymentType === 'microservice'
                                        ? 'bg-orange-600 text-white shadow-lg shadow-orange-500/30'
                                        : 'bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700'
                                }`}
                            >
                                <Box className="w-5 h-5" />
                                Microservice Template
                            </button>
                        </div>
                    </div>

                    {/* Metadata Card */}
                    <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-6">
                        <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-6">
                            Plugin Details
                        </h2>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                            <div>
                                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                                    Plugin Name
                                </label>
                                <input
                                    type="text"
                                    placeholder={deploymentType === 'microservice' ? "e.g. Python Microservice" : "e.g. GCP Bucket"}
                                    value={pluginName}
                                    onChange={(e) => setPluginName(e.target.value)}
                                    className="w-full px-3 py-2 rounded-lg bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-700 text-gray-900 dark:text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-orange-500"
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                                    Version
                                </label>
                                <input
                                    type="text"
                                    placeholder="e.g. 1.0.0"
                                    value={version}
                                    onChange={(e) => setVersion(e.target.value)}
                                    className="w-full px-3 py-2 rounded-lg bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-700 text-gray-900 dark:text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-orange-500"
                                />
                            </div>
                        </div>

                        <div className="mb-4">
                            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                                Description
                            </label>
                            <textarea
                                rows={3}
                                placeholder="Describe what this plugin does..."
                                value={description}
                                onChange={(e) => setDescription(e.target.value)}
                                className="w-full px-3 py-2 rounded-lg bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-700 text-gray-900 dark:text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-orange-500 resize-none"
                            />
                        </div>

                        {/* Microservice-specific fields */}
                        {deploymentType === 'microservice' && (
                            <div className="space-y-4 pt-4 border-t border-gray-200 dark:border-gray-700">
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                                        Template Repository URL <span className="text-red-500">*</span>
                                    </label>
                                    <input
                                        type="text"
                                        placeholder="https://github.com/org/repo.git"
                                        value={templateRepoUrl}
                                        onChange={(e) => setTemplateRepoUrl(e.target.value)}
                                        className="w-full px-3 py-2 rounded-lg bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-700 text-gray-900 dark:text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-orange-500"
                                    />
                                    <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                                        GitHub repository containing the template
                                    </p>
                                </div>
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                                        Template Path <span className="text-red-500">*</span>
                                    </label>
                                    <input
                                        type="text"
                                        placeholder="e.g. python-service"
                                        value={templatePath}
                                        onChange={(e) => setTemplatePath(e.target.value)}
                                        className="w-full px-3 py-2 rounded-lg bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-700 text-gray-900 dark:text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-orange-500"
                                    />
                                    <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                                        Subdirectory path in the repository (e.g., "python-service" for idp-templates/python-service)
                                    </p>
                                </div>
                            </div>
                        )}

                        {/* Infrastructure-specific info */}
                        {deploymentType === 'infrastructure' && (
                            <div className="text-sm text-gray-600 dark:text-gray-400">
                                <span className="font-medium text-gray-700 dark:text-gray-300">Template branch:</span>{' '}
                                <code className="px-1.5 py-0.5 rounded bg-gray-100 dark:bg-gray-800 border border-gray-300 dark:border-gray-700 text-xs">
                                    {templateBranch || 'plugin-&lt;plugin-name&gt;'}
                                </code>
                                <span className="ml-1 text-gray-500 dark:text-gray-500">
                                    {' '}
                                    All deployments for this plugin will be created from this template branch.
                                </span>
                            </div>
                        )}
                    </div>

                    {/* Upload Card - Only show for infrastructure */}
                    {deploymentType === 'infrastructure' && (
                        <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-6">
                            <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-6">Plugin Package (.zip)</h2>

                        {/* Drag & Drop Zone */}
                        <div
                            onDragEnter={handleDrag}
                            onDragLeave={handleDrag}
                            onDragOver={handleDrag}
                            onDrop={handleDrop}
                            className={`relative border-2 border-dashed rounded-lg p-8 text-center transition-all ${dragActive
                                ? 'border-orange-500 bg-orange-50 dark:bg-orange-500/10'
                                : 'border-gray-300 dark:border-gray-700 hover:border-gray-400 dark:hover:border-gray-600'
                                }`}
                        >
                            <input
                                id="plugin-file"
                                type="file"
                                accept=".zip"
                                onChange={handleFileChange}
                                className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                            />

                            <div className="flex flex-col items-center">
                                <div className="w-16 h-16 bg-orange-100 dark:bg-orange-500/20 rounded-full flex items-center justify-center mb-4">
                                    <Upload className="w-8 h-8 text-orange-600 dark:text-orange-400" />
                                </div>
                                <p className="text-lg font-medium text-gray-900 dark:text-white mb-2">
                                    Drag & drop your plugin ZIP file
                                </p>
                                <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
                                    or click to browse
                                </p>
                                <p className="text-xs text-gray-400 dark:text-gray-500">
                                    Maximum file size: 50MB
                                </p>
                            </div>
                        </div>

                        {/* File Info */}
                        {file && (
                            <div className="mt-4 p-4 bg-gray-50 dark:bg-gray-800/50 rounded-lg border border-gray-200 dark:border-gray-700">
                                <div className="flex items-center justify-between">
                                    <div className="flex items-center gap-3">
                                        <FileArchive className="w-5 h-5 text-orange-600 dark:text-orange-400" />
                                        <div>
                                            <p className="font-medium text-gray-900 dark:text-white">{file.name}</p>
                                            <p className="text-sm text-gray-500 dark:text-gray-400">
                                                {(file.size / 1024).toFixed(2)} KB
                                            </p>
                                        </div>
                                    </div>
                                    <CheckCircle2 className="w-5 h-5 text-green-600 dark:text-green-400" />
                                </div>
                            </div>
                        )}

                        </div>
                    )}

                    {/* Error/Success Messages - Moved outside upload card */}
                    {error && (
                        <div className="p-4 bg-red-50 dark:bg-red-500/10 border border-red-200 dark:border-red-500/30 rounded-lg flex items-start gap-3">
                            <AlertCircle className="w-5 h-5 text-red-600 dark:text-red-400 flex-shrink-0 mt-0.5" />
                            <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
                        </div>
                    )}

                    {success && (
                        <div className="p-4 bg-green-50 dark:bg-green-500/10 border border-green-200 dark:border-green-500/30 rounded-lg flex items-start gap-3">
                            <CheckCircle2 className="w-5 h-5 text-green-600 dark:text-green-400 flex-shrink-0 mt-0.5" />
                            <p className="text-sm text-green-600 dark:text-green-400">{success}</p>
                        </div>
                    )}

                    {/* Upload Button */}
                    <button
                        onClick={handleUpload}
                        disabled={uploading || (deploymentType === 'infrastructure' && !file) || (deploymentType === 'microservice' && (!templateRepoUrl || !templatePath))}
                        className={`w-full py-3 px-4 rounded-lg font-medium transition-all ${
                            !uploading && ((deploymentType === 'infrastructure' && file) || (deploymentType === 'microservice' && templateRepoUrl && templatePath))
                                ? 'bg-orange-600 hover:bg-orange-700 text-white shadow-lg shadow-orange-500/30'
                                : 'bg-gray-200 dark:bg-gray-800 text-gray-400 dark:text-gray-500 cursor-not-allowed'
                        }`}
                    >
                        {uploading ? (
                            <span className="flex items-center justify-center gap-2">
                                <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                                </svg>
                                {deploymentType === 'infrastructure' ? 'Uploading...' : 'Creating...'}
                            </span>
                        ) : (
                            deploymentType === 'infrastructure' ? 'Upload Plugin' : 'Create Microservice Template'
                        )}
                    </button>
                </div>

                {/* Right Column - Documentation */}
                <div className="space-y-6">
                    {/* Show different documentation based on deployment type */}
                    {deploymentType === 'infrastructure' ? (
                        <>
                            {/* Quick Start */}
                            <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-6">
                                <div className="flex items-center gap-2 mb-4">
                                    <Info className="w-5 h-5 text-orange-600 dark:text-orange-400" />
                                    <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Package Requirements</h3>
                                </div>
                                <ul className="space-y-3">
                                    <li className="flex items-start gap-2 text-sm">
                                        <CheckCircle2 className="w-4 h-4 text-green-600 dark:text-green-400 mt-0.5 flex-shrink-0" />
                                        <span className="text-gray-600 dark:text-gray-400">ZIP archive format</span>
                                    </li>
                                    <li className="flex items-start gap-2 text-sm">
                                        <CheckCircle2 className="w-4 h-4 text-green-600 dark:text-green-400 mt-0.5 flex-shrink-0" />
                                        <span className="text-gray-600 dark:text-gray-400">
                                            <code className="px-1.5 py-0.5 bg-gray-100 dark:bg-gray-800 rounded text-xs font-mono">plugin.yaml</code> manifest
                                        </span>
                                    </li>
                                    <li className="flex items-start gap-2 text-sm">
                                        <CheckCircle2 className="w-4 h-4 text-green-600 dark:text-green-400 mt-0.5 flex-shrink-0" />
                                        <span className="text-gray-600 dark:text-gray-400">
                                            <code className="px-1.5 py-0.5 bg-gray-100 dark:bg-gray-800 rounded text-xs font-mono">Pulumi.yaml</code> project file
                                        </span>
                                    </li>
                                    <li className="flex items-start gap-2 text-sm">
                                        <CheckCircle2 className="w-4 h-4 text-green-600 dark:text-green-400 mt-0.5 flex-shrink-0" />
                                        <span className="text-gray-600 dark:text-gray-400">
                                            Entrypoint file (e.g., <code className="px-1.5 py-0.5 bg-gray-100 dark:bg-gray-800 rounded text-xs font-mono">__main__.py</code>)
                                        </span>
                                    </li>
                                </ul>
                            </div>

                            {/* Plugin Structure */}
                            <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-6">
                                <div className="flex items-center gap-2 mb-4">
                                    <Code className="w-5 h-5 text-orange-500 dark:text-orange-400" />
                                    <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Structure Guide</h3>
                                </div>
                        <div className="bg-gradient-to-br from-gray-900 via-slate-900 to-gray-950 rounded-lg p-4 font-mono text-xs border border-gray-800">
                            <div className="text-gray-400 space-y-1">
                                <div className="text-amber-300 font-semibold">
                                    my-plugin/
                                </div>
                                <div className="pl-4 flex items-center gap-2">
                                    <span className="w-3 h-px bg-amber-400/60 rounded"></span>
                                    <span className="text-sky-300">plugin.yaml</span>
                                </div>
                                <div className="pl-4 flex items-center gap-2">
                                    <span className="w-3 h-px bg-amber-400/60 rounded"></span>
                                    <span className="text-sky-300">Pulumi.yaml</span>
                                </div>
                                <div className="pl-4 flex items-center gap-2">
                                    <span className="w-3 h-px bg-emerald-400/60 rounded"></span>
                                    <span className="text-emerald-300">__main__.py</span>
                                </div>
                                <div className="pl-8 flex items-center gap-2">
                                    <span className="w-3 h-px bg-gray-500/70 rounded"></span>
                                    <span className="text-gray-300">requirements.txt</span>
                                </div>
                                <div className="pl-4 text-amber-300 font-semibold pt-1">
                                    assets/
                                </div>
                                <div className="pl-8 flex items-center gap-2">
                                    <span className="w-3 h-px bg-sky-400/70 rounded"></span>
                                    <span className="text-sky-300">icon.png</span>
                                </div>
                            </div>
                        </div>
                    </div>

                            {/* Example Manifest */}
                            <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-6">
                                <div className="flex items-center gap-2 mb-4">
                                    <FileText className="w-5 h-5 text-orange-600 dark:text-orange-400" />
                                    <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Example Manifest</h3>
                                </div>
                                <div className="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-4 font-mono text-xs overflow-x-auto">
                                    <pre className="text-gray-600 dark:text-gray-400">
                                        {`id: my-plugin
name: My Plugin
version: 1.0.0
cloud_provider: gcp
entrypoint: __main__.py`}
                                    </pre>
                                </div>
                            </div>

                            {/* Quick Tip */}
                            <div className="bg-gradient-to-br from-orange-50 to-orange-50 dark:from-orange-500/10 dark:to-orange-500/10 rounded-xl border border-orange-200 dark:border-orange-500/30 p-6">
                                <div className="flex items-start gap-3">
                                    <div className="w-10 h-10 bg-orange-600 dark:bg-orange-500 rounded-lg flex items-center justify-center flex-shrink-0">
                                        <Zap className="w-5 h-5 text-white" />
                                    </div>
                                    <div>
                                        <h4 className="font-semibold text-gray-900 dark:text-white mb-2">Quick Tip</h4>
                                        <p className="text-sm text-gray-600 dark:text-gray-400">
                                            Check out the example GKE plugin in the <code className="px-1.5 py-0.5 bg-white dark:bg-gray-800 rounded text-xs font-mono">plugins/</code> directory to get started quickly!
                                        </p>
                                    </div>
                                </div>
                            </div>
                        </>
                    ) : (
                        <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-6">
                            <div className="flex items-center gap-2 mb-4">
                                <Info className="w-5 h-5 text-orange-600 dark:text-orange-400" />
                                <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Microservice Template</h3>
                            </div>
                            <ul className="space-y-3">
                                <li className="flex items-start gap-2 text-sm">
                                    <CheckCircle2 className="w-4 h-4 text-green-600 dark:text-green-400 mt-0.5 flex-shrink-0" />
                                    <span className="text-gray-600 dark:text-gray-400">Reference to a GitHub repository</span>
                                </li>
                                <li className="flex items-start gap-2 text-sm">
                                    <CheckCircle2 className="w-4 h-4 text-green-600 dark:text-green-400 mt-0.5 flex-shrink-0" />
                                    <span className="text-gray-600 dark:text-gray-400">Specify subdirectory path in the repository</span>
                                </li>
                                <li className="flex items-start gap-2 text-sm">
                                    <CheckCircle2 className="w-4 h-4 text-green-600 dark:text-green-400 mt-0.5 flex-shrink-0" />
                                    <span className="text-gray-600 dark:text-gray-400">Template should include Dockerfile and CI/CD workflows</span>
                                </li>
                            </ul>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

export default PluginUpload;
