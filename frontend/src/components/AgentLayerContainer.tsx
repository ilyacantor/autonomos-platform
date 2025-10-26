export default function AgentLayerContainer() {
  return (
    <div className="bg-gradient-to-br from-slate-900/60 to-slate-800/40 rounded-xl border border-slate-700/50 p-8">
      <div className="grid grid-cols-1 lg:grid-cols-[1fr_400px] gap-8 items-center">
        {/* Left: Robot Agents Image */}
        <div className="flex items-center justify-center">
          <img 
            src="/assets/robot-agents.png" 
            alt="AI Agents with holographic interfaces"
            className="w-full max-w-2xl h-auto object-contain rounded-lg"
          />
        </div>

        {/* Right: Description Text */}
        <div className="flex items-center">
          <p className="text-xl text-gray-300 leading-relaxed">
            Provides persistent, versioned data mappings so AI agents can reason with 
            consistent, validated inputs.
          </p>
        </div>
      </div>
    </div>
  );
}
