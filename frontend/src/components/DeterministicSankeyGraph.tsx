/**
 * Deterministic Sankey Graph Component
 * 
 * Renders DCL graph with guaranteed 4-column layout using custom deterministic
 * layout engine. This is a fundamental replacement for d3-sankey that doesn't
 * fight library algorithms.
 * 
 * Preserves all functionality:
 * - Source/agent filtering
 * - Hover effects and highlighting
 * - Narration messaging integration
 * - RAG learning engine hooks
 * - Visual Sankey aesthetic
 */

import { useEffect, useLayoutEffect, useRef, useState } from 'react';
import * as d3 from 'd3';
import { API_CONFIG } from '../config/api';
import {
  calculateDeterministicLayout,
  validateLayerAssignments,
  type GraphNode,
  type GraphEdge,
  type PositionedNode,
  type PositionedEdge,
  type LayoutConfig
} from '../utils/DeterministicGraphLayout';

interface GraphState {
  nodes: Array<{ 
    id: string; 
    label: string; 
    type: string; 
    fields?: string[]; 
    sourceSystem?: string;
    parentId?: string;
  }>;
  edges: Array<{
    source: string;
    target: string;
    label?: string;
    edgeType?: string;
    field_mappings?: any[];
    entity_fields?: string[];
    entity_name?: string;
  }>;
  dev_mode: boolean;
  confidence?: number;
}

interface DeterministicSankeyGraphProps {
  isActive?: boolean;
  selectedSources?: string[];
  selectedAgents?: string[];
}

export default function DeterministicSankeyGraph({ 
  isActive = true,
  selectedSources = [],
  selectedAgents = []
}: DeterministicSankeyGraphProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [state, setState] = useState<GraphState | null>(null);
  const [containerSize, setContainerSize] = useState({ width: 0, height: 0 });
  const [hoveredNode, setHoveredNode] = useState<string | null>(null);

  // Fetch graph state from backend
  useEffect(() => {
    if (!isActive) return;

    const fetchState = async () => {
      try {
        const response = await fetch(API_CONFIG.buildDclUrl('/state'));
        const data = await response.json();
        setState(data);
      } catch (error) {
        console.error('[Deterministic Graph] Error fetching state:', error);
      }
    };

    fetchState();
    
    const handleRefetch = () => fetchState();
    window.addEventListener('dcl-state-changed', handleRefetch);
    
    return () => window.removeEventListener('dcl-state-changed', handleRefetch);
  }, [isActive]);

  // Handle container resizing
  useEffect(() => {
    if (!containerRef.current) return;

    let animationFrameId: number | null = null;
    
    const resizeObserver = new ResizeObserver((entries) => {
      if (animationFrameId) {
        cancelAnimationFrame(animationFrameId);
      }
      
      animationFrameId = requestAnimationFrame(() => {
        for (const entry of entries) {
          const { width, height } = entry.contentRect;
          if (width > 0) {
            setContainerSize({ width, height: height || 400 });
          }
        }
      });
    });

    resizeObserver.observe(containerRef.current);

    return () => {
      if (animationFrameId) {
        cancelAnimationFrame(animationFrameId);
      }
      resizeObserver.disconnect();
    };
  }, []);

  // Render graph when state or selections change
  useLayoutEffect(() => {
    if (!state || !svgRef.current || !containerRef.current) return;
    if (!state.nodes || state.nodes.length === 0) return;
    if (containerSize.width === 0 || containerSize.height === 0) return;

    renderDeterministicGraph(
      state,
      svgRef.current,
      containerSize,
      selectedSources,
      selectedAgents,
      hoveredNode,
      setHoveredNode
    );
  }, [state, containerSize, selectedSources, selectedAgents, hoveredNode]);

  // Loading state
  if (!containerSize.width || !containerSize.height) {
    return (
      <div ref={containerRef} className="rounded-xl bg-gray-800/40 border border-gray-700 shadow-sm ring-1 ring-cyan-500/10 p-1 w-full md:min-h-[400px] flex items-center justify-center">
        <div className="flex items-center justify-center md:min-h-[400px]">
          <div className="text-sm text-gray-400 animate-pulse">Loading graph...</div>
        </div>
      </div>
    );
  }

  return (
    <div ref={containerRef} className="rounded-xl bg-gray-800/40 border border-gray-700 shadow-sm ring-1 ring-cyan-500/10 p-1 w-full md:min-h-[400px] flex items-center justify-center">
      <svg
        ref={svgRef}
        className="w-full h-auto"
        style={{ display: 'block' }}
      />
    </div>
  );
}

/**
 * Core rendering function using deterministic layout
 */
function renderDeterministicGraph(
  state: GraphState,
  svgElement: SVGSVGElement,
  containerSize: { width: number; height: number },
  selectedSources: string[],
  selectedAgents: string[],
  hoveredNode: string | null,
  setHoveredNode: (id: string | null) => void
) {
  const svg = d3.select(svgElement);
  svg.selectAll('*').remove();

  if (!state.nodes || state.nodes.length === 0) {
    svg
      .append('text')
      .attr('x', '50%')
      .attr('y', '50%')
      .attr('text-anchor', 'middle')
      .attr('fill', '#94a3b8')
      .attr('font-size', '14px')
      .text('No data available. Click "Connect & Map" to start.');
    return;
  }

  // STEP 1: Filter nodes based on selections
  let filteredNodes = state.nodes;

  if (selectedSources.length > 0) {
    filteredNodes = filteredNodes.filter(node => {
      if (node.type !== 'source') return true;
      return node.sourceSystem && selectedSources.includes(node.sourceSystem);
    });
  }

  if (selectedAgents.length > 0) {
    filteredNodes = filteredNodes.filter(node => {
      if (node.type !== 'agent') return true;
      const agentName = node.id.replace('agent_', '');
      return selectedAgents.includes(agentName);
    });
  }

  const validNodeIds = new Set(filteredNodes.map(n => n.id));
  const filteredEdges = state.edges.filter(edge => 
    validNodeIds.has(edge.source) && validNodeIds.has(edge.target)
  );

  if (filteredNodes.length === 0) {
    svg
      .append('text')
      .attr('x', '50%')
      .attr('y', '50%')
      .attr('text-anchor', 'middle')
      .attr('fill', '#94a3b8')
      .attr('font-size', '14px')
      .text('No nodes match current filters.');
    return;
  }

  // STEP 2: Assign layers to nodes
  const layerMap: Record<string, number> = {
    'source_parent': 0,
    'source':        1,
    'ontology':      2,
    'agent':         3
  };

  const graphNodes: GraphNode[] = filteredNodes.map(n => ({
    id: n.id,
    label: n.label,
    type: n.type as any,
    sourceSystem: n.sourceSystem,
    parentId: n.parentId,
    fields: n.fields,
    layer: layerMap[n.type] ?? 1
  }));

  const graphEdges: GraphEdge[] = filteredEdges.map(e => ({
    source: e.source,
    target: e.target,
    value: 1,
    edgeType: (e.edgeType ?? 'dataflow') as any,
    fieldMappings: e.field_mappings,
    edgeLabel: e.label,
    entityFields: e.entity_fields,
    entityName: e.entity_name
  }));

  // STEP 3: Validate layer assignments
  const validation = validateLayerAssignments(graphNodes);
  console.log('[Deterministic Graph] Layer validation:', validation);
  
  if (!validation.valid) {
    console.error('[Deterministic Graph] Invalid layer assignments:', validation.errors);
  }

  // STEP 4: Calculate deterministic layout
  const layoutConfig: LayoutConfig = {
    width: containerSize.width,
    height: containerSize.height,
    nodeWidth: 8,
    nodePadding: 18,
    columnPadding: 40
  };

  const layout = calculateDeterministicLayout(graphNodes, graphEdges, layoutConfig);

  console.log('[Deterministic Graph] Layout calculated:', {
    totalNodes: layout.nodes.length,
    distribution: validation.distribution,
    bounds: layout.bounds
  });

  // STEP 5: Set SVG dimensions
  const calculatedHeight = Math.min(
    containerSize.height,
    100 + (layout.nodes.length * 40)
  );

  svg
    .attr('width', containerSize.width)
    .attr('height', calculatedHeight)
    .attr('viewBox', `0 0 ${containerSize.width} ${calculatedHeight}`);

  // STEP 6: Render edges (drawn first, so nodes appear on top)
  const edgeGroup = svg.append('g').attr('class', 'edges');

  edgeGroup
    .selectAll('path')
    .data(layout.edges)
    .join('path')
    .attr('d', d => d.path)
    .attr('fill', 'none')
    .attr('stroke', '#475569')
    .attr('stroke-width', 2)
    .attr('opacity', 0.4)
    .attr('stroke-linecap', 'round');

  // STEP 7: Render nodes
  const nodeGroup = svg.append('g').attr('class', 'nodes');

  const nodeElements = nodeGroup
    .selectAll('g')
    .data(layout.nodes)
    .join('g')
    .attr('class', 'node')
    .attr('transform', d => `translate(${d.x0},${d.y0})`)
    .style('cursor', 'pointer')
    .on('mouseenter', function(event, d) {
      setHoveredNode(d.id);
      d3.select(this).select('rect')
        .attr('stroke-width', 2)
        .attr('stroke', '#06b6d4');
    })
    .on('mouseleave', function(event, d) {
      setHoveredNode(null);
      d3.select(this).select('rect')
        .attr('stroke-width', 1)
        .attr('stroke', '#475569');
    });

  // Node rectangles
  nodeElements
    .append('rect')
    .attr('width', d => d.width)
    .attr('height', d => d.height)
    .attr('fill', '#1e293b')
    .attr('stroke', '#475569')
    .attr('stroke-width', 1)
    .attr('rx', 2);

  // Node labels (for ontology, agent, and source_parent nodes)
  nodeElements
    .filter(d => d.type === 'ontology' || d.type === 'agent' || d.type === 'source_parent')
    .append('text')
    .attr('x', d => d.width + 8)
    .attr('y', d => d.height / 2)
    .attr('dy', '0.35em')
    .attr('fill', '#94a3b8')
    .attr('font-size', '10px')
    .attr('font-family', 'system-ui, -apple-system, sans-serif')
    .text(d => {
      let label = d.label || 'Unknown';
      if (d.type === 'ontology') {
        label = label.replace(/\s*\(unified\)\s*/i, '').trim();
      }
      return label;
    });

  console.log('[Deterministic Graph] Rendered successfully:', {
    nodes: layout.nodes.length,
    edges: layout.edges.length
  });
}
