'use client';

import React, { useState, useEffect, useRef } from 'react';
import { Search, Brain, Share2, Info, X, Zap, RefreshCw } from 'lucide-react';
import axios from 'axios';
import { API_URL } from '@/lib/api';

interface NodeData {
  id: number;
  label: string;
  mastery: number;
  exposures: number;
  pos: string;
  gloss: string;
  level: string;
  x?: number;
  y?: number;
}

interface EdgeData {
  source: number;
  target: number;
  relation: string;
}

interface KnowledgeGraphProps {
  userId: string;
  backendUrl: string;
}

export default function KnowledgeGraph({ userId, backendUrl }: KnowledgeGraphProps) {
  const [nodes, setNodes] = useState<NodeData[]>([]);
  const [edges, setEdges] = useState<EdgeData[]>([]);
  const [stats, setStats] = useState({ total_words: 0, total_connections: 0 });
  const [loading, setLoading] = useState<boolean>(true);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [selectedNode, setSelectedNode] = useState<NodeData | null>(null);

  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  const fetchGraphData = async () => {
    setLoading(true);
    try {
      const res = await axios.get(`${API_URL}/api/reader/graph/${userId}`);
      const rawNodes: NodeData[] = res.data.nodes || [];
      const rawEdges: EdgeData[] = res.data.edges || [];

      // Calculate initial layout positions in a force/circle pattern
      const width = 800;
      const height = 550;
      const centerX = width / 2;
      const centerY = height / 2;
      const radius = Math.min(width, height) * 0.38;

      const positionedNodes = rawNodes.map((n, i) => {
        const angle = (i / rawNodes.length) * 2 * Math.PI;
        // Introduce small radial variation for organic look
        const rVar = radius * (0.6 + 0.4 * Math.sin(i * 3));
        return {
          ...n,
          x: centerX + rVar * Math.cos(angle),
          y: centerY + rVar * Math.sin(angle)
        };
      });

      setNodes(positionedNodes);
      setEdges(rawEdges);
      setStats(res.data.stats || { total_words: positionedNodes.length, total_connections: rawEdges.length });
    } catch (err) {
      console.error("Failed to fetch knowledge graph data", err);
    }
    setLoading(false);
  };

  useEffect(() => {
    fetchGraphData();
  }, [userId]);

  // Draw Canvas Graph
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || nodes.length === 0) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Map nodes by ID for fast lookup
    const nodeMap = new Map<number, NodeData>();
    nodes.forEach(n => nodeMap.set(n.id, n));

    // 1. Draw Edges
    edges.forEach(edge => {
      const sourceNode = nodeMap.get(edge.source);
      const targetNode = nodeMap.get(edge.target);
      if (sourceNode?.x && sourceNode?.y && targetNode?.x && targetNode?.y) {
        const isHighlighted = selectedNode && (selectedNode.id === sourceNode.id || selectedNode.id === targetNode.id);

        ctx.beginPath();
        ctx.moveTo(sourceNode.x, sourceNode.y);
        ctx.lineTo(targetNode.x, targetNode.y);
        ctx.strokeStyle = isHighlighted ? '#1A6E6E' : '#e2e8f0';
        ctx.lineWidth = isHighlighted ? 2.5 : 1;
        ctx.stroke();
      }
    });

    // 2. Draw Nodes
    nodes.forEach(n => {
      if (!n.x || !n.y) return;

      const isSelected = selectedNode?.id === n.id;
      const matchesSearch = searchQuery.trim() !== '' && n.label.toLowerCase().includes(searchQuery.toLowerCase());

      // Determine Node Color by Mastery
      let fillColor = '#10b981'; // Moderate
      if (n.mastery >= 0.8) fillColor = '#1A6E6E'; // High mastery
      else if (n.mastery < 0.4) fillColor = '#f59e0b'; // Low / Learning

      const nodeRadius = isSelected ? 16 : matchesSearch ? 15 : 12;

      // Glow effect for selected or searched
      if (isSelected || matchesSearch) {
        ctx.beginPath();
        ctx.arc(n.x, n.y, nodeRadius + 6, 0, 2 * Math.PI);
        ctx.fillStyle = isSelected ? 'rgba(26, 110, 110, 0.25)' : 'rgba(245, 158, 11, 0.3)';
        ctx.fill();
      }

      // Main Node Circle
      ctx.beginPath();
      ctx.arc(n.x, n.y, nodeRadius, 0, 2 * Math.PI);
      ctx.fillStyle = fillColor;
      ctx.fill();
      ctx.strokeStyle = '#ffffff';
      ctx.lineWidth = 2;
      ctx.stroke();

      // Node Text Label
      ctx.font = isSelected ? 'bold 12px Inter, sans-serif' : '11px Inter, sans-serif';
      ctx.fillStyle = isSelected ? '#0f172a' : '#475569';
      ctx.textAlign = 'center';
      ctx.fillText(n.label, n.x, n.y + nodeRadius + 14);
    });

  }, [nodes, edges, selectedNode, searchQuery]);

  const handleCanvasClick = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const clickX = e.clientX - rect.left;
    const clickY = e.clientY - rect.top;

    // Check if clicked near a node
    const clickedNode = nodes.find(n => {
      if (!n.x || !n.y) return false;
      const dist = Math.hypot(n.x - clickX, n.y - clickY);
      return dist <= 18;
    });

    setSelectedNode(clickedNode || null);
  };

  return (
    <div style={{ maxWidth: '980px', margin: '1.5rem auto', padding: '0 1rem' }}>
      {/* Header Stats Bar */}
      <div className="card" style={{ padding: '1.25rem 1.75rem', marginBottom: '1rem', background: '#fff', borderRadius: '16px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <div style={{ width: '42px', height: '42px', borderRadius: '12px', background: '#e6f4f4', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#1A6E6E' }}>
            <Brain size={24} />
          </div>
          <div>
            <h2 style={{ fontSize: '1.25rem', fontWeight: 700, margin: 0, color: '#0f172a' }}>Digitales Gehirn (Wort-Netzwerk)</h2>
            <p style={{ fontSize: '0.85rem', color: '#64748b', margin: 0 }}>Visualisierung deiner gelernten Wörter und neuronalen Verbindungen.</p>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '1.5rem', fontSize: '0.875rem' }}>
          <div>
            <span style={{ color: '#64748b' }}>Wörter: </span>
            <strong style={{ color: '#1A6E6E', fontSize: '1rem' }}>{stats.total_words}</strong>
          </div>
          <div style={{ width: '1px', height: '20px', background: '#e2e8f0' }} />
          <div>
            <span style={{ color: '#64748b' }}>Verbindungen: </span>
            <strong style={{ color: '#10b981', fontSize: '1rem' }}>{stats.total_connections}</strong>
          </div>
        </div>
      </div>

      {/* Legend & Search Control Bar */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem', flexWrap: 'wrap', gap: '1rem' }}>
        {/* Color Legend */}
        <div style={{ display: 'flex', gap: '1rem', alignItems: 'center', fontSize: '0.8rem', background: '#fff', padding: '6px 16px', borderRadius: '9999px', border: '1px solid #e2e8f0' }}>
          <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            <span style={{ width: '10px', height: '10px', borderRadius: '50%', background: '#1A6E6E' }} /> Gelernt (≥80%)
          </span>
          <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            <span style={{ width: '10px', height: '10px', borderRadius: '50%', background: '#10b981' }} /> Im Training (40-79%)
          </span>
          <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            <span style={{ width: '10px', height: '10px', borderRadius: '50%', background: '#f59e0b' }} /> Neu (&lt;40%)
          </span>
        </div>

        {/* Search Input */}
        <div style={{ position: 'relative', width: '240px' }}>
          <Search size={16} color="#94a3b8" style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)' }} />
          <input
            type="text"
            placeholder="Wort suchen..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            style={{
              width: '100%',
              padding: '8px 12px 8px 36px',
              fontSize: '0.85rem',
              borderRadius: '8px',
              border: '1px solid #cbd5e1',
              outline: 'none'
            }}
          />
        </div>
      </div>

      {/* Interactive Canvas Container */}
      <div style={{ position: 'relative', background: '#fff', borderRadius: '16px', border: '1px solid #e2e8f0', overflow: 'hidden', minHeight: '550px' }}>
        {loading ? (
          <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '550px', color: '#94a3b8' }}>
            <RefreshCw className="animate-spin" size={36} />
          </div>
        ) : (
          <canvas
            ref={canvasRef}
            width={800}
            height={550}
            onClick={handleCanvasClick}
            style={{ width: '100%', height: '550px', cursor: 'pointer', display: 'block' }}
          />
        )}

        {/* Selected Word Sidebar / Card */}
        {selectedNode && (
          <div style={{
            position: 'absolute',
            top: '1rem',
            right: '1rem',
            width: '280px',
            background: 'rgba(255, 255, 255, 0.95)',
            backdropFilter: 'blur(8px)',
            borderRadius: '12px',
            padding: '1.25rem',
            boxShadow: '0 10px 25px -5px rgba(0,0,0,0.1)',
            border: '1px solid #cbd5e1',
            zIndex: 10
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.75rem' }}>
              <div>
                <span style={{ fontSize: '0.75rem', fontWeight: 600, color: '#1A6E6E', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                  {selectedNode.pos} ({selectedNode.level})
                </span>
                <h3 style={{ fontSize: '1.35rem', fontWeight: 700, margin: '2px 0 0', color: '#0f172a' }}>
                  {selectedNode.label}
                </h3>
              </div>
              <button onClick={() => setSelectedNode(null)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#94a3b8' }}>
                <X size={18} />
              </button>
            </div>

            <p style={{ fontSize: '0.875rem', color: '#334155', lineHeight: '1.5', marginBottom: '1rem', background: '#f8fafc', padding: '8px 12px', borderRadius: '8px' }}>
              {selectedNode.gloss || 'Keine Erklärung verfügbar.'}
            </p>

            <div style={{ marginBottom: '0.5rem', display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', fontWeight: 600 }}>
              <span>Wortschatz-Meisterschaft</span>
              <span style={{ color: '#1A6E6E' }}>{(selectedNode.mastery * 100).toFixed(0)}%</span>
            </div>
            <div style={{ height: '6px', width: '100%', background: '#e2e8f0', borderRadius: '9999px', overflow: 'hidden' }}>
              <div style={{ height: '100%', width: `${selectedNode.mastery * 100}%`, background: '#1A6E6E', borderRadius: '9999px' }} />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
