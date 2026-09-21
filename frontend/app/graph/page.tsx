"use client";

import { Card } from '@/components/ui/card';
import { EvidenceGraph } from '@/components/EvidenceGraph';

export default function GraphExplorerPage() {
  return (
    <div className="flex-1 p-8 space-y-8 bg-[#F8FAFC]">
      <div>
        <h1 className="text-3xl font-extrabold tracking-tight text-slate-900">Graph Explorer</h1>
        <p className="text-sm text-slate-500 mt-1">Global view of the TigerGraph fraud network.</p>
      </div>
      <Card className="p-6 border-slate-200 shadow-sm bg-white">
        <EvidenceGraph />
      </Card>
    </div>
  );
}
