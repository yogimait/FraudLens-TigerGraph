"use client";

import { useState, useEffect } from 'react';
import axios from 'axios';
import { useParams, useRouter } from 'next/navigation';
import { motion } from 'framer-motion';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { EvidenceGraph } from '@/components/EvidenceGraph';
import { RotateCw, CheckCircle, XCircle, AlertTriangle, ArrowLeft, Loader2, Network, FileText, ShieldAlert, User, Globe, MessageSquareWarning } from 'lucide-react';

const evidenceSourceIcon: Record<string, any> = {
  graph: Network,
  document: FileText,
  customer: User,
  external: Globe,
};

const evidenceSourceStyle: Record<string, string> = {
  graph: 'bg-blue-500/15 text-blue-400 border-blue-500/30',
  document: 'bg-amber-500/15 text-amber-500 border-amber-500/30',
  customer: 'bg-emerald-500/15 text-emerald-500 border-emerald-500/30',
  external: 'bg-purple-500/15 text-purple-400 border-purple-500/30',
};

function RouteBadge({ route }: { route?: string }) {
  const cfg: Record<string, { label: string; cls: string }> = {
    auto: { label: 'AUTO', cls: 'bg-emerald-500/15 text-emerald-500 border-emerald-500/30' },
    L1: { label: 'L1', cls: 'bg-amber-500/15 text-amber-500 border-amber-500/30' },
    L2: { label: 'L2', cls: 'bg-destructive/15 text-destructive border-destructive/30' },
  };
  const c = (route && cfg[route]) || cfg.auto;
  return (
    <Badge variant="outline" className={`text-[10px] font-bold tracking-wider ${c.cls}`}>
      {c.label}
    </Badge>
  );
}

function ActionRow({ act, executed }: { act: any; executed: boolean }) {
  return (
    <div className="flex items-start justify-between gap-4 p-4 bg-secondary/50 rounded-lg border border-border transition-colors hover:bg-secondary">
      <div className="min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="font-bold text-foreground font-mono">{act.action}</span>
          <RouteBadge route={act.route} />
          {executed && (
            <span className="text-[10px] font-bold text-emerald-500 uppercase tracking-wider">Executed by agent</span>
          )}
        </div>
        {act.reason && <p className="text-muted-foreground text-sm mt-1">{act.reason}</p>}
      </div>
    </div>
  );
}

function requiredApprovalLevel(caseData: any): 'L1' | 'L2' {
  const acts = caseData?.next_best_actions?.final || [];
  const exposure = caseData?.case?.exposure_usd ?? caseData?.exposure_usd ?? 0;
  if (acts.some((a: any) => a.action === 'FILE_REPORT' || a.action === 'BLOCK_ALL_CARDS')) return 'L2';
  if (acts.some((a: any) => a.action === 'BLOCK_CARD') && exposure > 2500) return 'L2';
  return 'L1';
}

export default function InvestigationView() {
  const params = useParams();
  const router = useRouter();
  const [caseData, setCaseData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('overview');

  useEffect(() => {
    if (params?.id) {
      fetchCase(params.id as string);
    }
  }, [params?.id]);

  const fetchCase = async (id: string) => {
    try {
      const res = await axios.get(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:3001'}/cases/${id}`);
      setCaseData(res.data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleAction = async (actionType: 'approve' | 'reject' | 'rerun') => {
    if (!caseData?.case_id) return;
    setActionLoading(true);
    try {
      if (actionType === 'rerun') {
        await axios.post(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:3001'}/cases/${caseData.case_id}/trigger`, {
          transaction_id: caseData.transaction_id,
          trigger_type: 'analyst_request'
        });
      } else {
        await axios.post(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:3001'}/cases/${caseData.case_id}/${actionType}`, {
          level: requiredApprovalLevel(caseData),
          reason: `Manually ${actionType}d by analyst`
        });
      }
      await fetchCase(caseData.case_id);
    } catch (e) {
      console.error(e);
      alert(`Action failed: ${e}`);
    } finally {
      setActionLoading(false);
    }
  };

  if (loading) return <div className="p-8 text-foreground bg-background min-h-screen">Loading case data...</div>;
  if (!caseData) return <div className="p-8 text-foreground bg-background min-h-screen">Case not found.</div>;

  const tabs = [
    { id: 'overview', label: 'Overview' },
    { id: 'graph', label: 'Graph View' },
    { id: 'evidence', label: 'Evidence & Analysis' },
    { id: 'policy', label: 'Policy Actions' },
  ];
  if (caseData.sar?.file) tabs.push({ id: 'sar', label: 'SAR Report' });

  const prob = caseData.fraud_probability || 0;
  const isHighRisk = prob > 0.7;
  const isMediumRisk = prob > 0.4 && prob <= 0.7;

  let riskColor = isHighRisk ? "text-destructive" : (isMediumRisk ? "text-amber-500" : "text-emerald-500");
  let riskBadgeColor = isHighRisk ? "bg-destructive/20 text-destructive border-destructive/30" :
                       (isMediumRisk ? "bg-amber-500/20 text-amber-500 border-amber-500/30" : "bg-emerald-500/20 text-emerald-500 border-emerald-500/30");

  let statusBadgeColor = caseData.status === 'closed' ? "bg-emerald-500/10 text-emerald-500 border-emerald-500/20" : "bg-blue-500/10 text-blue-500 border-blue-500/20";
  if (caseData.status === 'awaiting_approval') statusBadgeColor = "bg-purple-500/10 text-purple-400 border-purple-500/20";
  if (caseData.status === 'failed') statusBadgeColor = "bg-destructive/10 text-destructive border-destructive/20";

  const verdictStyles: Record<string, string> = {
    fraud: 'text-destructive',
    legitimate: 'text-emerald-500',
    uncertain: 'text-purple-400',
  };
  const verdictCls = verdictStyles[caseData.verdict] || 'text-foreground';

  const whatChanged = caseData.next_best_actions?.what_changed;
  const initialActions: any[] = caseData.next_best_actions?.initial || [];
  const finalActions: any[] = caseData.next_best_actions?.final || [];

  return (
    <div className="flex-1 p-8 space-y-6 bg-background relative min-h-screen">
      <div className="absolute inset-0 bg-[linear-gradient(to_right,#1E2433_1px,transparent_1px),linear-gradient(to_bottom,#1E2433_1px,transparent_1px)] bg-[size:24px_24px] opacity-20 pointer-events-none"></div>

      {/* Header */}
      <div className="relative z-10 flex justify-between items-start pb-6 border-b border-border">
        <div>
          <div className="flex items-center space-x-3 mb-2">
            <span className="text-sm font-medium text-muted-foreground hover:text-primary cursor-pointer flex items-center" onClick={() => router.push('/')}>
              <ArrowLeft className="w-4 h-4 mr-1" /> Dashboard
            </span>
            <span className="text-sm text-muted-foreground">/</span>
            <span className="text-sm font-medium text-foreground">{caseData.case_id}</span>
          </div>
          <div className="flex items-center space-x-4 mt-2">
            <h1 className="text-3xl font-extrabold text-foreground tracking-tight">Case {caseData.case_id}</h1>
            <Badge variant="outline" className={`text-xs font-bold uppercase tracking-wider ${riskBadgeColor}`}>
              {isHighRisk ? 'High Risk' : (isMediumRisk ? 'Medium Risk' : 'Low Risk')}
            </Badge>
          </div>
          <p className="text-muted-foreground mt-2 text-sm font-mono">
            Transaction: {caseData.transaction_id} • Trigger: {caseData.trigger_type}
          </p>
        </div>

        <div className="flex flex-col items-end space-y-4">
          <div className="text-right">
            <p className="text-xs text-muted-foreground uppercase tracking-wider mb-1">Current Status</p>
            <Badge variant="outline" className={`text-sm font-bold uppercase tracking-wider ${statusBadgeColor}`}>
              {caseData.status.replace('_', ' ')}
            </Badge>
          </div>
          <div className="flex space-x-2">
            <Button
              variant="outline"
              onClick={() => handleAction('rerun')}
              disabled={actionLoading}
              className="bg-secondary text-foreground border-border hover:bg-secondary/80"
            >
              {actionLoading ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <RotateCw className="w-4 h-4 mr-2" />}
              Re-run Agent
            </Button>
            {caseData.status === 'awaiting_approval' && (
              <>
                <Button
                  onClick={() => handleAction('approve')}
                  disabled={actionLoading}
                  className="bg-emerald-600 hover:bg-emerald-700 text-white"
                >
                  <CheckCircle className="w-4 h-4 mr-2" />
                  Approve
                </Button>
                <Button
                  onClick={() => handleAction('reject')}
                  disabled={actionLoading}
                  className="bg-destructive hover:bg-destructive/90 text-white"
                >
                  <XCircle className="w-4 h-4 mr-2" />
                  Reject
                </Button>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="relative z-10 flex gap-8 border-b border-border">
        {tabs.map(t => (
          <button
            key={t.id}
            onClick={() => setActiveTab(t.id)}
            className={`pb-3 text-sm font-medium transition-colors border-b-2 ${activeTab === t.id ? 'border-primary text-primary' : 'border-transparent text-muted-foreground hover:text-foreground'}`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <div className="relative z-10 py-4">
        {activeTab === 'overview' && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <Card className="bg-card border-border shadow-none overflow-hidden">
              <CardHeader className="bg-secondary/30 border-b border-border pb-4">
                <CardTitle className="text-lg text-foreground">Case Details</CardTitle>
              </CardHeader>
              <CardContent className="space-y-0 text-sm p-0">
                <div className="flex flex-col">
                  <div className="flex justify-between py-4 px-6 border-b border-border bg-secondary/10">
                    <span className="text-muted-foreground font-medium">Transaction ID</span>
                    <span className="font-mono text-foreground font-bold">{caseData.transaction_id}</span>
                  </div>
                  <div className="flex justify-between py-4 px-6 border-b border-border">
                    <span className="text-muted-foreground font-medium">Affected Txns</span>
                    <span className="font-mono text-foreground">{caseData.affected_txn_ids?.join(', ') || 'None'}</span>
                  </div>
                  <div className="flex justify-between py-4 px-6 border-b border-border bg-secondary/10">
                    <span className="text-muted-foreground font-medium">First Suspicious Txn</span>
                    <span className="font-mono text-foreground">{caseData.first_suspicious_txn_id || 'N/A'}</span>
                  </div>
                  <div className="flex justify-between py-4 px-6 border-b border-border">
                    <span className="text-muted-foreground font-medium">Jev Classification</span>
                    <span className="text-foreground">{caseData.metadata?.jev_classification?.jev_pattern || 'N/A'}</span>
                  </div>
                  <div className="flex justify-between py-4 px-6 border-b border-border bg-secondary/10">
                    <span className="text-muted-foreground font-medium">Agent Duration</span>
                    <span className="font-mono text-foreground">{caseData.metadata?.duration_seconds || caseData.latency_s || 0}s</span>
                  </div>
                  <div className="flex justify-between py-4 px-6 border-b border-border">
                    <span className="text-muted-foreground font-medium">Tool Calls / Tokens</span>
                    <span className="font-mono text-foreground">{caseData.tool_calls ?? '—'} / {caseData.tokens ?? '—'}</span>
                  </div>
                  <div className="flex justify-between py-4 px-6 border-b border-border bg-secondary/10">
                    <span className="text-muted-foreground font-medium">Written to Graph</span>
                    <span className="text-foreground">
                      {caseData.written_to_graph ? (
                        <span className="font-mono">Yes{caseData.graph_case_id ? ` (${caseData.graph_case_id})` : ''}</span>
                      ) : 'No'}
                    </span>
                  </div>
                  <div className="flex flex-col py-4 px-6 bg-secondary/10">
                    <span className="text-muted-foreground font-medium mb-1">Stop Reason</span>
                    <span className="text-foreground leading-relaxed">{caseData.stop_reason || 'Unknown'}</span>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className="col-span-2 bg-card border-border shadow-none overflow-hidden">
              <CardHeader className="bg-secondary/30 border-b border-border pb-4">
                <CardTitle className="text-lg text-foreground">Fraud Assessment</CardTitle>
              </CardHeader>
              <CardContent className="p-0">
                <div className="grid grid-cols-3">
                  <div className="flex flex-col items-center justify-center p-8 border-r border-border bg-card">
                    <div className="relative w-32 h-32 flex items-center justify-center mb-4">
                      <svg className="absolute inset-0 w-full h-full -rotate-90" viewBox="0 0 100 100">
                        <circle cx="50" cy="50" r="46" fill="transparent" stroke="currentColor" className="text-secondary" strokeWidth="8" />
                        <circle cx="50" cy="50" r="46" fill="transparent" stroke={isHighRisk ? '#EF4444' : (isMediumRisk ? '#F59E0B' : '#10B981')} strokeWidth="8" strokeDasharray={`${Math.max(prob * 289, 10)} 289`} strokeLinecap="round" />
                      </svg>
                      <span className="text-3xl font-extrabold text-foreground relative z-10">{(prob * 100).toFixed(0)}%</span>
                    </div>
                    <p className={`font-bold uppercase tracking-widest text-sm ${riskColor}`}>Probability</p>
                  </div>

                  <div className="col-span-2 flex flex-col justify-center p-8 bg-card/50">
                    <h4 className="font-bold text-muted-foreground uppercase text-xs tracking-wider mb-3">Pattern Classification</h4>
                    <div className="bg-secondary/40 border border-border rounded-lg p-5">
                      <span className="font-bold text-primary text-xl block mb-2">{caseData.pattern || 'Unknown Pattern'}</span>
                      <p className="text-sm text-foreground/90 leading-relaxed">{caseData.pattern_description || 'No description provided by the agent.'}</p>
                    </div>
                  </div>
                </div>

                <div className="grid grid-cols-2 border-t border-border bg-secondary/10">
                  <div className="p-6 border-r border-border">
                    <p className="text-xs font-bold text-muted-foreground uppercase tracking-wider mb-2">Verdict</p>
                    <div className="flex items-center gap-3 flex-wrap">
                      <span className={`font-bold text-2xl capitalize ${verdictCls}`}>{caseData.verdict || 'Pending'}</span>
                      {caseData.verdict === 'uncertain' && (
                        <span className="text-[10px] font-bold uppercase tracking-wider text-purple-400 bg-purple-500/10 border border-purple-500/20 rounded px-2 py-1">
                          Uncertain is a valid verdict
                        </span>
                      )}
                    </div>
                  </div>
                  <div className="p-6">
                    <p className="text-xs font-bold text-muted-foreground uppercase tracking-wider mb-2">Financial Exposure</p>
                    <span className="font-bold text-foreground font-mono text-2xl">${(caseData.exposure_usd || 0).toLocaleString('en-US', {minimumFractionDigits: 2})}</span>
                  </div>
                </div>

                <div className="border-t border-border p-6 space-y-4">
                  <div>
                    <p className="text-xs font-bold text-muted-foreground uppercase tracking-wider mb-2">Connected Cards</p>
                    <div className="flex flex-wrap gap-2">
                      {caseData.connected_card_ids?.length > 0 ? caseData.connected_card_ids.map((id: string) => (
                        <Badge key={id} variant="outline" className="font-mono text-xs bg-secondary/40 border-border text-foreground">{id}</Badge>
                      )) : <span className="text-sm text-muted-foreground">None</span>}
                    </div>
                  </div>
                  <div>
                    <p className="text-xs font-bold text-muted-foreground uppercase tracking-wider mb-2">Connected Device Profiles</p>
                    <div className="flex flex-wrap gap-2">
                      {caseData.connected_device_profiles?.length > 0 ? caseData.connected_device_profiles.map((id: string) => (
                        <Badge key={id} variant="outline" className="font-mono text-xs bg-secondary/40 border-border text-foreground">{id}</Badge>
                      )) : <span className="text-sm text-muted-foreground">None</span>}
                    </div>
                  </div>
                  <div>
                    <p className="text-xs font-bold text-muted-foreground uppercase tracking-wider mb-2">Similar Prior Cases</p>
                    <div className="flex flex-wrap gap-2">
                      {caseData.similar_prior_cases?.length > 0 ? caseData.similar_prior_cases.map((id: string) => (
                        <Badge
                          key={id}
                          variant="outline"
                          className="font-mono text-xs cursor-pointer bg-primary/10 border-primary/20 text-primary hover:bg-primary/20"
                          onClick={() => router.push(`/cases/${id}`)}
                        >
                          {id}
                        </Badge>
                      )) : <span className="text-sm text-muted-foreground">None</span>}
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        {activeTab === 'graph' && (
          <div style={{ width: '100%', minHeight: '500px', height: 'calc(100vh - 280px)' }} className="w-full border border-border rounded-lg overflow-hidden bg-[#0A0D14] relative">
            {(caseData.graph_data?.nodes?.length > 1 || caseData.graph_data?.edges?.length > 0) ? (
              <EvidenceGraph nodes={caseData.graph_data.nodes} edges={caseData.graph_data.edges || []} />
            ) : (
              <div className="absolute inset-0 flex items-center justify-center">
                <div className="text-center flex flex-col items-center">
                  <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-secondary mb-4 border border-border">
                    <Network className="w-8 h-8 text-muted-foreground" />
                  </div>
                  <h3 className="text-xl font-bold text-foreground">No connections found</h3>
                  <p className="text-sm text-muted-foreground mt-2 max-w-md">
                    TigerGraph did not return any related entities, devices, or cards for this transaction. This typically indicates an isolated, low-risk event or a completely new entity without historical overlap.
                  </p>
                </div>
              </div>
            )}
          </div>
        )}

        {activeTab === 'evidence' && (
          <div className="space-y-6">
            <Card className="bg-card border-border shadow-none">
              <CardHeader className="border-b border-border bg-secondary/30 pb-4">
                <CardTitle className="text-lg text-foreground flex items-center">
                  <FileText className="w-5 h-5 mr-2 text-primary" />
                  Synthesis Summary
                </CardTitle>
              </CardHeader>
              <CardContent className="pt-6">
                <div className="prose prose-invert max-w-none text-foreground/90 leading-relaxed text-sm">
                  {caseData.summary ? (
                    caseData.summary.split('\n').map((line: string, i: number) => (
                      <p key={i} className="mb-4 last:mb-0">{line}</p>
                    ))
                  ) : (
                    <p className="text-muted-foreground italic">Summary generation failed or was skipped.</p>
                  )}
                </div>
              </CardContent>
            </Card>

            <Card className="bg-card border-border shadow-none">
              <CardHeader className="border-b border-border bg-secondary/30 pb-4">
                <CardTitle className="text-lg text-foreground">Evidence Collected ({caseData.evidence?.length || 0})</CardTitle>
              </CardHeader>
              <CardContent className="pt-6">
                {caseData.evidence?.length > 0 ? (
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                    {caseData.evidence.map((ev: any, i: number) => {
                      const Icon = evidenceSourceIcon[ev.source] || Globe;
                      const style = evidenceSourceStyle[ev.source] || 'bg-secondary text-foreground border-border';
                      return (
                        <div key={i} className="p-4 bg-secondary/30 rounded-lg border border-border space-y-3">
                          <div className="flex items-center justify-between gap-2">
                            <Badge variant="outline" className={`text-[10px] font-bold uppercase tracking-wider ${style}`}>
                              <Icon className="w-3 h-3 mr-1" />
                              {ev.source}
                            </Badge>
                            <span className="font-mono text-[10px] text-muted-foreground bg-secondary border border-border rounded px-2 py-0.5 truncate max-w-[200px]" title={ev.ref}>
                              {ev.ref}
                            </span>
                          </div>
                          <p className="text-sm text-foreground leading-relaxed">{ev.claim}</p>
                          {ev.entity_ids?.length > 0 && (
                            <div className="flex flex-wrap gap-1.5">
                              {ev.entity_ids.map((id: string) => (
                                <span key={id} className="font-mono text-[10px] text-muted-foreground bg-secondary/60 border border-border rounded px-1.5 py-0.5">
                                  {id}
                                </span>
                              ))}
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground italic">No evidence items recorded.</p>
                )}
              </CardContent>
            </Card>

            {caseData.evidence_requests?.length > 0 && (
              <Card className="bg-card border-border shadow-none">
                <CardHeader className="border-b border-border bg-secondary/30 pb-4">
                  <CardTitle className="text-lg text-foreground flex items-center">
                    <MessageSquareWarning className="w-5 h-5 mr-2 text-amber-500" />
                    Evidence Requests ({caseData.evidence_requests.length})
                  </CardTitle>
                </CardHeader>
                <CardContent className="pt-6">
                  <div className="relative space-y-6 before:absolute before:left-1.5 before:top-2 before:bottom-2 before:w-px before:bg-border">
                    {caseData.evidence_requests.map((req: any, i: number) => (
                      <div key={i} className="relative pl-8">
                        <span className="absolute left-0 top-1 w-3 h-3 rounded-full bg-amber-500/30 border border-amber-500" />
                        <div className="flex items-center gap-3 flex-wrap">
                          <span className="font-bold text-foreground font-mono text-sm">{req.type}</span>
                          <span className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground bg-secondary border border-border rounded px-2 py-0.5">
                            step {req.asked_after_step}
                          </span>
                        </div>
                        <p className="text-sm text-muted-foreground mt-1">{req.assumed_response}</p>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        )}

        {activeTab === 'policy' && (
          <div className="space-y-6">
            <Card className="bg-card border-border shadow-none">
              <CardHeader className="border-b border-border bg-secondary/30 pb-4">
                <CardTitle className="text-lg text-foreground flex items-center">
                  <ShieldAlert className="w-5 h-5 mr-2 text-primary" />
                  Initial Actions (Pre-Evidence)
                </CardTitle>
              </CardHeader>
              <CardContent className="pt-6">
                {initialActions.length > 0 ? (
                  <div className="space-y-3">
                    {initialActions.map((act: any, idx: number) => (
                      <ActionRow key={idx} act={act} executed={act.route === 'auto'} />
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-6 text-muted-foreground">
                    <p>No initial actions recorded.</p>
                  </div>
                )}
              </CardContent>
            </Card>

            <Card className="bg-card border-border shadow-none">
              <CardHeader className="border-b border-border bg-primary/5 pb-4">
                <CardTitle className="text-lg text-primary flex items-center">
                  <CheckCircle className="w-5 h-5 mr-2" />
                  Final Actions (Post-Evidence)
                </CardTitle>
              </CardHeader>
              <CardContent className="pt-6 space-y-4">
                {finalActions.length > 0 ? (
                  <div className="space-y-3">
                    {finalActions.map((act: any, idx: number) => (
                      <div key={idx} className="rounded-lg border border-primary/20 bg-primary/10">
                        <ActionRow act={act} executed={act.route === 'auto'} />
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-6 text-muted-foreground">
                    <p>No final actions recorded.</p>
                  </div>
                )}
                {whatChanged && (
                  <div className="p-4 bg-amber-500/10 border border-amber-500/20 rounded-lg">
                    <p className="text-xs font-bold text-amber-500 uppercase tracking-wider mb-1">What Changed (Initial → Final)</p>
                    <p className="text-sm text-foreground leading-relaxed">{whatChanged}</p>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        )}

        {activeTab === 'sar' && caseData.sar?.file && (
          <Card className="bg-card border-border shadow-none">
            <CardHeader className="bg-secondary/50 border-b border-border">
              <div className="flex justify-between items-center">
                <CardTitle className="text-lg text-foreground">Suspicious Activity Report (SAR)</CardTitle>
                <Badge className="bg-emerald-600">Generated</Badge>
              </div>
            </CardHeader>
            <CardContent className="pt-6 space-y-6">
              <div className="grid grid-cols-3 gap-6">
                <div>
                  <h3 className="text-xs font-bold text-muted-foreground uppercase tracking-wider mb-2">Reason</h3>
                  <p className="text-sm text-foreground leading-relaxed">{caseData.sar.reason || '—'}</p>
                </div>
                <div>
                  <h3 className="text-xs font-bold text-muted-foreground uppercase tracking-wider mb-2">Subjects</h3>
                  <div className="flex flex-wrap gap-1.5">
                    {caseData.sar.subjects?.length > 0 ? caseData.sar.subjects.map((s: string) => (
                      <span key={s} className="font-mono text-xs text-foreground bg-secondary/40 border border-border rounded px-2 py-0.5">{s}</span>
                    )) : <span className="text-sm text-muted-foreground">None</span>}
                  </div>
                </div>
                <div>
                  <h3 className="text-xs font-bold text-muted-foreground uppercase tracking-wider mb-2">Total Amount / Activity Dates</h3>
                  <p className="text-sm font-mono text-foreground">
                    ${(caseData.sar.total_amount_usd || 0).toLocaleString('en-US', {minimumFractionDigits: 2})}
                  </p>
                  <p className="text-xs text-muted-foreground mt-1 font-mono">
                    {(caseData.sar.activity_dates || []).join(', ') || '—'}
                  </p>
                </div>
              </div>
              <div>
                <h3 className="text-xs font-bold text-muted-foreground uppercase tracking-wider mb-3">Narrative</h3>
                <div className="text-sm bg-secondary/30 p-6 rounded border border-border whitespace-pre-wrap leading-relaxed text-foreground">
                  {caseData.sar.narrative || 'Narrative generation failed.'}
                </div>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
