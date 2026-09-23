'use client';

import { useState, useCallback, useEffect, useMemo, useRef, memo } from 'react';
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
  BackgroundVariant,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import {
  forceSimulation,
  forceLink,
  forceManyBody,
  forceCenter,
  forceCollide,
  SimulationNodeDatum,
  SimulationLinkDatum,
  Simulation,
} from 'd3-force';
import { ShieldAlert, X } from 'lucide-react';

const MAX_NODES = 300;
const HIGH_VALUE_USD = 1000;

type GraphNodeType = 'card' | 'transaction' | 'device' | 'case';

const TYPE_COLORS: Record<GraphNodeType, { fill: string; stroke: string }> = {
  card:        { fill: '#38BDF8', stroke: '#7DD3FC' },
  transaction: { fill: '#34D399', stroke: '#6EE7B7' },
  device:      { fill: '#FBBF24', stroke: '#FDE68A' },
  case:        { fill: '#A78BFA', stroke: '#C4B5FD' },
};
const HIGH_VALUE = { fill: '#F87171', stroke: '#FCA5A5' };

function truncLabel(label: string): string {
  return label.length > 14 ? `${label.slice(0, 14)}…` : label;
}

function nodeRadius(type: GraphNodeType, amount: number | undefined): number {
  if (type === 'transaction') return 14 + Math.min(18, Math.sqrt(Math.max(0, amount || 0)) / 12);
  if (type === 'card') return 26;
  if (type === 'device') return 22;
  return 20;
}

// ── Custom circle node (memo prevents re-render unless data changes) ────
const CircleNode = memo(function CircleNode({ data }: { data: any }) {
  const color = data.highValue
    ? HIGH_VALUE
    : TYPE_COLORS[data.gtype as GraphNodeType] ?? TYPE_COLORS.case;
  return (
    <div
      className="relative flex flex-col items-center"
      style={{ opacity: data.dimmed ? 0.12 : 1, transition: 'opacity 0.2s' }}
    >
      <div
        style={{
          width: data.size,
          height: data.size,
          borderRadius: '50%',
          background: `${color.fill}55`,
          border: `2px solid ${color.stroke}`,
          boxShadow: data.active
            ? `0 0 0 3px ${color.stroke}, 0 0 20px ${color.fill}88`
            : `0 0 8px ${color.fill}33`,
        }}
      />
      <span
        className="absolute top-full mt-1 text-[9px] leading-tight text-slate-300 whitespace-nowrap pointer-events-none select-none"
        style={{ textShadow: '0 1px 3px rgba(0,0,0,0.8)' }}
        title={data.label}
      >
        {truncLabel(String(data.label))}
      </span>
      <Handle type="target" position={Position.Top} isConnectable={false}
        style={{ width: 1, height: 1, top: '50%', left: '50%', background: 'transparent', border: 'none' }} />
      <Handle type="source" position={Position.Bottom} isConnectable={false}
        style={{ width: 1, height: 1, bottom: '50%', left: '50%', background: 'transparent', border: 'none' }} />
    </div>
  );
});

const nodeTypes = { circle: CircleNode };

// ── Simulation types ────────────────────────────────────────────────────
interface SimNode extends SimulationNodeDatum {
  id: string; type: GraphNodeType; label: string; amount: number | undefined;
  fx?: number | null; fy?: number | null;
}
interface SimEdge extends SimulationLinkDatum<SimNode> {
  id: string; label?: string; _src: string; _tgt: string;
}

// ── Helper: build React Flow nodes/edges from sim state ─────────────────
function buildRFNodes(simNodes: SimNode[], radiusById: Map<string, number>): Node[] {
  return simNodes.map((n) => ({
    id: n.id,
    type: 'circle' as const,
    position: { x: n.x ?? 0, y: n.y ?? 0 },
    data: {
      label: n.label, amount: n.amount, gtype: n.type,
      highValue: n.type === 'transaction' && (n.amount || 0) > HIGH_VALUE_USD,
      size: (radiusById.get(n.id) || 16) * 2,
    },
    draggable: true,
  }));
}

function buildRFEdges(simEdges: SimEdge[]): Edge[] {
  return simEdges.map((e) => ({
    id: e.id,
    source: e._src,
    target: e._tgt,
    type: 'default',
    style: { stroke: 'rgba(148, 163, 184, 0.35)', strokeWidth: 1.2 },
  }));
}

// ── Main component ──────────────────────────────────────────────────────
interface EvidenceGraphProps { nodes: any[]; edges: any[] }

export function EvidenceGraph({ nodes: rawNodes, edges: rawEdges }: EvidenceGraphProps) {
  const [nodes, setNodes] = useState<Node[]>([]);
  const [edges, setEdges] = useState<Edge[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [pinnedId, setPinnedId] = useState<string | null>(null);
  const [hidden, setHidden] = useState(0);

  const simRef = useRef<Simulation<SimNode, SimEdge> | null>(null);
  const simNodesRef = useRef<SimNode[]>([]);
  const simEdgesRef = useRef<SimEdge[]>([]);
  const radiusRef = useRef<Map<string, number>>(new Map());
  const rafRef = useRef<number>(0);

  // ── Build simulation ONCE per data change, pre-compute layout (no animation) ──
  useEffect(() => {
    const safeNodes = Array.isArray(rawNodes) ? rawNodes : [];
    const safeEdges = Array.isArray(rawEdges) ? rawEdges : [];
    const sliced = safeNodes.length > MAX_NODES ? safeNodes.slice(0, MAX_NODES) : safeNodes;
    const keepIds = new Set(sliced.map((n) => String(n.id)));
    setHidden(safeNodes.length - sliced.length);

    const sNodes: SimNode[] = sliced.map((n, i) => ({
      id: String(n.id || `node-${i}`),
      type: (['card', 'transaction', 'device', 'case'].includes(n.type) ? n.type : 'case') as GraphNodeType,
      label: String(n.label || n.id || `node-${i}`),
      amount: Number(n.data?.amount) || undefined,
    }));

    const sEdges: SimEdge[] = safeEdges
      .map((e, i) => ({
        id: String(e.id || `e-${i}`),
        source: String(e.source) as any,
        target: String(e.target) as any,
        label: e.label,
        _src: String(e.source),
        _tgt: String(e.target),
      }))
      .filter((e) => keepIds.has(e._src) && keepIds.has(e._tgt) && e._src !== e._tgt);

    const radiusById = new Map<string, number>();
    sNodes.forEach((n) => radiusById.set(n.id, nodeRadius(n.type, n.amount)));

    simNodesRef.current = sNodes;
    simEdgesRef.current = sEdges;
    radiusRef.current = radiusById;

    // Kill previous sim
    if (simRef.current) simRef.current.stop();
    if (rafRef.current) cancelAnimationFrame(rafRef.current);

    const sim = forceSimulation<SimNode>(sNodes)
      .force('link', forceLink<SimNode, SimEdge>(sEdges).id((d) => d.id).distance(100).strength(0.4))
      .force('charge', forceManyBody<SimNode>().strength(-220))
      .force('center', forceCenter(0, 0).strength(0.05))
      .force('collide', forceCollide<SimNode>((d) => (radiusById.get(d.id) || 16) + 6))
      .alphaDecay(0.03)
      .velocityDecay(0.35)
      .stop(); // DON'T auto-run — we tick manually

    // Pre-compute layout: 300 ticks is plenty for convergence
    for (let i = 0; i < 300; i++) sim.tick();
    sim.stop();
    simRef.current = sim;

    // Render the static result once
    setNodes(buildRFNodes(sNodes, radiusById));
    setEdges(buildRFEdges(sEdges));
    setActiveId(null);
    setPinnedId(null);

    return () => {
      sim.stop();
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
    };
  }, [rawNodes, rawEdges]);

  // ── Drag: reheat sim, throttle React renders to every 3rd frame ────────
  const frameCount = useRef(0);

  const onNodeDragStart = useCallback((_: any, node: Node) => {
    const sim = simRef.current;
    if (!sim) return;
    const sn = simNodesRef.current.find((n) => n.id === node.id);
    if (sn) { sn.fx = node.position.x; sn.fy = node.position.y; }
    sim.alphaTarget(0.15).restart();
    frameCount.current = 0;

    const loop = () => {
      sim.tick();
      frameCount.current++;
      // Only push to React every 3rd frame — huge perf win with 300+ nodes
      if (frameCount.current % 3 === 0) {
        setNodes(buildRFNodes(simNodesRef.current, radiusRef.current));
      }
      if (sim.alpha() > 0.001) {
        rafRef.current = requestAnimationFrame(loop);
      }
    };
    if (rafRef.current) cancelAnimationFrame(rafRef.current);
    rafRef.current = requestAnimationFrame(loop);
  }, []);

  const onNodeDrag = useCallback((_: any, node: Node) => {
    const sn = simNodesRef.current.find((n) => n.id === node.id);
    if (sn) { sn.fx = node.position.x; sn.fy = node.position.y; }
  }, []);

  const onNodeDragStop = useCallback((_: any, node: Node) => {
    const sim = simRef.current;
    if (!sim) return;
    sim.alphaTarget(0);
    const sn = simNodesRef.current.find((n) => n.id === node.id);
    if (sn) { sn.fx = null; sn.fy = null; }
    // Final settle — render every 5th frame then stop
    frameCount.current = 0;
    const settle = () => {
      sim.tick();
      frameCount.current++;
      if (frameCount.current % 5 === 0) {
        setNodes(buildRFNodes(simNodesRef.current, radiusRef.current));
      }
      if (sim.alpha() > 0.005) {
        rafRef.current = requestAnimationFrame(settle);
      } else {
        setNodes(buildRFNodes(simNodesRef.current, radiusRef.current)); // final sync
      }
    };
    rafRef.current = requestAnimationFrame(settle);
  }, []);

  const onNodesChange = useCallback(
    (changes: NodeChange[]) => setNodes((nds) => applyNodeChanges(changes, nds)), []
  );
  const onEdgesChange = useCallback(
    (changes: EdgeChange[]) => setEdges((eds) => applyEdgeChanges(changes, eds)), []
  );

  // ── Focus / highlight ─────────────────────────────────────────────────
  const focusNodes = useMemo(() => {
    if (!activeId) return null;
    const s = new Set<string>([activeId]);
    edges.forEach((e) => {
      if (e.source === activeId) s.add(e.target);
      if (e.target === activeId) s.add(e.source);
    });
    return s;
  }, [edges, activeId]);

  const styledNodes = useMemo(() =>
    nodes.map((n) => ({
      ...n,
      data: { ...n.data, active: n.id === activeId, dimmed: focusNodes ? !focusNodes.has(n.id) : false },
      zIndex: n.id === activeId ? 10 : 0,
    })),
  [nodes, focusNodes, activeId]);

  const styledEdges = useMemo(() =>
    edges.map((e) => {
      const hit = focusNodes ? (e.source === activeId || e.target === activeId) : false;
      return hit
        ? { ...e, zIndex: 1, style: { stroke: '#7DD3FC', strokeWidth: 2.5 }, animated: true }
        : e;
    }),
  [edges, focusNodes, activeId]);

  const activeNode = useMemo(
    () => nodes.find((n) => n.id === (pinnedId ?? activeId)) ?? null,
    [nodes, pinnedId, activeId]
  );

  const onNodeMouseEnter = useCallback((_: any, node: Node) => setActiveId(node.id), []);
  const onNodeMouseLeave = useCallback(() => setActiveId((cur) => (pinnedId && cur === pinnedId ? cur : null)), [pinnedId]);
  const onNodeClick = useCallback((_: any, node: Node) => setPinnedId((cur) => (cur === node.id ? null : node.id)), []);
  const onPaneClick = useCallback(() => setPinnedId(null), []);
  const clearAll = useCallback(() => { setPinnedId(null); setActiveId(null); }, []);

  return (
    <div style={{ width: '100%', height: '100%', minHeight: 400, position: 'relative' }} className="evidence-graph-wrapper">
      <ReactFlow
        nodes={styledNodes}
        edges={styledEdges}
        nodeTypes={nodeTypes}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeMouseEnter={onNodeMouseEnter}
        onNodeMouseLeave={onNodeMouseLeave}
        onNodeClick={onNodeClick}
        onNodeDragStart={onNodeDragStart}
        onNodeDrag={onNodeDrag}
        onNodeDragStop={onNodeDragStop}
        onPaneClick={onPaneClick}
        fitView
        colorMode="dark"
        minZoom={0.1}
        maxZoom={2}
        proOptions={{ hideAttribution: true }}
        nodesConnectable={false}
        elementsSelectable={false}
      >
        <Background variant={BackgroundVariant.Dots} gap={24} size={1} color="#1E2433" />
        <Controls className="!bg-[#0A0D14] !border !border-[#1E2433] !rounded-lg [&>button]:!bg-transparent [&>button]:!border-b [&>button]:!border-[#1E2433] [&>button]:!fill-slate-400 [&>button:hover]:!bg-[#1E2433]" />

        {hidden > 0 && (
          <Panel position="bottom-left" className="!bg-transparent">
            <span className="text-[10px] text-muted-foreground font-mono">+{hidden} more nodes hidden</span>
          </Panel>
        )}

        <Panel position="top-left" className="!bg-[#0A0D14]/90 p-3 rounded-lg shadow-xl !border !border-[#1E2433] flex flex-col gap-3 max-w-xs">
          <div className="flex items-center gap-2 mb-1">
            <ShieldAlert className="w-4 h-4 text-primary" />
            <span className="text-xs font-bold text-foreground uppercase tracking-widest">Graph Legend</span>
          </div>
          <div className="grid grid-cols-2 gap-2">
            {([
              ['#38BDF8', '#7DD3FC', 'Card/Account'],
              ['#34D399', '#6EE7B7', 'Transaction'],
              ['#F87171', '#FCA5A5', 'High Value > $1,000'],
              ['#FBBF24', '#FDE68A', 'Device'],
              ['#A78BFA', '#C4B5FD', 'Case Memory'],
            ] as const).map(([fill, stroke, label]) => (
              <div key={label} className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full" style={{ background: `${fill}55`, border: `1.5px solid ${stroke}` }} />
                <span className="text-xs text-muted-foreground font-medium">{label}</span>
              </div>
            ))}
          </div>
        </Panel>

        {activeNode && (
          <Panel position="top-right" className="!bg-[#0A0D14]/95 p-3 rounded-lg shadow-xl !border !border-[#1E2433] w-56">
            <div className="flex items-start justify-between gap-2">
              <div className="min-w-0">
                <div className="text-xs font-bold text-foreground truncate" title={String(activeNode.data?.label)}>
                  {truncLabel(String(activeNode.data?.label ?? ''))}
                </div>
                <div className="text-[10px] uppercase tracking-wider text-muted-foreground mt-0.5 font-semibold">
                  {String(activeNode.data?.gtype ?? 'node')}
                </div>
              </div>
              <button aria-label="Clear selection" onClick={clearAll} className="text-muted-foreground hover:text-foreground shrink-0">
                <X className="w-3.5 h-3.5" />
              </button>
            </div>
            {activeNode.data?.amount !== undefined && (
              <div className="flex justify-between items-center mt-2 pt-2 border-t border-[#1E2433]">
                <span className="text-[9px] text-muted-foreground uppercase font-semibold">Amount</span>
                <span className={`text-[10px] font-mono font-bold ${(Number(activeNode.data.amount) || 0) > HIGH_VALUE_USD ? 'text-red-400' : 'text-emerald-400'}`}>
                  ${Number(activeNode.data.amount).toLocaleString('en-US', { minimumFractionDigits: 2 })}
                </span>
              </div>
            )}
          </Panel>
        )}
      </ReactFlow>
    </div>
  );
}
