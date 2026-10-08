import { useState } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '../../components/ui/Card';
import { Settings as SettingsIcon, User, Shield, Database, Palette, Bell, Key } from 'lucide-react';
import { cn } from '../../utils';

const sections = [
  { id: 'profile', label: 'Profile', icon: User },
  { id: 'security', label: 'Security & Access', icon: Shield },
  { id: 'notifications', label: 'Notifications', icon: Bell },
  { id: 'data', label: 'Data & Storage', icon: Database },
  { id: 'appearance', label: 'Appearance', icon: Palette },
  { id: 'api', label: 'API Keys', icon: Key },
];

export function Settings() {
  const [activeSection, setActiveSection] = useState('profile');

  return (
    <div className="space-y-6 pb-20">
      <div>
        <h1 className="text-3xl font-bold text-white mb-1">Settings</h1>
        <p className="text-sm text-text-muted">Manage your account, preferences, and system configuration.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Navigation */}
        <Card className="lg:col-span-1 h-fit">
          <CardContent className="p-2">
            <nav className="space-y-0.5">
              {sections.map(s => (
                <button
                  key={s.id}
                  onClick={() => setActiveSection(s.id)}
                  className={cn(
                    'w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors text-left',
                    activeSection === s.id
                      ? 'bg-primary/10 text-primary'
                      : 'text-text-muted hover:bg-surface-hover hover:text-white'
                  )}
                >
                  <s.icon className="w-4 h-4" />
                  {s.label}
                </button>
              ))}
            </nav>
          </CardContent>
        </Card>

        {/* Content */}
        <div className="lg:col-span-3 space-y-6">
          {activeSection === 'profile' && (
            <>
              <Card>
                <CardHeader><CardTitle>Profile Information</CardTitle></CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label className="text-xs text-text-muted uppercase font-bold mb-1.5 block">Full Name</label>
                      <input type="text" defaultValue="John Doe" className="w-full px-3 py-2.5 bg-surface border border-border rounded-lg text-sm text-white focus:outline-none focus:border-primary/50 transition-colors" />
                    </div>
                    <div>
                      <label className="text-xs text-text-muted uppercase font-bold mb-1.5 block">Email</label>
                      <input type="email" defaultValue="j.doe@evidentia.io" className="w-full px-3 py-2.5 bg-surface border border-border rounded-lg text-sm text-white focus:outline-none focus:border-primary/50 transition-colors" />
                    </div>
                    <div>
                      <label className="text-xs text-text-muted uppercase font-bold mb-1.5 block">Role</label>
                      <input type="text" defaultValue="Senior Investigator" className="w-full px-3 py-2.5 bg-surface border border-border rounded-lg text-sm text-white focus:outline-none focus:border-primary/50 transition-colors" />
                    </div>
                    <div>
                      <label className="text-xs text-text-muted uppercase font-bold mb-1.5 block">Badge ID</label>
                      <input type="text" defaultValue="INV-0427" className="w-full px-3 py-2.5 bg-surface border border-border rounded-lg text-sm text-white focus:outline-none focus:border-primary/50 transition-colors" readOnly />
                    </div>
                  </div>
                  <div className="pt-3">
                    <button className="px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary-hover transition-colors font-medium text-sm">Save Changes</button>
                  </div>
                </CardContent>
              </Card>
            </>
          )}

          {activeSection === 'security' && (
            <Card>
              <CardHeader><CardTitle>Security & Access</CardTitle></CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <label className="text-xs text-text-muted uppercase font-bold mb-1.5 block">Current Password</label>
                  <input type="password" placeholder="Enter current password" className="w-full px-3 py-2.5 bg-surface border border-border rounded-lg text-sm text-white focus:outline-none focus:border-primary/50 transition-colors" />
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="text-xs text-text-muted uppercase font-bold mb-1.5 block">New Password</label>
                    <input type="password" placeholder="Enter new password" className="w-full px-3 py-2.5 bg-surface border border-border rounded-lg text-sm text-white focus:outline-none focus:border-primary/50 transition-colors" />
                  </div>
                  <div>
                    <label className="text-xs text-text-muted uppercase font-bold mb-1.5 block">Confirm Password</label>
                    <input type="password" placeholder="Confirm new password" className="w-full px-3 py-2.5 bg-surface border border-border rounded-lg text-sm text-white focus:outline-none focus:border-primary/50 transition-colors" />
                  </div>
                </div>
                <div className="pt-3 flex gap-3">
                  <button className="px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary-hover transition-colors font-medium text-sm">Update Password</button>
                </div>
                <div className="pt-4 border-t border-border/50">
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="text-sm font-medium text-white">Two-Factor Authentication</div>
                      <div className="text-xs text-text-muted mt-0.5">Add an extra layer of security to your account.</div>
                    </div>
                    <button className="px-3 py-1.5 bg-surface border border-border rounded-lg text-xs font-medium text-text-muted hover:text-white transition-colors">Enable</button>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {activeSection === 'notifications' && (
            <Card>
              <CardHeader><CardTitle>Notification Preferences</CardTitle></CardHeader>
              <CardContent className="space-y-4">
                {[
                  { label: 'Evidence processing complete', desc: 'When an evidence item finishes analysis', defaultOn: true },
                  { label: 'New contradiction detected', desc: 'When AI identifies a logical conflict', defaultOn: true },
                  { label: 'Case assignment updates', desc: 'When you are assigned to or removed from a case', defaultOn: true },
                  { label: 'Investigation task reminders', desc: 'Pending tasks approaching deadline', defaultOn: false },
                  { label: 'System announcements', desc: 'Platform updates and maintenance notices', defaultOn: false },
                ].map(pref => (
                  <div key={pref.label} className="flex items-center justify-between p-3 rounded-lg bg-surface/50 border border-border/50">
                    <div>
                      <div className="text-sm font-medium text-white">{pref.label}</div>
                      <div className="text-xs text-text-muted mt-0.5">{pref.desc}</div>
                    </div>
                    <div className={cn(
                      'w-10 h-6 rounded-full relative cursor-pointer transition-colors',
                      pref.defaultOn ? 'bg-primary' : 'bg-surface-hover'
                    )}>
                      <div className={cn(
                        'absolute top-1 w-4 h-4 rounded-full bg-white shadow transition-all',
                        pref.defaultOn ? 'left-5' : 'left-1'
                      )} />
                    </div>
                  </div>
                ))}
              </CardContent>
            </Card>
          )}

          {(activeSection === 'data' || activeSection === 'appearance' || activeSection === 'api') && (
            <Card>
              <CardContent className="p-12 text-center">
                <SettingsIcon className="w-10 h-10 text-text-muted/30 mx-auto mb-3" />
                <h3 className="text-sm font-medium text-white mb-1">Configuration Coming Soon</h3>
                <p className="text-xs text-text-muted">This section will be available in a future update.</p>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
