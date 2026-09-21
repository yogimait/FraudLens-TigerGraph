"use client";

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardFooter } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { ShieldAlert, CheckCircle2, XCircle, AlertCircle, ArrowRight, UserCog } from 'lucide-react';

export default function ApprovalsPage() {
  const [selectedCase, setSelectedCase] = useState<string | null>('CASE-HHG-020');

  const pendingApprovals = [
    { id: 'CASE-HHG-020', risk: 'Medium Risk', prob: 40, pattern: 'Velocity', amount: '$0.00', req: 'L1 Approval' },
    { id: 'CASE-HHG-019', risk: 'High Risk', prob: 78, pattern: 'Unknown', amount: '$1,200.00', req: 'L2 Approval' },
    { id: 'CASE-HHG-045', risk: 'Medium Risk', prob: 52, pattern: 'Card Testing', amount: '$45.00', req: 'L1 Approval' }
  ];

  return (
    <div className="flex-1 p-8 h-screen overflow-hidden flex flex-col bg-[#F8FAFC]">
      <div className="mb-6 shrink-0 flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-extrabold tracking-tight text-slate-900">Approvals Center</h1>
          <p className="text-sm text-slate-500 mt-1">Review escalated investigations per Policy Engine rules.</p>
        </div>
        <Badge className="bg-orange-100 text-orange-800 border-orange-200 px-3 py-1">3 Pending Review</Badge>
      </div>
      
      <div className="flex-1 flex gap-6 min-h-0">
        {/* Left Pane - Queue */}
        <div className="w-1/3 flex flex-col gap-4 overflow-y-auto pr-2 pb-8">
          {pendingApprovals.map((item) => (
            <Card 
              key={item.id} 
              className={`cursor-pointer transition-all shadow-sm ${selectedCase === item.id ? 'border-blue-500 ring-1 ring-blue-500 bg-blue-50/30' : 'border-slate-200 hover:border-blue-300'}`}
              onClick={() => setSelectedCase(item.id)}
            >
              <CardContent className="p-5">
                <div className="flex justify-between items-start mb-3">
                  <span className="font-mono font-bold text-slate-900">{item.id}</span>
                  <Badge variant="outline" className={`text-xs ${item.risk === 'High Risk' ? 'bg-red-50 text-red-700 border-red-200' : 'bg-amber-50 text-amber-700 border-amber-200'}`}>
                    {item.risk}
                  </Badge>
                </div>
                <div className="space-y-1 mb-4">
                  <div className="flex justify-between text-sm"><span className="text-slate-500">Pattern</span><span className="font-medium text-slate-700">{item.pattern}</span></div>
                  <div className="flex justify-between text-sm"><span className="text-slate-500">Exposure</span><span className="font-medium text-slate-700">{item.amount}</span></div>
                </div>
                <div className="flex items-center text-xs font-bold text-indigo-700 bg-indigo-50 rounded px-2 py-1 w-fit">
                  <UserCog className="w-3 h-3 mr-1" /> {item.req} Required
                </div>
              </CardContent>
            </Card>
          ))}
        </div>

        {/* Right Pane - Detail */}
        <div className="flex-1 flex flex-col min-h-0 bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
          {selectedCase ? (
            <>
              <div className="p-6 border-b border-slate-100 bg-slate-50/50 flex justify-between items-center shrink-0">
                <div>
                  <h2 className="text-xl font-bold text-slate-900">{selectedCase}</h2>
                  <p className="text-sm text-slate-500 mt-1">Escalated by Agent: Requires Manual Intervention</p>
                </div>
                <Button variant="outline" size="sm" className="text-blue-600 bg-white border-blue-200">View Full Case <ArrowRight className="w-4 h-4 ml-2" /></Button>
              </div>
              
              <div className="p-6 flex-1 overflow-y-auto space-y-6">
                <div>
                  <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider mb-3">Proposed Action</h3>
                  <div className="bg-red-50 border border-red-100 rounded-lg p-4 flex items-start gap-3">
                    <ShieldAlert className="w-5 h-5 text-red-600 mt-0.5 shrink-0" />
                    <div>
                      <p className="font-bold text-red-900">BLOCK_CARD and NOTIFY_CUSTOMER</p>
                      <p className="text-sm text-red-700 mt-1">The agent recommends blocking the card immediately due to a high velocity of transactions following a long period of dormancy.</p>
                    </div>
                  </div>
                </div>

                <div>
                  <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider mb-3">Policy Trigger (R8)</h3>
                  <div className="bg-slate-50 border border-slate-200 rounded-lg p-4 text-sm text-slate-700">
                    <p className="font-medium mb-1">High Risk Score, Ambiguous Evidence</p>
                    <p>Fraud Probability is between 30% and 80%, and sufficient historical behavior data could not be retrieved from TigerGraph to confirm Account Takeover automatically. L1 Approval required to proceed with BLOCK_CARD.</p>
                  </div>
                </div>

                <div>
                  <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider mb-3">Analyst Notes</h3>
                  <textarea className="w-full h-32 p-3 border border-slate-200 rounded-lg text-sm bg-slate-50 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:bg-white transition-colors" placeholder="Add your justification for approval or rejection here..."></textarea>
                </div>
              </div>
              
              <div className="p-6 border-t border-slate-100 bg-slate-50 flex justify-end gap-3 shrink-0">
                <Button variant="outline" className="border-slate-300 text-slate-700 bg-white shadow-sm hover:bg-slate-50">
                  <AlertCircle className="w-4 h-4 mr-2" /> Request More Evidence
                </Button>
                <Button variant="outline" className="border-red-200 text-red-700 bg-white hover:bg-red-50 shadow-sm">
                  <XCircle className="w-4 h-4 mr-2" /> Reject Action
                </Button>
                <Button className="bg-emerald-600 hover:bg-emerald-700 text-white shadow-sm">
                  <CheckCircle2 className="w-4 h-4 mr-2" /> Approve Action
                </Button>
              </div>
            </>
          ) : (
            <div className="flex-1 flex items-center justify-center text-slate-400">
              Select a case from the queue to review.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
