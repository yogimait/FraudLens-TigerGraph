"use client";

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Download, Filter, FileText, CheckCircle2 } from 'lucide-react';

export default function ReportsPage() {
  const reports = [
    { id: 'SAR-2023-11-892', date: '2023-11-15 08:30', caseId: 'CASE-HHG-082', type: 'Suspicious Activity', status: 'Filed', amount: '$12,450.00' },
    { id: 'SAR-2023-11-891', date: '2023-11-14 14:15', caseId: 'CASE-HHG-019', type: 'Account Takeover', status: 'Filed', amount: '$4,200.00' },
    { id: 'SAR-2023-11-890', date: '2023-11-14 09:00', caseId: 'CASE-HHG-115', type: 'Structuring', status: 'Draft', amount: '$9,900.00' },
    { id: 'AUD-2023-11-004', date: '2023-11-10 17:00', caseId: 'N/A', type: 'Weekly Audit Log', status: 'Completed', amount: 'N/A' },
  ];

  return (
    <div className="flex-1 p-8 space-y-8 bg-[#F8FAFC]">
      <div className="flex justify-between items-end">
        <div>
          <h1 className="text-3xl font-extrabold tracking-tight text-slate-900">Reports & Compliance</h1>
          <p className="text-sm text-slate-500 mt-1">Manage exported SARs and system audit logs.</p>
        </div>
        <div className="flex gap-3">
          <Button variant="outline" className="text-slate-600 bg-white border-slate-200 shadow-sm"><Filter className="w-4 h-4 mr-2" /> Filter</Button>
          <Button className="bg-blue-600 hover:bg-blue-700 text-white shadow-sm"><Download className="w-4 h-4 mr-2" /> Export All</Button>
        </div>
      </div>
      
      <Card className="border-slate-200 shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <Table>
            <TableHeader className="bg-slate-50 border-b border-slate-200">
              <TableRow>
                <TableHead className="font-semibold text-slate-600 text-xs uppercase tracking-wider">Report ID</TableHead>
                <TableHead className="font-semibold text-slate-600 text-xs uppercase tracking-wider">Date Generated</TableHead>
                <TableHead className="font-semibold text-slate-600 text-xs uppercase tracking-wider">Related Case</TableHead>
                <TableHead className="font-semibold text-slate-600 text-xs uppercase tracking-wider">Type</TableHead>
                <TableHead className="font-semibold text-slate-600 text-xs uppercase tracking-wider">Exposure</TableHead>
                <TableHead className="font-semibold text-slate-600 text-xs uppercase tracking-wider">Status</TableHead>
                <TableHead className="text-right font-semibold text-slate-600 text-xs uppercase tracking-wider">Action</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {reports.map((report, i) => (
                <TableRow key={i} className="hover:bg-slate-50 transition-colors border-b border-slate-100 last:border-0">
                  <TableCell className="font-mono text-sm font-medium text-slate-900 flex items-center gap-2">
                    <FileText className="w-4 h-4 text-slate-400" />
                    {report.id}
                  </TableCell>
                  <TableCell className="text-sm text-slate-600">{report.date}</TableCell>
                  <TableCell className="text-sm text-blue-600 font-medium hover:underline cursor-pointer">{report.caseId}</TableCell>
                  <TableCell className="text-sm text-slate-600">{report.type}</TableCell>
                  <TableCell className="text-sm font-mono text-slate-700">{report.amount}</TableCell>
                  <TableCell>
                    {report.status === 'Filed' || report.status === 'Completed' ? (
                      <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200">
                        <CheckCircle2 className="w-3 h-3 mr-1" /> {report.status}
                      </Badge>
                    ) : (
                      <Badge variant="outline" className="bg-amber-50 text-amber-700 border-amber-200">
                        {report.status}
                      </Badge>
                    )}
                  </TableCell>
                  <TableCell className="text-right">
                    <Button variant="ghost" size="sm" className="text-slate-500 hover:text-blue-600">
                      <Download className="w-4 h-4" />
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </Card>
    </div>
  );
}
