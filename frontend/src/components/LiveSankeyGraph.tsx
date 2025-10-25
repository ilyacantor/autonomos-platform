import { useEffect, useRef, useState } from 'react';
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
  source: number;
  target: number;
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
  graph: {
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
  };
  dev_mode: boolean;
}

export default function LiveSankeyGraph() {
  const svgRef = useRef<SVGSVGElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [state, setState] = useState<GraphState | null>(null);
  const [animatingEdges, setAnimatingEdges] = useState<Set<string>>(new Set());
  const [dynamicHeight, setDynamicHeight] = useState<number>(600);
  const [containerSize, setContainerSize] = useState({ width: 0, height: 0 });

  useEffect(() => {
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
  }, []);

  useEffect(() => {
    if (!state || !svgRef.current || !containerRef.current) return;
    if (!state.graph || !state.graph.nodes || state.graph.nodes.length === 0) return;

    renderSankey(state, svgRef.current, containerRef.current, animatingEdges, setDynamicHeight);
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

    let debounceTimer: NodeJS.Timeout;
    
    const resizeObserver = new ResizeObserver((entries) => {
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(() => {
        for (const entry of entries) {
          const { width, height } = entry.contentRect;
          setContainerSize({ width, height });
        }
      }, 150);
    });

    resizeObserver.observe(containerRef.current);

    return () => {
      clearTimeout(debounceTimer);
      resizeObserver.disconnect();
    };
  }, []);

  return (
    <div ref={containerRef} className="rounded-xl bg-gray-800/40 border border-gray-700 shadow-sm ring-1 ring-cyan-500/10 p-3 h-full">
      <div className="relative w-full h-full mx-auto" style={{ minHeight: `${dynamicHeight}px` }}>
        <svg
          ref={svgRef}
          className="w-full h-full"
          style={{ minHeight: `${dynamicHeight}px`, overflow: 'visible' }}
        />
      </div>
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
  // Consistent clean boxes for all nodes on all layers
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
  animatingEdges: Set<string>,
  setDynamicHeight?: (height: number) => void
) {
  const svg = d3.select(svgElement);
  svg.selectAll('*').remove();

  if (!state.graph || !state.graph.nodes || state.graph.nodes.length === 0) {
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

  state.graph.nodes.forEach(n => {
    nodeIndexMap[n.id] = nodeIndex;
    sankeyNodes.push({
      name: n.label,
      type: n.type,
      id: n.id,
      sourceSystem: n.sourceSystem,
      parentId: n.parentId
    });
    nodeIndex++;
  });

  state.graph.edges.forEach(e => {
    if (nodeIndexMap[e.source] !== undefined && nodeIndexMap[e.target] !== undefined) {
      const sourceNode = state.graph.nodes.find(n => n.id === e.source);
      const targetNode = state.graph.nodes.find(n => n.id === e.target);
      
      const edgeType = ((e as any).edgeType ?? (e as any).edge_type ?? 'dataflow') as 'hierarchy' | 'dataflow';

      sankeyLinks.push({
        source: nodeIndexMap[e.source],
        target: nodeIndexMap[e.target],
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
  
  const { width } = (svg.node() as SVGSVGElement).getBoundingClientRect();
  const validWidth = width > 0 ? Math.max(width, 320) + 400 : 1200;

  const layerMap: Record<string, number> = {
    'source_parent': 0,
    'source':        1,
    'ontology':      2,
    'agent':         3
  };
  
  const layerCounts: Record<number, number> = { 0: 0, 1: 0, 2: 0, 3: 0 };
  sankeyNodes.forEach(node => {
    const layer = layerMap[node.type] ?? 1;
    layerCounts[layer] = (layerCounts[layer] || 0) + 1;
  });
  
  const totalNodeCount = sankeyNodes.length;
  const calculatedHeight = Math.min(800, 100 + (totalNodeCount * 40));
  
  if (setDynamicHeight) {
    setDynamicHeight(calculatedHeight);
  }

  const validHeight = calculatedHeight + 200;

  const sankey = d3Sankey<SankeyNode, SankeyLink>()
    .nodeWidth(8)
    .nodePadding(18)
    .extent([
      [1, 40],
      [validWidth - 1, validHeight - 40],
    ]);

  const graph = sankey({
    nodes: sankeyNodes.map(d => Object.assign({}, d)),
    links: sankeyLinks.map(d => Object.assign({}, d)),
  });
  
  const { nodes, links } = graph;
  
  const leftPadding = 20;
  const rightPadding = 20;
  const layerWidth = (validWidth - leftPadding - rightPadding) / 3;
  const layerXPositions = [
    leftPadding,
    leftPadding + layerWidth,
    leftPadding + layerWidth * 2,
    validWidth - rightPadding - 8
  ];
  
  nodes.forEach(node => {
    const nodeData = sankeyNodes.find(n => n.name === node.name);
    if (nodeData && nodeData.type && layerMap[nodeData.type] !== undefined) {
      const layer = layerMap[nodeData.type];
      node.depth = layer;
      node.x0 = layerXPositions[layer];
      node.x1 = layerXPositions[layer] + 8;
    } else {
      node.depth = 1;
      node.x0 = layerXPositions[1];
      node.x1 = layerXPositions[1] + 8;
    }
  });
  
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
    const nodeData = sankeyNodes.find(sn => sn.name === n.name);
    return nodeData && nodeData.type === 'ontology';
  });
  
  if (ontologyNodesInSankey.length > 1) {
    const totalOntologyHeight = ontologyNodesInSankey.reduce((sum, n) => sum + (n.y1! - n.y0!), 0);
    const availableSpace = validHeight - totalOntologyHeight - 80;
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
    const nodeData = sankeyNodes.find(sn => sn.name === n.name);
    return nodeData && nodeData.type === 'agent';
  });
  
  if (agentNodesInSankey.length > 0) {
    const totalAgentHeight = agentNodesInSankey.reduce((sum, n) => sum + (n.y1! - n.y0!), 0);
    const agentSpacing = 40;
    const totalPadding = (agentNodesInSankey.length - 1) * agentSpacing;
    const centerY = (validHeight - totalAgentHeight - totalPadding) / 2;
    
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

  const minX = Math.min(...nodes.map((n: any) => n.x0)) - 50;
  const maxX = Math.max(...nodes.map((n: any) => n.x1)) + 50;
  const minY = Math.min(...nodes.map((n: any) => n.y0)) - 50;
  const maxY = Math.max(...nodes.map((n: any) => n.y1)) + 50;
  
  const boundingWidth = maxX - minX;
  const boundingHeight = maxY - minY;
  
  const viewBoxPadding = 100;
  const viewBoxX = minX - viewBoxPadding;
  const viewBoxY = minY - viewBoxPadding;
  const viewBoxWidth = boundingWidth + (2 * viewBoxPadding);
  const viewBoxHeight = boundingHeight + (2 * viewBoxPadding);

  svg
    .attr('width', '100%')
    .attr('height', calculatedHeight + 'px')
    .attr('viewBox', `${viewBoxX} ${viewBoxY} ${viewBoxWidth} ${viewBoxHeight}`)
    .attr('preserveAspectRatio', 'xMidYMid meet');

  const mainGroup = svg
    .append('g')
    .attr('transform', `translate(${validWidth / 2}, ${validHeight / 2}) rotate(90) translate(${-validWidth / 2}, ${-validHeight / 2})`);

  mainGroup
    .append('g')
    .attr('fill', 'none')
    .selectAll('path')
    .data(links)
    .join('path')
    .attr('d', sankeyLinkHorizontal())
    .attr('stroke', (d: any, i: number) => {
      const originalLink = sankeyLinks[i];
      
      if (originalLink?.edgeType === 'hierarchy') {
        return '#475569';
      }
      
      const targetNode = sankeyNodes.find(n => n.name === d.target.name);
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
      
      const sourceNode = state.graph.nodes.find(n => nodeIndexMap[n.id] === originalLink.source);
      const targetNode = state.graph.nodes.find(n => nodeIndexMap[n.id] === originalLink.target);
      const edgeKey = `${sourceNode?.id}-${targetNode?.id}`;
      
      if (animatingEdges.has(edgeKey)) return 0.9;
      
      // Increase opacity for edges from data sources to layer 1
      if (sourceNode && (sourceNode.type === 'source' || sourceNode.type === 'source_parent')) {
        return 0.7;
      }
      
      return 0.4;
    })
    .attr('class', (_d: any, i: number) => {
      const originalLink = sankeyLinks[i];
      const sourceNode = state.graph.nodes.find(n => nodeIndexMap[n.id] === originalLink.source);
      const targetNode = state.graph.nodes.find(n => nodeIndexMap[n.id] === originalLink.target);
      const edgeKey = `${sourceNode?.id}-${targetNode?.id}`;
      return animatingEdges.has(edgeKey) ? 'animate-pulse' : '';
    })
    .style('cursor', (d: any, i: number) => {
      const originalLink = sankeyLinks[i];
      return originalLink?.edgeType === 'hierarchy' ? 'default' : 'pointer';
    })
    .on('mouseenter', function(event: MouseEvent, d: any) {
      const linkIndex = links.indexOf(d);
      const originalLink = sankeyLinks[linkIndex];
      
      if (originalLink?.edgeType === 'hierarchy') return;
      
      d3.select(this).attr('stroke-opacity', 0.7);
      
      const sourceNodeData = sankeyNodes.find(n => n.name === d.source.name);
      const targetNodeData = sankeyNodes.find(n => n.name === d.target.name);
      
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
        .style('z-index', 10000)
        .style('box-shadow', '0 4px 6px rgba(0, 0, 0, 0.3)')
        .style('max-width', '400px')
        .style('font-family', 'system-ui, -apple-system, sans-serif');
      
      edgeTooltip
        .html(tooltipContent)
        .style('left', (event.pageX + 10) + 'px')
        .style('top', (event.pageY - 10) + 'px')
        .style('opacity', 1);
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
        // Restore higher opacity for edges from data sources
        const sourceNode = state.graph.nodes.find(n => nodeIndexMap[n.id] === originalLink.source);
        if (sourceNode && (sourceNode.type === 'source' || sourceNode.type === 'source_parent')) {
          d3.select(this).attr('stroke-opacity', 0.7);
        } else {
          d3.select(this).attr('stroke-opacity', 0.4);
        }
      }
      d3.select('.sankey-edge-tooltip').style('opacity', 0);
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
    .style('opacity', 0)
    .style('z-index', 1000)
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
      const nodeData = sankeyNodes.find(n => n.name === d.name);
      
      if (nodeData?.type === 'source') {
        const hasOutgoingDataflow = state.graph.edges.some(e => 
          e.source === nodeData.id && ((e as any).edgeType ?? (e as any).edge_type) === 'dataflow'
        );
        return hasOutgoingDataflow ? (nodeStyle.fillOpacity || 1) : 0.5;
      }
      
      return nodeStyle.fillOpacity || 1;
    })
    .attr('stroke', (d: any) => {
      const nodeStyle = getNodeStyle(d, sankeyNodes);
      return nodeStyle.stroke || 'none';
    })
    .attr('stroke-width', (d: any) => {
      const nodeStyle = getNodeStyle(d, sankeyNodes);
      return nodeStyle.strokeWidth || 0;
    })
    .attr('stroke-opacity', (d: any) => {
      const nodeData = sankeyNodes.find(n => n.name === d.name);
      
      if (nodeData?.type === 'source') {
        const hasOutgoingDataflow = state.graph.edges.some(e => 
          e.source === nodeData.id && ((e as any).edgeType ?? (e as any).edge_type) === 'dataflow'
        );
        return hasOutgoingDataflow ? 1 : 0.6;
      }
      
      return 1;
    })
    .attr('stroke-dasharray', (d: any) => {
      const nodeData = sankeyNodes.find(n => n.name === d.name);
      
      if (nodeData?.type === 'source') {
        const hasOutgoingDataflow = state.graph.edges.some(e => 
          e.source === nodeData.id && ((e as any).edgeType ?? (e as any).edge_type) === 'dataflow'
        );
        return hasOutgoingDataflow ? 'none' : '4,4';
      }
      
      return 'none';
    })
    .style('cursor', 'pointer')
    .on('mouseenter', function(event: MouseEvent, d: any) {
      const nodeData = sankeyNodes.find(n => n.name === d.name);
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
        .style('opacity', 1)
        .style('left', (event.pageX + 10) + 'px')
        .style('top', (event.pageY - 10) + 'px');
    })
    .on('mousemove', function(event: MouseEvent) {
      tooltip
        .style('left', (event.pageX + 10) + 'px')
        .style('top', (event.pageY - 10) + 'px');
    })
    .on('mouseleave', function(event: MouseEvent, d: any) {
      const nodeData = sankeyNodes.find(n => n.name === d.name);
      
      if (nodeData?.type === 'ontology') {
        d3.select(this).attr('fill-opacity', 0.9);
      } else if (nodeData?.type === 'source') {
        const hasOutgoingDataflow = state.graph.edges.some(e => 
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
      
      tooltip.style('opacity', 0);
    })
    .on('click', async function(_event: MouseEvent, d: any) {
      const nodeData = sankeyNodes.find(n => n.name === d.name);
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

  const getLabelStyle = (nodeName: string, nodeType: string, nodeId?: string) => {
    const nameLower = nodeName.toLowerCase();
    
    if (nodeType === 'ontology') {
      if (nameLower.includes('customer') || nameLower.includes('account')) {
        return { bg: '#06b6d4', icon: 'user', text: '#ffffff', themed: true, outlined: false };
      } else if (nameLower.includes('transaction') || nameLower.includes('payment') || nameLower.includes('invoice')) {
        return { bg: '#f97316', icon: 'zap', text: '#ffffff', themed: true, outlined: false };
      } else if (nameLower.includes('opportunity') || nameLower.includes('deal')) {
        return { bg: '#8b5cf6', icon: 'target', text: '#ffffff', themed: true, outlined: false };
      } else if (nameLower.includes('product') || nameLower.includes('item')) {
        return { bg: '#10b981', icon: 'package', text: '#ffffff', themed: true, outlined: false };
      } else if (nameLower.includes('resource') || nameLower.includes('cloud')) {
        return { bg: '#3b82f6', icon: 'cloud', text: '#ffffff', themed: true, outlined: false };
      } else if (nameLower.includes('spend') || nameLower.includes('cost')) {
        return { bg: '#ef4444', icon: 'dollar', text: '#ffffff', themed: true, outlined: false };
      }
      return { bg: '#14b8a6', icon: 'database', text: '#ffffff', themed: true, outlined: false };
    }
    
    if (nodeType === 'agent') {
      return { bg: 'transparent', icon: 'bot', text: '#e2e8f0', themed: true, outlined: true, borderColor: '#a855f7' };
    }
    
    if (nodeType === 'source') {
      return { bg: 'rgba(15, 23, 42, 0.9)', icon: null, text: '#e2e8f0', themed: false, outlined: false };
    }
    
    return { bg: 'rgba(15, 23, 42, 0.9)', icon: null, text: '#e2e8f0', themed: false, outlined: false };
  };
  
  const getIconPath = (iconName: string) => {
    const icons: Record<string, string> = {
      user: 'M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2M12 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8z',
      users: 'M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM22 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75',
      zap: 'M13 2L3 14h9l-1 8 10-12h-9l1-8z',
      target: 'M22 12A10 10 0 1 1 12 2a10 10 0 0 1 10 10zM12 18a6 6 0 1 0 0-12 6 6 0 0 0 0 12zM12 14a2 2 0 1 0 0-4 2 2 0 0 0 0 4z',
      package: 'M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16zM3.3 7l8.7 5 8.7-5M12 22V12',
      cloud: 'M18 10h-1.26A8 8 0 1 0 9 20h9a5 5 0 0 0 0-10z',
      dollar: 'M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6',
      database: 'M21 12c0 1.66-4 3-9 3s-9-1.34-9-3M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5M21 5c0 1.66-4 3-9 3S3 6.66 3 5m18 0c0-1.66-4-3-9-3S3 3.34 3 5',
      databaseIcon: 'M4 6c0-1.1 1.34-2 3-2h10c1.66 0 3 .9 3 2s-1.34 2-3 2H7c-1.66 0-3-.9-3-2zM20 12c0 1.1-1.34 2-3 2H7c-1.66 0-3-.9-3-2s1.34-2 3-2h10c1.66 0 3 .9 3 2zM7 18c-1.66 0-3-.9-3-2s1.34-2 3-2h10c1.66 0 3 .9 3 2s-1.34 2-3 2H7z',
      warehouse: 'M3 21h18M3 7l9-4 9 4M6 21V10M18 21V10M6 10h12M6 14h12M6 18h12',
      settings: 'M12 20a8 8 0 1 0 0-16 8 8 0 0 0 0 16zM12 14a2 2 0 1 0 0-4 2 2 0 0 0 0 4zM12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41',
      bot: 'M12 8V4M8 8a4 4 0 0 1 8 0v4a4 4 0 0 1-8 0V8zM12 18v2M8 18h8M6 15a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v2a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2v-2z',
      server: 'M6 2h12a2 2 0 0 1 2 2v4a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2zM6 10h12a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2v-8a2 2 0 0 1 2-2zM8 6h.01M8 14h.01',
      table: 'M3 3h18v18H3zM3 9h18M3 15h18M9 3v18'
    };
    return icons[iconName] || icons.database;
  };

  // SUPPRESS ALL LABELS AND ICONS - Will re-enable for layers, agents, and sources in future iterations
  nodeGroups.each(function (this: any, _d: any) {
    // All label rendering suppressed
    return;
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
