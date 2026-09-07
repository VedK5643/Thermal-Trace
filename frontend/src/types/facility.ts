// Raw type returned from backend
export type FacilityType = string;
export type NormalizedFacilityType = 'industrial' | 'quarry' | 'chimney' | 'power plant' | 'works' | string;

export interface Facility {
  id: string;
  name?: string;
  type: NormalizedFacilityType;
  rawType?: string;
  latitude: number;
  longitude: number;
  city?: string;
  state?: string;
  country?: string;
  source?: string;
  osm_type?: string;
  osm_id?: number;
  raw_tags?: Record<string, any>;
}

export function getFacilityIcon(type: NormalizedFacilityType): string {
  if (type === 'power plant') return '⚡';
  if (type === 'quarry') return '⛏️';
  if (type === 'chimney') return '🏭';
  if (type === 'works') return '🏗️';
  if (type === 'refinery') return '⚗️';
  if (type === 'steel plant') return '🏭';
  if (type === 'cement plant') return '🏗️';
  if (type === 'lng terminal') return '💧';
  if (type === 'industrial') return '🏭';
  return '🏭'; // fallback
}

export function formatFacilityLabel(type: NormalizedFacilityType): string {
  // e.g. "power plant" -> "Power Plant"
  return type
    .split(' ')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}
