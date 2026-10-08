import { useMap } from 'react-leaflet';
import { Plus, Minus, Maximize2, Minimize2, LocateFixed } from 'lucide-react';
import L from 'leaflet';
import { GeoCase } from '../../types';

interface MapControlsProps {
  cases: GeoCase[];
  isExpanded: boolean;
  onToggleExpand: () => void;
}

export function MapControls({ cases, isExpanded, onToggleExpand }: MapControlsProps) {
  let map: any = null;
  try {
    map = useMap();
  } catch (err) {
    console.warn('MapControls mounted outside MapContainer context:', err);
    return null;
  }

  const handleFitBounds = () => {
    if (!map || cases.length === 0) return;
    try {
      const validPoints = cases
        .filter(c => typeof c.latitude === 'number' && typeof c.longitude === 'number')
        .map(c => [c.latitude, c.longitude] as [number, number]);
      if (validPoints.length > 0) {
        const bounds = L.latLngBounds(validPoints);
        map.fitBounds(bounds, { padding: [40, 40], maxZoom: 12 });
      }
    } catch (e) {
      console.warn('fitBounds error:', e);
    }
  };

  return (
    <div className="absolute bottom-4 right-4 z-[400] flex flex-col gap-2 bg-white/95 backdrop-blur-md p-1.5 rounded-2xl border border-[#eae4d9] shadow-md">
      <button
        onClick={() => map && map.zoomIn()}
        title="Zoom in"
        type="button"
        className="w-8 h-8 flex items-center justify-center hover:bg-[#faf7f2] rounded-xl text-[#70685e] hover:text-[#191410] transition-colors"
      >
        <Plus className="w-4 h-4 text-[#191410]" />
      </button>
      <button
        onClick={() => map && map.zoomOut()}
        title="Zoom out"
        type="button"
        className="w-8 h-8 flex items-center justify-center hover:bg-[#faf7f2] rounded-xl text-[#70685e] hover:text-[#191410] transition-colors"
      >
        <Minus className="w-4 h-4 text-[#191410]" />
      </button>
      <div className="w-full h-px bg-[#eae4d9] my-0.5" />
      <button
        onClick={handleFitBounds}
        title="Fit to all visible cases"
        type="button"
        className="w-8 h-8 flex items-center justify-center hover:bg-[#faf7f2] rounded-xl text-[#d93829] transition-colors"
      >
        <LocateFixed className="w-4 h-4" />
      </button>
      <button
        onClick={onToggleExpand}
        title={isExpanded ? 'Collapse map' : 'Expand map'}
        type="button"
        className="w-8 h-8 flex items-center justify-center hover:bg-[#faf7f2] rounded-xl text-[#70685e] hover:text-[#191410] transition-colors"
      >
        {isExpanded ? <Minimize2 className="w-4 h-4 text-[#191410]" /> : <Maximize2 className="w-4 h-4 text-[#191410]" />}
      </button>
    </div>
  );
}
