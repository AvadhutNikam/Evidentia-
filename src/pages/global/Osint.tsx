import { Card, CardHeader, CardTitle, CardContent } from '../../components/ui/Card';
import { Globe, Search, Download, User, Mail, Database, Server, ChevronDown } from 'lucide-react';
import { useState } from 'react';
import { cn } from '../../utils';

export function Osint() {
  const [activeTab, setActiveTab] = useState('person');

  const tools = [
    { id: 'person', label: 'Person Search', icon: User },
    { id: 'email', label: 'Email/Username', icon: Mail },
    { id: 'domain', label: 'Domain/IP', icon: Server },
    { id: 'breach', label: 'Breach Data', icon: Database },
  ];

  return (
    <div className="space-y-6 max-w-5xl mx-auto pb-20">
      <div>
        <h1 className="text-3xl font-bold text-white mb-1">OSINT Intelligence Workspace</h1>
        <p className="text-sm text-text-muted">Query public records, breach databases, and external intelligence sources.</p>
      </div>

      <Card className="overflow-hidden">
        <div className="flex border-b border-border/50 bg-surface-hover/50 overflow-x-auto">
          {tools.map(t => (
            <button 
              key={t.id}
              onClick={() => setActiveTab(t.id)}
              className={cn(
                "px-6 py-4 flex items-center gap-2 text-sm font-medium transition-colors border-b-2 whitespace-nowrap",
                activeTab === t.id 
                  ? "border-primary text-primary bg-primary/5" 
                  : "border-transparent text-text-muted hover:text-white hover:bg-surface-hover"
              )}
            >
              <t.icon className="w-4 h-4" />
              {t.label}
            </button>
          ))}
        </div>
        
        <CardContent className="p-8">
          <div className="max-w-2xl mx-auto">
            <h3 className="text-lg font-semibold text-white mb-4 text-center">
              Execute {tools.find(t => t.id === activeTab)?.label} Query
            </h3>
            
            <div className="flex gap-2">
              <div className="relative flex-1">
                <Search className="w-5 h-5 absolute left-4 top-1/2 -translate-y-1/2 text-text-muted" />
                <input 
                  type="text" 
                  placeholder={
                    activeTab === 'person' ? "Enter full name (e.g. John Doe)" :
                    activeTab === 'email' ? "Enter email or username" :
                    activeTab === 'domain' ? "Enter domain or IP address" :
                    "Enter identifier to check breaches"
                  }
                  className="w-full pl-12 pr-4 py-3 bg-background border border-border rounded-xl focus:outline-none focus:border-primary/50 text-white transition-colors"
                />
              </div>
              <button className="px-6 py-3 bg-primary text-white rounded-xl hover:bg-primary-hover transition-colors font-medium shadow-lg shadow-primary/20 flex items-center gap-2">
                <Search className="w-4 h-4" /> Search
              </button>
            </div>
            
            <p className="text-center text-xs text-text-muted mt-4">
              All queries are executed through secure proxies and logged for audit purposes.
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Mock Search Results */}
      <div className="mt-8 space-y-4">
        <div className="flex justify-between items-end mb-4">
          <h3 className="text-lg font-bold text-white">Recent Intelligence Findings</h3>
          <button className="text-sm font-medium text-primary hover:text-primary-hover flex items-center gap-1">
            View History <ChevronDown className="w-4 h-4" />
          </button>
        </div>

        <Card className="hover:border-primary/50 transition-colors">
          <CardContent className="p-5 flex flex-col md:flex-row gap-6 items-start md:items-center">
            <div className="w-12 h-12 rounded-lg bg-purple-500/10 flex items-center justify-center border border-purple-500/20 text-purple-400 shrink-0">
              <Globe className="w-6 h-6" />
            </div>
            <div className="flex-1">
              <div className="flex justify-between items-start mb-1">
                <h4 className="font-bold text-white text-lg">Offshore Company Registry Match</h4>
                <span className="text-xs font-semibold px-2 py-1 bg-surface border border-border rounded text-text-muted">
                  2 hours ago
                </span>
              </div>
              <p className="text-sm text-text-muted mb-3">
                Found "Nexus Global Holdings" in the Panama Papers database, linked to shell corporations in the Cayman Islands.
              </p>
              <div className="flex gap-2">
                <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase border bg-surface text-text-muted">
                  Source: ICIJ Database
                </span>
                <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase border bg-green-500/10 text-green-400 border-green-500/20">
                  Reliability: High
                </span>
              </div>
            </div>
            
            <div className="w-full md:w-auto flex flex-col gap-2 border-t md:border-t-0 md:border-l border-border/50 pt-4 md:pt-0 md:pl-6">
              <button className="w-full md:w-auto px-4 py-2 bg-primary/10 hover:bg-primary hover:text-white text-primary border border-primary/20 rounded-lg text-sm font-medium transition-all flex items-center justify-center gap-2">
                <Download className="w-4 h-4" /> Save to Case
              </button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}