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
    username: string;
    full_name: string;
    roles: string[];  // Now an array of role names from Casbin
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

    const isAdmin = user?.roles.includes('admin') || false;

    return (
        <AuthContext.Provider
            value={{
                user,
                loading,
                login,
                register,
                logout,
                isAuthenticated: !!user,
                isAdmin
            }}
        >
            {children}
        </AuthContext.Provider>
    );
};
