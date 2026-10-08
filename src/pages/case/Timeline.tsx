import { useParams } from 'react-router-dom';
import { useEffect, useState } from 'react';
import { timelineService, caseService } from '../../services';
import { TimelineEvent, Case } from '../../types';
import { Card } from '../../components/ui/Card';
import { Clock, MapPin, Users, FileText, ChevronRight } from 'lucide-react';
import { cn } from '../../utils';

export function Timeline() {
  const { caseId } = useParams();
  const [events, setEvents] = useState<TimelineEvent[]>([]);
  const [currentCase, setCurrentCase] = useState<Case | null>(null);

  useEffect(() => {
    if (caseId) {
      timelineService.getTimelineForCase(caseId).then(setEvents);
      caseService.getCaseById(caseId).then(c => {
        if(c) setCurrentCase(c);
      });
    }
  }, [caseId]);

  return (
    <div className="space-y-6 max-w-5xl mx-auto pb-20">
      <div>
        <h1 className="text-2xl font-serif font-bold text-[#191410] mb-1">Chronological Timeline</h1>
        <p className="text-sm text-text-muted">All extracted events ordered by time. Sourced automatically from evidence.</p>
      </div>

      <div className="relative border-l-2 border-primary/20 ml-6 md:ml-24 mt-12 space-y-12">
        {events.map((event, index) => (
          <div key={event.id} className="relative flex items-start group">
            {/* Timeline Dot */}
            <div className="absolute -left-[33px] md:-left-[29px] w-14 h-14 bg-background border-4 border-primary/20 rounded-full flex items-center justify-center group-hover:border-primary/50 group-hover:scale-110 transition-all z-10 shadow-lg">
              <Clock className="w-5 h-5 text-primary" />
            </div>

            {/* Date/Time Left side (Desktop only) */}
            <div className="hidden md:block absolute -left-48 w-40 text-right pr-8">
              <div className="text-sm font-bold text-white">
                {new Date(event.timestamp).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
              </div>
              <div className="text-xs font-mono text-primary mt-1">
                {new Date(event.timestamp).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })}
              </div>
            </div>

            {/* Content Card */}
            <Card className="ml-12 md:ml-16 w-full max-w-3xl hover:border-primary/30 transition-colors">
              <div className="p-5">
                {/* Mobile Date/Time */}
                <div className="md:hidden flex items-center gap-2 mb-3 text-sm">
                  <span className="font-bold text-white">{new Date(event.timestamp).toLocaleDateString()}</span>
                  <span className="text-primary font-mono">{new Date(event.timestamp).toLocaleTimeString()}</span>
                </div>

                <div className="flex justify-between items-start mb-3">
                  <h3 className="text-lg font-serif font-bold text-[#191410] group-hover:text-primary transition-colors">{event.title}</h3>
                  <span className={cn(
                    "px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider border",
                    (event.confidence ?? 85) >= 95 ? "bg-green-500/10 text-green-400 border-green-500/20" :
                    (event.confidence ?? 85) >= 80 ? "bg-blue-500/10 text-blue-400 border-blue-500/20" :
                    "bg-yellow-500/10 text-yellow-400 border-yellow-500/20"
                  )}>
                    Conf: {event.confidence ?? 85}%
                  </span>
                </div>
                
                <p className="text-sm text-text-muted mb-4">{event.description}</p>

                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-4 border-t border-border/50">
                  <div className="flex items-center gap-2 text-xs text-text-muted">
                    <MapPin className="w-4 h-4 text-primary/70" />
                    <span className="truncate" title={event.location}>{event.location}</span>
                  </div>
                  <div className="flex items-center gap-2 text-xs text-text-muted">
                    <Users className="w-4 h-4 text-purple-400/70" />
                    <span className="truncate">{(event.relatedEntityIds || event.entitiesInvolved || []).length} Entities</span>
                  </div>
                  <div className="flex items-center gap-2 text-xs text-blue-400 hover:text-blue-300 cursor-pointer transition-colors group/src">
                    <FileText className="w-4 h-4" />
                    <span>Source: {event.sourceEvidenceId}</span>
                    <ChevronRight className="w-3 h-3 opacity-0 group-hover/src:opacity-100 -ml-1 transition-all" />
                  </div>
                </div>
              </div>
            </Card>
          </div>
        ))}
      </div>
    </div>
  );
}