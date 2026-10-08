import { useParams } from 'react-router-dom';
import { useEffect, useState } from 'react';
import { investigationService } from '../../services';
import { InvestigationTask } from '../../types';
import { Card, CardContent } from '../../components/ui/Card';
import { CheckSquare, AlertTriangle, Lightbulb, Clock, CheckCircle2, PlayCircle } from 'lucide-react';
import { cn } from '../../utils';
import { useCaseState } from '../../engine/useCaseState';

export function InvestigationPlan() {
  const { caseId } = useParams();
  const [tasks, setTasks] = useState<InvestigationTask[]>([]);
  const stateTick = useCaseState();

  useEffect(() => {
    if (caseId) {
      investigationService.getTasksForCase(caseId).then(setTasks);
    }
  }, [caseId, stateTick]);

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'Completed': return <CheckCircle2 className="w-5 h-5 text-green-500" />;
      case 'In Progress': return <PlayCircle className="w-5 h-5 text-blue-500" />;
      default: return <Clock className="w-5 h-5 text-text-muted" />;
    }
  };

  return (
    <div className="space-y-6 max-w-5xl mx-auto pb-20">
      <div>
        <h1 className="text-2xl font-serif font-bold text-[#191410] mb-1">Investigation Plan</h1>
        <p className="text-sm text-text-muted">Recommended tasks based on hypotheses, missing information, and contradictions.</p>
      </div>

      <div className="space-y-4 mt-8">
        {tasks.map((task, idx) => (
          <Card key={`${task.id}-${idx}`} className={cn(
            "border-l-4 transition-colors hover:bg-surface/50",
            task.priority === 'High' ? "border-l-red-500" : task.priority === 'Medium' ? "border-l-yellow-500" : "border-l-blue-500",
            task.status === 'Completed' && "opacity-60 grayscale border-l-green-500"
          )}>
            <CardContent className="p-5 flex gap-4">
              <div className="mt-1">
                {getStatusIcon(task.status)}
              </div>
              <div className="flex-1">
                <div className="flex justify-between items-start mb-1">
                  <h3 className={cn("font-bold text-lg", task.status === 'Completed' ? "text-text-muted line-through" : "text-white")}>
                    {task.task}
                  </h3>
                  <div className="flex gap-2">
                    <span className="px-2 py-1 rounded bg-surface border border-border text-[10px] font-bold uppercase tracking-wider text-text-muted">
                      {task.status}
                    </span>
                  </div>
                </div>
                
                <p className="text-sm text-text-muted mb-4 max-w-3xl leading-relaxed">{task.reason}</p>
                
                <div className="flex flex-wrap gap-3 mt-auto">
                  {task.relatedContradictionId && (
                    <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-red-500/10 text-red-400 border border-red-500/20 text-xs font-semibold">
                      <AlertTriangle className="w-3.5 h-3.5" />
                      Resolves: {task.relatedContradictionId}
                    </div>
                  )}
                  {task.relatedHypothesisId && (
                    <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-yellow-500/10 text-yellow-500 border border-yellow-500/20 text-xs font-semibold">
                      <Lightbulb className="w-3.5 h-3.5" />
                      Tests: {task.relatedHypothesisId}
                    </div>
                  )}
                  {task.relatedEvidenceId && (
                    <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-surface-hover text-text-muted border border-border text-xs font-semibold">
                      Requires: <span className="font-mono">{task.relatedEvidenceId}</span>
                    </div>
                  )}
                </div>
              </div>
              
              {task.status !== 'Completed' && (
                <div className="flex flex-col gap-2 justify-center ml-4 pl-4 border-l border-border/50">
                  <button className="px-4 py-2 bg-primary/10 text-primary hover:bg-primary hover:text-white border border-primary/20 rounded-lg text-sm font-medium transition-all whitespace-nowrap">
                    Mark In Progress
                  </button>
                  <button className="px-4 py-2 bg-surface hover:bg-surface-hover border border-border text-text hover:text-white rounded-lg text-sm font-medium transition-colors whitespace-nowrap">
                    Complete Task
                  </button>
                </div>
              )}
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}