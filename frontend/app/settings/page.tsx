"use client";

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Save, Server, Shield, Moon, Sun, CheckCircle2 } from 'lucide-react';

const STORAGE_KEY = 'fraudlens.settings';
const DEFAULTS = { tgHost: 'https://goa-hackathon.i.tgcloud.io', graphName: 'AntiFraud', autoReject: 80, l1Escalation: 40 };

export default function SettingsPage() {
  const [theme, setTheme] = useState('dark');
  const [settings, setSettings] = useState(DEFAULTS);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    // Check initial theme from html class
    if (document.documentElement.classList.contains('dark')) {
      setTheme('dark');
    } else {
      setTheme('light');
    }
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) setSettings({ ...DEFAULTS, ...JSON.parse(stored) });
    } catch {
      // corrupted storage falls back to defaults
    }
  }, []);

  const toggleTheme = () => {
    if (theme === 'dark') {
      document.documentElement.classList.remove('dark');
      setTheme('light');
    } else {
      document.documentElement.classList.add('dark');
      setTheme('dark');
    }
  };

  const handleSave = () => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  const update = (key: keyof typeof DEFAULTS, value: string | number) =>
    setSettings(s => ({ ...s, [key]: value }));

  return (
    <div className="flex-1 p-8 space-y-8 bg-background relative min-h-screen">
      <div className="absolute inset-0 bg-[linear-gradient(to_right,#1E2433_1px,transparent_1px),linear-gradient(to_bottom,#1E2433_1px,transparent_1px)] bg-[size:24px_24px] opacity-20 pointer-events-none"></div>

      <div className="flex justify-between items-end relative z-10">
        <div>
          <h1 className="text-3xl font-serif font-extrabold tracking-tight text-foreground">System Settings</h1>
          <p className="text-sm text-muted-foreground mt-1">Configure TigerGraph connections, LLM parameters, and UI preferences.</p>
        </div>
        <div className="flex items-center gap-3">
          {saved && (
            <span className="text-sm text-emerald-500 flex items-center"><CheckCircle2 className="w-4 h-4 mr-1" /> Saved locally</span>
          )}
          <Button className="bg-primary hover:bg-primary/90 text-primary-foreground shadow-none" onClick={handleSave}><Save className="w-4 h-4 mr-2" /> Save Changes</Button>
        </div>
      </div>
      
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 relative z-10">
        <Card className="border-border bg-card shadow-none">
          <CardHeader className="pb-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-primary/20 rounded-lg text-primary"><Sun className="w-5 h-5" /></div>
              <div>
                <CardTitle className="text-lg font-serif text-foreground">Appearance</CardTitle>
                <CardDescription className="text-muted-foreground">Customize the UI theme</CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <label className="block text-sm font-medium text-foreground">Dark / Light Mode</label>
                <p className="text-xs text-muted-foreground mt-1">Switch between dark and light themes.</p>
              </div>
              <Button 
                onClick={toggleTheme}
                variant="outline"
                className="bg-secondary text-foreground border-border hover:bg-secondary/80"
              >
                {theme === 'dark' ? <Sun className="w-4 h-4 mr-2" /> : <Moon className="w-4 h-4 mr-2" />}
                {theme === 'dark' ? 'Switch to Light' : 'Switch to Dark'}
              </Button>
            </div>
          </CardContent>
        </Card>

        <Card className="border-border bg-card shadow-none">
          <CardHeader className="pb-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-primary/20 rounded-lg text-primary"><Server className="w-5 h-5" /></div>
              <div>
                <CardTitle className="text-lg font-serif text-foreground">Database Connections</CardTitle>
                <CardDescription className="text-muted-foreground">TigerGraph Savanna endpoints</CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-foreground mb-1">Host URL</label>
              <input type="text" value={settings.tgHost} onChange={(e) => update('tgHost', e.target.value)} className="w-full bg-input border border-border rounded-md px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary" />
            </div>
            <div>
              <label className="block text-sm font-medium text-foreground mb-1">Graph Name</label>
              <input type="text" value={settings.graphName} onChange={(e) => update('graphName', e.target.value)} className="w-full bg-input border border-border rounded-md px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary" />
            </div>
          </CardContent>
        </Card>

        <Card className="border-border bg-card shadow-none lg:col-span-2">
          <CardHeader className="pb-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-purple-500/20 rounded-lg text-purple-400"><Shield className="w-5 h-5" /></div>
              <div>
                <CardTitle className="text-lg font-serif text-foreground">Policy Engine Constraints</CardTitle>
                <CardDescription className="text-muted-foreground">Adjust routing probabilities and thresholds</CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="grid grid-cols-2 gap-8">
              <div>
                <div className="flex justify-between mb-1">
                  <label className="text-sm font-medium text-foreground">Auto-Reject Threshold (High Risk)</label>
                  <span className="text-sm font-bold text-destructive">{settings.autoReject}%</span>
                </div>
                <input type="range" min="0" max="100" value={settings.autoReject} onChange={(e) => update('autoReject', Number(e.target.value))} className="w-full accent-destructive" />
                <p className="text-xs text-muted-foreground mt-1">Cases above this probability are auto-blocked without L1 review.</p>
              </div>
              <div>
                <div className="flex justify-between mb-1">
                  <label className="text-sm font-medium text-foreground">L1 Escalation Threshold (Medium Risk)</label>
                  <span className="text-sm font-bold text-amber-500">{settings.l1Escalation}%</span>
                </div>
                <input type="range" min="0" max="100" value={settings.l1Escalation} onChange={(e) => update('l1Escalation', Number(e.target.value))} className="w-full accent-amber-500" />
                <p className="text-xs text-muted-foreground mt-1">Cases above this probability are routed to the Approvals Center.</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
