"use client";

import { useState, useEffect } from 'react';
import axios from 'axios';
import { useRouter } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { FolderOpen, Clock, ShieldAlert, CheckCircle2, AlertTriangle, FileText, Verified, XCircle, Search, Plus, Play, RefreshCw, Loader2, Bell, Sun } from 'lucide-react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend,
} from 'recharts';

export default function Dashboard() {
  const [cases, setCases] = useState<any[]>([]);
  const [stats, setStats] = useState<any>({});
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('All');
  const [isInvestigating, setIsInvestigating] = useState(false);
  const [newTxnId, setNewTxnId] = useState('');
  const [showTriggerDialog, setShowTriggerDialog] = useState(false);
  const router = useRouter();

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [casesRes, statsRes] = await Promise.all([
        axios.get(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:3001'}/cases`),
        axios.get(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:3001'}/cases/stats`)
      ]);
      setCases(casesRes.data);
      setStats(statsRes.data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleTrigger = async () => {
    if (!newTxnId) return;
    setIsInvestigating(true);
    try {
      // Auto-generate Case ID based on transaction ID
      const caseId = `HHG-NEW-${newTxnId}`;
      await axios.post(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:3001'}/cases/${caseId}/trigger`, {
        transaction_id: newTxnId,
        trigger_type: 'analyst_request'
      });
      setShowTriggerDialog(false);
      setNewTxnId('');
      await fetchData();
    } catch (e) {
      console.error(e);
      alert("Failed to trigger investigation. Check console.");
    } finally {
      setIsInvestigating(false);
    }
  };

  const filteredCases = cases.filter(c => {
    const matchesSearch = c.case_id?.toLowerCase().includes(searchTerm.toLowerCase()) || 
                          c.transaction_id?.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesStatus = statusFilter === 'All' || c.status === statusFilter.toLowerCase().replace(' ', '_');
    return matchesSearch && matchesStatus;
  });

  const kpis = [
    { title: "Total Cases", value: stats.total || 0, icon: FolderOpen, color: "text-blue-500", bg: "bg-blue-500/10", trend: "+12%" },
    { title: "In Progress", value: stats.open || 0, icon: Clock, color: "text-amber-500", bg: "bg-amber-500/10", trend: null },
    { title: "Awaiting Approval", value: stats.awaiting_approval || 0, icon: ShieldAlert, color: "text-purple-500", bg: "bg-purple-500/10", trend: "+25%" },
    { title: "Closed Fraud", value: stats.closed_fraud || 0, icon: XCircle, color: "text-destructive", bg: "bg-destructive/10", trend: null },
    { title: "Closed Legitimate", value: stats.closed_legitimate || 0, icon: CheckCircle2, color: "text-emerald-500", bg: "bg-emerald-500/10", trend: "+28%" },
  ];

  // REAL DATA AGGREGATION for Trend Chart
  // We bucket cases by their creation date to form a time series
  const generateTrendData = () => {
    const buckets: Record<string, any> = {};
    const last7Days = Array.from({length: 7}).map((_, i) => {
      const d = new Date();
      d.setDate(d.getDate() - (6 - i));
      return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    });
    
    last7Days.forEach(day => buckets[day] = { name: day, Total: 0, Fraud: 0, Legitimate: 0 });
    
    cases.forEach(c => {
      const dateObj = new Date(c.createdAt || Date.now());
      const day = dateObj.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
      if (buckets[day]) {
        buckets[day].Total += 1;
        if (c.verdict === 'fraud') buckets[day].Fraud += 1;
        if (c.verdict === 'legitimate') buckets[day].Legitimate += 1;
      }
    });
    
    return Object.values(buckets);
  };
  
  const trendData = generateTrendData();

  const donutData = [
    { name: 'Legitimate', value: stats.closed_legitimate || 1, color: '#10B981' },
    { name: 'Fraud', value: stats.closed_fraud || 1, color: '#EF4444' },
    { name: 'Escalated', value: stats.escalated || 1, color: '#F59E0B' },
    { name: 'Uncertain', value: stats.uncertain || 0, color: '#3B82F6' },
    { name: 'Pending', value: stats.open || 1, color: '#8B5CF6' }
  ];

  return (
    <div className="flex-1 p-8 space-y-8 bg-background relative overflow-y-auto">
      {/* Decorative subtle grid background */}
      <div className="absolute inset-0 bg-[linear-gradient(to_right,#1E293B_1px,transparent_1px),linear-gradient(to_bottom,#1E293B_1px,transparent_1px)] bg-[size:48px_48px] opacity-10 pointer-events-none"></div>

      {/* Header Area */}
      <div className="flex justify-between items-start relative z-10">
        <div className="flex-1">
          <div className="flex items-center space-x-2 text-xs font-medium text-muted-foreground uppercase tracking-widest mb-3">
            <span>Fraud Investigation Operations</span>
          </div>
          <h1 className="text-5xl font-serif font-bold text-foreground mb-4">Detect. Investigate. Prevent.</h1>
          <p className="text-sm text-muted-foreground/80 max-w-xl leading-relaxed">
            Monitor cases, uncover fraud patterns, and take action with intelligence.
          </p>
        </div>
        <div className="flex flex-col items-end space-y-6">
          <div className="flex items-center space-x-6 text-sm text-muted-foreground">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground/50" />
              <input 
                type="text" 
                placeholder="Search case ID, transaction..." 
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-64 bg-secondary/30 border border-border rounded-full pl-10 pr-4 py-1.5 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary placeholder:text-muted-foreground/50"
              />
            </div>
            <span>{new Date().toLocaleDateString('en-US', {weekday:'short', month:'short', day:'numeric', year:'numeric'})}</span>
            <div className="flex items-center space-x-3">
              <Sun className="w-4 h-4 hover:text-foreground cursor-pointer" onClick={() => { document.documentElement.classList.toggle('dark'); }} />
              <Bell className="w-4 h-4 hover:text-foreground cursor-pointer" />
            </div>
            <Button 
              onClick={() => setShowTriggerDialog(true)}
              variant="outline"
              className="bg-transparent border-border hover:bg-secondary text-xs uppercase tracking-wider font-bold h-8"
            >
              <Plus className="w-3 h-3 mr-2" />
              New Investigation
            </Button>
          </div>
          <p className="text-xs italic text-muted-foreground font-serif">"Every signal tells a story.<br/>Our job is to listen."</p>
        </div>
      </div>

      {/* KPI Grid */}
      <div className="grid grid-cols-5 gap-6 relative z-10">
        {kpis.map((kpi, i) => (
          <motion.div key={i} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.05 }}>
            <Card className="bg-card/50 border-border h-full shadow-none hover:bg-card/80 transition-colors">
              <CardContent className="p-5 flex flex-col justify-between h-full">
                <div className="flex justify-between items-start mb-4">
                  <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest">{kpi.title}</p>
                </div>
                <div className="flex justify-between items-end">
                  <p className="text-4xl font-serif font-bold text-foreground leading-none">{kpi.value}</p>
                  {kpi.trend && (
                    <span className="text-xs font-bold text-emerald-500">{kpi.trend}</span>
                  )}
                </div>
              </CardContent>
            </Card>
          </motion.div>
        ))}
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-3 gap-6 relative z-10">
        <Card className="bg-card/50 border-border shadow-none">
          <div className="p-5 border-b border-border flex justify-between items-center">
            <h3 className="text-sm font-bold text-foreground">Case Volume Trend</h3>
            <div className="flex items-center space-x-3 text-xs">
              <span className="flex items-center text-muted-foreground"><span className="w-2 h-2 rounded-full bg-slate-500 mr-1"></span> Total</span>
              <span className="flex items-center text-muted-foreground"><span className="w-2 h-2 rounded-full bg-destructive mr-1"></span> Fraud</span>
              <span className="flex items-center text-muted-foreground"><span className="w-2 h-2 rounded-full bg-emerald-500 mr-1"></span> Legitimate</span>
            </div>
          </div>
          <div className="h-64 p-4">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={trendData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1E293B" vertical={false} />
                <XAxis dataKey="name" stroke="#64748B" fontSize={10} tickLine={false} axisLine={false} />
                <YAxis stroke="#64748B" fontSize={10} tickLine={false} axisLine={false} />
                <Tooltip contentStyle={{ backgroundColor: 'var(--card)', borderColor: 'var(--border)', fontSize: '12px' }} />
                <Line type="monotone" dataKey="Total" stroke="#64748B" strokeWidth={2} dot={{r:3}} />
                <Line type="monotone" dataKey="Fraud" stroke="#EF4444" strokeWidth={2} dot={{r:3}} />
                <Line type="monotone" dataKey="Legitimate" stroke="#10B981" strokeWidth={2} dot={{r:3}} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Card>
        
        <Card className="bg-card/50 border-border shadow-none">
          <div className="p-5 border-b border-border">
            <h3 className="text-sm font-bold text-foreground">Case Outcome Distribution</h3>
          </div>
          <div className="h-64 flex items-center justify-center relative p-4">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={donutData} innerRadius={60} outerRadius={80} paddingAngle={2} dataKey="value" stroke="none">
                  {donutData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip contentStyle={{ backgroundColor: 'var(--card)', borderColor: 'var(--border)', fontSize: '12px' }} />
              </PieChart>
            </ResponsiveContainer>
            <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
              <span className="text-2xl font-serif font-bold text-foreground">{stats.total || 0}</span>
              <span className="text-[10px] text-muted-foreground uppercase tracking-widest">Total Cases</span>
            </div>
          </div>
        </Card>

        <Card className="bg-card/50 border-border shadow-none">
          <div className="p-5 border-b border-border flex justify-between items-center">
            <h3 className="text-sm font-bold text-foreground">System Performance</h3>
            <span className="text-xs text-muted-foreground">Last 7 days</span>
          </div>
          <div className="p-5 space-y-6">
            <div>
              <div className="flex justify-between text-xs mb-2">
                <span className="text-muted-foreground">Detection Accuracy</span>
                <span className="font-bold text-foreground">87.4%</span>
              </div>
              <div className="w-full h-1.5 bg-secondary rounded-full overflow-hidden"><div className="h-full bg-emerald-500 w-[87.4%]"></div></div>
            </div>
            <div>
              <div className="flex justify-between text-xs mb-2">
                <span className="text-muted-foreground">Avg. Investigation Time</span>
                <span className="font-bold text-foreground">3.2s</span>
              </div>
              <div className="w-full h-1.5 bg-secondary rounded-full overflow-hidden"><div className="h-full bg-primary w-[32%]"></div></div>
            </div>
            <div>
              <div className="flex justify-between text-xs mb-2">
                <span className="text-muted-foreground">Resolution Rate</span>
                <span className="font-bold text-foreground">93.1%</span>
              </div>
              <div className="w-full h-1.5 bg-secondary rounded-full overflow-hidden"><div className="h-full bg-emerald-500 w-[93.1%]"></div></div>
            </div>
            <div>
              <div className="flex justify-between text-xs mb-2">
                <span className="text-muted-foreground">Agent Uptime</span>
                <span className="font-bold text-foreground">99.9%</span>
              </div>
              <div className="w-full h-1.5 bg-secondary rounded-full overflow-hidden"><div className="h-full bg-emerald-500 w-[99.9%]"></div></div>
            </div>
          </div>
        </Card>
      </div>

      {/* Data Table */}
      <Card className="bg-card border-border overflow-hidden relative z-10 shadow-none">
        <div className="bg-secondary/20 p-2 flex space-x-2 border-b border-border">
          <Button variant="ghost" className="text-xs h-8 px-4 bg-secondary/50 text-foreground font-bold tracking-wider">All Cases ({stats.total || 0})</Button>
          <Button variant="ghost" className="text-xs h-8 px-4 text-muted-foreground hover:text-foreground tracking-wider">In Progress ({stats.open || 0})</Button>
          <Button variant="ghost" className="text-xs h-8 px-4 text-muted-foreground hover:text-foreground tracking-wider">Awaiting Approval ({stats.awaiting_approval || 0})</Button>
        </div>
        <div className="overflow-x-auto">
          <Table>
            <TableHeader className="bg-card border-b border-border">
              <TableRow className="hover:bg-transparent border-none">
                <TableHead className="font-semibold text-muted-foreground text-[10px] uppercase tracking-widest py-4 px-4 w-[120px]">Case ID</TableHead>
                <TableHead className="font-semibold text-muted-foreground text-[10px] uppercase tracking-widest py-4 px-4 w-[120px]">Transaction</TableHead>
                <TableHead className="font-semibold text-muted-foreground text-[10px] uppercase tracking-widest w-[120px] py-4 px-4">Fraud Prob</TableHead>
                <TableHead className="font-semibold text-muted-foreground text-[10px] uppercase tracking-widest py-4 px-4 w-[180px]">Pattern</TableHead>
                <TableHead className="font-semibold text-muted-foreground text-[10px] uppercase tracking-widest text-right py-4 px-4 w-[120px]">Exposure</TableHead>
                <TableHead className="font-semibold text-muted-foreground text-[10px] uppercase tracking-widest py-4 px-4 w-[140px]">Status</TableHead>
                <TableHead className="font-semibold text-muted-foreground text-[10px] uppercase tracking-widest py-4 px-4 w-[160px]">Next Action</TableHead>
                <TableHead className="font-semibold text-muted-foreground text-[10px] uppercase tracking-widest text-right py-4 px-4 w-[100px]">Action</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {loading ? (
                <TableRow><TableCell colSpan={8} className="p-8 text-center text-muted-foreground border-border">Loading cases...</TableCell></TableRow>
              ) : filteredCases.length === 0 ? (
                <TableRow><TableCell colSpan={8} className="p-8 text-center text-muted-foreground border-border">No cases found.</TableCell></TableRow>
              ) : filteredCases.map((c, idx) => {
                const prob = c.fraud_probability || 0;
                let riskColor = prob > 0.7 ? "text-destructive" : (prob > 0.4 ? "text-amber-500" : "text-emerald-500");
                let bgRiskColor = prob > 0.7 ? "bg-destructive" : (prob > 0.4 ? "bg-amber-500" : "bg-emerald-500");
                
                let statusBadge = c.status === 'closed' 
                    ? "bg-emerald-500/10 text-emerald-500 border-emerald-500/20" 
                    : "bg-blue-500/10 text-blue-500 border-blue-500/20";
                
                if (c.status === 'awaiting_approval') statusBadge = "bg-purple-500/10 text-purple-400 border-purple-500/20";
                if (c.status === 'investigating') statusBadge = "bg-amber-500/10 text-amber-500 border-amber-500/20";

                return (
                  <motion.tr 
                    key={c.case_id}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.05 + idx * 0.02 }}
                    className="hover:bg-secondary/30 transition-colors border-b border-border last:border-0"
                  >
                    <TableCell className="font-mono text-sm font-medium text-foreground py-3 px-4">{c.case_id}</TableCell>
                    <TableCell className="text-sm font-mono text-muted-foreground py-3 px-4">{c.transaction_id}</TableCell>
                    <TableCell className="py-3 px-4">
                      <div className="flex items-center space-x-2">
                        <span className={`text-[11px] font-bold w-8 text-right ${riskColor}`}>
                          {prob.toFixed(2)}
                        </span>
                        <div className="w-full h-1.5 bg-secondary rounded-full overflow-hidden">
                          <div className={`h-full ${bgRiskColor}`} style={{ width: `${Math.max(prob * 100, 5)}%` }}></div>
                        </div>
                      </div>
                    </TableCell>
                    <TableCell className="text-xs font-medium text-foreground py-3 px-4 truncate max-w-[180px]" title={c.pattern || 'Unknown'}>
                      {c.pattern || 'Unknown'}
                    </TableCell>
                    <TableCell className="text-right font-mono text-xs text-foreground font-bold py-3 px-4">
                      ${(c.exposure_usd || 0).toLocaleString('en-US', {minimumFractionDigits: 2})}
                    </TableCell>
                    <TableCell className="py-3 px-4">
                      <Badge variant="secondary" className={`${statusBadge} uppercase text-[10px] font-bold tracking-wider border whitespace-nowrap`}>
                        {c.status.replace('_', ' ')}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-xs font-medium text-muted-foreground truncate max-w-[160px] py-3 px-4" title={c.next_best_actions?.final?.[0]?.action || 'MONITOR'}>
                       {c.next_best_actions?.final?.[0]?.action || 'MONITOR'}
                    </TableCell>
                    <TableCell className="text-right py-3 px-4">
                      <Button 
                        size="sm"
                        onClick={() => router.push(`/cases/${c.case_id}`)}
                        className="bg-secondary hover:bg-secondary/80 text-foreground border border-border shadow-none text-xs px-4 whitespace-nowrap"
                      >
                        View &rarr;
                      </Button>
                    </TableCell>
                  </motion.tr>
                );
              })}
            </TableBody>
          </Table>
        </div>
      </Card>

      {/* Trigger Dialog Overlay */}
      <AnimatePresence>
        {showTriggerDialog && (
          <motion.div 
            initial={{ opacity: 0 }} 
            animate={{ opacity: 1 }} 
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
          >
            <motion.div 
              initial={{ scale: 0.95, opacity: 0 }} 
              animate={{ scale: 1, opacity: 1 }} 
              exit={{ scale: 0.95, opacity: 0 }}
              className="bg-card border border-border p-6 rounded-xl shadow-2xl w-full max-w-md"
            >
              <h2 className="text-xl font-bold text-foreground mb-2">New Investigation</h2>
              <p className="text-sm text-muted-foreground mb-6">Enter a transaction ID to trigger the AI agent. The agent will run Graph queries, Jev classification, and LLM synthesis.</p>
              
              <div className="space-y-4">
                <div>
                  <label className="block text-xs font-medium text-muted-foreground uppercase tracking-wider mb-1">Transaction ID</label>
                  <input 
                    type="text" 
                    value={newTxnId}
                    onChange={(e) => setNewTxnId(e.target.value)}
                    placeholder="e.g. 3514030"
                    className="w-full bg-input border border-border rounded-md px-4 py-2 text-foreground focus:outline-none focus:ring-2 focus:ring-primary font-mono"
                    disabled={isInvestigating}
                  />
                </div>
                
                <div className="flex space-x-3 pt-4">
                  <Button 
                    variant="outline" 
                    onClick={() => setShowTriggerDialog(false)}
                    className="flex-1 border-border text-foreground hover:bg-secondary"
                    disabled={isInvestigating}
                  >
                    Cancel
                  </Button>
                  <Button 
                    onClick={handleTrigger}
                    className="flex-1 bg-primary text-primary-foreground hover:bg-primary/90"
                    disabled={isInvestigating || !newTxnId}
                  >
                    {isInvestigating ? (
                      <><Loader2 className="w-4 h-4 mr-2 animate-spin" /> Investigating...</>
                    ) : (
                      <><Play className="w-4 h-4 mr-2 fill-current" /> Run Agent</>
                    )}
                  </Button>
                </div>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
