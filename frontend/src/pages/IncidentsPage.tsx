import React, { useMemo, useState } from 'react';
import Navbar from '../components/Navbar';
import { Search, Download, RotateCcw } from 'lucide-react';
import { useHotspotsQuery } from '../services/queries/useHotspotsQuery';
import { useFacilitiesQuery } from '../services/queries/useFacilitiesQuery';
import { useMapStore } from '../store/mapStore';
import { deriveIncidents } from '../utils/incidents';
import { downloadIncidentsCsv } from '../utils/exportCsv';
import IncidentTable from '../components/IncidentTable';

export default function IncidentsPage(): React.JSX.Element {
  const selectedDate = useMapStore((s) => s.selectedDate);
  const minimumConfidence = useMapStore((s) => s.minimumConfidence);
  const { data: hotspots, isLoading: hotspotsLoading } = useHotspotsQuery(selectedDate, minimumConfidence);
  const { data: facilities, isLoading: facilitiesLoading } = useFacilitiesQuery();
  
  const [searchQuery, setSearchQuery] = useState('');
  const [typeFilter, setTypeFilter] = useState('all');
  const [severityFilter, setSeverityFilter] = useState('all');

  const incidents = useMemo(() => {
    if (!hotspots || !facilities) return [];
    return deriveIncidents(hotspots, facilities);
  }, [hotspots, facilities]);

  const handleExport = () => {
    if (incidents.length === 0) return;
    const now = new Date().toISOString().split('T')[0];
    
    // Quick filter check to only export what's visible
    const filtered = incidents.filter(inc => {
      const effectiveType = inc.mlType || inc.type;
      if (typeFilter !== 'all' && effectiveType !== typeFilter) return false;
      if (severityFilter !== 'all' && inc.severity !== severityFilter) return false;
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

    downloadIncidentsCsv(filtered, `thermaltrace-incidents-${now}.csv`);
  };

  const resetFilters = () => {
    setSearchQuery('');
    setTypeFilter('all');
    setSeverityFilter('all');
  };

  return (
    <div className="flex flex-col h-screen w-screen overflow-hidden bg-[#080C14] text-[#E8EDF5]">
      <Navbar />

      <main className="flex-1 w-full p-3 sm:p-6 overflow-y-auto max-w-7xl mx-auto space-y-4 sm:space-y-6">
        {/* Page Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 sm:gap-4 border-b border-[#1E2D45] pb-4">
          <div>
            <h1 className="text-lg sm:text-xl font-bold tracking-tight text-[#E8EDF5]">
              INCIDENT LOG
            </h1>
            <p className="text-xs text-[#7A8FA8] mt-0.5 sm:mt-1">
              All classified thermal anomalies — India region
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2 sm:gap-3">
            <div className="relative w-full sm:w-auto">
              <Search className="w-4 h-4 text-[#7A8FA8] absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                placeholder="Search location or ID..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="bg-[#0F1623] border border-[#1E2D45] rounded-md pl-9 pr-3 py-1.5 text-xs text-[#E8EDF5] placeholder-[#7A8FA8]/60 focus:border-[#2D7DD2] focus:outline-none w-full sm:w-64"
              />
            </div>

            <div className="flex flex-wrap items-center gap-2 w-full sm:w-auto">
              <select
                value={typeFilter}
                onChange={(e) => setTypeFilter(e.target.value)}
                className="flex-1 sm:flex-initial bg-[#0F1623] border border-[#1E2D45] rounded-md px-2.5 py-1.5 text-xs text-[#E8EDF5] focus:outline-none focus:border-[#2D7DD2] appearance-none cursor-pointer"
              >
                <option value="all">All Types</option>
                <option value="industrial_thermal_source">Industrial Thermal Source</option>
                <option value="mining_thermal_source">Mining Thermal Source</option>
                <option value="natural_fire">Natural Fire</option>
                <option value="unknown">Unknown / Unclassified</option>
              </select>

              <select
                value={severityFilter}
                onChange={(e) => setSeverityFilter(e.target.value)}
                className="flex-1 sm:flex-initial bg-[#0F1623] border border-[#1E2D45] rounded-md px-2.5 py-1.5 text-xs text-[#E8EDF5] focus:outline-none focus:border-[#2D7DD2] appearance-none cursor-pointer"
              >
                <option value="all">All Severities</option>
                <option value="critical">Critical</option>
                <option value="high">High</option>
                <option value="medium">Medium</option>
                <option value="low">Low</option>
              </select>

              {(searchQuery || typeFilter !== 'all' || severityFilter !== 'all') && (
                <button
                  type="button"
                  onClick={resetFilters}
                  className="bg-[#162033]/60 hover:bg-[#162033] border border-[#1E2D45] text-[#7A8FA8] hover:text-[#E8EDF5] px-2 py-1.5 rounded-md transition-colors"
                  title="Reset Filters"
                >
                  <RotateCcw className="w-4 h-4" />
                </button>
              )}

              <button
                type="button"
                onClick={handleExport}
                disabled={incidents.length === 0}
                className="bg-[#2D7DD2]/10 border border-[#2D7DD2]/30 hover:bg-[#2D7DD2]/20 text-[#2D7DD2] px-3 py-1.5 rounded-md text-xs font-medium flex items-center gap-1.5 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Download className="w-3.5 h-3.5" />
                <span>Export CSV</span>
              </button>
            </div>
          </div>
        </div>

        {/* Operational Table Shell */}
        {hotspotsLoading || facilitiesLoading ? (
          <div className="bg-[#0F1623] border border-[#1E2D45] rounded-lg p-16 text-center shadow-xl">
            <p className="text-[#7A8FA8] text-sm flex items-center justify-center gap-2">
              <span className="w-4 h-4 border-2 border-[#2D7DD2] border-t-transparent rounded-full animate-spin"></span>
              Loading incident data...
            </p>
          </div>
        ) : (
          <IncidentTable
            incidents={incidents}
            searchQuery={searchQuery}
            typeFilter={typeFilter}
            severityFilter={severityFilter}
          />
        )}
      </main>
    </div>
  );
}
