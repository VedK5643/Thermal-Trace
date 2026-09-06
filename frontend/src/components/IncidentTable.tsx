import React, { useMemo, useState } from 'react';
import { ArrowUp, ArrowDown, ExternalLink } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import type { Incident } from '../types/incident';
import { HOTSPOT_COLORS, HOTSPOT_LABELS, type HotspotType } from '../types/hotspot';
import { useMapStore } from '../store/mapStore';

interface IncidentTableProps {
  incidents: Incident[];
  searchQuery: string;
  typeFilter: string;
  severityFilter: string;
}

type SortField = 'timestamp' | 'brightness' | 'confidence' | 'severity';
type SortOrder = 'asc' | 'desc';

export default function IncidentTable({
  incidents,
  searchQuery,
  typeFilter,
  severityFilter,
}: IncidentTableProps): React.JSX.Element {
  const navigate = useNavigate();
  const selectHotspot = useMapStore((s) => s.selectHotspot);
  const selectFacility = useMapStore((s) => s.selectFacility);
  const setSelectedDate = useMapStore((s) => s.setSelectedDate);

  const handleRowClick = (incident: Incident) => {
    if (incident.timestamp) {
      setSelectedDate(incident.timestamp.slice(0, 10));
    }
    selectHotspot(incident.hotspotId);
    if (incident.facilityId) {
      selectFacility(incident.facilityId);
    }
    navigate('/');
  };
  
  const [sortField, setSortField] = useState<SortField>('timestamp');
  const [sortOrder, setSortOrder] = useState<SortOrder>('desc');

  const filteredAndSortedIncidents = useMemo(() => {
    // Filter
    let result = incidents.filter((inc) => {
      // Type
      const effectiveType = inc.mlType || inc.type;
      if (typeFilter !== 'all' && effectiveType !== typeFilter) return false;
      // Severity
      if (severityFilter !== 'all' && inc.severity !== severityFilter) return false;
      // Search
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        if (
          !inc.facilityName?.toLowerCase().includes(q) &&
          !effectiveType.toLowerCase().includes(q) &&
          !inc.status.toLowerCase().includes(q) &&
          !inc.id.toLowerCase().includes(q)
        ) {
          return false;
        }
      }
      return true;
    });

    // Sort
    result.sort((a, b) => {
      let comparison = 0;
      switch (sortField) {
        case 'timestamp':
          comparison = new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime();
          break;
        case 'brightness':
          comparison = a.brightness - b.brightness;
          break;
        case 'confidence':
          comparison = a.confidence - b.confidence;
          break;
        case 'severity': {
          const severityRank: Record<string, number> = { critical: 4, high: 3, medium: 2, low: 1 };
          comparison = (severityRank[a.severity] || 0) - (severityRank[b.severity] || 0);
          break;
        }
      }
      return sortOrder === 'asc' ? comparison : -comparison;
    });

    return result;
  }, [incidents, searchQuery, typeFilter, severityFilter, sortField, sortOrder]);

  const toggleSort = (field: SortField) => {
    if (sortField === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortOrder('desc');
    }
  };

  const SortIcon = ({ field }: { field: SortField }) => {
    if (sortField !== field) return null;
    return sortOrder === 'asc' ? (
      <ArrowUp className="w-3 h-3 inline-block ml-1" />
    ) : (
      <ArrowDown className="w-3 h-3 inline-block ml-1" />
    );
  };

  if (filteredAndSortedIncidents.length === 0) {
    return (
      <div className="bg-[#0F1623] border border-[#1E2D45] rounded-lg p-16 text-center shadow-xl">
        <p className="text-[#7A8FA8] text-sm">NO INCIDENTS FOUND</p>
      </div>
    );
  }

  return (
    <div className="bg-[#0F1623] border border-[#1E2D45] rounded-lg overflow-hidden shadow-xl">
      <div className="overflow-x-auto custom-scrollbar">
        <table className="w-full text-left text-xs">
          <thead className="bg-[#162033] border-b border-[#1E2D45] text-[#7A8FA8] font-mono uppercase tracking-wider select-none whitespace-nowrap">
            <tr>
              <th className="py-2.5 sm:py-3 px-3 sm:px-4">INCIDENT ID</th>
              <th className="py-2.5 sm:py-3 px-3 sm:px-4">TYPE</th>
              <th className="py-2.5 sm:py-3 px-3 sm:px-4">FACILITY</th>
              <th 
                className="py-2.5 sm:py-3 px-3 sm:px-4 cursor-pointer hover:text-[#E8EDF5]"
                onClick={() => toggleSort('brightness')}
              >
                BRIGHTNESS <SortIcon field="brightness" />
              </th>
              <th 
                className="py-2.5 sm:py-3 px-3 sm:px-4 cursor-pointer hover:text-[#E8EDF5]"
                onClick={() => toggleSort('confidence')}
              >
                CONFIDENCE <SortIcon field="confidence" />
              </th>
              <th 
                className="py-2.5 sm:py-3 px-3 sm:px-4 cursor-pointer hover:text-[#E8EDF5]"
                onClick={() => toggleSort('timestamp')}
              >
                DETECTED <SortIcon field="timestamp" />
              </th>
              <th 
                className="py-2.5 sm:py-3 px-3 sm:px-4 cursor-pointer hover:text-[#E8EDF5]"
                onClick={() => toggleSort('severity')}
              >
                SEVERITY <SortIcon field="severity" />
              </th>
              <th className="py-2.5 sm:py-3 px-3 sm:px-4 text-right">ACTION</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#1E2D45]/60 text-[#E8EDF5]">
            {filteredAndSortedIncidents.map((inc) => {
              const d = new Date(inc.timestamp);
              const dateStr = d.toISOString().split('T')[0];
              const timeStr = d.toISOString().split('T')[1].slice(0, 5) + ' UTC';

              const severityColor =
                inc.severity === 'critical'
                  ? 'text-[#FF4444]'
                  : inc.severity === 'high'
                  ? 'text-[#FF8C00]'
                  : inc.severity === 'medium'
                  ? 'text-[#F5C518]'
                  : 'text-[#2D7DD2]';

              return (
                <tr 
                  key={inc.id}
                  onClick={() => handleRowClick(inc)}
                  className="hover:bg-[#162033]/60 cursor-pointer transition-colors"
                >
                  <td className="py-2.5 sm:py-3 px-3 sm:px-4 font-mono text-[#7A8FA8] whitespace-nowrap">{inc.id}</td>
                  <td className="py-2.5 sm:py-3 px-3 sm:px-4 whitespace-nowrap">
                    <div className="flex items-center gap-1.5">
                      <span
                        className="w-2 h-2 rounded-full shrink-0"
                        style={{ backgroundColor: HOTSPOT_COLORS[inc.mlType || inc.type] || HOTSPOT_COLORS.unknown }}
                      />
                      <span>{HOTSPOT_LABELS[(inc.mlType || inc.type) as HotspotType] || 'Unknown / Unclassified'}</span>
                    </div>
                  </td>
                  <td className="py-2.5 sm:py-3 px-3 sm:px-4 truncate max-w-[130px] sm:max-w-[200px]" title={inc.facilityName || ''}>
                    {inc.facilityName}
                  </td>
                  <td className="py-2.5 sm:py-3 px-3 sm:px-4 font-mono whitespace-nowrap">{inc.brightness} K</td>
                  <td className="py-2.5 sm:py-3 px-3 sm:px-4 font-mono whitespace-nowrap">{inc.confidence}%</td>
                  <td className="py-2.5 sm:py-3 px-3 sm:px-4 whitespace-nowrap">
                    <div className="flex flex-col">
                      <span>{dateStr}</span>
                      <span className="text-[10px] text-[#7A8FA8] font-mono">{timeStr}</span>
                    </div>
                  </td>
                  <td className={`py-2.5 sm:py-3 px-3 sm:px-4 uppercase font-semibold text-[10px] tracking-wider whitespace-nowrap ${severityColor}`}>
                    {inc.severity}
                  </td>
                  <td className="py-2.5 sm:py-3 px-3 sm:px-4 text-right whitespace-nowrap">
                    <button
                      type="button"
                      className="text-[#7A8FA8] hover:text-[#2D7DD2] transition-colors p-1"
                      title="View on map"
                    >
                      <ExternalLink className="w-4 h-4" />
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
