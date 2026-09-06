/**
 * Shared axios instance for ThermalTrace API.
 * In production builds, VITE_API_URL is strictly required.
 * Localhost fallback (http://localhost:8000) applies exclusively in local development mode.
 */
import axios from 'axios';

const envApiUrl = import.meta.env.VITE_API_URL || import.meta.env.VITE_API_BASE_URL;

let rawApiUrl = envApiUrl;
if (!rawApiUrl) {
  if (import.meta.env.DEV) {
    rawApiUrl = 'http://localhost:8000';
  } else {
    throw new Error('VITE_API_URL environment variable is required for production builds.');
  }
}

// Strip trailing /api/v1 if present to avoid double /api/v1 paths
const normalizedBaseUrl = rawApiUrl.replace(/\/api\/v1\/?$/, '');

const api = axios.create({
  baseURL: normalizedBaseUrl,
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json',
  },
});

export default api;
