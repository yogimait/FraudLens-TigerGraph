"use client";

import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Search, Database, Calendar, ArrowRight, Loader2, FileText } from 'lucide-react';
import { useState, useEffect } from 'react';
import axios from 'axios';
import { useRouter } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';

const VERDICT_STYLES: Record<string, string> = {
  fraud: 'bg-destructive/15 text-destructive border-destructive/30',
  legitimate: 'bg-emerald-500/15 text-emerald-500 border-emerald-500/30',
  uncertain: 'bg-purple-500/15 text-purple-400 border-purple-500/30',
};

export default function CaseMemoryPage() {
  const [query, setQuery] = useState("");
  const [verdictFilter, setVerdictFilter] = useState('All');
  const [isSearching, setIsSearching] = useState(false);
  const [allCases, setAllCases] = useState<any[]>([]);
  const [results, setResults] = useState<any[]>([]);
  const [hasSearched, setHasSearched] = useState(false);
  const router = useRouter();

  useEffect(() => {
    axios.get(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:3001'}/cases`).then(res => setAllCases(res.data)).catch(console.error);
  }, []);

  const handleSearch = () => {
    if (!query) return;
    setIsSearching(true);
    setHasSearched(true);

    const q = query.toLowerCase();
    const matched = allCases.filter(c => {
      if (verdictFilter !== 'All' && c.verdict !== verdictFilter.toLowerCase()) return false;
      const p = c.pattern?.toLowerCase() || '';
      const s = c.summary?.toLowerCase() || '';
      const pd = c.pattern_description?.toLowerCase() || '';
      const id = c.case_id?.toLowerCase() || '';

      if (p.includes(q)) return true;
      if (s.includes(q)) return true;
      if (pd.includes(q)) return true;
      if (id.includes(q)) return true;
      return false;
    });

    const ranked = matched.map(c => {
      const p = c.pattern?.toLowerCase() || '';
      const s = c.summary?.toLowerCase() || '';
      let matchField = 'case_id';
      if (p.includes(q)) matchField = 'pattern';
      else if (s.includes(q)) matchField = 'summary';
      else if ((c.pattern_description?.toLowerCase() || '').includes(q)) matchField = 'pattern_description';
      return { ...c, matchField };
    });

    setResults(ranked);
    setIsSearching(false);
  };

  return (
    <div className="flex-1 p-8 space-y-8 bg-background relative min-h-screen">
      <div className="absolute inset-0 bg-[linear-gradient(to_right,#1E2433_1px,transparent_1px),linear-gradient(to_bottom,#1E2433_1px,transparent_1px)] bg-[size:24px_24px] opacity-20 pointer-events-none"></div>

      <div className="relative z-10">
        <h1 className="text-3xl font-serif font-extrabold tracking-tight text-foreground">Investigation Archive</h1>
        <p className="text-sm text-muted-foreground mt-1">Search completed investigations in case memory by pattern, summary, or verdict.</p>
      </div>

      <Card className="border-border bg-card shadow-none relative z-10">
        <CardContent className="p-6">
          <div className="flex gap-4">
            <div className="relative flex-1">
              <Search className="absolute left-4 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground" />
              <input
                type="text"
                placeholder="Search by pattern, summary, or case ID (e.g. 'card testing', 'new device')"
                className="w-full pl-12 pr-4 py-3 bg-input border border-border rounded-lg text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary transition-shadow placeholder:text-muted-foreground/50"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
              />
            </div>
            <select
              className="bg-input border border-border rounded-lg px-4 py-3 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
              value={verdictFilter}
              onChange={(e) => setVerdictFilter(e.target.value)}
            >
              <option value="All">All verdicts</option>
              <option value="Fraud">Fraud</option>
              <option value="Legitimate">Legitimate</option>
              <option value="Uncertain">Uncertain</option>
            </select>
            <Button onClick={handleSearch} disabled={isSearching || !query} className="py-6 px-8 bg-primary hover:bg-primary/90 text-primary-foreground">
              {isSearching ? <><Loader2 className="w-4 h-4 mr-2 animate-spin" /> Searching...</> : 'Search'}
            </Button>
          </div>
        </CardContent>
      </Card>

      <AnimatePresence>
        {hasSearched && !isSearching && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="space-y-4 relative z-10"
          >
            <h2 className="text-lg font-serif font-bold text-foreground flex items-center gap-2">
              <Database className="w-5 h-5 text-muted-foreground" />
              Matched Cases ({results.length})
            </h2>

            <div className="grid grid-cols-1 gap-4">
              {results.length === 0 ? (
                <div className="p-8 text-center text-muted-foreground bg-card border border-border rounded-lg">No matching cases found.</div>
              ) : results.map((result, i) => (
                <motion.div
                  key={result.case_id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.1 }}
                >
                  <Card className="border-border bg-card hover:border-primary/50 transition-colors shadow-none">
                    <CardContent className="p-6 flex items-start justify-between">
                      <div className="space-y-3 max-w-3xl">
                        <div className="flex items-center gap-3 flex-wrap">
                          <span className="font-mono font-bold text-foreground">{result.case_id}</span>
                          <Badge variant="outline" className="bg-secondary text-foreground border-border">{result.pattern || 'Unknown Pattern'}</Badge>
                          {result.verdict && (
                            <Badge variant="outline" className={`uppercase text-[10px] font-bold tracking-wider ${VERDICT_STYLES[result.verdict] || 'bg-secondary text-foreground border-border'}`}>
                              {result.verdict}
                            </Badge>
                          )}
                          <Badge variant="outline" className="text-[10px] bg-primary/10 text-primary border-primary/20">
                            <FileText className="w-3 h-3 mr-1" /> matched: {result.matchField}
                          </Badge>
                          <div className="flex items-center text-xs text-muted-foreground gap-1">
                            <Calendar className="w-3 h-3" />
                            {new Date(result.updatedAt).toLocaleDateString()}
                          </div>
                        </div>
                        <p className="text-sm text-foreground/80 leading-relaxed line-clamp-2">{result.summary || 'No summary available.'}</p>
                        {result.similar_prior_cases?.length > 0 && (
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">Similar prior cases:</span>
                            {result.similar_prior_cases.map((id: string) => (
                              <Badge
                                key={id}
                                variant="outline"
                                className="font-mono text-[10px] cursor-pointer bg-primary/5 border-primary/20 text-primary hover:bg-primary/10"
                                onClick={() => router.push(`/cases/${id}`)}
                              >
                                {id}
                              </Badge>
                            ))}
                          </div>
                        )}
                      </div>

                      <div className="flex flex-col items-end gap-3 ml-4 shrink-0">
                        <Button variant="outline" size="sm" className="text-primary bg-primary/5 border-primary/20 hover:bg-primary/10" onClick={() => router.push(`/cases/${result.case_id}`)}>
                          View Case <ArrowRight className="w-4 h-4 ml-2" />
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                </motion.div>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
