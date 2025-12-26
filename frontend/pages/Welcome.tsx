import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Building2, Mail, LogOut, User } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';

export const WelcomePage: React.FC = () => {
    const navigate = useNavigate();
    const { user, logout, loading, isAuthenticated } = useAuth();

    const handleLogout = async () => {
        await logout();
    };

    if (loading) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-950">
                <div className="text-center">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-orange-600 mx-auto"></div>
                    <p className="mt-4 text-gray-600 dark:text-gray-400">Loading...</p>
                </div>
            </div>
        );
    }

    // If not authenticated, redirect to login
    if (!isAuthenticated) {
        navigate('/login');
        return null;
    }

    return (
        <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-950 px-4">
            <div className="max-w-2xl w-full">
                {/* Foundry Logo */}
                <div className="flex justify-center mb-8">
                    <div className="flex items-center gap-3">
                        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" className="text-orange-600 dark:text-orange-500">
                            <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                            <path d="M10 9L15 12L10 15V9Z" fill="currentColor" stroke="none" />
                        </svg>
                        <span className="font-bold text-4xl tracking-tight text-gray-900 dark:text-white font-sans">FOUNDRY</span>
                    </div>
                </div>

                {/* Welcome Message */}
                <div className="bg-white dark:bg-gray-900 rounded-2xl shadow-xl p-8 md:p-12 text-center">
                    <div className="mb-6">
                        <Building2 className="w-16 h-16 mx-auto text-gray-400 dark:text-gray-600 mb-4" />
                        <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
                            Welcome to Foundry
                        </h1>
                        <p className="text-lg text-gray-600 dark:text-gray-400">
                            You don't have access to any business units yet
                        </p>
                    </div>

                    {/* Information Card */}
                    <div className="bg-gray-50 dark:bg-gray-800 rounded-xl p-6 mb-8 text-left">
                        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-3">
                            What are Business Units?
                        </h2>
                        <p className="text-gray-600 dark:text-gray-400 mb-4">
                            Business units help organize and separate infrastructure deployments, resources, and access within Foundry. 
                            Each business unit (like "IT Operations") represents a distinct project or department with its own deployments, 
                            members, and owners.
                        </p>
                        <p className="text-gray-600 dark:text-gray-400">
                            To get started, you'll need to be added to a business unit by an administrator or business unit owner.
                        </p>
                    </div>

                    {/* Action Buttons */}
                    <div className="space-y-3">
                        <button
                            onClick={() => {
                                const subject = encodeURIComponent('Business Unit Access Request');
                                const body = encodeURIComponent(`Hello,\n\nI would like to request access to a business unit in Foundry.\n\nUser: ${user?.email}\n\nThank you!`);
                                window.location.href = `mailto:admin@example.com?subject=${subject}&body=${body}`;
                            }}
                            className="w-full flex items-center justify-center gap-2 px-6 py-3 bg-orange-600 hover:bg-orange-700 text-white font-medium rounded-lg transition-colors"
                        >
                            <Mail className="w-5 h-5" />
                            Contact Administrator
                        </button>

                        <div className="flex gap-3">
                            <Link
                                to="/profile"
                                className="flex-1 flex items-center justify-center gap-2 px-4 py-2 border border-gray-300 dark:border-gray-700 text-gray-700 dark:text-gray-300 font-medium rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
                            >
                                <User className="w-4 h-4" />
                                View Profile
                            </Link>

                            <button
                                onClick={handleLogout}
                                className="flex-1 flex items-center justify-center gap-2 px-4 py-2 border border-red-300 dark:border-red-700 text-red-600 dark:text-red-400 font-medium rounded-lg hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors"
                            >
                                <LogOut className="w-4 h-4" />
                                Sign Out
                            </button>
                        </div>
                    </div>
                </div>

                {/* Footer */}
                <p className="text-center text-sm text-gray-500 dark:text-gray-400 mt-6">
                    Need help? Contact your system administrator
                </p>
            </div>
        </div>
    );
};

