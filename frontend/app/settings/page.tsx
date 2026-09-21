"use client";

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Save, Server, Shield, Bell } from 'lucide-react';

export default function SettingsPage() {
  return (
    <div className="flex-1 p-8 space-y-8 bg-[#F8FAFC]">
      <div className="flex justify-between items-end">
        <div>
          <h1 className="text-3xl font-extrabold tracking-tight text-slate-900">System Settings</h1>
          <p className="text-sm text-slate-500 mt-1">Configure TigerGraph connections, LLM parameters, and Policy limits.</p>
        </div>
        <Button className="bg-blue-600 hover:bg-blue-700 text-white shadow-sm"><Save className="w-4 h-4 mr-2" /> Save Changes</Button>
      </div>
      
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <Card className="border-slate-200 shadow-sm">
          <CardHeader className="pb-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-blue-50 rounded-lg text-blue-600"><Server className="w-5 h-5" /></div>
              <div>
                <CardTitle className="text-lg">Database Connections</CardTitle>
                <CardDescription>TigerGraph Savanna endpoints and secrets</CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Host URL</label>
              <input type="text" defaultValue="https://goa-hackathon.i.tgcloud.io" className="w-full bg-slate-50 border border-slate-200 rounded-md px-3 py-2 text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500" />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Graph Name</label>
              <input type="text" defaultValue="AntiFraud" className="w-full bg-slate-50 border border-slate-200 rounded-md px-3 py-2 text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500" />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Secret Key</label>
              <input type="password" defaultValue="************************" className="w-full bg-slate-50 border border-slate-200 rounded-md px-3 py-2 text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500" />
            </div>
          </CardContent>
        </Card>

        <Card className="border-slate-200 shadow-sm">
          <CardHeader className="pb-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-indigo-50 rounded-lg text-indigo-600"><Shield className="w-5 h-5" /></div>
              <div>
                <CardTitle className="text-lg">Policy Engine Constraints</CardTitle>
                <CardDescription>Adjust routing probabilities and thresholds</CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-6">
            <div>
              <div className="flex justify-between mb-1">
                <label className="text-sm font-medium text-slate-700">Auto-Reject Threshold (High Risk)</label>
                <span className="text-sm font-bold text-red-600">80%</span>
              </div>
              <input type="range" min="0" max="100" defaultValue="80" className="w-full accent-red-600" />
              <p className="text-xs text-slate-500 mt-1">Cases above this probability are auto-blocked without L1 review.</p>
            </div>
            <div>
              <div className="flex justify-between mb-1">
                <label className="text-sm font-medium text-slate-700">L1 Escaltion Threshold (Medium Risk)</label>
                <span className="text-sm font-bold text-amber-600">40%</span>
              </div>
              <input type="range" min="0" max="100" defaultValue="40" className="w-full accent-amber-500" />
              <p className="text-xs text-slate-500 mt-1">Cases above this probability are routed to the Approvals Center.</p>
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">SAR Filing Threshold</label>
              <div className="flex items-center gap-2">
                <span className="text-sm text-slate-500">$</span>
                <input type="number" defaultValue="1000" className="flex-1 bg-slate-50 border border-slate-200 rounded-md px-3 py-2 text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500" />
              </div>
              <p className="text-xs text-slate-500 mt-1">Minimum exposure required to automatically generate a SAR.</p>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
