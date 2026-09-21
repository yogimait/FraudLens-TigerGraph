"use client";

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Search, Database, Fingerprint, Calendar, ArrowRight } from 'lucide-react';
import { useState } from 'react';

export default function CaseMemoryPage() {
  const [query, setQuery] = useState("");
  const [isSearching, setIsSearching] = useState(false);

  const mockResults = [
    { id: 'CASE-HHG-082', match: 94, type: 'Card Testing', date: '2023-11-14', details: 'Similar pattern of $1-$5 authorizations across 4 merchants within 10 minutes.' },
    { id: 'CASE-HHG-019', match: 88, type: 'Account Takeover', date: '2023-10-22', details: 'Device fingerprint match (IP and User-Agent) on a previously flagged device.' },
    { id: 'CASE-HHG-115', match: 76, type: 'Card Testing', date: '2023-09-05', details: 'Multiple failed CVV attempts followed by a successful small purchase.' }
  ];

  const handleSearch = () => {
    setIsSearching(true);
    setTimeout(() => setIsSearching(false), 800);
  };

  return (
    <div className="flex-1 p-8 space-y-8 bg-[#F8FAFC]">
      <div>
        <h1 className="text-3xl font-extrabold tracking-tight text-slate-900">Case Memory</h1>
        <p className="text-sm text-slate-500 mt-1">Semantic search through historical investigations using GraphRAG.</p>
      </div>
      
      <Card className="border-slate-200 shadow-sm">
        <CardContent className="p-6">
          <div className="flex gap-4">
            <div className="relative flex-1">
              <Search className="absolute left-4 top-3 h-5 w-5 text-slate-400" />
              <input
                type="text"
                placeholder="Describe a fraud pattern (e.g. 'Multiple small transactions followed by a large purchase on electronics')"
                className="w-full pl-12 pr-4 py-3 bg-slate-50 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 transition-shadow"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
              />
            </div>
            <Button onClick={handleSearch} disabled={isSearching || !query} className="py-6 px-8 bg-blue-600 hover:bg-blue-700 text-white">
              {isSearching ? 'Searching...' : 'Search Graph'}
            </Button>
          </div>
        </CardContent>
      </Card>

      <div className="space-y-4">
        <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
          <Database className="w-5 h-5 text-slate-500" />
          Similar Historical Cases
        </h2>
        
        <div className="grid grid-cols-1 gap-4">
          {mockResults.map((result, i) => (
            <Card key={i} className="border-slate-200 hover:border-blue-300 transition-colors shadow-sm">
              <CardContent className="p-6 flex items-start justify-between">
                <div className="space-y-3">
                  <div className="flex items-center gap-3">
                    <span className="font-mono font-bold text-slate-900">{result.id}</span>
                    <Badge variant="outline" className="bg-slate-50 text-slate-600">{result.type}</Badge>
                    <div className="flex items-center text-xs text-slate-500 gap-1">
                      <Calendar className="w-3 h-3" />
                      {result.date}
                    </div>
                  </div>
                  <p className="text-sm text-slate-600 max-w-2xl">{result.details}</p>
                </div>
                
                <div className="flex flex-col items-end gap-3">
                  <div className="flex items-center gap-2">
                    <Fingerprint className={`w-4 h-4 ${result.match > 90 ? 'text-green-600' : 'text-amber-500'}`} />
                    <span className={`text-lg font-bold ${result.match > 90 ? 'text-green-600' : 'text-amber-500'}`}>
                      {result.match}% Match
                    </span>
                  </div>
                  <Button variant="outline" size="sm" className="text-blue-600 border-blue-200 hover:bg-blue-50">
                    View Case <ArrowRight className="w-4 h-4 ml-2" />
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </div>
  );
}
