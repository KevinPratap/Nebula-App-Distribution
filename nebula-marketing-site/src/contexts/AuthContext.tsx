import React, { createContext, useContext, useState, useEffect } from 'react';
import { authService } from '../services/auth';

interface AuthContextType {
    user: any;
    loading: boolean;
    login: (email: string, password: string, rememberMe?: boolean) => Promise<{ success: boolean; error?: string }>;
    logout: () => Promise<void>;
    refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
    const [user, setUser] = useState<any>(null);
    const [loading, setLoading] = useState(true);

    const refreshUser = async () => {
        try {
            const userData = await authService.refreshUser();
            if (userData && !userData.error) {
                setUser(userData);
            } else {
                setUser(null);
                // Clear local bits if server says session is invalid
                localStorage.removeItem('nebula_user');
            }
        } catch (error) {
            setUser(null);
            localStorage.removeItem('nebula_user');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        refreshUser();
    }, []);

    const login = async (email: string, password: string, rememberMe?: boolean) => {
        const result = await authService.login(email, password, rememberMe);
        if (result.success) {
            await refreshUser(); // Fetch full user profile
        }
        return result;
    };

    const logout = async () => {
        setLoading(true);
        await authService.logout();
        setUser(null);
        setLoading(false);
    };

    return (
        <AuthContext.Provider value={{ user, loading, login, logout, refreshUser }}>
            {children}
        </AuthContext.Provider>
    );
};

export const useAuth = () => {
    const context = useContext(AuthContext);
    if (context === undefined) {
        throw new Error('useAuth must be used within an AuthProvider');
    }
    return context;
};
