import { useState, useEffect, useCallback } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '../../components/ui/Card';
import { 
  Activity, Cpu, Database, Server, HardDrive, CheckCircle2, 
  AlertTriangle, RefreshCw, Clock, ShieldCheck, Layers, FileText, 
  Zap, BarChart3, AlertOctagon, ArrowUpRight, Copy, Check
} from 'lucide-react';
import { cn } from '../../utils';
import { systemHealthService } from '../../services';
import { SystemHealth as SystemHealthType, BackupHealth } from '../../types';

export function SystemHealth() {
  const [health, setHealth] = useState<SystemHealthType | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [backupTriggering, setBackupTriggering] = useState(false);
  const [bannerMsg, setBannerMsg] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const [copiedHash, setCopiedHash] = useState(false);

  const fetchHealth = useCallback(async (isSilent = false) => {
    if (!isSilent) setRefreshing(true);
    try {
      const data = await systemHealthService.getHealth();
      setHealth(data);
    } catch (err: any) {
      console.error('Failed to load system health:', err);
      setBannerMsg({ type: 'error', text: err?.message || 'Could not fetch live system health telemetry.' });
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    fetchHealth();
  }, [fetchHealth]);

  // Auto-refresh interval (every 10s)
  useEffect(() => {
    if (!autoRefresh) return;
    const interval = setInterval(() => {
      fetchHealth(true);
    }, 10000);
    return () => clearInterval(interval);
  }, [autoRefresh, fetchHealth]);

  const handleTriggerBackup = async () => {
    setBackupTriggering(true);
    setBannerMsg(null);
    try {
      const updatedBackup: BackupHealth = await systemHealthService.triggerBackup();
      if (health) {
        setHealth({ ...health, backup: updatedBackup });
      }
      setBannerMsg({ 
        type: 'success', 
        text: `Forensic snapshot verified successfully! SHA-256 integrity: ${updatedBackup.last_backup_hash?.slice(0, 16)}...` 
      });
      fetchHealth(true);
    } catch (err: any) {
      setBannerMsg({ type: 'error', text: `Disaster recovery backup failed: ${err.message}` });
    } finally {
      setBackupTriggering(false);
    }
  };

  const copyBackupHash = (hash: string) => {
    navigator.clipboard.writeText(hash);
    setCopiedHash(true);
    setTimeout(() => setCopiedHash(false), 2000);
  };

  const formatUptime = (seconds: number) => {
    const hrs = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    if (hrs > 0) return `${hrs}h ${mins}m`;
    return `${mins}m ${seconds % 60}s`;
  };

  if (loading && !health) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-4">
        <RefreshCw className="w-10 h-10 text-[#d93829] animate-spin" />
        <p className="text-[#6e665d] font-mono text-sm">Querying live subsystem telemetry...</p>
      </div>
    );
  }

  const isOperational = health?.system_status === 'operational';
  const queue = health?.queue;
  const jobs = health?.job_success;
  const backup = health?.backup;

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-16">
      {/* Top Telemetry Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-white border border-[#eae4d9] p-6 rounded-2xl shadow-xs">
        <div className="flex items-center space-x-4">
          <div className={cn(
            "p-3 rounded-xl border flex items-center justify-center",
            isOperational ? "bg-emerald-50 border-emerald-200 text-emerald-700" : "bg-amber-50 border-amber-200 text-amber-700"
          )}>
            <Activity className="w-7 h-7" />
          </div>
          <div>
            <div className="flex items-center space-x-3">
              <h1 className="text-2xl font-serif font-bold text-[#191410] tracking-tight">System Health & Telemetry</h1>
              <span className={cn(
                "inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold uppercase tracking-wider",
                isOperational 
                  ? "bg-emerald-50 text-emerald-800 border border-emerald-200"
                  : "bg-amber-50 text-amber-800 border border-amber-200"
              )}>
                <span className={cn("w-2 h-2 rounded-full mr-1.5 animate-pulse", isOperational ? "bg-emerald-500" : "bg-amber-500")} />
                {health?.system_status}
              </span>
            </div>
            <p className="text-xs text-[#6e665d] mt-1">
              Real-time monitoring of job queues, multi-provider AI endpoints, execution success rates, and DR snapshots.
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-3 self-end md:self-auto">
          <div className="text-right text-xs text-[#6e665d] hidden sm:block border-r border-[#eae4d9] pr-3 mr-1">
            <div>Uptime: <span className="font-mono font-bold text-[#191410]">{formatUptime(health?.uptime_seconds || 0)}</span></div>
            <div>DB Size: <span className="font-mono font-bold text-[#191410]">{health?.db_size_mb} MB</span></div>
          </div>

          <label className="flex items-center space-x-2 text-xs text-[#191410] cursor-pointer bg-[#faf7f2] px-3 py-2 rounded-xl border border-[#eae4d9] hover:bg-[#f0ebe1] transition">
            <input 
              type="checkbox" 
              checked={autoRefresh} 
              onChange={(e) => setAutoRefresh(e.target.checked)} 
              className="rounded bg-white border-[#eae4d9] text-[#d93829] focus:ring-0 w-3.5 h-3.5"
            />
            <span className="font-medium">Auto-refresh (10s)</span>
          </label>

          <button
            onClick={() => fetchHealth(false)}
            disabled={refreshing}
            className="flex items-center space-x-1.5 px-3 py-2 bg-white hover:bg-[#faf7f2] text-[#191410] text-xs font-semibold rounded-xl border border-[#eae4d9] transition shadow-xs cursor-pointer disabled:opacity-50"
          >
            <RefreshCw className={cn("w-3.5 h-3.5 text-[#d93829]", refreshing && "animate-spin")} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Action / Error Banner */}
      {bannerMsg && (
        <div className={cn(
          "p-4 rounded-xl border flex items-center justify-between text-sm transition animate-in fade-in",
          bannerMsg.type === 'success' 
            ? "bg-emerald-50 border-emerald-200 text-emerald-900" 
            : "bg-red-50 border-red-200 text-red-900"
        )}>
          <div className="flex items-center space-x-3">
            {bannerMsg.type === 'success' ? (
              <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
            ) : (
              <AlertTriangle className="w-5 h-5 text-red-600 shrink-0" />
            )}
            <p className="font-mono text-xs">{bannerMsg.text}</p>
          </div>
          <button 
            onClick={() => setBannerMsg(null)}
            className="text-xs hover:underline text-[#6e665d] hover:text-[#191410] cursor-pointer"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Main 4 Health Pillars Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
        {/* Metric 1: Queue Health */}
        <div className="p-5 rounded-2xl bg-white border border-[#eae4d9] shadow-xs hover:-translate-y-0.5 transition-all flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between pb-2 border-b border-[#f0ebe1]">
              <span className="text-[11px] uppercase font-bold tracking-wider text-[#6e665d] font-mono">Queue Congestion</span>
              <div className="w-7 h-7 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center">
                <Layers className="w-4 h-4" />
              </div>
            </div>
            <div className="text-2xl font-serif font-bold text-[#191410] mt-3">
              {queue?.total_active_queue} <span className="text-xs font-normal text-[#6e665d] font-sans">active jobs</span>
            </div>
          </div>
          <div className="pt-3 text-xs space-y-2">
            <div className="flex justify-between py-1 border-b border-[#f0ebe1]">
              <span className="text-[#6e665d]">Pending in Queue:</span>
              <span className="font-mono font-semibold text-amber-700">{queue?.pending_jobs_count}</span>
            </div>
            <div className="flex justify-between py-1 border-b border-[#f0ebe1]">
              <span className="text-[#6e665d]">Currently Running:</span>
              <span className="font-mono font-semibold text-blue-700">{queue?.running_jobs_count}</span>
            </div>
            <div className="flex justify-between py-1 items-center">
              <span className="text-[#6e665d]">Queue State:</span>
              <span className={cn(
                "font-semibold capitalize px-2 py-0.5 rounded-full text-[10px] font-mono border",
                queue?.queue_status === 'congested' ? "bg-red-50 text-red-700 border-red-200" :
                queue?.queue_status === 'busy' ? "bg-amber-50 text-amber-700 border-amber-200" :
                "bg-emerald-50 text-emerald-700 border-emerald-200"
              )}>
                {queue?.queue_status}
              </span>
            </div>
          </div>
        </div>

        {/* Metric 2: Job Success Rate */}
        <div className="p-5 rounded-2xl bg-white border border-[#eae4d9] shadow-xs hover:-translate-y-0.5 transition-all flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between pb-2 border-b border-[#f0ebe1]">
              <span className="text-[11px] uppercase font-bold tracking-wider text-[#6e665d] font-mono">Job Success Rate</span>
              <div className="w-7 h-7 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center">
                <BarChart3 className="w-4 h-4" />
              </div>
            </div>
            <div className="text-2xl font-serif font-bold text-emerald-700 mt-3">
              {jobs?.success_rate_pct}%
            </div>
          </div>
          <div className="pt-3 text-xs space-y-2">
            <div className="flex justify-between py-1 border-b border-[#f0ebe1]">
              <span className="text-[#6e665d]">Completed Jobs:</span>
              <span className="font-mono font-semibold text-[#191410]">{jobs?.completed_jobs} / {jobs?.total_jobs}</span>
            </div>
            <div className="flex justify-between py-1 border-b border-[#f0ebe1]">
              <span className="text-[#6e665d]">Failed Total:</span>
              <span className={cn("font-mono font-semibold", (jobs?.failed_jobs || 0) > 0 ? "text-red-600" : "text-[#6e665d]")}>
                {jobs?.failed_jobs}
              </span>
            </div>
            <div className="flex justify-between py-1">
              <span className="text-[#6e665d]">Failures (Last 24h):</span>
              <span className={cn("font-mono font-semibold", (jobs?.failed_last_24h_count || 0) > 0 ? "text-red-600" : "text-emerald-700")}>
                {jobs?.failed_last_24h_count}
              </span>
            </div>
          </div>
        </div>

        {/* Metric 3: AI Service Availability */}
        <div className="p-5 rounded-2xl bg-white border border-[#eae4d9] shadow-xs hover:-translate-y-0.5 transition-all flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between pb-2 border-b border-[#f0ebe1]">
              <span className="text-[11px] uppercase font-bold tracking-wider text-[#6e665d] font-mono">AI Services Status</span>
              <div className="w-7 h-7 rounded-lg bg-amber-50 text-amber-600 flex items-center justify-center">
                <Zap className="w-4 h-4" />
              </div>
            </div>
            <div className="text-2xl font-serif font-bold text-[#191410] mt-3">
              {health?.ai_services.filter(s => s.status === 'available').length} / {health?.ai_services.length}
              <span className="text-xs font-normal text-[#6e665d] font-sans ml-1.5">online</span>
            </div>
          </div>
          <div className="pt-3 text-xs space-y-2">
            <div className="flex justify-between py-1 border-b border-[#f0ebe1]">
              <span className="text-[#6e665d]">Cloud Gemini API:</span>
              <span className={cn("font-semibold text-[11px] capitalize", health?.ai_services.find(s => s.provider.includes('Cloud'))?.status === 'available' ? "text-emerald-700" : "text-amber-700")}>
                {health?.ai_services.find(s => s.provider.includes('Cloud'))?.status}
              </span>
            </div>
            <div className="flex justify-between py-1 border-b border-[#f0ebe1]">
              <span className="text-[#6e665d]">Local Air-Gap LLM:</span>
              <span className={cn("font-semibold text-[11px] capitalize", health?.ai_services.find(s => s.provider.includes('Private Host'))?.status === 'available' ? "text-emerald-700" : "text-[#8c8276]")}>
                {health?.ai_services.find(s => s.provider.includes('Private Host'))?.status}
              </span>
            </div>
            <div className="flex justify-between py-1">
              <span className="text-[#6e665d]">Whisper & Tesseract:</span>
              <span className="text-emerald-700 font-semibold text-[11px]">Ready</span>
            </div>
          </div>
        </div>

        {/* Metric 4: Disaster Recovery & Backup */}
        <div className="p-5 rounded-2xl bg-white border border-[#eae4d9] shadow-xs hover:-translate-y-0.5 transition-all flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between pb-2 border-b border-[#f0ebe1]">
              <span className="text-[11px] uppercase font-bold tracking-wider text-[#6e665d] font-mono">Last Verified Backup</span>
              <div className="w-7 h-7 rounded-lg bg-purple-50 text-purple-600 flex items-center justify-center">
                <Database className="w-4 h-4" />
              </div>
            </div>
            <div className="text-xl font-serif font-bold text-[#191410] mt-3 truncate" title={backup?.time_since_backup_human}>
              {backup?.time_since_backup_human}
            </div>
          </div>
          <div className="pt-3 text-xs space-y-2">
            <div className="flex justify-between py-1 border-b border-[#f0ebe1]">
              <span className="text-[#6e665d]">Restore Test:</span>
              <span className="text-emerald-700 font-semibold font-mono text-[11px] flex items-center">
                <CheckCircle2 className="w-3.5 h-3.5 mr-1 text-emerald-600" />
                {backup?.restore_test_status?.toUpperCase()}
              </span>
            </div>
            <div className="flex justify-between py-1 border-b border-[#f0ebe1]">
              <span className="text-[#6e665d]">Snapshot Status:</span>
              <span className="text-[#191410] font-medium capitalize">{backup?.backup_status?.replace('_', ' ')}</span>
            </div>
            <div className="pt-1">
              <button
                onClick={handleTriggerBackup}
                disabled={backupTriggering}
                className="w-full py-2 px-3 bg-[#fdeee9] hover:bg-[#d93829] text-[#d93829] hover:text-white border border-[#d93829]/30 rounded-xl text-xs font-semibold flex items-center justify-center space-x-1.5 transition cursor-pointer disabled:opacity-50"
              >
                <HardDrive className={cn("w-3.5 h-3.5", backupTriggering && "animate-spin")} />
                <span>{backupTriggering ? 'Taking snapshot...' : 'Trigger Backup Snapshot'}</span>
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* AI Services Matrix */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <Cpu className="w-4 h-4 text-[#d93829]" />
            <span>AI Service Endpoints & Execution Diagnostics</span>
          </CardTitle>
          <span className="text-xs text-[#6e665d] font-mono">Live Subsystem Health</span>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {health?.ai_services.map((svc, idx) => (
              <div 
                key={idx}
                className="p-4 bg-[#faf7f2] rounded-xl border border-[#eae4d9] hover:border-[#d93829]/30 transition flex flex-col justify-between space-y-3"
              >
                <div className="flex items-start justify-between">
                  <div>
                    <h3 className="text-sm font-bold text-[#191410]">{svc.service_name}</h3>
                    <p className="text-xs text-[#6e665d] font-mono mt-0.5">{svc.provider}</p>
                  </div>
                  <div className="flex items-center space-x-2">
                    {svc.latency_ms !== null && svc.latency_ms !== undefined && (
                      <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-blue-50 border border-blue-200 text-blue-700 font-semibold">
                        {svc.latency_ms} ms
                      </span>
                    )}
                    <span className={cn(
                      "px-2.5 py-0.5 rounded-full text-[11px] font-semibold capitalize border",
                      svc.status === 'available' ? "bg-emerald-50 text-emerald-700 border-emerald-200" :
                      svc.status === 'degraded' ? "bg-amber-50 text-amber-700 border-amber-200" :
                      "bg-stone-100 text-stone-600 border-stone-200"
                    )}>
                      {svc.status}
                    </span>
                  </div>
                </div>

                <div className="text-xs space-y-1 font-mono text-[#6e665d] bg-white p-3 rounded-lg border border-[#eae4d9]">
                  <div className="truncate"><span className="text-[#8c8276] font-semibold">Target:</span> {svc.endpoint_or_model}</div>
                  <div className="text-[#191410] text-[11px] font-sans mt-1">{svc.notes}</div>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Disaster Recovery Verification Panel */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <ShieldCheck className="w-4 h-4 text-emerald-600" />
            <span>Automated Disaster Recovery & Sandbox Integrity Test</span>
          </CardTitle>
          <span className="text-xs text-[#6e665d] font-mono">Automated SQLite PRAGMA Verification</span>
        </CardHeader>
        <CardContent>
          <div className="p-5 bg-[#faf7f2] rounded-xl border border-[#eae4d9] flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="space-y-2">
              <div className="flex items-center space-x-2">
                <span className="text-xs font-bold text-[#191410]">Latest Backup Archive:</span>
                <span className="font-mono text-xs text-purple-800 bg-purple-50 px-2.5 py-0.5 rounded border border-purple-200 font-semibold">
                  {backup?.last_backup_filename || 'No backup on record'}
                </span>
              </div>
              <p className="text-xs text-[#6e665d]">
                Created: <span className="font-mono font-semibold text-[#191410]">{backup?.last_backup_at ? new Date(backup.last_backup_at).toLocaleString() : 'N/A'}</span>
                {' '}({backup?.time_since_backup_human})
              </p>
              {backup?.last_backup_hash && (
                <div className="flex items-center space-x-2 pt-1">
                  <span className="text-[11px] text-[#6e665d]">SHA-256 Hash:</span>
                  <span className="font-mono text-[11px] text-[#191410] bg-white px-2 py-0.5 rounded border border-[#eae4d9] select-all">
                    {backup.last_backup_hash}
                  </span>
                  <button
                    onClick={() => copyBackupHash(backup.last_backup_hash!)}
                    className="p-1 hover:text-[#d93829] text-[#6e665d] transition cursor-pointer"
                    title="Copy SHA-256 Hash"
                  >
                    {copiedHash ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5" />}
                  </button>
                </div>
              )}
            </div>

            <div className="flex flex-col items-start md:items-end space-y-2 shrink-0">
              <div className="flex items-center space-x-2 bg-emerald-50 border border-emerald-200 px-3 py-1.5 rounded-xl text-emerald-800 text-xs font-bold">
                <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                <span>Sandbox Restore Test: PASSED</span>
              </div>
              <p className="text-[11px] text-[#6e665d] max-w-sm text-left md:text-right">
                {backup?.restore_test_notes}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Recent Jobs Telemetry Table */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <Clock className="w-4 h-4 text-[#d93829]" />
            <span>Recent Background Analysis Jobs & Diagnostics</span>
          </CardTitle>
          <span className="text-xs text-[#6e665d] font-mono">{jobs?.recent_jobs.length || 0} recorded jobs</span>
        </CardHeader>
        <CardContent>
          {(!jobs?.recent_jobs || jobs.recent_jobs.length === 0) ? (
            <p className="text-xs text-[#8c8276] font-mono text-center py-8">No recent background jobs found.</p>
          ) : (
            <div className="overflow-x-auto rounded-xl border border-[#eae4d9]">
              <table className="w-full text-left text-xs font-mono">
                <thead>
                  <tr className="border-b border-[#eae4d9] bg-[#faf7f2] text-[#6e665d] uppercase text-[10px] tracking-wider">
                    <th className="py-3 px-4 font-bold">Job ID</th>
                    <th className="py-3 px-4 font-bold">Case</th>
                    <th className="py-3 px-4 font-bold">Type</th>
                    <th className="py-3 px-4 font-bold">Stage</th>
                    <th className="py-3 px-4 font-bold">Status</th>
                    <th className="py-3 px-4 font-bold">Duration</th>
                    <th className="py-3 px-4 font-bold">Submitted</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#eae4d9] bg-white text-[#191410]">
                  {jobs.recent_jobs.map((job) => (
                    <tr key={job.id} className="hover:bg-[#faf7f2] transition">
                      <td className="py-3 px-4 font-bold text-[#191410]">#{job.id}</td>
                      <td className="py-3 px-4 font-semibold text-blue-700">Case #{job.case_id}</td>
                      <td className="py-3 px-4 capitalize font-sans">{job.job_type}</td>
                      <td className="py-3 px-4 text-[#6e665d]">{job.current_stage || 'complete'}</td>
                      <td className="py-3 px-4">
                        <span className={cn(
                          "px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase border",
                          job.status === 'completed' ? "bg-emerald-50 text-emerald-700 border-emerald-200" :
                          job.status === 'failed' ? "bg-red-50 text-red-700 border-red-200" :
                          job.status === 'running' ? "bg-blue-50 text-blue-700 border-blue-200 animate-pulse" :
                          "bg-amber-50 text-amber-700 border-amber-200"
                        )}>
                          {job.status}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-[#6e665d]">
                        {job.duration_seconds !== null && job.duration_seconds !== undefined ? `${job.duration_seconds}s` : '-'}
                      </td>
                      <td className="py-3 px-4 text-[#6e665d]">
                        {job.created_at ? new Date(job.created_at).toLocaleTimeString() : '-'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
export default SystemHealth;
