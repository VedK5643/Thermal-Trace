export type HotspotType =
  | 'industrial_thermal_source'
  | 'mining_thermal_source'
  | 'natural_fire'
  | 'unknown';

export type Severity = 'low' | 'medium' | 'high' | 'critical';

export type HotspotStatus = 'active' | 'resolved' | 'monitoring';



export interface Hotspot {
  id: string;
  latitude: number;
  longitude: number;
  type: HotspotType;  // Raw FIRMS telemetry type
  brightness: number;
  confidence: number; // NASA FIRMS confidence
  severity: Severity;
  timestamp: string;
  facilityId: string | null;
  status: HotspotStatus;
  // Phase 6 ML Prediction fields
  mlType?: HotspotType;
  mlConfidence?: number;
  modelVersion?: string;
  mlExplanation?: string | Record<string, number>;
  // ESA WorldCover 10m land-cover context
  landCoverClass?: number;
  landCoverName?: string;
}

export const HOTSPOT_COLORS: Record<HotspotType, string> = {
  industrial_thermal_source: '#FF4444',
  mining_thermal_source: '#FF8C00',
  natural_fire: '#3DB86B',
  unknown: '#4A5568',
};

export const HOTSPOT_LABELS: Record<HotspotType, string> = {
  industrial_thermal_source: 'Industrial Thermal Source',
  mining_thermal_source: 'Mining Thermal Source',
  natural_fire: 'Natural Fire',
  unknown: 'Unknown / Unclassified',
};
