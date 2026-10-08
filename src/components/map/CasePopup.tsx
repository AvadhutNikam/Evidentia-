import { useNavigate } from 'react-router-dom';
import { FileText, Users, Eye, ArrowRight, MapPin } from 'lucide-react';
import { GeoCase } from '../../types';
import { cn } from '../../utils';
import { CRIME_TYPE_CONFIG, STATUS_BADGE_CLASSES, SEVERITY_BADGE_CLASSES } from './mapConfig';

interface CasePopupProps {
  geoCase: GeoCase;
}

export function CasePopup({ geoCase }: CasePopupProps) {
  const navigate = useNavigate();
  const crimeColor = CRIME_TYPE_CONFIG[geoCase.crimeType]?.color ?? CRIME_TYPE_CONFIG.Other.color;

  return (
    <div className="w-64 -m-3 font-sans">
      <div className="px-4 pt-4 pb-3 border-b border-border/60">
        <div className="flex items-center gap-2 mb-1.5">
          <span className="w-2 h-2 rounded-full shrink-0" style={{ background: crimeColor }} />
          <span className="text-[10px] font-bold uppercase tracking-wider text-text-muted font-mono">{geoCase.id}</span>
        </div>
        <h3 className="text-sm font-bold text-white leading-snug">{geoCase.title}</h3>
        <div className="flex items-center gap-1 mt-1.5 text-xs text-text-muted">
          <MapPin className="w-3 h-3 shrink-0" />
          <span className="truncate">{geoCase.location}</span>
        </div>
      </div>

      <div className="px-4 py-3 space-y-3">
        <div className="flex flex-wrap gap-1.5">
          <span className={cn('px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider border', STATUS_BADGE_CLASSES[geoCase.status])}>
            {geoCase.status}
          </span>
          <span className={cn('px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider border', SEVERITY_BADGE_CLASSES[geoCase.severity])}>
            {geoCase.severity}
          </span>
          <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider border bg-surface-hover text-text-muted border-border">
            {geoCase.crimeType}
          </span>
        </div>

        <div className="grid grid-cols-3 gap-2 text-center">
          <div className="bg-surface-hover/60 rounded-lg py-1.5">
            <div className="flex items-center justify-center gap-1 text-white font-bold text-sm">
              <FileText className="w-3 h-3 text-text-muted" />{geoCase.evidenceCount}
            </div>
            <div className="text-[9px] text-text-muted uppercase tracking-wider mt-0.5">Evidence</div>
          </div>
          <div className="bg-surface-hover/60 rounded-lg py-1.5">
            <div className="flex items-center justify-center gap-1 text-white font-bold text-sm">
              <Users className="w-3 h-3 text-text-muted" />{geoCase.suspectCount}
            </div>
            <div className="text-[9px] text-text-muted uppercase tracking-wider mt-0.5">Suspects</div>
          </div>
          <div className="bg-surface-hover/60 rounded-lg py-1.5">
            <div className="flex items-center justify-center gap-1 text-white font-bold text-sm">
              <Eye className="w-3 h-3 text-text-muted" />{geoCase.witnessCount}
            </div>
            <div className="text-[9px] text-text-muted uppercase tracking-wider mt-0.5">Witnesses</div>
          </div>
        </div>
      </div>

      <div className="px-4 pb-4 pt-1">
        <button
          onClick={() => navigate(`/cases/${geoCase.id}`)}
          className="w-full flex items-center justify-center gap-1.5 px-3 py-2 bg-primary/10 hover:bg-primary/20 text-primary border border-primary/20 rounded-lg text-xs font-bold uppercase tracking-wider transition-colors"
        >
          View Case <ArrowRight className="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
  );
}
