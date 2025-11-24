import React from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useApp } from '../App';
import { ArrowLeft, CheckCircle2, XCircle, Download, ExternalLink, ShieldCheck, Tag } from 'lucide-react';

export const PluginDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { plugins, togglePlugin } = useApp();
  const plugin = plugins.find((p) => p.id === id);

  if (!plugin) {
    return <div className="text-center py-20 text-gray-900 dark:text-white">Plugin not found</div>;
  }

  const handleToggle = () => {
    togglePlugin(plugin.id);
  };

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
                    <div>
                        <div className="flex items-center gap-3 mb-1">
                            <h1 className="text-2xl font-bold text-gray-900 dark:text-white">{plugin.name}</h1>
                            {plugin.status === 'Enabled' && (
                                <span className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-green-500/10 text-green-600 dark:text-green-400 text-xs font-medium border border-green-500/20">
                                    <CheckCircle2 className="w-3 h-3" /> Enabled
                                </span>
                            )}
                        </div>
                        <p className="text-gray-500 dark:text-gray-400">by <span className="font-medium text-gray-700 dark:text-gray-300">{plugin.author}</span> • Version {plugin.version}</p>
                    </div>
                </div>
                
                <div className="p-8">
                    <div className="mb-8">
                        <h2 className="text-lg font-bold text-gray-900 dark:text-white mb-4">About</h2>
                        <p className="text-gray-600 dark:text-gray-300 leading-relaxed">{plugin.description}</p>
                    </div>

                    <div>
                        <h2 className="text-lg font-bold text-gray-900 dark:text-white mb-4">Features</h2>
                        <ul className="grid grid-cols-1 md:grid-cols-2 gap-3">
                            {plugin.features.map((feature, idx) => (
                                <li key={idx} className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-300 bg-gray-50 dark:bg-gray-800/50 p-3 rounded-lg border border-gray-100 dark:border-gray-800">
                                    <ShieldCheck className="w-4 h-4 text-indigo-500" />
                                    {feature}
                                </li>
                            ))}
                        </ul>
                    </div>
                </div>
            </div>
        </div>

        {/* Right Column: Actions & Meta */}
        <div className="lg:col-span-1 space-y-6">
            <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-800 p-6 shadow-xl transition-colors">
                <h3 className="text-sm font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-4">Configuration</h3>
                
                <button
                    onClick={handleToggle}
                    className={`w-full py-3 px-4 rounded-xl font-bold text-sm flex items-center justify-center gap-2 transition-all mb-4 ${
                        plugin.status === 'Enabled'
                            ? 'bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 border border-red-200 dark:border-red-800 hover:bg-red-100 dark:hover:bg-red-900/30'
                            : 'bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg shadow-indigo-500/25'
                    }`}
                >
                    {plugin.status === 'Enabled' ? (
                        <>Disable Plugin <XCircle className="w-4 h-4" /></>
                    ) : (
                        <>Enable Plugin <CheckCircle2 className="w-4 h-4" /></>
                    )}
                </button>

                {plugin.status === 'Enabled' && (
                     <div className="bg-green-50 dark:bg-green-900/10 border border-green-200 dark:border-green-900/30 rounded-lg p-3 text-xs text-green-700 dark:text-green-400 mb-6 text-center">
                        Plugin is active and running.
                     </div>
                )}

                <div className="space-y-4 pt-4 border-t border-gray-100 dark:border-gray-800">
                    <div>
                        <span className="block text-xs font-medium text-gray-500 mb-2">Capabilities</span>
                        <div className="flex flex-wrap gap-1.5">
                            {plugin.tags.map(tag => (
                                <span key={tag} className="px-2 py-1 bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 text-xs rounded-md border border-gray-200 dark:border-gray-700 flex items-center gap-1">
                                    <Tag className="w-3 h-3" /> {tag}
                                </span>
                            ))}
                        </div>
                    </div>
                    
                    <div>
                        <span className="block text-xs font-medium text-gray-500 mb-2">Resources</span>
                        <a href="#" className="flex items-center gap-2 text-sm text-indigo-600 dark:text-indigo-400 hover:underline mb-1">
                            <ExternalLink className="w-3 h-3" /> Documentation
                        </a>
                        <a href="#" className="flex items-center gap-2 text-sm text-indigo-600 dark:text-indigo-400 hover:underline">
                            <Download className="w-3 h-3" /> Release Notes
                        </a>
                    </div>
                </div>
            </div>
        </div>

      </div>
    </div>
  );
};