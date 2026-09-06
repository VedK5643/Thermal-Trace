import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import Navbar from '../components/Navbar';
import api from '../services/api';
import {
  BarChart3,
  TrendingUp,
  Layers,
  MapPin,
  Bot,
  Filter,
  Calendar,
  Activity,
  Flame,
  PieChart,
  Info,
  CheckCircle2
} from 'lucide-react';

interface SummaryData {
  totalObservations: number;
  classificationDistribution: Record<string, number>;
  severityDistribution: Record<string, number>;
  industrialSourcePercentage: number;
  highFrpEvents: number;
  anomalousEvents: number;
  persistentEvents: number;
  highCriticalAlerts: number;
  modelVersion: string;
  benchmarkDisclosure: string;
}

interface RegionalItem {
  state: string;
  totalObservations: number;
  industrialObservations: number;
  miningObservations: number;
  naturalFires: number;
  persistentEvents: number;
}

interface TemporalItem {
  date: string;
  industrial_thermal_source: number;
  mining_thermal_source: number;
  natural_fire: number;
  unknown: number;
  total: number;
}

export default function AnalyticsPage(): React.JSX.Element {
  const navigate = useNavigate();
  const [summary, setSummary] = useState<SummaryData | null>(null);
  const [regionalData, setRegionalData] = useState<RegionalItem[]>([]);
  const [temporalData, setTemporalData] = useState<TemporalItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filter State
  const [selectedState, setSelectedState] = useState<string>('all');
  const [selectedClassification, setSelectedClassification] = useState<string>('all');
  const [selectedSeverity, setSelectedSeverity] = useState<string>('all');
  const [days, setDays] = useState<number>(7);

  useEffect(() => {
    fetchAnalytics();
  }, [selectedState, selectedClassification, selectedSeverity, days]);

  const fetchAnalytics = async () => {
    setLoading(true);
    setError(null);
    try {
      const params: Record<string, any> = { days };
      if (selectedState !== 'all') params.state = selectedState;
      if (selectedClassification !== 'all') params.classification = selectedClassification;
      if (selectedSeverity !== 'all') params.severity = selectedSeverity;

      const [sumRes, regRes, tempRes] = await Promise.all([
        api.get('/api/v1/analytics/summary', { params }),
        api.get('/api/v1/analytics/regional'),
        api.get('/api/v1/analytics/temporal', { params })
      ]);

      setSummary(sumRes.data);
      setRegionalData(regRes.data.states || []);
      setTemporalData(tempRes.data.series || []);
    } catch (err: any) {
      setError('Failed to fetch analytics from backend database.');
    } finally {
      setLoading(false);
    }
  };

  const handleViewOnMap = (stateFilter?: string, classFilter?: string) => {
    let url = '/?';
    if (stateFilter && stateFilter !== 'all') url += `state=${encodeURIComponent(stateFilter)}&`;
    if (classFilter && classFilter !== 'all') url += `classification=${encodeURIComponent(classFilter)}`;
    navigate(url);
  };

  const handleAskAI = () => {
    const promptText = `Analyze ThermalTrace activity: Total ${summary?.totalObservations || 0} observations, ${summary?.industrialSourcePercentage || 0}% predicted industrial sources, ${summary?.persistentEvents || 0} persistent events across India. Why is this period significant?`;
    window.dispatchEvent(new CustomEvent('ask-ai-hotspot', { detail: { hotspotId: promptText } }));
  };

  const classDist = summary?.classificationDistribution || {};
  const totalObs = summary?.totalObservations || 0;

  return (
    <div className="flex flex-col h-screen w-screen overflow-hidden bg-[#080C14] text-[#E8EDF5]">
      <Navbar />

      <main className="flex-1 w-full p-3 sm:p-6 overflow-y-auto max-w-7xl mx-auto space-y-4 sm:space-y-6">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 sm:gap-4 border-b border-[#1E2D45] pb-4 sm:pb-5">
          <div>
            <div className="flex items-center gap-2">
              <div className="p-2 bg-[#2D7DD2]/10 border border-[#2D7DD2]/30 rounded-lg text-[#2D7DD2]">
                <BarChart3 className="w-4 h-4 sm:w-5 sm:h-5" />
              </div>
              <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-[#E8EDF5]">
                Thermal Anomaly Analytics
              </h1>
            </div>
            <p className="text-xs text-[#7A8FA8] mt-1">
              Quantitative intelligence and time-series trend analysis generated dynamically from PostGIS thermal observations. Satellite imagery provides spatial context and geographic verification.
            </p>
          </div>

          <button
            onClick={handleAskAI}
            className="px-3.5 py-2 bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 border border-amber-500/30 rounded-xl text-xs font-semibold flex items-center gap-2 transition-colors w-fit"
          >
            <Bot className="w-4 h-4 text-amber-400" />
            <span>Ask AI About This Analysis</span>
          </button>
        </div>

        {/* Filter Bar */}
        <div className="bg-[#111827] border border-[#1E2D45] p-3 sm:p-4 rounded-xl flex flex-wrap gap-2.5 sm:gap-4 items-center justify-between shadow-xl">
          <div className="flex flex-wrap items-center gap-2.5 sm:gap-3 text-xs w-full sm:w-auto">
            <div className="flex items-center gap-1.5 text-[#7A8FA8] flex-1 sm:flex-initial">
              <Calendar className="w-4 h-4 text-[#2D7DD2] shrink-0" />
              <span className="hidden sm:inline">Time Window:</span>
              <select
                value={days}
                onChange={(e) => setDays(Number(e.target.value))}
                className="w-full sm:w-auto bg-[#080C14] border border-[#1E2D45] rounded-lg px-2.5 py-1.5 text-xs text-[#E8EDF5] focus:outline-none"
              >
                <option value={7}>Past 7 Days</option>
                <option value={14}>Past 14 Days</option>
                <option value={30}>Past 30 Days</option>
              </select>
            </div>

            <div className="flex items-center gap-1.5 text-[#7A8FA8] flex-1 sm:flex-initial">
              <Filter className="w-3.5 h-3.5 shrink-0" />
              <span className="hidden sm:inline">State:</span>
              <select
                value={selectedState}
                onChange={(e) => setSelectedState(e.target.value)}
                className="w-full sm:w-auto bg-[#080C14] border border-[#1E2D45] rounded-lg px-2.5 py-1.5 text-xs text-[#E8EDF5] focus:outline-none"
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

            <div className="flex items-center gap-1.5 text-[#7A8FA8] flex-1 sm:flex-initial">
              <span className="hidden sm:inline">Classification:</span>
              <select
                value={selectedClassification}
                onChange={(e) => setSelectedClassification(e.target.value)}
                className="w-full sm:w-auto bg-[#080C14] border border-[#1E2D45] rounded-lg px-2.5 py-1.5 text-xs text-[#E8EDF5] focus:outline-none"
              >
                <option value="all">All Classifications</option>
                <option value="industrial_thermal_source">Industrial Thermal Source</option>
                <option value="mining_thermal_source">Mining Thermal Source</option>
                <option value="natural_fire">Natural Fire</option>
                <option value="unknown">Unknown / Unclassified</option>
              </select>
            </div>

            <div className="flex items-center gap-1.5 text-[#7A8FA8] flex-1 sm:flex-initial">
              <span className="hidden sm:inline">Severity:</span>
              <select
                value={selectedSeverity}
                onChange={(e) => setSelectedSeverity(e.target.value)}
                className="w-full sm:w-auto bg-[#080C14] border border-[#1E2D45] rounded-lg px-2.5 py-1.5 text-xs text-[#E8EDF5] focus:outline-none"
              >
                <option value="all">All Severities</option>
                <option value="critical">Critical</option>
                <option value="high">High</option>
                <option value="medium">Medium</option>
                <option value="low">Low</option>
              </select>
            </div>
          </div>

          <button
            onClick={() => handleViewOnMap(selectedState, selectedClassification)}
            className="px-3 py-1.5 bg-[#2D7DD2]/20 hover:bg-[#2D7DD2]/30 text-[#2D7DD2] border border-[#2D7DD2]/30 rounded-lg text-xs font-medium flex items-center gap-1.5 transition-colors w-full sm:w-auto justify-center"
          >
            <MapPin className="w-3.5 h-3.5" />
            <span>Apply to Map</span>
          </button>
        </div>

        {/* Top Analytics Metrics */}
        {loading ? (
          <div className="p-12 text-center text-xs text-[#7A8FA8] flex flex-col items-center gap-2">
            <div className="w-6 h-6 border-2 border-[#2D7DD2] border-t-transparent rounded-full animate-spin"></div>
            <span>Calculating thermal telemetry metrics from PostgreSQL backend...</span>
          </div>
        ) : error ? (
          <div className="p-8 text-center text-xs text-red-400 bg-red-950/20">{error}</div>
        ) : (
          <>
            {/* Top KPI Cards Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
              <div className="bg-[#111827] border border-[#1E2D45] p-3.5 sm:p-4 rounded-xl space-y-1 shadow-lg">
                <div className="flex items-center justify-between text-[#7A8FA8]">
                  <span className="text-[10px] sm:text-[11px] font-bold uppercase tracking-wider">TOTAL OBSERVATIONS</span>
                  <Activity className="w-4 h-4 text-[#2D7DD2]" />
                </div>
                <div className="text-xl sm:text-2xl font-extrabold text-[#E8EDF5]">{totalObs.toLocaleString()}</div>
                <div className="text-[10px] text-[#7A8FA8]">FIRMS Satellite Detections</div>
              </div>

              <div className="bg-[#111827] border border-[#1E2D45] p-3.5 sm:p-4 rounded-xl space-y-1 shadow-lg">
                <div className="flex items-center justify-between text-[#7A8FA8]">
                  <span className="text-[10px] sm:text-[11px] font-bold uppercase tracking-wider">INDUSTRIAL THERMAL SOURCES</span>
                  <Flame className="w-4 h-4 text-red-400" />
                </div>
                <div className="text-xl sm:text-2xl font-extrabold text-red-400">
                  {summary?.industrialSourcePercentage || 0}%
                </div>
                <div className="text-[10px] text-[#7A8FA8]">
                  {summary?.classificationDistribution?.industrial_thermal_source || 0} Predicted Industrial Thermal Sources
                </div>
              </div>

              <div className="bg-[#111827] border border-[#1E2D45] p-3.5 sm:p-4 rounded-xl space-y-1 shadow-lg">
                <div className="flex items-center justify-between text-[#7A8FA8]">
                  <span className="text-[10px] sm:text-[11px] font-bold uppercase tracking-wider">PERSISTENT EVENTS</span>
                  <Flame className="w-4 h-4 text-amber-400" />
                </div>
                <div className="text-xl sm:text-2xl font-extrabold text-amber-400">
                  {summary?.persistentEvents || 0}
                </div>
                <div className="text-[10px] text-[#7A8FA8]">Multi-day Thermal Sources</div>
              </div>

              <div className="bg-[#111827] border border-[#1E2D45] p-3.5 sm:p-4 rounded-xl space-y-1 shadow-lg">
                <div className="flex items-center justify-between text-[#7A8FA8]">
                  <span className="text-[10px] sm:text-[11px] font-bold uppercase tracking-wider">ACTIVE STATES</span>
                  <Layers className="w-4 h-4 text-emerald-400" />
                </div>
                <div className="text-xl sm:text-2xl font-extrabold text-emerald-400">
                  {regionalData.length || 0}
                </div>
                <div className="text-[10px] text-[#7A8FA8]">India Regions Covered</div>
              </div>
            </div>

            {/* Classification Breakdown & Model Metric Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 sm:gap-6">
              {/* Classification Distribution */}
              <div className="lg:col-span-2 bg-[#111827] border border-[#1E2D45] p-4 sm:p-5 rounded-xl space-y-4 shadow-xl">
                <div className="flex items-center justify-between border-b border-[#1E2D45] pb-3">
                  <h3 className="font-bold text-xs sm:text-sm text-[#E8EDF5] flex items-center gap-2">
                    <PieChart className="w-4 h-4 text-[#2D7DD2]" />
                    ML Model Classification Distribution
                  </h3>
                  <span className="text-[10px] font-mono text-[#7A8FA8]">thermalwatch-v1</span>
                </div>

                <div className="space-y-3">
                  {[
                    { key: 'industrial_thermal_source', label: 'Industrial Thermal Source', color: 'bg-red-500' },
                    { key: 'mining_thermal_source', label: 'Mining Thermal Source', color: 'bg-amber-400' },
                    { key: 'natural_fire', label: 'Natural Fire', color: 'bg-emerald-400' },
                    { key: 'unknown', label: 'Unknown / Unclassified', color: 'bg-slate-500' },
                  ].map((item) => {
                    const count = classDist[item.key as keyof typeof classDist] || 0;
                    const pct = totalObs > 0 ? ((count / totalObs) * 100).toFixed(1) : '0';
                    return (
                      <div key={item.key} className="space-y-1">
                        <div className="flex justify-between text-xs">
                          <span className="font-medium text-[#E8EDF5] flex items-center gap-2">
                            <span className={`w-2.5 h-2.5 rounded-full ${item.color}`} />
                            {item.label}
                          </span>
                          <span className="font-mono text-[#7A8FA8]">
                            {count.toLocaleString()} ({pct}%)
                          </span>
                        </div>
                        <div className="w-full h-2 bg-[#080C14] rounded-full overflow-hidden">
                          <div
                            className={`h-full ${item.color} transition-all duration-500`}
                            style={{ width: `${pct}%` }}
                          />
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

            {/* Problem Statement Category Coverage Table */}
            <div className="bg-[#111827] border border-[#1E2D45] p-4 sm:p-5 rounded-xl space-y-3 shadow-xl">
              <div className="flex items-center justify-between border-b border-[#1E2D45] pb-3">
                <h3 className="font-bold text-xs sm:text-sm text-[#E8EDF5] flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-[#38BDF8]" />
                  Problem Statement Fire Category Coverage Matrix
                </h3>
                <span className="text-[10px] font-mono font-bold text-[#38BDF8] bg-[#0284C7]/15 border border-[#0284C7]/30 px-2 py-0.5 rounded">
                  Validated Mapping
                </span>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs text-[#94A3B8]">
                  <thead className="bg-[#080C14] text-[10px] text-[#7A8FA8] uppercase font-mono">
                    <tr>
                      <th className="p-2">PS Target Category</th>
                      <th className="p-2">Model Classification</th>
                      <th className="p-2">Coverage Status</th>
                      <th className="p-2 hidden md:table-cell">Technical Evidence Basis</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#1E2D45]/60 text-[11px]">
                    <tr>
                      <td className="p-2 text-[#E8EDF5] font-medium">Industrial Fires / Process Heat</td>
                      <td className="p-2 font-mono text-red-400">industrial_thermal_source</td>
                      <td className="p-2"><span className="px-1.5 py-0.5 rounded text-[9px] font-bold bg-emerald-950/60 text-emerald-400 border border-emerald-500/30">CLASSIFIED</span></td>
                      <td className="p-2 hidden md:table-cell text-[10px] text-[#64748B]">Persistence ≥ 9 mo/yr incl. monsoon & OSM industrial proximity ≤ 2km</td>
                    </tr>
                    <tr>
                      <td className="p-2 text-[#E8EDF5] font-medium">Gas Flares</td>
                      <td className="p-2 font-mono text-red-400">industrial_thermal_source</td>
                      <td className="p-2"><span className="px-1.5 py-0.5 rounded text-[9px] font-bold bg-sky-950/60 text-sky-400 border border-sky-500/30">GROUPED</span></td>
                      <td className="p-2 hidden md:table-cell text-[10px] text-[#64748B]">Persistent flaring stacks at oil refineries & petrochemical complexes</td>
                    </tr>
                    <tr>
                      <td className="p-2 text-[#E8EDF5] font-medium">Mining Activity</td>
                      <td className="p-2 font-mono text-amber-400">mining_thermal_source</td>
                      <td className="p-2"><span className="px-1.5 py-0.5 rounded text-[9px] font-bold bg-emerald-950/60 text-emerald-400 border border-emerald-500/30">CLASSIFIED</span></td>
                      <td className="p-2 hidden md:table-cell text-[10px] text-[#64748B]">Persistence & OSM landuse_quarry proximity ≤ 2km</td>
                    </tr>
                    <tr>
                      <td className="p-2 text-[#E8EDF5] font-medium">Agricultural Burning</td>
                      <td className="p-2 font-mono text-emerald-400">natural_fire</td>
                      <td className="p-2"><span className="px-1.5 py-0.5 rounded text-[9px] font-bold bg-sky-950/60 text-sky-400 border border-sky-500/30">GROUPED</span></td>
                      <td className="p-2 hidden md:table-cell text-[10px] text-[#64748B]">Seasonal stubble burning in crop zones (active ≤ 3 mo/yr)</td>
                    </tr>
                    <tr>
                      <td className="p-2 text-[#E8EDF5] font-medium">Wildfire / Forest Fire</td>
                      <td className="p-2 font-mono text-emerald-400">natural_fire</td>
                      <td className="p-2"><span className="px-1.5 py-0.5 rounded text-[9px] font-bold bg-sky-950/60 text-sky-400 border border-sky-500/30">GROUPED</span></td>
                      <td className="p-2 hidden md:table-cell text-[10px] text-[#64748B]">Seasonal open vegetation fires in forested/woodland regions</td>
                    </tr>
                    <tr>
                      <td className="p-2 text-[#E8EDF5] font-medium">Other Natural Fires</td>
                      <td className="p-2 font-mono text-emerald-400">natural_fire</td>
                      <td className="p-2"><span className="px-1.5 py-0.5 rounded text-[9px] font-bold bg-sky-950/60 text-sky-400 border border-sky-500/30">GROUPED</span></td>
                      <td className="p-2 hidden md:table-cell text-[10px] text-[#64748B]">Seasonal fires across grasslands, shrublands & non-crop areas</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>

              {/* Model Information Card */}
              <div className="bg-[#111827] border border-[#1E2D45] p-4 sm:p-5 rounded-xl space-y-4 shadow-xl flex flex-col justify-between">
                <div>
                  <h3 className="font-bold text-xs sm:text-sm text-[#E8EDF5] flex items-center gap-2 border-b border-[#1E2D45] pb-3 mb-3">
                    <Info className="w-4 h-4 text-[#2D7DD2]" />
                    Model Metadata & Notice
                  </h3>

                  <div className="space-y-2 text-xs text-[#7A8FA8]">
                    <div className="bg-[#080C14] p-3 rounded-lg border border-[#1E2D45]">
                      <span className="text-[10px] uppercase font-bold text-[#7A8FA8] block">Benchmark Metric</span>
                      <span className="text-sm font-bold text-emerald-400 mt-0.5 block">93.70% Accuracy</span>
                      <span className="text-[11px] text-[#7A8FA8] mt-1 block">Synthetic Engineering Benchmark (`thermaltrace-ml-1m-v2`)</span>
                    </div>

                    <div className="bg-amber-950/20 border border-amber-500/20 p-3 rounded-lg text-amber-200/90 text-[11px] leading-relaxed">
                      <strong className="text-amber-300 block mb-0.5">Important Notice:</strong>
                      The 93.70% benchmark was evaluated on synthetic rule-generated data. Real-world ground-truth validation is NOT established. OpenStreetMap industrial infrastructure provides corroborating geospatial evidence and is not treated as ground truth. ThermalTrace ML provides probabilistic model predictions.
                    </div>
                  </div>
                </div></div>
            </div>

            {/* Temporal Series Breakdown Section */}
            {temporalData.length > 0 && (
              <div className="bg-[#111827] border border-[#1E2D45] p-4 sm:p-5 rounded-xl space-y-3 shadow-xl">
                <h3 className="font-bold text-xs sm:text-sm text-[#E8EDF5] flex items-center gap-2 border-b border-[#1E2D45] pb-3">
                  <Activity className="w-4 h-4 text-[#2D7DD2]" />
                  <span>Daily Time-Series Trend Breakdown</span>
                </h3>
                <div className="overflow-x-auto custom-scrollbar">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-[#162033] text-[#7A8FA8] uppercase font-bold text-[10px] whitespace-nowrap">
                      <tr>
                        <th className="px-3 py-2">Date</th>
                        <th className="px-3 py-2">Industrial Thermal Source</th>
                        <th className="px-3 py-2">Mining Thermal Source</th>
                        <th className="px-3 py-2">Natural Fire</th>
                        <th className="px-3 py-2">Unknown / Unclassified</th>
                        <th className="px-3 py-2 text-right">Daily Total</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[#1E2D45]/60 text-[#E8EDF5]">
                      {temporalData.map((row, i) => (
                        <tr key={i} className="hover:bg-[#162033]/40">
                          <td className="px-3 py-2 font-mono text-[#2D7DD2] whitespace-nowrap">{row.date}</td>
                          <td className="px-3 py-2 font-mono text-red-400 font-bold whitespace-nowrap">{row.industrial_thermal_source}</td>
                          <td className="px-3 py-2 font-mono text-amber-400 whitespace-nowrap">{row.mining_thermal_source}</td>
                          <td className="px-3 py-2 font-mono text-emerald-400 whitespace-nowrap">{row.natural_fire}</td>
                          <td className="px-3 py-2 font-mono text-[#7A8FA8] whitespace-nowrap">{row.unknown}</td>
                          <td className="px-3 py-2 font-mono text-right font-bold whitespace-nowrap">{row.total}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
            <div className="bg-[#111827] border border-[#1E2D45] rounded-xl overflow-hidden shadow-2xl p-4 sm:p-5 space-y-4">
              <div className="flex items-center justify-between border-b border-[#1E2D45] pb-3">
                <h3 className="font-bold text-xs sm:text-sm text-[#E8EDF5] flex items-center gap-2">
                  <TrendingUp className="w-4 h-4 text-[#2D7DD2]" />
                  <span>Regional Activity Ranking Across India</span>
                </h3>
                <span className="text-xs text-[#7A8FA8]">{regionalData.length} States Monitored</span>
              </div>

              <div className="overflow-x-auto custom-scrollbar">
                <table className="w-full text-left text-xs">
                  <thead className="bg-[#162033] text-[#7A8FA8] uppercase font-bold tracking-wider text-[10px] whitespace-nowrap">
                    <tr>
                      <th className="px-3 sm:px-4 py-3">State / Region</th>
                      <th className="px-3 sm:px-4 py-3">Total Observations</th>
                      <th className="px-3 sm:px-4 py-3">Industrial Thermal Sources</th>
                      <th className="px-3 sm:px-4 py-3">Mining Thermal Sources</th>
                      <th className="px-3 sm:px-4 py-3">Natural Fires</th>
                      <th className="px-3 sm:px-4 py-3">Persistent Events</th>
                      <th className="px-3 sm:px-4 py-3 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#1E2D45]/60 text-[#E8EDF5]">
                    {regionalData.map((row, i) => (
                      <tr key={i} className="hover:bg-[#162033]/40 transition-colors">
                        <td className="px-3 sm:px-4 py-3 font-semibold text-[#E8EDF5] whitespace-nowrap">{row.state}</td>
                        <td className="px-3 sm:px-4 py-3 font-mono whitespace-nowrap">{row.totalObservations}</td>
                        <td className="px-3 sm:px-4 py-3 font-mono text-red-400 font-bold whitespace-nowrap">{row.industrialObservations}</td>
                        <td className="px-3 sm:px-4 py-3 font-mono text-amber-400 whitespace-nowrap">{row.miningObservations}</td>
                        <td className="px-3 sm:px-4 py-3 font-mono text-emerald-400 whitespace-nowrap">{row.naturalFires}</td>
                        <td className="px-3 sm:px-4 py-3 font-mono text-orange-400 whitespace-nowrap">{row.persistentEvents}</td>
                        <td className="px-3 sm:px-4 py-3 text-right whitespace-nowrap">
                          <button
                            onClick={() => handleViewOnMap(row.state)}
                            className="px-2.5 py-1 bg-[#2D7DD2]/20 hover:bg-[#2D7DD2]/30 text-[#2D7DD2] rounded text-[11px] font-medium transition-colors"
                          >
                            View on Map
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </>
        )}
      </main>
    </div>
  );
}
