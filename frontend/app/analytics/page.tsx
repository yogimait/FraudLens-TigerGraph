"use client";

import { useState, useEffect } from 'react';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar } from 'recharts';
import { Target, TrendingUp, ShieldCheck, AlertOctagon } from 'lucide-react';

export default function AnalyticsPage() {
  const [stats, setStats] = useState<any>({});
  const [patternData, setPatternData] = useState<any[]>([]);
  const [trendData, setTrendData] = useState<any[]>([]);
  
  useEffect(() => {
    fetchStats();
  }, []);

  const fetchStats = async () => {
    try {
      const [statsRes, casesRes] = await Promise.all([
        axios.get(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:3001'}/cases/stats`),
        axios.get(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:3001'}/cases`)
      ]);
      
      setStats(statsRes.data);

      const cases = casesRes.data;
      const patterns: Record<string, number> = {};
      cases.forEach((c: any) => {
        const pat = c.pattern || 'Unknown';
        patterns[pat] = (patterns[pat] || 0) + 1;
      });

      const patternArray = Object.entries(patterns)
        .map(([name, count]) => ({ name, count }))
        .sort((a, b) => b.count - a.count)
        .slice(0, 5); // top 5

      setPatternData(patternArray);

      // Real trend data calculation
      const dayCounts = [0, 0, 0, 0, 0, 0, 0]; // Sun-Sat
      cases.forEach((c: any) => {
        if (c.updatedAt) {
          const date = new Date(c.updatedAt);
          const day = date.getDay();
          // Shift so Monday is 0
          const shiftedDay = day === 0 ? 6 : day - 1;
          dayCounts[shiftedDay]++;
        }
      });
      
      setTrendData([
        { name: 'Mon', cases: dayCounts[0] },
        { name: 'Tue', cases: dayCounts[1] },
        { name: 'Wed', cases: dayCounts[2] },
        { name: 'Thu', cases: dayCounts[3] },
        { name: 'Fri', cases: dayCounts[4] },
        { name: 'Sat', cases: dayCounts[5] },
        { name: 'Sun', cases: dayCounts[6] },
      ]);
    } catch (e) {
      console.error(e);
    }
  };

  const totalClosed = (stats.closed_fraud || 0) + (stats.closed_legitimate || 0);
  const accuracy = totalClosed > 0 ? ((stats.closed_fraud || 0) / totalClosed * 100).toFixed(1) : "0.0";
  const autoRes = stats.total > 0 ? (((stats.closed_legitimate || 0) + (stats.closed_fraud || 0)) / stats.total * 100).toFixed(1) : "0.0";

  // We now use trendData from state, populated by actual MongoDB records.

  return (
    <div className="flex-1 p-8 space-y-8 bg-background relative min-h-screen">
      <div className="absolute inset-0 bg-[linear-gradient(to_right,#1E2433_1px,transparent_1px),linear-gradient(to_bottom,#1E2433_1px,transparent_1px)] bg-[size:24px_24px] opacity-20 pointer-events-none"></div>

      <div className="relative z-10">
        <h1 className="text-3xl font-serif font-extrabold tracking-tight text-foreground">Analytics & Performance</h1>
        <p className="text-sm text-muted-foreground mt-1">Review system detection accuracy and operational metrics.</p>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 relative z-10">
        <Card className="border-border bg-card shadow-none">
          <CardContent className="p-6">
            <div className="flex items-center space-x-3 mb-2 text-muted-foreground">
              <Target className="w-5 h-5 text-primary" />
              <span className="font-medium text-xs uppercase tracking-wider">Detection Accuracy</span>
            </div>
            <div className="text-3xl font-bold text-foreground">{accuracy}%</div>
            <p className="text-xs text-emerald-500 mt-1 flex items-center"><TrendingUp className="w-3 h-3 mr-1" /> Based on closed cases</p>
          </CardContent>
        </Card>
        <Card className="border-border bg-card shadow-none">
          <CardContent className="p-6">
            <div className="flex items-center space-x-3 mb-2 text-muted-foreground">
              <ShieldCheck className="w-5 h-5 text-emerald-500" />
              <span className="font-medium text-xs uppercase tracking-wider">Confirmed Fraud</span>
            </div>
            <div className="text-3xl font-bold text-foreground">{stats.closed_fraud || 0}</div>
            <p className="text-xs text-emerald-500 mt-1 flex items-center"><TrendingUp className="w-3 h-3 mr-1" /> Cases identified</p>
          </CardContent>
        </Card>
        <Card className="border-border bg-card shadow-none">
          <CardContent className="p-6">
            <div className="flex items-center space-x-3 mb-2 text-muted-foreground">
              <AlertOctagon className="w-5 h-5 text-destructive" />
              <span className="font-medium text-xs uppercase tracking-wider">Pending Interventions</span>
            </div>
            <div className="text-3xl font-bold text-foreground">{stats.awaiting_approval || 0}</div>
            <p className="text-xs text-muted-foreground mt-1 flex items-center">Cases requiring analyst review</p>
          </CardContent>
        </Card>
        <Card className="border-border bg-card shadow-none">
          <CardContent className="p-6">
            <div className="flex items-center space-x-3 mb-2 text-muted-foreground">
              <TrendingUp className="w-5 h-5 text-primary" />
              <span className="font-medium text-xs uppercase tracking-wider">Resolution Rate</span>
            </div>
            <div className="text-3xl font-bold text-foreground">{autoRes}%</div>
            <p className="text-xs text-muted-foreground mt-1">Total cases processed to closure</p>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 relative z-10">
        <Card className="border-border bg-card shadow-none">
          <CardHeader>
            <CardTitle className="text-lg font-serif text-foreground">Volume Trends (7 Days)</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-[300px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={trendData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                  <XAxis dataKey="name" stroke="var(--muted-foreground)" fontSize={12} tickLine={false} axisLine={false} />
                  <YAxis stroke="var(--muted-foreground)" fontSize={12} tickLine={false} axisLine={false} />
                  <Tooltip contentStyle={{ backgroundColor: 'var(--card)', border: '1px solid var(--border)', borderRadius: '8px', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }} itemStyle={{ color: 'var(--foreground)' }} />
                  <Line type="monotone" dataKey="cases" stroke="var(--primary)" strokeWidth={2} dot={{ r: 4, fill: 'var(--primary)', strokeWidth: 2, stroke: 'var(--card)' }} activeDot={{ r: 6 }} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        <Card className="border-border bg-card shadow-none">
          <CardHeader>
            <CardTitle className="text-lg font-serif text-foreground">Top Fraud Patterns Identified</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-[300px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={patternData} layout="vertical" margin={{ top: 0, right: 0, left: 20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="var(--border)" />
                  <XAxis type="number" stroke="var(--muted-foreground)" fontSize={12} tickLine={false} axisLine={false} />
                  <YAxis type="category" dataKey="name" stroke="var(--muted-foreground)" fontSize={12} tickLine={false} axisLine={false} width={100} />
                  <Tooltip cursor={{ fill: 'var(--secondary)' }} contentStyle={{ backgroundColor: 'var(--card)', border: '1px solid var(--border)', borderRadius: '8px' }} itemStyle={{ color: 'var(--foreground)' }} />
                  <Bar dataKey="count" fill="var(--primary)" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
