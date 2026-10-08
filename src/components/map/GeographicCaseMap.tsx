import { useEffect, useMemo, useState } from 'react';
import { MapContainer, TileLayer, useMap } from 'react-leaflet';
import { Filter, ChevronDown } from 'lucide-react';
import { geoCaseService } from '../../services';
import { GeoCase } from '../../types';
import { cn } from '../../utils';
import { useMarkerClusters } from './useMarkerClusters';
import { CaseMarker } from './CaseMarker';
import { MapControls } from './MapControls';
import { MapLegend } from './MapLegend';
import { MapFilters, MapFilterState } from './MapFilters';
import { ErrorBoundary } from '../common/ErrorBoundary';

const INDIA_CENTER: [number, number] = [22.9734, 78.6569];
const INDIA_DEFAULT_ZOOM = 5;

function ClusteredMarkers({ cases }: { cases: GeoCase[] }) {
  const clusters = useMarkerClusters(cases);
  return (
    <>
      {clusters.map(item => (
        <CaseMarker key={item.type === 'cluster' ? item.id : item.case.id} item={item} />
      ))}
    </>
  );
}

function MapResizeHandler({ trigger }: { trigger: unknown }) {
  const map = useMap();
  useEffect(() => {
    const id = window.setTimeout(() => {
      try {
        if (map) map.invalidateSize();
      } catch {}
    }, 260);
    return () => window.clearTimeout(id);
  }, [map, trigger]);
  return null;
}

export function GeographicCaseMap() {
  const [allCases, setAllCases] = useState<GeoCase[]>([]);
  const [loading, setLoading] = useState(true);
  const [isExpanded, setIsExpanded] = useState(false);
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [filters, setFilters] = useState<MapFilterState>({
    search: '',
    status: 'All',
    crimeType: 'All',
    severity: 'All',
  });

  useEffect(() => {
    geoCaseService.getGeoCases().then(data => {
      setAllCases(data || []);
      setLoading(false);
    }).catch(err => {
      console.warn('Failed to fetch geo cases:', err);
      setLoading(false);
    });
  }, []);

  const filteredCases = useMemo(() => {
    return allCases.filter(c => {
      if (!c) return false;
      if (filters.status !== 'All' && c.status !== filters.status) return false;
      if (filters.crimeType !== 'All' && c.crimeType !== filters.crimeType) return false;
      if (filters.severity !== 'All' && c.severity !== filters.severity) return false;
      if (filters.search) {
        const q = filters.search.toLowerCase();
        const matchTitle = (c.title || '').toLowerCase().includes(q);
        const matchLoc = (c.location || '').toLowerCase().includes(q);
        const matchId = (c.id || '').toLowerCase().includes(q);
        if (!matchTitle && !matchLoc && !matchId) return false;
      }
      return true;
    });
  }, [allCases, filters]);

  return (
    <ErrorBoundary fallbackTitle="Geospatial Map Unavailable">
      <div className="rounded-3xl bg-white border border-[#eae4d9] shadow-xs overflow-hidden">
        {/* Header */}
        <div className="p-6 border-b border-[#f0ebe1] flex flex-wrap items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-[#d93829] animate-pulse" />
              <h3 className="font-serif font-bold text-lg text-[#191410]">Geographic Case Intelligence</h3>
            </div>
            <p className="text-xs text-[#6e665d] mt-0.5">
              Interactive jurisdiction map tracking national & international forensic dockets
            </p>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setFiltersOpen(!filtersOpen)}
              type="button"
              className={cn(
                "inline-flex items-center gap-2 px-4 py-2 rounded-full text-xs font-semibold border transition-all",
                filtersOpen ? "bg-[#d93829] text-white border-[#d93829]" : "bg-[#faf7f2] text-[#70685e] border-[#eae4d9] hover:text-[#191410]"
              )}
            >
              <Filter className="w-3.5 h-3.5" />
              <span>Filters</span>
              <ChevronDown className={cn("w-3.5 h-3.5 transition-transform", filtersOpen && "rotate-180")} />
            </button>
            <button
              onClick={() => setIsExpanded(!isExpanded)}
              type="button"
              className="px-4 py-2 rounded-full text-xs font-semibold bg-[#faf7f2] text-[#70685e] border border-[#eae4d9] hover:text-[#191410] transition-colors"
            >
              {isExpanded ? 'Collapse View' : 'Expand View'}
            </button>
          </div>
        </div>

        {/* Filter Drawer */}
        {filtersOpen && (
          <div className="p-4 bg-[#faf7f2] border-b border-[#eae4d9]">
            <MapFilters filters={filters} onChange={setFilters} totalCount={allCases.length} filteredCount={filteredCases.length} />
          </div>
        )}

        {/* Map Viewport Container */}
        <div className={cn("relative w-full transition-all duration-300", isExpanded ? "h-[620px]" : "h-[420px]")}>
          {loading ? (
            <div className="h-full w-full flex items-center justify-center bg-[#faf7f2]">
              <div className="w-8 h-8 border-2 border-[#d93829] border-t-transparent rounded-full animate-spin" />
            </div>
          ) : (
            <MapContainer
              center={INDIA_CENTER}
              zoom={INDIA_DEFAULT_ZOOM}
              scrollWheelZoom={false}
              className="h-full w-full z-0"
              style={{ background: '#faf7f2' }}
            >
              <TileLayer
                attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              />
              <MapResizeHandler trigger={isExpanded} />
              <ClusteredMarkers cases={filteredCases} />
              <MapControls cases={filteredCases} isExpanded={isExpanded} onToggleExpand={() => setIsExpanded(!isExpanded)} />
            </MapContainer>
          )}

          {/* Map Legend Overlay in bottom-left */}
          <div className="absolute bottom-4 left-4 z-[400] pointer-events-auto max-w-xs bg-white/95 backdrop-blur-md p-2.5 rounded-2xl border border-[#eae4d9] shadow-md">
            <MapLegend />
          </div>
        </div>
      </div>
    </ErrorBoundary>
  );
}
