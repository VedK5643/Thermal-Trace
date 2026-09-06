import type { Facility } from '../types/facility';
import api from './api';

/**
 * Fetch facility data from FastAPI backend.
 * Phase 4: calls GET /api/v1/facilities
 */
export async function fetchFacilities(): Promise<Facility[]> {
  const response = await api.get('/api/v1/facilities', {
    params: { page_size: 500 },
  });
  return response.data.data as Facility[];
}

