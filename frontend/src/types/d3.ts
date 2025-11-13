/**
 * D3 and D3-Sankey Type Definitions
 *
 * Extends D3 types with specific properties needed for our Sankey diagram implementation.
 * These types represent the augmented node and link objects after D3-Sankey processing.
 */

import { SankeyGraph, SankeyNode as D3SankeyNode, SankeyLink as D3SankeyLink } from 'd3-sankey';

/**
 * Source node data before D3-Sankey processing
 */
export interface SankeyNodeDatum {
  name: string;
  type: 'source_parent' | 'source' | 'ontology' | 'agent';
  id: string;
  sourceSystem?: string;
  parentId?: string;
}

/**
 * Source link data before D3-Sankey processing
 */
export interface SankeyLinkDatum {
  source: number;
  target: number;
  value: number;
  edgeType?: 'hierarchy' | 'dataflow';
  sourceSystem?: string;
  targetType?: string;
  fieldMappings?: FieldMapping[];
  tableFields?: string[];
  edgeLabel?: string;
  entityFields?: string[];
  entityName?: string;
}

/**
 * Field mapping structure for link tooltips
 */
export interface FieldMapping {
  source: string;
  onto_field: string;
  confidence?: number;
}

/**
 * Augmented Sankey node after D3-Sankey processing
 * Contains original data plus layout properties computed by d3-sankey
 */
export interface SankeyNode extends D3SankeyNode<SankeyNodeDatum, SankeyLinkDatum> {
  // Properties from D3SankeyNode
  x0?: number;
  x1?: number;
  y0?: number;
  y1?: number;
  depth?: number;
  height?: number;
  value?: number;
  // Properties from our source data
  name: string;
  type: string;
  id: string;
  sourceSystem?: string;
  parentId?: string;
  // Computed properties
  sourceLinks?: SankeyLink[];
  targetLinks?: SankeyLink[];
  index?: number;
}

/**
 * Augmented Sankey link after D3-Sankey processing
 * Contains original data plus layout properties computed by d3-sankey
 */
export interface SankeyLink extends D3SankeyLink<SankeyNodeDatum, SankeyLinkDatum> {
  // Properties from D3SankeyLink
  source: SankeyNode;
  target: SankeyNode;
  y0?: number;
  y1?: number;
  width?: number;
  value: number;
  // Properties from our source data
  edgeType?: 'hierarchy' | 'dataflow';
  sourceSystem?: string;
  targetType?: string;
  fieldMappings?: FieldMapping[];
  tableFields?: string[];
  edgeLabel?: string;
  entityFields?: string[];
  entityName?: string;
  index?: number;
}

/**
 * Complete Sankey graph structure after D3-Sankey processing
 */
export interface SankeyGraphData extends SankeyGraph<SankeyNodeDatum, SankeyLinkDatum> {
  nodes: SankeyNode[];
  links: SankeyLink[];
}

/**
 * Node styling properties
 */
export interface NodeStyle {
  fill: string;
  stroke?: string;
  strokeWidth?: number;
  fillOpacity?: number;
}

/**
 * Label data for node labels
 */
export interface LabelData {
  element: SVGGElement;
  nodeData: SankeyNodeDatum;
  d: SankeyNode;
  label: string;
  fontSize: number;
  pillHeight: number;
  pillWidth: number;
  padding: number;
  xPos: number;
  yPos: number;
  borderColor: string;
}

/**
 * D3 Selection types for our specific use cases
 */
export type D3Selection<T extends d3.BaseType = SVGSVGElement> = d3.Selection<T, unknown, null, undefined>;
export type D3NodeSelection = d3.Selection<SVGRectElement, SankeyNode, SVGGElement, unknown>;
export type D3LinkSelection = d3.Selection<SVGPathElement, SankeyLink, SVGGElement, unknown>;
export type D3GroupSelection = d3.Selection<SVGGElement, SankeyNode, SVGGElement, unknown>;

/**
 * Re-export d3 namespace for convenience
 */
import * as d3 from 'd3';
export type { d3 };
