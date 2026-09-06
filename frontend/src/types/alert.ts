export type AlertSeverity = 'info' | 'warning' | 'critical';

export interface Alert {
  id: string;
  hotspotId?: string;
  facilityId?: string;
  severity: AlertSeverity;
  title: string;
  message: string;
  timestamp: string;
  acknowledged: boolean;
}
