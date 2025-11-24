import React, { useState, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { SERVICES } from '../constants';
import { Provider, ServiceType } from '../types';
import { useApp } from '../App';
import { Search, Filter, ArrowRight, Cloud, Database, HardDrive, Cpu, Box, AlertTriangle } from 'lucide-react';

export const ServicesPage: React.FC = () => {
  const { plugins } = useApp();
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedProvider, setSelectedProvider] = useState<Provider | 'All'>('All');
  const [selectedType, setSelectedType] = useState<ServiceType | 'All'>('All');

  const filteredServices = useMemo(() => {
    // Map providers to their plugin IDs
    const providerPluginMap: Record<string, string> = {
      'AWS': 'aws-provider',
      'GCP': 'gcp-provider',
      'Azure': 'azure-provider',
      'DigitalOcean': 'do-provider'
    };

    return SERVICES.filter((service) => {
      // 1. Check if the Provider Plugin is enabled
      const requiredPluginId = providerPluginMap[service.provider];
      const isPluginEnabled = !requiredPluginId || plugins.find(p => p.id === requiredPluginId)?.status === 'Enabled';

      if (!isPluginEnabled) return false;

      // 2. Apply existing filters
      const matchesSearch = service.name.toLowerCase().includes(searchQuery.toLowerCase()) || 
                            service.tags.some(tag => tag.toLowerCase().includes(searchQuery.toLowerCase()));
      const matchesProvider = selectedProvider === 'All' || service.provider === selectedProvider;
      const matchesType = selectedType === 'All' || service.type === selectedType;
      
      return matchesSearch && matchesProvider && matchesType;
    });
  }, [searchQuery, selectedProvider, selectedType, plugins]);

  const getProviderColor = (p: Provider) => {
    switch (p) {
      case 'AWS': return 'bg-orange-500/10 text-orange-600 dark:text-orange-400 border-orange-500/20';
      case 'GCP': return 'bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/20';
      case 'Azure': return 'bg-sky-500/10 text-sky-600 dark:text-sky-400 border-sky-500/20';
      case 'DigitalOcean': return 'bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 border-indigo-500/20';
      default: return 'bg-gray-500/10 text-gray-600 dark:text-gray-400 border-gray-500/20';
    }
  };

  const getTypeIcon = (t: ServiceType) => {
    switch(t) {
        case 'Compute': return <Cpu className="w-4 h-4"/>;
        case 'Storage': return <HardDrive className="w-4 h-4"/>;
        case 'Database': return <Database className="w-4 h-4"/>;
        case 'Container': return <Box className="w-4 h-4"/>;
        default: return <Cloud className="w-4 h-4"/>;
    }
  }

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
            className="w-full bg-gray-50 dark:bg-gray-950 border border-gray-200 dark:border-gray-700 rounded-lg py-2.5 pl-10 pr-4 text-gray-900 dark:text-gray-300 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500 transition-all placeholder:text-gray-400 dark:placeholder:text-gray-600"
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
            onChange={(e) => setSelectedProvider(e.target.value as Provider | 'All')}
            className="bg-gray-50 dark:bg-gray-950 border border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-300 text-sm rounded-lg focus:ring-indigo-500 focus:border-indigo-500 block p-2.5"
          >
            <option value="All">All Providers</option>
            <option value="AWS">AWS</option>
            <option value="GCP">GCP</option>
            <option value="Azure">Azure</option>
            <option value="DigitalOcean">DigitalOcean</option>
          </select>

          <select 
            value={selectedType}
            onChange={(e) => setSelectedType(e.target.value as ServiceType | 'All')}
            className="bg-gray-50 dark:bg-gray-950 border border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-300 text-sm rounded-lg focus:ring-indigo-500 focus:border-indigo-500 block p-2.5"
          >
            <option value="All">All Types</option>
            <option value="Container">Container</option>
            <option value="Storage">Storage</option>
            <option value="Database">Database</option>
            <option value="Compute">Compute</option>
          </select>
        </div>
      </div>

      {/* Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
        {filteredServices.map((service) => (
          <Link 
            key={service.id} 
            to={`/service/${service.id}`}
            className="group relative bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-2xl p-6 hover:border-indigo-500/50 hover:shadow-2xl hover:shadow-indigo-500/10 transition-all duration-300 flex flex-col h-full"
          >
            <div className="flex items-start justify-between mb-4">
               <div className="p-3 bg-gray-50 dark:bg-white rounded-xl shadow-sm dark:shadow-lg group-hover:scale-110 transition-transform duration-300 border border-gray-100 dark:border-none">
                  <img src={service.icon} alt={service.provider} className="w-8 h-8 object-contain" />
               </div>
               <span className={`text-xs font-medium px-2.5 py-1 rounded-full border ${getProviderColor(service.provider)}`}>
                 {service.provider}
               </span>
            </div>
            
            <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-2 group-hover:text-indigo-600 dark:group-hover:text-indigo-400 transition-colors">{service.name}</h3>
            <p className="text-sm text-gray-500 dark:text-gray-400 mb-6 flex-grow line-clamp-3">{service.description}</p>
            
            <div className="space-y-4">
              <div className="flex flex-wrap gap-2">
                {service.tags.slice(0, 3).map((tag) => (
                  <span key={tag} className="text-xs bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 px-2 py-1 rounded border border-gray-200 dark:border-gray-700">
                    #{tag}
                  </span>
                ))}
              </div>
              
              <div className="flex items-center justify-between pt-4 border-t border-gray-100 dark:border-gray-800">
                 <div className="flex items-center gap-1.5 text-xs text-gray-500">
                    {getTypeIcon(service.type)}
                    {service.type}
                 </div>
                 <div className="flex items-center gap-1 text-sm font-medium text-indigo-600 dark:text-indigo-400 group-hover:translate-x-1 transition-transform">
                   Deploy <ArrowRight className="w-4 h-4" />
                 </div>
              </div>
            </div>
          </Link>
        ))}
        
        {filteredServices.length === 0 && (
            <div className="col-span-full flex flex-col items-center justify-center py-20 text-gray-500 dark:text-gray-500">
                <div className="bg-gray-100 dark:bg-gray-800 p-4 rounded-full mb-4">
                  <AlertTriangle className="w-8 h-8 opacity-50" />
                </div>
                <h3 className="text-lg font-medium text-gray-900 dark:text-white">No services found</h3>
                <p className="text-sm mt-1 max-w-sm text-center">
                  This might be because the corresponding provider plugins are disabled or no services match your search filters.
                </p>
                <Link to="/plugins" className="mt-4 text-indigo-600 dark:text-indigo-400 hover:underline">
                  Check Plugins &rarr;
                </Link>
            </div>
        )}
      </div>
    </div>
  );
};