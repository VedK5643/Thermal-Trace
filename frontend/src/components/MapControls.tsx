import { Plus, Minus, RotateCcw, Navigation } from 'lucide-react';
import type { MapRef } from 'react-map-gl/maplibre';
import {
  DEFAULT_MAP_CENTER,
  DEFAULT_MAP_ZOOM,
  DEFAULT_MAP_BEARING,
  DEFAULT_MAP_PITCH,
} from '../types/map';

interface MapControlsProps {
  mapRef: React.RefObject<MapRef>;
}

export default function MapControls({ mapRef }: MapControlsProps): React.JSX.Element {
  const handleZoomIn = () => {
    const map = mapRef.current;
    if (map) map.zoomIn({ duration: 300 });
  };

  const handleZoomOut = () => {
    const map = mapRef.current;
    if (map) map.zoomOut({ duration: 300 });
  };

  const handleResetMap = () => {
    const map = mapRef.current;
    if (map) {
      map.flyTo({
        center: DEFAULT_MAP_CENTER,
        zoom: DEFAULT_MAP_ZOOM,
        bearing: DEFAULT_MAP_BEARING,
        pitch: DEFAULT_MAP_PITCH,
        duration: 1200,
      });
    }
  };

  const handleLocate = () => {
    const map = mapRef.current;
    if (map && 'geolocation' in navigator) {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          map.flyTo({
            center: [position.coords.longitude, position.coords.latitude],
            zoom: 12,
            duration: 1200,
          });
        },
        () => {
          handleResetMap();
        },
      );
    } else {
      handleResetMap();
    }
  };

  return (
    <div
      className="absolute left-3 bottom-3 z-20 flex flex-col overflow-hidden select-none rounded-xl"
      style={{
        backgroundColor: '#111827',
        border: '1px solid #1e293b',
        boxShadow: '0 8px 32px rgba(0,0,0,0.8)',
      }}
    >
      {/* Zoom In */}
      <button
        type="button"
        title="Zoom In"
        aria-label="Zoom In"
        onClick={handleZoomIn}
        className="w-9 h-9 flex items-center justify-center bg-[#111827] text-[#E8EDF5] hover:bg-[#1E2D45] transition-colors border-b border-[#1e293b] cursor-pointer"
      >
        <Plus className="w-4 h-4" />
      </button>

      {/* Zoom Out */}
      <button
        type="button"
        title="Zoom Out"
        aria-label="Zoom Out"
        onClick={handleZoomOut}
        className="w-9 h-9 flex items-center justify-center bg-[#111827] text-[#E8EDF5] hover:bg-[#1E2D45] transition-colors border-b border-[#1e293b] cursor-pointer"
      >
        <Minus className="w-4 h-4" />
      </button>

      {/* Reset Map */}
      <button
        type="button"
        title="Reset Map"
        aria-label="Reset Map"
        onClick={handleResetMap}
        className="w-9 h-9 flex items-center justify-center bg-[#111827] text-[#2D7DD2] hover:bg-[#1E2D45] transition-colors border-b border-[#1e293b] cursor-pointer"
      >
        <RotateCcw className="w-3.5 h-3.5" />
      </button>

      {/* Locate */}
      <button
        type="button"
        title="Locate"
        aria-label="Locate"
        onClick={handleLocate}
        className="w-9 h-9 flex items-center justify-center bg-[#111827] text-[#E8EDF5] hover:bg-[#1E2D45] transition-colors cursor-pointer"
      >
        <Navigation className="w-3.5 h-3.5" />
      </button>
    </div>
  );
}
