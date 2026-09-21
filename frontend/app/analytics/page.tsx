"use client";

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar } from 'recharts';
import { Target, TrendingUp, ShieldCheck, AlertOctagon } from 'lucide-react';

const trendData = [
  { name: 'Mon', fraud: 4000, legitimate: 2400 },
  { name: 'Tue', fraud: 3000, legitimate: 1398 },
  { name: 'Wed', fraud: 2000, legitimate: 9800 },
  { name: 'Thu', fraud: 2780, legitimate: 3908 },
  { name: 'Fri', fraud: 1890, legitimate: 4800 },
  { name: 'Sat', fraud: 2390, legitimate: 3800 },
  { name: 'Sun', fraud: 3490, legitimate: 4300 },
];

const patternData = [
  { name: 'Card Testing', count: 1240 },
  { name: 'Account Takeover', count: 850 },
  { name: 'Device Spoofing', count: 620 },
  { name: 'Synthetic ID', count: 430 },
];

export default function AnalyticsPage() {
  return (
    <div className="flex-1 p-8 space-y-8 bg-[#F8FAFC]">
      <div>
        <h1 className="text-3xl font-extrabold tracking-tight text-slate-900">Analytics & Performance</h1>
        <p className="text-sm text-slate-500 mt-1">Review system detection accuracy and operational metrics.</p>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card className="border-slate-200 shadow-sm">
          <CardContent className="p-6">
            <div className="flex items-center space-x-3 mb-2 text-slate-500">
              <Target className="w-5 h-5 text-blue-600" />
              <span className="font-medium">Detection Accuracy</span>
            </div>
            <div className="text-3xl font-bold text-slate-900">94.2%</div>
            <p className="text-xs text-green-600 mt-1 flex items-center"><TrendingUp className="w-3 h-3 mr-1" /> +1.2% this week</p>
          </CardContent>
        </Card>
        <Card className="border-slate-200 shadow-sm">
          <CardContent className="p-6">
            <div className="flex items-center space-x-3 mb-2 text-slate-500">
              <ShieldCheck className="w-5 h-5 text-emerald-600" />
              <span className="font-medium">Loss Prevented</span>
            </div>
            <div className="text-3xl font-bold text-slate-900">$2.4M</div>
            <p className="text-xs text-green-600 mt-1 flex items-center"><TrendingUp className="w-3 h-3 mr-1" /> +$400k this week</p>
          </CardContent>
        </Card>
        <Card className="border-slate-200 shadow-sm">
          <CardContent className="p-6">
            <div className="flex items-center space-x-3 mb-2 text-slate-500">
              <AlertOctagon className="w-5 h-5 text-red-600" />
              <span className="font-medium">False Positives</span>
            </div>
            <div className="text-3xl font-bold text-slate-900">2.1%</div>
            <p className="text-xs text-green-600 mt-1 flex items-center"><TrendingUp className="w-3 h-3 mr-1" /> -0.5% this week</p>
          </CardContent>
        </Card>
        <Card className="border-slate-200 shadow-sm">
          <CardContent className="p-6">
            <div className="flex items-center space-x-3 mb-2 text-slate-500">
              <TrendingUp className="w-5 h-5 text-indigo-600" />
              <span className="font-medium">Auto-Resolution</span>
            </div>
            <div className="text-3xl font-bold text-slate-900">78%</div>
            <p className="text-xs text-slate-500 mt-1">Cases handled without manual review</p>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card className="border-slate-200 shadow-sm">
          <CardHeader>
            <CardTitle className="text-lg">Volume Trends (7 Days)</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-[300px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={trendData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                  <XAxis dataKey="name" stroke="#94a3b8" fontSize={12} />
                  <YAxis stroke="#94a3b8" fontSize={12} />
                  <Tooltip contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }} />
                  <Line type="monotone" dataKey="fraud" stroke="#ef4444" strokeWidth={2} dot={false} />
                  <Line type="monotone" dataKey="legitimate" stroke="#22c55e" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        <Card className="border-slate-200 shadow-sm">
          <CardHeader>
            <CardTitle className="text-lg">Top Fraud Patterns</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-[300px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={patternData} layout="vertical" margin={{ top: 0, right: 0, left: 40, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" horizontal={true} vertical={false} stroke="#f1f5f9" />
                  <XAxis type="number" stroke="#94a3b8" fontSize={12} />
                  <YAxis dataKey="name" type="category" stroke="#64748b" fontSize={12} width={100} />
                  <Tooltip cursor={{fill: '#f8fafc'}} contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }} />
                  <Bar dataKey="count" fill="#4f46e5" radius={[0, 4, 4, 0]} barSize={20} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
