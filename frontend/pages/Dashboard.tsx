import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { 
    Server, 
    AlertCircle, 
    Zap, 
    ArrowRight, 
    CheckCircle, 
    XCircle, 
    Clock,
    Package,
    Bell,
    PlayCircle,
    LayoutGrid,
    TrendingUp,
    Users,
    Shield
} from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { BusinessUnitWarningModal } from '../components/BusinessUnitWarningModal';
import api from '../services/api';
import { appLogger } from '../utils/logger';
import { EnvironmentBadge } from '../components/EnvironmentBadge';

interface DashboardStats {
    totalDeployments: number;
    activeDeployments: number;
    failedDeployments: number;
    provisioningDeployments: number;
    totalPlugins: number;
    unreadNotifications: number;
    envStats: { environment: string; count: number }[];
}

interface RecentDeployment {
    id: string;
    name: string;
    status: string;
    environment: string;
    plugin_id: string;
    created_at: string;
}

interface RecentNotification {
    id: string;
    title: string;
    message: string;
    type: string;
    is_read: boolean;
    created_at: string;
    link?: string;
}

export const DashboardPage: React.FC = () => {
    const { user, isAdmin, activeBusinessUnit, hasBusinessUnitAccess, isLoadingBusinessUnits, isLoadingActiveBusinessUnit } = useAuth();
    const [showBusinessUnitWarning, setShowBusinessUnitWarning] = useState(false);
    const [stats, setStats] = useState<DashboardStats>({
        totalDeployments: 0,
        activeDeployments: 0,
        failedDeployments: 0,
        provisioningDeployments: 0,
        totalPlugins: 0,
        unreadNotifications: 0,
        envStats: []
    });
    const [recentDeployments, setRecentDeployments] = useState<RecentDeployment[]>([]);
    const [recentNotifications, setRecentNotifications] = useState<RecentNotification[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');

    useEffect(() => {
        fetchDashboardData();
    }, [isLoadingBusinessUnits, isLoadingActiveBusinessUnit, activeBusinessUnit, hasBusinessUnitAccess]);

    const fetchDashboardData = async () => {
        // Wait for business units and active business unit to load before checking
        if (isLoadingBusinessUnits || isLoadingActiveBusinessUnit) {
            return;
        }
        
        // Check if business unit is selected (admins can bypass)
        const userIsAdmin = isAdmin || (user?.roles || []).some(role => role.toLowerCase() === 'admin');
        if (!userIsAdmin && (!activeBusinessUnit || !hasBusinessUnitAccess)) {
            setShowBusinessUnitWarning(true);
            setLoading(false);
            return;
        }
        
        try {
            setLoading(true);
            setError('');

            // Fetch all data in parallel (with error handling)
            const [deploymentsData, pluginsData, notificationsData, envStatsData] = await Promise.all([
                api.listDeployments({ limit: 100 }).catch(() => ({ items: [], total: 0 })),
                api.pluginsApi.listPlugins().catch(() => []),
                api.notificationsApi.getNotifications(false).catch(() => ({ items: [], total: 0 })),
                api.request('/api/v1/deployments/stats/by-environment').catch(() => [])
            ]);

            // Process deployments
            const deployments = Array.isArray(deploymentsData) ? deploymentsData : (deploymentsData?.items || []);
            const activeDeployments = deployments.filter((d: any) => d.status === 'active').length;
            const failedDeployments = deployments.filter((d: any) => d.status === 'failed').length;
            const provisioningDeployments = deployments.filter((d: any) => d.status === 'provisioning').length;
            
            // Get recent deployments (last 5)
            const recent = deployments
                .slice(0, 5)
                .map((d: any) => ({
                    id: d.id,
                    name: d.name,
                    status: d.status,
                    environment: d.environment,
                    plugin_id: d.plugin_id,
                    created_at: d.created_at
                }));


            // Process plugins
            const plugins = Array.isArray(pluginsData) ? pluginsData : (pluginsData?.items || []);

            // Process notifications
            const notifications = Array.isArray(notificationsData) ? notificationsData : (notificationsData?.items || []);
            const unreadNotifications = notifications.filter((n: any) => !n.is_read).length;
            const recentNotificationsList = notifications.slice(0, 5).map((n: any) => ({
                id: n.id,
                title: n.title,
                message: n.message,
                type: n.type,
                is_read: n.is_read,
                created_at: n.created_at,
                link: n.link
            }));

            // Process environment stats
            const envStats = Array.isArray(envStatsData) ? envStatsData : [];

            setStats({
                totalDeployments: deployments.length,
                activeDeployments,
                failedDeployments,
                provisioningDeployments,
                totalPlugins: plugins.length,
                unreadNotifications,
                envStats
            });

            setRecentDeployments(recent);
            setRecentNotifications(recentNotificationsList);

        } catch (err: any) {
            appLogger.error('Failed to fetch dashboard data:', err);
            setError(err.message || 'Failed to load dashboard');
        } finally {
            setLoading(false);
        }
    };

    const getStatusIcon = (status: string) => {
        switch (status.toLowerCase()) {
            case 'active':
                return <CheckCircle className="w-4 h-4 text-green-600 dark:text-green-400" />;
            case 'failed':
            case 'dead_letter':
                return <XCircle className="w-4 h-4 text-red-600 dark:text-red-400" />;
            case 'provisioning':
            case 'pending':
            case 'running':
                return <Clock className="w-4 h-4 text-yellow-600 dark:text-yellow-400" />;
            default:
                return <Server className="w-4 h-4 text-gray-600 dark:text-gray-400" />;
        }
    };

    const getStatusColor = (status: string) => {
        switch (status.toLowerCase()) {
            case 'active':
            case 'success':
                return 'text-green-600 dark:text-green-400 bg-green-50 dark:bg-green-900/20';
            case 'failed':
            case 'dead_letter':
                return 'text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20';
            case 'provisioning':
            case 'pending':
            case 'running':
                return 'text-yellow-600 dark:text-yellow-400 bg-yellow-50 dark:bg-yellow-900/20';
            default:
                return 'text-gray-600 dark:text-gray-400 bg-gray-50 dark:bg-gray-800';
        }
    };

    const getNotificationIcon = (type: string) => {
        switch (type) {
            case 'success':
                return <CheckCircle className="w-4 h-4 text-green-600 dark:text-green-400" />;
            case 'error':
                return <XCircle className="w-4 h-4 text-red-600 dark:text-red-400" />;
            case 'warning':
                return <AlertCircle className="w-4 h-4 text-yellow-600 dark:text-yellow-400" />;
            default:
                return <Bell className="w-4 h-4 text-blue-600 dark:text-blue-400" />;
        }
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center min-h-[400px]">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-orange-600"></div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
                <p className="text-red-800 dark:text-red-200">{error}</p>
            </div>
        );
    }

    return (
        <div className="space-y-6 animate-in fade-in duration-500">
            {/* Header */}
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
                <div>
                    <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Dashboard</h1>
                    <p className="text-gray-500 dark:text-gray-400 mt-1">
                        Welcome back, {user?.full_name || user?.username}. Here's your platform overview.
                    </p>
                </div>
                <div className="flex gap-2">
                    <Link 
                        to="/provision" 
                        className="bg-orange-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-orange-500 transition-colors shadow-lg shadow-orange-500/20 flex items-center gap-2"
                    >
                        <Zap className="w-4 h-4" /> Quick Deploy
                    </Link>
                    {isAdmin && (
                        <Link 
                            to="/admin-dashboard" 
                            className="bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 px-4 py-2 rounded-lg text-sm font-medium hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors flex items-center gap-2"
                        >
                            <Shield className="w-4 h-4" /> Admin
                        </Link>
                    )}
                </div>
            </div>

            {/* Stats Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {/* Total Deployments */}
                <div className="bg-white dark:bg-gray-900 p-6 rounded-2xl border border-gray-200 dark:border-gray-800 transition-colors hover:border-gray-300 dark:hover:border-gray-700">
                    <div className="flex items-center justify-between mb-4">
                        <div className="p-3 rounded-xl bg-blue-500/10 text-blue-600 dark:text-blue-400">
                            <Server className="w-6 h-6" />
                        </div>
                        <Link to="/deployments" className="text-xs text-blue-600 dark:text-blue-400 hover:underline">
                            View all →
                        </Link>
                    </div>
                    <h3 className="text-2xl font-bold text-gray-900 dark:text-white">{stats.totalDeployments}</h3>
                    <p className="text-sm text-gray-500 dark:text-gray-400 font-medium">Total Deployments</p>
                    <div className="mt-2 flex gap-2 text-xs">
                        <span className="text-green-600 dark:text-green-400">{stats.activeDeployments} active</span>
                        {stats.failedDeployments > 0 && (
                            <span className="text-red-600 dark:text-red-400">{stats.failedDeployments} failed</span>
                        )}
                        {stats.provisioningDeployments > 0 && (
                            <span className="text-yellow-600 dark:text-yellow-400">{stats.provisioningDeployments} provisioning</span>
                        )}
                    </div>
                </div>

                {/* Plugins */}
                <div className="bg-white dark:bg-gray-900 p-6 rounded-2xl border border-gray-200 dark:border-gray-800 transition-colors hover:border-gray-300 dark:hover:border-gray-700">
                    <div className="flex items-center justify-between mb-4">
                        <div className="p-3 rounded-xl bg-purple-500/10 text-purple-600 dark:text-purple-400">
                            <Package className="w-6 h-6" />
                        </div>
                        <Link to="/services" className="text-xs text-purple-600 dark:text-purple-400 hover:underline">
                            View all →
                        </Link>
                    </div>
                    <h3 className="text-2xl font-bold text-gray-900 dark:text-white">{stats.totalPlugins}</h3>
                    <p className="text-sm text-gray-500 dark:text-gray-400 font-medium">Available Plugins</p>
                </div>

                {/* Notifications */}
                <div className="bg-white dark:bg-gray-900 p-6 rounded-2xl border border-gray-200 dark:border-gray-800 transition-colors hover:border-gray-300 dark:hover:border-gray-700">
                    <div className="flex items-center justify-between mb-4">
                        <div className="p-3 rounded-xl bg-green-500/10 text-green-600 dark:text-green-400">
                            <Bell className="w-6 h-6" />
                        </div>
                        {stats.unreadNotifications > 0 && (
                            <span className="bg-red-500 text-white text-xs font-bold px-2 py-1 rounded-full">
                                {stats.unreadNotifications}
                            </span>
                        )}
                    </div>
                    <h3 className="text-2xl font-bold text-gray-900 dark:text-white">{stats.unreadNotifications}</h3>
                    <p className="text-sm text-gray-500 dark:text-gray-400 font-medium">Unread Notifications</p>
                </div>
            </div>

            {/* Main Content Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Recent Deployments */}
                <div className="lg:col-span-2 bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-800 p-6">
                    <div className="flex items-center justify-between mb-4">
                        <h2 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                            <Server className="w-5 h-5" />
                            Recent Deployments
                        </h2>
                        <Link 
                            to="/deployments" 
                            onClick={(e) => {
                                const userIsAdmin = isAdmin || (user?.roles || []).some(role => role.toLowerCase() === 'admin');
                                if (!userIsAdmin && (!activeBusinessUnit || !hasBusinessUnitAccess)) {
                                    e.preventDefault();
                                    setShowBusinessUnitWarning(true);
                                }
                            }}
                            className="text-sm text-blue-600 dark:text-blue-400 hover:underline flex items-center gap-1"
                        >
                            View all <ArrowRight className="w-4 h-4" />
                        </Link>
                    </div>
                    <div className="space-y-3">
                        {recentDeployments.length > 0 ? (
                            recentDeployments.map((deployment) => (
                                <Link
                                    key={deployment.id}
                                    to={`/deployment/${deployment.id}`}
                                    onClick={(e) => {
                                        const userIsAdmin = isAdmin || (user?.roles || []).some(role => role.toLowerCase() === 'admin');
                                        if (!userIsAdmin && (!activeBusinessUnit || !hasBusinessUnitAccess)) {
                                            e.preventDefault();
                                            setShowBusinessUnitWarning(true);
                                        }
                                    }}
                                    className="block p-4 rounded-lg bg-gray-50 dark:bg-gray-800 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                                >
                                    <div className="flex items-center justify-between">
                                        <div className="flex items-center gap-3 flex-1 min-w-0">
                                            {getStatusIcon(deployment.status)}
                                            <div className="flex-1 min-w-0">
                                                <p className="text-sm font-medium text-gray-900 dark:text-white truncate">
                                                    {deployment.name}
                                                </p>
                                                <div className="flex items-center gap-2 mt-1">
                                                    <EnvironmentBadge environment={deployment.environment} size="sm" />
                                                    <span className="text-xs text-gray-500 dark:text-gray-400">
                                                        {new Date(deployment.created_at).toLocaleDateString()}
                                                    </span>
                                                </div>
                                            </div>
                                        </div>
                                        <div className="flex items-center gap-1.5">
                                            <span className={`text-xs font-medium px-2 py-1 rounded-full ${getStatusColor(deployment.status)}`}>
                                                {deployment.status}
                                            </span>
                                            {deployment.update_status === 'update_failed' && (
                                                <AlertCircle className="w-4 h-4 text-yellow-500" title={deployment.last_update_error || 'Update failed'} />
                                            )}
                                            {deployment.update_status === 'updating' && (
                                                <Loader2 className="w-4 h-4 text-blue-500 animate-spin" />
                                            )}
                                        </div>
                                    </div>
                                </Link>
                            ))
                        ) : (
                            <div className="text-center py-8 text-gray-500 dark:text-gray-400">
                                <Server className="w-12 h-12 mx-auto mb-2 opacity-50" />
                                <p>No deployments yet</p>
                                <Link 
                                    to="/provision" 
                                    className="text-blue-600 dark:text-blue-400 hover:underline mt-2 inline-block"
                                >
                                    Create your first deployment
                                </Link>
                            </div>
                        )}
                    </div>
                </div>

                {/* Quick Actions */}
                <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-800 p-6">
                    <h2 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2 mb-4">
                        <Zap className="w-5 h-5" />
                        Quick Actions
                    </h2>
                    <div className="space-y-2">
                        <Link
                            to="/provision"
                            className="flex items-center justify-between p-3 rounded-lg bg-gray-50 dark:bg-gray-800 hover:bg-orange-50 dark:hover:bg-orange-900/20 transition-colors group"
                        >
                            <div className="flex items-center gap-3">
                                <PlayCircle className="w-5 h-5 text-orange-600 dark:text-orange-400" />
                                <span className="text-sm font-medium text-gray-900 dark:text-white">Provision Infrastructure</span>
                            </div>
                            <ArrowRight className="w-4 h-4 text-gray-400 group-hover:text-orange-600 dark:group-hover:text-orange-400" />
                        </Link>
                        <Link
                            to="/services"
                            className="flex items-center justify-between p-3 rounded-lg bg-gray-50 dark:bg-gray-800 hover:bg-blue-50 dark:hover:bg-blue-900/20 transition-colors group"
                        >
                            <div className="flex items-center gap-3">
                                <LayoutGrid className="w-5 h-5 text-blue-600 dark:text-blue-400" />
                                <span className="text-sm font-medium text-gray-900 dark:text-white">Browse Catalog</span>
                            </div>
                            <ArrowRight className="w-4 h-4 text-gray-400 group-hover:text-blue-600 dark:group-hover:text-blue-400" />
                        </Link>
                        <Link
                            to="/deployments"
                            className="flex items-center justify-between p-3 rounded-lg bg-gray-50 dark:bg-gray-800 hover:bg-purple-50 dark:hover:bg-purple-900/20 transition-colors group"
                        >
                            <div className="flex items-center gap-3">
                                <Server className="w-5 h-5 text-purple-600 dark:text-purple-400" />
                                <span className="text-sm font-medium text-gray-900 dark:text-white">Deployments</span>
                            </div>
                            <ArrowRight className="w-4 h-4 text-gray-400 group-hover:text-purple-600 dark:group-hover:text-purple-400" />
                        </Link>
                        {isAdmin && (
                            <>
                                <Link
                                    to="/users"
                                    className="flex items-center justify-between p-3 rounded-lg bg-gray-50 dark:bg-gray-800 hover:bg-indigo-50 dark:hover:bg-indigo-900/20 transition-colors group"
                                >
                                    <div className="flex items-center gap-3">
                                        <Users className="w-5 h-5 text-indigo-600 dark:text-indigo-400" />
                                        <span className="text-sm font-medium text-gray-900 dark:text-white">Manage Users</span>
                                    </div>
                                    <ArrowRight className="w-4 h-4 text-gray-400 group-hover:text-indigo-600 dark:group-hover:text-indigo-400" />
                                </Link>
                                <Link
                                    to="/roles"
                                    className="flex items-center justify-between p-3 rounded-lg bg-gray-50 dark:bg-gray-800 hover:bg-pink-50 dark:hover:bg-pink-900/20 transition-colors group"
                                >
                                    <div className="flex items-center gap-3">
                                        <Shield className="w-5 h-5 text-pink-600 dark:text-pink-400" />
                                        <span className="text-sm font-medium text-gray-900 dark:text-white">Manage Roles</span>
                                    </div>
                                    <ArrowRight className="w-4 h-4 text-gray-400 group-hover:text-pink-600 dark:group-hover:text-pink-400" />
                                </Link>
                            </>
                        )}
                    </div>
                </div>
            </div>

            {/* Recent Notifications */}
            <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-800 p-6">
                    <div className="flex items-center justify-between mb-4">
                        <h2 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                            <Bell className="w-5 h-5" />
                            Recent Notifications
                        </h2>
                        {stats.unreadNotifications > 0 && (
                            <span className="bg-red-500 text-white text-xs font-bold px-2 py-1 rounded-full">
                                {stats.unreadNotifications} unread
                            </span>
                        )}
                    </div>
                    <div className="space-y-3">
                        {recentNotifications.length > 0 ? (
                            recentNotifications.map((notification) => (
                                <div
                                    key={notification.id}
                                    className={`p-4 rounded-lg ${notification.is_read 
                                        ? 'bg-gray-50 dark:bg-gray-800' 
                                        : 'bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800'
                                    }`}
                                >
                                    <div className="flex items-start gap-3">
                                        {getNotificationIcon(notification.type)}
                                        <div className="flex-1 min-w-0">
                                            <p className="text-sm font-medium text-gray-900 dark:text-white">
                                                {notification.title}
                                            </p>
                                            <p className="text-xs text-gray-600 dark:text-gray-400 mt-1 line-clamp-2">
                                                {notification.message}
                                            </p>
                                            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                                                {new Date(notification.created_at).toLocaleDateString()}
                                            </p>
                                        </div>
                                    </div>
                                </div>
                            ))
                        ) : (
                            <div className="text-center py-8 text-gray-500 dark:text-gray-400">
                                <Bell className="w-12 h-12 mx-auto mb-2 opacity-50" />
                                <p>No notifications</p>
                            </div>
                        )}
                    </div>
            </div>

            {/* Environment Breakdown */}
            {stats.envStats.length > 0 && (
                <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-800 p-6">
                    <h2 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2 mb-4">
                        <TrendingUp className="w-5 h-5" />
                        Environment Breakdown
                    </h2>
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                        {['development', 'staging', 'production'].map((env) => {
                            const envStat = stats.envStats.find(s => s.environment === env);
                            const count = envStat?.count || 0;
                            return (
                                <Link
                                    key={env}
                                    to={`/deployments?environment=${env}`}
                                    onClick={(e) => {
                                        const userIsAdmin = isAdmin || (user?.roles || []).some(role => role.toLowerCase() === 'admin');
                                        if (!userIsAdmin && (!activeBusinessUnit || !hasBusinessUnitAccess)) {
                                            e.preventDefault();
                                            setShowBusinessUnitWarning(true);
                                        }
                                    }}
                                    className="p-4 rounded-lg bg-gray-50 dark:bg-gray-800 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                                >
                                    <div className="flex items-center justify-between mb-2">
                                        <EnvironmentBadge environment={env} size="md" showIcon={true} />
                                    </div>
                                    <p className="text-2xl font-bold text-gray-900 dark:text-white">{count}</p>
                                    <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">Deployments</p>
                                </Link>
                            );
                        })}
                    </div>
                </div>
            )}

            {/* Business Unit Warning Modal */}
            <BusinessUnitWarningModal
                isOpen={showBusinessUnitWarning}
                onClose={() => setShowBusinessUnitWarning(false)}
                onSelectBusinessUnit={() => {
                    const selector = document.querySelector('[data-business-unit-selector]');
                    if (selector) {
                        (selector as HTMLElement).click();
                    }
                }}
                action="view deployments"
            />
        </div>
    );
};
