import { Search } from 'lucide-react';
import { GeoCaseStatus, CrimeType, Severity } from '../../types';
import { STATUS_OPTIONS, CRIME_TYPE_OPTIONS, SEVERITY_OPTIONS } from './mapConfig';

export interface MapFilterState {
  search: string;
  status: GeoCaseStatus | 'All';
  crimeType: CrimeType | 'All';
  severity: Severity | 'All';
}

interface MapFiltersProps {
  filters: MapFilterState;
  onChange: (filters: MapFilterState) => void;
  totalCount?: number;
  filteredCount?: number;
}

const selectClasses = "bg-surface border border-border rounded-lg pl-3 pr-8 py-2 text-xs font-medium text-text-muted hover:text-white focus:outline-none focus:border-primary/50 transition-colors appearance-none cursor-pointer";

export function MapFilters({ filters, onChange }: MapFiltersProps) {
  return (
    <div className="flex flex-col sm:flex-row flex-wrap gap-2 items-stretch sm:items-center">
      <div className="relative flex-1 min-w-[160px]">
        <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-text-muted" />
        <input
          type="text"
          value={filters.search}
          onChange={(e) => onChange({ ...filters, search: e.target.value })}
          placeholder="Search cases..."
          className="w-full pl-8 pr-3 py-2 bg-surface border border-border rounded-lg text-xs focus:outline-none focus:border-primary/50 text-white transition-colors"
        />
      </div>

      <select
        value={filters.status}
        onChange={(e) => onChange({ ...filters, status: e.target.value as MapFilterState['status'] })}
        className={selectClasses}
      >
        {STATUS_OPTIONS.map(s => <option key={s} value={s}>{s === 'All' ? 'All Cases' : s}</option>)}
      </select>

      <select
        value={filters.crimeType}
        onChange={(e) => onChange({ ...filters, crimeType: e.target.value as MapFilterState['crimeType'] })}
        className={selectClasses}
      >
        {CRIME_TYPE_OPTIONS.map(c => <option key={c} value={c}>{c === 'All' ? 'All Crimes' : c}</option>)}
      </select>

      <select
        value={filters.severity}
        onChange={(e) => onChange({ ...filters, severity: e.target.value as MapFilterState['severity'] })}
        className={selectClasses}
      >
        {SEVERITY_OPTIONS.map(s => <option key={s} value={s}>{s === 'All' ? 'All Severity' : s}</option>)}
      </select>
    </div>
  );
}
