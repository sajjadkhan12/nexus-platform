import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, Filter, ArrowRight, Cloud, Database, HardDrive, Cpu, Box, AlertTriangle, Loader, Lock, Unlock } from 'lucide-react';
import api from '../services/api';
import { appLogger } from '../utils/logger';
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

import { useAuth } from '../contexts/AuthContext';

export const ServicesPage: React.FC = () => {
  const navigate = useNavigate();
  const { isAdmin } = useAuth();
  const { addNotification } = useNotification();
  const [plugins, setPlugins] = useState<Plugin[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedProvider, setSelectedProvider] = useState<string>('All');
  const [selectedType, setSelectedType] = useState<string>('All');
  const [togglingLock, setTogglingLock] = useState<string | null>(null);


  useEffect(() => {
    loadPlugins();
  }, []);

  const loadPlugins = async () => {
    try {
      setLoading(true);
      const data = await api.listPlugins();
      console.log('Loaded plugins in Services:', data); // Debug
      setPlugins(data);
    } catch (err) {
      appLogger.error('Failed to load plugins:', err);
    } finally {
      setLoading(false);
    }
  };


  const handleToggleLock = async (e: React.MouseEvent, plugin: Plugin) => {
    e.stopPropagation();
    try {
      setTogglingLock(plugin.id);
      if (plugin.is_locked) {
        await api.unlockPlugin(plugin.id);
        addNotification('success', `Plugin ${plugin.name} has been unlocked`);
      } else {
        await api.lockPlugin(plugin.id);
        addNotification('success', `Plugin ${plugin.name} has been locked`);
      }
      await loadPlugins();
    } catch (err: any) {
      addNotification('error', err.message || 'Failed to toggle lock');
    } finally {
      setTogglingLock(null);
    }
  };



  const filteredServices = plugins.filter(plugin => {
    const matchesSearch = plugin.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      plugin.description.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesProvider = selectedProvider === 'All' || plugin.cloud_provider === selectedProvider;
    const matchesType = selectedType === 'All' || plugin.category === selectedType;

    return matchesSearch && matchesProvider && matchesType;
  });

  const getProviderColor = (provider: string) => {
    switch (provider.toUpperCase()) {
      case 'AWS': return 'bg-orange-500/10 text-orange-600 dark:text-orange-400 border-orange-500/20';
      case 'GCP': return 'bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/20';
      case 'AZURE': return 'bg-sky-500/10 text-sky-600 dark:text-sky-400 border-sky-500/20';
      case 'DIGITALOCEAN': return 'bg-orange-500/10 text-orange-600 dark:text-orange-400 border-orange-500/20';
      default: return 'bg-gray-500/10 text-gray-600 dark:text-gray-400 border-gray-500/20';
    }
  };

  const getTypeIcon = (type: string) => {
    switch (type.toLowerCase()) {
      case 'compute': return <Cpu className="w-4 h-4" />;
      case 'storage': return <HardDrive className="w-4 h-4" />;
      case 'database': return <Database className="w-4 h-4" />;
      case 'container':
      case 'kubernetes': return <Box className="w-4 h-4" />;
      default: return <Cloud className="w-4 h-4" />;
    }
  };

  const extractTags = (plugin: Plugin) => {
    const tags = [];
    if (plugin.cloud_provider) tags.push(`#${plugin.cloud_provider.toLowerCase()}`);
    if (plugin.category) tags.push(`#${plugin.category.toLowerCase()}`);
    return tags.slice(0, 3);
  };

  return (
    <div className="space-y-8 animate-in fade-in duration-500">

      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Service Catalog</h1>
          <p className="text-gray-500 dark:text-gray-400 mt-1">Select infrastructure templates to deploy to your cloud environments.</p>
        </div>
      </div>

      {/* Filters Bar */}
      <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-4 shadow-sm flex flex-col lg:flex-row gap-4 justify-between items-center transition-colors">

        {/* Search */}
        <div className="relative w-full lg:w-96">
          <Search className="w-5 h-5 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 dark:text-gray-500" />
          <input
            type="text"
            placeholder="Search services, tags..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-gray-50 dark:bg-gray-950 border border-gray-200 dark:border-gray-700 rounded-lg py-2.5 pl-10 pr-4 text-gray-900 dark:text-gray-300 focus:outline-none focus:ring-2 focus:ring-orange-500/50 focus:border-orange-500 transition-all placeholder:text-gray-400 dark:placeholder:text-gray-600"
          />
        </div>

        {/* Dropdowns */}
        <div className="flex flex-wrap items-center gap-3 w-full lg:w-auto">
          <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400 bg-gray-50 dark:bg-gray-950 px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-700">
            <Filter className="w-4 h-4" />
            <span>Filters:</span>
          </div>

          <select
            value={selectedProvider}
            onChange={(e) => setSelectedProvider(e.target.value)}
            className="bg-gray-50 dark:bg-gray-950 border border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-300 text-sm rounded-lg focus:ring-orange-500 focus:border-orange-500 block p-2.5"
          >
            <option value="All">All Providers</option>
            <option value="AWS">AWS</option>
            <option value="GCP">GCP</option>
            <option value="Azure">Azure</option>
            <option value="DigitalOcean">DigitalOcean</option>
          </select>

          <select
            value={selectedType}
            onChange={(e) => setSelectedType(e.target.value)}
            className="bg-gray-50 dark:bg-gray-950 border border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-300 text-sm rounded-lg focus:ring-orange-500 focus:border-orange-500 block p-2.5"
          >
            <option value="All">All Types</option>
            <option value="container">Container</option>
            <option value="storage">Storage</option>
            <option value="database">Database</option>
            <option value="compute">Compute</option>
            <option value="kubernetes">Kubernetes</option>
          </select>
        </div>
      </div>

      {/* Loading State */}
      {loading && (
        <div className="flex flex-col items-center justify-center py-20">
          <Loader className="w-8 h-8 text-orange-600 dark:text-orange-400 animate-spin mb-4" />
          <p className="text-gray-600 dark:text-gray-400">Loading services...</p>
        </div>
      )}

      {/* Grid */}
      {!loading && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
          {filteredServices.map((service) => {
            const isLocked = service.is_locked || false;
            const hasAccess = service.has_access || false;
            
            return (
              <div
                key={service.id}
                onClick={() => navigate(`/provision/${service.id}`)}
                className="group relative bg-white dark:bg-gray-900 border rounded-2xl p-6 transition-all duration-300 flex flex-col h-full border-gray-200 dark:border-gray-800 hover:border-orange-500/50 hover:shadow-2xl hover:shadow-orange-500/10 cursor-pointer"
              >
              {/* Lock Icon Overlay - Show only if locked AND user doesn't have access */}
              {/* Make it clickable for admins to toggle lock status */}
              {isLocked && !hasAccess ? (
                <div 
                  className={`absolute top-4 right-4 z-10 ${isAdmin ? 'cursor-pointer' : ''}`}
                  onClick={isAdmin ? (e) => {
                    e.stopPropagation();
                    handleToggleLock(e, service);
                  } : undefined}
                  title={isAdmin ? 'Click to unlock plugin' : 'Plugin is locked'}
                >
                  <div className="flex items-center gap-1 px-2 py-1 bg-red-500/10 text-red-600 dark:text-red-400 rounded-full border border-red-500/30">
                    <Lock className="w-3 h-3" />
                    <span className="text-xs font-medium">Locked</span>
                  </div>
                </div>
              ) : (
                <div 
                  className={`absolute top-4 right-4 z-10 ${isAdmin ? 'cursor-pointer' : ''}`}
                  onClick={isAdmin ? (e) => {
                    e.stopPropagation();
                    handleToggleLock(e, service);
                  } : undefined}
                  title={isAdmin ? 'Click to lock plugin' : 'Plugin is unlocked'}
                >
                  <div className="flex items-center gap-1 px-2 py-1 bg-green-500/10 text-green-600 dark:text-green-400 rounded-full border border-green-500/30">
                    <Unlock className="w-3 h-3" />
                    <span className="text-xs font-medium">Unlocked</span>
                  </div>
                </div>
              )}
              
              <div className="flex items-start justify-between mb-4">
                <div className="p-3 bg-gray-50 dark:bg-white rounded-xl shadow-sm dark:shadow-lg group-hover:scale-110 transition-transform duration-300 border border-gray-100 dark:border-none">
                  {service.icon ? (
                    <img src={service.icon} alt={service.cloud_provider} className="w-8 h-8 object-contain" />
                  ) : (
                    <div className="w-8 h-8 bg-gradient-to-br from-orange-500 to-orange-600 rounded-lg flex items-center justify-center">
                      <Box className="w-5 h-5 text-white" />
                    </div>
                  )}
                </div>
              </div>

              <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-2 group-hover:text-orange-600 dark:group-hover:text-orange-400 transition-colors">{service.name}</h3>
              <p className="text-sm text-gray-500 dark:text-gray-400 mb-6 flex-grow line-clamp-3">{service.description}</p>

              {/* Footer - Category, Provider Badge, Deploy Button, and Tags */}
              <div className="pt-4 border-t border-gray-100 dark:border-gray-800 mt-auto space-y-3">
                {/* Category */}
                <div className="flex items-center gap-1.5 text-xs text-gray-500 dark:text-gray-400">
                  {getTypeIcon(service.category)}
                  <span>{service.category}</span>
                </div>
                
                {/* First Row: Provider Badge and Deploy Button */}
                <div className="flex items-center justify-between">
                  <span className={`text-xs font-medium px-2.5 py-1 rounded-full border ${getProviderColor(service.cloud_provider)}`}>
                    {service.cloud_provider.toUpperCase()}
                  </span>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      navigate(`/provision/${service.id}`);
                    }}
                    className="flex items-center gap-2 px-4 py-2 bg-orange-600 hover:bg-orange-700 text-white rounded-lg font-medium text-sm transition-all group-hover:shadow-lg group-hover:shadow-orange-500/30"
                  >
                    Deploy
                    <ArrowRight className="w-4 h-4" />
                  </button>
                </div>
                
                {/* Second Row: Tags */}
                <div className="flex flex-wrap gap-2">
                  {extractTags(service).map((tag) => (
                    <span key={tag} className="text-xs bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 px-2 py-1 rounded border border-gray-200 dark:border-gray-700">
                      {tag}
                    </span>
                  ))}
                </div>
              </div>
              </div>
            );
          })}

          {!loading && filteredServices.length === 0 && (
            <div className="col-span-full flex flex-col items-center justify-center py-20 text-gray-500 dark:text-gray-500">
              <div className="bg-gray-100 dark:bg-gray-800 p-4 rounded-full mb-4">
                <AlertTriangle className="w-8 h-8 opacity-50" />
              </div>
              <h3 className="text-lg font-medium text-gray-900 dark:text-white">No services found</h3>
              <p className="text-sm mt-1 max-w-sm text-center">
                {searchQuery || selectedProvider !== 'All' || selectedType !== 'All'
                  ? 'No services match your current filters. Try adjusting your search criteria.'
                  : 'No plugins have been uploaded yet. Upload your first plugin to get started.'}
              </p>
              {!searchQuery && selectedProvider === 'All' && selectedType === 'All' && isAdmin && (
                <button
                  onClick={() => navigate('/plugin-upload')}
                  className="mt-4 px-6 py-2.5 bg-orange-600 hover:bg-orange-700 text-white rounded-lg font-medium transition-colors"
                >
                  Upload Plugin
                </button>
              )}
            </div>
          )}
        </div>
      )}

    </div>
  );
};