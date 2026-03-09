import type { DemoDefinition } from '../demoTypes';
import { e2eDataFlowDemo } from './e2eDataFlow';
import { maestraDemo } from './maestraDemo';

/** All available guided demos */
export const AVAILABLE_DEMOS: DemoDefinition[] = [e2eDataFlowDemo, maestraDemo];
