export default function DCLSankeyPlaceholder() {
  return (
    <div className="rounded-xl bg-gray-800/40 border border-gray-700 shadow-sm ring-1 ring-cyan-500/10 p-3 h-full">
      <div className="relative w-full h-full mx-auto" style={{ minHeight: '500px' }}>
        <div className="absolute top-2 left-2 z-10">
          <span className="text-xs text-gray-400 uppercase tracking-wider font-semibold">
            Live DCL Connectivity Graph
          </span>
        </div>

        <div className="flex flex-col items-center justify-center h-full pt-6">
          <img
            src="/image.png"
            alt="Data Sources to Tables to Unified Ontology to Agents"
            className="object-contain max-h-full max-w-full mx-auto opacity-90"
          />
        </div>

        <div className="absolute bottom-2 left-0 right-0 text-center">
          <p className="text-xs text-gray-400">
            Data Sources → Tables → Unified Ontology → Agents
          </p>
        </div>
      </div>
    </div>
  );
}
