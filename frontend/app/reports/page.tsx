"use client";

import { useState, useEffect } from 'react';
import axios from 'axios';
import { useRouter } from 'next/navigation';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Download, Filter, FileText, CheckCircle2 } from 'lucide-react';

export default function ReportsPage() {
  const router = useRouter();
  const [sars, setSars] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchSars();
  }, []);

  const fetchSars = async () => {
    try {
      const res = await axios.get(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:3001'}/cases`);
      const sarCases = res.data.filter((c: any) => c.sar?.file === true);
      setSars(sarCases);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = (caseData: any) => {
    const text = `SUSPICIOUS ACTIVITY REPORT (SAR)\n================================\nCase ID: ${caseData.case_id}\nDate: ${new Date(caseData.updatedAt).toISOString()}\nExposure: $${caseData.exposure_usd}\nPattern: ${caseData.pattern}\n\nNARRATIVE:\n${caseData.sar.narrative}\n`;
    const blob = new Blob([text], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `SAR_${caseData.case_id}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="flex-1 p-8 space-y-8 bg-background relative min-h-screen">
      <div className="absolute inset-0 bg-[linear-gradient(to_right,#1E2433_1px,transparent_1px),linear-gradient(to_bottom,#1E2433_1px,transparent_1px)] bg-[size:24px_24px] opacity-20 pointer-events-none"></div>

      <div className="flex justify-between items-end relative z-10">
        <div>
          <h1 className="text-3xl font-serif font-extrabold tracking-tight text-foreground">Reports & Compliance</h1>
          <p className="text-sm text-muted-foreground mt-1">Manage exported SARs and compliance logs.</p>
        </div>
        <div className="flex gap-3">
          <Button variant="outline" className="text-foreground bg-card border-border shadow-none hover:bg-secondary"><Filter className="w-4 h-4 mr-2" /> Filter</Button>
          <Button className="bg-primary hover:bg-primary/90 text-primary-foreground shadow-none"><Download className="w-4 h-4 mr-2" /> Export All</Button>
        </div>
      </div>
      
      <Card className="border-border bg-card shadow-none overflow-hidden relative z-10">
        <div className="overflow-x-auto">
          <Table>
            <TableHeader className="bg-secondary/50 border-b border-border">
              <TableRow className="border-none hover:bg-transparent">
                <TableHead className="font-semibold text-muted-foreground text-xs uppercase tracking-wider">Report ID</TableHead>
                <TableHead className="font-semibold text-muted-foreground text-xs uppercase tracking-wider">Date Generated</TableHead>
                <TableHead className="font-semibold text-muted-foreground text-xs uppercase tracking-wider">Related Case</TableHead>
                <TableHead className="font-semibold text-muted-foreground text-xs uppercase tracking-wider">Pattern</TableHead>
                <TableHead className="font-semibold text-muted-foreground text-xs uppercase tracking-wider">Exposure</TableHead>
                <TableHead className="font-semibold text-muted-foreground text-xs uppercase tracking-wider">Status</TableHead>
                <TableHead className="text-right font-semibold text-muted-foreground text-xs uppercase tracking-wider">Action</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {loading ? (
                <TableRow><TableCell colSpan={7} className="text-center p-8 text-muted-foreground">Loading SARs...</TableCell></TableRow>
              ) : sars.length === 0 ? (
                <TableRow><TableCell colSpan={7} className="text-center p-8 text-muted-foreground">No SARs have been generated yet.</TableCell></TableRow>
              ) : sars.map((report, i) => (
                <TableRow key={i} className="hover:bg-secondary/30 transition-colors border-b border-border last:border-0">
                  <TableCell className="font-mono text-sm font-medium text-foreground flex items-center gap-2">
                    <FileText className="w-4 h-4 text-primary" />
                    SAR-{report.case_id.replace('CASE-', '')}
                  </TableCell>
                  <TableCell className="text-sm text-muted-foreground">{new Date(report.updatedAt).toLocaleString()}</TableCell>
                  <TableCell 
                    className="text-sm text-primary font-medium hover:underline cursor-pointer"
                    onClick={() => router.push(`/cases/${report.case_id}`)}
                  >
                    {report.case_id}
                  </TableCell>
                  <TableCell className="text-sm text-foreground">{report.pattern}</TableCell>
                  <TableCell className="text-sm font-mono text-foreground">${(report.exposure_usd || 0).toLocaleString('en-US', {minimumFractionDigits: 2})}</TableCell>
                  <TableCell>
                    <Badge variant="outline" className="bg-emerald-500/10 text-emerald-500 border-emerald-500/20">
                      <CheckCircle2 className="w-3 h-3 mr-1" /> Ready
                    </Badge>
                  </TableCell>
                  <TableCell className="text-right">
                    <Button variant="ghost" size="sm" className="text-muted-foreground hover:text-primary hover:bg-primary/10" onClick={() => handleDownload(report)}>
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
