/**
 * Authentication Service Client for ThermalTrace using Supabase Auth.
 * Manages Supabase Auth session, JWT persistence, and Axios Authorization header headers.
 */
import api from './api';
import { supabase } from './supabaseClient';

export interface User {
  id: string;
  name: string;
  email: string;
}

export interface AuthResponse {
  token: string;
  user: User;
}

const TOKEN_KEY = 'thermaltrace_auth_token';
const USER_KEY = 'thermaltrace_user_data';

export const getStoredToken = (): string | null => {
  return localStorage.getItem(TOKEN_KEY);
};

export const getStoredUser = (): User | null => {
  const data = localStorage.getItem(USER_KEY);
  if (!data) return null;
  try {
    return JSON.parse(data);
  } catch {
    return null;
  }
};

export const setAuthData = (token: string, user: User) => {
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(USER_KEY, JSON.stringify(user));
  api.defaults.headers.common['Authorization'] = `Bearer ${token}`;
};

export const clearAuthData = () => {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
  delete api.defaults.headers.common['Authorization'];
};

// Initialize Authorization header if token exists
const existingToken = getStoredToken();
if (existingToken) {
  api.defaults.headers.common['Authorization'] = `Bearer ${existingToken}`;
}

export const login = async (email: string, password: string, displayName?: string): Promise<User> => {
  // Attempt Supabase Auth login first
  try {
    const { data, error } = await supabase.auth.signInWithPassword({ email, password });
    if (!error && data.session && data.user) {
      const user: User = {
        id: data.user.id,
        name: displayName || data.user.user_metadata?.name || email.split('@')[0].replace('.', ' ').toUpperCase(),
        email: data.user.email || email,
      };
      setAuthData(data.session.access_token, user);
      return user;
    }
  } catch (supaErr) {
    console.warn('Supabase Auth connection fallback to backend authentication:', supaErr);
  }

  // Seamless fallback to FastAPI backend auth endpoint
  const res = await api.post('/api/v1/auth/login', { email, password });
  const user: User = {
    ...res.data.user,
    name: displayName || res.data.user.name || email.split('@')[0].replace('.', ' ').toUpperCase(),
  };
  setAuthData(res.data.token, user);
  return user;
};

export const signup = async (name: string, email: string, password: string): Promise<User> => {
  // Attempt Supabase Auth signup first
  try {
    const { data, error } = await supabase.auth.signUp({
      email,
      password,
      options: { data: { name } },
    });

    if (!error && data.user) {
      const token = data.session?.access_token || `supa-${data.user.id}`;
      const user: User = {
        id: data.user.id,
        name: name || email.split('@')[0],
        email: data.user.email || email,
      };
      setAuthData(token, user);
      return user;
    }
  } catch (supaErr) {
    console.warn('Supabase Auth connection fallback to backend authentication:', supaErr);
  }

  // Fallback to FastAPI backend auth endpoint
  const res = await api.post('/api/v1/auth/signup', { name, email, password });
  setAuthData(res.data.token, res.data.user);
  return res.data.user;
};

export const logout = async () => {
  try {
    await supabase.auth.signOut();
  } catch {
    // Ignore Supabase signout network error
  }
  try {
    await api.post('/api/v1/auth/logout');
  } catch {
    // Ignore backend logout error
  } finally {
    clearAuthData();
  }
};
