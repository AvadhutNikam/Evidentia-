import React from 'react';
import { useSearchParams } from 'react-router-dom';
import { Network, Users, Layers, Share2 } from 'lucide-react';
import { KnowledgeGraph } from './KnowledgeGraph';
import { Entities } from './Entities';
import { AnalysisWorkspace } from './AnalysisWorkspace';
import { CrossCaseIntelligence } from './CrossCaseIntelligence';
import { cn } from '../../utils';

export function LinkAnalysis() {
  const [searchParams, setSearchParams] = useSearchParams();
  const currentTab = searchParams.get('tab') || 'network';

  const handleTabChange = (tab: 'network' | 'entities' | 'workspace' | 'cross-case') => {
    setSearchParams({ tab });
  };

  return (
    <div className="h-full flex flex-col space-y-4">
      {/* Top Tab Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-[#eae4d9] shrink-0">
        <div>
          <div className="text-[11px] font-mono tracking-widest text-[#d93829] uppercase font-bold mb-0.5 flex items-center gap-1.5">
            <Network className="w-3.5 h-3.5 text-[#d93829]" />
            <span>Multi-Source Link Analysis</span>
          </div>
          <h1 className="text-xl lg:text-2xl font-serif font-bold text-[#191410]">
            Link Analysis & Entity Intelligence
          </h1>
        </div>

        {/* Tab Switcher Pills */}
        <div className="flex items-center bg-[#f0ebe1] p-1 rounded-full border border-[#d8d0c5] shrink-0 self-start sm:self-auto">
          <button
            onClick={() => handleTabChange('network')}
            className={cn(
              "px-3.5 py-1.5 rounded-full text-xs font-bold transition-all flex items-center gap-1.5 cursor-pointer",
              currentTab === 'network'
                ? "bg-white text-[#191410] shadow-xs"
                : "text-[#6e665d] hover:text-[#191410]"
            )}
          >
            <Network className="w-3.5 h-3.5 text-[#d93829]" />
            <span>Network Graph</span>
          </button>

          <button
            onClick={() => handleTabChange('entities')}
            className={cn(
              "px-3.5 py-1.5 rounded-full text-xs font-bold transition-all flex items-center gap-1.5 cursor-pointer",
              currentTab === 'entities'
                ? "bg-white text-[#191410] shadow-xs"
                : "text-[#6e665d] hover:text-[#191410]"
            )}
          >
            <Users className="w-3.5 h-3.5 text-blue-700" />
            <span>People & Places</span>
          </button>

          <button
            onClick={() => handleTabChange('workspace')}
            className={cn(
              "px-3.5 py-1.5 rounded-full text-xs font-bold transition-all flex items-center gap-1.5 cursor-pointer",
              currentTab === 'workspace'
                ? "bg-white text-[#191410] shadow-xs"
                : "text-[#6e665d] hover:text-[#191410]"
            )}
          >
            <Layers className="w-3.5 h-3.5 text-purple-700" />
            <span>Analysis Workspace</span>
          </button>

          <button
            onClick={() => handleTabChange('cross-case')}
            className={cn(
              "px-3.5 py-1.5 rounded-full text-xs font-bold transition-all flex items-center gap-1.5 cursor-pointer",
              currentTab === 'cross-case'
                ? "bg-white text-[#191410] shadow-xs"
                : "text-[#6e665d] hover:text-[#191410]"
            )}
          >
            <Share2 className="w-3.5 h-3.5 text-emerald-700" />
            <span>Cross-Case Intel</span>
          </button>
        </div>
      </div>

      {/* Tab Contents */}
      <div className="flex-1 min-h-0">
        {currentTab === 'network' && <KnowledgeGraph />}
        {currentTab === 'entities' && <Entities />}
        {currentTab === 'workspace' && <AnalysisWorkspace />}
        {currentTab === 'cross-case' && <CrossCaseIntelligence />}
      </div>
    </div>
  );
}

