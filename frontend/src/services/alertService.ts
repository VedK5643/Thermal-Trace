import type { Alert } from '../types/alert';
import api from './api';

/**
 * Fetch alert data from FastAPI backend.
 * Phase 4: calls GET /api/v1/alerts
 */
export async function fetchAlerts(date?: string): Promise<Alert[]> {
  const response = await api.get('/api/v1/alerts', {
    params: { page_size: 500, date },
  });
  return response.data.data as Alert[];
}

