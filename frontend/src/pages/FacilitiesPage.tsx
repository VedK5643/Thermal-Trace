import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import Navbar from '../components/Navbar';
import api from '../services/api';
import {
  Building2,
  Search,
  Filter,
  MapPin,
  Bot,
  Info,
  ChevronLeft,
  ChevronRight,
  ShieldAlert
} from 'lucide-react';

interface FacilityItem {
  id: string;
  name: string;
  type: string;
  category?: string;
  state: string;
  city?: string;
  latitude: number;
  longitude: number;
  country?: string;
}

export default function FacilitiesPage(): React.JSX.Element {
  const navigate = useNavigate();
  const [facilities, setFacilities] = useState<FacilityItem[]>([]);
  const [summaryCounts, setSummaryCounts] = useState<Record<string, number>>({});
  const [totalCount, setTotalCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filter & Search State
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedType, setSelectedType] = useState<string>('all');
  const [selectedState, setSelectedState] = useState<string>('all');
  const [currentPage, setCurrentPage] = useState(1);
  const [selectedFacility, setSelectedFacility] = useState<FacilityItem | null>(null);

  const pageSize = 15;

  useEffect(() => {
    fetchFacilities();
    fetchSummary();
  }, [currentPage, selectedType, selectedState]);

  const fetchSummary = async () => {
    try {
      const res = await api.get('/api/v1/facilities/summary');
      setSummaryCounts(res.data.typeDistribution || {});
    } catch (err) {
      console.error('Failed to load facility summary:', err);
    }
  };

  const fetchFacilities = async () => {
    setLoading(true);
    setError(null);
    try {
      const params: Record<string, any> = {
        page: currentPage,
        page_size: pageSize,
      };
      if (selectedType !== 'all') params.type = selectedType;
      if (selectedState !== 'all') params.state = selectedState;

      const res = await api.get('/api/v1/facilities', { params });
      setFacilities(res.data.data || []);
      setTotalCount(res.data.pagination?.total || 0);
    } catch (err: any) {
      setError('Failed to load facilities. Please verify backend connection.');
    } finally {
      setLoading(false);
    }
  };

  const filteredFacilities = facilities.filter((f) => {
    if (!searchTerm.trim()) return true;
    const term = searchTerm.toLowerCase();
    return (
      f.name.toLowerCase().includes(term) ||
      f.state.toLowerCase().includes(term) ||
      (f.city && f.city.toLowerCase().includes(term)) ||
      f.type.toLowerCase().includes(term)
    );
  });

  const handleViewOnMap = (facility: FacilityItem) => {
    navigate(`/?lat=${facility.latitude}&lng=${facility.longitude}&zoom=12`);
  };

  const handleAskAI = (facility: FacilityItem) => {
    const promptText = `Analyze thermal activity near ${facility.name} (${facility.type} in ${facility.state}). Are there any predicted industrial thermal sources or persistent thermal anomalies nearby?`;
    window.dispatchEvent(new CustomEvent('ask-ai-hotspot', { detail: { hotspotId: promptText } }));
  };

  const totalPages = Math.ceil(totalCount / pageSize) || 1;

  return (
    <div className="flex flex-col h-screen w-screen overflow-hidden bg-[#080C14] text-[#E8EDF5]">
      <Navbar />

      <main className="flex-1 w-full p-3 sm:p-6 overflow-y-auto max-w-7xl mx-auto space-y-4 sm:space-y-6">
        {/* Page Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 sm:gap-4 border-b border-[#1E2D45] pb-4 sm:pb-5">
          <div>
            <div className="flex items-center gap-2">
              <div className="p-2 bg-[#2D7DD2]/10 border border-[#2D7DD2]/30 rounded-lg text-[#2D7DD2]">
                <Building2 className="w-4 h-4 sm:w-5 sm:h-5" />
              </div>
              <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-[#E8EDF5]">
                Industrial Facility Inventory
              </h1>
            </div>
            <p className="text-xs text-[#7A8FA8] mt-1">
              Searchable operational infrastructure providing spatial context for detected thermal anomalies across India. Satellite imagery provides visual and geographic verification.
            </p>
          </div>

          <div className="flex items-center gap-2 bg-[#111827] border border-[#1E2D45] p-2.5 sm:px-3.5 sm:py-2 rounded-xl text-xs text-[#7A8FA8]">
            <Info className="w-4 h-4 text-[#2D7DD2] shrink-0" />
            <span>Facility proximity represents <strong className="text-[#E8EDF5]">contextual spatial evidence</strong> (NOT proof of causation).</span>
          </div>
        </div>

        {/* Summary Metric Cards */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2.5 sm:gap-3">
          <div className="bg-[#111827] border border-[#1E2D45] p-3 sm:p-3.5 rounded-xl shadow-lg">
            <span className="text-[9px] sm:text-[10px] font-bold text-[#7A8FA8] uppercase tracking-wider block">Total Facilities</span>
            <span className="text-lg sm:text-xl font-extrabold text-[#E8EDF5] mt-0.5 sm:mt-1 block">{totalCount}</span>
          </div>
          <div className="bg-[#111827] border border-[#1E2D45] p-3 sm:p-3.5 rounded-xl shadow-lg">
            <span className="text-[9px] sm:text-[10px] font-bold text-[#7A8FA8] uppercase tracking-wider block">Refineries</span>
            <span className="text-lg sm:text-xl font-extrabold text-[#2D7DD2] mt-0.5 sm:mt-1 block">{summaryCounts['Refinery'] || summaryCounts['refinery'] || 0}</span>
          </div>
          <div className="bg-[#111827] border border-[#1E2D45] p-3 sm:p-3.5 rounded-xl shadow-lg">
            <span className="text-[9px] sm:text-[10px] font-bold text-[#7A8FA8] uppercase tracking-wider block">Power Plants</span>
            <span className="text-lg sm:text-xl font-extrabold text-amber-400 mt-0.5 sm:mt-1 block">{summaryCounts['Power Plant'] || summaryCounts['power_plant'] || 0}</span>
          </div>
          <div className="bg-[#111827] border border-[#1E2D45] p-3 sm:p-3.5 rounded-xl shadow-lg">
            <span className="text-[9px] sm:text-[10px] font-bold text-[#7A8FA8] uppercase tracking-wider block">Steel Plants</span>
            <span className="text-lg sm:text-xl font-extrabold text-orange-400 mt-0.5 sm:mt-1 block">{summaryCounts['Steel Plant'] || 0}</span>
          </div>
          <div className="bg-[#111827] border border-[#1E2D45] p-3 sm:p-3.5 rounded-xl shadow-lg">
            <span className="text-[9px] sm:text-[10px] font-bold text-[#7A8FA8] uppercase tracking-wider block">Cement Plants</span>
            <span className="text-lg sm:text-xl font-extrabold text-emerald-400 mt-0.5 sm:mt-1 block">{summaryCounts['Cement Plant'] || 0}</span>
          </div>
          <div className="bg-[#111827] border border-[#1E2D45] p-3 sm:p-3.5 rounded-xl shadow-lg">
            <span className="text-[9px] sm:text-[10px] font-bold text-[#7A8FA8] uppercase tracking-wider block">LNG Terminals</span>
            <span className="text-lg sm:text-xl font-extrabold text-cyan-400 mt-0.5 sm:mt-1 block">{summaryCounts['LNG Terminal'] || summaryCounts['lng_terminal'] || 0}</span>
          </div>
        </div>

        {/* Filter Controls Bar */}
        <div className="bg-[#111827] border border-[#1E2D45] p-3 sm:p-4 rounded-xl flex flex-col md:flex-row gap-3 items-center justify-between shadow-xl">
          <div className="relative flex-1 w-full">
            <Search className="w-4 h-4 text-[#7A8FA8] absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Search facility by name, city, state, or type..."
              className="w-full bg-[#080C14] border border-[#1E2D45] rounded-lg pl-9 pr-3 py-2 text-xs text-[#E8EDF5] placeholder-[#7A8FA8] focus:border-[#2D7DD2]/50 focus:outline-none transition-colors"
            />
          </div>

          <div className="flex flex-wrap items-center gap-2 sm:gap-3 w-full md:w-auto">
            <div className="flex items-center gap-1.5 flex-1 sm:flex-initial">
              <Filter className="w-3.5 h-3.5 text-[#7A8FA8] shrink-0" />
              <select
                value={selectedType}
                onChange={(e) => {
                  setSelectedType(e.target.value);
                  setCurrentPage(1);
                }}
                className="w-full sm:w-auto bg-[#080C14] border border-[#1E2D45] rounded-lg px-2.5 py-2 text-xs text-[#E8EDF5] focus:outline-none"
              >
                <option value="all">All Types</option>
                <option value="refinery">Refinery</option>
                <option value="power_plant">Power Plant</option>
                <option value="steel_plant">Steel Plant</option>
                <option value="cement_plant">Cement Plant</option>
                <option value="lng_terminal">LNG Terminal</option>
              </select>
            </div>

            <select
              value={selectedState}
              onChange={(e) => {
                setSelectedState(e.target.value);
                setCurrentPage(1);
              }}
              className="flex-1 sm:flex-initial bg-[#080C14] border border-[#1E2D45] rounded-lg px-2.5 py-2 text-xs text-[#E8EDF5] focus:outline-none"
            >
              <option value="all">All States</option>
              <option value="Gujarat">Gujarat</option>
              <option value="Maharashtra">Maharashtra</option>
              <option value="Karnataka">Karnataka</option>
              <option value="Tamil Nadu">Tamil Nadu</option>
              <option value="Odisha">Odisha</option>
              <option value="West Bengal">West Bengal</option>
            </select>
          </div>
        </div>

        {/* Main Facilities Table */}
        <div className="bg-[#111827] border border-[#1E2D45] rounded-xl overflow-hidden shadow-2xl">
          {loading ? (
            <div className="p-12 text-center text-xs text-[#7A8FA8] flex flex-col items-center gap-2">
              <div className="w-6 h-6 border-2 border-[#2D7DD2] border-t-transparent rounded-full animate-spin"></div>
              <span>Querying PostGIS facility infrastructure database...</span>
            </div>
          ) : error ? (
            <div className="p-8 text-center text-xs text-red-400 bg-red-950/20">{error}</div>
          ) : filteredFacilities.length === 0 ? (
            <div className="p-12 text-center text-xs text-[#7A8FA8]">
              No industrial facilities matching the selected criteria.
            </div>
          ) : (
            <div className="overflow-x-auto custom-scrollbar">
              <table className="w-full text-left text-xs">
                <thead className="bg-[#162033] border-b border-[#1E2D45] text-[#7A8FA8] uppercase font-bold tracking-wider text-[10px] whitespace-nowrap">
                  <tr>
                    <th className="px-3 sm:px-4 py-3">Facility Name</th>
                    <th className="px-3 sm:px-4 py-3">Type</th>
                    <th className="px-3 sm:px-4 py-3">State</th>
                    <th className="px-3 sm:px-4 py-3">Coordinates</th>
                    <th className="px-3 sm:px-4 py-3">Proximity Status</th>
                    <th className="px-3 sm:px-4 py-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#1E2D45]/60 text-[#E8EDF5]">
                  {filteredFacilities.map((f) => (
                    <tr key={f.id} className="hover:bg-[#162033]/40 transition-colors">
                      <td className="px-3 sm:px-4 py-3 sm:py-3.5 font-semibold flex items-center gap-2 whitespace-nowrap">
                        <Building2 className="w-4 h-4 text-[#2D7DD2] shrink-0" />
                        <span>{f.name}</span>
                      </td>
                      <td className="px-3 sm:px-4 py-3 sm:py-3.5 whitespace-nowrap">
                        <span className="px-2 py-0.5 rounded text-[11px] font-medium bg-[#2D7DD2]/10 text-[#2D7DD2] border border-[#2D7DD2]/20">
                          {f.type}
                        </span>
                      </td>
                      <td className="px-3 sm:px-4 py-3 sm:py-3.5 text-[#7A8FA8] whitespace-nowrap">{f.state}</td>
                      <td className="px-3 sm:px-4 py-3 sm:py-3.5 font-mono text-[11px] text-[#7A8FA8] whitespace-nowrap">
                        {f.latitude.toFixed(4)}°, {f.longitude.toFixed(4)}°
                      </td>
                      <td className="px-3 sm:px-4 py-3 sm:py-3.5 whitespace-nowrap">
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-950/40 text-emerald-400 border border-emerald-500/20">
                          Spatial Context Active
                        </span>
                      </td>
                      <td className="px-3 sm:px-4 py-3 sm:py-3.5 text-right whitespace-nowrap space-x-1 sm:space-x-1.5">
                        <button
                          onClick={() => setSelectedFacility(f)}
                          className="px-2 sm:px-2.5 py-1 bg-[#162033] hover:bg-[#1E2D45] text-[#E8EDF5] border border-[#1E2D45] rounded-md transition-colors text-[11px]"
                        >
                          Details
                        </button>
                        <button
                          onClick={() => handleViewOnMap(f)}
                          className="px-2 sm:px-2.5 py-1 bg-[#2D7DD2]/20 hover:bg-[#2D7DD2]/30 text-[#2D7DD2] border border-[#2D7DD2]/30 rounded-md transition-colors text-[11px] inline-flex items-center gap-1"
                        >
                          <MapPin className="w-3 h-3" />
                          <span>Map</span>
                        </button>
                        <button
                          onClick={() => handleAskAI(f)}
                          className="px-2 sm:px-2.5 py-1 bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 border border-amber-500/30 rounded-md transition-colors text-[11px] inline-flex items-center gap-1"
                        >
                          <Bot className="w-3 h-3 text-amber-400" />
                          <span>Ask AI</span>
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Pagination Controls */}
          <div className="px-4 py-3 bg-[#162033]/60 border-t border-[#1E2D45] flex flex-col sm:flex-row gap-2 items-center justify-between text-xs text-[#7A8FA8]">
            <span>
              Showing {filteredFacilities.length} of {totalCount} facilities
            </span>

            <div className="flex items-center gap-2">
              <button
                disabled={currentPage === 1}
                onClick={() => setCurrentPage((p) => Math.max(p - 1, 1))}
                className="p-1.5 bg-[#080C14] hover:bg-[#1E2D45] disabled:opacity-40 border border-[#1E2D45] rounded-md"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              <span>Page {currentPage} of {totalPages}</span>
              <button
                disabled={currentPage >= totalPages}
                onClick={() => setCurrentPage((p) => p + 1)}
                className="p-1.5 bg-[#080C14] hover:bg-[#1E2D45] disabled:opacity-40 border border-[#1E2D45] rounded-md"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>

        {/* Facility Detail Drawer Modal */}
        {selectedFacility && (
          <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-3 sm:p-4">
            <div className="bg-[#111827] border border-[#1E2D45] rounded-2xl max-w-lg w-full max-h-[90vh] overflow-y-auto p-4 sm:p-6 space-y-3 sm:space-y-4 shadow-2xl relative custom-scrollbar">
              <div className="flex items-center justify-between border-b border-[#1E2D45] pb-3">
                <div className="flex items-center gap-2 pr-2 truncate">
                  <Building2 className="w-5 h-5 text-[#2D7DD2] shrink-0" />
                  <h3 className="font-bold text-base text-[#E8EDF5] truncate">{selectedFacility.name}</h3>
                </div>
                <button
                  onClick={() => setSelectedFacility(null)}
                  className="text-[#7A8FA8] hover:text-[#E8EDF5] text-xs font-semibold px-2 py-1 bg-[#162033] rounded-md shrink-0"
                >
                  Close
                </button>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 sm:gap-3 text-xs">
                <div className="bg-[#080C14] border border-[#1E2D45] p-2.5 sm:p-3 rounded-lg">
                  <span className="text-[10px] text-[#7A8FA8] uppercase font-bold block">Facility Type</span>
                  <span className="text-sm font-semibold text-[#2D7DD2] mt-0.5 block">{selectedFacility.type}</span>
                </div>
                <div className="bg-[#080C14] border border-[#1E2D45] p-2.5 sm:p-3 rounded-lg">
                  <span className="text-[10px] text-[#7A8FA8] uppercase font-bold block">State Scope</span>
                  <span className="text-sm font-semibold text-[#E8EDF5] mt-0.5 block">{selectedFacility.state}</span>
                </div>
                <div className="bg-[#080C14] border border-[#1E2D45] p-2.5 sm:p-3 rounded-lg">
                  <span className="text-[10px] text-[#7A8FA8] uppercase font-bold block">Latitude</span>
                  <span className="text-sm font-mono text-[#E8EDF5] mt-0.5 block">{selectedFacility.latitude}°</span>
                </div>
                <div className="bg-[#080C14] border border-[#1E2D45] p-2.5 sm:p-3 rounded-lg">
                  <span className="text-[10px] text-[#7A8FA8] uppercase font-bold block">Longitude</span>
                  <span className="text-sm font-mono text-[#E8EDF5] mt-0.5 block">{selectedFacility.longitude}°</span>
                </div>
              </div>

              {/* Scientific Non-Causation Disclaimer Box */}
              <div className="bg-amber-950/20 border border-amber-500/30 p-3 rounded-xl text-xs text-amber-200 space-y-1">
                <div className="font-semibold flex items-center gap-1.5 text-amber-300">
                  <ShieldAlert className="w-4 h-4 shrink-0 text-amber-400" />
                  <span>Scientific Spatial Context Notice</span>
                </div>
                <p className="text-[11px] text-amber-200/80 leading-relaxed">
                  Proximity of thermal observations to this facility represents spatial context for monitoring. ThermalTrace does NOT claim this facility caused any detected thermal anomaly. OpenStreetMap industrial infrastructure provides corroborating geospatial evidence and is not treated as ground truth.
                </p>
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  onClick={() => handleViewOnMap(selectedFacility)}
                  className="px-4 py-2 bg-[#2D7DD2] hover:bg-[#2D7DD2]/90 text-white rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-colors"
                >
                  <MapPin className="w-4 h-4" />
                  <span>View on Map</span>
                </button>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
