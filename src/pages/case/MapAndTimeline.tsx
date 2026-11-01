import React from 'react';
import { useSearchParams } from 'react-router-dom';
import { Clock, Map as MapIcon } from 'lucide-react';
import { Timeline } from './Timeline';
import { CaseMap } from './CaseMap';
import { cn } from '../../utils';

export function MapAndTimeline() {
  const [searchParams, setSearchParams] = useSearchParams();
  const currentTab = searchParams.get('tab') || 'timeline';

  const handleTabChange = (tab: 'timeline' | 'map') => {
    setSearchParams({ tab });
  };

  return (
    <div className="h-full flex flex-col space-y-4">
      {/* Top Tab Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-[#eae4d9] shrink-0">
        <div>
          <div className="text-[11px] font-mono tracking-widest text-[#d93829] uppercase font-bold mb-0.5 flex items-center gap-1.5">
            <MapIcon className="w-3.5 h-3.5 text-[#d93829]" />
            <span>Spatio-Temporal Crime Scene Analysis</span>
          </div>
          <h1 className="text-xl lg:text-2xl font-serif font-bold text-[#191410]">
            Map and Timeline
          </h1>
        </div>

        {/* Tab Switcher Pills */}
        <div className="flex items-center bg-[#f0ebe1] p-1 rounded-full border border-[#d8d0c5] shrink-0 self-start sm:self-auto">
          <button
            onClick={() => handleTabChange('timeline')}
            className={cn(
              "px-3.5 py-1.5 rounded-full text-xs font-bold transition-all flex items-center gap-1.5 cursor-pointer",
              currentTab === 'timeline'
                ? "bg-white text-[#191410] shadow-xs"
                : "text-[#6e665d] hover:text-[#191410]"
            )}
          >
            <Clock className="w-3.5 h-3.5 text-[#d93829]" />
            <span>Timeline Chronology</span>
          </button>

          <button
            onClick={() => handleTabChange('map')}
            className={cn(
              "px-3.5 py-1.5 rounded-full text-xs font-bold transition-all flex items-center gap-1.5 cursor-pointer",
              currentTab === 'map'
                ? "bg-white text-[#191410] shadow-xs"
                : "text-[#6e665d] hover:text-[#191410]"
            )}
          >
            <MapIcon className="w-3.5 h-3.5 text-blue-700" />
            <span>Crime Scene Map</span>
          </button>
        </div>
      </div>

      {/* Tab Contents */}
      <div className="flex-1 min-h-0">
        {currentTab === 'timeline' && <Timeline />}
        {currentTab === 'map' && <CaseMap />}
      </div>
    </div>
  );
}

export default MapAndTimeline;

