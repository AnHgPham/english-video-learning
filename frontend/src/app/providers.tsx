'use client';

import { createContext, useContext, useEffect, useState } from 'react';
import apiClient, { User } from '@/lib/api-client';
import { usePathname, useRouter } from 'next/navigation';

interface AuthContextType {
  user: User | null;
  loading: boolean;
  login: (email: string, password?: string, openId?: string) => Promise<void>;
  logout: () => Promise<void>;
  isAdmin: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
}

export function Providers({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();
  const pathname = usePathname();

  // Check authentication on mount
  useEffect(() => {
    checkAuth();
  }, []);

  // Handle unauthorized events
  useEffect(() => {
    const handleUnauthorized = () => {
      setUser(null);
      if (!pathname?.startsWith('/login')) {
        router.push('/login');
      }
    };

    window.addEventListener('auth:unauthorized', handleUnauthorized);
    return () => window.removeEventListener('auth:unauthorized', handleUnauthorized);
  }, [pathname, router]);

  const checkAuth = async () => {
    try {
      const token = apiClient.getToken();
      if (!token) {
        setLoading(false);
        return;
      }

      const response = await apiClient.auth.check();
      if (response.authenticated) {
        setUser(response.user);
      }
    } catch (error) {
      console.error('Auth check failed:', error);
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  const login = async (email: string, password?: string, openId?: string) => {
    try {
      const response = await apiClient.auth.login({
        email,
        password,
        open_id: openId,
      });
      setUser(response.user);
      router.push('/');
    } catch (error) {
      throw error;
    }
  };

  const logout = async () => {
    try {
      await apiClient.auth.logout();
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      setUser(null);
      router.push('/login');
    }
  };

  const isAdmin = user?.role === 'admin';

  return (
    <AuthContext.Provider value={{ user, loading, login, logout, isAdmin }}>
      {children}
    </AuthContext.Provider>
  );
}
