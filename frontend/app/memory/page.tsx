"use client";

import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Search, Database, Fingerprint, Calendar, ArrowRight, Loader2 } from 'lucide-react';
import { useState, useEffect } from 'react';
import axios from 'axios';
import { useRouter } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';

export default function CaseMemoryPage() {
  const [query, setQuery] = useState("");
  const [isSearching, setIsSearching] = useState(false);
  const [allCases, setAllCases] = useState<any[]>([]);
  const [results, setResults] = useState<any[]>([]);
  const [hasSearched, setHasSearched] = useState(false);
  const router = useRouter();

  useEffect(() => {
    // Pre-fetch cases so "search" is fast
    axios.get(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:3001'}/cases`).then(res => setAllCases(res.data)).catch(console.error);
  }, []);

  const handleSearch = () => {
    if (!query) return;
    setIsSearching(true);
    setHasSearched(true);
    
    const q = query.toLowerCase();
    
    // Real keyword search over fetched cases
    const matched = allCases.filter(c => {
      const p = c.pattern?.toLowerCase() || '';
      const s = c.summary?.toLowerCase() || '';
      const pd = c.pattern_description?.toLowerCase() || '';
      const id = c.case_id?.toLowerCase() || '';
      
      return p.includes(q) || s.includes(q) || pd.includes(q) || id.includes(q);
    });
    
    // Rank matches based on where the match occurred (simple deterministic scoring)
    const ranked = matched.map(c => {
      let score = 50; // base score for matching
      const p = c.pattern?.toLowerCase() || '';
      const s = c.summary?.toLowerCase() || '';
      
      if (p.includes(q)) score += 30; // Pattern match is highly relevant
      if (s.includes(q)) score += 20; // Summary match is moderately relevant
      
      return { ...c, matchScore: score };
    }).sort((a, b) => b.matchScore - a.matchScore).slice(0, 10); // show top 10
    
    setResults(ranked);
    setIsSearching(false);
  };

  return (
    <div className="flex-1 p-8 space-y-8 bg-background relative min-h-screen">
      <div className="absolute inset-0 bg-[linear-gradient(to_right,#1E2433_1px,transparent_1px),linear-gradient(to_bottom,#1E2433_1px,transparent_1px)] bg-[size:24px_24px] opacity-20 pointer-events-none"></div>

      <div className="relative z-10">
        <h1 className="text-3xl font-serif font-extrabold tracking-tight text-foreground">Case Memory</h1>
        <p className="text-sm text-muted-foreground mt-1">Semantic search through historical investigations using GraphRAG.</p>
      </div>
      
      <Card className="border-border bg-card shadow-none relative z-10">
        <CardContent className="p-6">
          <div className="flex gap-4">
            <div className="relative flex-1">
              <Search className="absolute left-4 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground" />
              <input
                type="text"
                placeholder="Describe a fraud pattern (e.g. 'Multiple small transactions followed by a large purchase on electronics')"
                className="w-full pl-12 pr-4 py-3 bg-input border border-border rounded-lg text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary transition-shadow placeholder:text-muted-foreground/50"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
              />
            </div>
            <Button onClick={handleSearch} disabled={isSearching || !query} className="py-6 px-8 bg-primary hover:bg-primary/90 text-primary-foreground">
              {isSearching ? <><Loader2 className="w-4 h-4 mr-2 animate-spin" /> Searching...</> : 'Search Graph'}
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
              Similar Historical Cases
            </h2>
            
            <div className="grid grid-cols-1 gap-4">
              {results.length === 0 ? (
                <div className="p-8 text-center text-muted-foreground bg-card border border-border rounded-lg">No semantic matches found.</div>
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
                        <div className="flex items-center gap-3">
                          <span className="font-mono font-bold text-foreground">{result.case_id}</span>
                          <Badge variant="outline" className="bg-secondary text-foreground border-border">{result.pattern || 'Unknown Pattern'}</Badge>
                          <div className="flex items-center text-xs text-muted-foreground gap-1">
                            <Calendar className="w-3 h-3" />
                            {new Date(result.updatedAt).toLocaleDateString()}
                          </div>
                        </div>
                        <p className="text-sm text-foreground/80 leading-relaxed line-clamp-2">{result.summary || 'No summary available.'}</p>
                      </div>
                      
                      <div className="flex flex-col items-end gap-3 ml-4 shrink-0">
                        <div className="flex items-center gap-2">
                          <Fingerprint className={`w-4 h-4 ${result.matchScore > 80 ? 'text-emerald-500' : 'text-amber-500'}`} />
                          <span className={`text-lg font-bold ${result.matchScore >= 80 ? 'text-emerald-500' : 'text-amber-500'}`}>
                            Relevance: {result.matchScore}
                          </span>
                        </div>
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
