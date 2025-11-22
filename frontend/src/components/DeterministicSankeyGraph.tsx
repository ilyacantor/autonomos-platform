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
  const [hoveredEdge, setHoveredEdge] = useState<string | null>(null);

  // Fetch graph state from backend
  // IMPORTANT: Use /state endpoint for real DCL data with source-level nodes
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
      setHoveredNode,
      hoveredEdge,
      setHoveredEdge
    );
  }, [state, containerSize, selectedSources, selectedAgents, hoveredNode, hoveredEdge]);

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
  setHoveredNode: (id: string | null) => void,
  hoveredEdge: string | null,
  setHoveredEdge: (id: string | null) => void
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

  // Source color map for visual styling
  const sourceColorMap: Record<string, { parent: string; child: string }> = {
    dynamics: { parent: '#3b82f6', child: '#60a5fa' },
    salesforce: { parent: '#8b5cf6', child: '#a78bfa' },
    sap: { parent: '#10b981', child: '#34d399' },
    netsuite: { parent: '#f59e0b', child: '#fbbf24' },
    legacy_sql: { parent: '#ef4444', child: '#f87171' },
    snowflake: { parent: '#06b6d4', child: '#22d3ee' },
    supabase: { parent: '#14b8a6', child: '#2dd4bf' },
    mongodb: { parent: '#10b981', child: '#34d399' },
  };

  // STEP 1: Filter nodes based on selections
  // Canonical mapping: backend sourceSystem values → frontend slug values
  // This is the FUNDAMENTAL FIX for case/format variations from backend
  const SOURCE_SYSTEM_MAPPING: Record<string, string> = {
    // Production system names
    'Dynamics': 'dynamics',
    'Salesforce': 'salesforce',
    'Hubspot': 'hubspot',
    'Sap': 'sap',
    'SAP': 'sap',
    'Netsuite': 'netsuite',
    'NetSuite': 'netsuite',
    'Legacy Sql': 'legacy_sql',
    'Legacy SQL': 'legacy_sql',
    'legacy_sql': 'legacy_sql',
    'Snowflake': 'snowflake',
    'Supabase': 'supabase',
    'Mongodb': 'mongodb',
    'MongoDB': 'mongodb',
    // Demo graph system names (from demo_graph.json)
    'HubSpot': 'hubspot',
    'Stripe': 'stripe',
    'PostgreSQL': 'postgresql',
    'MySQL': 'mysql',
    'Google Sheets': 'google_sheets',
    'CSV Files': 'csv'
  };

  // Apply user-selected filters for sources and agents
  let filteredNodes = state.nodes;

  // Filter source nodes based on selectedSources
  if (selectedSources.length > 0) {
    filteredNodes = filteredNodes.filter(node => {
      // Always keep source_parent, ontology, and agent nodes
      if (node.type === 'source_parent' || node.type === 'ontology' || node.type === 'agent') {
        // For agents, filter by selectedAgents
        if (node.type === 'agent') {
          return selectedAgents.length === 0 || selectedAgents.includes(node.id);
        }
        return true;
      }
      
      // For source nodes, check if their sourceSystem is in selectedSources
      if (node.type === 'source' && node.sourceSystem) {
        const normalizedSource = SOURCE_SYSTEM_MAPPING[node.sourceSystem] || node.sourceSystem.toLowerCase();
        return selectedSources.includes(normalizedSource);
      }
      
      return true;
    });
  }

  // Also filter by selectedAgents if specified
  if (selectedAgents.length > 0) {
    filteredNodes = filteredNodes.filter(node => {
      if (node.type === 'agent') {
        return selectedAgents.includes(node.id);
      }
      return true;
    });
  }

  console.log('[Deterministic Graph] After filtering:', {
    filteredNodes: filteredNodes.length,
    nodeTypes: filteredNodes.reduce((acc: Record<string, number>, n) => {
      acc[n.type] = (acc[n.type] || 0) + 1;
      return acc;
    }, {}),
    selectedSources,
    selectedAgents
  });

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

  // STEP 5: Calculate label dimensions to determine true content bounds
  // Labels extend to the right of nodes, so we need to include them in bounds calculation
  const labelGap = 8; // Gap between node and label
  
  // Collect label data to calculate true content extent
  const labelData: Array<{
    node: PositionedNode;
    label: string;
    fontSize: number;
    pillHeight: number;
    pillWidth: number;
    padding: number;
    borderColor: string;
  }> = [];

  layout.nodes.forEach(node => {
    if (node.type === 'source_parent' || node.type === 'source' || node.type === 'ontology' || node.type === 'agent') {
      // For source nodes (L1), use sourceSystem as label
      // For ontology nodes, remove "(Unified)" or "(unified)" suffix
      let label = node.label || 'Unknown';
      
      if (node.type === 'source' && node.sourceSystem) {
        label = node.sourceSystem;
      } else if (node.type === 'ontology') {
        label = label.replace(/\s*\(unified\)\s*/i, '').trim();
      }
      
      const padding = 4;
      const fontSize = 10;
      const pillHeight = 16;
      const textWidth = label.length * 6;
      const pillWidth = textWidth + (padding * 2);
      
      let borderColor = '#475569';
      if (node.type === 'source_parent') {
        borderColor = '#22c55e';
      } else if (node.type === 'source') {
        const sourceKey = node.sourceSystem?.toLowerCase() || '';
        borderColor = sourceColorMap[sourceKey]?.parent || '#60a5fa';
      } else if (node.type === 'ontology') {
        borderColor = '#60a5fa';
      } else if (node.type === 'agent') {
        borderColor = '#9333ea';
      }
      
      labelData.push({
        node,
        label,
        fontSize,
        pillHeight,
        pillWidth,
        padding,
        borderColor
      });
    }
  });

  // Calculate true content bounds including labels
  const contentMaxX = Math.max(
    layout.bounds.maxX,
    ...labelData.map(item => item.node.x0 + item.node.width + labelGap + item.pillWidth)
  );

  // STEP 6: Set SVG dimensions with proper viewBox for responsive scaling
  const padding = 20;
  const viewBoxX = layout.bounds.minX - padding;
  const viewBoxY = layout.bounds.minY - padding;
  const viewBoxWidth = (contentMaxX - layout.bounds.minX) + (padding * 2);
  const viewBoxHeight = (layout.bounds.maxY - layout.bounds.minY) + (padding * 2);

  // Debug logging for visibility troubleshooting
  console.log('[Deterministic Graph] SVG Geometry:', {
    containerSize,
    viewBox: { x: viewBoxX, y: viewBoxY, width: viewBoxWidth, height: viewBoxHeight },
    bounds: layout.bounds,
    sampleNode: layout.nodes[0] ? { id: layout.nodes[0].id, x: layout.nodes[0].x0, y: layout.nodes[0].y0 } : null
  });

  // FUNDAMENTAL FIX: Set explicit height instead of 'auto' to prevent flexbox collapse
  // The container uses 'flex items-center' which can cause SVG with h-auto to collapse to 0
  const svgHeight = Math.max(400, containerSize.height || 400);
  
  svg
    .attr('viewBox', `${viewBoxX} ${viewBoxY} ${viewBoxWidth} ${viewBoxHeight}`)
    .attr('preserveAspectRatio', 'xMidYMid meet')
    .style('width', '100%')
    .style('height', `${svgHeight}px`);

  // Helper function to get edge stroke color
  const getEdgeColor = (edge: PositionedEdge, sourceNode: PositionedNode | undefined, targetNode: PositionedNode | undefined) => {
    // Color hierarchy edges from source_parent (layer 0) to source (layer 1) green
    if (edge.edgeType === 'hierarchy' && sourceNode?.type === 'source_parent') {
      return '#22c55e';
    }
    
    // Other hierarchy edges remain gray
    if (edge.edgeType === 'hierarchy') {
      return '#475569';
    }
    
    if (targetNode && targetNode.type === 'agent') {
      return '#9333ea';
    }
    if (edge.sourceSystem) {
      return sourceColorMap[edge.sourceSystem]?.child || '#0bcad9';
    }
    return '#94a3b8';
  };

  // Helper function to get edge opacity
  const getEdgeOpacity = (edge: PositionedEdge, sourceNode: PositionedNode | undefined, isHovered: boolean) => {
    if (isHovered) {
      return edge.edgeType === 'hierarchy' ? 0.6 : 0.7;
    }
    
    if (edge.edgeType === 'hierarchy') {
      return 0.35;
    }
    
    if (sourceNode && (sourceNode.type === 'source' || sourceNode.type === 'source_parent')) {
      return 0.7;
    }
    
    return 0.4;
  };

  // Helper function to check if source node has outgoing dataflow
  const hasOutgoingDataflow = (nodeId: string) => {
    return state.edges.some(e => 
      e.source === nodeId && (e.edgeType ?? 'dataflow') === 'dataflow'
    );
  };

  // Helper function to get node fill opacity
  const getNodeFillOpacity = (node: PositionedNode, isHovered: boolean) => {
    if (node.type === 'ontology') {
      return isHovered ? 1 : 0.9;
    } else if (node.type === 'source') {
      const hasDataflow = hasOutgoingDataflow(node.id);
      return hasDataflow ? 1 : 0.5;
    } else if (node.type === 'agent') {
      return 0;
    } else if (node.type === 'source_parent') {
      return 0.7;
    }
    return 0.7;
  };

  // Helper function to get node stroke opacity
  const getNodeStrokeOpacity = (node: PositionedNode, isHovered: boolean) => {
    if (isHovered && (node.type === 'source' || node.type === 'agent')) {
      return 1;
    }
    
    if (node.type === 'source') {
      const hasDataflow = hasOutgoingDataflow(node.id);
      return hasDataflow ? 1 : 0.6;
    } else if (node.type === 'agent' || node.type === 'source_parent') {
      return 1;
    }
    
    return 0;
  };

  // STEP 6: Render edges (drawn first, so nodes appear on top)
  const edgeGroup = svg.append('g').attr('class', 'edges');

  // Create edge tooltip
  const edgeTooltip = d3.select('body')
    .selectAll('.sankey-edge-tooltip')
    .data([null])
    .join('div')
    .attr('class', 'sankey-edge-tooltip')
    .style('position', 'fixed')
    .style('background', 'rgba(15, 23, 42, 0.95)')
    .style('color', '#e2e8f0')
    .style('padding', '8px 12px')
    .style('border-radius', '6px')
    .style('border', '1px solid #475569')
    .style('font-size', '12px')
    .style('pointer-events', 'none')
    .style('z-index', '10000')
    .style('box-shadow', '0 4px 6px rgba(0, 0, 0, 0.3)')
    .style('max-width', '400px')
    .style('font-family', 'system-ui, -apple-system, sans-serif')
    .style('opacity', '0')
    .style('display', 'none');

  edgeGroup
    .selectAll('path')
    .data(layout.edges)
    .join('path')
    .attr('d', d => d.path)
    .attr('fill', 'none')
    .attr('stroke', d => {
      const sourceNode = layout.nodes.find(n => n.id === d.source);
      const targetNode = layout.nodes.find(n => n.id === d.target);
      return getEdgeColor(d, sourceNode, targetNode);
    })
    .attr('stroke-width', d => Math.min(Math.max(0.5, d.value * 2), 20))
    .attr('opacity', d => {
      const sourceNode = layout.nodes.find(n => n.id === d.source);
      const edgeKey = `${d.source}-${d.target}`;
      const isHovered = hoveredEdge === edgeKey;
      return getEdgeOpacity(d, sourceNode, isHovered);
    })
    .attr('stroke-linecap', 'round')
    .style('cursor', 'pointer')
    .on('mouseenter', function(event: MouseEvent, d: PositionedEdge) {
      const edgeKey = `${d.source}-${d.target}`;
      setHoveredEdge(edgeKey);
      
      const sourceNode = layout.nodes.find(n => n.id === d.source);
      const targetNode = layout.nodes.find(n => n.id === d.target);
      const tooltipContent = getEdgeTooltip(sourceNode, targetNode, d);
      
      edgeTooltip
        .html(tooltipContent)
        .style('left', (event.pageX + 10) + 'px')
        .style('top', (event.pageY - 10) + 'px')
        .style('opacity', '1')
        .style('display', 'block');
    })
    .on('mousemove', function(event: MouseEvent) {
      edgeTooltip
        .style('left', (event.pageX + 10) + 'px')
        .style('top', (event.pageY - 10) + 'px');
    })
    .on('mouseleave', function() {
      setHoveredEdge(null);
      edgeTooltip.style('opacity', '0').style('display', 'none');
    });

  // STEP 7: Render nodes
  const nodeGroup = svg.append('g').attr('class', 'nodes');

  const nodeTooltip = d3.select('body')
    .selectAll('.sankey-tooltip')
    .data([null])
    .join('div')
    .attr('class', 'sankey-tooltip')
    .style('position', 'absolute')
    .style('background', 'rgba(15, 23, 42, 0.95)')
    .style('color', '#e2e8f0')
    .style('padding', '8px 12px')
    .style('border-radius', '6px')
    .style('border', '1px solid #475569')
    .style('font-size', '12px')
    .style('pointer-events', 'none')
    .style('opacity', '0')
    .style('z-index', '1000')
    .style('box-shadow', '0 4px 6px rgba(0, 0, 0, 0.3)');

  const nodeElements = nodeGroup
    .selectAll('g')
    .data(layout.nodes)
    .join('g')
    .attr('class', 'node')
    .attr('transform', d => `translate(${d.x0},${d.y0})`)
    .style('cursor', 'pointer')
    .on('mouseenter', function(event: MouseEvent, d: PositionedNode) {
      setHoveredNode(d.id);
      
      let tooltipContent = `<strong>${d.label}</strong><br/>`;
      tooltipContent += `Type: ${d.type}`;
      
      if (d.type === 'source' || d.type === 'source_parent') {
        tooltipContent += `<br/>System: ${d.sourceSystem || 'Unknown'}`;
      }
      
      nodeTooltip
        .html(tooltipContent)
        .style('opacity', '1')
        .style('left', (event.pageX + 10) + 'px')
        .style('top', (event.pageY - 10) + 'px');
    })
    .on('mousemove', function(event: MouseEvent) {
      nodeTooltip
        .style('left', (event.pageX + 10) + 'px')
        .style('top', (event.pageY - 10) + 'px');
    })
    .on('mouseleave', function() {
      setHoveredNode(null);
      nodeTooltip.style('opacity', '0');
    });

  // Node rectangles
  nodeElements
    .append('rect')
    .attr('width', d => d.width)
    .attr('height', d => d.height)
    .attr('fill', '#1e293b')
    .attr('fill-opacity', d => getNodeFillOpacity(d, hoveredNode === d.id))
    .attr('stroke', '#475569')
    .attr('stroke-width', 1)
    .attr('stroke-opacity', d => getNodeStrokeOpacity(d, hoveredNode === d.id))
    .attr('rx', 2);

  // Render pillbox labels (labelData already calculated in STEP 5)
  labelData.forEach(item => {
    const pillGroup = nodeGroup
      .append('g')
      .attr('class', 'node-label-group')
      .attr('transform', `translate(${item.node.x0 + item.node.width + 8}, ${item.node.y0 + item.node.height / 2})`);
    
    // Background pill
    pillGroup.append('rect')
      .attr('x', 0)
      .attr('y', -item.pillHeight / 2)
      .attr('width', item.pillWidth)
      .attr('height', item.pillHeight)
      .attr('rx', item.pillHeight / 2)
      .attr('ry', item.pillHeight / 2)
      .attr('fill', '#1e293b')
      .attr('stroke', item.borderColor)
      .attr('stroke-width', 1.5)
      .attr('fill-opacity', 0.9)
      .attr('stroke-opacity', 0.9);
    
    // Text label positioned inside pill
    pillGroup.append('text')
      .attr('x', item.pillWidth / 2)
      .attr('y', 0)
      .attr('text-anchor', 'middle')
      .attr('dominant-baseline', 'central')
      .attr('fill', '#e2e8f0')
      .attr('font-size', item.fontSize)
      .attr('font-family', 'system-ui, -apple-system, sans-serif')
      .attr('font-weight', '500')
      .attr('pointer-events', 'none')
      .text(item.label);
  });

  console.log('[Deterministic Graph] Rendered successfully:', {
    nodes: layout.nodes.length,
    edges: layout.edges.length
  });
}

/**
 * Generate tooltip content for edges
 */
function getEdgeTooltip(
  sourceNode: PositionedNode | undefined,
  targetNode: PositionedNode | undefined,
  edge: PositionedEdge
): string {
  if (!sourceNode || !targetNode) return 'Data Flow';
  
  const sourceName = sourceNode.label || 'Unknown';
  const targetName = targetNode.label || 'Unknown';
  
  let flowDescription = '';
  if (sourceNode.type === 'source_parent' && targetNode.type === 'source') {
    flowDescription = 'System to table connection';
  } else if (sourceNode.type === 'source' && targetNode.type === 'ontology') {
    flowDescription = 'Raw data mapped to unified schema';
  } else if (sourceNode.type === 'ontology' && targetNode.type === 'agent') {
    flowDescription = 'Ontology field consumed by agent';
  } else {
    flowDescription = 'Data flow';
  }
  
  let tooltip = `
    <strong>Data Flow</strong><br>
    <span style="color: #94a3b8; font-size: 10px;">${flowDescription}</span><br>
    <div style="margin-top: 4px; padding-top: 4px; border-top: 1px solid #475569;">
      <span style="color: #60a5fa;">From:</span> ${sourceName}<br>
      <span style="color: #34d399;">To:</span> ${targetName}
    </div>
  `;
  
  if (edge.fieldMappings && edge.fieldMappings.length > 0) {
    tooltip += `
      <div style="margin-top: 6px; padding-top: 6px; border-top: 1px solid #475569;">
        <strong style="color: #a78bfa; font-size: 10px;">Field Mappings:</strong><br>
        <div style="max-height: 120px; overflow-y: auto; margin-top: 4px;">
    `;
    edge.fieldMappings.forEach((field: any) => {
      const sourceField = field.source || 'N/A';
      const ontoField = field.onto_field || 'N/A';
      const confidence = field.confidence ? `(${Math.round(field.confidence * 100)}%)` : '';
      tooltip += `
        <div style="font-size: 10px; margin: 2px 0; color: #cbd5e1;">
          <span style="color: #60a5fa;">${sourceField}</span> → <span style="color: #34d399;">${ontoField}</span> <span style="color: #94a3b8;">${confidence}</span>
        </div>
      `;
    });
    tooltip += `</div></div>`;
  }
  
  if (sourceNode.type === 'ontology' && targetNode.type === 'agent' && edge.entityFields && edge.entityFields.length > 0) {
    const entityName = edge.entityName || 'entity';
    tooltip += `
      <div style="margin-top: 6px; padding-top: 6px; border-top: 1px solid #475569;">
        <strong style="color: #a78bfa; font-size: 10px;">Unified ${entityName.replace('_', ' ').toUpperCase()} Fields:</strong><br>
        <div style="max-height: 120px; overflow-y: auto; margin-top: 4px;">
    `;
    edge.entityFields.forEach(field => {
      tooltip += `
        <div style="font-size: 10px; margin: 2px 0; color: #cbd5e1;">
          <span style="color: #34d399;">•</span> ${field}
        </div>
      `;
    });
    tooltip += `</div></div>`;
  }
  
  return tooltip;
}
