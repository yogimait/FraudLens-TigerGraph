"use client";

import { useState, useEffect } from 'react';
import axios from 'axios';
import { Card } from '@/components/ui/card';
import { EvidenceGraph } from '@/components/EvidenceGraph';
import { Loader2 } from 'lucide-react';

export default function GraphExplorerPage() {
  const [nodes, setNodes] = useState<any[]>([]);
  const [edges, setEdges] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchGlobalGraph = async () => {
      try {
        const res = await axios.get(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:3001'}/cases`);
        const cases = res.data;
        
        let allNodes: any[] = [];
        let allEdges: any[] = [];
        
        // Aggregate first 5 cases to avoid massive overlap for the demo
        cases.slice(0, 5).forEach((c: any) => {
          if (c.graph_data?.nodes) {
            allNodes = [...allNodes, ...c.graph_data.nodes];
          }
          if (c.graph_data?.edges) {
            allEdges = [...allEdges, ...c.graph_data.edges];
          }
        });

        // Deduplicate nodes
        const uniqueNodes = Array.from(new Map(allNodes.map(item => [item.id, item])).values());

        setNodes(uniqueNodes);
        setEdges(allEdges);
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    };
    fetchGlobalGraph();
  }, []);

  return (
    <div className="flex-1 p-8 space-y-8 bg-background relative min-h-screen">
      <div className="absolute inset-0 bg-[linear-gradient(to_right,#1E2433_1px,transparent_1px),linear-gradient(to_bottom,#1E2433_1px,transparent_1px)] bg-[size:24px_24px] opacity-20 pointer-events-none"></div>

      <div className="relative z-10">
        <h1 className="text-3xl font-serif font-extrabold tracking-tight text-foreground">Graph Explorer</h1>
        <p className="text-sm text-muted-foreground mt-1">Global view of the TigerGraph fraud network.</p>
      </div>
      
      <Card className="p-1 border-border shadow-none bg-card h-[700px] relative z-10 overflow-hidden">
        {loading ? (
          <div className="h-full w-full flex items-center justify-center text-muted-foreground">
            <Loader2 className="w-8 h-8 animate-spin" />
          </div>
        ) : (
          <EvidenceGraph nodes={nodes} edges={edges} />
        )}
      </Card>
    </div>
  );
}
