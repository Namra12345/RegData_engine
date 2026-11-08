

import React, { createContext, useContext, useState } from 'react';
import { apiService } from '../api/services';

interface User {
  id: number;
  username: string;
  role: string;
  is_active: boolean;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
  isAuthenticated: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [token, setToken] = useState<string | null>(localStorage.getItem('regdata_token'));
  const [user, setUser] = useState<User | null>(() => {
    const savedUser = localStorage.getItem('regdata_user');
    return savedUser ? JSON.parse(savedUser) : null;
  });

  const login = async (username: string, password: string) => {
    const data = await apiService.login(username, password);
    const accessToken = data.access_token;
    localStorage.setItem('regdata_token', accessToken);
    setToken(accessToken);

    // Fetch user profile
    const profile = await apiService.getCurrentUser();
    localStorage.setItem('regdata_user', JSON.stringify(profile));
    setUser(profile);
  };

  const logout = () => {
    localStorage.removeItem('regdata_token');
    localStorage.removeItem('regdata_user');
    setToken(null);
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, token, login, logout, isAuthenticated: !!token }}>
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