"use client";

import { useState, useEffect } from 'react';
import axios from 'axios';
import { useRouter } from 'next/navigation';
import { motion } from 'framer-motion';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { FolderOpen, Clock, ShieldAlert, CheckCircle2, AlertTriangle, FileText, Verified, XCircle } from 'lucide-react';

export default function Dashboard() {
  const [cases, setCases] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    fetchCases();
  }, []);

  const fetchCases = async () => {
    try {
      const res = await axios.get('http://localhost:3001/cases');
      setCases(res.data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const kpis = [
    { title: "Total Cases", value: "12,845", icon: FolderOpen, color: "text-slate-600" },
    { title: "Open / In Progress", value: "342", icon: Clock, color: "text-blue-600" },
    { title: "Awaiting Evidence", value: "87", icon: ShieldAlert, color: "text-amber-600" },
    { title: "Awaiting Approval", value: "19", icon: Verified, color: "text-purple-600" },
    { title: "Escalated", value: "28", icon: AlertTriangle, color: "text-red-600" },
    { title: "Closed Fraud", value: "1,492", icon: XCircle, color: "text-red-700" },
    { title: "Closed Legitimate", value: "10,877", icon: CheckCircle2, color: "text-emerald-600" },
    { title: "SARs Generated", value: "124", icon: FileText, color: "text-indigo-600" },
  ];

  return (
    <div className="flex-1 p-8 space-y-8 bg-[#F8FAFC]">
      {/* Header Area */}
      <div className="flex justify-between items-start">
        <div>
          <div className="text-sm text-slate-500 mb-1">FraudLens / Incident Management / Active Triage</div>
          <h1 className="text-3xl font-extrabold tracking-tight text-slate-900">Fraud Operations Command Center</h1>
        </div>
        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-2 text-sm font-medium bg-green-100 text-green-800 px-3 py-1 rounded-full">
            <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></span>
            <span>Live Stream: 42 tx/sec</span>
          </div>
          <Button variant="outline" className="border-slate-300 text-slate-700 font-medium">Export SAR Batch</Button>
          <Button className="bg-[#090D16] text-white hover:bg-slate-800 font-medium">Deploy Rule</Button>
        </div>
      </div>

      {/* KPI Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {kpis.map((kpi, i) => (
          <motion.div key={i} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.05 }}>
            <Card className="shadow-sm border-slate-200">
              <CardContent className="p-5 flex items-center space-x-4">
                <div className={`p-3 rounded-lg bg-slate-50 ${kpi.color}`}>
                  <kpi.icon className="w-6 h-6" />
                </div>
                <div>
                  <p className="text-sm font-medium text-slate-500">{kpi.title}</p>
                  <p className="text-2xl font-bold text-slate-900">{kpi.value}</p>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        ))}
      </div>

      {/* Search & Filters */}
      <Card className="p-4 shadow-sm border-slate-200">
        <div className="flex space-x-4">
          <input 
            type="text" 
            placeholder="Search Case ID, Customer ID, Card ID, Transaction ID (Press ⌘K)..." 
            className="flex-1 bg-slate-50 border border-slate-200 rounded-md px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <select className="bg-white border border-slate-200 rounded-md px-4 py-2 text-sm text-slate-700">
            <option>Risk Level: All</option>
          </select>
          <select className="bg-white border border-slate-200 rounded-md px-4 py-2 text-sm text-slate-700">
            <option>Pattern: All</option>
          </select>
          <select className="bg-white border border-slate-200 rounded-md px-4 py-2 text-sm text-slate-700">
            <option>Status: All</option>
          </select>
        </div>
      </Card>

      {/* Data Table */}
      <Card className="shadow-sm border-slate-200 overflow-hidden">
        <div className="overflow-x-auto">
          <Table>
            <TableHeader className="bg-slate-50">
              <TableRow>
                <TableHead className="font-semibold text-slate-600 text-xs uppercase">Case ID</TableHead>
                <TableHead className="font-semibold text-slate-600 text-xs uppercase">Customer</TableHead>
                <TableHead className="font-semibold text-slate-600 text-xs uppercase">Fraud Prob</TableHead>
                <TableHead className="font-semibold text-slate-600 text-xs uppercase">Pattern</TableHead>
                <TableHead className="font-semibold text-slate-600 text-xs uppercase text-right">Exposure</TableHead>
                <TableHead className="font-semibold text-slate-600 text-xs uppercase">Status</TableHead>
                <TableHead className="font-semibold text-slate-600 text-xs uppercase">Next Action</TableHead>
                <TableHead className="font-semibold text-slate-600 text-xs uppercase"></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {loading ? (
                <TableRow><TableCell colSpan={8} className="p-8 text-center text-slate-500">Loading cases...</TableCell></TableRow>
              ) : cases.length === 0 ? (
                <TableRow><TableCell colSpan={8} className="p-8 text-center text-slate-500">No cases found.</TableCell></TableRow>
              ) : cases.map((c, idx) => {
                const prob = c.fraud_probability || 0;
                let riskColor = prob > 0.7 ? "text-red-600" : (prob > 0.4 ? "text-amber-600" : "text-green-600");
                let statusBadge = c.status === 'closed' 
                    ? "bg-green-100 text-green-800" 
                    : "bg-blue-100 text-blue-800";
                
                if (c.status === 'awaiting_approval') statusBadge = "bg-purple-100 text-purple-800";

                return (
                  <motion.tr 
                    key={c.case_id}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.1 + idx * 0.05 }}
                    className="hover:bg-slate-50 transition-colors border-b border-slate-100 last:border-0"
                  >
                    <TableCell className="font-mono text-sm font-medium text-slate-900">{c.case_id}</TableCell>
                    <TableCell className="text-sm text-slate-600">CUST-{c.transaction_id || '90142'}</TableCell>
                    <TableCell>
                      <div className="flex items-center space-x-2">
                        <div className="w-16 h-2 bg-slate-100 rounded-full overflow-hidden">
                          <div className={`h-full ${prob > 0.7 ? 'bg-red-500' : (prob > 0.4 ? 'bg-amber-500' : 'bg-green-500')}`} style={{ width: `${Math.max(prob * 100, 5)}%` }}></div>
                        </div>
                        <span className={`text-xs font-bold ${riskColor}`}>
                          {(prob * 100).toFixed(0)}%
                        </span>
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline" className="bg-slate-50 text-slate-600 border-slate-200">
                        {c.pattern || 'Anomaly'}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right font-mono text-sm font-medium">
                      ${(c.exposure_usd || 0).toLocaleString('en-US', {minimumFractionDigits: 2})}
                    </TableCell>
                    <TableCell>
                      <Badge variant="secondary" className={`${statusBadge} uppercase text-[10px] font-bold tracking-wider`}>
                        {c.status.replace('_', ' ')}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-sm font-medium text-slate-700">
                       {c.next_best_actions?.final?.[0]?.action || 'MONITOR'}
                    </TableCell>
                    <TableCell className="text-right">
                      <Button 
                        size="sm"
                        onClick={() => router.push(`/cases/${c.case_id}`)}
                        className="bg-blue-600 hover:bg-blue-700 text-white shadow-none text-xs px-4"
                      >
                        View Case &rarr;
                      </Button>
                    </TableCell>
                  </motion.tr>
                );
              })}
            </TableBody>
          </Table>
        </div>
      </Card>
    </div>
  );
}
