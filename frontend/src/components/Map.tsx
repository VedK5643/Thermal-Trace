import React, { useCallback, useMemo, useState, useRef, useEffect } from 'react';
import ReactMapGL, {
  Source,
  Layer,
  MapRef,
} from 'react-map-gl/maplibre';
import type { MapLayerMouseEvent } from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import { ChevronDown, Layers, Check, Globe } from 'lucide-react';
import { useHotspotsQuery } from '../services/queries/useHotspotsQuery';
import { useFacilitiesQuery } from '../services/queries/useFacilitiesQuery';
import { useFirmsStatusQuery } from '../services/queries/useFirmsStatusQuery';
import { useMapStore } from '../store/mapStore';
import {
  hotspotsToGeoJSON,
  facilitiesToGeoJSON,
  filterHotspots,
  filterFacilities,
} from '../utils/geojson';
import { HOTSPOT_COLORS } from '../types/hotspot';
import { INDIA_VIEWPORT } from '../types/map';
import {
  MAP_STYLES,
  buildMapStyleSpec,
  fetchSatelliteStyleSpec,
  getCachedSatelliteStyleSpec,
} from '../config/mapStyles';
import type { StyleSpecification } from 'maplibre-gl';
import type { GeoJSONFeatureCollection } from '../utils/geojson';

// Empty GeoJSON for initial/fallback state
const EMPTY_GEOJSON: GeoJSONFeatureCollection = {
  type: 'FeatureCollection',
  features: [],
};

interface MapComponentProps {
  mapRef: React.RefObject<MapRef>;
}

export default function Map({ mapRef }: MapComponentProps): React.JSX.Element {
  // Zustand selectors
  const selectedHotspotId = useMapStore((s) => s.selectedHotspotId);
  const selectedFacilityId = useMapStore((s) => s.selectedFacilityId);
  const activeHotspotTypes = useMapStore((s) => s.activeHotspotTypes);
  const activeFacilityTypes = useMapStore((s) => s.activeFacilityTypes);
  const minimumConfidence = useMapStore((s) => s.minimumConfidence);
  const selectedDate = useMapStore((s) => s.selectedDate);
  const showHeatmap = useMapStore((s) => s.showHeatmap);
  const showFacilities = useMapStore((s) => s.showFacilities);
  const showRiskZones = useMapStore((s) => s.showRiskZones);
  const selectHotspot = useMapStore((s) => s.selectHotspot);
  const selectFacility = useMapStore((s) => s.selectFacility);
  const mapStyleId = useMapStore((s) => s.mapStyle);
  const setMapStyle = useMapStore((s) => s.setMapStyle);

  // Basemap selector dropdown state
  const [isStyleDropdownOpen, setIsStyleDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Close dropdown on click outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsStyleDropdownOpen(false);
      }
    }
    if (isStyleDropdownOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isStyleDropdownOpen]);

  // TanStack Query data
  const { data: hotspots } = useHotspotsQuery(selectedDate, minimumConfidence);
  const { data: facilities } = useFacilitiesQuery();

  // Cached satellite style spec state
  const [satelliteSpec, setSatelliteSpec] = useState<StyleSpecification | null>(() =>
    getCachedSatelliteStyleSpec(),
  );

  useEffect(() => {
    fetchSatelliteStyleSpec().then((spec) => {
      setSatelliteSpec(spec);
    });
  }, []);

  // Active map style configuration object
  const activeStyleOption = useMemo(() => {
    return MAP_STYLES.find((s) => s.id === mapStyleId) || MAP_STYLES[0];
  }, [mapStyleId]);

  // Dynamic MapLibre style spec memoized by activeStyleOption & satelliteSpec
  const mapStyleSpec = useMemo(() => {
    if (mapStyleId === 'satellite') {
      return satelliteSpec || buildMapStyleSpec(activeStyleOption);
    }
    return buildMapStyleSpec(activeStyleOption);
  }, [mapStyleId, activeStyleOption, satelliteSpec]);

  // Filtered Hotspots (memoized)
  const filteredHotspots = useMemo(() => {
    if (!hotspots) return [];
    return filterHotspots(hotspots, activeHotspotTypes);
  }, [hotspots, activeHotspotTypes]);

  // Filtered Facilities (memoized)
  const filteredFacilities = useMemo(() => {
    if (!facilities) return [];
    return filterFacilities(facilities, activeFacilityTypes);
  }, [facilities, activeFacilityTypes]);

  const hotspotsGeoJSON = useMemo(
    () => (filteredHotspots.length > 0 ? hotspotsToGeoJSON(filteredHotspots) : EMPTY_GEOJSON),
    [filteredHotspots],
  );

  const facilitiesGeoJSON = useMemo(
    () => (filteredFacilities.length > 0 ? facilitiesToGeoJSON(filteredFacilities) : EMPTY_GEOJSON),
    [filteredFacilities],
  );

  const { data: firmsStatus } = useFirmsStatusQuery();

  // FIRMS Sync Freshness formatting derived from backend lastSyncSuccessAt
  const syncFreshnessDisplay = useMemo(() => {
    if (!firmsStatus?.lastSyncSuccessAt) return 'No sync data';
    const diffMs = Date.now() - new Date(firmsStatus.lastSyncSuccessAt).getTime();
    if (diffMs < 0 || isNaN(diffMs)) return 'Just now';
    const diffM = Math.floor(diffMs / 60000);
    const diffH = Math.floor(diffMs / 3600000);

    if (diffM < 2) return 'Just now';
    if (diffM < 60) return `${diffM}m ago`;
    if (diffH < 24) return `${diffH}h ago`;
    return `${Math.floor(diffH / 24)}d ago`;
  }, [firmsStatus?.lastSyncSuccessAt]);

  // Selected hotspot GeoJSON for highlight
  const selectedHotspotGeoJSON = useMemo(() => {
    if (!selectedHotspotId) return EMPTY_GEOJSON;
    const selected = (hotspots || []).filter((h) => h.id === selectedHotspotId);
    return selected.length > 0 ? hotspotsToGeoJSON(selected) : EMPTY_GEOJSON;
  }, [selectedHotspotId, hotspots]);

  // Selected facility GeoJSON for highlight
  const selectedFacilityGeoJSON = useMemo(() => {
    if (!selectedFacilityId) return EMPTY_GEOJSON;
    const selected = (facilities || []).filter((f) => f.id === selectedFacilityId);
    return selected.length > 0 ? facilitiesToGeoJSON(selected) : EMPTY_GEOJSON;
  }, [selectedFacilityId, facilities]);

  // Click handlers
  const handleMapClick = useCallback(
    (event: MapLayerMouseEvent) => {
      const features = event.features;
      if (!features || features.length === 0) {
        selectHotspot(null);
        selectFacility(null);
        return;
      }

      const feature = features[0];
      if (
        feature.layer?.id === 'hotspot-points' ||
        feature.layer?.id === 'hotspot-points-selected'
      ) {
        const id = feature.properties?.id as string;
        if (id) selectHotspot(id);
      } else if (feature.layer?.id === 'facility-points') {
        const id = feature.properties?.id as string;
        if (id) selectFacility(id);
      }
    },
    [selectHotspot, selectFacility],
  );

  // Fly to selected feature (hotspot or facility)
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    if (selectedHotspotId) {
      const selected = (hotspots || []).find((h) => h.id === selectedHotspotId)
        || filteredHotspots.find((h) => h.id === selectedHotspotId);
      if (selected) {
        map.flyTo({
          center: [selected.longitude, selected.latitude],
          zoom: 13.5,
          duration: 1200,
          essential: true,
        });
      }
    } else if (selectedFacilityId) {
      const selected = (facilities || []).find((f) => f.id === selectedFacilityId)
        || filteredFacilities.find((f) => f.id === selectedFacilityId);
      if (selected) {
        map.flyTo({
          center: [selected.longitude, selected.latitude],
          zoom: 13.5,
          duration: 1200,
          essential: true,
        });
      }
    }
  }, [selectedHotspotId, selectedFacilityId, filteredHotspots, filteredFacilities, hotspots, facilities]);

  // Cursor management
  const handleMouseEnter = useCallback(() => {
    const map = mapRef.current?.getMap();
    if (map) map.getCanvas().style.cursor = 'pointer';
  }, [mapRef]);

  const handleMouseLeave = useCallback(() => {
    const map = mapRef.current?.getMap();
    if (map) map.getCanvas().style.cursor = '';
  }, [mapRef]);

  return (
    <div className="relative w-full h-full">
      {/* ─── COMPACT NASA FIRMS NRT STATUS CARD (Top-Left inside Map) ─── */}
      <div className="absolute top-3 left-24 md:left-3 z-20 rounded-xl px-2.5 py-1.5 sm:px-3 sm:py-2 flex items-center gap-2 sm:gap-2.5 select-none border border-[#1e293b] shadow-2xl backdrop-blur-md bg-[#0F1623]/90 text-[#E8EDF5]">
        <div className="w-6 h-6 sm:w-7 sm:h-7 rounded-full bg-[#0B3D91] flex items-center justify-center font-black text-[8px] sm:text-[9px] text-white tracking-tighter shrink-0 border border-white/20">
          NASA
        </div>
        <div className="space-y-0.5">
          <div className="flex items-center gap-1.5 sm:gap-2">
            <span className="text-[10px] sm:text-[11px] font-bold text-[#E8EDF5] tracking-wide">
              NASA FIRMS NRT
            </span>
            <span className={`inline-flex items-center gap-1 px-1.5 py-0.2 rounded text-[8px] sm:text-[9px] font-bold uppercase ${
              firmsStatus?.status === 'live'
                ? 'bg-emerald-950/60 text-emerald-400 border border-emerald-500/30'
                : firmsStatus?.status === 'delayed'
                ? 'bg-amber-950/60 text-amber-400 border border-amber-500/30'
                : firmsStatus?.status === 'degraded'
                ? 'bg-red-950/60 text-red-400 border border-red-500/30'
                : 'bg-orange-950/60 text-orange-400 border border-orange-500/30'
            }`}>
              <span className={`w-1.5 h-1.5 rounded-full ${
                firmsStatus?.status === 'live' ? 'bg-emerald-400 animate-pulse' : firmsStatus?.status === 'delayed' ? 'bg-amber-400' : 'bg-red-400'
              }`} />
              {firmsStatus?.status ? firmsStatus.status.toUpperCase() : 'LIVE'}
            </span>
          </div>
          <div className="text-[8.5px] sm:text-[9px] font-mono text-[#7A8FA8] flex items-center gap-1.5">
            <span className="hidden sm:inline">VIIRS SNPP • NOAA-20 • NOAA-21</span>
            <span className="hidden sm:inline">•</span>
            <span className="text-[#E8EDF5]">Synced {syncFreshnessDisplay}</span>
          </div>
        </div>
      </div>

      <ReactMapGL
        ref={mapRef}
        initialViewState={{
          longitude: INDIA_VIEWPORT.longitude,
          latitude: INDIA_VIEWPORT.latitude,
          zoom: INDIA_VIEWPORT.zoom,
        }}
        mapStyle={mapStyleSpec}
        onClick={handleMapClick}
        interactiveLayerIds={['hotspot-points', 'facility-points']}
        onMouseEnter={handleMouseEnter}
        onMouseLeave={handleMouseLeave}
        attributionControl={false}
        reuseMaps
      >
        {/* ---- RISK ZONES LAYER ---- */}
        {showRiskZones && (
          <Source
            id="hotspots-risk-zones"
            type="geojson"
            data={hotspotsGeoJSON}
          >
            <Layer
              id="hotspot-risk-zone-fill"
              type="circle"
              paint={{
                'circle-radius': [
                  'interpolate',
                  ['linear'],
                  ['zoom'],
                  4, 12,
                  8, 22,
                  12, 38,
                  15, 55,
                ],
                'circle-color': 'rgba(239, 68, 68, 0.08)',
                'circle-stroke-width': 1.5,
                'circle-stroke-color': 'rgba(239, 68, 68, 0.45)',
              }}
            />
          </Source>
        )}

        {/* ---- HEATMAP LAYER ---- */}
        {showHeatmap && (
          <Source
            id="hotspots-heat"
            type="geojson"
            data={hotspotsGeoJSON}
          >
            <Layer
              id="hotspot-heatmap"
              type="heatmap"
              paint={{
                'heatmap-weight': [
                  'interpolate',
                  ['linear'],
                  ['get', 'heatWeight'],
                  0, 0.1,
                  0.4, 0.6,
                  1.0, 1.8,
                ],
                'heatmap-intensity': [
                  'interpolate',
                  ['linear'],
                  ['zoom'],
                  4, 0.6,
                  8, 1.6,
                  11, 3.2,
                  14, 5.5,
                ],
                'heatmap-radius': [
                  'interpolate',
                  ['linear'],
                  ['zoom'],
                  4, 16,
                  8, 24,
                  11, 32,
                  14, 38,
                ],
                'heatmap-opacity': [
                  'interpolate',
                  ['linear'],
                  ['zoom'],
                  4, 0.75,
                  9, 0.65,
                  14, 0.5,
                ],
                'heatmap-color': [
                  'interpolate',
                  ['linear'],
                  ['heatmap-density'],
                  0, 'rgba(0,0,0,0)',
                  0.04, 'rgba(255,235,59,0.25)', // Soft outer yellow fringe
                  0.18, '#FFC107',               // Bright Amber / Yellow
                  0.38, '#FF9800',               // Warm Orange
                  0.58, '#F4511E',               // Red-Orange
                  0.78, '#E53935',               // Vibrant Red
                  1.00, '#B71C1C',               // Deep Dark Red Core
                ],
              }}
            />
          </Source>
        )}

        {/* ---- HOTSPOT POINT LAYER ---- */}
        <Source
          id="hotspots-points"
          type="geojson"
          data={hotspotsGeoJSON}
        >
          <Layer
            id="hotspot-points-glow"
            type="circle"
            paint={{
              'circle-radius': [
                'interpolate',
                ['linear'],
                ['zoom'],
                5, 6,
                10, 9,
                15, 14,
              ],
              'circle-color': [
                'match',
                ['coalesce', ['get', 'mlType'], ['get', 'type']],
                'industrial_thermal_source', HOTSPOT_COLORS.industrial_thermal_source,
                'mining_thermal_source', HOTSPOT_COLORS.mining_thermal_source,
                'natural_fire', HOTSPOT_COLORS.natural_fire,
                'unknown', HOTSPOT_COLORS.unknown,
                HOTSPOT_COLORS.unknown,
              ],
              'circle-opacity': 0.25,
              'circle-blur': 0.8,
            }}
          />
          <Layer
            id="hotspot-points"
            type="circle"
            paint={{
              'circle-radius': [
                'interpolate',
                ['linear'],
                ['zoom'],
                5, 3.5,
                10, 5.5,
                15, 8,
              ],
              'circle-color': [
                'match',
                ['coalesce', ['get', 'mlType'], ['get', 'type']],
                'industrial_thermal_source', HOTSPOT_COLORS.industrial_thermal_source,
                'mining_thermal_source', HOTSPOT_COLORS.mining_thermal_source,
                'natural_fire', HOTSPOT_COLORS.natural_fire,
                'unknown', HOTSPOT_COLORS.unknown,
                HOTSPOT_COLORS.unknown,
              ],
              'circle-stroke-width': 1.5,
              'circle-stroke-color': '#080C14',
              'circle-opacity': 0.9,
            }}
          />
        </Source>

        {/* ---- FACILITY LAYER ---- */}
        {showFacilities && (
          <Source
            id="facilities-points"
            type="geojson"
            data={facilitiesGeoJSON}
          >
            <Layer
              id="facility-points"
              type="circle"
              paint={{
                'circle-radius': [
                  'interpolate',
                  ['linear'],
                  ['zoom'],
                  5, 4,
                  10, 6,
                  15, 9,
                ],
                'circle-color': '#2D7DD2',
                'circle-stroke-width': 2,
                'circle-stroke-color': '#E8EDF5',
                'circle-opacity': 0.85,
              }}
            />
          </Source>
        )}

        {/* ---- SELECTED HOTSPOT HIGHLIGHT ---- */}
        <Source
          id="selected-hotspot"
          type="geojson"
          data={selectedHotspotGeoJSON}
        >
          <Layer
            id="hotspot-selected-glow"
            type="circle"
            paint={{
              'circle-radius': 18,
              'circle-color': '#FF4444',
              'circle-opacity': 0.2,
              'circle-blur': 0.6,
            }}
          />
          <Layer
            id="hotspot-points-selected"
            type="circle"
            paint={{
              'circle-radius': 8,
              'circle-color': '#FF4444',
              'circle-stroke-width': 2.5,
              'circle-stroke-color': '#E8EDF5',
              'circle-opacity': 1,
            }}
          />
        </Source>

        {/* ---- SELECTED FACILITY HIGHLIGHT ---- */}
        <Source
          id="selected-facility"
          type="geojson"
          data={selectedFacilityGeoJSON}
        >
          <Layer
            id="facility-selected-glow"
            type="circle"
            paint={{
              'circle-radius': 18,
              'circle-color': '#2D7DD2',
              'circle-opacity': 0.25,
              'circle-blur': 0.5,
            }}
          />
          <Layer
            id="facility-selected-point"
            type="circle"
            paint={{
              'circle-radius': 7,
              'circle-color': '#2D7DD2',
              'circle-stroke-width': 2.5,
              'circle-stroke-color': '#E8EDF5',
              'circle-opacity': 1,
            }}
          />
        </Source>
      </ReactMapGL>

      {/* Dynamic Basemap Selector Dropdown */}
      <div className="absolute top-3 right-3 z-20" ref={dropdownRef}>
        <div className="relative">
          <button
            type="button"
            onClick={() => setIsStyleDropdownOpen(!isStyleDropdownOpen)}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-semibold shadow-xl transition-all cursor-pointer border border-[#1e293b] bg-[#111827] text-[#E8EDF5] hover:bg-[#1E2D45]"
          >
            {activeStyleOption.id === 'satellite' ? (
              <Globe className="w-3.5 h-3.5 text-emerald-400" />
            ) : (
              <Layers className="w-3.5 h-3.5 text-[#2D7DD2]" />
            )}
            <span>{activeStyleOption.label}</span>
            <ChevronDown className="w-3 h-3 text-[#6B7280]" />
          </button>

          {/* Dropdown Options List */}
          {isStyleDropdownOpen && (
            <div
              className="absolute right-0 top-full mt-1.5 z-50 rounded-xl shadow-2xl overflow-hidden py-1 w-64 bg-[#111827] border border-[#1e293b]"
              style={{ boxShadow: '0 10px 30px rgba(0,0,0,0.9)' }}
            >
              <div className="px-3 py-1.5 border-b border-[#1e293b] text-[10px] font-bold text-[#6B7280] uppercase tracking-wider flex items-center justify-between">
                <span>BASEMAP THEMES</span>
                <span className="text-[9px] text-[#475569] font-normal">8 MODES</span>
              </div>
              <div className="py-1 max-h-80 overflow-y-auto custom-scrollbar">
                {MAP_STYLES.map((style) => {
                  const isSelected = style.id === mapStyleId;
                  return (
                    <button
                      key={style.id}
                      type="button"
                      onClick={() => {
                        setMapStyle(style.id);
                        setIsStyleDropdownOpen(false);
                      }}
                      className="w-full flex items-start justify-between px-3 py-2 text-left hover:bg-[#1E2D45] transition-colors cursor-pointer"
                      style={{
                        backgroundColor: isSelected ? 'rgba(45,125,210,0.15)' : 'transparent',
                      }}
                    >
                      <div>
                        <div
                          className="flex items-center gap-1.5 text-xs"
                          style={{
                            fontWeight: isSelected ? 700 : 500,
                            color: isSelected ? '#2D7DD2' : '#E8EDF5',
                          }}
                        >
                          {style.id === 'satellite' ? (
                            <Globe className="w-3 h-3 text-emerald-400 shrink-0" />
                          ) : (
                            <Layers className="w-3 h-3 text-[#2D7DD2] shrink-0" />
                          )}
                          <span>{style.label}</span>
                          <span className="text-[9px] px-1 py-0.2 rounded font-normal bg-[rgba(255,255,255,0.06)] text-[#94A3B8]">
                            {style.provider}
                          </span>
                        </div>
                        <div className="text-[10px] text-[#6B7280] mt-0.5 pl-4">
                          {style.description}
                        </div>
                      </div>
                      {isSelected && (
                        <Check className="w-3.5 h-3.5 text-[#2D7DD2] mt-0.5 shrink-0" />
                      )}
                    </button>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
