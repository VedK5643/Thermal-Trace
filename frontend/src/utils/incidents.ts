import type { Hotspot } from '../types/hotspot';
import type { Facility } from '../types/facility';
import type { Incident } from '../types/incident';

export function deriveIncidents(
  hotspots: Hotspot[],
  facilities: Facility[]
): Incident[] {
  // Create a quick lookup map for facilities
  const facilityMap = new Map<string, Facility>();
  for (const f of facilities) {
    facilityMap.set(f.id, f);
  }

  return hotspots.map((h) => {
    const facilityName = h.facilityId
      ? facilityMap.get(h.facilityId)?.name || 'Unknown Facility'
      : 'Not identified';

    return {
      id: h.id, // Using hotspot ID as the incident ID for simplicity in frontend
      hotspotId: h.id,
      facilityId: h.facilityId,
      facilityName,
      type: h.type,
      mlType: h.mlType,
      latitude: h.latitude,
      longitude: h.longitude,
      brightness: h.brightness,
      confidence: h.confidence,
      severity: h.severity,
      timestamp: h.timestamp,
      status: h.status,
    };
  });
}
