import React from 'react';
import { useMapStore } from '../store/mapStore';
import { getRollingISTDates } from '../utils/dateUtils';

interface DateItem {
  label: string;
  isoDate: string;
  isToday?: boolean;
}

export default function Timeline(): React.JSX.Element {
  const selectedDate = useMapStore((s) => s.selectedDate);
  const setSelectedDate = useMapStore((s) => s.setSelectedDate);
  useMapStore((s) => s.todayIST); // Subscribe to midnight rollover events

  const dates: DateItem[] = getRollingISTDates(7);

  const selectedIndex = dates.findIndex((d) => d.isoDate === selectedDate);
  const activeIndex = selectedIndex >= 0 ? selectedIndex : dates.length - 1;

  const handleDateClick = (index: number): void => {
    setSelectedDate(dates[index].isoDate);
  };

  const progressPercent = (activeIndex / (dates.length - 1)) * 100;

  return (
    <div
      className="absolute z-20 flex flex-col justify-between"
      style={{
        bottom: 0,
        left: '50%',
        transform: 'translateX(-50%)',
        width: 'calc(100% - 380px)',
        maxWidth: 720,
        minWidth: 320,
        height: 52,
        backgroundColor: '#111827',
        borderTop: '1px solid #1e293b',
        borderLeft: '1px solid #1e293b',
        borderRight: '1px solid #1e293b',
        borderBottom: 'none',
        borderRadius: '10px 10px 0 0',
        boxShadow: '0 -4px 24px rgba(0,0,0,0.7)',
        padding: '6px 16px 4px 16px',
      }}
    >
      {/* Header row with TIMELINE label and TODAY button */}
      <div className="flex items-center justify-between" style={{ height: 16 }}>
        <span style={{ fontSize: 9, fontWeight: 700, letterSpacing: '0.08em', color: '#6B7280', textTransform: 'uppercase' }}>
          TIMELINE
        </span>
        <div className="flex items-center gap-2">
          <span style={{ fontSize: 9, fontFamily: 'monospace', color: '#4B5563' }}>-6D</span>
          <button
            type="button"
            onClick={() => handleDateClick(dates.length - 1)}
            style={{
              fontSize: 9,
              fontWeight: 700,
              padding: '1px 8px',
              borderRadius: 3,
              backgroundColor: activeIndex === dates.length - 1 ? '#2D7DD2' : '#1e293b',
              color: activeIndex === dates.length - 1 ? '#FFFFFF' : '#6B7280',
              border: 'none',
              cursor: 'pointer',
            }}
          >
            TODAY
          </button>
        </div>
      </div>

      {/* Track & Date Nodes */}
      <div className="relative flex items-center" style={{ height: 26 }}>
        {/* Background track line */}
        <div
          style={{
            position: 'absolute',
            top: 6,
            left: 10,
            right: 10,
            height: 2,
            backgroundColor: '#1e293b',
            borderRadius: 1,
          }}
        />
        {/* Active progress track line */}
        <div
          style={{
            position: 'absolute',
            top: 6,
            left: 10,
            width: `calc(${progressPercent}% * 0.96)`,
            height: 2,
            backgroundColor: '#2D7DD2',
            borderRadius: 1,
            transition: 'width 0.2s ease',
          }}
        />

        {/* Date node items */}
        <div className="w-full flex items-center justify-between relative z-10 px-1">
          {dates.map((item, index) => {
            const isActive = index === activeIndex;
            const isPast = index < activeIndex;
            return (
              <button
                key={item.isoDate}
                type="button"
                onClick={() => handleDateClick(index)}
                className="flex flex-col items-center cursor-pointer"
                style={{ backgroundColor: 'transparent', border: 'none', padding: 0, gap: 2 }}
              >
                {/* Node circle */}
                <div
                  style={{
                    width: isActive ? 14 : 10,
                    height: isActive ? 14 : 10,
                    borderRadius: '50%',
                    backgroundColor: isActive ? '#2D7DD2' : isPast ? '#2D7DD2' : '#111827',
                    border: `2px solid ${isActive ? '#E8EDF5' : isPast ? '#2D7DD2' : '#374151'}`,
                    boxShadow: isActive ? '0 0 6px rgba(45,125,210,0.8)' : 'none',
                    transition: 'all 0.15s ease',
                  }}
                />
                {/* Date label */}
                <span
                  style={{
                    fontSize: 10,
                    fontWeight: isActive ? 700 : 500,
                    color: isActive ? '#E8EDF5' : '#6B7280',
                    whiteSpace: 'nowrap',
                    lineHeight: 1,
                  }}
                >
                  {item.label}
                </span>
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}
