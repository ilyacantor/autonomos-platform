/**
 * Deterministic Graph Layout Engine
 * 
 * Provides guaranteed 4-column layout (L0 → L1 → L2 → L3) without fighting
 * library algorithms. This is a fundamental solution that replaces d3-sankey's
 * breadth-first relaxation with explicit column positioning.
 * 
 * Design Principles:
 * - Fixed column X positions (no auto-layout interference)
 * - Deterministic Y spacing within columns
 * - Preserves all node/edge data for rendering
 * - No dependencies on d3-sankey
 */

export interface GraphNode {
  id: string;
  label: string;
  type: 'source_parent' | 'source' | 'ontology' | 'agent';
  sourceSystem?: string;
  parentId?: string;
  fields?: string[];
  layer: number; // Explicit layer assignment (0, 1, 2, or 3)
}

export interface GraphEdge {
  source: string; // Node ID
  target: string; // Node ID
  value: number;
  edgeType?: 'hierarchy' | 'dataflow';
  sourceSystem?: string;
  targetType?: string;
  fieldMappings?: any[];
  edgeLabel?: string;
  entityFields?: string[];
  entityName?: string;
}

export interface PositionedNode extends GraphNode {
  x0: number; // Left edge X coordinate
  x1: number; // Right edge X coordinate
  y0: number; // Top edge Y coordinate
  y1: number; // Bottom edge Y coordinate
  width: number;
  height: number;
}

export interface PositionedEdge extends GraphEdge {
  sourceNode: PositionedNode;
  targetNode: PositionedNode;
  // Path points for curved rendering
  path: string;
}

export interface LayoutConfig {
  width: number;
  height: number;
  nodeWidth: number;
  nodePadding: number;
  columnPadding: number; // Horizontal space between columns
}

export interface LayoutResult {
  nodes: PositionedNode[];
  edges: PositionedEdge[];
  bounds: {
    minX: number;
    maxX: number;
    minY: number;
    maxY: number;
  };
}

/**
 * CORE LAYOUT ALGORITHM
 * 
 * 1. Group nodes by layer (0, 1, 2, 3)
 * 2. Calculate fixed X positions for each column
 * 3. Calculate Y positions using vertical spacing within columns
 * 4. Generate curved edge paths between positioned nodes
 */
export function calculateDeterministicLayout(
  nodes: GraphNode[],
  edges: GraphEdge[],
  config: LayoutConfig
): LayoutResult {
  // Step 1: Group nodes by layer
  const nodesByLayer: Map<number, GraphNode[]> = new Map();
  for (let i = 0; i <= 3; i++) {
    nodesByLayer.set(i, []);
  }

  nodes.forEach(node => {
    const layer = node.layer ?? 1; // Default to layer 1 if not specified
    if (!nodesByLayer.has(layer)) {
      nodesByLayer.set(layer, []);
    }
    nodesByLayer.get(layer)!.push(node);
  });

  // Step 2: Calculate fixed X positions for each column
  const totalColumns = 4;
  const availableWidth = config.width - (2 * config.columnPadding);
  const columnSpacing = availableWidth / (totalColumns - 1);

  const columnXPositions = new Map<number, number>();
  for (let i = 0; i < totalColumns; i++) {
    columnXPositions.set(i, config.columnPadding + (i * columnSpacing));
  }

  // Step 3: Calculate Y positions using vertical spacing within columns
  const positionedNodes: PositionedNode[] = [];
  const nodeMap = new Map<string, PositionedNode>();

  nodesByLayer.forEach((layerNodes, layer) => {
    if (layerNodes.length === 0) return;

    const columnX = columnXPositions.get(layer) ?? config.columnPadding;
    
    // Calculate vertical spacing for this column
    const totalNodesInColumn = layerNodes.length;
    const totalNodeHeight = totalNodesInColumn * config.nodeWidth; // Assuming square nodes initially
    const totalPadding = Math.max(0, totalNodesInColumn - 1) * config.nodePadding;
    const totalHeight = totalNodeHeight + totalPadding;

    // Center the column vertically
    let currentY = (config.height - totalHeight) / 2;

    // Position each node in this column
    layerNodes.forEach(node => {
      const nodeHeight = config.nodeWidth; // Can be adjusted based on node type
      
      const positionedNode: PositionedNode = {
        ...node,
        x0: columnX,
        x1: columnX + config.nodeWidth,
        y0: currentY,
        y1: currentY + nodeHeight,
        width: config.nodeWidth,
        height: nodeHeight
      };

      positionedNodes.push(positionedNode);
      nodeMap.set(node.id, positionedNode);

      currentY += nodeHeight + config.nodePadding;
    });
  });

  // Step 4: Generate curved edge paths
  const positionedEdges: PositionedEdge[] = edges
    .map(edge => {
      const sourceNode = nodeMap.get(edge.source);
      const targetNode = nodeMap.get(edge.target);

      if (!sourceNode || !targetNode) {
        console.warn(`[Layout] Edge references missing node: ${edge.source} → ${edge.target}`);
        return null;
      }

      // Generate Bézier curve path
      const path = generateCurvedPath(sourceNode, targetNode);

      return {
        ...edge,
        sourceNode,
        targetNode,
        path
      };
    })
    .filter((edge): edge is PositionedEdge => edge !== null);

  // Calculate bounds
  const bounds = {
    minX: Math.min(...positionedNodes.map(n => n.x0)),
    maxX: Math.max(...positionedNodes.map(n => n.x1)),
    minY: Math.min(...positionedNodes.map(n => n.y0)),
    maxY: Math.max(...positionedNodes.map(n => n.y1))
  };

  return {
    nodes: positionedNodes,
    edges: positionedEdges,
    bounds
  };
}

/**
 * Generate a smooth Bézier curve path between two nodes
 * 
 * Uses horizontal control points for Sankey-style curves
 */
function generateCurvedPath(source: PositionedNode, target: PositionedNode): string {
  // Start point: right edge of source node, vertically centered
  const x0 = source.x1;
  const y0 = source.y0 + (source.height / 2);

  // End point: left edge of target node, vertically centered
  const x1 = target.x0;
  const y1 = target.y0 + (target.height / 2);

  // Control points for horizontal Sankey-style curve
  const midX = (x0 + x1) / 2;
  
  // Cubic Bézier curve: M start C cp1x,cp1y cp2x,cp2y end
  return `M ${x0},${y0} C ${midX},${y0} ${midX},${y1} ${x1},${y1}`;
}

/**
 * Validate that nodes have proper layer assignments
 */
export function validateLayerAssignments(nodes: GraphNode[]): {
  valid: boolean;
  errors: string[];
  distribution: Record<number, number>;
} {
  const errors: string[] = [];
  const distribution: Record<number, number> = {};

  nodes.forEach(node => {
    const layer = node.layer;
    
    if (layer === undefined) {
      errors.push(`Node ${node.id} missing layer assignment`);
    } else if (layer < 0 || layer > 3) {
      errors.push(`Node ${node.id} has invalid layer ${layer} (must be 0-3)`);
    }

    distribution[layer ?? -1] = (distribution[layer ?? -1] ?? 0) + 1;
  });

  return {
    valid: errors.length === 0,
    errors,
    distribution
  };
}
