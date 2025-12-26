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

interface BusinessUnit {
    id: string;
    name: string;
    slug: string;
    description?: string;
    role?: string;  // Role name (e.g., "bu-owner", "developer", "viewer")
    member_count?: number;  // Number of members in this business unit
    can_manage_members?: boolean;  // Whether user has business_units:manage_members permission
}

interface AuthContextType {
    user: User | null;
    loading: boolean;
    login: (identifier: string, password: string) => Promise<void>;
    logout: () => Promise<void>;
    isAuthenticated: boolean;
    isAdmin: boolean;
    businessUnits: BusinessUnit[];
    activeBusinessUnit: BusinessUnit | null;
    hasBusinessUnitAccess: boolean;
    isOwner: boolean;
    isLoadingBusinessUnits: boolean;
    isSwitchingBusinessUnit: boolean;
    userPermissions: Set<string>;
    hasPermission: (permission: string) => boolean;
    fetchBusinessUnits: () => Promise<void>;
    setActiveBusinessUnit: (bu: BusinessUnit | null) => Promise<void>;
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
    const [businessUnits, setBusinessUnits] = useState<BusinessUnit[]>([]);
    const [activeBusinessUnit, setActiveBusinessUnitState] = useState<BusinessUnit | null>(null);
    const [isLoadingBusinessUnits, setIsLoadingBusinessUnits] = useState(true);
    const [isLoadingActiveBusinessUnit, setIsLoadingActiveBusinessUnit] = useState(true);
    const [isSwitchingBusinessUnit, setIsSwitchingBusinessUnit] = useState(false);
    const [userPermissions, setUserPermissions] = useState<Set<string>>(new Set());

    useEffect(() => {
        // Check if user is already logged in
        const token = getAccessToken();
        if (token) {
            fetchUser();
        } else {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        // Fetch business units when user is loaded (admins can still access without business units)
        if (user) {
            fetchBusinessUnits();
            fetchUserPermissions();
        }
    }, [user]);

    const fetchUserPermissions = async () => {
        try {
            const permissions = await api.request<Array<{ slug: string }>>('/api/v1/users/me/permissions');
            const permissionSlugs = permissions.map(p => p.slug.toLowerCase().trim());
            setUserPermissions(new Set(permissionSlugs));
        } catch (error) {
            console.error('Failed to fetch user permissions:', error);
            setUserPermissions(new Set());
        }
    };

    useEffect(() => {
        // Load active business unit from backend and localStorage
        const loadActiveBusinessUnit = async () => {
            setIsLoadingActiveBusinessUnit(true);
            
            if (businessUnits.length === 0) {
                setIsLoadingActiveBusinessUnit(false);
                return; // No business units to select
            }

            let foundActive = false;

            // Try to get from backend first
            try {
                const backendActive = await api.businessUnitsApi.getActiveBusinessUnit();
                if (backendActive.business_unit_id) {
                    // Try exact match first
                    let found = businessUnits.find(bu => bu.id === backendActive.business_unit_id);
                    // If not found, try case-insensitive match (UUID format might differ)
                    if (!found) {
                        found = businessUnits.find(bu => 
                            bu.id.toLowerCase() === backendActive.business_unit_id.toLowerCase()
                        );
                    }
                    if (found) {
                        setActiveBusinessUnitState(found);
                        localStorage.setItem('activeBusinessUnit', JSON.stringify(found));
                        foundActive = true;
                        setIsLoadingActiveBusinessUnit(false);
                        return;
                    } else {
                        console.warn('Active business unit from backend not found in user\'s business units list:', backendActive.business_unit_id);
                    }
                }
            } catch (error) {
                console.error('Failed to get active business unit from backend:', error);
            }

            // Fallback to localStorage
            if (!foundActive) {
                const stored = localStorage.getItem('activeBusinessUnit');
                if (stored) {
                    try {
                        const parsed = JSON.parse(stored);
                        let found = businessUnits.find(bu => bu.id === parsed.id);
                        // Try case-insensitive match
                        if (!found) {
                            found = businessUnits.find(bu => 
                                bu.id.toLowerCase() === parsed.id?.toLowerCase()
                            );
                        }
                        if (found) {
                            setActiveBusinessUnitState(found);
                            // Sync to backend
                            try {
                                await api.businessUnitsApi.setActiveBusinessUnit(found.id);
                            } catch (e) {
                                console.error('Failed to sync active BU to backend:', e);
                            }
                            foundActive = true;
                            setIsLoadingActiveBusinessUnit(false);
                            return;
                        }
                    } catch (e) {
                        // Invalid stored data, ignore
                        console.error('Failed to parse stored business unit:', e);
                    }
                }
            }

            // Auto-select first business unit if user has access but none is selected
            if (!foundActive && businessUnits.length > 0) {
                setActiveBusinessUnitState(businessUnits[0]);
                localStorage.setItem('activeBusinessUnit', JSON.stringify(businessUnits[0]));
                // Sync to backend
                try {
                    await api.businessUnitsApi.setActiveBusinessUnit(businessUnits[0].id);
                } catch (e) {
                    console.error('Failed to sync active BU to backend:', e);
                }
            }
            
            setIsLoadingActiveBusinessUnit(false);
        };

        loadActiveBusinessUnit();
    }, [businessUnits]);

    const fetchUser = async () => {
        try {
            const userData = await api.getCurrentUser();
            setUser(userData);
        } catch (error: any) {
            // Only logout on authentication errors (401), not permission errors (403)
            // If it's a 403, the user is authenticated but lacks permission - shouldn't logout
            if (error?.message?.includes('401') || error?.message?.includes('Unauthorized') || error?.message?.includes('Session expired')) {
                // Authentication error - user will be redirected to login
                removeAccessToken();
            } else {
                // Other errors (like 403) - log but don't logout
                console.error('Failed to fetch user:', error);
                // Still remove token if it's clearly an auth issue
                if (error?.message?.includes('credentials') || error?.message?.includes('token')) {
                    removeAccessToken();
                }
            }
        } finally {
            setLoading(false);
        }
    };

    const fetchBusinessUnits = async () => {
        setIsLoadingBusinessUnits(true);
        try {
            const units = await api.businessUnitsApi.listBusinessUnits();
            setBusinessUnits(units);
        } catch (error) {
            console.error('Failed to fetch business units:', error);
            setBusinessUnits([]);
        } finally {
            setIsLoadingBusinessUnits(false);
        }
    };

    const setActiveBusinessUnit = async (bu: BusinessUnit | null) => {
        setIsSwitchingBusinessUnit(true);
        try {
            setActiveBusinessUnitState(bu);
            if (bu) {
                localStorage.setItem('activeBusinessUnit', JSON.stringify(bu));
                // Send to backend to store in session
                try {
                    await api.businessUnitsApi.setActiveBusinessUnit(bu.id);
                } catch (error) {
                    console.error('Failed to set active business unit on server:', error);
                }
            } else {
                localStorage.removeItem('activeBusinessUnit');
            }
            // Small delay to allow UI to show loading state
            await new Promise(resolve => setTimeout(resolve, 300));
        } finally {
            setIsSwitchingBusinessUnit(false);
        }
    };

    const login = async (identifier: string, password: string) => {
        const response = await api.login(identifier, password);
        setAccessToken(response.access_token);
        // Refresh token is handled via HTTP-only cookie
        setUser(response.user);
        // Business units will be fetched in useEffect
    };

    const logout = async () => {
        await api.logout();
        setUser(null);
        setBusinessUnits([]);
        setActiveBusinessUnitState(null);
        localStorage.removeItem('activeBusinessUnit');
    };

    const isAdmin = user?.roles.includes('admin') || false;
    // Admins have access even without business units, regular users need business unit access
    const hasBusinessUnitAccess = isAdmin || businessUnits.length > 0;
    // Check if user can manage members in any business unit (permission-based, not role-name-based)
    const isOwner = businessUnits.some(bu => bu.can_manage_members === true) || false;
    
    // Helper function to check if user has a specific permission
    const hasPermission = (permission: string): boolean => {
        if (isAdmin) return true; // Admins have all permissions
        const normalizedPermission = permission.toLowerCase().trim();
        return userPermissions.has(normalizedPermission);
    };

    return (
        <AuthContext.Provider
            value={{
                user,
                loading,
                login,
                logout,
                isAuthenticated: !!user,
                isAdmin,
                businessUnits,
                activeBusinessUnit,
                hasBusinessUnitAccess,
                isOwner,
                isLoadingBusinessUnits,
                isLoadingActiveBusinessUnit,
                isSwitchingBusinessUnit,
                userPermissions,
                hasPermission,
                fetchBusinessUnits,
                setActiveBusinessUnit
            }}
        >
            {children}
        </AuthContext.Provider>
    );
};
