import { useEffect, useLayoutEffect, useRef, useState } from 'react';
import * as d3 from 'd3';
import { sankey as d3Sankey, sankeyLinkHorizontal } from 'd3-sankey';
import { API_CONFIG } from '../config/api';

interface SankeyNode {
  name: string;
  type: string;
  id: string;
  sourceSystem?: string;
  parentId?: string;
}

interface SankeyLink {
  source: number | string;
  target: number | string;
  value: number;
  edgeType?: 'hierarchy' | 'dataflow';
  sourceSystem?: string;
  targetType?: string;
  fieldMappings?: any[];
  edgeLabel?: string;
  entityFields?: string[];
  entityName?: string;
  tableFields?: string[];
}

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

interface LiveSankeyGraphProps {
  isActive?: boolean;
}

export default function LiveSankeyGraph({ isActive = true }: LiveSankeyGraphProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [state, setState] = useState<GraphState | null>(null);
  const [animatingEdges, setAnimatingEdges] = useState<Set<string>>(new Set());
  const [containerSize, setContainerSize] = useState({ width: 0, height: 0 });
  const [isRendering, setIsRendering] = useState(false);
  const rafRef = useRef<number | null>(null);

  useEffect(() => {
    // Only fetch if graph is active (visible)
    if (!isActive) return;

    const fetchState = async () => {
      try {
        const response = await fetch(API_CONFIG.buildDclUrl('/state'));
        const data = await response.json();
        setState(data);
      } catch (error) {
        console.error('Error fetching state:', error);
      }
    };

    fetchState();
    
    const handleRefetch = () => fetchState();
    window.addEventListener('dcl-state-changed', handleRefetch);
    
    return () => window.removeEventListener('dcl-state-changed', handleRefetch);
  }, [isActive]);

  useLayoutEffect(() => {
    if (!state || !svgRef.current || !containerRef.current) return;
    if (!state.nodes || state.nodes.length === 0) return;
    if (containerSize.width === 0 || containerSize.height === 0) return;

    setIsRendering(true);
    
    if (rafRef.current) {
      cancelAnimationFrame(rafRef.current);
    }

    rafRef.current = requestAnimationFrame(() => {
      renderSankey(state, svgRef.current!, containerRef.current!, animatingEdges);
      setIsRendering(false);
    });

    return () => {
      if (rafRef.current) {
        cancelAnimationFrame(rafRef.current);
      }
    };
  }, [state, animatingEdges, containerSize]);

  const triggerEdgeAnimation = (edgeKey: string) => {
    setAnimatingEdges(prev => new Set(prev).add(edgeKey));
    setTimeout(() => {
      setAnimatingEdges(prev => {
        const next = new Set(prev);
        next.delete(edgeKey);
        return next;
      });
    }, 2000);
  };

  useEffect(() => {
    const handleEvent = (event: CustomEvent) => {
      const { type, sourceId, targetId } = event.detail;
      if (type === 'new_source' || type === 'source_removed' || type === 'fault' || type === 'schema_drift') {
        triggerEdgeAnimation(`${sourceId}-${targetId}`);
      }
    };

    window.addEventListener('dcl-graph-event' as any, handleEvent);
    return () => window.removeEventListener('dcl-graph-event' as any, handleEvent);
  }, []);

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

  // Block rendering until ResizeObserver provides valid dimensions
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

interface NodeStyle {
  fill: string;
  stroke?: string;
  strokeWidth?: number;
  fillOpacity?: number;
}

function getNodeStyle(_node: any, _sankeyNodes: SankeyNode[]): NodeStyle {
  return {
    fill: '#1e293b',
    stroke: '#475569',
    strokeWidth: 1,
    fillOpacity: 1
  };
}

function renderSankey(
  state: GraphState,
  svgElement: SVGSVGElement,
  container: HTMLDivElement,
  animatingEdges: Set<string>
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

  const sankeyNodes: SankeyNode[] = [];
  const sankeyLinks: SankeyLink[] = [];
  const nodeIndexMap: Record<string, number> = {};
  let nodeIndex = 0;

  const layerMap: Record<string, number> = {
    'source_parent': 0,
    'source':        1,
    'ontology':      2,
    'agent':         3
  };

  state.nodes.forEach(n => {
    nodeIndexMap[n.id] = nodeIndex;
    const targetLayer = layerMap[n.type] !== undefined ? layerMap[n.type] : 1;
    sankeyNodes.push({
      name: n.label,
      type: n.type,
      id: n.id,
      sourceSystem: n.sourceSystem,
      parentId: n.parentId,
      layer: targetLayer  // Use 'layer' - d3-sankey respects this property natively
    } as any);
    nodeIndex++;
  });

  state.edges.forEach(e => {
    if (nodeIndexMap[e.source] !== undefined && nodeIndexMap[e.target] !== undefined) {
      const sourceNode = state.nodes.find(n => n.id === e.source);
      const targetNode = state.nodes.find(n => n.id === e.target);
      
      const edgeType = ((e as any).edgeType ?? (e as any).edge_type ?? 'dataflow') as 'hierarchy' | 'dataflow';

      sankeyLinks.push({
        source: e.source,
        target: e.target,
        value: 1,
        edgeType: edgeType,
        sourceSystem: sourceNode?.sourceSystem,
        targetType: targetNode?.type,
        fieldMappings: e.field_mappings || [],
        edgeLabel: e.label || '',
        entityFields: e.entity_fields || [],
        entityName: e.entity_name || '',
      });
    }
  });

  const containerRect = container.getBoundingClientRect();
  const validWidth = Math.max(containerRect.width, 320);
  // Allow mobile to shrink below 400px, only enforce minimum on desktop
  const isMobile = window.innerWidth < 768; // md breakpoint
  const validHeight = Math.max(containerRect.height, isMobile ? 200 : 400);
  
  const totalNodeCount = sankeyNodes.length;
  const calculatedHeight = Math.min(validHeight, 100 + (totalNodeCount * 40));

  // Set SVG dimensions (critical for rendering with h-auto class)
  svg
    .attr('width', validWidth)
    .attr('height', calculatedHeight)
    .attr('viewBox', `0 0 ${validWidth} ${calculatedHeight}`);

  // D3-sankey respects node.layer property natively - no custom nodeAlign needed!
  // We just need to set .layer on each node and d3-sankey will position them correctly
  const sankey = d3Sankey<SankeyNode, SankeyLink>()
    .nodeWidth(8)
    .nodePadding(18)
    .extent([
      [1, 20],
      [validWidth - 1, calculatedHeight - 20],
    ])
    .nodeId((d: any) => d.id);  // Tell d3-sankey to use id field for node identity

  const graph = sankey({
    nodes: sankeyNodes.map(d => Object.assign({}, d)),
    links: sankeyLinks.map(d => Object.assign({}, d)),
  });
  
  const { nodes, links } = graph;
  
  // Debug: Log sankey-computed positions
  console.log('[Sankey Debug] Sankey computed', nodes.length, 'nodes');
  const depthCounts: Record<number, number> = {};
  nodes.forEach((n: any) => {
    depthCounts[n.depth] = (depthCounts[n.depth] || 0) + 1;
  });
  console.log('[Sankey Debug] Nodes per depth level:', depthCounts);
  console.log('[Sankey Debug] Sample positions:', nodes.slice(0, 10).map((n: any) => ({ 
    id: n.id, 
    depth: n.depth, 
    x0: Math.round(n.x0), 
    x1: Math.round(n.x1) 
  })));
  
  const recalculateLinkPositions = () => {
    links.forEach((link: any) => {
      const source = link.source;
      const target = link.target;
      
      link.y0 = source.y0 + (source.y1 - source.y0) / 2;
      link.y1 = target.y0 + (target.y1 - target.y0) / 2;
    });
  };
  
  recalculateLinkPositions();

  const ontologyNodesInSankey = nodes.filter(n => {
    const nodeData = sankeyNodes.find(sn => sn.id === (n as any).id);  // Match by ID
    return nodeData && nodeData.type === 'ontology';
  });
  
  if (ontologyNodesInSankey.length > 1) {
    const totalOntologyHeight = ontologyNodesInSankey.reduce((sum, n) => sum + (n.y1! - n.y0!), 0);
    const availableSpace = calculatedHeight - totalOntologyHeight - 80;
    const spacing = availableSpace / (ontologyNodesInSankey.length - 1);
    
    let currentY = 40;
    ontologyNodesInSankey.forEach(node => {
      const nodeHeight = node.y1! - node.y0!;
      node.y0 = currentY;
      node.y1 = currentY + nodeHeight;
      currentY += nodeHeight + spacing;
    });
    
    recalculateLinkPositions();
  }

  const agentNodesInSankey = nodes.filter(n => {
    const nodeData = sankeyNodes.find(sn => sn.id === (n as any).id);  // Match by ID
    return nodeData && nodeData.type === 'agent';
  });
  
  if (agentNodesInSankey.length > 0) {
    const totalAgentHeight = agentNodesInSankey.reduce((sum, n) => sum + (n.y1! - n.y0!), 0);
    const agentSpacing = 40;
    const totalPadding = (agentNodesInSankey.length - 1) * agentSpacing;
    const centerY = (calculatedHeight - totalAgentHeight - totalPadding) / 2;
    
    let currentY = centerY;
    agentNodesInSankey.forEach(node => {
      const nodeHeight = node.y1! - node.y0!;
      node.y0 = currentY;
      node.y1 = currentY + nodeHeight;
      currentY += nodeHeight + agentSpacing;
    });
    
    recalculateLinkPositions();
  }

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

  const minX = Math.min(...nodes.map((n: any) => n.x0));
  const maxX = Math.max(...nodes.map((n: any) => n.x1));
  const minY = Math.min(...nodes.map((n: any) => n.y0));
  const maxY = Math.max(...nodes.map((n: any) => n.y1));
  
  const boundingWidth = maxX - minX;
  const boundingHeight = maxY - minY;
  
  // Pre-calculate maximum label width by measuring all labels that will be displayed
  // This prevents label clipping for long agent names like "Autonomous Optimization Agent"
  let maxMeasuredLabelWidth = 0;
  
  // Create a temporary SVG group for measurement (will be removed after measurement)
  const tempGroup = svg.append('g');
  
  nodes.forEach((d: any) => {
    const nodeData = sankeyNodes.find(n => n.id === d.id);  // Match by ID
    
    // Only measure labels for source_parent, ontology, and agent nodes (same as label creation logic)
    if (nodeData && (nodeData.type === 'source_parent' || nodeData.type === 'ontology' || nodeData.type === 'agent')) {
      // For ontology nodes, remove "(Unified)" or "(unified)" suffix (same as label creation logic)
      let label = d.name || 'Unknown';
      if (nodeData.type === 'ontology') {
        label = label.replace(/\s*\(unified\)\s*/i, '').trim();
      }
      
      // All labels use consistent sizing
      const isAgent = nodeData.type === 'agent';
      const padding = 4;
      const fontSize = 10;
      
      // Create a temporary text element to measure width
      const tempText = tempGroup
        .append('text')
        .attr('font-size', fontSize)
        .attr('font-family', 'system-ui, -apple-system, sans-serif')
        .text(label);
      
      const textWidth = (tempText.node() as SVGTextElement)?.getComputedTextLength() || 0;
      const pillWidth = textWidth + (padding * 2);
      
      // Track the maximum pill width
      maxMeasuredLabelWidth = Math.max(maxMeasuredLabelWidth, pillWidth);
    }
  });
  
  // Remove the temporary measurement group
  tempGroup.remove();
  
  // Use the measured maxLabelWidth to calculate viewBox dimensions
  // Minimal bottom padding for mobile (2px bottom vs 20px top/left)
  const labelOffset = 8;
  const viewBoxPaddingTop = 20;
  const viewBoxPaddingBottom = 2; // Minimal bottom padding for tight mobile layout
  const viewBoxPaddingLeft = 20;
  const extendedRightPadding = viewBoxPaddingTop + labelOffset + maxMeasuredLabelWidth;
  
  const viewBoxX = minX - viewBoxPaddingLeft;
  const viewBoxY = minY - viewBoxPaddingTop;
  const viewBoxWidth = boundingWidth + viewBoxPaddingLeft + extendedRightPadding;
  const viewBoxHeight = boundingHeight + viewBoxPaddingTop + viewBoxPaddingBottom;

  svg
    .attr('viewBox', `${viewBoxX} ${viewBoxY} ${viewBoxWidth} ${viewBoxHeight}`)
    .attr('preserveAspectRatio', 'xMidYMid meet')
    .attr('height', viewBoxHeight);

  // Add clipPath to prevent edges from bleeding outside container
  svg.append('defs')
    .append('clipPath')
    .attr('id', 'graph-clip')
    .append('rect')
    .attr('x', viewBoxX)
    .attr('y', viewBoxY)
    .attr('width', viewBoxWidth)
    .attr('height', viewBoxHeight);

  const mainGroup = svg
    .append('g')
    .attr('clip-path', 'url(#graph-clip)');

  mainGroup
    .append('g')
    .attr('fill', 'none')
    .selectAll('path')
    .data(links)
    .join('path')
    .attr('d', sankeyLinkHorizontal())
    .attr('stroke', (d: any, i: number) => {
      const originalLink = sankeyLinks[i];
      const sourceNode = state.nodes.find(n => nodeIndexMap[n.id] === originalLink.source);
      const targetNode = sankeyNodes.find(n => n.id === d.target.id);  // Match by ID
      
      // Color hierarchy edges from source_parent (layer 0) to source (layer 1) green
      if (originalLink?.edgeType === 'hierarchy' && sourceNode?.type === 'source_parent') {
        return '#22c55e';
      }
      
      // Other hierarchy edges remain gray
      if (originalLink?.edgeType === 'hierarchy') {
        return '#475569';
      }
      
      if (targetNode && targetNode.type === 'agent') {
        return '#9333ea';
      }
      if (originalLink && originalLink.sourceSystem) {
        return sourceColorMap[originalLink.sourceSystem]?.child || '#0bcad9';
      }
      return '#94a3b8';
    })
    .attr('stroke-width', (d: any) => Math.min(Math.max(0.5, d.width * 0.5), 20))
    .attr('stroke-opacity', (_d: any, i: number) => {
      const originalLink = sankeyLinks[i];
      
      if (originalLink?.edgeType === 'hierarchy') {
        return 0.35;
      }
      
      const sourceNode = state.nodes.find(n => nodeIndexMap[n.id] === originalLink.source);
      const targetNode = state.nodes.find(n => nodeIndexMap[n.id] === originalLink.target);
      const edgeKey = `${sourceNode?.id}-${targetNode?.id}`;
      
      if (animatingEdges.has(edgeKey)) return 0.9;
      
      if (sourceNode && (sourceNode.type === 'source' || sourceNode.type === 'source_parent')) {
        return 0.7;
      }
      
      return 0.4;
    })
    .attr('class', (_d: any, i: number) => {
      const originalLink = sankeyLinks[i];
      const sourceNode = state.nodes.find(n => nodeIndexMap[n.id] === originalLink.source);
      const targetNode = state.nodes.find(n => nodeIndexMap[n.id] === originalLink.target);
      const edgeKey = `${sourceNode?.id}-${targetNode?.id}`;
      return animatingEdges.has(edgeKey) ? 'animate-pulse' : '';
    })
    .style('cursor', 'pointer')
    .on('mouseenter', function(event: MouseEvent, d: any) {
      const linkIndex = links.indexOf(d);
      const originalLink = sankeyLinks[linkIndex];
      
      // Increase opacity on hover for all edge types
      if (originalLink?.edgeType === 'hierarchy') {
        d3.select(this).attr('stroke-opacity', 0.6);
      } else {
        d3.select(this).attr('stroke-opacity', 0.7);
      }
      
      const sourceNodeData = sankeyNodes.find(n => n.id === d.source.id);  // Match by ID
      const targetNodeData = sankeyNodes.find(n => n.id === d.target.id);  // Match by ID
      
      const tooltipContent = getEdgeTooltip(sourceNodeData, targetNodeData, originalLink);
      
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
        .style('font-family', 'system-ui, -apple-system, sans-serif');
      
      edgeTooltip
        .html(tooltipContent)
        .style('left', (event.pageX + 10) + 'px')
        .style('top', (event.pageY - 10) + 'px')
        .style('opacity', '1')
        .style('display', 'block');
    })
    .on('mousemove', function(event: MouseEvent) {
      d3.select('.sankey-edge-tooltip')
        .style('left', (event.pageX + 10) + 'px')
        .style('top', (event.pageY - 10) + 'px');
    })
    .on('mouseleave', function(_event: MouseEvent, d: any) {
      const linkIndex = links.indexOf(d);
      const originalLink = sankeyLinks[linkIndex];
      
      if (originalLink?.edgeType === 'hierarchy') {
        d3.select(this).attr('stroke-opacity', 0.35);
      } else {
        const sourceNode = state.nodes.find(n => nodeIndexMap[n.id] === originalLink.source);
        if (sourceNode && (sourceNode.type === 'source' || sourceNode.type === 'source_parent')) {
          d3.select(this).attr('stroke-opacity', 0.7);
        } else {
          d3.select(this).attr('stroke-opacity', 0.4);
        }
      }
      d3.select('.sankey-edge-tooltip').style('opacity', '0').style('display', 'none');
    });

  const nodeGroups = mainGroup.append('g').selectAll('g').data(nodes).join('g');

  const tooltip = d3.select('body')
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

  nodeGroups
    .append('rect')
    .attr('x', (d: any) => d.x0)
    .attr('y', (d: any) => d.y0)
    .attr('width', (d: any) => d.x1 - d.x0)
    .attr('height', (d: any) => Math.max(d.y1 - d.y0, 2))
    .attr('fill', (d: any) => {
      const nodeStyle = getNodeStyle(d, sankeyNodes);
      return nodeStyle.fill;
    })
    .attr('fill-opacity', (d: any) => {
      const nodeStyle = getNodeStyle(d, sankeyNodes);
      const nodeData = sankeyNodes.find(n => n.id === d.id);  // Match by ID
      
      if (nodeData?.type === 'ontology') {
        return 0.9;
      } else if (nodeData?.type === 'source') {
        const hasOutgoingDataflow = state.edges.some(e => 
          e.source === nodeData.id && ((e as any).edgeType ?? (e as any).edge_type) === 'dataflow'
        );
        return hasOutgoingDataflow ? 1 : 0.5;
      } else if (nodeData?.type === 'agent') {
        return 0;
      } else if (nodeData?.type === 'source_parent') {
        return 0.7;
      }
      
      return nodeStyle.fillOpacity || 0.7;
    })
    .attr('stroke', (d: any) => {
      const nodeStyle = getNodeStyle(d, sankeyNodes);
      return nodeStyle.stroke || '#475569';
    })
    .attr('stroke-width', (d: any) => {
      const nodeStyle = getNodeStyle(d, sankeyNodes);
      return nodeStyle.strokeWidth || 0;
    })
    .attr('stroke-opacity', (d: any) => {
      const nodeData = sankeyNodes.find(n => n.id === d.id);  // Match by ID
      
      if (nodeData?.type === 'source') {
        const hasOutgoingDataflow = state.edges.some(e => 
          e.source === nodeData.id && ((e as any).edgeType ?? (e as any).edge_type) === 'dataflow'
        );
        return hasOutgoingDataflow ? 1 : 0.6;
      } else if (nodeData?.type === 'agent' || nodeData?.type === 'source_parent') {
        return 1;
      }
      
      return 0;
    })
    .style('cursor', 'pointer')
    .on('mouseenter', function(event: MouseEvent, d: any) {
      const nodeData = sankeyNodes.find(n => n.id === d.id);  // Match by ID
      if (!nodeData) return;
      
      if (nodeData.type === 'ontology') {
        d3.select(this).attr('fill-opacity', 1);
      } else if (nodeData.type === 'source' || nodeData.type === 'agent') {
        d3.select(this).attr('stroke-opacity', 1);
      }
      
      let tooltipContent = `<strong>${d.name}</strong><br/>`;
      tooltipContent += `Type: ${nodeData.type}`;
      
      if (nodeData.type === 'source' || nodeData.type === 'source_parent') {
        tooltipContent += `<br/>System: ${nodeData.sourceSystem || 'Unknown'}`;
      }
      
      tooltip
        .html(tooltipContent)
        .style('opacity', '1')
        .style('left', (event.pageX + 10) + 'px')
        .style('top', (event.pageY - 10) + 'px');
    })
    .on('mousemove', function(event: MouseEvent) {
      tooltip
        .style('left', (event.pageX + 10) + 'px')
        .style('top', (event.pageY - 10) + 'px');
    })
    .on('mouseleave', function(event: MouseEvent, d: any) {
      const nodeData = sankeyNodes.find(n => n.id === d.id);  // Match by ID
      
      if (nodeData?.type === 'ontology') {
        d3.select(this).attr('fill-opacity', 0.9);
      } else if (nodeData?.type === 'source') {
        const hasOutgoingDataflow = state.edges.some(e => 
          e.source === nodeData.id && ((e as any).edgeType ?? (e as any).edge_type) === 'dataflow'
        );
        d3.select(this).attr('fill-opacity', hasOutgoingDataflow ? 1 : 0.5);
        d3.select(this).attr('stroke-opacity', hasOutgoingDataflow ? 1 : 0.6);
      } else if (nodeData?.type === 'agent') {
        d3.select(this).attr('fill-opacity', 0).attr('stroke-opacity', 1);
      } else if (nodeData?.type === 'source_parent') {
        d3.select(this).attr('fill-opacity', 0.7).attr('stroke-opacity', 1);
      } else {
        d3.select(this).attr('fill-opacity', 0.7);
      }
      
      tooltip.style('opacity', '0');
    })
    .on('click', async function(_event: MouseEvent, d: any) {
      const nodeData = sankeyNodes.find(n => n.id === d.id);  // Match by ID
      if (!nodeData) return;
      
      try {
        const response = await fetch(API_CONFIG.buildDclUrl(`/preview?node=${nodeData.id}`));
        const data = await response.json();
        console.log('Preview data for', nodeData.id, ':', data);
        
        window.dispatchEvent(new CustomEvent('sankey-node-click', { 
          detail: { node: nodeData, preview: data } 
        }));
      } catch (error) {
        console.error('Error fetching preview:', error);
      }
    });

  // Add pillbox labels for data source, ontology, and agent nodes
  // First pass: collect all label data
  const labelData: Array<{
    element: any;
    nodeData: any;
    d: any;
    label: string;
    fontSize: number;
    pillHeight: number;
    pillWidth: number;
    padding: number;
    xPos: number;
    yPos: number;
    borderColor: string;
  }> = [];
  
  nodeGroups.each(function (this: any, d: any) {
    const nodeData = sankeyNodes.find(n => n.id === d.id);  // Match by ID
    
    // Add labels to source_parent nodes (data sources), ontology nodes, and agent nodes
    if (nodeData && (nodeData.type === 'source_parent' || nodeData.type === 'ontology' || nodeData.type === 'agent')) {
      // For ontology nodes, remove "(Unified)" or "(unified)" suffix
      let label = d.name || 'Unknown';
      if (nodeData.type === 'ontology') {
        label = label.replace(/\s*\(unified\)\s*/i, '').trim();
      }
      
      // All labels use consistent sizing
      const isAgent = nodeData.type === 'agent';
      const padding = 4;
      const fontSize = 10;
      const pillHeight = 16;
      
      // Create a temporary text element to measure width
      const tempText = d3.select(this)
        .append('text')
        .attr('font-size', fontSize)
        .attr('font-family', 'system-ui, -apple-system, sans-serif')
        .text(label);
      
      const textWidth = (tempText.node() as SVGTextElement)?.getComputedTextLength() || 0;
      tempText.remove();
      
      const pillWidth = textWidth + (padding * 2);
      
      // Calculate position (offset to the right of the node)
      const xPos = d.x1 + labelOffset;
      const yPos = (d.y0 + d.y1) / 2;
      
      // Determine border color based on node type
      let borderColor = '#475569'; // default slate gray
      if (nodeData.type === 'source_parent') {
        borderColor = '#22c55e'; // green for data source labels
      } else if (nodeData.type === 'ontology') {
        borderColor = '#60a5fa'; // blue for ontology/entity labels
      } else if (nodeData.type === 'agent') {
        borderColor = '#9333ea'; // purple for agent labels
      }
      
      labelData.push({
        element: this,
        nodeData,
        d,
        label,
        fontSize,
        pillHeight,
        pillWidth,
        padding,
        xPos,
        yPos,
        borderColor
      });
    }
  });
  
  // Second pass: adjust positions to avoid overlaps and render labels
  // Group labels by X position (layer) for collision detection
  const layerGroups = new Map<number, typeof labelData>();
  labelData.forEach(item => {
    const layerKey = Math.round(item.xPos);
    if (!layerGroups.has(layerKey)) {
      layerGroups.set(layerKey, []);
    }
    layerGroups.get(layerKey)!.push(item);
  });
  
  // Adjust Y positions within each layer to prevent overlaps
  layerGroups.forEach(layerItems => {
    // Sort by Y position
    layerItems.sort((a, b) => a.yPos - b.yPos);
    
    // Adjust positions if overlapping (labels extend vertically in horizontal layout)
    const minGap = 4; // minimum gap between labels
    for (let i = 1; i < layerItems.length; i++) {
      const prev = layerItems[i - 1];
      const curr = layerItems[i];
      
      // Labels extend vertically by pillHeight
      const prevBottom = prev.yPos + (prev.pillHeight / 2);
      const currTop = curr.yPos - (curr.pillHeight / 2);
      
      if (prevBottom + minGap > currTop) {
        // Overlap detected, push current label down
        const overlap = (prevBottom + minGap) - currTop;
        curr.yPos += overlap;
      }
    }
  });
  
  // Third pass: render all labels with adjusted positions
  labelData.forEach(item => {
    // Create group for pillbox anchored to node edge (horizontal layout)
    const pillGroup = d3.select(item.element)
      .append('g')
      .attr('class', 'node-label-group')
      .attr('transform', `translate(${item.d.x1 + 8}, ${item.yPos})`);
    
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

  function getEdgeTooltip(sourceNodeData: SankeyNode | undefined, targetNodeData: SankeyNode | undefined, linkData: SankeyLink): string {
    if (!sourceNodeData || !targetNodeData) return 'Data Flow';
    
    const sourceName = sourceNodeData.name || 'Unknown';
    const targetName = targetNodeData.name || 'Unknown';
    
    let flowDescription = '';
    if (sourceNodeData.type === 'source_parent' && targetNodeData.type === 'source') {
      flowDescription = 'System to table connection';
    } else if (sourceNodeData.type === 'source' && targetNodeData.type === 'ontology') {
      flowDescription = 'Raw data mapped to unified schema';
    } else if (sourceNodeData.type === 'ontology' && targetNodeData.type === 'agent') {
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
    
    if (sourceNodeData.type === 'source_parent' && targetNodeData.type === 'source' && linkData?.tableFields?.length) {
      tooltip += `
        <div style="margin-top: 6px; padding-top: 6px; border-top: 1px solid #475569;">
          <strong style="color: #a78bfa; font-size: 10px;">Table Fields:</strong><br>
          <div style="max-height: 120px; overflow-y: auto; margin-top: 4px;">
      `;
      linkData.tableFields.forEach(field => {
        tooltip += `
          <div style="font-size: 10px; margin: 2px 0; color: #cbd5e1;">
            <span style="color: #60a5fa;">•</span> ${field}
          </div>
        `;
      });
      tooltip += `</div></div>`;
    }
    
    if (linkData?.fieldMappings?.length) {
      tooltip += `
        <div style="margin-top: 6px; padding-top: 6px; border-top: 1px solid #475569;">
          <strong style="color: #a78bfa; font-size: 10px;">Field Mappings:</strong><br>
          <div style="max-height: 120px; overflow-y: auto; margin-top: 4px;">
      `;
      linkData.fieldMappings.forEach((field: any) => {
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
    
    if (sourceNodeData.type === 'ontology' && targetNodeData.type === 'agent' && linkData?.entityFields?.length) {
      const entityName = linkData.entityName || 'entity';
      tooltip += `
        <div style="margin-top: 6px; padding-top: 6px; border-top: 1px solid #475569;">
          <strong style="color: #a78bfa; font-size: 10px;">Unified ${entityName.replace('_', ' ').toUpperCase()} Fields:</strong><br>
          <div style="max-height: 120px; overflow-y: auto; margin-top: 4px;">
      `;
      linkData.entityFields.forEach(field => {
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
}
