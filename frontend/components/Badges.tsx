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
            bg: 'bg-green-500/10 dark:bg-green-500/20',
            text: 'text-green-700 dark:text-green-300',
            border: 'border-green-500/30 dark:border-green-500/30 hover:border-green-500/50 dark:hover:border-green-500/40',
            icon: size === 'sm' ? <CheckCircle2 className="w-3.5 h-3.5" /> : <CheckCircle2 className="w-4 h-4" />,
            dot: 'bg-green-500 shadow-[0_0_6px_rgba(34,197,94,0.5)]'
        },
        provisioning: {
            bg: 'bg-gray-100/80 dark:bg-gray-800/80',
            text: 'text-gray-700 dark:text-gray-300',
            border: 'border-gray-200/50 dark:border-gray-700/50 hover:border-gray-300 dark:hover:border-gray-600',
            icon: size === 'sm' ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Loader2 className="w-4 h-4 animate-spin" />,
            dot: 'bg-yellow-500 animate-pulse shadow-[0_0_6px_rgba(234,179,8,0.5)]'
        },
        failed: {
            bg: 'bg-gray-100/80 dark:bg-gray-800/80',
            text: 'text-gray-700 dark:text-gray-300',
            border: 'border-gray-200/50 dark:border-gray-700/50 hover:border-gray-300 dark:hover:border-gray-600',
            icon: size === 'sm' ? <XCircle className="w-3.5 h-3.5" /> : <XCircle className="w-4 h-4" />,
            dot: 'bg-red-500 shadow-[0_0_6px_rgba(239,68,68,0.5)]'
        },
        stopped: {
            bg: 'bg-gray-100/80 dark:bg-gray-800/80',
            text: 'text-gray-700 dark:text-gray-300',
            border: 'border-gray-200/50 dark:border-gray-700/50 hover:border-gray-300 dark:hover:border-gray-600',
            icon: size === 'sm' ? <AlertCircle className="w-3.5 h-3.5" /> : <AlertCircle className="w-4 h-4" />,
            dot: 'bg-gray-500 shadow-[0_0_6px_rgba(107,114,128,0.5)]'
        }
    };

    const variant = variants[status.toLowerCase() as keyof typeof variants] || variants.stopped;
    const padding = size === 'sm' ? 'px-3 py-1.5' : 'px-4 py-2';
    const textSize = size === 'sm' ? 'text-xs' : 'text-sm';

    return (
        <div className="flex items-center gap-2">
            {showDot && <span className={`w-2 h-2 rounded-full animate-pulse ${variant.dot}`}></span>}
            <span className={`inline-flex items-center gap-1.5 ${padding} rounded-full ${textSize} font-semibold border transition-all duration-200 shadow-sm hover:shadow hover:bg-gray-100 dark:hover:bg-gray-800 ${variant.bg} ${variant.text} ${variant.border}`}>
                <span className="flex items-center justify-center opacity-70">
                    {variant.icon}
                </span>
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
    return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-gray-100/80 dark:bg-gray-800/80 text-gray-700 dark:text-gray-300 border border-gray-200/50 dark:border-gray-700/50 hover:border-gray-300 dark:hover:border-gray-600 hover:bg-gray-100 dark:hover:bg-gray-800 transition-all duration-200 shadow-sm hover:shadow">
            <span className="flex items-center justify-center opacity-70">
                <Package className="w-3 h-3" />
            </span>
            {pluginId}
        </span>
    );
};
