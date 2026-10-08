import { useState, useEffect, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { caseService, evidenceService, entityService, timelineService, contradictionService, hypothesisService } from '../../services';
import type { Case, Evidence, Entity, TimelineEvent, Contradiction, Hypothesis } from '../../types';
import { Card, CardContent } from '../../components/ui/Card';
import { SearchIcon, FileText, Users, Clock, AlertTriangle, Lightbulb, Briefcase, X } from 'lucide-react';
import { cn } from '../../utils';

type ResultItem =
  | { kind: 'case'; data: Case }
  | { kind: 'evidence'; data: Evidence; caseId: string }
  | { kind: 'entity'; data: Entity; caseId: string }
  | { kind: 'timeline'; data: TimelineEvent; caseId: string }
  | { kind: 'contradiction'; data: Contradiction; caseId: string }
  | { kind: 'hypothesis'; data: Hypothesis; caseId: string };

import type { LucideIcon } from 'lucide-react';

const KIND_CONFIG: Record<string, { icon: LucideIcon; color: string; bg: string }> = {
  case: { icon: Briefcase, color: 'text-primary', bg: 'bg-primary/10 border-primary/20' },
  evidence: { icon: FileText, color: 'text-blue-400', bg: 'bg-blue-500/10 border-blue-500/20' },
  entity: { icon: Users, color: 'text-green-400', bg: 'bg-green-500/10 border-green-500/20' },
  timeline: { icon: Clock, color: 'text-indigo-400', bg: 'bg-indigo-500/10 border-indigo-500/20' },
  contradiction: { icon: AlertTriangle, color: 'text-red-400', bg: 'bg-red-500/10 border-red-500/20' },
  hypothesis: { icon: Lightbulb, color: 'text-yellow-400', bg: 'bg-yellow-500/10 border-yellow-500/20' },
};

function getLabel(item: ResultItem): string {
  switch (item.kind) {
    case 'case': return item.data.name;
    case 'evidence': return item.data.fileName;
    case 'entity': return `${item.data.name} (${item.data.type})`;
    case 'timeline': return item.data.title;
    case 'contradiction': return `${item.data.conflictType}: ${item.data.id}`;
    case 'hypothesis': return item.data.title;
  }
}

function getSublabel(item: ResultItem): string {
  switch (item.kind) {
    case 'case': return item.data.id;
    case 'evidence': return `${item.data.id} - ${item.data.fileType} - ${item.data.processingStatus}`;
    case 'entity': return `${item.data.id} - Confidence: ${item.data.confidence}%`;
    case 'timeline': return `${item.data.id} - ${new Date(item.data.timestamp).toLocaleString()}`;
    case 'contradiction': return `${item.data.id} - ${item.data.conflictType} - ${item.data.status}`;
    case 'hypothesis': return `${item.data.id} - ${item.data.status} - ${item.data.confidence}%`;
  }
}

export function Search() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<ResultItem[]>([]);
  const [searched, setSearched] = useState(false);

  useEffect(() => {
    if (!query.trim()) { setResults([]); setSearched(false); return; }
    const q = query.trim().toLowerCase();
    const timer = setTimeout(async () => {
      const cases = await caseService.getCases();
      const items: ResultItem[] = [];

      for (const c of cases) {
        if (`${c.id} ${c.name} ${c.description} ${c.status}`.toLowerCase().includes(q)) {
          items.push({ kind: 'case', data: c });
        }
      }

      for (const c of cases) {
        const [ev, ent, tl, con, hyp] = await Promise.all([
          evidenceService.getEvidenceForCase(c.id),
          entityService.getEntitiesForCase(c.id),
          timelineService.getTimelineForCase(c.id),
          contradictionService.getContradictionsForCase(c.id),
          hypothesisService.getHypothesesForCase(c.id),
        ]);
        for (const e of ev) {
          if (`${e.id} ${e.fileName} ${e.fileType} ${e.source} ${e.tags.join(' ')}`.toLowerCase().includes(q)) {
            items.push({ kind: 'evidence', data: e, caseId: c.id });
          }
        }
        for (const e of ent) {
          if (`${e.id} ${e.name} ${e.type} ${e.aliases.join(' ')}`.toLowerCase().includes(q)) {
            items.push({ kind: 'entity', data: e, caseId: c.id });
          }
        }
        for (const t of tl) {
          if (`${t.id} ${t.title} ${t.description} ${t.location}`.toLowerCase().includes(q)) {
            items.push({ kind: 'timeline', data: t, caseId: c.id });
          }
        }
        for (const c2 of con) {
          if (`${c2.id} ${c2.conflictType} ${c2.statementA} ${c2.statementB}`.toLowerCase().includes(q)) {
            items.push({ kind: 'contradiction', data: c2, caseId: c.id });
          }
        }
        for (const h of hyp) {
          if (`${h.id} ${h.title} ${h.description}`.toLowerCase().includes(q)) {
            items.push({ kind: 'hypothesis', data: h, caseId: c.id });
          }
        }
      }

      setResults(items);
      setSearched(true);
    }, 300);
    return () => clearTimeout(timer);
  }, [query]);

  const caseLink = (item: ResultItem) => {
    const cid = 'caseId' in item ? item.caseId : item.data.id;
    switch (item.kind) {
      case 'case': return `/cases/${cid}`;
      case 'evidence': return `/cases/${cid}/evidence/${item.data.id}`;
      case 'entity': return `/cases/${cid}/entities`;
      case 'timeline': return `/cases/${cid}/timeline`;
      case 'contradiction': return `/cases/${cid}/contradictions`;
      case 'hypothesis': return `/cases/${cid}/hypotheses`;
    }
  };

  const counts = useMemo(() => {
    const map = new Map<string, number>();
    for (const r of results) { map.set(r.kind, (map.get(r.kind) ?? 0) + 1); }
    return map;
  }, [results]);

  return (
    <div className="space-y-6 max-w-4xl mx-auto pb-20">
      <div>
        <h1 className="text-3xl font-bold text-white mb-1">Global Search</h1>
        <p className="text-sm text-text-muted">Search across all cases, evidence, entities, and analysis results.</p>
      </div>

      <Card className="p-4 relative">
        <SearchIcon className="w-5 h-5 absolute left-7 top-1/2 -translate-y-1/2 text-text-muted" />
        <input
          type="text"
          value={query}
          onChange={e => setQuery(e.target.value)}
          placeholder="Search cases, evidence, entities, contradictions..."
          className="w-full pl-12 pr-10 py-3 bg-background border border-border rounded-lg text-sm focus:outline-none focus:border-primary/50 text-white transition-colors"
          autoFocus
        />
        {query && (
          <button onClick={() => setQuery('')} className="absolute right-7 top-1/2 -translate-y-1/2 text-text-muted hover:text-white transition-colors">
            <X className="w-4 h-4" />
          </button>
        )}
      </Card>

      {searched && (
        <div className="flex flex-wrap gap-2">
          {Array.from(counts.entries()).map(([kind, count]) => {
            const cfg = KIND_CONFIG[kind];
            return (
              <span key={kind} className={cn('px-3 py-1 rounded-md text-xs font-semibold border flex items-center gap-1.5', cfg.bg)}>
                <cfg.icon className={cn('w-3.5 h-3.5', cfg.color)} />
                {count} {kind}{count !== 1 ? 's' : ''}
              </span>
            );
          })}
        </div>
      )}

      <div className="space-y-2">
        {results.map((item, i) => {
          const cfg = KIND_CONFIG[item.kind];
          const Icon = cfg.icon;
          return (
            <Link key={`${item.kind}-${i}`} to={caseLink(item)}>
              <Card className="hover:border-primary/50 transition-colors group">
                <CardContent className="p-4 flex items-center gap-4">
                  <div className={cn('w-10 h-10 rounded-lg flex items-center justify-center border shrink-0', cfg.bg)}>
                    <Icon className={cn('w-5 h-5', cfg.color)} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-medium text-white truncate group-hover:text-primary transition-colors">{getLabel(item)}</div>
                    <div className="text-xs text-text-muted mt-0.5 truncate">{getSublabel(item)}</div>
                  </div>
                  <span className="text-[10px] font-bold uppercase tracking-wider text-text-muted bg-surface-hover px-2 py-1 rounded border border-border shrink-0">{item.kind}</span>
                </CardContent>
              </Card>
            </Link>
          );
        })}

        {searched && results.length === 0 && (
          <div className="text-center py-16">
            <SearchIcon className="w-10 h-10 text-text-muted/30 mx-auto mb-3" />
            <p className="text-sm text-text-muted">No results found for &quot;{query}&quot;</p>
          </div>
        )}
      </div>
    </div>
  );
}
