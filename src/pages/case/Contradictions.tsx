import { useParams, Link } from 'react-router-dom';
import { useEffect, useState } from 'react';
import { contradictionService, investigationService, evidenceService } from '../../services';
import { Contradiction, Evidence } from '../../types';
import { Card, CardHeader, CardTitle, CardContent } from '../../components/ui/Card';
import { AlertTriangle, Clock, Sparkles, RefreshCw, CheckCircle, ShieldAlert, FileText, Check, ExternalLink, GitBranch, ArrowUpRight } from 'lucide-react';
import { cn } from '../../utils';
import { useCaseState } from '../../engine/useCaseState';

export function Contradictions() {
  const { caseId } = useParams();
  const [contradictions, setContradictions] = useState<Contradiction[]>([]);
  const [caseEvidence, setCaseEvidence] = useState<Evidence[]>([]);
  const [isScanning, setIsScanning] = useState(false);
  const [scanMessage, setScanMessage] = useState<string | null>(null);
  const [taskCreatedIds, setTaskCreatedIds] = useState<Record<string, boolean>>({});
  const stateTick = useCaseState();

  const loadContradictions = () => {
    if (caseId) {
      contradictionService.getContradictionsForCase(caseId).then(setContradictions);
      evidenceService.getEvidenceForCase(caseId).then(setCaseEvidence);
    }
  };

  useEffect(() => {
    loadContradictions();
  }, [caseId, stateTick]);

  const handleRunNLIScan = async () => {
    if (!caseId || isScanning) return;
    setIsScanning(true);
    setScanMessage('Extracting factual claims across evidence exhibits & running NLI inference...');
    try {
      const updated = await contradictionService.detectContradictions(caseId);
      setContradictions(updated);
      setScanMessage(`Scan complete: ${updated.length} forensic contradiction(s) verified via NLI.`);
      setTimeout(() => setScanMessage(null), 5000);
    } catch (err) {
      console.error('NLI Contradiction Scan error:', err);
      setScanMessage('Scan encountered an error. Check backend logs.');
      setTimeout(() => setScanMessage(null), 5000);
    } finally {
      setIsScanning(false);
    }
  };

  const handleDismiss = async (cId: string) => {
    await contradictionService.updateStatus(cId, 'Dismissed');
    setContradictions(prev => prev.map(c => c.id === cId ? { ...c, status: 'Dismissed' } : c));
  };

  const handleCreateTask = async (c: Contradiction) => {
    if (!caseId) return;
    try {
      await investigationService.createTask({
        caseId,
        task: `Resolve ${c.conflictType}: Verify conflicting assertions between ${c.sourceAId} and ${c.sourceBId}`,
        reason: `Automated investigation task generated from AI NLI Contradiction detection (${c.confidence}% confidence). Statement A: "${c.statementA.slice(0, 100)}..." vs Statement B: "${c.statementB.slice(0, 100)}..."`,
        relatedContradictionId: c.id,
        priority: 'High',
        status: 'Pending',
        assignedTo: 'Lead Forensic Investigator'
      });
      setTaskCreatedIds(prev => ({ ...prev, [c.id]: true }));
    } catch (err) {
      console.error('Failed to create task:', err);
    }
  };

  const resolveEvidenceTarget = (sourceStr: string) => {
    if (!sourceStr) return null;
    const direct = caseEvidence.find(e => 
      String(e.id) === sourceStr || 
      e.id === sourceStr.replace(/^E-/, '') ||
      `E-${e.id}` === sourceStr
    );
    if (direct) return direct;

    const lower = sourceStr.toLowerCase();
    const byName = caseEvidence.find(e => {
      const fn = (e.fileName || '').toLowerCase();
      return fn && (lower.includes(fn) || fn.includes(lower));
    });
    if (byName) return byName;

    const numMatch = sourceStr.match(/#?(\d+)/);
    if (numMatch) {
      const byNum = caseEvidence.find(e => String(e.id) === numMatch[1]);
      if (byNum) return byNum;
    }
    return null;
  };

  return (
    <div className="space-y-6 max-w-5xl mx-auto pb-12">
      {/* Header with Title and Action Button */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-border/40 pb-5">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-2xl font-serif font-bold text-[#191410]">Contradiction Detection</h1>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-red-500/10 text-red-600 border border-red-500/20">
              NLI Engine Active
            </span>
          </div>
          <p className="text-sm text-text-muted mt-1">
            Natural Language Inference (NLI) claims cross-comparison: extracts factual claims from exhibits and classifies pairwise conflicts into <span className="font-mono text-xs font-semibold text-emerald-600">ENTAILMENT</span>, <span className="font-mono text-xs font-semibold text-red-600">CONTRADICTION</span>, or <span className="font-mono text-xs font-semibold text-slate-500">NEUTRAL</span>.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handleRunNLIScan}
            disabled={isScanning}
            className={cn(
              "flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-semibold transition-all shadow-md cursor-pointer",
              isScanning
                ? "bg-amber-500/20 text-amber-700 border border-amber-500/30 cursor-wait"
                : "bg-red-600 hover:bg-red-700 text-white shadow-red-600/20 active:scale-98"
            )}
          >
            {isScanning ? (
              <>
                <RefreshCw className="w-4 h-4 animate-spin text-amber-600" />
                <span>Comparing Claims (NLI)...</span>
              </>
            ) : (
              <>
                <Sparkles className="w-4 h-4" />
                <span>Run NLI Contradiction Scan</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Pipeline Architecture Indicator */}
      <div className="p-4 rounded-xl bg-surface border border-border/60 shadow-xs">
        <div className="flex flex-wrap items-center justify-between gap-3 text-xs text-text-muted">
          <div className="flex items-center gap-2 font-mono">
            <span className="px-2 py-0.5 rounded bg-blue-500/10 text-blue-700 font-semibold border border-blue-500/20">Evidence A</span>
            <span>&rarr; extracted claims</span>
            <span className="font-bold text-text">&times;</span>
            <span className="px-2 py-0.5 rounded bg-purple-500/10 text-purple-700 font-semibold border border-purple-500/20">Evidence B</span>
            <span>&rarr; extracted claims</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-text-muted font-medium">NLI Classifier:</span>
            <span className="px-2 py-0.5 rounded font-mono font-bold bg-red-500/10 text-red-600 border border-red-500/20">CONTRADICTION</span>
            <span className="px-2 py-0.5 rounded font-mono bg-emerald-500/10 text-emerald-600 border border-emerald-500/20">ENTAILMENT</span>
            <span className="px-2 py-0.5 rounded font-mono bg-slate-500/10 text-slate-600 border border-slate-500/20">NEUTRAL</span>
          </div>
        </div>
        {scanMessage && (
          <div className="mt-3 pt-3 border-t border-border/40 text-xs font-medium text-amber-700 flex items-center gap-2 animate-fade-in">
            <Sparkles className="w-3.5 h-3.5 text-amber-500 animate-pulse" />
            <span>{scanMessage}</span>
          </div>
        )}
      </div>

      {/* Contradictions List */}
      <div className="grid gap-6">
        {contradictions.length === 0 ? (
          <Card className="p-12 text-center border-dashed">
            <div className="w-12 h-12 rounded-full bg-emerald-500/10 text-emerald-600 flex items-center justify-center mx-auto mb-3">
              <CheckCircle className="w-6 h-6" />
            </div>
            <h3 className="text-base font-serif font-bold text-[#191410]">No Logical Contradictions Detected</h3>
            <p className="text-sm text-text-muted mt-1 max-w-md mx-auto">
              All extracted factual claims across evidentiary exhibits currently align or are mutually neutral. Click "Run NLI Contradiction Scan" above to re-evaluate after adding exhibits.
            </p>
          </Card>
        ) : (
          contradictions.map((c, idx) => {
            const targetA = resolveEvidenceTarget(c.sourceAId);
            const targetB = resolveEvidenceTarget(c.sourceBId);

            return (
              <Card key={`${c.id}-${idx}`} className={cn(
                "border shadow-sm overflow-hidden transition-all bg-white",
                c.status === 'Dismissed' 
                  ? "opacity-60 border-border bg-surface/50" 
                  : "border-red-500/20 shadow-[0_0_15px_rgba(239,68,68,0.05)]"
              )}>
                <div className="h-1 w-full bg-gradient-to-r from-red-500/60 to-orange-500/60" />
                <CardHeader className="bg-red-500/5 border-b border-red-500/10 py-3.5 px-6">
                  <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-2 w-full">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-full bg-red-500/20 flex items-center justify-center border border-red-500/30 shrink-0">
                        <AlertTriangle className="w-4 h-4 text-red-600" />
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <CardTitle className="text-[#191410] text-base font-bold">{c.conflictType}</CardTitle>
                          <span className="font-mono text-[10px] px-1.5 py-0.5 rounded bg-surface border border-border text-text-muted font-bold">
                            NLI: CONTRADICTION
                          </span>
                        </div>
                        <div className="text-xs text-text-muted mt-0.5">Reference: {c.id}</div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2.5">
                      <span className="px-2.5 py-1 rounded-full text-xs font-bold border border-border bg-surface text-text-muted">
                        {Math.round(c.confidence)}% NLI Confidence
                      </span>
                      <span className={cn(
                        "px-2.5 py-1 rounded-full text-xs font-bold border uppercase tracking-wider flex items-center gap-1.5",
                        c.status === 'Detected' ? "bg-red-500/10 text-red-600 border-red-500/30" :
                        c.status === 'Dismissed' ? "bg-slate-500/10 text-slate-500 border-slate-500/30" :
                        "bg-yellow-500/10 text-yellow-600 border-yellow-500/30"
                      )}>
                        {c.status === 'Detected' ? <AlertTriangle className="w-3 h-3" /> : <Clock className="w-3 h-3" />}
                        {c.status}
                      </span>
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="p-6">
                  <div className="grid grid-cols-1 md:grid-cols-5 gap-4 items-stretch">
                    {/* Evidence A Claim */}
                    <div className="md:col-span-2 bg-[#f8fafc] p-4 rounded-xl border border-blue-200/60 relative overflow-hidden group">
                      <div className="absolute top-0 left-0 w-1.5 h-full bg-blue-500" />
                      <div className="text-xs font-bold text-blue-700 uppercase tracking-wider mb-2.5 flex items-center justify-between gap-2">
                        <span className="flex items-center gap-1">
                          <GitBranch className="w-3.5 h-3.5 text-blue-600" />
                          <span>Claim A Provenance</span>
                        </span>
                        {targetA ? (
                          <Link
                            to={`/cases/${caseId}/evidence/${targetA.id}`}
                            className="inline-flex items-center gap-1 px-2.5 py-1 rounded bg-blue-100/70 hover:bg-blue-200 text-blue-800 border border-blue-300 text-[11px] font-mono font-bold transition-all hover:border-blue-500 group/link"
                            title={`Inspect source exhibit: ${targetA.fileName}`}
                          >
                            <FileText className="w-3 h-3 text-blue-700 shrink-0" />
                            <span className="truncate max-w-[130px]">{targetA.fileName}</span>
                            <ExternalLink className="w-2.5 h-2.5 opacity-70 group-hover/link:opacity-100 shrink-0" />
                          </Link>
                        ) : (
                          <span className="text-text-muted font-mono font-normal truncate max-w-[140px]" title={c.sourceAId}>
                            {c.sourceAId}
                          </span>
                        )}
                      </div>
                      <p className="text-sm text-[#191410] leading-relaxed font-sans">{c.statementA}</p>
                      {targetA && (
                        <div className="mt-3 pt-2.5 border-t border-blue-200/50 flex items-center justify-between text-[11px] font-mono">
                          <span className="text-blue-700">└── Exhibit #{targetA.id}</span>
                          <Link 
                            to={`/cases/${caseId}/evidence/${targetA.id}`}
                            className="text-blue-700 hover:text-blue-900 font-bold flex items-center gap-0.5 hover:underline"
                          >
                            Inspect Source <ArrowUpRight className="w-3 h-3" />
                          </Link>
                        </div>
                      )}
                    </div>

                    {/* VS Indicator */}
                    <div className="md:col-span-1 flex flex-col items-center justify-center py-2">
                      <div className="w-9 h-9 rounded-full bg-red-500/10 border border-red-500/20 flex items-center justify-center shadow-xs">
                        <span className="text-red-600 font-bold text-xs">VS</span>
                      </div>
                      <div className="h-full w-px bg-red-500/20 my-2 hidden md:block" />
                    </div>

                    {/* Evidence B Claim */}
                    <div className="md:col-span-2 bg-[#faf5ff] p-4 rounded-xl border border-purple-200/60 relative overflow-hidden group">
                      <div className="absolute top-0 left-0 w-1.5 h-full bg-purple-500" />
                      <div className="text-xs font-bold text-purple-700 uppercase tracking-wider mb-2.5 flex items-center justify-between gap-2">
                        <span className="flex items-center gap-1">
                          <GitBranch className="w-3.5 h-3.5 text-purple-600" />
                          <span>Claim B Provenance</span>
                        </span>
                        {targetB ? (
                          <Link
                            to={`/cases/${caseId}/evidence/${targetB.id}`}
                            className="inline-flex items-center gap-1 px-2.5 py-1 rounded bg-purple-100/70 hover:bg-purple-200 text-purple-800 border border-purple-300 text-[11px] font-mono font-bold transition-all hover:border-purple-500 group/link"
                            title={`Inspect source exhibit: ${targetB.fileName}`}
                          >
                            <FileText className="w-3 h-3 text-purple-700 shrink-0" />
                            <span className="truncate max-w-[130px]">{targetB.fileName}</span>
                            <ExternalLink className="w-2.5 h-2.5 opacity-70 group-hover/link:opacity-100 shrink-0" />
                          </Link>
                        ) : (
                          <span className="text-text-muted font-mono font-normal truncate max-w-[140px]" title={c.sourceBId}>
                            {c.sourceBId}
                          </span>
                        )}
                      </div>
                      <p className="text-sm text-[#191410] leading-relaxed font-sans">{c.statementB}</p>
                      {targetB && (
                        <div className="mt-3 pt-2.5 border-t border-purple-200/50 flex items-center justify-between text-[11px] font-mono">
                          <span className="text-purple-700">└── Exhibit #{targetB.id}</span>
                          <Link 
                            to={`/cases/${caseId}/evidence/${targetB.id}`}
                            className="text-purple-700 hover:text-purple-900 font-bold flex items-center gap-0.5 hover:underline"
                          >
                            Inspect Source <ArrowUpRight className="w-3 h-3" />
                          </Link>
                        </div>
                      )}
                    </div>
                  </div>
                  
                  {/* Actions */}
                  <div className="mt-5 pt-4 border-t border-border/50 flex flex-wrap items-center justify-between gap-3">
                  <div className="text-xs text-text-muted flex items-center gap-1.5">
                    <ShieldAlert className="w-3.5 h-3.5 text-amber-500" />
                    <span>Cross-exhibit evidentiary proposition conflict</span>
                  </div>

                  <div className="flex items-center gap-2.5">
                    {c.status !== 'Dismissed' && (
                      <button
                        onClick={() => handleDismiss(c.id)}
                        className="px-3 py-1.5 text-xs font-medium text-text-muted hover:text-text bg-surface hover:bg-surface-hover border border-border rounded-lg transition-colors"
                      >
                        Dismiss
                      </button>
                    )}
                    <button
                      onClick={() => handleCreateTask(c)}
                      disabled={taskCreatedIds[c.id]}
                      className={cn(
                        "flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-semibold rounded-lg transition-all shadow-xs",
                        taskCreatedIds[c.id]
                          ? "bg-emerald-500/20 text-emerald-700 border border-emerald-500/30 cursor-default"
                          : "text-white bg-primary hover:bg-primary-hover shadow-primary/20"
                      )}
                    >
                      {taskCreatedIds[c.id] ? (
                        <>
                          <Check className="w-3.5 h-3.5" />
                          <span>Task Created</span>
                        </>
                      ) : (
                        <>
                          <FileText className="w-3.5 h-3.5" />
                          <span>Create Investigation Task</span>
                        </>
                      )}
                    </button>
                  </div>
                </div>
              </CardContent>
            </Card>
          );
        }))}
      </div>
    </div>
  );
}