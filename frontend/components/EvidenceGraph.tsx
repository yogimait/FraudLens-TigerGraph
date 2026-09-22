import { useState, useCallback, useEffect, useMemo } from 'react';
import {
  ReactFlow,
  Controls,
  Background,
  applyNodeChanges,
  applyEdgeChanges,
  NodeChange,
  EdgeChange,
  Node,
  Edge,
  Panel,
  Handle,
  Position,
  MarkerType
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { Badge } from '@/components/ui/badge';
import { CreditCard, ArrowRightLeft, Smartphone, ShieldAlert } from 'lucide-react';

// --- CUSTOM NODES ---

const CardNode = ({ data }: any) => {
  return (
    <div className="bg-[#0A0D14] border border-blue-500/50 rounded-xl p-3 w-48 shadow-[0_0_15px_rgba(59,130,246,0.15)] transition-all hover:border-blue-400 hover:shadow-[0_0_20px_rgba(59,130,246,0.25)]">
      <Handle type="source" position={Position.Bottom} className="w-2 h-2 !bg-blue-500 border-none" />
      <Handle type="target" position={Position.Top} className="w-2 h-2 !bg-blue-500 border-none" />
      <div className="flex items-center gap-2 mb-2">
        <div className="p-1.5 bg-blue-500/20 rounded-md shrink-0">
          <CreditCard className="w-4 h-4 text-blue-400" />
        </div>
        <span className="text-xs font-bold text-foreground truncate">{data.label}</span>
      </div>
      <div className="text-[10px] text-muted-foreground uppercase tracking-wider font-semibold">Account Node</div>
    </div>
  );
};

const TransactionNode = ({ data }: any) => {
  const isHighRisk = data.isHighRisk;
  const borderColor = isHighRisk ? 'border-red-500/50' : 'border-slate-600/50';
  const shadowColor = isHighRisk ? 'shadow-[0_0_15px_rgba(239,68,68,0.15)]' : 'shadow-none';
  const iconBg = isHighRisk ? 'bg-red-500/20' : 'bg-slate-700/50';
  const iconColor = isHighRisk ? 'text-red-400' : 'text-slate-300';

  return (
    <div className={`bg-[#0A0D14] border ${borderColor} rounded-lg p-2.5 w-44 transition-all hover:border-slate-400 ${shadowColor}`}>
      <Handle type="target" position={Position.Top} className="w-2 h-2 !bg-slate-400 border-none" />
      <Handle type="source" position={Position.Bottom} className="w-2 h-2 !bg-slate-400 border-none" />
      <div className="flex items-center gap-2 mb-1.5">
        <div className={`p-1 rounded-md shrink-0 ${iconBg}`}>
          <ArrowRightLeft className={`w-3 h-3 ${iconColor}`} />
        </div>
        <span className="text-xs font-bold text-foreground truncate" title={data.label}>{data.label}</span>
      </div>
      {data.amount !== undefined && (
        <div className="flex justify-between items-center mt-2 pt-2 border-t border-border/50">
          <span className="text-[9px] text-muted-foreground uppercase font-semibold">Amount</span>
          <span className="text-[10px] font-mono text-emerald-400 font-bold">${Number(data.amount).toLocaleString('en-US', {minimumFractionDigits: 2})}</span>
        </div>
      )}
    </div>
  );
};

const DeviceNode = ({ data }: any) => {
  return (
    <div className="bg-[#0A0D14] border border-amber-500/50 rounded-xl p-3 w-44 shadow-[0_0_15px_rgba(245,158,11,0.15)] transition-all hover:border-amber-400 hover:shadow-[0_0_20px_rgba(245,158,11,0.25)]">
      <Handle type="target" position={Position.Top} className="w-2 h-2 !bg-amber-500 border-none" />
      <Handle type="source" position={Position.Bottom} className="w-2 h-2 !bg-amber-500 border-none" />
      <div className="flex items-center gap-2">
        <div className="p-1.5 bg-amber-500/20 rounded-md shrink-0">
          <Smartphone className="w-4 h-4 text-amber-400" />
        </div>
        <div className="overflow-hidden">
          <span className="block text-xs font-bold text-foreground truncate">{data.label}</span>
          <span className="block text-[9px] text-muted-foreground uppercase tracking-wider mt-0.5 font-semibold">Device Node</span>
        </div>
      </div>
    </div>
  );
};

// --- COMPONENT ---

interface EvidenceGraphProps {
  nodes: any[];
  edges: any[];
}

export function EvidenceGraph({ nodes: rawNodes, edges: rawEdges }: EvidenceGraphProps) {
  const [nodes, setNodes] = useState<Node[]>([]);
  const [edges, setEdges] = useState<Edge[]>([]);

  const nodeTypes = useMemo(() => ({
    card: CardNode,
    transaction: TransactionNode,
    device: DeviceNode,
  }), []);

  // Convert raw API graph data to ReactFlow format
  useEffect(() => {
    if (!rawNodes || !rawEdges) return;

    const safeNodes = Array.isArray(rawNodes) ? rawNodes : [];
    const safeEdges = Array.isArray(rawEdges) ? rawEdges : [];
    
    // Grouping setup for hierarchical layout
    const cards = safeNodes.filter(n => n.type === 'card');
    const cardPositions = new Map();
    cards.forEach((c, i) => {
      // Space cards horizontally by 500px to allow room for their transactions
      cardPositions.set(c.id || `node-${i}`, { x: 300 + (i * 600), y: 100 });
    });
    
    const txnCounts = new Map();

    const layoutNodes = safeNodes.map((n, i) => {
      const nodeId = String(n.id || `node-${i}`);
      let x = 400;
      let y = 300;
      
      const nodeData = {
        label: n.label || nodeId,
        amount: n.data?.amount,
        isHighRisk: (n.data?.amount || 0) > 1000
      };

      if (n.type === 'transaction') {
        // Find which card this transaction is connected to
        const edge = safeEdges.find(e => String(e.target) === nodeId || String(e.source) === nodeId);
        const relatedCardId = edge ? (String(edge.source).startsWith('card-') ? String(edge.source) : (String(edge.target).startsWith('card-') ? String(edge.target) : null)) : null;
        
        if (relatedCardId && cardPositions.has(relatedCardId)) {
           const cx = cardPositions.get(relatedCardId).x;
           const count = txnCounts.get(relatedCardId) || 0;
           txnCounts.set(relatedCardId, count + 1);
           
           // Arrange transactions below the card in neat rows of 4
           const row = Math.floor(count / 4);
           const col = count % 4;
           x = cx + (col - 1.5) * 200; // center them under the card (width is 176px, so 200 spacing)
           y = 280 + row * 120;
        } else {
           // Fallback if not connected to a card
           x = 200 + (i * 200) % 800;
           y = 400 + Math.floor(i / 4) * 120;
        }
      } else if (n.type === 'card') {
        if (cardPositions.has(nodeId)) {
          x = cardPositions.get(nodeId).x;
          y = cardPositions.get(nodeId).y;
        } else {
          x = 400; y = 100;
        }
      } else if (n.type === 'device') {
        x = 600 + (i * 180) % 540;
        y = 50 + Math.floor(i / 3) * 120;
      }

      // Map API types to custom node types
      const reactFlowType = (n.type === 'card' || n.type === 'transaction' || n.type === 'device') ? n.type : 'default';

      return {
        id: nodeId,
        type: reactFlowType,
        position: { x, y },
        data: nodeData,
        ...(reactFlowType === 'default' && {
          style: {
            background: 'var(--card)',
            color: 'var(--foreground)',
            border: '1px solid var(--border)',
            borderRadius: '8px',
            padding: '10px'
          }
        })
      };
    });

    const layoutEdges = safeEdges.map((e, i) => {
      const isHighRiskSource = layoutNodes.find(n => n.id === String(e.source))?.data?.isHighRisk;
      const isHighRiskTarget = layoutNodes.find(n => n.id === String(e.target))?.data?.isHighRisk;
      const isHighRiskEdge = isHighRiskSource || isHighRiskTarget;

      return {
        id: String(e.id || `e-${i}`),
        source: String(e.source),
        target: String(e.target),
        label: e.label,
        animated: isHighRiskEdge, // animate edges involving high risk transactions
        type: 'smoothstep', // Use smoothstep for better looking edges
        style: { 
          stroke: isHighRiskEdge ? 'hsl(var(--destructive) / 0.5)' : 'hsl(var(--muted-foreground) / 0.3)', 
          strokeWidth: isHighRiskEdge ? 2 : 1.5 
        },
        markerEnd: {
          type: MarkerType.ArrowClosed,
          color: isHighRiskEdge ? 'hsl(var(--destructive) / 0.5)' : 'hsl(var(--muted-foreground) / 0.3)',
        },
        labelStyle: { fill: 'var(--foreground)', fontSize: 10, fontWeight: 700 },
        labelBgStyle: { fill: 'var(--card)', color: 'var(--foreground)', fillOpacity: 0.8 },
      }
    });

    setNodes(layoutNodes);
    setEdges(layoutEdges);
  }, [rawNodes, rawEdges]);

  const onNodesChange = useCallback(
    (changes: NodeChange[]) => setNodes((nds) => applyNodeChanges(changes, nds)),
    []
  );
  const onEdgesChange = useCallback(
    (changes: EdgeChange[]) => setEdges((eds) => applyEdgeChanges(changes, eds)),
    []
  );

  return (
    <div style={{ width: '100%', height: '100%', minHeight: 400, position: 'relative' }} className="evidence-graph-wrapper">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        style={{ width: '100%', height: '100%' }}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        fitView
        colorMode="dark"
        minZoom={0.2}
        maxZoom={2}
      >
        <Background gap={24} size={1} color="hsl(var(--muted-foreground) / 0.15)" />
        <Controls className="bg-card border-border fill-foreground" />
        <Panel position="top-left" className="bg-card/90 p-3 rounded-lg shadow-xl border border-border flex flex-col gap-3 max-w-xs">
          <div className="flex items-center gap-2 mb-1">
            <ShieldAlert className="w-4 h-4 text-primary" />
            <span className="text-xs font-bold text-foreground uppercase tracking-widest">Graph Legend</span>
          </div>
          <div className="grid grid-cols-2 gap-2">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-blue-500/20 border border-blue-500/50"></div>
              <span className="text-xs text-muted-foreground font-medium">Card/Account</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-sm bg-slate-700/50 border border-slate-600/50"></div>
              <span className="text-xs text-muted-foreground font-medium">Transaction</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-sm bg-red-500/20 border border-red-500/50"></div>
              <span className="text-xs text-muted-foreground font-medium">High Value Txn</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-amber-500/20 border border-amber-500/50"></div>
              <span className="text-xs text-muted-foreground font-medium">Device</span>
            </div>
          </div>
        </Panel>
      </ReactFlow>
    </div>
  );
}
