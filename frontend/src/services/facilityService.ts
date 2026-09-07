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
  
  // Handle various potential backend response shapes
  let rawData: any[] = [];
  if (Array.isArray(response.data)) {
    rawData = response.data;
  } else if (response.data && Array.isArray(response.data.data)) {
    rawData = response.data.data;
  } else if (response.data && Array.isArray(response.data.items)) {
    rawData = response.data.items;
  }
  
  // The backend now guarantees canonical 'type' and preserves 'rawType'
  return rawData as Facility[];
}

