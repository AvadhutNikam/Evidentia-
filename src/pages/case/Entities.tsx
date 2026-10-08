import { useParams } from 'react-router-dom';
import { useEffect, useState } from 'react';
import { entityService } from '../../services';
import { Entity } from '../../types';
import { Card } from '../../components/ui/Card';
import { Users, Building, MapPin, Car, Calendar, Search } from 'lucide-react';
import { cn } from '../../utils';

export function Entities() {
  const { caseId } = useParams();
  const [entities, setEntities] = useState<Entity[]>([]);

  useEffect(() => {
    if (caseId) {
      entityService.getEntitiesForCase(caseId).then(setEntities);
    }
  }, [caseId]);

  const getIcon = (type: string) => {
    switch (type) {
      case 'Person': return <Users className="w-5 h-5 text-blue-400" />;
      case 'Organization': return <Building className="w-5 h-5 text-purple-400" />;
      case 'Location': return <MapPin className="w-5 h-5 text-green-400" />;
      case 'Vehicle': return <Car className="w-5 h-5 text-yellow-400" />;
      case 'Event': return <Calendar className="w-5 h-5 text-red-400" />;
      default: return <Users className="w-5 h-5 text-text-muted" />;
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-serif font-bold text-[#191410] mb-1">Extracted Entities</h1>
        <p className="text-sm text-text-muted">People, organizations, and objects discovered across all evidence.</p>
      </div>

      <Card className="p-4 relative">
        <Search className="w-4 h-4 absolute left-7 top-1/2 -translate-y-1/2 text-text-muted" />
        <input 
          type="text" 
          placeholder="Search entities..." 
          className="w-full pl-10 pr-4 py-2 bg-background border border-border rounded-lg text-sm focus:outline-none focus:border-primary/50 text-white"
        />
      </Card>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {entities.map(entity => (
          <Card key={entity.id} className="p-5 hover:border-primary/50 transition-colors cursor-pointer group">
            <div className="flex justify-between items-start mb-4">
              <div className="w-10 h-10 rounded-lg bg-surface flex items-center justify-center border border-border">
                {getIcon(entity.type)}
              </div>
              <span className={cn(
                "px-2 py-1 rounded text-[10px] font-bold uppercase tracking-wider border",
                entity.confidence >= 95 ? "bg-green-500/10 text-green-400 border-green-500/20" : "bg-blue-500/10 text-blue-400 border-blue-500/20"
              )}>
                {entity.confidence}% Conf
              </span>
            </div>
            <h3 className="text-lg font-serif font-semibold text-[#191410] mb-1 group-hover:text-primary transition-colors">{entity.name}</h3>
            <p className="text-xs text-text-muted mb-4">{entity.type}</p>
            
            {entity.aliases.length > 0 && (
              <div className="mb-4">
                <div className="text-[10px] uppercase font-bold text-text-muted mb-1">Aliases</div>
                <div className="flex gap-1 flex-wrap">
                  {entity.aliases.map(a => (
                    <span key={a} className="px-2 py-0.5 bg-surface-hover rounded text-[10px] text-text border border-border">
                      {a}
                    </span>
                  ))}
                </div>
              </div>
            )}

            <div className="pt-3 border-t border-border/50 text-xs text-text-muted flex justify-between">
              <span>{entity.sourceEvidenceIds.length} Evidence Sources</span>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}