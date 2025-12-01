import React, { useEffect, useState } from 'react';
import { MOCK_BUILDS } from '../constants';
import { Server, Activity, DollarSign, AlertCircle, Zap, ArrowUpRight, GitBranch, CheckCircle2, XCircle, Clock, Loader2, ArrowRight } from 'lucide-react';
import { Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import api from '../services/api';

export const DashboardPage: React.FC = () => {
    const { user } = useAuth();
    const [deployments, setDeployments] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetchDeployments();
    }, []);

    const fetchDeployments = async () => {
        try {
            const data = await api.listDeployments();
            setDeployments(data);
        } catch (error) {
            console.error('Failed to fetch deployments:', error);
        } finally {
            setLoading(false);
        }
    };

    const stats = [
        { name: 'Active Services', value: loading ? '...' : deployments.length.toString(), icon: Server, color: 'bg-blue-500/10 text-blue-600 dark:text-blue-400', change: '+2 this week' },
        { name: 'Monthly Cost', value: '$1,320', icon: DollarSign, color: 'bg-green-500/10 text-green-600 dark:text-green-400', change: '+12% vs last month' },
        { name: 'Health Status', value: '98.9%', icon: Activity, color: 'bg-orange-500/10 text-orange-600 dark:text-orange-400', change: 'All systems normal' },
        { name: 'Open Incidents', value: '0', icon: AlertCircle, color: 'bg-orange-500/10 text-orange-600 dark:text-orange-400', change: 'No active alerts' },
    ];

    return (
        <div className="space-y-6 animate-in fade-in duration-500">
            <div className="flex justify-between items-center">
                <div>
                    <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Platform Overview</h1>
                    <p className="text-gray-500 dark:text-gray-400 mt-1">Welcome back, {user?.full_name || user?.username}. Here's what's happening with your infrastructure.</p>
                </div>
                <Link to="/services" className="bg-orange-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-orange-500 transition-colors shadow-lg shadow-orange-500/20 flex items-center gap-2">
                    <Zap className="w-4 h-4" /> Quick Deploy
                </Link>
            </div>

            {/* Stats Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                {stats.map((stat) => (
                    <div key={stat.name} className="bg-white dark:bg-gray-900 p-6 rounded-2xl border border-gray-200 dark:border-gray-800 transition-colors hover:border-gray-300 dark:hover:border-gray-700">
                        <div className="flex items-center justify-between mb-4">
                            <div className={`p-3 rounded-xl ${stat.color}`}>
                                <stat.icon className="w-6 h-6" />
                            </div>
                            <span className="flex items-center text-xs font-medium text-green-600 dark:text-green-400 bg-green-50 dark:bg-green-500/10 px-2 py-1 rounded-full">
                                {stat.change.includes('+') ? <ArrowUpRight className="w-3 h-3 mr-1" /> : null}
                                {stat.change}
                            </span>
                        </div>
                        <h3 className="text-2xl font-bold text-gray-900 dark:text-white">{stat.value}</h3>
                        <p className="text-sm text-gray-500 dark:text-gray-400 font-medium">{stat.name}</p>
                    </div>
                ))}
            </div>

            {/* Recent Builds Card */}
            <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-800 p-6 shadow-sm transition-colors">
                <div className="flex items-center justify-between mb-6">
                    <div>
                        <h3 className="text-lg font-bold text-gray-900 dark:text-white">Recent Builds</h3>
                        <p className="text-sm text-gray-500 dark:text-gray-400">CI/CD Pipeline Status</p>
                    </div>
                    <button className="text-sm font-medium text-orange-600 dark:text-orange-400 hover:underline flex items-center gap-1">
                        View All History <ArrowRight className="w-3 h-3" />
                    </button>
                </div>

                <div className="space-y-4">
                    {MOCK_BUILDS.map(build => (
                        <div key={build.id} className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-4 rounded-xl border border-gray-100 dark:border-gray-800 bg-gray-50 dark:bg-gray-950/50 hover:border-gray-200 dark:hover:border-gray-700 transition-colors group">
                            {/* Left side: Icon + Info */}
                            <div className="flex items-center gap-4">
                                <div className={`p-2.5 rounded-lg flex-shrink-0 transition-colors ${build.status === 'Running' ? 'bg-blue-500/10 text-blue-600' :
                                        build.status === 'Success' ? 'bg-green-500/10 text-green-600' :
                                            'bg-red-500/10 text-red-600'
                                    }`}>
                                    {build.status === 'Running' ? <Loader2 className="w-5 h-5 animate-spin" /> :
                                        build.status === 'Success' ? <CheckCircle2 className="w-5 h-5" /> :
                                            <XCircle className="w-5 h-5" />}
                                </div>
                                <div>
                                    <div className="flex items-center gap-2 mb-0.5">
                                        <span className="text-sm font-bold text-gray-900 dark:text-white group-hover:text-orange-600 dark:group-hover:text-orange-400 transition-colors">{build.project}</span>
                                        <span className="text-xs text-gray-500 bg-white dark:bg-gray-800 px-1.5 py-0.5 rounded border border-gray-200 dark:border-gray-700">{build.id}</span>
                                    </div>
                                    <div className="flex items-center gap-3 text-xs text-gray-500 dark:text-gray-400">
                                        <span className="flex items-center gap-1"><GitBranch className="w-3 h-3" /> {build.branch}</span>
                                        <span className="hidden sm:inline text-gray-300 dark:text-gray-700">•</span>
                                        <span className="font-mono text-gray-400">{build.commit}</span>
                                    </div>
                                </div>
                            </div>

                            {/* Right side: Meta + Status */}
                            <div className="flex items-center gap-6 justify-between md:justify-end min-w-[200px]">
                                <div className="text-right">
                                    <p className="text-xs font-medium text-gray-900 dark:text-white mb-0.5">{build.initiator}</p>
                                    <p className="text-xs text-gray-500 flex items-center justify-end gap-1">
                                        <Clock className="w-3 h-3" /> {build.duration}
                                    </p>
                                </div>

                                {build.status === 'Running' ? (
                                    <div className="w-24 h-1.5 bg-gray-200 dark:bg-gray-800 rounded-full overflow-hidden">
                                        <div className="h-full bg-blue-500 animate-pulse w-2/3 rounded-full"></div>
                                    </div>
                                ) : (
                                    <span className={`text-xs font-medium px-2 py-1 rounded-md border ${build.status === 'Success' ? 'bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-400 border-green-200 dark:border-green-900/30' :
                                            'bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400 border-red-200 dark:border-red-900/30'
                                        }`}>
                                        {build.status.toUpperCase()}
                                    </span>
                                )}
                            </div>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
};