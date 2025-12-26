import React, { useState, useEffect } from 'react';
import { EnvironmentBadge } from './EnvironmentBadge';
import api from '../services/api';
import { Lock } from 'lucide-react';

interface Environment {
  name: string;
  display: string;
  description: string;
  icon: string;
}

const ENVIRONMENTS: Environment[] = [
  {
    name: 'development',
    display: 'Development',
    description: 'Development and testing environment',
    icon: '🔧'
  },
  {
    name: 'staging',
    display: 'Staging',
    description: 'Pre-production staging environment',
    icon: '🚀'
  },
  {
    name: 'production',
    display: 'Production',
    description: 'Production environment',
    icon: '⚡'
  }
];

interface EnvironmentSelectorProps {
  value: string;
  onChange: (env: string) => void;
  userRoles?: string[];
  disabled?: boolean;
}

export const EnvironmentSelector: React.FC<EnvironmentSelectorProps> = ({ 
  value, 
  onChange, 
  userRoles = [],
  disabled = false
}) => {
  const [permissions, setPermissions] = useState<Set<string>>(new Set());
  const [loadingPermissions, setLoadingPermissions] = useState(true);

  // Fetch user permissions to check environment-specific deployment permissions
  useEffect(() => {
    const fetchPermissions = async () => {
      try {
        const userPermissions = await api.request<Array<{ slug: string }>>('/api/v1/users/me/permissions');
        const permissionSlugs = userPermissions.map(p => p.slug.toLowerCase().trim());
        setPermissions(new Set(permissionSlugs));
      } catch (error: any) {
        setPermissions(new Set());
      } finally {
        setLoadingPermissions(false);
      }
    };
    fetchPermissions();
  }, []);

  // Determine which environments user can deploy to using new permission format
  const canDeployTo = (env: string): boolean => {
    if (disabled) return false;
    
    // Check for new format: business_unit:deployments:create:{environment}
    const envPermission = `business_unit:deployments:create:${env}`.toLowerCase();
    
    // Check permissions (new format)
    if (!loadingPermissions && permissions.size > 0) {
      if (permissions.has(envPermission)) {
        return true;
      }
      
      // Also check for platform admin permissions (platform:*)
      const hasPlatformPermission = Array.from(permissions).some(p => 
        p.startsWith('platform:')
      );
      if (hasPlatformPermission) {
        // Platform admins can deploy to any environment
        return true;
      }
    }
    
    // No permission found - user cannot deploy to this environment
    return false;
  };
  
  return (
    <div className="space-y-4">
      <label className="block text-sm font-medium text-gray-900 dark:text-gray-100">
        Environment <span className="text-red-500">*</span>
      </label>
      
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
        {ENVIRONMENTS.map((env) => {
          const canDeploy = canDeployTo(env.name);
          const isSelected = value === env.name;
          
          return (
            <button
              key={env.name}
              type="button"
              onClick={() => canDeploy && !disabled && onChange(env.name)}
              disabled={!canDeploy || disabled}
              className={`
                relative group
                p-4 rounded-xl border-2 transition-all duration-200
                ${isSelected
                  ? 'border-blue-500 dark:border-blue-400 bg-blue-50 dark:bg-blue-900/30 shadow-md shadow-blue-500/20'
                  : canDeploy
                  ? 'border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 hover:border-gray-300 dark:hover:border-gray-600 hover:shadow-md'
                  : 'border-gray-200 dark:border-gray-800 bg-gray-50 dark:bg-gray-900/50 opacity-60'
                }
                ${!canDeploy || disabled
                  ? 'cursor-not-allowed'
                  : 'cursor-pointer'
                }
                focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 dark:focus:ring-offset-gray-900
              `}
            >
              {/* Selected indicator */}
              {isSelected && canDeploy && (
                <div className="absolute top-2 right-2">
                  <div className="w-5 h-5 bg-blue-500 dark:bg-blue-400 rounded-full flex items-center justify-center">
                    <svg className="w-3 h-3 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                    </svg>
                  </div>
                </div>
              )}

              {/* Lock icon for unavailable environments */}
              {!canDeploy && (
                <div className="absolute top-2 right-2">
                  <Lock className="w-4 h-4 text-gray-400 dark:text-gray-500" />
                </div>
              )}

              <div className="flex flex-col items-center gap-3 text-center">
                {/* Environment icon and badge */}
                <div className="flex flex-col items-center gap-2">
                  <div className="text-2xl">{env.icon}</div>
                  <EnvironmentBadge 
                    environment={env.name} 
                    showIcon={false}
                    size="sm"
                  />
                </div>
                
                {/* Environment name and description */}
                <div className="space-y-1">
                  <div className={`text-sm font-semibold ${
                    isSelected 
                      ? 'text-blue-700 dark:text-blue-300' 
                      : canDeploy
                      ? 'text-gray-900 dark:text-gray-100'
                      : 'text-gray-500 dark:text-gray-400'
                  }`}>
                    {env.display}
                  </div>
                  <div className="text-xs text-gray-600 dark:text-gray-400 leading-relaxed">
                    {env.description}
                  </div>
                </div>
              </div>
            </button>
          );
        })}
      </div>
      
      {!value && (
        <p className="text-sm text-gray-500 dark:text-gray-400 text-center">
          Select an environment to continue
        </p>
      )}
    </div>
  );
};
