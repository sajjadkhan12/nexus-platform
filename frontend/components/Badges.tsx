import React from 'react';
import { CheckCircle2, Loader2, AlertCircle, XCircle, Package } from 'lucide-react';

interface StatusBadgeProps {
    status: string;
    size?: 'sm' | 'lg';
    showDot?: boolean;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, size = 'sm', showDot = false }) => {
    const variants = {
        active: {
            bg: 'bg-green-500/10',
            text: 'text-green-600 dark:text-green-400',
            border: 'border-green-500/20',
            icon: size === 'sm' ? <CheckCircle2 className="w-3.5 h-3.5" /> : <CheckCircle2 className="w-4 h-4" />,
            dot: 'bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.6)]'
        },
        provisioning: {
            bg: 'bg-yellow-500/10',
            text: 'text-yellow-600 dark:text-yellow-400',
            border: 'border-yellow-500/20',
            icon: size === 'sm' ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Loader2 className="w-4 h-4 animate-spin" />,
            dot: 'bg-yellow-500 animate-pulse'
        },
        failed: {
            bg: 'bg-red-500/10',
            text: 'text-red-600 dark:text-red-400',
            border: 'border-red-500/20',
            icon: size === 'sm' ? <XCircle className="w-3.5 h-3.5" /> : <XCircle className="w-4 h-4" />,
            dot: 'bg-red-500'
        },
        stopped: {
            bg: 'bg-gray-500/10',
            text: 'text-gray-600 dark:text-gray-400',
            border: 'border-gray-500/20',
            icon: size === 'sm' ? <AlertCircle className="w-3.5 h-3.5" /> : <AlertCircle className="w-4 h-4" />,
            dot: 'bg-gray-500'
        }
    };

    const variant = variants[status.toLowerCase() as keyof typeof variants] || variants.stopped;
    const padding = size === 'sm' ? 'px-3 py-1' : 'px-4 py-2';
    const textSize = size === 'sm' ? 'text-xs' : 'text-sm';

    return (
        <div className="flex items-center gap-2">
            {showDot && <span className={`w-2 h-2 rounded-full ${variant.dot}`}></span>}
            <span className={`inline-flex items-center gap-1.5 ${padding} rounded-full ${textSize} font-semibold border ${variant.bg} ${variant.text} ${variant.border}`}>
                {variant.icon}
                {status.charAt(0).toUpperCase() + status.slice(1)}
            </span>
        </div>
    );
};

interface PluginBadgeProps {
    pluginId: string;
    provider?: string;
}

export const PluginBadge: React.FC<PluginBadgeProps> = ({ pluginId, provider }) => {
    const providerColors: Record<string, string> = {
        gcp: 'bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/20',
        aws: 'bg-orange-500/10 text-orange-600 dark:text-orange-400 border-orange-500/20',
        azure: 'bg-cyan-500/10 text-cyan-600 dark:text-cyan-400 border-cyan-500/20',
    };

    const color = provider ? providerColors[provider.toLowerCase()] || 'bg-purple-500/10 text-purple-600 dark:text-purple-400 border-purple-500/20' : 'bg-purple-500/10 text-purple-600 dark:text-purple-400 border-purple-500/20';

    return (
        <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium border ${color}`}>
            <Package className="w-3 h-3" />
            {pluginId}
        </span>
    );
};
