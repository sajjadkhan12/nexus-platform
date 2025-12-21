import React from 'react';

const ENVIRONMENT_STYLES = {
  development: 'bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200 border-blue-300 dark:border-blue-700',
  staging: 'bg-yellow-100 dark:bg-yellow-900 text-yellow-800 dark:text-yellow-200 border-yellow-300 dark:border-yellow-700',
  production: 'bg-red-100 dark:bg-red-900 text-red-800 dark:text-red-200 border-red-300 dark:border-red-700'
};

const ENVIRONMENT_ICONS = {
  development: '🔧',
  staging: '🚀',
  production: '⚡'
};

interface EnvironmentBadgeProps {
  environment: string;
  showIcon?: boolean;
  size?: 'sm' | 'md' | 'lg';
}

export const EnvironmentBadge: React.FC<EnvironmentBadgeProps> = ({ 
  environment, 
  showIcon = false,
  size = 'md'
}) => {
  const sizeClasses = {
    sm: 'px-2 py-0.5 text-xs',
    md: 'px-3 py-1 text-xs',
    lg: 'px-4 py-1.5 text-sm'
  };
  
  const normalizedEnv = environment.toLowerCase();
  const style = ENVIRONMENT_STYLES[normalizedEnv] || ENVIRONMENT_STYLES.development;
  const icon = ENVIRONMENT_ICONS[normalizedEnv] || '';
  
  return (
    <span 
      className={`inline-flex items-center gap-1 rounded-full font-semibold border ${style} ${sizeClasses[size]}`}
      title={`${environment.charAt(0).toUpperCase() + environment.slice(1)} Environment`}
    >
      {showIcon && icon}
      {environment.toUpperCase()}
    </span>
  );
};
