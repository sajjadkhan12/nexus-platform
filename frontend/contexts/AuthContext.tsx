import React, { createContext, useContext, useState, useEffect } from 'react';
import api from '../services/api';

interface Role {
    id: string;
    name: string;
    description?: string;
    permissions: Permission[];
}

interface Permission {
    id: string;
    slug: string;
    description?: string;
}

interface User {
    id: string;
    email: string;
    full_name: string;
    roles: Role[];
    is_active: boolean;
    avatar_url?: string;
    created_at?: string;
}

interface AuthContextType {
    user: User | null;
    loading: boolean;
    login: (email: string, password: string) => Promise<void>;
    register: (email: string, password: string, full_name: string) => Promise<void>;
    logout: () => Promise<void>;
    isAuthenticated: boolean;
    isAdmin: boolean;
    hasPermission: (permissionSlug: string) => boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const useAuth = () => {
    const context = useContext(AuthContext);
    if (!context) {
        throw new Error('useAuth must be used within AuthProvider');
    }
    return context;
};

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
    const [user, setUser] = useState<User | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        // Check if user is already logged in
        const token = localStorage.getItem('access_token');
        if (token) {
            fetchUser();
        } else {
            setLoading(false);
        }
    }, []);

    const fetchUser = async () => {
        try {
            const userData = await api.getCurrentUser();
            setUser(userData);
        } catch (error) {
            console.error('Failed to fetch user:', error);
            localStorage.removeItem('access_token');
        } finally {
            setLoading(false);
        }
    };

    const login = async (email: string, password: string) => {
        const response = await api.login(email, password);
        localStorage.setItem('access_token', response.access_token);
        // Refresh token is handled via HTTP-only cookie
        setUser(response.user);
    };

    const register = async (email: string, password: string, full_name: string) => {
        // Note: Register API might need update if it expected username
        const response = await api.register(email, password, full_name);
        localStorage.setItem('access_token', response.access_token);
        setUser(response.user);
    };

    const logout = async () => {
        await api.logout();
        setUser(null);
    };

    const hasPermission = (permissionSlug: string): boolean => {
        if (!user) return false;
        // Check if any of the user's roles has the permission
        return user.roles.some(role =>
            role.permissions.some(p => p.slug === permissionSlug)
        );
    };

    const isAdmin = user?.roles.some(r => r.name === 'admin') || false;

    // Debug logging
    console.log('Auth Debug:', { user, isAdmin, roles: user?.roles });

    return (
        <AuthContext.Provider
            value={{
                user,
                loading,
                login,
                register,
                logout,
                isAuthenticated: !!user,
                isAdmin,
                hasPermission
            }}
        >
            {children}
        </AuthContext.Provider>
    );
};
