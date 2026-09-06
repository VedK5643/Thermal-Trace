import { HotspotType, Severity, HotspotStatus } from './hotspot';

export interface Incident {
  id: string; // usually hotspot id
  hotspotId: string;
  facilityId: string | null;
  facilityName: string | null;
  type: HotspotType;
  mlType?: HotspotType;
  latitude: number;
  longitude: number;
  brightness: number;
  confidence: number;
  severity: Severity;
  timestamp: string;
  status: HotspotStatus;
}
