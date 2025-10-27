export default function HeroSection() {
  const scrollToDCL = () => {
    const dclElement = document.getElementById('dcl-graph-container');
    if (dclElement) {
      dclElement.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  };

  return (
    <div className="px-6 py-12">
      {/* Main Hero Content */}
      <div>
        <img 
          src="/assets/autonomos-logo.png" 
          alt="autonomOS" 
          className="h-16 object-contain -mt-12 -ml-5"
        />
        <h2 className="text-xl font-medium text-white mt-[-55px]">
          The Operating System for the Intelligent Enterprise
        </h2>
        <p className="text-2xl font-normal text-gray-200 max-w-3xl leading-relaxed mt-4">
          <span className="text-cyan-400 font-medium">autonomOS</span> connects, normalizes, maps, and orchestrates
          your enterprise data <span className="text-cyan-400 font-medium">automatically</span> — freeing
          your teams to focus on insights, not integration.
        </p>
      </div>

      {/* Value Proposition */}
      <div className="mt-6">
        <p className="text-3xl font-medium">
          <span className="text-cyan-400">Stop building pipelines.</span> <span className="text-white">Start delivering outcomes.</span>
        </p>
      </div>

      {/* Run Live Demo Button */}
      <div className="mt-8">
        <button
          onClick={scrollToDCL}
          className="bg-cyan-500 hover:bg-cyan-600 text-white font-medium px-8 py-3 rounded-lg transition-colors duration-200 shadow-lg hover:shadow-cyan-500/50"
        >
          Run Live Demo
        </button>
      </div>
    </div>
  );
}
