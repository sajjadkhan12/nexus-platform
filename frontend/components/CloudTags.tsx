import React from 'react';
import { Cloud, MapPin, Clock, Server } from 'lucide-react';

interface CloudProviderBadgeProps {
    provider: string;
    size?: 'sm' | 'md';
}

export const CloudProviderBadge: React.FC<CloudProviderBadgeProps> = ({ provider, size = 'sm' }) => {
    const providerConfig: Record<string, { 
        icon?: React.ReactNode;
        label: string;
    }> = {
        aws: {
            icon: <Cloud className="w-3.5 h-3.5" />,
            label: 'AWS'
        },
        gcp: {
            icon: <Cloud className="w-3.5 h-3.5" />,
            label: 'GCP'
        },
        azure: {
            icon: <Cloud className="w-3.5 h-3.5" />,
            label: 'Azure'
        }
    };

    const config = providerConfig[provider?.toLowerCase()] || {
        icon: <Cloud className="w-3.5 h-3.5" />,
        label: provider?.toUpperCase() || 'Unknown'
    };

    const padding = size === 'sm' ? 'px-3 py-1.5' : 'px-4 py-2';
    const textSize = size === 'sm' ? 'text-xs' : 'text-sm';

    return (
        <span className={`inline-flex items-center gap-1.5 ${padding} rounded-full ${textSize} font-semibold bg-gray-100/80 dark:bg-gray-800/80 text-gray-700 dark:text-gray-300 border border-gray-200/50 dark:border-gray-700/50 hover:border-gray-300 dark:hover:border-gray-600 hover:bg-gray-100 dark:hover:bg-gray-800 transition-all duration-200 shadow-sm hover:shadow`}>
            <span className="flex items-center justify-center opacity-70">
                {config.icon}
            </span>
            {config.label}
        </span>
    );
};

interface RegionBadgeProps {
    region: string;
    size?: 'sm' | 'md';
}

export const RegionBadge: React.FC<RegionBadgeProps> = ({ region, size = 'sm' }) => {
    const padding = size === 'sm' ? 'px-3 py-1.5' : 'px-4 py-2';
    const textSize = size === 'sm' ? 'text-xs' : 'text-sm';
    
    const displayRegion = region && region !== 'unknown' ? region.toUpperCase() : 'Unknown';

    return (
        <span className={`inline-flex items-center gap-1.5 ${padding} rounded-full ${textSize} font-semibold bg-gray-100/80 dark:bg-gray-800/80 text-gray-700 dark:text-gray-300 border border-gray-200/50 dark:border-gray-700/50 hover:border-gray-300 dark:hover:border-gray-600 hover:bg-gray-100 dark:hover:bg-gray-800 transition-all duration-200 shadow-sm hover:shadow`}>
            <span className="flex items-center justify-center opacity-70">
                <MapPin className="w-3.5 h-3.5" />
            </span>
            {displayRegion}
        </span>
    );
};

interface MetadataTagProps {
    icon: React.ReactNode;
    label: string;
    value: string | number;
    size?: 'sm' | 'md';
    color?: 'blue' | 'gray' | 'teal' | 'emerald' | 'amber';
}

export const MetadataTag: React.FC<MetadataTagProps> = ({ icon, label, value, size = 'sm', color = 'blue' }) => {
    const padding = size === 'sm' ? 'px-3 py-1.5' : 'px-4 py-2';
    const textSize = size === 'sm' ? 'text-xs' : 'text-sm';

    return (
        <span className={`inline-flex items-center gap-1.5 ${padding} rounded-full ${textSize} font-semibold bg-gray-100/80 dark:bg-gray-800/80 text-gray-700 dark:text-gray-300 border border-gray-200/50 dark:border-gray-700/50 hover:border-gray-300 dark:hover:border-gray-600 hover:bg-gray-100 dark:hover:bg-gray-800 transition-all duration-200 shadow-sm hover:shadow`} title={label}>
            <span className="flex items-center justify-center opacity-70">
                {icon}
            </span>
            {value}
        </span>
    );
};

