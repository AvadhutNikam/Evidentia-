import React from 'react';
import { useSearchParams } from 'react-router-dom';
import { Target, UserCheck, AlertTriangle } from 'lucide-react';
import { Hypotheses } from './Hypotheses';
import { SuspectProfile } from './SuspectProfile';
import { Contradictions } from './Contradictions';
import { cn } from '../../utils';

export function SuspectsAndTheories() {
  const [searchParams, setSearchParams] = useSearchParams();
  const currentTab = searchParams.get('tab') || 'theories';

  const handleTabChange = (tab: 'theories' | 'profiles' | 'contradictions') => {
    setSearchParams({ tab });
  };

  return (
    <div className="h-full flex flex-col space-y-4">
      {/* Top Tab Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-[#eae4d9] shrink-0">
        <div>
          <div className="text-[11px] font-mono tracking-widest text-[#d93829] uppercase font-bold mb-0.5 flex items-center gap-1.5">
            <Target className="w-3.5 h-3.5 text-[#d93829]" />
            <span>Forensic Suspect Evaluation</span>
          </div>
          <h1 className="text-xl lg:text-2xl font-serif font-bold text-[#191410]">
            Suspects and Theories
          </h1>
        </div>

        {/* Tab Switcher Pills */}
        <div className="flex items-center bg-[#f0ebe1] p-1 rounded-full border border-[#d8d0c5] shrink-0 self-start sm:self-auto">
          <button
            onClick={() => handleTabChange('theories')}
            className={cn(
              "px-3.5 py-1.5 rounded-full text-xs font-bold transition-all flex items-center gap-1.5 cursor-pointer",
              currentTab === 'theories'
                ? "bg-white text-[#191410] shadow-xs"
                : "text-[#6e665d] hover:text-[#191410]"
            )}
          >
            <Target className="w-3.5 h-3.5 text-[#d93829]" />
            <span>Case Theories</span>
          </button>

          <button
            onClick={() => handleTabChange('profiles')}
            className={cn(
              "px-3.5 py-1.5 rounded-full text-xs font-bold transition-all flex items-center gap-1.5 cursor-pointer",
              currentTab === 'profiles'
                ? "bg-white text-[#191410] shadow-xs"
                : "text-[#6e665d] hover:text-[#191410]"
            )}
          >
            <UserCheck className="w-3.5 h-3.5 text-blue-700" />
            <span>Suspect Profiles</span>
          </button>

          <button
            onClick={() => handleTabChange('contradictions')}
            className={cn(
              "px-3.5 py-1.5 rounded-full text-xs font-bold transition-all flex items-center gap-1.5 cursor-pointer",
              currentTab === 'contradictions'
                ? "bg-white text-[#191410] shadow-xs"
                : "text-[#6e665d] hover:text-[#191410]"
            )}
          >
            <AlertTriangle className="w-3.5 h-3.5 text-amber-700" />
            <span>Alibi & Conflicts</span>
          </button>
        </div>
      </div>

      {/* Tab Contents */}
      <div className="flex-1 min-h-0">
        {currentTab === 'theories' && <Hypotheses />}
        {currentTab === 'profiles' && <SuspectProfile />}
        {currentTab === 'contradictions' && <Contradictions />}
      </div>
    </div>
  );
}

export default SuspectsAndTheories;

