import { Card } from '../../components/ui/Card';
import { Map as MapIcon, Filter, Layers, Navigation } from 'lucide-react';

export function CaseMap() {
  return (
    <div className="h-[calc(100vh-8rem)] flex flex-col space-y-4">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-serif font-bold text-[#191410] mb-1">Geospatial Intelligence</h1>
          <p className="text-sm text-text-muted">Map of extracted locations and physical evidence trails.</p>
        </div>
        <div className="flex gap-2">
          <button className="flex items-center gap-2 px-3 py-1.5 bg-surface border border-border rounded-lg text-sm text-text-muted hover:text-white transition-colors">
            <Filter className="w-4 h-4" /> Filters
          </button>
          <button className="flex items-center gap-2 px-3 py-1.5 bg-surface border border-border rounded-lg text-sm text-text-muted hover:text-white transition-colors">
            <Layers className="w-4 h-4" /> Map Layers
          </button>
        </div>
      </div>

      <Card className="flex-1 relative overflow-hidden flex items-center justify-center bg-[#0a1526]">
        {/* Mock Map Background Grid */}
        <div className="absolute inset-0 opacity-10 pointer-events-none" style={{ backgroundImage: 'linear-gradient(#3b82f6 1px, transparent 1px), linear-gradient(90deg, #3b82f6 1px, transparent 1px)', backgroundSize: '40px 40px' }}></div>
        
        {/* Map Center Placeholder Text */}
        <div className="z-10 text-center pointer-events-none">
          <MapIcon className="w-12 h-12 text-primary/50 mx-auto mb-3" />
          <h2 className="text-lg font-serif font-bold text-[#191410]/50">Interactive Map Component</h2>
          <p className="text-xs text-text-muted">Leaflet / Mapbox integration pending backend geo-coordinates.</p>
        </div>

        {/* Mock Map Pins */}
        <div className="absolute top-1/4 left-1/4 flex items-center justify-center cursor-pointer group">
          <div className="absolute w-12 h-12 bg-red-500/20 rounded-full animate-ping" />
          <div className="w-4 h-4 bg-red-500 rounded-full border-2 border-white shadow-lg z-10" />
          <div className="absolute top-6 left-1/2 -translate-x-1/2 opacity-0 group-hover:opacity-100 transition-opacity bg-surface border border-border px-3 py-1.5 rounded text-xs whitespace-nowrap z-20 shadow-xl">
            <div className="font-bold text-white">Apex HQ</div>
            <div className="text-text-muted">Event: Suspicious Email</div>
          </div>
        </div>

        <div className="absolute top-1/2 right-1/3 flex items-center justify-center cursor-pointer group">
          <div className="w-4 h-4 bg-blue-500 rounded-full border-2 border-white shadow-lg z-10" />
          <div className="absolute top-6 left-1/2 -translate-x-1/2 opacity-0 group-hover:opacity-100 transition-opacity bg-surface border border-border px-3 py-1.5 rounded text-xs whitespace-nowrap z-20 shadow-xl">
            <div className="font-bold text-white">Zurich Airport</div>
            <div className="text-text-muted">Event: Flight Boarded</div>
          </div>
        </div>

        {/* Floating controls */}
        <div className="absolute bottom-6 right-6 flex flex-col gap-2 glass-panel p-2 rounded-lg">
          <button className="w-8 h-8 flex items-center justify-center hover:bg-surface-hover rounded text-text-muted hover:text-white transition-colors text-lg font-bold">
            +
          </button>
          <button className="w-8 h-8 flex items-center justify-center hover:bg-surface-hover rounded text-text-muted hover:text-white transition-colors text-lg font-bold">
            -
          </button>
          <div className="w-full h-px bg-border my-1" />
          <button className="w-8 h-8 flex items-center justify-center hover:bg-surface-hover rounded text-primary transition-colors">
            <Navigation className="w-4 h-4" />
          </button>
        </div>
      </Card>
    </div>
  );
}