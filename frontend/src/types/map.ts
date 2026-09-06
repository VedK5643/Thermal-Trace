export interface MapViewport {
  longitude: number;
  latitude: number;
  zoom: number;
  bearing?: number;
  pitch?: number;
}

export const DEFAULT_MAP_CENTER: [number, number] = [78.9629, 22.5];
export const DEFAULT_MAP_ZOOM = 4.2;
export const DEFAULT_MAP_BEARING = 0;
export const DEFAULT_MAP_PITCH = 0;

export const INDIA_VIEWPORT: MapViewport = {
  longitude: DEFAULT_MAP_CENTER[0],
  latitude: DEFAULT_MAP_CENTER[1],
  zoom: DEFAULT_MAP_ZOOM,
  bearing: DEFAULT_MAP_BEARING,
  pitch: DEFAULT_MAP_PITCH,
};

