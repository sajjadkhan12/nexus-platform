import React, { useState, useRef, useEffect } from 'react';
import { ChevronDown, Building2, Search, X, Loader2 } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';

export const BusinessUnitSelector: React.FC = () => {
    const { businessUnits, activeBusinessUnit, setActiveBusinessUnit, hasBusinessUnitAccess, isAdmin, isSwitchingBusinessUnit } = useAuth();
    const [isOpen, setIsOpen] = useState(false);
    const [searchQuery, setSearchQuery] = useState('');
    const dropdownRef = useRef<HTMLDivElement>(null);
    const searchInputRef = useRef<HTMLInputElement>(null);

    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
                setIsOpen(false);
                setSearchQuery(''); // Clear search when closing
            }
        };

        document.addEventListener('mousedown', handleClickOutside);
        return () => {
            document.removeEventListener('mousedown', handleClickOutside);
        };
    }, []);

    // Focus search input when dropdown opens
    useEffect(() => {
        if (isOpen && searchInputRef.current) {
            // Small delay to ensure the dropdown is rendered
            setTimeout(() => {
                searchInputRef.current?.focus();
            }, 100);
        } else {
            setSearchQuery(''); // Clear search when closing
        }
    }, [isOpen]);

    // Show "All Business Units" for admins if no business units or no selection
    if (isAdmin && businessUnits.length === 0) {
        return (
            <div className="flex items-center gap-2 px-3 py-2 text-sm text-gray-500 dark:text-gray-400">
                <Building2 className="w-4 h-4" />
                <span>All Business Units (Admin)</span>
            </div>
        );
    }

    // For normal users without business unit access, show a non-clickable message
    if (!hasBusinessUnitAccess && !isAdmin) {
        return (
            <div className="flex items-center gap-2 px-3 py-2 text-sm text-gray-500 dark:text-gray-400">
                <Building2 className="w-4 h-4" />
                <span>No Business Unit</span>
            </div>
        );
    }

    // Ensure normal users with business units can always open the dropdown
    // The button should be clickable if user has business units OR is admin

    const handleSelect = async (bu: typeof businessUnits[0] | null) => {
        await setActiveBusinessUnit(bu);
        setIsOpen(false);
        setSearchQuery(''); // Clear search after selection
    };

    // Filter business units based on search query
    const filteredBusinessUnits = businessUnits.filter((bu) => {
        if (!searchQuery.trim()) return true;
        const query = searchQuery.toLowerCase();
        return (
            bu.name.toLowerCase().includes(query) ||
            bu.slug.toLowerCase().includes(query) ||
            (bu.description && bu.description.toLowerCase().includes(query))
        );
    });

    // Check if "All Business Units" matches search (for admins)
    const showAllBusinessUnits = isAdmin && (
        !searchQuery.trim() || 
        'all business units'.includes(searchQuery.toLowerCase()) ||
        'admin view'.includes(searchQuery.toLowerCase())
    );

    return (
        <div className="relative" ref={dropdownRef} data-business-unit-selector>
            <button
                onClick={() => setIsOpen(!isOpen)}
                disabled={isSwitchingBusinessUnit}
                className={`flex items-center gap-2 px-3 py-2 text-sm font-medium rounded-lg transition-all duration-200 ${
                    !activeBusinessUnit && hasBusinessUnitAccess
                        ? 'bg-orange-100 dark:bg-orange-900/30 text-orange-700 dark:text-orange-400 border border-orange-300 dark:border-orange-700'
                        : 'bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700'
                } ${isSwitchingBusinessUnit ? 'opacity-75 cursor-wait' : ''}`}
            >
                {isSwitchingBusinessUnit ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                    <Building2 className="w-4 h-4" />
                )}
                <span className="hidden sm:inline">
                    {isSwitchingBusinessUnit ? 'Switching...' : (activeBusinessUnit ? activeBusinessUnit.name : 'Select Business Unit')}
                </span>
                <span className="sm:hidden">
                    {isSwitchingBusinessUnit ? 'Switching...' : (activeBusinessUnit ? activeBusinessUnit.name.substring(0, 10) + '...' : 'Select BU')}
                </span>
                {!isSwitchingBusinessUnit && (
                    <ChevronDown className={`w-4 h-4 transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`} />
                )}
            </button>

            {isOpen && (
                <div className="absolute top-full left-0 mt-2 w-72 bg-white dark:bg-gray-900 rounded-xl shadow-lg border border-gray-200 dark:border-gray-800 ring-1 ring-black ring-opacity-5 z-50 animate-in fade-in zoom-in-95 duration-150 origin-top-left">
                    {/* Search Input */}
                    <div className="px-3 pt-3 pb-2 border-b border-gray-200 dark:border-gray-800">
                        <div className="relative">
                            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                            <input
                                ref={searchInputRef}
                                type="text"
                                placeholder="Search by name, slug..."
                                value={searchQuery}
                                onChange={(e) => setSearchQuery(e.target.value)}
                                onClick={(e) => e.stopPropagation()}
                                className="w-full pl-9 pr-8 py-2 text-sm border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-transparent"
                            />
                            {searchQuery && (
                                <button
                                    onClick={(e) => {
                                        e.stopPropagation();
                                        setSearchQuery('');
                                        searchInputRef.current?.focus();
                                    }}
                                    className="absolute right-2 top-1/2 -translate-y-1/2 p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 rounded"
                                >
                                    <X className="w-3.5 h-3.5" />
                                </button>
                            )}
                        </div>
                    </div>

                    {/* Business Units List */}
                    <div className="py-2 max-h-80 overflow-y-auto">
                        {showAllBusinessUnits && (
                            <button
                                onClick={() => handleSelect(null)}
                                className={`w-full text-left px-4 py-2.5 text-sm transition-colors flex items-center justify-between ${
                                    !activeBusinessUnit
                                        ? 'bg-orange-50 dark:bg-orange-500/10 text-orange-600 dark:text-orange-400'
                                        : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800'
                                }`}
                            >
                                <div className="flex flex-col">
                                    <span className="font-medium">All Business Units</span>
                                    <span className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                                        Admin view - see all data
                                    </span>
                                </div>
                                {!activeBusinessUnit && (
                                    <div className="w-2 h-2 rounded-full bg-orange-500"></div>
                                )}
                            </button>
                        )}
                        {filteredBusinessUnits.length === 0 ? (
                            <div className="px-4 py-3 text-sm text-gray-500 dark:text-gray-400 text-center">
                                {searchQuery ? `No business units found matching "${searchQuery}"` : 'No business units available'}
                            </div>
                        ) : (
                            filteredBusinessUnits.map((bu) => (
                                <button
                                    key={bu.id}
                                    onClick={() => handleSelect(bu)}
                                    className={`w-full text-left px-4 py-2.5 text-sm transition-colors flex items-center justify-between ${
                                        activeBusinessUnit?.id === bu.id
                                            ? 'bg-orange-50 dark:bg-orange-500/10 text-orange-600 dark:text-orange-400'
                                            : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800'
                                    }`}
                                >
                                    <div className="flex flex-col min-w-0 flex-1">
                                        <span className="font-medium truncate">{bu.name}</span>
                                        <div className="flex items-center gap-2 mt-0.5">
                                            <span className="text-xs text-gray-500 dark:text-gray-400">/{bu.slug}</span>
                                            {bu.description && (
                                                <span className="text-xs text-gray-500 dark:text-gray-400 truncate">
                                                    • {bu.description}
                                                </span>
                                            )}
                                        </div>
                                    </div>
                                    {activeBusinessUnit?.id === bu.id && (
                                        <div className="w-2 h-2 rounded-full bg-orange-500 ml-2 flex-shrink-0"></div>
                                    )}
                                </button>
                            ))
                        )}
                    </div>
                </div>
            )}
        </div>
    );
};

