"use client";

import { useState, useEffect } from 'react';
import axios from 'axios';
import { useRouter } from 'next/navigation';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { ShieldAlert, CheckCircle2, XCircle, AlertCircle, ArrowRight, UserCog, Loader2 } from 'lucide-react';

export default function ApprovalsPage() {
  const router = useRouter();
  const [cases, setCases] = useState<any[]>([]);
  const [selectedCaseId, setSelectedCaseId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [analystNote, setAnalystNote] = useState('');

  const fetchApprovals = async () => {
    try {
      const res = await axios.get(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:3001'}/cases`);
      const pending = res.data.filter((c: any) => c.status === 'awaiting_approval');
      setCases(pending);
      if (pending.length > 0 && !selectedCaseId) {
        setSelectedCaseId(pending[0].case_id);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchApprovals();
  }, []);

  const handleAction = async (actionType: 'approve' | 'reject') => {
    if (!selectedCaseId) return;
    setActionLoading(true);
    try {
      await axios.post(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:3001'}/cases/${selectedCaseId}/${actionType}`, {
        level: 'L1',
        reason: analystNote || `Manually ${actionType}d by analyst`
      });
      setAnalystNote('');
      
      const currentIndex = cases.findIndex(c => c.case_id === selectedCaseId);
      const remainingCases = cases.filter(c => c.case_id !== selectedCaseId);
      setCases(remainingCases);
      
      if (remainingCases.length > 0) {
        const nextIndex = currentIndex < remainingCases.length ? currentIndex : remainingCases.length - 1;
        setSelectedCaseId(remainingCases[nextIndex].case_id);
      } else {
        setSelectedCaseId(null);
      }

      await fetchApprovals();
    } catch (e) {
      console.error(e);
      alert(`Action failed: ${e}`);
    } finally {
      setActionLoading(false);
    }
  };

  const selectedCase = cases.find(c => c.case_id === selectedCaseId);

  return (
    <div className="flex-1 p-8 overflow-hidden flex flex-col bg-background relative">
      <div className="absolute inset-0 bg-[linear-gradient(to_right,#1E2433_1px,transparent_1px),linear-gradient(to_bottom,#1E2433_1px,transparent_1px)] bg-[size:24px_24px] opacity-20 pointer-events-none"></div>

      <div className="mb-6 shrink-0 flex justify-between items-center relative z-10">
        <div>
          <h1 className="text-3xl font-serif font-extrabold tracking-tight text-foreground">Approvals Center</h1>
          <p className="text-sm text-muted-foreground mt-1">Review escalated investigations per Policy Engine rules.</p>
        </div>
        <Badge className="bg-purple-500/20 text-purple-400 border-purple-500/30 px-3 py-1 font-bold">
          {cases.length} Pending Review
        </Badge>
      </div>
      
      <div className="flex-1 flex gap-6 min-h-0 relative z-10 w-full overflow-hidden">
        {/* Left Pane - Queue */}
        <div className="w-1/3 shrink-0 min-w-[320px] flex flex-col gap-4 overflow-y-auto pr-2 pb-8">
          {loading ? (
            <div className="text-muted-foreground p-4">Loading queue...</div>
          ) : cases.length === 0 ? (
            <div className="text-muted-foreground p-4 bg-card border border-border rounded-lg text-center">
              No pending approvals.
            </div>
          ) : cases.map((item) => {
            const prob = item.fraud_probability || 0;
            const isHighRisk = prob > 0.7;
            const riskLabel = isHighRisk ? "High Risk" : (prob > 0.4 ? "Medium Risk" : "Low Risk");
            const reqLabel = item.next_best_actions?.final?.find((a:any) => a.action.includes('APPROVAL'))?.action || 'L1_APPROVAL';

            return (
              <Card 
                key={item.case_id} 
                className={`cursor-pointer transition-all shadow-none ${selectedCaseId === item.case_id ? 'border-primary ring-1 ring-primary bg-primary/5' : 'border-border bg-card hover:border-primary/50'}`}
                onClick={() => setSelectedCaseId(item.case_id)}
              >
                <CardContent className="p-5">
                  <div className="flex justify-between items-start mb-3">
                    <span className="font-mono font-bold text-foreground">{item.case_id}</span>
                    <Badge variant="outline" className={`text-xs ${isHighRisk ? 'bg-destructive/20 text-destructive border-destructive/30' : 'bg-amber-500/20 text-amber-500 border-amber-500/30'}`}>
                      {riskLabel}
                    </Badge>
                  </div>
                  <div className="space-y-1 mb-4">
                    <div className="flex justify-between text-sm"><span className="text-muted-foreground">Pattern</span><span className="font-medium text-foreground">{item.pattern || 'Unknown'}</span></div>
                    <div className="flex justify-between text-sm"><span className="text-muted-foreground">Exposure</span><span className="font-medium text-foreground font-mono">${(item.exposure_usd || 0).toLocaleString('en-US', {minimumFractionDigits: 2})}</span></div>
                  </div>
                  <div className="flex items-center text-xs font-bold text-purple-400 bg-purple-500/10 rounded px-2 py-1 w-fit border border-purple-500/20">
                    <UserCog className="w-3 h-3 mr-1" /> {reqLabel.replace('REQUIRE_', '')}
                  </div>
                </CardContent>
              </Card>
            )
          })}
        </div>

        {/* Right Pane - Detail */}
        <div className="flex-1 flex flex-col min-h-0 bg-card border border-border rounded-xl shadow-none overflow-hidden">
          {selectedCase ? (
            <>
              <div className="p-6 border-b border-border bg-secondary/50 flex justify-between items-center shrink-0">
                <div>
                  <h2 className="text-xl font-serif font-bold text-foreground">{selectedCase.case_id}</h2>
                  <p className="text-sm text-muted-foreground mt-1">Escalated by Agent: Requires Manual Intervention</p>
                </div>
                <Button 
                  variant="outline" 
                  size="sm" 
                  className="text-primary bg-transparent border-primary/50 hover:bg-primary/10"
                  onClick={() => router.push(`/cases/${selectedCase.case_id}`)}
                >
                  View Full Case <ArrowRight className="w-4 h-4 ml-2" />
                </Button>
              </div>
              
              <div className="p-6 flex-1 overflow-y-auto space-y-6">
                <div>
                  <h3 className="text-xs font-bold text-muted-foreground uppercase tracking-wider mb-3">Proposed Final Actions</h3>
                  <div className="bg-secondary/30 border border-border rounded-lg p-4 flex items-start gap-3 w-full">
                    <ShieldAlert className="w-5 h-5 text-primary mt-0.5 shrink-0" />
                    <div className="space-y-2 w-full min-w-0">
                      {selectedCase.next_best_actions?.final?.map((act: any, i: number) => (
                        <div key={i}>
                          <p className="font-bold text-foreground font-mono truncate">{act.action}</p>
                          <p className="text-sm text-muted-foreground mt-1 break-words whitespace-pre-wrap">{act.reason}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>

                <div>
                  <h3 className="text-xs font-bold text-muted-foreground uppercase tracking-wider mb-3">Policy Trigger & Stop Reason</h3>
                  <div className="bg-secondary/30 border border-border rounded-lg p-4 text-sm text-foreground w-full">
                    <p className="font-medium mb-1 text-primary">Execution Halted</p>
                    <p className="text-muted-foreground break-words whitespace-pre-wrap">{selectedCase.stop_reason || 'Agent requested approval before proceeding.'}</p>
                  </div>
                </div>

                <div>
                  <h3 className="text-xs font-bold text-muted-foreground uppercase tracking-wider mb-3">Analyst Notes</h3>
                  <textarea 
                    className="w-full h-32 p-3 border border-border rounded-lg text-sm bg-input text-foreground focus:outline-none focus:ring-1 focus:ring-primary placeholder:text-muted-foreground/50 transition-colors" 
                    placeholder="Add your justification for approval or rejection here..."
                    value={analystNote}
                    onChange={(e) => setAnalystNote(e.target.value)}
                  ></textarea>
                </div>
              </div>
              
              <div className="p-6 border-t border-border bg-secondary/30 flex justify-end gap-3 shrink-0">
                <Button 
                  variant="outline" 
                  className="border-destructive/30 text-destructive bg-transparent hover:bg-destructive/10"
                  onClick={() => handleAction('reject')}
                  disabled={actionLoading}
                >
                  {actionLoading ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <XCircle className="w-4 h-4 mr-2" />}
                  Reject Action
                </Button>
                <Button 
                  className="bg-emerald-600 hover:bg-emerald-700 text-white"
                  onClick={() => handleAction('approve')}
                  disabled={actionLoading}
                >
                  {actionLoading ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <CheckCircle2 className="w-4 h-4 mr-2" />}
                  Approve Action
                </Button>
              </div>
            </>
          ) : (
            <div className="flex-1 flex items-center justify-center text-muted-foreground font-medium">
              Select a case from the queue to review.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
