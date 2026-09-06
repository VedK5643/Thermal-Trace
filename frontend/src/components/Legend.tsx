import React, { useMemo } from 'react';
import { Info, RotateCcw, Check } from 'lucide-react';
import { useMapStore } from '../store/mapStore';
import { useHotspotsQuery } from '../services/queries/useHotspotsQuery';
import { useActivityQuery } from '../services/queries/useActivityQuery';
import { getTodayISTString, formatISTDateLabel } from '../utils/dateUtils';
import type { HotspotType } from '../types/hotspot';
import { HOTSPOT_COLORS, HOTSPOT_LABELS } from '../types/hotspot';
import type { FacilityType } from '../types/facility';
import { FACILITY_LABELS } from '../types/facility';

interface HotspotTypeItem {
  type: HotspotType;
  label: string;
  color: string;
}

interface FacilityTypeItem {
  type: FacilityType;
  label: string;
  icon: string;
}

export default function Legend(): React.JSX.Element {
  const activeHotspotTypes = useMapStore((s) => s.activeHotspotTypes);
  const toggleHotspotType = useMapStore((s) => s.toggleHotspotType);
  const selectedDate = useMapStore((s) => s.selectedDate);
  const activeFacilityTypes = useMapStore((s) => s.activeFacilityTypes);
  const toggleFacilityType = useMapStore((s) => s.toggleFacilityType);
  const minimumConfidence = useMapStore((s) => s.minimumConfidence);
  const setMinimumConfidence = useMapStore((s) => s.setMinimumConfidence);
  const resetFilters = useMapStore((s) => s.resetFilters);

  const { data: hotspots } = useHotspotsQuery(selectedDate, minimumConfidence);

  const todayIST = getTodayISTString();
  const { data: activityData } = useActivityQuery(todayIST, minimumConfidence);

  const activeDay = useMemo(() => {
    if (!activityData?.days) return null;
    return activityData.days.find((d) => d.date === selectedDate) || activityData.days[activityData.days.length - 1];
  }, [activityData, selectedDate]);

  // Category counts from real FIRMS data
  const counts = useMemo(() => {
    const counts = {
      industrial_thermal_source: 0,
      mining_thermal_source: 0,
      natural_fire: 0,
      unknown: 0,
    };

    if (hotspots) {
      hotspots.forEach((h) => {
        const type = (h.mlType || h.type) as HotspotType;
        if (counts[type as keyof typeof counts] !== undefined) counts[type as keyof typeof counts]++;
        else counts.unknown++;
      });
    }
    return counts;
  }, [hotspots]);

  const legendItems: HotspotTypeItem[] = [
    { type: 'industrial_thermal_source', label: HOTSPOT_LABELS.industrial_thermal_source, color: HOTSPOT_COLORS.industrial_thermal_source },
    { type: 'mining_thermal_source', label: HOTSPOT_LABELS.mining_thermal_source, color: HOTSPOT_COLORS.mining_thermal_source },
    { type: 'natural_fire', label: HOTSPOT_LABELS.natural_fire, color: HOTSPOT_COLORS.natural_fire },
    { type: 'unknown', label: HOTSPOT_LABELS.unknown, color: HOTSPOT_COLORS.unknown },
  ];

  const facilityTypes: FacilityTypeItem[] = [
    { type: 'refinery', label: FACILITY_LABELS.refinery, icon: '⚗️' },
    { type: 'power_plant', label: FACILITY_LABELS.power_plant, icon: '⚡' },
    { type: 'steel_plant', label: FACILITY_LABELS.steel_plant, icon: '🏭' },
    { type: 'cement_plant', label: FACILITY_LABELS.cement_plant, icon: '🏗️' },
    { type: 'lng_terminal', label: FACILITY_LABELS.lng_terminal, icon: '💧' },
  ];

  return (
    <aside className="w-full h-full flex flex-col bg-[#0D121F] overflow-hidden select-none border-r border-[#1e293b]">
      {/* Panel Header */}
      <div className="flex items-center justify-between px-3 py-2.5 border-b border-[#1e293b] shrink-0 bg-[#090D16]">
        <span className="text-[11px] font-bold tracking-widest text-[#E8EDF5] uppercase flex items-center gap-1.5">
          LEGEND & FILTERS
        </span>
        <div className="flex items-center gap-2">
          <button
            type="button"
            title="Reset Filters"
            onClick={resetFilters}
            className="text-[#6B7280] hover:text-[#2D7DD2] transition-colors p-1 rounded cursor-pointer"
          >
            <RotateCcw className="w-3 h-3" />
          </button>
          <span className="text-[9px] font-mono font-bold text-[#10B981] bg-[rgba(16,185,129,0.12)] border border-[rgba(16,185,129,0.3)] px-1.5 py-0.5 rounded flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-[#10B981] animate-ping" />
            LIVE
          </span>
        </div>
      </div>

      {/* Panel Body — Ultra-compact non-scrolling layout */}
      <div className="flex-1 flex flex-col justify-between p-3 space-y-2 overflow-hidden text-xs">
        {/* Section 1: Hotspot Type */}
        <div>
          <div className="flex items-center justify-between mb-1">
            <span className="text-[10px] font-bold text-[#6B7280] uppercase tracking-wider flex items-center gap-1">
              HOTSPOT TYPE <span className="text-[8px] text-[#2D7DD2] lowercase">(Observation Type)</span>
            </span>
          </div>
          <div className="space-y-1">
            {legendItems.map((item) => {
              const isActive = activeHotspotTypes.includes(item.type);
              const count = counts[item.type as keyof typeof counts] || 0;
              const hoverTip =
                item.type === 'industrial_thermal_source'
                  ? 'Includes industrial process heat, power plants, refineries & gas flares'
                  : item.type === 'mining_thermal_source'
                  ? 'Includes quarries, mineral extraction & overburden activity'
                  : item.type === 'natural_fire'
                  ? 'Encompasses agricultural stubble burning, wildfires & forest fires'
                  : 'Persistent heat anomalies > 2km from mapped industrial context';
              return (
                <button
                  key={item.type}
                  type="button"
                  title={hoverTip}
                  onClick={() => toggleHotspotType(item.type)}
                  className="flex items-center justify-between w-full px-2 py-1 rounded-md border transition-all cursor-pointer hover:bg-[#162032]"
                  style={{
                    backgroundColor: isActive ? 'rgba(30, 45, 69, 0.5)' : 'transparent',
                    borderColor: isActive ? '#1e293b' : 'transparent',
                    opacity: isActive ? 1 : 0.4,
                  }}
                >
                  <div className="flex items-center gap-2">
                    <span
                      className="w-2.5 h-2.5 rounded-full shrink-0 shadow-sm"
                      style={{ backgroundColor: item.color }}
                    />
                    <span className="text-[11px] text-[#E8EDF5] font-medium">
                      {item.label}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] font-mono text-[#8B9BB4]">{count}</span>
                    <div
                      className={`w-3.5 h-3.5 rounded-[3px] border flex items-center justify-center transition-all duration-200 shrink-0 ${
                        isActive
                          ? 'bg-[#2D7DD2] border-[#2D7DD2] shadow-sm shadow-[#2D7DD2]/40 ring-1 ring-[#2D7DD2]/30'
                          : 'bg-[#111827] border-[#374151] hover:border-[#6B7280]'
                      }`}
                    >
                      {isActive && <Check className="w-2.5 h-2.5 text-white stroke-[3]" />}
                    </div>
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        {/* Section 1.5: Problem Statement Category Coverage Mapping */}
        <div className="pt-1.5 border-t border-[#1e293b]/70">
          <details className="group">
            <summary className="text-[10px] font-bold text-[#38BDF8] hover:text-[#7DD3FC] cursor-pointer flex items-center justify-between tracking-wider uppercase select-none">
              <span className="flex items-center gap-1">
                <Info className="w-3 h-3 text-[#38BDF8]" />
                PS Category Coverage
              </span>
              <span className="text-[9px] text-[#64748B] group-open:rotate-180 transition-transform">▼</span>
            </summary>
            <div className="mt-1.5 p-2 bg-[#090D16] border border-[#1E293B] rounded-lg text-[9.5px] space-y-1 text-[#94A3B8]">
              <div className="flex justify-between items-center border-b border-[#1E293B] pb-1">
                <span className="text-[#E8EDF5] font-semibold">PS Category</span>
                <span className="text-[#38BDF8] font-mono text-[8.5px]">Model Class</span>
              </div>
              <div className="flex justify-between"><span className="text-[#E2E8F0]">Industrial Fires</span><span className="text-[#EF4444] font-mono">industrial</span></div>
              <div className="flex justify-between"><span className="text-[#E2E8F0]">Gas Flares</span><span className="text-[#EF4444] font-mono">industrial (grouped)</span></div>
              <div className="flex justify-between"><span className="text-[#E2E8F0]">Mining Activity</span><span className="text-[#F59E0B] font-mono">mining</span></div>
              <div className="flex justify-between"><span className="text-[#E2E8F0]">Agricultural Burning</span><span className="text-[#10B981] font-mono">natural_fire (grouped)</span></div>
              <div className="flex justify-between"><span className="text-[#E2E8F0]">Wildfire / Forest Fire</span><span className="text-[#10B981] font-mono">natural_fire (grouped)</span></div>
              <div className="flex justify-between"><span className="text-[#E2E8F0]">Other Natural Fires</span><span className="text-[#10B981] font-mono">natural_fire (grouped)</span></div>
            </div>
          </details>
        </div>

        {/* Section 2: Heat Intensity */}
        <div className="pt-1.5 border-t border-[#1e293b]/70">
          <div className="flex items-center justify-between mb-1">
            <span className="text-[10px] font-bold text-[#6B7280] uppercase tracking-wider">
              HEAT INTENSITY
            </span>
          </div>
          <div className="space-y-0.5">
            <div
              className="w-full h-1.5 rounded-full"
              style={{
                background: 'linear-gradient(to right, #3B82F6, #F59E0B, #F97316, #DC2626)',
              }}
            />
            <div className="flex justify-between text-[9px] text-[#6B7280] font-mono">
              <span>Low</span>
              <span>Medium</span>
              <span>High</span>
            </div>
          </div>
        </div>

        {/* Section 3: Confidence */}
        <div className="pt-1.5 border-t border-[#1e293b]/70">
          <div className="flex items-center justify-between mb-1">
            <span className="text-[10px] font-bold text-[#6B7280] uppercase tracking-wider flex items-center gap-1">
              CONFIDENCE <Info className="w-3 h-3 text-[#6B7280]" />
            </span>
            <span className="font-mono text-[10px] font-bold text-[#2D7DD2] bg-[#162033] px-1.5 py-0.5 rounded">
              ≥ {minimumConfidence}%
            </span>
          </div>
          <input
            type="range"
            min="0"
            max="100"
            step="5"
            value={minimumConfidence}
            onChange={(e) => setMinimumConfidence(Number(e.target.value))}
            className="w-full cursor-pointer accent-[#2D7DD2]"
            style={{ height: 4, background: '#1e293b', borderRadius: 4 }}
          />
        </div>

        {/* Section 4: Facility Type */}
        <div className="pt-1.5 border-t border-[#1e293b]/70">
          <div className="flex items-center justify-between mb-1">
            <span className="text-[10px] font-bold text-[#6B7280] uppercase tracking-wider">
              FACILITY TYPE
            </span>
          </div>
          <div className="space-y-0.5">
            {facilityTypes.map((item) => {
              const isActive = activeFacilityTypes.includes(item.type);
              return (
                <button
                  key={item.type}
                  type="button"
                  onClick={() => toggleFacilityType(item.type)}
                  className="flex items-center justify-between w-full px-2 py-0.5 text-left text-[11px] text-[#9CA3AF] rounded hover:bg-[#162032] transition-colors cursor-pointer"
                  style={{ opacity: isActive ? 1 : 0.4 }}
                >
                  <div className="flex items-center gap-2">
                    <span className="text-[11px]">{item.icon}</span>
                    <span className={isActive ? 'text-[#E8EDF5] font-medium' : 'text-[#6B7280]'}>
                      {item.label}
                    </span>
                  </div>
                  <div
                    className={`w-3.5 h-3.5 rounded-[3px] border flex items-center justify-center transition-all duration-200 shrink-0 ${
                      isActive
                        ? 'bg-[#2D7DD2] border-[#2D7DD2] shadow-sm shadow-[#2D7DD2]/40 ring-1 ring-[#2D7DD2]/30'
                        : 'bg-[#111827] border-[#374151] hover:border-[#6B7280]'
                    }`}
                  >
                    {isActive && <Check className="w-2.5 h-2.5 text-white stroke-[3]" />}
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        {/* Section 5: Daily Detection Metrics (Non-scrolling & Vibrant) */}
        <div className="pt-1.5 border-t border-[#1e293b]/80">
          <div className="flex items-center justify-between mb-1">
            <span className="text-[10px] font-bold text-[#6B7280] uppercase tracking-wider flex items-center gap-1">
              DAILY DETECTION METRICS
            </span>
            <span className="text-[9px] font-mono font-bold text-[#38BDF8] bg-[#0284C7]/15 border border-[#0284C7]/30 px-1.5 py-0.5 rounded-full">
              {formatISTDateLabel(selectedDate, false)}
            </span>
          </div>

          <div className="bg-gradient-to-br from-[#090D16] via-[#0F172A] to-[#090D16] border border-[#1E293B] rounded-lg p-2 space-y-1.5 shadow-inner">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-[#EF4444] shadow-sm shadow-[#EF4444]/50 animate-pulse" />
                <span className="text-[10px] text-[#94A3B8] font-medium">FIRMS Detections</span>
              </div>
              <span className="text-[11px] font-mono font-bold text-[#FF5555]">
                {activeDay?.total?.toLocaleString() ?? 0}
              </span>
            </div>

            <div className="flex items-center justify-between pt-1 border-t border-[#1E293B]/80">
              <div className="flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-white shadow-sm shadow-white/50" />
                <span className="text-[10px] text-[#94A3B8] font-medium">Unique Thermal Sources</span>
              </div>
              <span className="text-[11px] font-mono font-bold text-white">
                {activeDay?.uniqueSources?.toLocaleString() ?? 0}
              </span>
            </div>
          </div>

          <p className="mt-1 text-[8.5px] text-[#64748B] italic leading-tight">
            Raw FIRMS satellite detections are spatially grouped into unique thermal sources prior to AI classification.
          </p>
        </div>
      </div>
    </aside>
  );
}
