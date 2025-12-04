import React from 'react';
import { createContext, useState, useEffect, ReactNode, useCallback } from 'react';
import { API_CONFIG, AUTH_TOKEN_KEY } from '../config/api';

const TOKEN_EXPIRY_KEY = 'auth_token_expiry';
const TOKEN_EXPIRY_DURATION = 480 * 60 * 1000; // 8 hours in milliseconds (matches backend JWT_EXPIRE_MINUTES=480)

interface User {
  email: string;
  name: string;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (name: string, email: string, password: string) => Promise<void>;
  logout: () => void;
}

export const AuthContext = createContext<AuthContextType | undefined>(undefined);

interface AuthProviderProps {
  children: ReactNode;
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const logout = useCallback(() => {
    localStorage.removeItem(AUTH_TOKEN_KEY);
    localStorage.removeItem(TOKEN_EXPIRY_KEY);
    setToken(null);
    setUser(null);
  }, []);

  const checkTokenExpiry = useCallback(() => {
    const storedToken = localStorage.getItem(AUTH_TOKEN_KEY);
    const expiryStr = localStorage.getItem(TOKEN_EXPIRY_KEY);

    if (!storedToken) {
      return false;
    }

    // Handle legacy tokens without expiry timestamp
    if (!expiryStr) {
      console.log('[Auth] Legacy token without expiry found, logging out...');
      logout();
      return false;
    }

    const expiry = parseInt(expiryStr, 10);
    const now = Date.now();

    if (now >= expiry) {
      console.log('[Auth] Token expired after 30 minutes, logging out...');
      logout();
      return false;
    }

    return true;
  }, [logout]);

  useEffect(() => {
    const storedToken = localStorage.getItem(AUTH_TOKEN_KEY);
    if (storedToken && checkTokenExpiry()) {
      setToken(storedToken);
      fetchUserProfile(storedToken);
    } else {
      setIsLoading(false);
    }

    // Listen for 401 unauthorized events from API calls
    const handleUnauthorized = () => {
      console.log('[Auth] Received unauthorized event, logging out...');
      logout();
    };
    window.addEventListener('auth:unauthorized', handleUnauthorized);

    return () => {
      window.removeEventListener('auth:unauthorized', handleUnauthorized);
    };
  }, [checkTokenExpiry, logout]);

  const fetchUserProfile = async (authToken: string) => {
    try {
      const response = await fetch(API_CONFIG.buildApiUrl('/auth/me'), {
        headers: {
          'Authorization': `Bearer ${authToken}`,
        },
      });

      if (response.ok) {
        const userData = await response.json();
        setUser(userData);
      } else if (response.status === 401) {
        console.log('[Auth] 401 on profile fetch, logging out...');
        logout();
      } else {
        localStorage.removeItem(AUTH_TOKEN_KEY);
        localStorage.removeItem(TOKEN_EXPIRY_KEY);
        setToken(null);
      }
    } catch (error) {
      console.error('Failed to fetch user profile:', error);
      logout();
    } finally {
      setIsLoading(false);
    }
  };

  const login = async (email: string, password: string) => {
    const response = await fetch(API_CONFIG.buildApiUrl('/auth/login'), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ email, password }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Invalid credentials');
    }

    const data = await response.json();
    const authToken = data.access_token || data.token;
    
    const expiry = Date.now() + TOKEN_EXPIRY_DURATION;
    localStorage.setItem(AUTH_TOKEN_KEY, authToken);
    localStorage.setItem(TOKEN_EXPIRY_KEY, expiry.toString());
    setToken(authToken);
    
    await fetchUserProfile(authToken);
  };

  const register = async (name: string, email: string, password: string) => {
    const response = await fetch(API_CONFIG.buildApiUrl('/auth/register'), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ name, email, password }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Registration failed');
    }

    const data = await response.json();
    const authToken = data.access_token || data.token;
    
    const expiry = Date.now() + TOKEN_EXPIRY_DURATION;
    localStorage.setItem(AUTH_TOKEN_KEY, authToken);
    localStorage.setItem(TOKEN_EXPIRY_KEY, expiry.toString());
    setToken(authToken);
    
    await fetchUserProfile(authToken);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isAuthenticated: !!token,
        isLoading,
        login,
        register,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}
