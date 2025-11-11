import NLPGateway from './NLPGateway';

export default function ControlCenterPage() {
  return (
    <div className="space-y-8 px-4 sm:px-6 py-6">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-4xl font-bold text-white mb-4">Control Center</h1>
        <p className="text-lg text-gray-300 max-w-4xl leading-relaxed">
          Natural language interface to all AutonomOS services. Query your data, manage finances, investigate incidents, and discover dependencies—all through conversational AI with RAG-powered knowledge retrieval.
        </p>
      </div>

      <NLPGateway />
    </div>
  );
}
