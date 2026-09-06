import type { Hotspot, HotspotType } from '../types/hotspot';
import type { Facility, FacilityType } from '../types/facility';

export interface GeoJSONFeature {
  type: 'Feature';
  geometry: {
    type: 'Point';
    coordinates: [number, number]; // [longitude, latitude]
  };
  properties: Record<string, unknown>;
}

export interface GeoJSONFeatureCollection {
  type: 'FeatureCollection';
  features: GeoJSONFeature[];
}

/**
 * Convert Hotspot[] to GeoJSON FeatureCollection.
 * Coordinates are [longitude, latitude] per GeoJSON spec.
 */
export function hotspotsToGeoJSON(hotspots: Hotspot[]): GeoJSONFeatureCollection {
  return {
    type: 'FeatureCollection',
    features: hotspots.map((h) => {
      const effectiveType = h.mlType || h.type;
      return {
        type: 'Feature' as const,
        geometry: {
          type: 'Point' as const,
          coordinates: [h.longitude, h.latitude] as [number, number],
        },
        properties: {
          id: h.id,
          type: effectiveType,
          rawType: h.type,
          mlType: h.mlType || 'unknown',
          mlConfidence: h.mlConfidence ?? 0.0,
          modelVersion: h.modelVersion || 'xgboost-v1',
          mlExplanation: h.mlExplanation,
          brightness: h.brightness,
          confidence: h.confidence,
          severity: h.severity,
          timestamp: h.timestamp,
          facilityId: h.facilityId,
          status: h.status,
          // Normalized brightness for heatmap weight (0-1 range)
          normalizedBrightness: Math.min(1, Math.max(0, (h.brightness - 240) / (360 - 240))),
          // Combined weight using brightness and confidence
          heatWeight: Math.min(
            1,
            Math.max(
              0,
              ((h.brightness - 240) / (360 - 240)) * 0.7 +
                (h.confidence / 100) * 0.3,
            ),
          ),
        },
      };
    }),
  };
}

/**
 * Convert Facility[] to GeoJSON FeatureCollection.
 */
export function facilitiesToGeoJSON(facilities: Facility[]): GeoJSONFeatureCollection {
  return {
    type: 'FeatureCollection',
    features: facilities.map((f) => ({
      type: 'Feature' as const,
      geometry: {
        type: 'Point' as const,
        coordinates: [f.longitude, f.latitude] as [number, number],
      },
      properties: {
        id: f.id,
        name: f.name,
        type: f.type,
        city: f.city,
        state: f.state,
        country: f.country,
      },
    })),
  };
}

/**
 * Geographic boundary check for Indian landmass, islands (Andaman & Nicobar, Lakshadweep),
 * and Union Territories. Filters out points that fall outside India.
 */
export function isInsideIndia(lat: number, lon: number): boolean {
  // 1. Primary bounding box check for India & UTs (6.0°N to 37.1°N, 68.0°E to 97.4°E)
  if (lat < 6.0 || lat > 37.1 || lon < 68.0 || lon > 97.4) {
    return false;
  }
  // 2. Exclude Sri Lanka (south of 10.0°N and east of 79.5°E)
  if (lat < 10.0 && lon > 79.5) {
    return false;
  }
  // 3. Exclude Pakistan (west of Indian border)
  if (lon < 68.1) {
    return false;
  }
  if (lat < 24.0 && lon < 68.1) {
    return false;
  }
  if (lat >= 24.0 && lat < 28.0 && lon < 70.0) {
    return false;
  }
  if (lat >= 28.0 && lat < 30.5 && lon < 73.5) {
    return false;
  }
  if (lat >= 30.5 && lat < 32.5 && lon < 74.55) {
    return false;
  }
  if (lat >= 32.5 && lon < 73.8) {
    return false;
  }
  // 4. Exclude Nepal
  if (lat >= 27.3 && lat <= 30.5 && lon >= 80.0 && lon <= 88.2) {
    return false;
  }
  // 5. Exclude Bangladesh
  if (lat > 20.6 && lat < 26.6 && lon > 88.0 && lon < 92.6) {
    const isWb = lon <= 88.8 || lat <= 21.8;
    const isTripura = lat >= 22.8 && lat <= 24.6 && lon >= 91.1 && lon <= 92.4;
    const isMeghalaya = lat >= 25.0 && lat <= 26.1 && lon >= 89.8 && lon <= 92.8;
    const isAssam = lat >= 25.8;
    if (!(isWb || isTripura || isMeghalaya || isAssam)) {
      return false;
    }
  }
  // 6. Exclude Myanmar
  if (lon > 97.4) {
    return false;
  }
  if (lat < 22.0 && lon > 93.0) {
    const isAndamanNicobar = lat >= 6.5 && lat <= 14.0 && lon >= 92.0 && lon <= 94.5;
    if (!isAndamanNicobar) {
      return false;
    }
  }
  return true;
}

/**
 * Filter hotspots by effective ML classification type and India boundary.
 */
export function filterHotspots(
  hotspots: Hotspot[],
  activeTypes: HotspotType[],
): Hotspot[] {
  return hotspots.filter(
    (h) =>
      activeTypes.includes(h.mlType || h.type) &&
      isInsideIndia(h.latitude, h.longitude),
  );
}

/**
 * Filter facilities by facility type and India boundary.
 */
export function filterFacilities(
  facilities: Facility[],
  activeTypes: FacilityType[],
): Facility[] {
  return facilities.filter(
    (f) =>
      activeTypes.includes(f.type) &&
      isInsideIndia(f.latitude, f.longitude),
  );
}
