import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Upload, FileArchive, CheckCircle2, AlertCircle, Info, Code, FileText, Zap } from 'lucide-react';
import api from '../services/api';
import { useAuth } from '../contexts/AuthContext';

const PluginUpload: React.FC = () => {
    const { isAdmin, loading: authLoading } = useAuth();
    const navigate = useNavigate();
    const [file, setFile] = useState<File | null>(null);
    const [uploading, setUploading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [success, setSuccess] = useState<string | null>(null);
    const [dragActive, setDragActive] = useState(false);

    useEffect(() => {
        if (!authLoading && !isAdmin) {
            navigate('/');
        }
    }, [authLoading, isAdmin, navigate]);

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
        if (!file) {
            setError('Please select a file');
            return;
        }

        setUploading(true);
        setError(null);
        setSuccess(null);

        try {
            const result = await api.uploadPlugin(file);
            setSuccess(`✅ Plugin "${result.plugin_id}" v${result.version} uploaded successfully!`);
            setFile(null);
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
                    Upload infrastructure-as-code plugins to extend your platform capabilities
                </p>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                {/* Left Column - Upload Form */}
                <div className="lg:col-span-2 space-y-6">
                    {/* Upload Card */}
                    <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-6">
                        <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-6">Upload Package</h2>

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

                        {/* Error Message */}
                        {error && (
                            <div className="mt-4 p-4 bg-red-50 dark:bg-red-500/10 border border-red-200 dark:border-red-500/30 rounded-lg flex items-start gap-3">
                                <AlertCircle className="w-5 h-5 text-red-600 dark:text-red-400 flex-shrink-0 mt-0.5" />
                                <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
                            </div>
                        )}

                        {/* Success Message */}
                        {success && (
                            <div className="mt-4 p-4 bg-green-50 dark:bg-green-500/10 border border-green-200 dark:border-green-500/30 rounded-lg flex items-start gap-3">
                                <CheckCircle2 className="w-5 h-5 text-green-600 dark:text-green-400 flex-shrink-0 mt-0.5" />
                                <p className="text-sm text-green-600 dark:text-green-400">{success}</p>
                            </div>
                        )}

                        {/* Upload Button */}
                        <button
                            onClick={handleUpload}
                            disabled={!file || uploading}
                            className={`mt-6 w-full py-3 px-4 rounded-lg font-medium transition-all ${file && !uploading
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
                                    Uploading...
                                </span>
                            ) : (
                                'Upload Plugin'
                            )}
                        </button>
                    </div>
                </div>

                {/* Right Column - Documentation */}
                <div className="space-y-6">
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
                            <Code className="w-5 h-5 text-orange-600 dark:text-orange-400" />
                            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Structure</h3>
                        </div>
                        <div className="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-4 font-mono text-xs">
                            <div className="text-gray-600 dark:text-gray-400 space-y-1">
                                <div>my-plugin/</div>
                                <div className="pl-4">├── plugin.yaml</div>
                                <div className="pl-4">├── Pulumi.yaml</div>
                                <div className="pl-4">├── __main__.py</div>
                                <div className="pl-4">├── requirements.txt</div>
                                <div className="pl-4">└── assets/</div>
                                <div className="pl-8">└── icon.png</div>
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
                </div>
            </div>
        </div>
    );
};

export default PluginUpload;
