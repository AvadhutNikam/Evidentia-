import React from 'react';
import { NavLink } from 'react-router-dom';
import { LayoutDashboard, Briefcase, FileText, Clock, Network, Globe, Mic, Map, Bot, BarChart2, Settings, User } from 'lucide-react';
import { cn } from '../../utils';

const navItems = [
  { name: 'Dashboard', path: '/dashboard', icon: LayoutDashboard },
  { name: 'Cases', path: '/cases', icon: Briefcase },
  { name: 'Evidence', path: '/evidence', icon: FileText },
  { name: 'Timeline', path: '/timeline', icon: Clock },
  { name: 'Knowledge Graph', path: '/knowledge-graph', icon: Network },
  { name: 'OSINT Intelligence', path: '/osint', icon: Globe },
  { name: 'Interviews', path: '/interviews', icon: Mic },
  { name: 'Case Map', path: '/case-map', icon: Map },
  { name: 'AI Assistant', path: '/assistant', icon: Bot },
  { name: 'Reports', path: '/reports', icon: BarChart2 },
];

export function Sidebar() {
  return (
    <div className="w-64 h-screen bg-surface border-r border-border flex flex-col fixed left-0 top-0">
      <div className="h-16 flex items-center px-6 border-b border-border">
        <div className="flex items-center gap-2 text-primary">
          <Network className="w-6 h-6" />
          <span className="text-xl font-bold tracking-wider text-text">EVIDENTIA</span>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto py-4">
        <nav className="space-y-1 px-3">
          {navItems.map((item) => (
            <NavLink
              key={item.name}
              to={item.path}
              className={({ isActive }) => cn(
                "flex items-center gap-3 px-3 py-2 rounded-lg transition-colors group",
                isActive 
                  ? "bg-primary/10 text-primary" 
                  : "text-textMuted hover:bg-surfaceHover hover:text-text"
              )}
            >
              <item.icon className="w-5 h-5" />
              <span className="font-medium">{item.name}</span>
            </NavLink>
          ))}
        </nav>
      </div>

      <div className="p-4 border-t border-border space-y-1">
        <NavLink to="/settings" className={({ isActive }) => cn("flex items-center gap-3 px-3 py-2 rounded-lg transition-colors", isActive ? "bg-primary/10 text-primary" : "text-textMuted hover:bg-surfaceHover hover:text-text")}>
          <Settings className="w-5 h-5" />
          <span className="font-medium">Settings</span>
        </NavLink>
        <button className="w-full flex items-center gap-3 px-3 py-2 rounded-lg transition-colors text-textMuted hover:bg-surfaceHover hover:text-text">
          <User className="w-5 h-5" />
          <span className="font-medium">Profile</span>
        </button>
      </div>
    </div>
  );
}
