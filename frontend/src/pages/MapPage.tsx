import React, { useRef, useState, useEffect } from 'react';
import type { MapRef } from 'react-map-gl/maplibre';
import Navbar from '../components/Navbar';
import Map from '../components/Map';
import MapControls from '../components/MapControls';
import Legend from '../components/Legend';
import RightPanel from '../components/RightPanel';
import BottomAnalytics from '../components/BottomAnalytics';
import { AlertCircle, ArrowRight, SlidersHorizontal, Info, X } from 'lucide-react';
import { useMapStore } from '../store/mapStore';

export default function MapPage(): React.JSX.Element {
  const mapRef = useRef<MapRef>(null!);
  const fetchAndSetLatestDate = useMapStore((s) => s.fetchAndSetLatestDate);
  const selectedHotspotId = useMapStore((s) => s.selectedHotspotId);
  const selectedFacilityId = useMapStore((s) => s.selectedFacilityId);

  const [isMobileLegendOpen, setIsMobileLegendOpen] = useState(false);
  const [isMobilePanelOpen, setIsMobilePanelOpen] = useState(false);

  useEffect(() => {
    fetchAndSetLatestDate();
  }, [fetchAndSetLatestDate]);

  // Automatically open mobile panel drawer when a hotspot or facility is selected on mobile/tablet
  useEffect(() => {
    if (selectedHotspotId || selectedFacilityId) {
      if (window.innerWidth < 1024) {
        setIsMobilePanelOpen(true);
      }
    }
  }, [selectedHotspotId, selectedFacilityId]);

  return (
    <div className="flex flex-col h-screen w-screen overflow-hidden bg-[#080C14] text-[#E8EDF5] select-none">
      {/* 1. NAVBAR (Fixed Height ~48px) */}
      <Navbar />

      {/* 2. THREE-COLUMN DASHBOARD LAYOUT */}
      <main className="flex-1 min-h-0 flex w-full overflow-hidden relative">
        {/* LEFT COLUMN: Legend & Filters (FULL HEIGHT ON DESKTOP) */}
        <div className="hidden md:block w-[260px] lg:w-[280px] shrink-0 h-full overflow-hidden border-r border-[#1e293b] bg-[#0D121F]">
          <Legend />
        </div>

        {/* CENTER COLUMN: Split Vertically (Alert banner + Map on top, Past Activity below) */}
        <div className="flex-1 min-w-0 h-full flex flex-col overflow-hidden bg-[#080C14] relative">
          {/* SYSTEM ALERT NOTIFICATION BAR (Contained to Map Width Only) */}
          <div className="bg-[rgba(220,38,38,0.12)] border-b border-[rgba(220,38,38,0.3)] px-3 sm:px-4 py-1 flex items-center justify-between text-xs shrink-0 h-7">
            <div className="flex items-center gap-2 text-[11px] truncate">
              <span className="flex items-center gap-1 font-bold text-[#FF4444] shrink-0">
                <AlertCircle className="w-3.5 h-3.5" />
                Active Alerts
              </span>
              <span className="text-[#6B7280]">|</span>
              <span className="text-[#E8EDF5] truncate">
                Near-real-time thermal anomaly monitoring — India
              </span>
              <span className="hidden sm:inline text-[#6B7280] font-mono text-[9px]">NRT</span>
            </div>
            <a
              href="/incidents"
              className="text-[10px] font-semibold text-[#2D7DD2] hover:underline flex items-center gap-0.5 shrink-0"
            >
              <span>View All</span>
              <ArrowRight className="w-3 h-3" />
            </a>
          </div>

          {/* Top: Map Area (flex-1) */}
          <div className="flex-1 min-h-0 w-full relative overflow-hidden bg-[#080C14]">
            <Map mapRef={mapRef} />
            <MapControls mapRef={mapRef} />

            {/* Mobile/Tablet Quick Drawer Trigger Buttons */}
            <div className="absolute top-3 left-3 z-30 flex items-center gap-2 md:hidden">
              <button
                type="button"
                onClick={() => setIsMobileLegendOpen(true)}
                className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-semibold bg-[#111827]/90 border border-[#1e293b] text-[#E8EDF5] shadow-lg backdrop-blur-md hover:bg-[#1E2D45] transition-colors"
                title="Open Legend & Filters"
              >
                <SlidersHorizontal className="w-3.5 h-3.5 text-[#2D7DD2]" />
                <span>Filters</span>
              </button>
            </div>

            <div className="absolute top-3 right-24 z-30 flex items-center gap-2 lg:hidden">
              <button
                type="button"
                onClick={() => setIsMobilePanelOpen(true)}
                className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-semibold bg-[#111827]/90 border border-[#1e293b] text-[#E8EDF5] shadow-lg backdrop-blur-md hover:bg-[#1E2D45] transition-colors"
                title="Open Intelligence Panel"
              >
                <Info className="w-3.5 h-3.5 text-[#2D7DD2]" />
                <span className="hidden sm:inline">Intelligence</span>
              </button>
            </div>
          </div>

          {/* Bottom: Past Activity Dashboard (Center-Only Width, aligned with Map) */}
          <div className="h-[150px] sm:h-[160px] lg:h-[175px] shrink-0 w-full border-t border-[#1e293b] overflow-hidden bg-[#080C14]">
            <BottomAnalytics />
          </div>
        </div>

        {/* RIGHT COLUMN: Intelligence Panel (FULL HEIGHT ON DESKTOP) */}
        <div className="hidden lg:block w-[320px] lg:w-[340px] shrink-0 h-full overflow-hidden border-l border-[#1e293b] bg-[#0D121F]">
          <RightPanel />
        </div>
      </main>

      {/* MOBILE LEGEND DRAWER OVERLAY (< 768px) */}
      {isMobileLegendOpen && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex justify-start md:hidden">
          <div className="w-[280px] h-full bg-[#0D121F] border-r border-[#1e293b] flex flex-col relative shadow-2xl animate-in slide-in-from-left duration-200">
            <div className="p-2 border-b border-[#1e293b] flex justify-end bg-[#090D16]">
              <button
                onClick={() => setIsMobileLegendOpen(false)}
                className="p-1 text-[#6B7280] hover:text-white rounded-md bg-[#162033]"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
            <div className="flex-1 overflow-hidden">
              <Legend />
            </div>
          </div>
        </div>
      )}

      {/* MOBILE RIGHT PANEL DRAWER OVERLAY (< 1024px) */}
      {isMobilePanelOpen && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex justify-end lg:hidden">
          <div className="w-[320px] max-w-[calc(100vw-2rem)] h-full bg-[#0D121F] border-l border-[#1e293b] flex flex-col relative shadow-2xl animate-in slide-in-from-right duration-200">
            <div className="p-2 border-b border-[#1e293b] flex justify-end bg-[#090D16]">
              <button
                onClick={() => setIsMobilePanelOpen(false)}
                className="p-1 text-[#6B7280] hover:text-white rounded-md bg-[#162033]"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
            <div className="flex-1 overflow-hidden">
              <RightPanel />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
