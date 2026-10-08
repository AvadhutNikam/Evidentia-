import { CRIME_TYPE_CONFIG } from './mapConfig';

export function MapLegend() {
  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5">
      {Object.entries(CRIME_TYPE_CONFIG).map(([type, cfg]) => (
        <div key={type} className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full shrink-0" style={{ background: cfg.color }} />
          <span className="text-[11px] font-medium text-text-muted">{cfg.label}</span>
        </div>
      ))}
    </div>
  );
}
