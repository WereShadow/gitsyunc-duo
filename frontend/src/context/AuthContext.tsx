import React, { createContext, useContext, useState, useEffect } from 'react';
import { User, Duo } from '../types';
import { api } from '../services/api';

interface AuthContextType {
  user: User | null;
  duo: Duo | null;
  loading: boolean;
  login: (email: string, password: str) => Promise<void>;
  register: (email: string, password: str, full_name: string) => Promise<void>;
  logout: () => void;
  refreshState: () => Promise<void>;
  switchDemoUser: (targetEmail: 'alex@gitsync.dev' | 'morgan@gitsync.dev') => Promise<void>;
}

type str = string;

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [duo, setDuo] = useState<Duo | null>(null);
  const [loading, setLoading] = useState(true);

  const refreshState = async () => {
    try {
      const token = localStorage.getItem('gitsync_token');
      if (!token) {
        setUser(null);
        setDuo(null);
        setLoading(false);
        return;
      }
      const currentUser = await api.getMe();
      setUser(currentUser);

      try {
        const currentDuo = await api.getCurrentDuo();
        setDuo(currentDuo);
      } catch {
        setDuo(null);
      }
    } catch {
      api.removeToken();
      setUser(null);
      setDuo(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refreshState();
  }, []);

  const login = async (email: string, password: str) => {
    await api.login({ email, password });
    await refreshState();
  };

  const register = async (email: string, password: str, full_name: string) => {
    await api.register({ email, password, full_name });
    await refreshState();
  };

  const logout = () => {
    api.removeToken();
    setUser(null);
    setDuo(null);
  };

  const switchDemoUser = async (targetEmail: 'alex@gitsync.dev' | 'morgan@gitsync.dev') => {
    setLoading(true);
    try {
      await api.login({ email: targetEmail, password: 'password123' });
      await refreshState();
    } catch (err) {
      console.error("Failed to switch demo user:", err);
      setLoading(false);
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        duo,
        loading,
        login,
        register,
        logout,
        refreshState,
        switchDemoUser,
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
