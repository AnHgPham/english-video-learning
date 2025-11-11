/**
 * Authentication Context for English Video Learning Platform
 * Manages user authentication state, login/logout/register flows
 * Provides ProtectedRoute wrapper for auth-gated pages
 */

import React, {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  ReactNode,
} from 'react';
import { useNavigate } from 'react-router-dom';
import apiClient, {
  User,
  LoginRequest,
  RegisterRequest,
  TokenResponse,
} from './api-client';

// ============================================
// Type Definitions
// ============================================

interface AuthContextType {
  // State
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;

  // Actions
  login: (credentials: LoginRequest) => Promise<void>;
  register: (data: RegisterRequest) => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
  clearError: () => void;

  // Helpers
  isAdmin: () => boolean;
}

// ============================================
// Context Creation
// ============================================

const AuthContext = createContext<AuthContextType | undefined>(undefined);

// ============================================
// Auth Provider Component
// ============================================

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const isAuthenticated = !!user;

  /**
   * Initialize auth state on mount
   * Check if user has valid token and fetch user data
   */
  useEffect(() => {
    const initAuth = async () => {
      const token = apiClient.getToken();

      if (!token) {
        setIsLoading(false);
        return;
      }

      try {
        // Verify token and get user data
        const userData = await apiClient.auth.me();
        setUser(userData);
      } catch (err) {
        // Token is invalid, clear it
        console.error('Auth initialization failed:', err);
        apiClient.clearToken();
        setUser(null);
      } finally {
        setIsLoading(false);
      }
    };

    initAuth();
  }, []);

  /**
   * Listen for unauthorized events (401 responses)
   * Auto-logout user when token expires or is invalid
   */
  useEffect(() => {
    const handleUnauthorized = () => {
      setUser(null);
      setError('Your session has expired. Please login again.');
    };

    window.addEventListener('auth:unauthorized', handleUnauthorized);

    return () => {
      window.removeEventListener('auth:unauthorized', handleUnauthorized);
    };
  }, []);

  /**
   * Login user
   */
  const login = useCallback(async (credentials: LoginRequest) => {
    setIsLoading(true);
    setError(null);

    try {
      const response: TokenResponse = await apiClient.auth.login(credentials);
      setUser(response.user);
    } catch (err: any) {
      const errorMessage = err?.detail || 'Login failed. Please try again.';
      setError(errorMessage);
      throw new Error(errorMessage);
    } finally {
      setIsLoading(false);
    }
  }, []);

  /**
   * Register new user
   */
  const register = useCallback(async (data: RegisterRequest) => {
    setIsLoading(true);
    setError(null);

    try {
      const response: TokenResponse = await apiClient.auth.register(data);
      setUser(response.user);
    } catch (err: any) {
      const errorMessage = err?.detail || 'Registration failed. Please try again.';
      setError(errorMessage);
      throw new Error(errorMessage);
    } finally {
      setIsLoading(false);
    }
  }, []);

  /**
   * Logout user
   */
  const logout = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      await apiClient.auth.logout();
    } catch (err) {
      console.error('Logout error:', err);
      // Continue with logout even if API call fails
    } finally {
      setUser(null);
      apiClient.clearToken();
      setIsLoading(false);
    }
  }, []);

  /**
   * Refresh user data
   * Useful after profile updates
   */
  const refreshUser = useCallback(async () => {
    if (!isAuthenticated) return;

    try {
      const userData = await apiClient.auth.me();
      setUser(userData);
    } catch (err) {
      console.error('Failed to refresh user data:', err);
      setError('Failed to refresh user data');
    }
  }, [isAuthenticated]);

  /**
   * Clear error message
   */
  const clearError = useCallback(() => {
    setError(null);
  }, []);

  /**
   * Check if current user is admin
   */
  const isAdmin = useCallback((): boolean => {
    return user?.role === 'admin';
  }, [user]);

  // Context value
  const value: AuthContextType = {
    user,
    isAuthenticated,
    isLoading,
    error,
    login,
    register,
    logout,
    refreshUser,
    clearError,
    isAdmin,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

// ============================================
// Custom Hook to Use Auth Context
// ============================================

/**
 * Hook to access auth context
 * Must be used within AuthProvider
 */
export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);

  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }

  return context;
};

// ============================================
// Protected Route Component
// ============================================

interface ProtectedRouteProps {
  children: ReactNode;
  requireAdmin?: boolean;
  redirectTo?: string;
}

/**
 * Protected Route Wrapper
 * Redirects to login if user is not authenticated
 * Optionally requires admin role
 */
export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({
  children,
  requireAdmin = false,
  redirectTo = '/login',
}) => {
  const { isAuthenticated, isLoading, isAdmin } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    // Wait for loading to complete
    if (isLoading) return;

    // Redirect if not authenticated
    if (!isAuthenticated) {
      navigate(redirectTo, { replace: true });
      return;
    }

    // Redirect if admin is required but user is not admin
    if (requireAdmin && !isAdmin()) {
      navigate('/', { replace: true });
    }
  }, [isAuthenticated, isLoading, requireAdmin, isAdmin, navigate, redirectTo]);

  // Show loading state
  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading...</p>
        </div>
      </div>
    );
  }

  // Don't render children if not authenticated or not admin (when required)
  if (!isAuthenticated || (requireAdmin && !isAdmin())) {
    return null;
  }

  return <>{children}</>;
};

// ============================================
// Public Route Component (Redirect if authenticated)
// ============================================

interface PublicRouteProps {
  children: ReactNode;
  redirectTo?: string;
}

/**
 * Public Route Wrapper
 * Redirects authenticated users away from login/register pages
 */
export const PublicRoute: React.FC<PublicRouteProps> = ({
  children,
  redirectTo = '/',
}) => {
  const { isAuthenticated, isLoading } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (isLoading) return;

    if (isAuthenticated) {
      navigate(redirectTo, { replace: true });
    }
  }, [isAuthenticated, isLoading, navigate, redirectTo]);

  // Show loading state
  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading...</p>
        </div>
      </div>
    );
  }

  // Don't render if authenticated (will redirect)
  if (isAuthenticated) {
    return null;
  }

  return <>{children}</>;
};

// ============================================
// Higher-Order Component for Auth Protection
// ============================================

/**
 * HOC to wrap components with authentication requirement
 * Alternative to ProtectedRoute for component-level protection
 */
export function withAuth<P extends object>(
  Component: React.ComponentType<P>,
  requireAdmin: boolean = false
) {
  return function AuthenticatedComponent(props: P) {
    return (
      <ProtectedRoute requireAdmin={requireAdmin}>
        <Component {...props} />
      </ProtectedRoute>
    );
  };
}

// ============================================
// Exports
// ============================================

export default AuthContext;
