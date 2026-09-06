// Raw type returned from backend
export type RawFacilityType = string;

// Normalized type used for filtering and display
export type NormalizedFacilityType = string;

export interface Facility {
  id: string;
  name: string;
  type: NormalizedFacilityType;
  rawType: RawFacilityType; // Preserve the raw type
  latitude: number;
  longitude: number;
  city: string;
  state: string;
  country: string;
  source?: string;
}

/**
 * Normalizes raw OSM backend categories into a stable set of frontend display types.
 * Known raw categories from OSM data: "industrial", "quarry", "chimney", "power plant", "works", etc.
 */
export function normalizeFacilityType(rawType: string): NormalizedFacilityType {
  if (!rawType) return 'unknown';
  
  const lower = rawType.toLowerCase().trim();
  
  if (lower.includes('power')) return 'power plant';
  if (lower.includes('quarry')) return 'quarry';
  if (lower.includes('chimney')) return 'chimney';
  if (lower.includes('works')) return 'works';
  if (lower.includes('refinery')) return 'refinery';
  if (lower.includes('steel')) return 'steel plant';
  if (lower.includes('cement')) return 'cement plant';
  if (lower.includes('lng')) return 'lng terminal';
  if (lower.includes('industrial')) return 'industrial';
  
  return lower; // fallback for unmapped types
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
