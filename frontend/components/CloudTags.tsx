import React from 'react';
import { Cloud, MapPin, Clock, Server } from 'lucide-react';

interface CloudProviderBadgeProps {
    provider: string;
    size?: 'sm' | 'md';
}

export const CloudProviderBadge: React.FC<CloudProviderBadgeProps> = ({ provider, size = 'sm' }) => {
    const providerConfig: Record<string, { 
        bg: string; 
        text: string; 
        border: string; 
        icon?: React.ReactNode;
        label: string;
    }> = {
        aws: {
            bg: 'bg-orange-500/10',
            text: 'text-orange-600 dark:text-orange-400',
            border: 'border-orange-500/20',
            icon: <Cloud className="w-3.5 h-3.5" />,
            label: 'AWS'
        },
        gcp: {
            bg: 'bg-blue-500/10',
            text: 'text-blue-600 dark:text-blue-400',
            border: 'border-blue-500/20',
            icon: <Cloud className="w-3.5 h-3.5" />,
            label: 'GCP'
        },
        azure: {
            bg: 'bg-cyan-500/10',
            text: 'text-cyan-600 dark:text-cyan-400',
            border: 'border-cyan-500/20',
            icon: <Cloud className="w-3.5 h-3.5" />,
            label: 'Azure'
        }
    };

    const config = providerConfig[provider?.toLowerCase()] || {
        bg: 'bg-gray-500/10',
        text: 'text-gray-600 dark:text-gray-400',
        border: 'border-gray-500/20',
        icon: <Cloud className="w-3.5 h-3.5" />,
        label: provider?.toUpperCase() || 'Unknown'
    };

    const padding = size === 'sm' ? 'px-3 py-1' : 'px-4 py-1.5';
    const textSize = size === 'sm' ? 'text-xs' : 'text-sm';

    return (
        <span className={`inline-flex items-center gap-1.5 ${padding} rounded-full ${textSize} font-semibold border ${config.bg} ${config.text} ${config.border}`}>
            {config.icon}
            {config.label}
        </span>
    );
};

interface RegionBadgeProps {
    region: string;
    size?: 'sm' | 'md';
}

export const RegionBadge: React.FC<RegionBadgeProps> = ({ region, size = 'sm' }) => {
    const padding = size === 'sm' ? 'px-3 py-1' : 'px-4 py-1.5';
    const textSize = size === 'sm' ? 'text-xs' : 'text-sm';
    
    const displayRegion = region && region !== 'unknown' ? region : 'Unknown';
    
    // Use purple/indigo for region badge
    const bg = 'bg-purple-500/10';
    const text = 'text-purple-600 dark:text-purple-400';
    const border = 'border-purple-500/20';

    return (
        <span className={`inline-flex items-center gap-1.5 ${padding} rounded-full ${textSize} font-semibold border ${bg} ${text} ${border}`}>
            <MapPin className="w-3.5 h-3.5" />
            {displayRegion}
        </span>
    );
};

interface MetadataTagProps {
    icon: React.ReactNode;
    label: string;
    value: string | number;
    size?: 'sm' | 'md';
    color?: 'blue' | 'gray' | 'teal';
}

export const MetadataTag: React.FC<MetadataTagProps> = ({ icon, label, value, size = 'sm', color = 'blue' }) => {
    const padding = size === 'sm' ? 'px-3 py-1' : 'px-4 py-1.5';
    const textSize = size === 'sm' ? 'text-xs' : 'text-sm';

    const colorConfig = {
        blue: {
            bg: 'bg-blue-500/10',
            text: 'text-blue-600 dark:text-blue-400',
            border: 'border-blue-500/20'
        },
        gray: {
            bg: 'bg-gray-500/10',
            text: 'text-gray-600 dark:text-gray-400',
            border: 'border-gray-500/20'
        },
        teal: {
            bg: 'bg-teal-500/10',
            text: 'text-teal-600 dark:text-teal-400',
            border: 'border-teal-500/20'
        }
    };

    const config = colorConfig[color];

    return (
        <span className={`inline-flex items-center gap-1.5 ${padding} rounded-full ${textSize} font-semibold border ${config.bg} ${config.text} ${config.border}`} title={label}>
            {icon}
            {value}
        </span>
    );
};

