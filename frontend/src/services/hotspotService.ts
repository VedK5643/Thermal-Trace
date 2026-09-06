import type { Hotspot } from '../types/hotspot';
import api from './api';

/**
 * Fetch hotspot data from FastAPI backend with canonical filters.
 */
export async function fetchHotspots(
  date?: string,
  minConfidence?: number,
  state?: string,
): Promise<Hotspot[]> {
  const params: Record<string, any> = { page_size: 2000 };
  if (date) {
    params.start_date = date;
    params.end_date = date;
  }
  if (minConfidence !== undefined) {
    params.min_confidence = minConfidence;
  }
  if (state) {
    params.state = state;
  }
  
  const response = await api.get('/api/v1/hotspots', { params });
  return response.data.data as Hotspot[];
}

export interface ActivityDay {
  date: string;
  total: number;
  uniqueSources: number;
  byType: Record<string, number>;
  byTypeUnique: Record<string, number>;
}

export interface ActivityResponse {
  days: ActivityDay[];
}

/**
 * Fetch 7-day hotspot activity aggregation from FastAPI backend.
 */
export async function fetchHotspotActivity(
  endDate: string,
  minConfidence?: number,
  state?: string,
): Promise<ActivityResponse> {
  const params: Record<string, any> = { end_date: endDate };
  if (minConfidence !== undefined) {
    params.min_confidence = minConfidence;
  }
  if (state) {
    params.state = state;
  }
  
  const response = await api.get('/api/v1/hotspots/activity', { params });
  return response.data as ActivityResponse;
}
