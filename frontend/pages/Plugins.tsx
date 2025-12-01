import React, { useState, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { useApp } from '../App';
import { Search, Filter, ArrowRight, ToggleLeft, ToggleRight, CheckCircle2 } from 'lucide-react';

export const PluginsPage: React.FC = () => {
  const { plugins, togglePlugin } = useApp();
  const [searchQuery, setSearchQuery] = useState('');
  const [filterStatus, setFilterStatus] = useState<'All' | 'Enabled' | 'Disabled'>('All');

  const filteredPlugins = useMemo(() => {
    return plugins.filter((plugin) => {
      const matchesSearch = plugin.name.toLowerCase().includes(searchQuery.toLowerCase()) || 
                            plugin.tags.some(tag => tag.toLowerCase().includes(searchQuery.toLowerCase()));
      const matchesStatus = filterStatus === 'All' || plugin.status === filterStatus;
      
      return matchesSearch && matchesStatus;
    });
  }, [plugins, searchQuery, filterStatus]);

  const handleToggle = (e: React.MouseEvent, id: string) => {
    e.preventDefault(); // Prevent navigation when clicking the toggle
    e.stopPropagation();
    togglePlugin(id);
  };

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Plugins Marketplace</h1>
          <p className="text-gray-500 dark:text-gray-400 mt-1">Manage integrations, providers, and extensions for your platform.</p>
        </div>
      </div>

      {/* Filters Bar */}
      <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-4 shadow-sm flex flex-col lg:flex-row gap-4 justify-between items-center transition-colors">
        
        {/* Search */}
        <div className="relative w-full lg:w-96">
          <Search className="w-5 h-5 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 dark:text-gray-500" />
          <input
            type="text"
            placeholder="Search plugins..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-gray-50 dark:bg-gray-950 border border-gray-200 dark:border-gray-700 rounded-lg py-2.5 pl-10 pr-4 text-gray-900 dark:text-gray-300 focus:outline-none focus:ring-2 focus:ring-orange-500/50 focus:border-orange-500 transition-all placeholder:text-gray-400 dark:placeholder:text-gray-600"
          />
        </div>

        {/* Dropdowns */}
        <div className="flex flex-wrap items-center gap-3 w-full lg:w-auto">
          <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400 bg-gray-50 dark:bg-gray-950 px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-700">
            <Filter className="w-4 h-4" />
            <span>Status:</span>
          </div>
          
          <select 
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value as 'All' | 'Enabled' | 'Disabled')}
            className="bg-gray-50 dark:bg-gray-950 border border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-300 text-sm rounded-lg focus:ring-orange-500 focus:border-orange-500 block p-2.5"
          >
            <option value="All">All Plugins</option>
            <option value="Enabled">Enabled</option>
            <option value="Disabled">Disabled</option>
          </select>
        </div>
      </div>

      {/* Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
        {filteredPlugins.map((plugin) => (
          <Link 
            key={plugin.id} 
            to={`/plugin/${plugin.id}`}
            className="group relative bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-2xl p-6 hover:border-orange-500/50 hover:shadow-2xl hover:shadow-orange-500/10 transition-all duration-300 flex flex-col h-full"
          >
            <div className="flex items-start justify-between mb-4">
               <div className="p-3 bg-gray-50 dark:bg-white rounded-xl shadow-sm dark:shadow-lg border border-gray-100 dark:border-none group-hover:scale-110 transition-transform">
                  <img src={plugin.icon} alt={plugin.name} className="w-8 h-8 object-contain" />
               </div>
               <button 
                onClick={(e) => handleToggle(e, plugin.id)}
                className={`transition-colors duration-200 focus:outline-none ${
                    plugin.status === 'Enabled' ? 'text-green-500 hover:text-green-600' : 'text-gray-300 hover:text-gray-400 dark:text-gray-600 dark:hover:text-gray-500'
                }`}
               >
                 {plugin.status === 'Enabled' ? <ToggleRight className="w-8 h-8" /> : <ToggleLeft className="w-8 h-8" />}
               </button>
            </div>
            
            <div className="mb-2">
                <h3 className="text-lg font-bold text-gray-900 dark:text-white group-hover:text-orange-600 dark:group-hover:text-orange-400 transition-colors">{plugin.name}</h3>
                <p className="text-xs text-gray-500 dark:text-gray-400">by {plugin.author}</p>
            </div>
            
            <p className="text-sm text-gray-500 dark:text-gray-400 mb-6 flex-grow line-clamp-2">{plugin.description}</p>
            
            <div className="space-y-4">
              <div className="flex flex-wrap gap-2">
                {plugin.tags.slice(0, 2).map((tag) => (
                  <span key={tag} className="text-xs bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 px-2 py-1 rounded border border-gray-200 dark:border-gray-700">
                    #{tag}
                  </span>
                ))}
              </div>
              
              <div className="flex items-center justify-between pt-4 border-t border-gray-100 dark:border-gray-800">
                 <div className={`flex items-center gap-1.5 text-xs font-medium px-2 py-0.5 rounded-full ${
                     plugin.status === 'Enabled' 
                        ? 'bg-green-500/10 text-green-600 dark:text-green-400' 
                        : 'bg-gray-500/10 text-gray-500 dark:text-gray-400'
                 }`}>
                    {plugin.status === 'Enabled' && <CheckCircle2 className="w-3 h-3" />}
                    {plugin.status}
                 </div>
                 <div className="flex items-center gap-1 text-sm font-medium text-orange-600 dark:text-orange-400 group-hover:translate-x-1 transition-transform">
                   Details <ArrowRight className="w-4 h-4" />
                 </div>
              </div>
            </div>
          </Link>
        ))}
        
        {filteredPlugins.length === 0 && (
            <div className="col-span-full flex flex-col items-center justify-center py-20 text-gray-500 dark:text-gray-500">
                <Search className="w-12 h-12 mb-4 opacity-20" />
                <p>No plugins found matching your filters.</p>
            </div>
        )}
      </div>
    </div>
  );
};