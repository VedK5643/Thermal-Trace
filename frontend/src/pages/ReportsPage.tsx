import React, { useState } from 'react';
import Navbar from '../components/Navbar';
import api from '../services/api';
import {
  FileText,
  Filter,
  Bot,
  ShieldAlert,
  FileJson,
  FileSpreadsheet
} from 'lucide-react';

interface ReportData {
  reportMetadata: {
    title: string;
    generatedAt: string;
    scope: string;
    appliedFilters: Record<string, any>;
  };
  executiveSummary: {
    totalObservations: number;
    predictedIndustrialThermalSources: number;
    predictedMiningThermalSources: number;
    predictedNaturalFires: number;
    unknownObservations: number;
    persistentThermalEvents: number;
    highFrpEvents: number;
    totalActiveAlerts: number;
  };
  thermalActivityBreakdown: {
    classificationDistribution: Record<string, number>;
    alertSeverityBreakdown: Record<string, number>;
  };
  scientificDisclosures: {
    satelliteSource: string;
    modelInformation: string;
    benchmarkAccuracy: string;
    nonCausationNotice: string;
  };
  incidentRecords: Array<{
    id: string;
    latitude: number;
    longitude: number;
    timestamp: string;
    predictedClassification: string;
    mlConfidence: number;
    frpMw: number | null;
    severity: string;
    facilityDistanceKm: number | null;
  }>;
}

export default function ReportsPage(): React.JSX.Element {
  // Filter Form State
  const [selectedState, setSelectedState] = useState<string>('all');
  const [selectedClassification, setSelectedClassification] = useState<string>('all');
  const [selectedSeverity, setSelectedSeverity] = useState<string>('all');
  const [loading, setLoading] = useState(false);
  const [report, setReport] = useState<ReportData | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleGenerateReport = async () => {
    setLoading(true);
    setError(null);
    try {
      const payload: Record<string, any> = { format: 'json' };
      if (selectedState !== 'all') payload.state = selectedState;
      if (selectedClassification !== 'all') payload.classification = selectedClassification;
      if (selectedSeverity !== 'all') payload.severity = selectedSeverity;

      const res = await api.post('/api/v1/reports/generate', payload);
      setReport(res.data);
    } catch (err: any) {
      setError('Failed to generate report from backend service.');
    } finally {
      setLoading(false);
    }
  };

  const handleDownloadCSV = async () => {
    try {
      const payload: Record<string, any> = { format: 'csv' };
      if (selectedState !== 'all') payload.state = selectedState;
      if (selectedClassification !== 'all') payload.classification = selectedClassification;
      if (selectedSeverity !== 'all') payload.severity = selectedSeverity;

      const res = await api.post('/api/v1/reports/generate', payload, { responseType: 'blob' });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `thermaltrace_report_${selectedState}_${Date.now()}.csv`);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (err) {
      alert('Failed to download CSV report.');
    }
  };

  const handleDownloadJSON = () => {
    if (!report) return;
    const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `thermaltrace_report_${Date.now()}.json`);
    document.body.appendChild(link);
    link.click();
    link.remove();
  };

  const handleAskAIReport = () => {
    if (!report) return;
    window.dispatchEvent(new CustomEvent('ask-ai-hotspot', { detail: { hotspotId: 'Generated Intelligence Report' } }));
  };

  return (
    <div className="flex flex-col h-screen w-screen overflow-hidden bg-[#080C14] text-[#E8EDF5]">
      <Navbar />

      <main className="flex-1 w-full p-3 sm:p-6 overflow-y-auto max-w-7xl mx-auto space-y-4 sm:space-y-6">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 sm:gap-4 border-b border-[#1E2D45] pb-4 sm:pb-5">
          <div>
            <div className="flex items-center gap-2">
              <div className="p-2 bg-[#2D7DD2]/10 border border-[#2D7DD2]/30 rounded-lg text-[#2D7DD2]">
                <FileText className="w-4 h-4 sm:w-5 sm:h-5" />
              </div>
              <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-[#E8EDF5]">
                Intelligence Report Generator
              </h1>
            </div>
            <p className="text-xs text-[#7A8FA8] mt-1">
              Generate structured, human-readable thermal anomaly incident reports backed by real PostgreSQL/PostGIS backend telemetry.
            </p>
          </div>
        </div>

        {/* Configuration Form Bar */}
        <div className="bg-[#111827] border border-[#1E2D45] p-4 sm:p-5 rounded-xl space-y-4 shadow-xl">
          <h3 className="text-xs sm:text-sm font-bold text-[#E8EDF5] flex items-center gap-2">
            <Filter className="w-4 h-4 text-[#2D7DD2]" />
            <span>Configure Report Parameters</span>
          </h3>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
            <div>
              <label className="text-[10px] font-bold text-[#7A8FA8] uppercase block mb-1">State / Scope</label>
              <select
                value={selectedState}
                onChange={(e) => setSelectedState(e.target.value)}
                className="w-full bg-[#080C14] border border-[#1E2D45] rounded-lg px-3 py-2 text-xs text-[#E8EDF5] focus:outline-none"
              >
                <option value="all">All India</option>
                <option value="Gujarat">Gujarat</option>
                <option value="Maharashtra">Maharashtra</option>
                <option value="Karnataka">Karnataka</option>
                <option value="Tamil Nadu">Tamil Nadu</option>
                <option value="Odisha">Odisha</option>
                <option value="West Bengal">West Bengal</option>
              </select>
            </div>

            <div>
              <label className="text-[10px] font-bold text-[#7A8FA8] uppercase block mb-1">ML Classification</label>
              <select
                value={selectedClassification}
                onChange={(e) => setSelectedClassification(e.target.value)}
                className="w-full bg-[#080C14] border border-[#1E2D45] rounded-lg px-3 py-2 text-xs text-[#E8EDF5] focus:outline-none"
              >
                <option value="all">All Classifications</option>
                <option value="industrial_thermal_source">Industrial Thermal Source</option>
                <option value="mining_thermal_source">Mining Thermal Source</option>
                <option value="natural_fire">Natural Fire</option>
                <option value="unknown">Unknown / Unclassified</option>
              </select>
            </div>

            <div>
              <label className="text-[10px] font-bold text-[#7A8FA8] uppercase block mb-1">Severity Filter</label>
              <select
                value={selectedSeverity}
                onChange={(e) => setSelectedSeverity(e.target.value)}
                className="w-full bg-[#080C14] border border-[#1E2D45] rounded-lg px-3 py-2 text-xs text-[#E8EDF5] focus:outline-none"
              >
                <option value="all">All Severities</option>
                <option value="critical">Critical</option>
                <option value="high">High</option>
                <option value="medium">Medium</option>
                <option value="low">Low</option>
              </select>
            </div>

            <div className="flex items-end">
              <button
                onClick={handleGenerateReport}
                disabled={loading}
                className="w-full py-2 bg-[#2D7DD2] hover:bg-[#2D7DD2]/90 disabled:opacity-50 text-white rounded-lg text-xs font-semibold flex items-center justify-center gap-1.5 transition-colors shadow-lg"
              >
                {loading ? <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" /> : <FileText className="w-4 h-4" />}
                <span>Generate Intelligence Report</span>
              </button>
            </div>
          </div>
        </div>

        {/* Rendered Report Document View */}
        {error ? (
          <div className="p-8 text-center text-xs text-red-400 bg-red-950/20 border border-red-500/20 rounded-xl">{error}</div>
        ) : report ? (
          <div className="bg-[#111827] border border-[#1E2D45] rounded-2xl p-4 sm:p-6 space-y-4 sm:space-y-6 shadow-2xl">
            {/* Report Header & Action Bar */}
            <div className="flex flex-col md:flex-row md:items-center justify-between border-b border-[#1E2D45] pb-4 gap-4">
              <div>
                <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded bg-[#2D7DD2]/10 text-[#2D7DD2] border border-[#2D7DD2]/30 text-[10px] font-bold uppercase tracking-wider mb-1">
                  Official ThermalTrace Incident Report
                </div>
                <h2 className="text-lg sm:text-xl font-bold text-[#E8EDF5]">{report.reportMetadata.title}</h2>
                <div className="text-xs text-[#7A8FA8] mt-0.5">
                  Scope: <strong className="text-[#E8EDF5]">{report.reportMetadata.scope}</strong> | Generated: {new Date(report.reportMetadata.generatedAt).toLocaleString()}
                </div>
              </div>

              <div className="flex flex-wrap items-center gap-2">
                <button
                  onClick={handleDownloadJSON}
                  className="px-3 py-1.5 bg-[#162033] hover:bg-[#1E2D45] text-[#E8EDF5] border border-[#1E2D45] rounded-lg text-xs font-medium flex items-center gap-1.5 transition-colors"
                >
                  <FileJson className="w-4 h-4 text-emerald-400" />
                  <span>JSON</span>
                </button>
                <button
                  onClick={handleDownloadCSV}
                  className="px-3 py-1.5 bg-[#162033] hover:bg-[#1E2D45] text-[#E8EDF5] border border-[#1E2D45] rounded-lg text-xs font-medium flex items-center gap-1.5 transition-colors"
                >
                  <FileSpreadsheet className="w-4 h-4 text-[#2D7DD2]" />
                  <span>CSV</span>
                </button>
                <button
                  onClick={handleAskAIReport}
                  className="px-3 py-1.5 bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 border border-amber-500/30 rounded-lg text-xs font-medium flex items-center gap-1.5 transition-colors"
                >
                  <Bot className="w-4 h-4 text-amber-400" />
                  <span>Analyze with AI</span>
                </button>
              </div>
            </div>

            {/* Executive Summary Grid */}
            <div className="space-y-2">
              <h3 className="text-xs font-bold uppercase tracking-wider text-[#7A8FA8]">1. Executive Summary</h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2.5 sm:gap-3">
                <div className="bg-[#080C14] border border-[#1E2D45] p-3 sm:p-3.5 rounded-xl">
                  <span className="text-[10px] text-[#7A8FA8] uppercase font-bold block">Total Observations</span>
                  <span className="text-lg sm:text-xl font-extrabold text-[#E8EDF5] mt-0.5 block">{report.executiveSummary.totalObservations}</span>
                </div>
                <div className="bg-[#080C14] border border-[#1E2D45] p-3 sm:p-3.5 rounded-xl">
                  <span className="text-[10px] text-[#7A8FA8] uppercase font-bold block">Predicted Industrial Thermal Sources</span>
                  <span className="text-lg sm:text-xl font-extrabold text-red-400 mt-0.5 block">{report.executiveSummary.predictedIndustrialThermalSources}</span>
                </div>
                <div className="bg-[#080C14] border border-[#1E2D45] p-3 sm:p-3.5 rounded-xl">
                  <span className="text-[10px] text-[#7A8FA8] uppercase font-bold block">Mining Thermal Sources</span>
                  <span className="text-lg sm:text-xl font-extrabold text-amber-400 mt-0.5 block">{report.executiveSummary.predictedMiningThermalSources}</span>
                </div>
                <div className="bg-[#080C14] border border-[#1E2D45] p-3 sm:p-3.5 rounded-xl">
                  <span className="text-[10px] text-[#7A8FA8] uppercase font-bold block">Persistent Events</span>
                  <span className="text-lg sm:text-xl font-extrabold text-orange-400 mt-0.5 block">{report.executiveSummary.persistentThermalEvents}</span>
                </div>
              </div>
            </div>

            {/* Incident Records Table */}
            <div className="space-y-2">
              <h3 className="text-xs font-bold uppercase tracking-wider text-[#7A8FA8]">2. Sample Incident Telemetry</h3>
              <div className="overflow-x-auto border border-[#1E2D45] rounded-xl custom-scrollbar">
                <table className="w-full text-left text-xs">
                  <thead className="bg-[#162033] text-[#7A8FA8] uppercase font-bold text-[10px] whitespace-nowrap">
                    <tr>
                      <th className="px-3 sm:px-4 py-2.5">ID</th>
                      <th className="px-3 sm:px-4 py-2.5">Location</th>
                      <th className="px-3 sm:px-4 py-2.5">ML Prediction</th>
                      <th className="px-3 sm:px-4 py-2.5">Confidence</th>
                      <th className="px-3 sm:px-4 py-2.5">Severity</th>
                      <th className="px-3 sm:px-4 py-2.5">Facility Dist</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#1E2D45]/60 text-[#E8EDF5]">
                    {report.incidentRecords.slice(0, 10).map((inc) => (
                      <tr key={inc.id} className="hover:bg-[#162033]/40">
                        <td className="px-3 sm:px-4 py-2.5 font-mono text-[11px] text-[#2D7DD2] whitespace-nowrap">{inc.id}</td>
                        <td className="px-3 sm:px-4 py-2.5 font-mono text-[11px] text-[#7A8FA8] whitespace-nowrap">{inc.latitude.toFixed(3)}°, {inc.longitude.toFixed(3)}°</td>
                        <td className="px-3 sm:px-4 py-2.5 capitalize whitespace-nowrap">{inc.predictedClassification.replace('_', ' ')}</td>
                        <td className="px-3 sm:px-4 py-2.5 font-mono whitespace-nowrap">{(inc.mlConfidence * 100).toFixed(0)}%</td>
                        <td className="px-3 sm:px-4 py-2.5 capitalize whitespace-nowrap">{inc.severity}</td>
                        <td className="px-3 sm:px-4 py-2.5 font-mono text-[#7A8FA8] whitespace-nowrap">{inc.facilityDistanceKm ? `${inc.facilityDistanceKm.toFixed(1)} km` : 'N/A'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Mandatory Scientific Disclosure Box */}
            <div className="bg-[#080C14] border border-[#1E2D45] p-4 rounded-xl space-y-2 text-xs">
              <div className="font-bold text-[#E8EDF5] flex items-center gap-1.5">
                <ShieldAlert className="w-4 h-4 text-[#2D7DD2]" />
                <span>Mandatory Scientific Disclosures</span>
              </div>
              <ul className="list-disc list-inside text-[#7A8FA8] text-[11px] space-y-1">
                <li>Telemetry source: {report.scientificDisclosures.satelliteSource}</li>
                <li>Model Information: {report.scientificDisclosures.modelInformation}</li>
                <li>Problem Statement Taxonomy Mapping: Industrial Fires / Gas Flares map to industrial_thermal_source; Mining Activity maps to mining_thermal_source; Agricultural Burning, Wildfires, Forest Fires & Natural Fires map to natural_fire.</li>
                <li>Benchmark Accuracy: {report.scientificDisclosures.benchmarkAccuracy}</li>
                <li>Proximity Notice: {report.scientificDisclosures.nonCausationNotice}</li>
              </ul>
            </div>
          </div>
        ) : (
          <div className="bg-[#111827] border border-[#1E2D45] rounded-2xl p-12 text-center text-xs text-[#7A8FA8] space-y-2 shadow-2xl">
            <FileText className="w-8 h-8 text-[#2D7DD2] mx-auto opacity-80" />
            <p className="text-sm font-semibold text-[#E8EDF5]">No report generated yet.</p>
            <p>Configure parameters above and click "Generate Intelligence Report" to compile real backend telemetry into an operational report.</p>
          </div>
        )}
      </main>
    </div>
  );
}
