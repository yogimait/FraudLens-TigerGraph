import { useState, useCallback } from 'react';
import {
  ReactFlow,
  Controls,
  Background,
  applyNodeChanges,
  applyEdgeChanges,
  NodeChange,
  EdgeChange,
  Node,
  Edge
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { Badge } from '@/components/ui/badge';

const initialNodes: Node[] = [
  { id: '1', position: { x: 400, y: 150 }, data: { label: 'Customer C-45892' }, style: { backgroundColor: '#F8FAFC', border: '2px solid #6366F1', borderRadius: '50%', width: 80, height: 80, display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 'bold', fontSize: '10px', textAlign: 'center' } },
  { id: '2', position: { x: 200, y: 100 }, data: { label: 'Card ****9921' }, style: { backgroundColor: '#FEF2F2', border: '2px solid #EF4444', borderRadius: '8px', padding: '10px' } },
  { id: '3', position: { x: 600, y: 100 }, data: { label: 'Device iPhone 14' }, style: { backgroundColor: '#FFFBEB', border: '2px solid #F59E0B', borderRadius: '8px', padding: '10px' } },
  { id: '4', position: { x: 200, y: 300 }, data: { label: 'Txn $2,340' }, style: { backgroundColor: '#FEF2F2', border: '2px solid #EF4444', borderRadius: '8px', padding: '10px' } },
  { id: '5', position: { x: 400, y: 300 }, data: { label: 'Txn $125' }, style: { backgroundColor: '#F8FAFC', border: '1px solid #CBD5E1', borderRadius: '8px', padding: '10px' } },
  { id: '6', position: { x: 750, y: 250 }, data: { label: 'Closed Case #7792' }, style: { backgroundColor: '#F8FAFC', border: '2px solid #64748B', borderRadius: '8px', padding: '10px', color: '#64748B' } },
];

const initialEdges: Edge[] = [
  { id: 'e1-2', source: '1', target: '2', label: 'OWNS', animated: true },
  { id: 'e1-3', source: '1', target: '3', label: 'USES_DEVICE' },
  { id: 'e2-4', source: '2', target: '4', label: 'MADE_TXN', animated: true, style: { stroke: '#EF4444' } },
  { id: 'e2-5', source: '2', target: '5', label: 'MADE_TXN' },
  { id: 'e3-6', source: '3', target: '6', label: 'SHARED_DEVICE', animated: true, style: { stroke: '#F59E0B', strokeDasharray: '5,5' } },
];

export function EvidenceGraph() {
  const [nodes, setNodes] = useState<Node[]>(initialNodes);
  const [edges, setEdges] = useState<Edge[]>(initialEdges);

  const onNodesChange = useCallback(
    (changes: NodeChange[]) => setNodes((nds) => applyNodeChanges(changes, nds)),
    []
  );
  const onEdgesChange = useCallback(
    (changes: EdgeChange[]) => setEdges((eds) => applyEdgeChanges(changes, eds)),
    []
  );

  return (
    <div className="h-[500px] w-full bg-slate-50 border border-slate-200 rounded-lg relative overflow-hidden">
      <div className="absolute top-4 left-4 z-10 bg-white p-2 rounded shadow-sm border border-slate-200 flex gap-2">
        <Badge variant="outline" className="bg-blue-50 text-blue-700">Customer</Badge>
        <Badge variant="outline" className="bg-red-50 text-red-700 border-red-200">Card</Badge>
        <Badge variant="outline" className="bg-amber-50 text-amber-700 border-amber-200">Device</Badge>
        <Badge variant="outline" className="bg-slate-100 text-slate-700">Closed Case</Badge>
      </div>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        fitView
      >
        <Background gap={16} size={1} color="#E2E8F0" />
        <Controls />
      </ReactFlow>
    </div>
  );
}
