import React, { createContext, useContext, useState, useEffect } from 'react';
import { UserOut, TokenResponse } from '../types';

interface AuthContextType {
  user: UserOut | null;
  token: string | null;
  role: string;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<boolean>;
  loginAsDemoRole: (role: 'admin' | 'lead_investigator' | 'analyst' | 'reviewer') => Promise<boolean>;
  logout: () => void;
  can: (action: string, caseId?: number | string) => boolean;
  isCaseAccessible: (caseId: number | string) => boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const API_BASE = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

const DEMO_CREDENTIALS: Record<string, { email: string; password: string }> = {
  admin: { email: 'admin@evidentia.gov.in', password: 'Password123!' },
  lead_investigator: { email: 'lead@evidentia.gov.in', password: 'Password123!' },
  analyst: { email: 'analyst@evidentia.gov.in', password: 'Password123!' },
  reviewer: { email: 'reviewer@evidentia.gov.in', password: 'Password123!' }
};

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<UserOut | null>(() => {
    const saved = localStorage.getItem('evidentia_user');
    return saved ? JSON.parse(saved) : null;
  });
  const [token, setToken] = useState<string | null>(() => {
    return localStorage.getItem('evidentia_access_token') || null;
  });
  const [isLoading, setIsLoading] = useState<boolean>(true);

  useEffect(() => {
    // If token exists, refresh or verify session with /auth/me
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
          localStorage.setItem('evidentia_user', JSON.stringify(userData));
        })
        .catch(() => {
          // Token invalid: clear or fallback to local admin
          console.warn('Session verification failed, logging out.');
          logout();
        })
        .finally(() => {
          setIsLoading(false);
        });
    } else {
      // If no token exists, log in as default Admin so app is instantly ready
      loginAsDemoRole('admin').finally(() => setIsLoading(false));
    }
  }, []);

  const login = async (email: string, password: string): Promise<boolean> => {
    setIsLoading(true);
    try {
      const res = await fetch(`${API_BASE}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Login failed');
      }

      const data: TokenResponse = await res.json();
      setToken(data.access_token);
      setUser(data.user);
      localStorage.setItem('evidentia_access_token', data.access_token);
      localStorage.setItem('evidentia_refresh_token', data.refresh_token);
      localStorage.setItem('evidentia_user', JSON.stringify(data.user));
      return true;
    } catch (error: any) {
      console.error('Login error:', error);
      alert(error.message || 'Login failed');
      return false;
    } finally {
      setIsLoading(false);
    }
  };

  const loginAsDemoRole = async (role: 'admin' | 'lead_investigator' | 'analyst' | 'reviewer'): Promise<boolean> => {
    const creds = DEMO_CREDENTIALS[role];
    if (creds) {
      return login(creds.email, creds.password);
    }
    return false;
  };

  const logout = () => {
    setUser(null);
    setToken(null);
    localStorage.removeItem('evidentia_access_token');
    localStorage.removeItem('evidentia_refresh_token');
    localStorage.removeItem('evidentia_user');
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
