import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Users, Shield, Server, Settings, Activity, ArrowRight, Layers } from 'lucide-react';
import api from '../services/api';

interface AdminStats {
    total_users: number;
    active_users: number;
    inactive_users: number;
    total_groups: number;
    total_roles: number;
    role_distribution: { role: string; count: number }[];
}

export const AdminDashboard: React.FC = () => {
    const navigate = useNavigate();
    const [stats, setStats] = useState<AdminStats | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchStats = async () => {
            try {
                const data = await api.getAdminStats();
                setStats(data);
            } catch (error) {
                console.error('Failed to fetch admin stats:', error);
            } finally {
                setLoading(false);
            }
        };
        fetchStats();
    }, []);

    if (loading) {
        return (
            <div className="flex items-center justify-center min-h-[400px]">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
            </div>
        );
    }

    return (
        <div className="max-w-7xl mx-auto space-y-8">
            <div>
                <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Admin Dashboard</h1>
                <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">System overview and management</p>
            </div>

            {/* Stats Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                <button
                    onClick={() => navigate('/users')}
                    className="bg-white dark:bg-gray-900 p-6 rounded-xl border border-gray-200 dark:border-gray-800 shadow-sm hover:border-indigo-500 dark:hover:border-indigo-500 transition-all cursor-pointer text-left w-full"
                >
                    <div className="flex items-center justify-between mb-4">
                        <div className="p-2 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
                            <Users className="w-6 h-6 text-blue-600 dark:text-blue-400" />
                        </div>
                        <span className="text-xs font-medium text-green-600 bg-green-50 dark:bg-green-900/20 px-2 py-1 rounded-full">
                            {stats?.active_users} Active
                        </span>
                    </div>
                    <p className="text-sm text-gray-500 dark:text-gray-400">Total Users</p>
                    <h3 className="text-2xl font-bold text-gray-900 dark:text-white">{stats?.total_users}</h3>
                </button>

                <button
                    onClick={() => navigate('/groups')}
                    className="bg-white dark:bg-gray-900 p-6 rounded-xl border border-gray-200 dark:border-gray-800 shadow-sm hover:border-indigo-500 dark:hover:border-indigo-500 transition-all cursor-pointer text-left w-full"
                >
                    <div className="flex items-center justify-between mb-4">
                        <div className="p-2 bg-indigo-50 dark:bg-indigo-900/20 rounded-lg">
                            <Layers className="w-6 h-6 text-indigo-600 dark:text-indigo-400" />
                        </div>
                    </div>
                    <p className="text-sm text-gray-500 dark:text-gray-400">Total Groups</p>
                    <h3 className="text-2xl font-bold text-gray-900 dark:text-white">{stats?.total_groups}</h3>
                </button>

                <button
                    onClick={() => navigate('/roles')}
                    className="bg-white dark:bg-gray-900 p-6 rounded-xl border border-gray-200 dark:border-gray-800 shadow-sm hover:border-indigo-500 dark:hover:border-indigo-500 transition-all cursor-pointer text-left w-full"
                >
                    <div className="flex items-center justify-between mb-4">
                        <div className="p-2 bg-purple-50 dark:bg-purple-900/20 rounded-lg">
                            <Shield className="w-6 h-6 text-purple-600 dark:text-purple-400" />
                        </div>
                    </div>
                    <p className="text-sm text-gray-500 dark:text-gray-400">Total Roles</p>
                    <h3 className="text-2xl font-bold text-gray-900 dark:text-white">{stats?.total_roles}</h3>
                </button>

                <div className="bg-white dark:bg-gray-900 p-6 rounded-xl border border-gray-200 dark:border-gray-800 shadow-sm">
                    <div className="flex items-center justify-between mb-4">
                        <div className="p-2 bg-orange-50 dark:bg-orange-900/20 rounded-lg">
                            <Activity className="w-6 h-6 text-orange-600 dark:text-orange-400" />
                        </div>
                    </div>
                    <p className="text-sm text-gray-500 dark:text-gray-400">System Status</p>
                    <h3 className="text-2xl font-bold text-gray-900 dark:text-white">Healthy</h3>
                </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                {/* Quick Actions */}
                <div className="lg:col-span-2 space-y-6">
                    <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Quick Actions</h2>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <button
                            onClick={() => navigate('/users')}
                            className="flex items-center justify-between p-4 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl hover:border-indigo-500 dark:hover:border-indigo-500 transition-colors group text-left"
                        >
                            <div className="flex items-center gap-4">
                                <div className="p-3 bg-gray-50 dark:bg-gray-800 rounded-lg group-hover:bg-indigo-50 dark:group-hover:bg-indigo-900/20 transition-colors">
                                    <Users className="w-6 h-6 text-gray-600 dark:text-gray-400 group-hover:text-indigo-600 dark:group-hover:text-indigo-400" />
                                </div>
                                <div>
                                    <h3 className="font-medium text-gray-900 dark:text-white">Manage Users</h3>
                                    <p className="text-sm text-gray-500 dark:text-gray-400">Add, edit, or remove users</p>
                                </div>
                            </div>
                            <ArrowRight className="w-5 h-5 text-gray-400 group-hover:text-indigo-600 dark:group-hover:text-indigo-400 transition-colors" />
                        </button>

                        <button
                            onClick={() => navigate('/groups')}
                            className="flex items-center justify-between p-4 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl hover:border-indigo-500 dark:hover:border-indigo-500 transition-colors group text-left"
                        >
                            <div className="flex items-center gap-4">
                                <div className="p-3 bg-gray-50 dark:bg-gray-800 rounded-lg group-hover:bg-indigo-50 dark:group-hover:bg-indigo-900/20 transition-colors">
                                    <Layers className="w-6 h-6 text-gray-600 dark:text-gray-400 group-hover:text-indigo-600 dark:group-hover:text-indigo-400" />
                                </div>
                                <div>
                                    <h3 className="font-medium text-gray-900 dark:text-white">Manage Groups</h3>
                                    <p className="text-sm text-gray-500 dark:text-gray-400">Organize users into groups</p>
                                </div>
                            </div>
                            <ArrowRight className="w-5 h-5 text-gray-400 group-hover:text-indigo-600 dark:group-hover:text-indigo-400 transition-colors" />
                        </button>

                        <button
                            onClick={() => navigate('/roles')}
                            className="flex items-center justify-between p-4 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl hover:border-indigo-500 dark:hover:border-indigo-500 transition-colors group text-left"
                        >
                            <div className="flex items-center gap-4">
                                <div className="p-3 bg-gray-50 dark:bg-gray-800 rounded-lg group-hover:bg-indigo-50 dark:group-hover:bg-indigo-900/20 transition-colors">
                                    <Shield className="w-6 h-6 text-gray-600 dark:text-gray-400 group-hover:text-indigo-600 dark:group-hover:text-indigo-400" />
                                </div>
                                <div>
                                    <h3 className="font-medium text-gray-900 dark:text-white">Manage Roles</h3>
                                    <p className="text-sm text-gray-500 dark:text-gray-400">Define roles and permissions</p>
                                </div>
                            </div>
                            <ArrowRight className="w-5 h-5 text-gray-400 group-hover:text-indigo-600 dark:group-hover:text-indigo-400 transition-colors" />
                        </button>

                        <button
                            onClick={() => navigate('/settings')}
                            className="flex items-center justify-between p-4 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl hover:border-indigo-500 dark:hover:border-indigo-500 transition-colors group text-left"
                        >
                            <div className="flex items-center gap-4">
                                <div className="p-3 bg-gray-50 dark:bg-gray-800 rounded-lg group-hover:bg-indigo-50 dark:group-hover:bg-indigo-900/20 transition-colors">
                                    <Settings className="w-6 h-6 text-gray-600 dark:text-gray-400 group-hover:text-indigo-600 dark:group-hover:text-indigo-400" />
                                </div>
                                <div>
                                    <h3 className="font-medium text-gray-900 dark:text-white">System Settings</h3>
                                    <p className="text-sm text-gray-500 dark:text-gray-400">Configure platform settings</p>
                                </div>
                            </div>
                            <ArrowRight className="w-5 h-5 text-gray-400 group-hover:text-indigo-600 dark:group-hover:text-indigo-400 transition-colors" />
                        </button>
                    </div>
                </div>

                {/* Role Distribution */}
                <div className="bg-white dark:bg-gray-900 p-6 rounded-xl border border-gray-200 dark:border-gray-800 shadow-sm">
                    <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-6">Role Distribution</h3>
                    <div className="space-y-4">
                        {stats?.role_distribution.map((item, index) => {
                            const percentage = Math.round((item.count / (stats.total_users || 1)) * 100);
                            return (
                                <div key={item.role}>
                                    <div className="flex justify-between text-sm mb-1">
                                        <span className="font-medium text-gray-700 dark:text-gray-300 capitalize">{item.role}</span>
                                        <span className="text-gray-500 dark:text-gray-400">{item.count} users ({percentage}%)</span>
                                    </div>
                                    <div className="w-full bg-gray-100 dark:bg-gray-800 rounded-full h-2">
                                        <div
                                            className={`h-2 rounded-full ${index % 3 === 0 ? 'bg-indigo-600' :
                                                index % 3 === 1 ? 'bg-purple-600' : 'bg-blue-600'
                                                }`}
                                            style={{ width: `${percentage}%` }}
                                        ></div>
                                    </div>
                                </div>
                            );
                        })}
                        {(!stats?.role_distribution || stats.role_distribution.length === 0) && (
                            <p className="text-sm text-gray-500 text-center py-4">No data available</p>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
};
