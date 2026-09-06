import React, { useMemo } from 'react';
import { CalendarDays } from 'lucide-react';
import { useMapStore } from '../store/mapStore';
import { useActivityQuery } from '../services/queries/useActivityQuery';
import type { HotspotType } from '../types/hotspot';
import { HOTSPOT_COLORS, HOTSPOT_LABELS } from '../types/hotspot';

import { getTodayISTString, formatISTDateLabel } from '../utils/dateUtils';

interface DateItem {
  label: string;
  isoDate: string;
  isToday?: boolean;
  counts: Record<HotspotType, number>;
  countsUnique: Record<HotspotType, number>;
  total: number;
  uniqueSources: number;
}

export default function BottomAnalytics(): React.JSX.Element {
  const selectedDate = useMapStore((s) => s.selectedDate);
  const setSelectedDate = useMapStore((s) => s.setSelectedDate);
  const minimumConfidence = useMapStore((s) => s.minimumConfidence);
  const todayIST = getTodayISTString();

  // Always fetch 7-day activity sequence ending on Today IST for NRT monitoring
  const { data: activityData } = useActivityQuery(todayIST, minimumConfidence);

  // 7-day date items computed dynamically from backend aggregation
  const dates: DateItem[] = useMemo(() => {
    if (!activityData || !activityData.days) return [];

    return activityData.days.map((day) => {
      const label = formatISTDateLabel(day.date, false);
      const isToday = day.date === todayIST;
      
      const counts: Record<HotspotType, number> = {
        industrial_thermal_source: day.byType.industrialThermalSource || 0,
        mining_thermal_source: day.byType.miningThermalSource || 0,
        natural_fire: day.byType.naturalFire || 0,
        unknown: day.byType.unknown || 0,
      };

      const countsUnique: Record<HotspotType, number> = {
        industrial_thermal_source: day.byTypeUnique?.industrialThermalSource || 0,
        mining_thermal_source: day.byTypeUnique?.miningThermalSource || 0,
        natural_fire: day.byTypeUnique?.naturalFire || 0,
        unknown: day.byTypeUnique?.unknown || 0,
      };

      return {
        label,
        isoDate: day.date,
        isToday,
        counts,
        countsUnique,
        total: day.total,
        uniqueSources: day.uniqueSources || 0,
      };
    });
  }, [activityData, todayIST]);

  // Find max total count among all 7 days for relative height scaling
  const maxTotal = useMemo(() => {
    const totals = dates.map((d) =>
      d.counts.industrial_thermal_source + d.counts.mining_thermal_source + d.counts.natural_fire,
    );
    return Math.max(...totals, 10);
  }, [dates]);

  const categories: HotspotType[] = [
    'industrial_thermal_source',
    'mining_thermal_source',
    'natural_fire',
    'unknown',
  ];

  return (
    <footer className="w-full h-full bg-[#080C14] border-t border-[#1e293b] flex flex-col justify-between p-3 select-none overflow-hidden">
      {/* Header Row */}
      <div className="flex items-center justify-between shrink-0 mb-1 px-1">
        <div className="flex items-center gap-2">
          <CalendarDays className="w-3.5 h-3.5 text-[#2D7DD2]" />
          <span className="text-[11px] font-bold text-[#E8EDF5] tracking-wider uppercase whitespace-nowrap">
            HOTSPOT ACTIVITY — LAST 7 DAYS (ALL INDIA)
          </span>
        </div>

        {/* Category Legend Badges */}
        <div className="flex items-center gap-4 text-[10px] font-medium">
          {categories.map((cat) => (
            <span key={cat} className="flex items-center gap-1.5 text-[#9CA3AF]">
              <span
                className="w-2.5 h-2.5 rounded-sm shrink-0"
                style={{ backgroundColor: HOTSPOT_COLORS[cat] }}
              />
              <span className="hidden md:inline">{HOTSPOT_LABELS[cat]}</span>
            </span>
          ))}
        </div>
      </div>

      {/* Expanded 7-Day Stacked Bar Chart */}
      <div className="flex-1 relative flex items-end justify-between px-1.5 sm:px-4 pt-2 sm:pt-3 pb-0.5 gap-1 sm:gap-3 md:gap-6 bg-[#0D121F] rounded-lg border border-[#1e293b] overflow-x-auto custom-scrollbar">
        {/* Subtle Horizontal Grid lines */}
        <div className="absolute inset-0 flex flex-col justify-between pointer-events-none p-2 opacity-15">
          <div className="border-b border-[#2D7DD2] w-full" />
          <div className="border-b border-[#2D7DD2] w-full" />
          <div className="border-b border-[#2D7DD2] w-full" />
        </div>

        {dates.map((d) => {
          const isSelected = d.isoDate === selectedDate;
          const total = d.total || 1; // Total FIRMS Detections in sync with Legend panel
          const barHeightPct = Math.max(18, Math.min((total / maxTotal) * 100, 92));

          return (
            <button
              key={d.isoDate}
              type="button"
              onClick={() => setSelectedDate(d.isoDate)}
              className="flex-1 min-w-[36px] flex flex-col items-center group cursor-pointer h-full justify-end z-10 transition-transform active:scale-95"
            >
              {/* FIRMS Detection Total Badge */}
              <span
                className="text-[8.5px] sm:text-[9px] font-mono font-bold mb-0.5 sm:mb-1 transition-colors"
                style={{ color: isSelected ? '#2D7DD2' : '#6B7280' }}
              >
                {d.total}
              </span>

              {/* Stacked Bar Container */}
              <div
                className="w-full max-w-[36px] sm:max-w-[48px] lg:max-w-[56px] rounded-t-md flex flex-col-reverse overflow-hidden transition-all duration-200 group-hover:brightness-110"
                style={{
                  height: `${barHeightPct}%`,
                  border: isSelected ? '2px solid #2D7DD2' : '1px solid #1e293b',
                  boxShadow: isSelected ? '0 0 14px rgba(45,125,210,0.7)' : 'none',
                }}
              >
                <div
                  className="w-full transition-all duration-500 rounded-t-sm"
                  style={{
                    height: total > 0 ? `${(d.counts.industrial_thermal_source / total) * 100}%` : '0%',
                    backgroundColor: HOTSPOT_COLORS.industrial_thermal_source,
                  }}
                />
                <div
                  className="w-full transition-all duration-500"
                  style={{
                    height: total > 0 ? `${(d.counts.mining_thermal_source / total) * 100}%` : '0%',
                    backgroundColor: HOTSPOT_COLORS.mining_thermal_source,
                  }}
                />
                <div
                  className="w-full transition-all duration-500"
                  style={{
                    height: total > 0 ? `${(d.counts.natural_fire / total) * 100}%` : '0%',
                    backgroundColor: HOTSPOT_COLORS.natural_fire,
                  }}
                />
                <div
                  className="w-full transition-all duration-500"
                  style={{
                    height: total > 0 ? `${(d.counts.unknown / total) * 100}%` : '0%',
                    backgroundColor: HOTSPOT_COLORS.unknown,
                  }}
                />
              </div>

              {/* Date Button Base Label */}
              <div
                className={`text-[8.5px] sm:text-[10px] mt-1 font-mono px-1 sm:px-2 py-0.5 rounded-md transition-all whitespace-nowrap ${
                  isSelected
                    ? 'text-white font-bold bg-[#2D7DD2] shadow-md ring-2 ring-[rgba(45,125,210,0.4)]'
                    : 'text-[#8B9BB4] group-hover:text-[#E8EDF5] bg-[#111827]'
                }`}
              >
                {d.label} <span className="hidden sm:inline">{d.isToday ? '(Today)' : ''}</span>
              </div>
            </button>
          );
        })}
      </div>
    </footer>
  );
}
