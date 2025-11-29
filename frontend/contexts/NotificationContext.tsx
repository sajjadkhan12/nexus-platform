import React, { createContext, useContext, useState, useCallback } from 'react';
import { X, CheckCircle, AlertCircle, Info, AlertTriangle } from 'lucide-react';

export type NotificationType = 'success' | 'error' | 'info' | 'warning';

export interface Notification {
    id: string;
    type: NotificationType;
    message: string;
    duration?: number;
}

interface NotificationContextType {
    addNotification: (type: NotificationType, message: string, duration?: number) => void;
    removeNotification: (id: string) => void;
}

const NotificationContext = createContext<NotificationContextType | undefined>(undefined);

export const useNotification = () => {
    const context = useContext(NotificationContext);
    if (!context) {
        throw new Error('useNotification must be used within a NotificationProvider');
    }
    return context;
};

export const NotificationProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
    const [notifications, setNotifications] = useState<Notification[]>([]);

    const removeNotification = useCallback((id: string) => {
        setNotifications(prev => prev.filter(n => n.id !== id));
    }, []);

    const addNotification = useCallback((type: NotificationType, message: string, duration = 5000) => {
        const id = Math.random().toString(36).substring(2, 9);
        setNotifications(prev => [...prev, { id, type, message, duration }]);

        if (duration > 0) {
            setTimeout(() => {
                removeNotification(id);
            }, duration);
        }
    }, [removeNotification]);

    return (
        <NotificationContext.Provider value={{ addNotification, removeNotification }}>
            {children}

            {/* Notification Container */}
            <div className="fixed top-4 right-4 z-50 flex flex-col gap-2 max-w-md w-full pointer-events-none">
                {notifications.map(notification => (
                    <div
                        key={notification.id}
                        className={`
                            pointer-events-auto flex items-start gap-3 p-4 rounded-lg shadow-lg border animate-in slide-in-from-right-full duration-300
                            ${notification.type === 'success' ? 'bg-white dark:bg-gray-800 border-green-200 dark:border-green-900/50 text-green-800 dark:text-green-400' : ''}
                            ${notification.type === 'error' ? 'bg-white dark:bg-gray-800 border-red-200 dark:border-red-900/50 text-red-800 dark:text-red-400' : ''}
                            ${notification.type === 'warning' ? 'bg-white dark:bg-gray-800 border-yellow-200 dark:border-yellow-900/50 text-yellow-800 dark:text-yellow-400' : ''}
                            ${notification.type === 'info' ? 'bg-white dark:bg-gray-800 border-blue-200 dark:border-blue-900/50 text-blue-800 dark:text-blue-400' : ''}
                        `}
                    >
                        <div className="flex-shrink-0 mt-0.5">
                            {notification.type === 'success' && <CheckCircle className="w-5 h-5 text-green-500" />}
                            {notification.type === 'error' && <AlertCircle className="w-5 h-5 text-red-500" />}
                            {notification.type === 'warning' && <AlertTriangle className="w-5 h-5 text-yellow-500" />}
                            {notification.type === 'info' && <Info className="w-5 h-5 text-blue-500" />}
                        </div>
                        <div className="flex-1 text-sm font-medium text-gray-900 dark:text-gray-100">
                            {notification.message}
                        </div>
                        <button
                            onClick={() => removeNotification(notification.id)}
                            className="flex-shrink-0 text-gray-400 hover:text-gray-500 dark:hover:text-gray-300 transition-colors"
                        >
                            <X className="w-4 h-4" />
                        </button>
                    </div>
                ))}
            </div>
        </NotificationContext.Provider>
    );
};
