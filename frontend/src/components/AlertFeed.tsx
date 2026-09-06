import React from 'react';
import { Bell, AlertCircle, AlertTriangle, Info, X } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useAlertsQuery } from '../services/queries/useAlertsQuery';
import { useMapStore } from '../store/mapStore';
import type { AlertSeverity, Alert } from '../types/alert';

export default function AlertFeed(): React.JSX.Element {
  const navigate = useNavigate();
  const { data: alerts, isLoading } = useAlertsQuery();
  const selectHotspot = useMapStore((s) => s.selectHotspot);
  const selectFacility = useMapStore((s) => s.selectFacility);
  const setSelectedDate = useMapStore((s) => s.setSelectedDate);
  const [isOpen, setIsOpen] = React.useState(false);

  const unackCount = alerts?.filter((a) => !a.acknowledged).length ?? 0;

  const handleAlertClick = (alert: Alert) => {
    if (alert.timestamp) {
      const dateStr = alert.timestamp.slice(0, 10);
      setSelectedDate(dateStr);
    }
    if (alert.hotspotId) {
      selectHotspot(alert.hotspotId);
    } else if (alert.facilityId) {
      selectFacility(alert.facilityId);
    }
    setIsOpen(false);
    navigate('/');
  };

  const getIcon = (severity: AlertSeverity) => {
    switch (severity) {
      case 'critical': return <AlertCircle className="w-3.5 h-3.5 text-[#FF4444]" />;
      case 'warning': return <AlertTriangle className="w-3.5 h-3.5 text-[#F97316]" />;
      case 'info': return <Info className="w-3.5 h-3.5 text-[#2D7DD2]" />;
    }
  };

  const getSeverityColor = (severity: AlertSeverity) => {
    switch (severity) {
      case 'critical': return 'border-l-[#FF4444]';
      case 'warning': return 'border-l-[#F97316]';
      case 'info': return 'border-l-[#2D7DD2]';
    }
  };

  return (
    <>
      {/* Toggle Button — positioned top-right near map theme selector */}
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="absolute z-20 flex items-center gap-1.5 cursor-pointer"
        style={{
          top: 16,
          right: 176,
          padding: '6px 10px',
          backgroundColor: '#111827',
          border: '1px solid #1e293b',
          borderRadius: 8,
          boxShadow: '0 8px 32px rgba(0,0,0,0.8)',
          color: '#E8EDF5',
        }}
        title="Alert Notifications"
        aria-label="Toggle alerts"
      >
        <Bell style={{ width: 14, height: 14, color: '#E8EDF5' }} />
        {unackCount > 0 && (
          <span style={{ fontSize: 10, fontWeight: 700, color: '#FF4444' }}>{unackCount}</span>
        )}
      </button>

      {/* Panel - opens down beneath button */}
      {isOpen && (
        <div
          className="absolute z-30 w-72 max-h-80 flex flex-col overflow-hidden"
          style={{
            top: 56,
            right: 176,
            backgroundColor: '#111827',
            border: '1px solid #1e293b',
            borderRadius: 12,
            boxShadow: '0 12px 40px rgba(0,0,0,0.9)',
          }}
        >
          {/* Header */}
          <div
            className="flex items-center justify-between px-3 py-2.5 shrink-0"
            style={{ borderBottom: '1px solid #1e293b' }}
          >
            <span className="text-[10px] font-bold tracking-widest text-[#6B7280] uppercase flex items-center gap-1.5">
              <Bell className="w-3.5 h-3.5 text-[#FF4444]" />
              ALERTS
              {unackCount > 0 && (
                <span className="ml-1 bg-[#FF4444] text-white text-[9px] font-bold px-1.5 py-0.5 rounded-full">
                  {unackCount}
                </span>
              )}
            </span>
            <button
              type="button"
              onClick={() => setIsOpen(false)}
              className="text-[#6B7280] hover:text-[#E8EDF5] p-0.5 rounded cursor-pointer"
              style={{ backgroundColor: 'transparent' }}
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>

          {/* Alert list */}
          <div className="flex-1 overflow-y-auto p-2 space-y-1.5">
            {isLoading && (
              <p className="text-center text-[#6B7280] text-xs py-4">Loading alerts...</p>
            )}
            {!isLoading && (!alerts || alerts.length === 0) && (
              <p className="text-center text-[#6B7280] text-xs py-4">No active alerts.</p>
            )}
            {alerts?.map((alert) => {
              const d = new Date(alert.timestamp);
              const time = d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });

              return (
                <button
                  key={alert.id}
                  type="button"
                  onClick={() => handleAlertClick(alert)}
                  className={`w-full text-left px-3 py-2 rounded-lg border-l-2 cursor-pointer ${getSeverityColor(alert.severity)}`}
                  style={{
                    backgroundColor: 'rgba(30,45,69,0.5)',
                    borderTop: '1px solid #374151',
                    borderRight: '1px solid #374151',
                    borderBottom: '1px solid #374151',
                  }}
                >
                  <div className="flex items-center justify-between gap-2 mb-0.5">
                    <div className="flex items-center gap-1.5">
                      {getIcon(alert.severity)}
                      <span className="text-[11px] font-semibold text-[#E8EDF5]">{alert.title}</span>
                    </div>
                    <span className="text-[9px] font-mono text-[#4B5563]">{time}</span>
                  </div>
                  <p className="text-[10px] text-[#6B7280] line-clamp-2 ml-5">{alert.message}</p>
                </button>
              );
            })}
          </div>
        </div>
      )}
    </>
  );
}
