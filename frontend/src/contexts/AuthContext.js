import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import API from '@/api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const checkAuth = useCallback(async () => {
    const token = localStorage.getItem('servall_token');
    if (!token) {
      setUser(false);
      setLoading(false);
      return;
    }
    try {
      const { data } = await API.get('/auth/me');
      setUser(data);
    } catch {
      localStorage.removeItem('servall_token');
      setUser(false);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  const login = async (email, password) => {
    const { data } = await API.post('/auth/login', { email, password });
    if (data.access_token) {
      localStorage.setItem('servall_token', data.access_token);
    }
    setUser(data.user);
    return data.user;
  };

  const logout = async () => {
    localStorage.removeItem('servall_token');
    setUser(false);
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, logout, checkAuth }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
