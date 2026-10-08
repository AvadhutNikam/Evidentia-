// src/pages/case/ActivityLog.tsx
import { useParams } from 'react-router-dom';
import { useEffect, useState, useMemo } from 'react';
import { auditService } from '../../services';
import type { AuditLogEntry, ChainVerificationResult } from '../../types';
import { Card, CardContent } from '../../components/ui/Card';
import {
  Activity, FileText, Users, Clock, Lightbulb, AlertTriangle, CheckSquare, Plus,
  ShieldCheck, ShieldAlert, RefreshCw, Key, Lock, ArrowRight, Copy, Check, Filter, Search
} from 'lucide-react';
import { cn } from '../../utils';

export function ActivityLog() {
  const { caseId } = useParams();
  const [logs, setLogs] = useState<AuditLogEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [verifying, setVerifying] = useState(false);
  const [verificationResult, setVerificationResult] = useState<ChainVerificationResult | null>(null);
  const [copiedHash, setCopiedHash] = useState<string | null>(null);

  // Filters
  const [actionFilter, setActionFilter] = useState<string>('ALL');
  const [userFilter, setUserFilter] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState<string>('');

  const fetchLogs = async () => {
    if (!caseId) return;
    try {
      setLoading(true);
      const data = await auditService.getCaseAuditLogs(caseId);
      setLogs(data);
    } catch (err) {
      console.error('Failed to load audit logs:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLogs();
    // Run verification automatically on mount to show audit status
    handleVerifyChain();
  }, [caseId]);

  const handleVerifyChain = async () => {
    try {
      setVerifying(true);
      const result = await auditService.verifyAuditChain(caseId);
      setVerificationResult(result);
    } catch (err) {
      console.error('Verification failed:', err);
    } finally {
      setVerifying(false);
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedHash(text);
    setTimeout(() => setCopiedHash(null), 2000);
  };

  const uniqueUsers = useMemo(() => {
    const names = new Set(logs.map(l => l.user_name).filter(Boolean));
    return ['ALL', ...Array.from(names)];
  }, [logs]);

  const uniqueActions = useMemo(() => {
    const acts = new Set(logs.map(l => l.action_type).filter(Boolean));
    return ['ALL', ...Array.from(acts)];
  }, [logs]);

  const filteredLogs = useMemo(() => {
    return logs.filter(l => {
      const matchAction = actionFilter === 'ALL' || l.action_type === actionFilter;
      const matchUser = userFilter === 'ALL' || l.user_name === userFilter;
      const matchSearch = !searchQuery.trim() || 
        l.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
        l.action_type.toLowerCase().includes(searchQuery.toLowerCase()) ||
        l.target_type.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (l.target_id && l.target_id.toLowerCase().includes(searchQuery.toLowerCase())) ||
        l.current_hash.toLowerCase().includes(searchQuery.toLowerCase());
      return matchAction && matchUser && matchSearch;
    });
  }, [logs, actionFilter, userFilter, searchQuery]);

  const getActionConfig = (action: string) => {
    switch (action.toUpperCase()) {
      case 'EVIDENCE_UPLOAD':
        return { label: 'Evidence Upload', icon: FileText, color: 'text-blue-400 bg-blue-500/10 border-blue-500/30' };
      case 'INTEGRITY_VERIFY':
        return { label: 'SHA-256 Verified', icon: ShieldCheck, color: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30' };
      case 'TAMPER_DETECTED':
        return { label: 'Tamper Alert', icon: ShieldAlert, color: 'text-rose-400 bg-rose-500/10 border-rose-500/30' };
      case 'CLASSIFICATION_OVERRIDE':
        return { label: 'Analyst Override', icon: Lightbulb, color: 'text-amber-400 bg-amber-500/10 border-amber-500/30' };
      case 'SCORING_RECALCULATE':
        return { label: 'ACH Recalculate', icon: RefreshCw, color: 'text-cyan-400 bg-cyan-500/10 border-cyan-500/30' };
      case 'EVIDENCE_SOFT_DELETE':
        return { label: 'Soft Delete', icon: AlertTriangle, color: 'text-orange-400 bg-orange-500/10 border-orange-500/30' };
      case 'LOGIN':
        return { label: 'User Login', icon: Lock, color: 'text-indigo-400 bg-indigo-500/10 border-indigo-500/30' };
      case 'CASE_CREATE':
        return { label: 'Case Registered', icon: Plus, color: 'text-green-400 bg-green-500/10 border-green-500/30' };
      default:
        return { label: action, icon: Activity, color: 'text-slate-400 bg-slate-500/10 border-slate-500/30' };
    }
  };

  return (
    <div className="space-y-6 pb-24 max-w-7xl mx-auto">
      {/* Page Header with Real-Time Cryptographic Ledger State */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-xs font-mono text-cyan-400 uppercase tracking-wider mb-1">
            <Lock className="w-3.5 h-3.5" /> Immutable Audit Ledger • Sec. 65B Certified
          </div>
          <h1 className="text-2xl lg:text-3xl font-serif font-bold text-white tracking-tight">
            Case Activity & Cryptographic Audit Log
          </h1>
          <p className="text-sm text-text-muted mt-1">
            Append-only tamper-evident event stream chained using SHA-256 Merkle proofs.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handleVerifyChain}
            disabled={verifying}
            className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white font-semibold rounded-lg shadow-lg shadow-emerald-900/30 transition-all text-xs disabled:opacity-50"
          >
            {verifying ? (
              <>
                <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                <span>Verifying Hash Chains...</span>
              </>
            ) : (
              <>
                <ShieldCheck className="w-4 h-4 text-emerald-200" />
                <span>Verify Merkle Audit Chain</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Merkle Cryptographic Integrity Status Card */}
      {verificationResult && (
        <div className={cn(
          "p-4 rounded-xl border flex flex-col md:flex-row md:items-center justify-between gap-4 transition-all shadow-lg",
          verificationResult.chain_intact
            ? "bg-[#0b1a1a] border-emerald-500/30 text-emerald-300"
            : "bg-[#240b0b] border-rose-500/50 text-rose-300"
        )}>
          <div className="flex items-start md:items-center gap-3">
            <div className={cn(
              "w-10 h-10 rounded-lg flex items-center justify-center shrink-0 border",
              verificationResult.chain_intact
                ? "bg-emerald-500/20 border-emerald-500/40 text-emerald-400"
                : "bg-rose-500/20 border-rose-500/40 text-rose-400"
            )}>
              {verificationResult.chain_intact ? <ShieldCheck className="w-5 h-5" /> : <ShieldAlert className="w-5 h-5" />}
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-bold text-sm tracking-wide text-white">
                  {verificationResult.chain_intact ? "Cryptographic Merkle Chain Verified Intact" : "CRITICAL TAMPER WARNING DETECTED"}
                </span>
                <span className={cn(
                  "px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase border",
                  verificationResult.chain_intact
                    ? "bg-emerald-500/20 text-emerald-300 border-emerald-500/40"
                    : "bg-rose-500/20 text-rose-300 border-rose-500/40"
                )}>
                  {verificationResult.status}
                </span>
              </div>
              <p className="text-xs text-text-muted mt-0.5">
                {verificationResult.message}
              </p>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-4 text-xs font-mono text-text-muted border-t md:border-t-0 md:border-l border-border/60 pt-3 md:pt-0 md:pl-5">
            <div>
              <div className="text-[10px] uppercase text-text-muted">Verified Blocks</div>
              <div className="text-white font-bold">{verificationResult.verified_count} / {verificationResult.total_entries}</div>
            </div>
            <div>
              <div className="text-[10px] uppercase text-text-muted">Genesis Hash</div>
              <div className="text-white font-bold">{verificationResult.genesis_hash.slice(0, 10)}...</div>
            </div>
            <div>
              <div className="text-[10px] uppercase text-text-muted">Ledger Tip Hash</div>
              <div className="text-emerald-400 font-bold">{verificationResult.latest_hash.slice(0, 10)}...</div>
            </div>
          </div>
        </div>
      )}

      {/* Filter and Search Bar */}
      <Card className="p-4 bg-surface border-border">
        <div className="flex flex-col md:flex-row items-stretch md:items-center justify-between gap-3">
          <div className="flex-1 relative">
            <Search className="w-4 h-4 text-text-muted absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search description, target, hash fingerprint, or action..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-background border border-border rounded-lg pl-9 pr-3 py-1.5 text-xs text-white placeholder-text-muted focus:outline-none focus:border-cyan-500"
            />
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <div className="flex items-center gap-1.5 text-xs text-text-muted">
              <Filter className="w-3.5 h-3.5 text-cyan-400" />
              <span>Action:</span>
            </div>
            <select
              value={actionFilter}
              onChange={(e) => setActionFilter(e.target.value)}
              className="bg-background border border-border rounded-lg px-2.5 py-1.5 text-xs text-white focus:outline-none focus:border-cyan-500"
            >
              {uniqueActions.map(act => (
                <option key={act} value={act}>{act}</option>
              ))}
            </select>

            <div className="flex items-center gap-1.5 text-xs text-text-muted ml-2">
              <Users className="w-3.5 h-3.5 text-cyan-400" />
              <span>Actor:</span>
            </div>
            <select
              value={userFilter}
              onChange={(e) => setUserFilter(e.target.value)}
              className="bg-background border border-border rounded-lg px-2.5 py-1.5 text-xs text-white focus:outline-none focus:border-cyan-500"
            >
              {uniqueUsers.map(usr => (
                <option key={usr} value={usr}>{usr}</option>
              ))}
            </select>
          </div>
        </div>
      </Card>

      {/* Audit Ledger Block Feed */}
      {loading ? (
        <div className="animate-pulse space-y-3">
          {[1, 2, 3, 4].map(n => (
            <div key={n} className="h-24 bg-surface rounded-xl border border-border" />
          ))}
        </div>
      ) : filteredLogs.length === 0 ? (
        <Card className="p-12 text-center bg-surface border-border">
          <Activity className="w-10 h-10 text-text-muted mx-auto mb-3 opacity-40" />
          <h3 className="text-sm font-semibold text-white">No Audit Entries Match Filter</h3>
          <p className="text-xs text-text-muted mt-1">Adjust filters or upload new evidence to populate the cryptographic ledger.</p>
        </Card>
      ) : (
        <div className="relative border-l-2 border-border/80 ml-6 space-y-4">
          {filteredLogs.map((entry, index) => {
            const conf = getActionConfig(entry.action_type);
            const Icon = conf.icon;
            const isLatest = index === 0;

            return (
              <div key={entry.id} className="relative flex items-start gap-4 group">
                {/* Node on Timeline */}
                <div className={cn(
                  "absolute -left-[25px] w-10 h-10 rounded-full border-2 flex items-center justify-center transition-all z-10 shadow-md",
                  isLatest ? "bg-surface border-cyan-400 scale-105" : "bg-surface border-border group-hover:border-cyan-500/50"
                )}>
                  <Icon className={cn("w-4 h-4", conf.color.split(' ')[0])} />
                </div>

                {/* Entry Card */}
                <Card className="flex-1 ml-4 bg-surface border-border hover:border-cyan-500/30 transition-all">
                  <CardContent className="p-4 space-y-3">
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-border/40 pb-2.5">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className={cn(
                          "px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold uppercase tracking-wider border",
                          conf.color
                        )}>
                          {conf.label}
                        </span>
                        <span className="text-xs font-semibold text-white">
                          {entry.user_name}
                        </span>
                        {entry.user_role && (
                          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-background border border-border text-text-muted uppercase">
                            {entry.user_role}
                          </span>
                        )}
                        <span className="text-text-muted text-xs">•</span>
                        <span className="text-[11px] font-mono text-cyan-400">
                          Target: {entry.target_type} {entry.target_id ? `(#${entry.target_id})` : ''}
                        </span>
                      </div>

                      <div className="flex items-center gap-2 text-[11px] text-text-muted font-mono whitespace-nowrap">
                        <Clock className="w-3 h-3 text-text-muted" />
                        <span>{new Date(entry.timestamp).toLocaleString()}</span>
                      </div>
                    </div>

                    {/* Description Body */}
                    <p className="text-xs text-slate-200 leading-relaxed font-sans">
                      {entry.description}
                    </p>

                    {/* Before & After Values for Auditing Changes */}
                    {(entry.before_value || entry.after_value) && (
                      <div className="p-2.5 rounded-lg bg-background/80 border border-border/60 text-[11px] font-mono flex flex-wrap items-center gap-3">
                        {entry.before_value && (
                          <div className="flex items-center gap-1.5 text-rose-300">
                            <span className="text-text-muted uppercase text-[9px]">Before:</span>
                            <span className="line-through opacity-80">{entry.before_value}</span>
                          </div>
                        )}
                        {entry.before_value && entry.after_value && (
                          <ArrowRight className="w-3 h-3 text-text-muted" />
                        )}
                        {entry.after_value && (
                          <div className="flex items-center gap-1.5 text-emerald-300">
                            <span className="text-text-muted uppercase text-[9px]">After:</span>
                            <span className="font-bold">{entry.after_value}</span>
                          </div>
                        )}
                      </div>
                    )}

                    {/* Merkle Cryptographic Chaining Footer */}
                    <div className="pt-2 border-t border-border/40 flex flex-col md:flex-row md:items-center justify-between gap-2 text-[10px] font-mono text-text-muted">
                      <div className="flex items-center gap-3 flex-wrap">
                        <span className="text-cyan-400 font-bold">Block #{entry.id}</span>
                        <div className="flex items-center gap-1">
                          <span>Prev Hash:</span>
                          <span className="text-slate-400">{entry.previous_hash.slice(0, 12)}...</span>
                        </div>
                        <div className="flex items-center gap-1">
                          <span>Block Hash:</span>
                          <span className="text-emerald-400">{entry.current_hash.slice(0, 16)}...</span>
                        </div>
                      </div>

                      <button
                        onClick={() => copyToClipboard(entry.current_hash)}
                        className="flex items-center gap-1 text-[10px] text-text-muted hover:text-white transition-colors cursor-pointer self-start md:self-auto"
                        title="Copy full 64-char SHA-256 block hash"
                      >
                        {copiedHash === entry.current_hash ? (
                          <>
                            <Check className="w-3 h-3 text-emerald-400" />
                            <span className="text-emerald-400">Copied</span>
                          </>
                        ) : (
                          <>
                            <Copy className="w-3 h-3" />
                            <span>Copy Digest</span>
                          </>
                        )}
                      </button>
                    </div>
                  </CardContent>
                </Card>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
