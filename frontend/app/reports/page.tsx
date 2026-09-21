"use client";

import { Card } from '@/components/ui/card';

export default function ReportsPage() {
  return (
    <div className="flex-1 p-8 space-y-8 bg-[#F8FAFC]">
      <div>
        <h1 className="text-3xl font-extrabold tracking-tight text-slate-900">Reports</h1>
        <p className="text-sm text-slate-500 mt-1">Exported SARs and compliance documentation.</p>
      </div>
      <Card className="p-8 text-center text-slate-500 border-slate-200 shadow-sm bg-white min-h-[400px] flex items-center justify-center">
        This view is currently under construction.
      </Card>
    </div>
  );
}
