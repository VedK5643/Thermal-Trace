import type { Incident } from '../types/incident';

export function downloadIncidentsCsv(incidents: Incident[], filename: string) {
  // Define CSV headers
  const headers = [
    'ID',
    'Date',
    'Time',
    'Type',
    'Location (Lat)',
    'Location (Lon)',
    'Facility',
    'Brightness (K)',
    'Confidence (%)',
    'Severity',
    'Status',
  ];

  // Map incident data to rows
  const rows = incidents.map((inc) => {
    const d = new Date(inc.timestamp);
    const dateStr = d.toISOString().split('T')[0];
    const timeStr = d.toISOString().split('T')[1].slice(0, 5) + ' UTC';

    const escapeCsv = (val: string | number | null) => {
      if (val === null || val === undefined) return '""';
      const str = String(val);
      if (str.includes(',') || str.includes('"') || str.includes('\n')) {
        return `"${str.replace(/"/g, '""')}"`;
      }
      return str;
    };

    return [
      escapeCsv(inc.id),
      escapeCsv(dateStr),
      escapeCsv(timeStr),
      escapeCsv(inc.mlType || inc.type),
      escapeCsv(inc.latitude),
      escapeCsv(inc.longitude),
      escapeCsv(inc.facilityName),
      escapeCsv(inc.brightness),
      escapeCsv(inc.confidence),
      escapeCsv(inc.severity),
      escapeCsv(inc.status),
    ].join(',');
  });

  const csvContent = [headers.join(','), ...rows].join('\n');
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  
  // Create download link and trigger
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.setAttribute('href', url);
  link.setAttribute('download', filename);
  link.style.visibility = 'hidden';
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}
