import React, { useState, useEffect, useRef } from 'react';
import { Bell, Check, Trash2, ExternalLink, Info, CheckCircle, AlertTriangle, AlertCircle } from 'lucide-react';
import { Link } from 'react-router-dom';
import api from '../services/api';

interface Notification {
    id: string;
    title: string;
    message: string;
    type: 'info' | 'success' | 'warning' | 'error';
    is_read: boolean;
    created_at: string;
    link?: string;
}

export const NotificationCenter: React.FC = () => {
    const [notifications, setNotifications] = useState<Notification[]>([]);
    const [isOpen, setIsOpen] = useState(false);
    const [loading, setLoading] = useState(false);
    const dropdownRef = useRef<HTMLDivElement>(null);

    const unreadCount = notifications.filter(n => !n.is_read).length;

    useEffect(() => {
        loadNotifications();

        // Poll for new notifications only when tab is visible
        // Increased from 10s to 30s to reduce server load
        let interval: NodeJS.Timeout | null = null;

        const startPolling = () => {
            // Clear existing interval if any
            if (interval) clearInterval(interval);
            // Poll every 30 seconds (reduced from 10s)
            interval = setInterval(loadNotifications, 30000);
        };

        const stopPolling = () => {
            if (interval) {
                clearInterval(interval);
                interval = null;
            }
        };

        // Handle visibility change
        const handleVisibilityChange = () => {
            if (document.hidden) {
                stopPolling();
            } else {
                loadNotifications(); // Fetch immediately when tab becomes visible
                startPolling();
            }
        };

        // Start polling initially if tab is visible
        if (!document.hidden) {
            startPolling();
        }

        // Listen for visibility changes
        document.addEventListener('visibilitychange', handleVisibilityChange);

        return () => {
            stopPolling();
            document.removeEventListener('visibilitychange', handleVisibilityChange);
        };
    }, []);

    // Close dropdown when clicking outside
    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
                setIsOpen(false);
            }
        };

        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    const loadNotifications = async () => {
        try {
            const data = await api.getNotifications();
            setNotifications(data);
        } catch (err) {
            console.error('Failed to load notifications:', err);
        }
    };

    const markAsRead = async (id: string) => {
        try {
            await api.markNotificationRead(id);
            setNotifications(prev => prev.map(n =>
                n.id === id ? { ...n, is_read: true } : n
            ));
        } catch (err) {
            console.error('Failed to mark notification as read:', err);
        }
    };

    const markAllAsRead = async () => {
        try {
            await api.markAllNotificationsRead();
            setNotifications(prev => prev.map(n => ({ ...n, is_read: true })));
        } catch (err) {
            console.error('Failed to mark all as read:', err);
        }
    };

    const getIcon = (type: string) => {
        switch (type) {
            case 'success': return <CheckCircle className="w-5 h-5 text-green-500" />;
            case 'warning': return <AlertTriangle className="w-5 h-5 text-yellow-500" />;
            case 'error': return <AlertCircle className="w-5 h-5 text-red-500" />;
            default: return <Info className="w-5 h-5 text-blue-500" />;
        }
    };

    const formatTime = (dateString: string) => {
        const date = new Date(dateString);
        const now = new Date();
        const diff = now.getTime() - date.getTime();

        if (diff < 60000) return 'Just now';
        if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
        if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
        return date.toLocaleDateString();
    };

    return (
        <div className="relative" ref={dropdownRef}>
            <button
                onClick={() => setIsOpen(!isOpen)}
                className="relative p-2 text-gray-400 hover:text-gray-500 dark:hover:text-gray-300 transition-colors rounded-full hover:bg-gray-100 dark:hover:bg-gray-800"
            >
                <Bell className="w-5 h-5" />
                {unreadCount > 0 && (
                    <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-red-500 rounded-full ring-2 ring-white dark:ring-gray-900" />
                )}
            </button>

            {isOpen && (
                <div className="absolute right-0 mt-2 w-80 sm:w-96 bg-white dark:bg-gray-900 rounded-xl shadow-lg border border-gray-200 dark:border-gray-800 overflow-hidden z-50">
                    <div className="p-4 border-b border-gray-200 dark:border-gray-800 flex items-center justify-between">
                        <h3 className="font-semibold text-gray-900 dark:text-white">Notifications</h3>
                        {unreadCount > 0 && (
                            <button
                                onClick={markAllAsRead}
                                className="text-xs text-orange-600 dark:text-orange-400 hover:text-orange-700 font-medium"
                            >
                                Mark all as read
                            </button>
                        )}
                    </div>

                    <div className="max-h-[400px] overflow-y-auto">
                        {notifications.length === 0 ? (
                            <div className="p-8 text-center text-gray-500 dark:text-gray-400">
                                <Bell className="w-8 h-8 mx-auto mb-2 opacity-20" />
                                <p>No notifications</p>
                            </div>
                        ) : (
                            <div className="divide-y divide-gray-100 dark:divide-gray-800">
                                {notifications.map((notification) => (
                                    <div
                                        key={notification.id}
                                        onClick={() => {
                                            if (notification.link) {
                                                markAsRead(notification.id);
                                                setIsOpen(false);
                                                // Use window.location for external or just navigate if internal
                                                // Since we are in router context, we can use Link wrapper or navigate
                                            }
                                        }}
                                        className={`p-4 hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors cursor-pointer relative group ${!notification.is_read ? 'bg-orange-50/50 dark:bg-orange-900/10' : ''
                                            }`}
                                    >
                                        {notification.link && (
                                            <Link
                                                to={notification.link}
                                                className="absolute inset-0 z-10"
                                                onClick={() => {
                                                    markAsRead(notification.id);
                                                    setIsOpen(false);
                                                }}
                                            />
                                        )}
                                        <div className="flex gap-3 relative z-0">
                                            <div className="flex-shrink-0 mt-1">
                                                {getIcon(notification.type)}
                                            </div>
                                            <div className="flex-1 min-w-0">
                                                <div className="flex items-start justify-between gap-2">
                                                    <p className={`text-sm font-medium ${!notification.is_read ? 'text-gray-900 dark:text-white' : 'text-gray-600 dark:text-gray-300'
                                                        }`}>
                                                        {notification.title}
                                                    </p>
                                                    <span className="text-xs text-gray-400 whitespace-nowrap">
                                                        {formatTime(notification.created_at)}
                                                    </span>
                                                </div>
                                                <p className="text-sm text-gray-500 dark:text-gray-400 mt-1 break-words">
                                                    {notification.message}
                                                </p>
                                                {!notification.is_read && (
                                                    <div className="mt-2 flex justify-end">
                                                        <button
                                                            onClick={(e) => {
                                                                e.preventDefault();
                                                                e.stopPropagation();
                                                                markAsRead(notification.id);
                                                            }}
                                                            className="text-xs text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 flex items-center gap-1 relative z-20"
                                                        >
                                                            <Check className="w-3 h-3" />
                                                            Mark as read
                                                        </button>
                                                    </div>
                                                )}
                                            </div>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
};
