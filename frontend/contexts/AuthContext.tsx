import React, { createContext, useContext, useState, useEffect } from 'react';
import api from '../services/api';
import { getAccessToken, removeAccessToken, setAccessToken } from '../utils/tokenStorage';

interface Role {
    id: string;
    name: string;
    description?: string;
    permissions: Permission[];
}

interface Permission {
    id?: string;
    slug: string;
    name?: string;
    description?: string;
    category?: string;
    resource?: string;
    action?: string;
    environment?: string;
    icon?: string;
    created_at?: string;
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
        const token = getAccessToken();
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
            // Error handling - user will be redirected to login
            removeAccessToken();
        } finally {
            setLoading(false);
        }
    };

    const login = async (email: string, password: string) => {
        const response = await api.login(email, password);
        setAccessToken(response.access_token);
        // Refresh token is handled via HTTP-only cookie
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
                logout,
                isAuthenticated: !!user,
                isAdmin
            }}
        >
            {children}
        </AuthContext.Provider>
    );
};
