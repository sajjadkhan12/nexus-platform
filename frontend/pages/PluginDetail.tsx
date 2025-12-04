import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Download, ExternalLink, ShieldCheck, Tag, Trash2, Loader } from 'lucide-react';
import api from '../services/api';
import { useAuth } from '../contexts/AuthContext';
import { useNotification } from '../contexts/NotificationContext';

interface Plugin {
  id: string;
  name: string;
  description: string;
  author: string;
  category: string;
  cloud_provider: string;
  latest_version: string;
  icon?: string;
  is_locked?: boolean;
  has_access?: boolean;
}

export const PluginDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { isAdmin } = useAuth();
  const { addNotification } = useNotification();
  const [plugin, setPlugin] = useState<Plugin | null>(null);
  const [loading, setLoading] = useState(true);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  useEffect(() => {
    if (id) {
      loadPlugin();
    }
  }, [id]);

  const loadPlugin = async () => {
    try {
      setLoading(true);
      const data = await api.getPlugin(id!);
      setPlugin(data);
    } catch (err: any) {
      addNotification('error', err.message || 'Failed to load plugin');
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async () => {
    if (!plugin) return;
    
    setIsDeleting(true);
    try {
      await api.deletePlugin(plugin.id);
      addNotification('success', `Plugin ${plugin.name} has been deleted`);
      navigate('/services');
    } catch (err: any) {
      addNotification('error', err.message || 'Failed to delete plugin');
    } finally {
      setIsDeleting(false);
      setShowDeleteModal(false);
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh]">
        <Loader className="w-10 h-10 text-orange-600 dark:text-orange-400 animate-spin mb-4" />
        <p className="text-gray-600 dark:text-gray-400">Loading plugin...</p>
      </div>
    );
  }

  if (!plugin) {
    return (
      <div className="text-center py-20 text-gray-900 dark:text-white">
        <p className="mb-4">Plugin not found</p>
        <button
          onClick={() => navigate('/services')}
          className="px-4 py-2 bg-orange-600 text-white rounded-lg hover:bg-orange-700 transition-colors"
        >
          Back to Services
        </button>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6 animate-in slide-in-from-bottom-4 duration-500">
        
      <button onClick={() => navigate(-1)} className="flex items-center gap-2 text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white transition-colors">
        <ArrowLeft className="w-4 h-4" /> Back to Plugins
      </button>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Left Column: Details */}
        <div className="lg:col-span-2 space-y-6">
            <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-800 overflow-hidden transition-colors">
                <div className="p-6 border-b border-gray-200 dark:border-gray-800 flex items-start gap-5 bg-gradient-to-r from-gray-50 to-white dark:from-gray-900 dark:to-gray-800">
                    <div className="p-4 bg-white rounded-2xl shadow-lg border border-gray-100 dark:border-none flex-shrink-0">
                        <img src={plugin.icon} alt={plugin.name} className="w-12 h-12 object-contain" />
                    </div>
                    <div className="flex-1">
                        <div className="flex items-center gap-3 mb-1">
                            <h1 className="text-2xl font-bold text-gray-900 dark:text-white">{plugin.name}</h1>
                            {isAdmin && (
                                <button
                                    onClick={() => setShowDeleteModal(true)}
                                    className="p-1.5 text-gray-400 hover:text-red-600 dark:hover:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors"
                                    title="Delete plugin"
                                >
                                    <Trash2 className="w-5 h-5" />
                                </button>
                            )}
                        </div>
                        <p className="text-gray-500 dark:text-gray-400">by <span className="font-medium text-gray-700 dark:text-gray-300">{plugin.author}</span> • Version {plugin.latest_version}</p>
                    </div>
                </div>
                
                <div className="p-8">
                    <div className="mb-8">
                        <h2 className="text-lg font-bold text-gray-900 dark:text-white mb-4">About</h2>
                        <p className="text-gray-600 dark:text-gray-300 leading-relaxed">{plugin.description}</p>
                    </div>

                    <div>
                        <h2 className="text-lg font-bold text-gray-900 dark:text-white mb-4">Details</h2>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                            <div className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-300 bg-gray-50 dark:bg-gray-800/50 p-3 rounded-lg border border-gray-100 dark:border-gray-800">
                                <ShieldCheck className="w-4 h-4 text-orange-500" />
                                <span className="font-medium">Provider:</span> {plugin.cloud_provider.toUpperCase()}
                            </div>
                            <div className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-300 bg-gray-50 dark:bg-gray-800/50 p-3 rounded-lg border border-gray-100 dark:border-gray-800">
                                <ShieldCheck className="w-4 h-4 text-orange-500" />
                                <span className="font-medium">Category:</span> {plugin.category}
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        {/* Right Column: Actions & Meta */}
        <div className="lg:col-span-1 space-y-6">
            <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-800 p-6 shadow-xl transition-colors">
                <h3 className="text-sm font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-4">Actions</h3>
                
                <button
                    onClick={() => navigate(`/provision/${plugin.id}`)}
                    className="w-full py-3 px-4 rounded-xl font-bold text-sm flex items-center justify-center gap-2 transition-all mb-4 bg-orange-600 hover:bg-orange-500 text-white shadow-lg shadow-orange-500/25"
                >
                    Deploy Plugin
                </button>

                <div className="space-y-4 pt-4 border-t border-gray-100 dark:border-gray-800">
                    <div>
                        <span className="block text-xs font-medium text-gray-500 mb-2">Provider</span>
                        <span className="inline-flex items-center px-3 py-1 bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 text-xs rounded-md border border-gray-200 dark:border-gray-700">
                            {plugin.cloud_provider.toUpperCase()}
                        </span>
                    </div>
                    
                    <div>
                        <span className="block text-xs font-medium text-gray-500 mb-2">Category</span>
                        <span className="inline-flex items-center px-3 py-1 bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 text-xs rounded-md border border-gray-200 dark:border-gray-700">
                            {plugin.category}
                        </span>
                    </div>
                </div>
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
                  Are you sure you want to delete "{plugin.name}"? This will remove all versions and deployments using this plugin.
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
    </div>
  );
};