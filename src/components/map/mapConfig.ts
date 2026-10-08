import L from 'leaflet';
import { CrimeType, Severity, GeoCaseStatus } from '../../types';

// Central color/label registry for crime types, shared by markers, the
// legend, and the filter dropdown so they never drift out of sync.
export const CRIME_TYPE_CONFIG: Record<CrimeType, { color: string; label: string }> = {
  'Murder': { color: '#f43f5e', label: 'Murder' },          // danger
  'Robbery': { color: '#f59e0b', label: 'Robbery' },        // warning
  'Theft': { color: '#eab308', label: 'Theft' },            // yellow
  'Cybercrime': { color: '#0ea5e9', label: 'Cybercrime' },  // primary
  'Missing Person': { color: '#8b5cf6', label: 'Missing Person' }, // accent
  'Fraud': { color: '#ec4899', label: 'Fraud' },            // pink
  'Other': { color: '#94a3b8', label: 'Other' },            // text-muted
};

export const STATUS_OPTIONS: (GeoCaseStatus | 'All')[] = ['All', 'Active', 'Investigating', 'Solved', 'Closed'];
export const CRIME_TYPE_OPTIONS: (CrimeType | 'All')[] = ['All', 'Murder', 'Theft', 'Robbery', 'Cybercrime', 'Missing Person', 'Fraud', 'Other'];
export const SEVERITY_OPTIONS: (Severity | 'All')[] = ['All', 'Low', 'Medium', 'High', 'Critical'];

export const STATUS_BADGE_CLASSES: Record<GeoCaseStatus, string> = {
  Active: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
  Investigating: 'bg-primary/10 text-primary border-primary/20',
  Solved: 'bg-success/10 text-success border-success/20',
  Closed: 'bg-surface-hover text-text-muted border-border',
};

export const SEVERITY_BADGE_CLASSES: Record<Severity, string> = {
  Low: 'bg-success/10 text-success border-success/20',
  Medium: 'bg-warning/10 text-warning border-warning/20',
  High: 'bg-orange-500/10 text-orange-400 border-orange-500/20',
  Critical: 'bg-danger/10 text-danger border-danger/20',
};

// Individual case marker — a colored dot in the Evidentia style (matches
// the pin treatment already used in CaseMap.tsx), with a pulse ring for
// Critical severity to draw the investigator's eye.
export function createCaseIcon(crimeType: CrimeType, severity: Severity, isSelected = false): L.DivIcon {
  const color = CRIME_TYPE_CONFIG[crimeType]?.color ?? CRIME_TYPE_CONFIG.Other.color;
  const pulse = severity === 'Critical'
    ? `<span style="position:absolute;inset:-8px;border-radius:9999px;background:${color}33;animation:evidentia-pulse 1.8s ease-out infinite;"></span>`
    : '';
  const ring = isSelected ? `box-shadow:0 0 0 3px ${color}55,0 2px 6px rgba(0,0,0,0.5);` : 'box-shadow:0 2px 6px rgba(0,0,0,0.5);';

  return L.divIcon({
    className: 'evidentia-case-marker',
    html: `
      <div style="position:relative;width:16px;height:16px;">
        ${pulse}
        <div style="width:16px;height:16px;border-radius:9999px;background:${color};border:2px solid #f8fafc;${ring}"></div>
      </div>
    `,
    iconSize: [16, 16],
    iconAnchor: [8, 8],
    popupAnchor: [0, -10],
  });
}

// Cluster marker — a numbered badge sized loosely by count, styled to
// match Evidentia's primary/glass aesthetic rather than a generic gray blob.
export function createClusterIcon(count: number): L.DivIcon {
  const size = count < 10 ? 34 : count < 25 ? 40 : 48;
  return L.divIcon({
    className: 'evidentia-cluster-marker',
    html: `
      <div style="
        width:${size}px;height:${size}px;border-radius:9999px;
        background:rgba(14,165,233,0.18);
        border:2px solid #0ea5e9;
        display:flex;align-items:center;justify-content:center;
        color:#f8fafc;font-weight:700;font-size:${count < 100 ? 13 : 11}px;
        box-shadow:0 2px 10px rgba(0,0,0,0.5), 0 0 0 4px rgba(14,165,233,0.08);
        backdrop-filter:blur(4px);
      ">${count}</div>
    `,
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
  });
}
