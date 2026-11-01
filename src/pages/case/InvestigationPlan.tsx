import { useParams } from 'react-router-dom';
import { useEffect, useState, useMemo } from 'react';
import { investigationService } from '../../services';
import { InvestigationTask } from '../../types';
import { Card, CardContent } from '../../components/ui/Card';
import { 
  CheckSquare, AlertTriangle, Lightbulb, Clock, CheckCircle2, PlayCircle, 
  Sparkles, X, User, Zap, ShieldAlert, Filter, TrendingUp, Check
} from 'lucide-react';
import { cn } from '../../utils';
import { useCaseState } from '../../engine/useCaseState';
import { GapsAndNextStepsModal } from '../../components/case/GapsAndNextStepsModal';

export function InvestigationPlan() {
  const { caseId } = useParams();
  const [tasks, setTasks] = useState<InvestigationTask[]>([]);
  const [categoryFilter, setCategoryFilter] = useState<string>('all');
  const [isGapsModalOpen, setIsGapsModalOpen] = useState(false);
  const [dismissingId, setDismissingId] = useState<string | null>(null);
  const stateTick = useCaseState();

  const loadTasks = () => {
    if (caseId) {
      investigationService.getTasksForCase(caseId).then(setTasks);
    }
  };

  useEffect(() => {
    loadTasks();
  }, [caseId, stateTick]);

  const handleDismiss = async (taskId: string) => {
    if (!caseId) return;
    setDismissingId(taskId);
    try {
      await investigationService.dismissTask(caseId, taskId);
      setTasks(prev => prev.filter(t => t.id !== taskId));
    } catch (err) {
      console.error('Failed to dismiss task:', err);
    } finally {
      setDismissingId(null);
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'Completed': return <CheckCircle2 className="w-5 h-5 text-emerald-600" />;
      case 'In Progress': return <PlayCircle className="w-5 h-5 text-blue-600" />;
      default: return <Clock className="w-5 h-5 text-[#8c8276]" />;
    }
  };

  const filteredTasks = useMemo(() => {
    return tasks.filter(t => {
      if (t.dismissed) return false;
      if (categoryFilter === 'gap_detection' && t.category !== 'gap_detection') return false;
      if (categoryFilter === 'next_best_step' && t.category !== 'next_best_step') return false;
      if (categoryFilter === 'general' && (t.category === 'gap_detection' || t.category === 'next_best_step')) return false;
      return true;
    });
  }, [tasks, categoryFilter]);

  const gapTasksCount = useMemo(() => tasks.filter(t => t.category === 'gap_detection').length, [tasks]);
  const nextStepTasksCount = useMemo(() => tasks.filter(t => t.category === 'next_best_step').length, [tasks]);

  return (
    <div className="space-y-6 max-w-5xl mx-auto pb-24 text-[#191410]">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-[#eae4d9]">
        <div>
          <div className="text-[11px] font-mono tracking-widest text-[#d93829] uppercase font-bold mb-1 flex items-center gap-1.5">
            <CheckSquare className="w-3.5 h-3.5 text-[#d93829]" />
            <span>Operational Investigative Action Docket</span>
          </div>
          <h1 className="text-2xl lg:text-3xl font-serif font-bold text-[#191410]">
            Investigation Plan & Task Queue
          </h1>
          <p className="text-xs text-[#6e665d] mt-1 max-w-2xl leading-relaxed">
            Prioritized tasks generated from procedural gap detection, Bayesian next-best-step simulations, and case contradictions.
          </p>
        </div>

        <button
          onClick={() => setIsGapsModalOpen(true)}
          className="flex items-center gap-2 px-4 py-2.5 bg-[#191410] hover:bg-[#d93829] text-white rounded-full text-xs font-bold transition-all cursor-pointer shadow-xs whitespace-nowrap self-start md:self-auto"
        >
          <Sparkles className="w-4 h-4 text-amber-400" />
          <span>Gap Detection & Next Steps</span>
          {(gapTasksCount > 0 || nextStepTasksCount > 0) && (
            <span className="px-1.5 py-0.2 rounded-full text-[10px] font-mono font-bold bg-white text-[#191410]">
              {tasks.length}
            </span>
          )}
        </button>
      </div>

      {/* Filter Tabs */}
      <div className="p-3 rounded-2xl bg-white border border-[#eae4d9] flex flex-wrap items-center justify-between gap-3 shadow-xs">
        <div className="flex items-center gap-2 flex-wrap">
          <Filter className="w-3.5 h-3.5 text-[#8c8276] mr-1" />
          {[
            { key: 'all', label: `All Tasks (${tasks.length})` },
            { key: 'gap_detection', label: `Procedural Gaps (${gapTasksCount})` },
            { key: 'next_best_step', label: `Next Best Steps (${nextStepTasksCount})` },
            { key: 'general', label: `General (${tasks.length - gapTasksCount - nextStepTasksCount})` },
          ].map(f => (
            <button
              key={f.key}
              onClick={() => setCategoryFilter(f.key)}
              className={cn(
                "px-3.5 py-1.5 rounded-full text-xs font-mono transition-all cursor-pointer border",
                categoryFilter === f.key
                  ? "bg-[#191410] text-white border-[#191410] font-bold shadow-xs"
                  : "bg-[#faf7f2] hover:bg-[#eae4d9] text-[#6e665d] border-[#eae4d9]"
              )}
            >
              {f.label}
            </button>
          ))}
        </div>

        <div className="text-[11px] font-mono text-[#8c8276]">
          Showing {filteredTasks.length} active tasks
        </div>
      </div>

      {/* Task Cards List */}
      <div className="space-y-4 mt-6">
        {filteredTasks.length === 0 ? (
          <div className="text-center py-16 border border-dashed border-[#eae4d9] bg-white rounded-3xl">
            <CheckCircle2 className="w-12 h-12 text-emerald-500 mx-auto mb-3" />
            <h3 className="text-base font-serif font-bold text-[#191410]">No Tasks In This Category</h3>
            <p className="text-xs text-[#6e665d] mt-1">Open "Gap Detection & Next Steps" to simulate new candidate forensic tasks.</p>
          </div>
        ) : (
          filteredTasks.map((task, idx) => {
            const isGap = task.category === 'gap_detection';
            const isNextStep = task.category === 'next_best_step';
            const isHigh = task.priority === 'High';

            return (
              <Card 
                key={`${task.id}-${idx}`} 
                className={cn(
                  "border-l-4 transition-all hover:bg-[#faf7f2] bg-white border-[#eae4d9] rounded-2xl shadow-xs overflow-hidden",
                  isHigh ? "border-l-rose-500" : (task.priority === 'Medium' ? "border-l-amber-500" : "border-l-blue-500"),
                  task.status === 'Completed' && "opacity-60 grayscale border-l-emerald-500"
                )}
              >
                <CardContent className="p-5 flex flex-col md:flex-row gap-4 justify-between">
                  <div className="flex gap-3 flex-1">
                    <div className="mt-1 shrink-0">
                      {getStatusIcon(task.status)}
                    </div>
                    <div className="space-y-2 flex-1">
                      {/* Category & Metadata Badges */}
                      <div className="flex items-center gap-2 flex-wrap">
                        {isGap && (
                          <span className="px-2 py-0.5 rounded-full text-[10px] font-mono font-bold bg-rose-50 text-rose-800 border border-rose-200 flex items-center gap-1">
                            <ShieldAlert className="w-3 h-3 text-rose-700" />
                            <span>Procedural Gap Rule</span>
                          </span>
                        )}
                        {isNextStep && (
                          <span className="px-2 py-0.5 rounded-full text-[10px] font-mono font-bold bg-amber-50 text-amber-900 border border-amber-300 flex items-center gap-1">
                            <Zap className="w-3 h-3 text-amber-700" />
                            <span>Simulated Next Step</span>
                          </span>
                        )}
                        {task.impact_score && (
                          <span className="px-2 py-0.5 rounded-full text-[10px] font-mono font-bold bg-blue-50 text-blue-900 border border-blue-200">
                            Impact: {task.impact_score.toFixed(0)}/100
                          </span>
                        )}
                        <span className={cn(
                          "px-2 py-0.5 rounded-full text-[10px] font-mono font-bold uppercase tracking-wider border",
                          isHigh ? "bg-rose-50 text-rose-800 border-rose-200" : "bg-stone-50 text-stone-700 border-stone-200"
                        )}>
                          {task.priority} Priority
                        </span>
                        {task.assignedTo && (
                          <span className="px-2 py-0.5 rounded-full text-[10px] font-mono text-[#191410] bg-[#faf7f2] border border-[#d8d0c5] flex items-center gap-1">
                            <User className="w-3 h-3 text-[#8c8276]" />
                            <span>{task.assignedTo}</span>
                          </span>
                        )}
                      </div>

                      {/* Title & Reason */}
                      <h3 className={cn("font-serif font-bold text-base text-[#191410]", task.status === 'Completed' && "line-through text-stone-400")}>
                        {task.task}
                      </h3>
                      <p className="text-xs text-[#6e665d] leading-relaxed max-w-2xl">{task.reason}</p>
                      
                      {/* Related IDs */}
                      <div className="flex flex-wrap gap-2 pt-1">
                        {task.relatedContradictionId && (
                          <div className="flex items-center gap-1 px-2.5 py-1 rounded-md bg-rose-50 text-rose-800 border border-rose-200 text-[10px] font-mono font-semibold">
                            <AlertTriangle className="w-3 h-3" />
                            Resolves: {task.relatedContradictionId}
                          </div>
                        )}
                        {task.relatedHypothesisId && (
                          <div className="flex items-center gap-1 px-2.5 py-1 rounded-md bg-amber-50 text-amber-800 border border-amber-200 text-[10px] font-mono font-semibold">
                            <Lightbulb className="w-3 h-3" />
                            Tests: {task.relatedHypothesisId}
                          </div>
                        )}
                        {task.relatedEvidenceId && (
                          <div className="flex items-center gap-1 px-2.5 py-1 rounded-md bg-[#faf7f2] text-[#6e665d] border border-[#eae4d9] text-[10px] font-mono font-semibold">
                            Requires: {task.relatedEvidenceId}
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                  
                  {/* Action Buttons */}
                  <div className="flex md:flex-col gap-2 justify-center shrink-0 border-t md:border-t-0 md:border-l border-[#eae4d9] pt-3 md:pt-0 md:pl-4">
                    <button 
                      onClick={() => handleDismiss(task.id)}
                      disabled={dismissingId === task.id}
                      className="px-3.5 py-1.5 bg-[#faf7f2] hover:bg-[#eae4d9] text-[#6e665d] hover:text-[#d93829] border border-[#eae4d9] rounded-xl text-xs font-bold transition-all cursor-pointer whitespace-nowrap flex items-center justify-center gap-1"
                    >
                      <X className="w-3.5 h-3.5" />
                      <span>Dismiss</span>
                    </button>
                  </div>
                </CardContent>
              </Card>
            );
          })
        )}
      </div>

      {/* Modal Integration */}
      <GapsAndNextStepsModal
        isOpen={isGapsModalOpen}
        onClose={() => setIsGapsModalOpen(false)}
        caseId={caseId || ''}
        onTaskCreated={() => {
          loadTasks();
        }}
      />
    </div>
  );
}