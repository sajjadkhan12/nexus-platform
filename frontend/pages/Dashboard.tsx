import React, { useEffect, useState } from 'react';
import { Server, Activity, DollarSign, AlertCircle, Zap, ArrowUpRight, ArrowRight } from 'lucide-react';
import { Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import api from '../services/api';
import { appLogger } from '../utils/logger';

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
            appLogger.error('Failed to fetch deployments:', error);
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

        </div>
    );
};