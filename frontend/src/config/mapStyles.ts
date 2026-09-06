import type { StyleSpecification, LayerSpecification } from 'maplibre-gl';

export type MapStyleId =
  | 'satellite'
  | 'positron'
  | 'bright'
  | 'liberty'
  | 'dark'
  | 'fiord'
  | '3d'
  | 'terrain';

export interface MapStyleConfig {
  id: MapStyleId;
  name: string;
  label: string;
  styleUrl?: string;
  tileUrl?: string;
  tiles?: string[];
  provider: string;
  requiresApiKey: boolean;
  attribution: string;
  type: 'vector' | 'raster';
  description: string;
}

export const DEFAULT_MAP_STYLE_ID: MapStyleId = 'satellite';

export const MAP_STYLES: MapStyleConfig[] = [
  {
    id: 'satellite',
    name: 'Satellite',
    label: 'Satellite / Earth',
    tileUrl: 'https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
    tiles: [
      'https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
      'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
    ],
    provider: 'Esri World Imagery',
    requiresApiKey: false,
    attribution:
      'Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community | &copy; <a href="https://openfreemap.org">OpenFreeMap</a>',
    type: 'raster',
    description: 'High-resolution satellite & Earth imagery with OpenFreeMap labels',
  },
  {
    id: 'positron',
    name: 'Positron',
    label: 'OpenFreeMap Positron',
    styleUrl: 'https://tiles.openfreemap.org/styles/positron',
    provider: 'OpenFreeMap',
    requiresApiKey: false,
    attribution:
      '&copy; <a href="https://openfreemap.org">OpenFreeMap</a>, &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    type: 'vector',
    description: 'Minimal light vector theme optimized for analytical heatmaps',
  },
  {
    id: 'bright',
    name: 'Bright',
    label: 'OpenFreeMap Bright',
    styleUrl: 'https://tiles.openfreemap.org/styles/bright',
    provider: 'OpenFreeMap',
    requiresApiKey: false,
    attribution:
      '&copy; <a href="https://openfreemap.org">OpenFreeMap</a>, &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    type: 'vector',
    description: 'Clean modern light vector theme with clear geography',
  },
  {
    id: 'liberty',
    name: 'Liberty',
    label: 'OpenFreeMap Liberty',
    styleUrl: 'https://tiles.openfreemap.org/styles/liberty',
    provider: 'OpenFreeMap',
    requiresApiKey: false,
    attribution:
      '&copy; <a href="https://openfreemap.org">OpenFreeMap</a>, &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    type: 'vector',
    description: 'Detailed geographic vector map with rich feature labels',
  },
  {
    id: 'dark',
    name: 'Dark',
    label: 'OpenFreeMap Dark',
    styleUrl: 'https://tiles.openfreemap.org/styles/dark',
    provider: 'OpenFreeMap',
    requiresApiKey: false,
    attribution:
      '&copy; <a href="https://openfreemap.org">OpenFreeMap</a>, &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    type: 'vector',
    description: 'Primary dark vector theme with high thermal contrast',
  },
  {
    id: 'fiord',
    name: 'Fiord',
    label: 'OpenFreeMap Fiord',
    styleUrl: 'https://tiles.openfreemap.org/styles/fiord',
    provider: 'OpenFreeMap',
    requiresApiKey: false,
    attribution:
      '&copy; <a href="https://openfreemap.org">OpenFreeMap</a>, &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    type: 'vector',
    description: 'Cool blue-gray vector theme for high visual focus',
  },
  {
    id: '3d',
    name: '3D',
    label: 'OpenFreeMap 3D',
    styleUrl: 'https://tiles.openfreemap.org/styles/3d',
    provider: 'OpenFreeMap',
    requiresApiKey: false,
    attribution:
      '&copy; <a href="https://openfreemap.org">OpenFreeMap</a>, &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    type: 'vector',
    description: 'Vector basemap with 3D terrain & building height extruded layers',
  },
  {
    id: 'terrain',
    name: 'Terrain',
    label: 'OpenTopoMap Terrain',
    tileUrl: 'https://a.tile.opentopomap.org/{z}/{x}/{y}.png',
    tiles: [
      'https://a.tile.opentopomap.org/{z}/{x}/{y}.png',
      'https://b.tile.opentopomap.org/{z}/{x}/{y}.png',
      'https://c.tile.opentopomap.org/{z}/{x}/{y}.png',
    ],
    provider: 'OpenTopoMap',
    requiresApiKey: false,
    attribution:
      'Map data &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors, SRTM | Map style &copy; <a href="https://opentopomap.org">OpenTopoMap</a> (<a href="https://creativecommons.org/licenses/by-sa/3.0/">CC-BY-SA</a>)',
    type: 'raster',
    description: 'Topographic & terrain-oriented context',
  },
];

let cachedSatelliteStyleSpec: StyleSpecification | null = null;
let satelliteStylePromise: Promise<StyleSpecification> | null = null;

export function buildFallbackRasterSpec(config: MapStyleConfig): StyleSpecification {
  let tiles = config.tiles || [config.tileUrl!];
  const arcgisKey = (import.meta.env.VITE_ARCGIS_API_KEY || import.meta.env.VITE_ESRI_API_KEY) as string | undefined;

  if (config.id === 'satellite' && arcgisKey) {
    tiles = tiles.map((t) => (t.includes('?') ? `${t}&token=${arcgisKey}` : `${t}?token=${arcgisKey}`));
  }

  return {
    version: 8,
    name: config.name,
    sources: {
      'basemap-source': {
        type: 'raster',
        tiles: tiles,
        tileSize: 256,
        minzoom: 0,
        maxzoom: 19,
        attribution: config.attribution,
      },
    },
    layers: [
      {
        id: 'basemap-layer',
        type: 'raster',
        source: 'basemap-source',
        minzoom: 0,
        maxzoom: 19,
      },
    ],
  };
}

export async function fetchSatelliteStyleSpec(): Promise<StyleSpecification> {
  if (cachedSatelliteStyleSpec) {
    return cachedSatelliteStyleSpec;
  }
  if (satelliteStylePromise) {
    return satelliteStylePromise;
  }

  const satConfig = MAP_STYLES.find((s) => s.id === 'satellite') || MAP_STYLES[0];

  satelliteStylePromise = (async () => {
    try {
      const res = await fetch('https://tiles.openfreemap.org/styles/positron');
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const ofmStyle = await res.json();

      let tiles = satConfig.tiles || [satConfig.tileUrl!];
      const arcgisKey = (import.meta.env.VITE_ARCGIS_API_KEY || import.meta.env.VITE_ESRI_API_KEY) as string | undefined;
      if (arcgisKey) {
        tiles = tiles.map((t) => (t.includes('?') ? `${t}&token=${arcgisKey}` : `${t}?token=${arcgisKey}`));
      }

      // Filter OpenFreeMap vector layers to extract boundary lines and symbol text labels
      const vectorOverlayLayers: LayerSpecification[] = (ofmStyle.layers || [])
        .filter((l: any) => l.type === 'symbol' || l.id.startsWith('boundary_') || l.id.startsWith('highway_major'))
        .map((l: any) => {
          const layer = JSON.parse(JSON.stringify(l));
          if (layer.type === 'symbol' && layer.paint) {
            // White label text with dark halo for maximum legibility over satellite imagery
            layer.paint['text-color'] = '#FFFFFF';
            layer.paint['text-halo-color'] = '#000000';
            layer.paint['text-halo-width'] = 2;
            layer.paint['text-halo-blur'] = 1;
            if (layer.paint['icon-halo-color']) {
              layer.paint['icon-halo-color'] = '#000000';
              layer.paint['icon-halo-width'] = 1;
            }
          } else if (layer.id.startsWith('boundary_') && layer.paint) {
            // Subtle boundary lines over satellite imagery
            layer.paint['line-color'] = 'rgba(255, 255, 255, 0.7)';
          }
          return layer;
        });

      const satelliteStyleSpec: StyleSpecification = {
        version: 8,
        name: 'Satellite with Vector Labels',
        glyphs: ofmStyle.glyphs || 'https://tiles.openfreemap.org/fonts/{fontstack}/{range}.pbf',
        sprite: ofmStyle.sprite || 'https://tiles.openfreemap.org/sprites/ofm_f384/ofm',
        sources: {
          'basemap-source': {
            type: 'raster',
            tiles: tiles,
            tileSize: 256,
            minzoom: 0,
            maxzoom: 19,
            attribution: satConfig.attribution,
          },
          'openmaptiles': ofmStyle.sources?.openmaptiles || {
            type: 'vector',
            url: 'https://tiles.openfreemap.org/planet',
          },
        },
        layers: [
          {
            id: 'basemap-layer',
            type: 'raster',
            source: 'basemap-source',
            minzoom: 0,
            maxzoom: 19,
          },
          ...vectorOverlayLayers,
        ],
      };

      cachedSatelliteStyleSpec = satelliteStyleSpec;
      return satelliteStyleSpec;
    } catch (err) {
      console.warn('Could not fetch OpenFreeMap vector labels for Satellite basemap:', err);
      const fallback = buildFallbackRasterSpec(satConfig);
      cachedSatelliteStyleSpec = fallback;
      return fallback;
    }
  })();

  return satelliteStylePromise;
}

// Prefetch satellite style specification immediately on module load
fetchSatelliteStyleSpec().catch(() => {});

export function getCachedSatelliteStyleSpec(): StyleSpecification | null {
  return cachedSatelliteStyleSpec;
}

export function buildMapStyleSpec(config: MapStyleConfig): string | StyleSpecification {
  if (config.id === 'satellite') {
    return cachedSatelliteStyleSpec || buildFallbackRasterSpec(config);
  }
  if (config.type === 'vector' && config.styleUrl) {
    return config.styleUrl;
  }
  return buildFallbackRasterSpec(config);
}
