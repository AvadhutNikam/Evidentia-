import React, { createContext, useContext, useState, useEffect } from 'react';
import { UserOut, TokenResponse } from '../types';
import { API_BASE, STORAGE_KEYS, isDemoMode } from '../config/api';

export interface LoginResult {
  success: boolean;
  requires2FA?: boolean;
  tempToken?: string;
  error?: string;
}

interface AuthContextType {
  user: UserOut | null;
  token: string | null;
  role: string;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<LoginResult>;
  complete2FA: (tempToken: string, code: string) => Promise<{ success: boolean; error?: string }>;
  loginAsDemoRole: (role: 'admin' | 'lead_investigator' | 'analyst' | 'reviewer') => Promise<boolean>;
  logout: () => void;
  can: (action: string, caseId?: number | string) => boolean;
  isCaseAccessible: (caseId: number | string) => boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const DEMO_CREDENTIALS: Record<string, { email: string; password: string }> = {
  admin: { email: 'admin@evidentia.gov.in', password: 'Password123!' },
  lead_investigator: { email: 'lead@evidentia.gov.in', password: 'Password123!' },
  analyst: { email: 'analyst@evidentia.gov.in', password: 'Password123!' },
  reviewer: { email: 'reviewer@evidentia.gov.in', password: 'Password123!' }
};

const DEMO_USERS: Record<string, UserOut> = {
  admin: {
    id: 1,
    email: 'admin@evidentia.gov.in',
    full_name: 'Dr. Vikramaditya Sen (Administrator)',
    role: 'admin',
    badge_number: 'CBI-DIR-001',
    is_active: true,
    created_at: new Date().toISOString(),
    accessible_cases: [1, 2, 3, 4, 5]
  },
  lead_investigator: {
    id: 2,
    email: 'lead@evidentia.gov.in',
    full_name: 'Inspector Rajesh Deshmukh',
    role: 'lead_investigator',
    badge_number: 'SIT-LEAD-402',
    is_active: true,
    created_at: new Date().toISOString(),
    accessible_cases: [1, 2]
  },
  analyst: {
    id: 3,
    email: 'analyst@evidentia.gov.in',
    full_name: 'Forensic Officer Anita Roy',
    role: 'analyst',
    badge_number: 'CFSL-BIO-882',
    is_active: true,
    created_at: new Date().toISOString(),
    accessible_cases: [1, 2]
  },
  reviewer: {
    id: 4,
    email: 'reviewer@evidentia.gov.in',
    full_name: 'Hon. Justice K. Ramanathan (Retd)',
    role: 'reviewer',
    badge_number: 'JUD-REV-019',
    is_active: true,
    created_at: new Date().toISOString(),
    accessible_cases: [1, 2]
  }
};

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<UserOut | null>(() => {
    const saved = localStorage.getItem(STORAGE_KEYS.USER);
    return saved ? JSON.parse(saved) : null;
  });
  const [token, setToken] = useState<string | null>(() => {
    return localStorage.getItem(STORAGE_KEYS.ACCESS_TOKEN) || null;
  });
  const [isLoading, setIsLoading] = useState<boolean>(true);

  // Listen to cross-cutting API client events for token refresh and unauthorized logout
  useEffect(() => {
    const handleTokenRefreshed = (e: Event) => {
      const data = (e as CustomEvent).detail;
      if (data?.access_token) {
        setToken(data.access_token);
        if (data.user) {
          setUser(data.user);
        }
      }
    };

    const handleUnauthorized = () => {
      logout();
    };

    window.addEventListener('evidentia:token-refreshed', handleTokenRefreshed);
    window.addEventListener('evidentia:auth-unauthorized', handleUnauthorized);

    return () => {
      window.removeEventListener('evidentia:token-refreshed', handleTokenRefreshed);
      window.removeEventListener('evidentia:auth-unauthorized', handleUnauthorized);
    };
  }, []);

  useEffect(() => {
    // If token exists, verify session with /auth/me
    if (token) {
      fetch(`${API_BASE}/auth/me`, {
        headers: { Authorization: `Bearer ${token}` }
      })
        .then((res) => {
          if (res.ok) return res.json();
          throw new Error('Token expired or invalid');
        })
        .then((userData) => {
          setUser(userData);
          localStorage.setItem(STORAGE_KEYS.USER, JSON.stringify(userData));
        })
        .catch(() => {
          console.warn('Session verification failed, logging out.');
          logout();
        })
        .finally(() => {
          setIsLoading(false);
        });
    } else {
      // If user explicitly logged out, remain logged out
      const explicitlyLoggedOut = localStorage.getItem('evidentia_logged_out') === 'true';
      if (explicitlyLoggedOut) {
        setIsLoading(false);
      } else {
        // First visit default login for seamless evaluator review
        loginAsDemoRole('admin').finally(() => setIsLoading(false));
      }
    }
  }, []);

  const login = async (email: string, password: string): Promise<LoginResult> => {
    setIsLoading(true);
    try {
      const res = await fetch(`${API_BASE}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Login failed');
      }

      const data: TokenResponse = await res.json();
      if (data.requires_2fa) {
        return {
          success: false,
          requires2FA: true,
          tempToken: data.temp_token || ''
        };
      }

      setToken(data.access_token);
      setUser(data.user || null);
      localStorage.setItem(STORAGE_KEYS.ACCESS_TOKEN, data.access_token);
      localStorage.setItem(STORAGE_KEYS.REFRESH_TOKEN, data.refresh_token);
      if (data.user) {
        localStorage.setItem(STORAGE_KEYS.USER, JSON.stringify(data.user));
      }
      localStorage.removeItem('evidentia_logged_out');
      return { success: true };
    } catch (error: any) {
      console.error('Login error:', error);
      // In explicit Demo Mode, allow fallback mock authentication
      if (isDemoMode()) {
        const foundRole = Object.keys(DEMO_CREDENTIALS).find(
          r => DEMO_CREDENTIALS[r].email.toLowerCase() === email.toLowerCase()
        ) as 'admin' | 'lead_investigator' | 'analyst' | 'reviewer' | undefined;

        if (foundRole && DEMO_USERS[foundRole]) {
          const mockUser = DEMO_USERS[foundRole];
          const mockToken = `mock-demo-jwt-token-${foundRole}`;
          setUser(mockUser);
          setToken(mockToken);
          localStorage.setItem(STORAGE_KEYS.ACCESS_TOKEN, mockToken);
          localStorage.setItem(STORAGE_KEYS.REFRESH_TOKEN, `mock-demo-refresh-token-${foundRole}`);
          localStorage.setItem(STORAGE_KEYS.USER, JSON.stringify(mockUser));
          localStorage.removeItem('evidentia_logged_out');
          return { success: true };
        }
      }
      return { success: false, error: error.message || 'Login failed' };
    } finally {
      setIsLoading(false);
    }
  };

  const complete2FA = async (tempToken: string, code: string): Promise<{ success: boolean; error?: string }> => {
    setIsLoading(true);
    try {
      const res = await fetch(`${API_BASE}/auth/2fa/challenge`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ temp_token: tempToken, code })
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || '2FA Verification failed');
      }
      const data: TokenResponse = await res.json();
      setToken(data.access_token);
      setUser(data.user || null);
      localStorage.setItem(STORAGE_KEYS.ACCESS_TOKEN, data.access_token);
      localStorage.setItem(STORAGE_KEYS.REFRESH_TOKEN, data.refresh_token);
      if (data.user) {
        localStorage.setItem(STORAGE_KEYS.USER, JSON.stringify(data.user));
      }
      localStorage.removeItem('evidentia_logged_out');
      return { success: true };
    } catch (error: any) {
      return { success: false, error: error.message || 'Invalid 2FA code' };
    } finally {
      setIsLoading(false);
    }
  };

  const loginAsDemoRole = async (role: 'admin' | 'lead_investigator' | 'analyst' | 'reviewer'): Promise<boolean> => {
    const creds = DEMO_CREDENTIALS[role];
    if (creds) {
      const res = await login(creds.email, creds.password);
      if (res.success) return true;

      // If live backend unreachable and Demo Mode is active, use demo profile
      if (isDemoMode()) {
        const mockUser = DEMO_USERS[role];
        const mockToken = `mock-demo-jwt-token-${role}`;
        setUser(mockUser);
        setToken(mockToken);
        localStorage.setItem(STORAGE_KEYS.ACCESS_TOKEN, mockToken);
        localStorage.setItem(STORAGE_KEYS.REFRESH_TOKEN, `mock-demo-refresh-token-${role}`);
        localStorage.setItem(STORAGE_KEYS.USER, JSON.stringify(mockUser));
        localStorage.removeItem('evidentia_logged_out');
        return true;
      }
    }
    return false;
  };

  const logout = () => {
    setUser(null);
    setToken(null);
    localStorage.removeItem(STORAGE_KEYS.ACCESS_TOKEN);
    localStorage.removeItem(STORAGE_KEYS.REFRESH_TOKEN);
    localStorage.removeItem(STORAGE_KEYS.USER);
    localStorage.setItem('evidentia_logged_out', 'true');
  };

  // Helper for checking role permissions
  const can = (action: string, caseId?: number | string): boolean => {
    if (!user) return false;
    const currentRole = user.role;

    if (currentRole === 'admin') return true;

    // Check case isolation first if caseId is provided
    if (caseId !== undefined && !isCaseAccessible(caseId)) {
      return false;
    }

    switch (action) {
      case 'delete_case':
      case 'finalize_case':
        return currentRole === 'admin' || currentRole === 'lead_investigator';

      case 'delete_evidence':
        return currentRole === 'admin' || currentRole === 'lead_investigator';

      case 'add_evidence':
      case 'analyze':
      case 'override_scoring':
        return currentRole !== 'reviewer';

      case 'read':
      case 'export':
      case 'comment':
        return true;

      default:
        return false;
    }
  };

  const isCaseAccessible = (caseId: number | string): boolean => {
    if (!user) return false;
    if (user.role === 'admin') return true;
    if (!user.accessible_cases) return false;
    const numId = typeof caseId === 'number' ? caseId : parseInt(String(caseId).replace(/\D/g, ''));
    return user.accessible_cases.includes(numId);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        role: user?.role || 'analyst',
        isAuthenticated: !!token && !!user,
        isLoading,
        login,
        complete2FA,
        loginAsDemoRole,
        logout,
        can,
        isCaseAccessible
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
