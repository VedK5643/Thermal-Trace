import type { Facility } from '../types/facility';
import { normalizeFacilityType } from '../types/facility';
import api from './api';

/**
 * Fetch facility data from FastAPI backend.
 * Phase 4: calls GET /api/v1/facilities
 */
export async function fetchFacilities(): Promise<Facility[]> {
  const response = await api.get('/api/v1/facilities', {
    params: { page_size: 500 },
  });
  
  // Normalize types from the backend so that frontend filters have a stable target
  return response.data.data.map((f: any) => ({
    ...f,
    rawType: f.type,
    type: normalizeFacilityType(f.type)
  })) as Facility[];
}

