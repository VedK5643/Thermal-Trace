export type FacilityType =
  | 'refinery'
  | 'power_plant'
  | 'steel_plant'
  | 'cement_plant'
  | 'lng_terminal';

export interface Facility {
  id: string;
  name: string;
  type: FacilityType;
  latitude: number;
  longitude: number;
  city: string;
  state: string;
  country: string;
  source?: string;
}

export const FACILITY_LABELS: Record<FacilityType, string> = {
  refinery: 'Refinery',
  power_plant: 'Power Plant',
  steel_plant: 'Steel Plant',
  cement_plant: 'Cement Plant',
  lng_terminal: 'LNG Terminal',
};
