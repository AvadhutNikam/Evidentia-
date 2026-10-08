import { useEffect, useState } from 'react';
import { caseService } from '../../services';
import type { Case } from '../../types';
import { Card, CardContent } from '../../components/ui/Card';
import { BarChart2, Briefcase, Download, Calendar, FileText } from 'lucide-react';
import { cn } from '../../utils';

export function Reports() {
  const [cases, setCases] = useState<Case[]>([]);

  useEffect(() => {
    caseService.getCases().then(setCases);
  }, []);

  const statusCounts = {
    active: cases.filter(c => c.status === 'Active' || c.status === 'Under Investigation').length,
    closed: cases.filter(c => c.status === 'Closed' || c.status === 'Archived').length,
    total: cases.length,
  };

  const totalEvidence = cases.reduce((s, c) => s + c.evidenceCount, 0);

  return (
    <div className="space-y-6 pb-20">
      <div>
        <h1 className="text-3xl font-bold text-white mb-1">Reports</h1>
        <p className="text-sm text-text-muted">Generate cross-case intelligence reports and summaries.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {[
          { label: 'Total Cases', value: statusCounts.total, icon: Briefcase, color: 'text-primary', bg: 'bg-primary/10 border-primary/20' },
          { label: 'Active Investigations', value: statusCounts.active, icon: BarChart2, color: 'text-blue-400', bg: 'bg-blue-500/10 border-blue-500/20' },
          { label: 'Total Evidence Items', value: totalEvidence, icon: FileText, color: 'text-green-400', bg: 'bg-green-500/10 border-green-500/20' },
        ].map(s => (
          <Card key={s.label} className="p-5 flex items-center gap-4">
            <div className={cn('w-12 h-12 rounded-lg flex items-center justify-center border', s.bg)}>
              <s.icon className={cn('w-6 h-6', s.color)} />
            </div>
            <div>
              <div className="text-2xl font-bold text-white">{s.value}</div>
              <div className="text-xs text-text-muted uppercase tracking-wider font-semibold">{s.label}</div>
            </div>
          </Card>
        ))}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {[
          { title: 'Global Intelligence Summary', description: 'Aggregated overview of all active investigations, key statistics, and system-wide analysis trends.', icon: BarChart2, color: 'text-primary', bg: 'bg-primary/10 border-primary/20', date: 'Generated on demand' },
          { title: 'Case Comparison Matrix', description: 'Side-by-side comparison of evidence counts, entity distributions, and status across all cases.', icon: Briefcase, color: 'text-blue-400', bg: 'bg-blue-500/10 border-blue-500/20', date: 'Generated on demand' },
          { title: 'Evidence Processing Report', description: 'Pipeline status across all cases showing processing completion rates and failures.', icon: FileText, color: 'text-green-400', bg: 'bg-green-500/10 border-green-500/20', date: 'Generated on demand' },
          { title: 'Monthly Investigation Digest', description: 'Periodic summary of new cases, resolved cases, and key findings across the organization.', icon: Calendar, color: 'text-yellow-400', bg: 'bg-yellow-500/10 border-yellow-500/20', date: 'First of each month' },
        ].map(report => {
          const Icon = report.icon;
          return (
            <Card key={report.title} className="group hover:border-primary/50 transition-colors">
              <CardContent className="p-6">
                <div className={cn('w-11 h-11 rounded-lg flex items-center justify-center border mb-4', report.bg)}>
                  <Icon className={cn('w-5 h-5', report.color)} />
                </div>
                <h3 className="text-base font-bold text-white mb-2 group-hover:text-primary transition-colors">{report.title}</h3>
                <p className="text-sm text-text-muted mb-4 leading-relaxed">{report.description}</p>
                <div className="flex justify-between items-center pt-3 border-t border-border/50">
                  <span className="text-[10px] text-text-muted uppercase tracking-wider font-semibold">{report.date}</span>
                  <button className="flex items-center gap-1.5 px-3 py-1.5 bg-surface hover:bg-surface-hover border border-border text-text hover:text-white rounded-lg text-xs font-semibold transition-colors">
                    <Download className="w-3.5 h-3.5" /> Generate
                  </button>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
