export default function HeroSection() {
  const scrollToDCL = () => {
    const dclElement = document.getElementById('dcl-graph-container');
    if (dclElement) {
      dclElement.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  };

  return (
    <div className="px-6 py-12 space-y-6">
      {/* Main Hero Content */}
      <div className="space-y-4">
        <div className="mb-4">
          <img 
            src="/assets/autonomos-logo.png" 
            alt="autonomOS"
            className="h-16 w-auto"
          />
        </div>
        <h2 className="text-2xl font-semibold text-white">
          The Operating System for the Intelligent Enterprise
        </h2>
        <p className="text-lg text-gray-300 max-w-3xl flex items-center gap-2 flex-wrap">
          <img 
            src="/assets/autonomos-logo.png" 
            alt="autonomOS"
            className="h-6 w-auto inline-block"
          />
          <span>connects, normalizes, maps, and orchestrates
          your enterprise data <span className="text-cyan-400 font-semibold">automatically</span> — freeing
          your teams to focus on insights, not integration.</span>
        </p>
      </div>

      {/* Value Proposition */}
      <div className="pt-4 space-y-2">
        <p className="text-xl">
          <span className="text-cyan-400">Stop building pipelines.</span>
        </p>
        <p className="text-2xl font-semibold text-white">
          Start delivering outcomes.
        </p>
      </div>

      {/* Run Live Demo Button */}
      <div className="pt-6">
        <button
          onClick={scrollToDCL}
          className="bg-cyan-500 hover:bg-cyan-600 text-white font-semibold px-8 py-3 rounded-lg transition-colors duration-200 shadow-lg hover:shadow-cyan-500/50"
        >
          Run Live Demo
        </button>
      </div>
    </div>
  );
}
