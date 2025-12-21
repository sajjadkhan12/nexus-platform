import React from 'react';
import { CheckCircle, XCircle, PlayCircle, Clock, AlertCircle, Skull } from 'lucide-react';

export interface Job {
    id: string;
    status: string;
    inputs?: any;
    [key: string]: any;
}

/**
 * Get status color classes for job status badges
 * Deletion jobs (with action: 'destroy') are always shown in red
 */
export function getStatusColor(status: string, job?: Job): string {
    // Check if this is a deletion job - show red for deletion jobs
    const isDeletionJob = job?.inputs?.action === 'destroy' || job?.inputs?.ACTION === 'destroy';
    
    if (isDeletionJob) {
        // For deletion jobs, always show red regardless of status
        return 'text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800';
    }
    
    // Normal provisioning jobs
    switch (status?.toLowerCase()) {
        case 'success': return 'text-green-600 dark:text-green-400 bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800';
        case 'failed': return 'text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800';
        case 'dead_letter': return 'text-purple-600 dark:text-purple-400 bg-purple-50 dark:bg-purple-900/20 border-purple-200 dark:border-purple-800';
        case 'running': return 'text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800';
        case 'pending': return 'text-yellow-600 dark:text-yellow-400 bg-yellow-50 dark:bg-yellow-900/20 border-yellow-200 dark:border-yellow-800';
        default: return 'text-gray-600 dark:text-gray-400 bg-gray-50 dark:bg-gray-900/20 border-gray-200 dark:border-gray-800';
    }
}

/**
 * Get status color classes for job status badges (alternative style with opacity)
 */
export function getStatusColorAlt(status: string, job?: Job): string {
    // Check if this is a deletion job - show red for deletion jobs
    const isDeletionJob = job?.inputs?.action === 'destroy' || job?.inputs?.ACTION === 'destroy';
    
    if (isDeletionJob) {
        // For deletion jobs, always show red regardless of status
        return 'text-red-500 bg-red-500/10 border-red-500/20';
    }
    
    // Normal provisioning jobs
    switch (status?.toLowerCase()) {
        case 'success': return 'text-green-500 bg-green-500/10 border-green-500/20';
        case 'failed': return 'text-red-500 bg-red-500/10 border-red-500/20';
        case 'dead_letter': return 'text-purple-500 bg-purple-500/10 border-purple-500/20';
        case 'running': return 'text-blue-500 bg-blue-500/10 border-blue-500/20';
        case 'pending': return 'text-yellow-500 bg-yellow-500/10 border-yellow-500/20';
        default: return 'text-gray-500 bg-gray-500/10 border-gray-500/20';
    }
}

/**
 * Get status icon component for job status
 */
export function getStatusIcon(status: string): React.ReactElement {
    switch (status?.toLowerCase()) {
        case 'success': return React.createElement(CheckCircle, { className: "w-4 h-4" });
        case 'failed': return React.createElement(XCircle, { className: "w-4 h-4" });
        case 'dead_letter': return React.createElement(Skull, { className: "w-4 h-4" });
        case 'running': return React.createElement(PlayCircle, { className: "w-4 h-4 animate-pulse" });
        case 'pending': return React.createElement(Clock, { className: "w-4 h-4" });
        default: return React.createElement(AlertCircle, { className: "w-4 h-4" });
    }
}

/**
 * Get status icon component for job status (larger size)
 */
export function getStatusIconLarge(status: string): React.ReactElement {
    switch (status?.toLowerCase()) {
        case 'success': return React.createElement(CheckCircle, { className: "w-5 h-5" });
        case 'failed': return React.createElement(XCircle, { className: "w-5 h-5" });
        case 'dead_letter': return React.createElement(Skull, { className: "w-5 h-5" });
        case 'running': return React.createElement(PlayCircle, { className: "w-5 h-5 animate-pulse" });
        case 'pending': return React.createElement(Clock, { className: "w-5 h-5" });
        default: return React.createElement(AlertCircle, { className: "w-5 h-5" });
    }
}

