import AOAStatusCard from './AOAStatusCard';
import AOADetailsModal from './AOADetailsModal';
import AOAFunctionsPanel from './AOAFunctionsPanel';
import DCLGraphContainer from './DCLGraphContainer';
import AgentPerformanceMonitor from './AgentPerformanceMonitor';
import {
  mockAgentNodes,
  mockDCLStats,
  mockMappingReviews,
  mockSchemaChanges,
  mockAgentPerformance,
} from '../mocks/data';

export default function DashboardPage() {
  return (
    <div className="space-y-6">
      <div className="px-6 py-4 space-y-1">
        <h1 className="text-2xl font-semibold text-white">Agentic Orchestration Hub</h1>
        <p className="text-sm text-gray-400">
          Continuous oversight of agent activity and Data Connectivity Layer performance.
        </p>
      </div>

      <DCLGraphContainer
        mappings={mockMappingReviews}
        schemaChanges={mockSchemaChanges}
      />

      <div className="grid grid-cols-1 lg:grid-cols-[1fr_300px] gap-6">
        <AOAStatusCard />
        <AgentPerformanceMonitor agents={mockAgentPerformance} />
      </div>
      
      <AOAFunctionsPanel />

      <AOADetailsModal />
    </div>
  );
}
